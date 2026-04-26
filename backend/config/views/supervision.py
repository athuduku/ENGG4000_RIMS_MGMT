import json
import re
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Q
from config.decorators import researcher_required
from config.utils import log_action
from config.models import (
    CustomUser, ResearcherProfile, StudentProfile,
    SupervisionRecord, SupervisorRequest, StudentNotification
)


@login_required
@require_http_methods(["POST"])
def api_request_supervisor(request):
    """Student requests a researcher as their supervisor."""
    if request.user.user_type != 'student':
        return JsonResponse({'success': False, 'error': 'Students only'}, status=403)
    try:
        data = json.loads(request.body)
        supervisor_id = data.get('supervisor_id')
        if not supervisor_id:
            return JsonResponse({'success': False, 'error': 'supervisor_id required'}, status=400)

        supervisor = ResearcherProfile.objects.get(id=supervisor_id)
        student_profile = StudentProfile.objects.get(user=request.user)

        # Check if already has an approved supervisor
        if student_profile.supervisor:
            return JsonResponse({
                'success': False,
                'error': f'You already have an assigned supervisor: {student_profile.supervisor.user.get_full_name()}'
            }, status=400)

        # Check for existing pending request to this supervisor
        existing = SupervisorRequest.objects.filter(
            student=student_profile, supervisor=supervisor, status='pending',
        ).first()
        if existing:
            return JsonResponse({
                'success': False,
                'error': 'You already have a pending request to this supervisor.'
            }, status=400)

        sup_request = SupervisorRequest.objects.create(
            student=student_profile, supervisor=supervisor, status='pending',
        )

        # Notify admins
        for admin_user in CustomUser.objects.filter(user_type='admin'):
            StudentNotification.objects.create(
                user=admin_user,
                message=f'{request.user.get_full_name()} requested {supervisor.user.get_full_name()} as their supervisor.',
                request_id=sup_request.id,    # fixed: was missing
            )

        # Notify the supervisor directly
        StudentNotification.objects.create(
            user=supervisor.user,
            message=f'{request.user.get_full_name()} has requested you as their supervisor.',
            request_id=sup_request.id,
        )

        # Audit log
        log_action(
            request, 'supervisor_requested', target=sup_request,
            summary=f'{request.user.get_full_name()} requested {supervisor.user.get_full_name()} as supervisor',
            details={'supervisor_id': supervisor.id, 'student_id': student_profile.id},
        )

        return JsonResponse({
            'success': True,
            'message': f'Supervisor request sent to {supervisor.user.get_full_name()}.',
            'request_id': sup_request.id,
        })
    except ResearcherProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Researcher not found'}, status=404)
    except StudentProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)



@login_required
@require_http_methods(["POST"])
def api_request_co_supervisor(request):
    if request.user.user_type != 'student':
        return JsonResponse({'success': False, 'error': 'Students only'}, status=403)
    try:
        data = json.loads(request.body)
        supervisor_id = data.get('supervisor_id')
        if not supervisor_id:
            return JsonResponse({'success': False, 'error': 'supervisor_id required'}, status=400)

        supervisor      = ResearcherProfile.objects.get(id=supervisor_id)
        student_profile = StudentProfile.objects.get(user=request.user)

        # Can't add primary supervisor as co-supervisor
        if student_profile.supervisor and student_profile.supervisor.id == supervisor.id:
            return JsonResponse({
                'success': False,
                'error': f'{supervisor.user.get_full_name()} is already your primary supervisor.'
            }, status=400)

        # Already a co-supervisor
        if student_profile.co_supervisors.filter(id=supervisor.id).exists():
            return JsonResponse({
                'success': False,
                'error': f'{supervisor.user.get_full_name()} is already your co-supervisor.'
            }, status=400)

        # Instantly add — no approval needed
        student_profile.co_supervisors.add(supervisor)

        # Notify the researcher
        StudentNotification.objects.create(
            user=supervisor.user,
            message=f'{request.user.get_full_name()} has added you as their co-supervisor.',
        )

        # Notify admins
        for admin_user in CustomUser.objects.filter(user_type='admin'):
            StudentNotification.objects.create(
                user=admin_user,
                message=f'{request.user.get_full_name()} added {supervisor.user.get_full_name()} as co-supervisor.',
            )

        log_action(
            request, 'supervisor_requested', target=student_profile,
            summary=f'{request.user.get_full_name()} added {supervisor.user.get_full_name()} as co-supervisor',
            details={'supervisor_id': supervisor.id, 'student_id': student_profile.id},
        )

        return JsonResponse({
            'success': True,
            'message': f'{supervisor.user.get_full_name()} added as co-supervisor.',
        })

    except ResearcherProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Researcher not found'}, status=404)
    except StudentProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)



@login_required
@require_http_methods(["POST"])
def api_remove_co_supervisor(request):
    if request.user.user_type != 'student':
        return JsonResponse({'success': False, 'error': 'Students only'}, status=403)
    try:
        data = json.loads(request.body)
        supervisor_id = data.get('supervisor_id')
        if not supervisor_id:
            return JsonResponse({'success': False, 'error': 'supervisor_id required'}, status=400)

        supervisor      = ResearcherProfile.objects.get(id=supervisor_id)
        student_profile = StudentProfile.objects.get(user=request.user)

        if not student_profile.co_supervisors.filter(id=supervisor.id).exists():
            return JsonResponse({'success': False, 'error': 'Not a co-supervisor.'}, status=400)

        student_profile.co_supervisors.remove(supervisor)

        StudentNotification.objects.create(
            user=supervisor.user,
            message=f'{request.user.get_full_name()} has removed you as their co-supervisor.',
        )

        log_action(
            request, 'profile_updated', target=student_profile,
            summary=f'{request.user.get_full_name()} removed {supervisor.user.get_full_name()} as co-supervisor',
        )

        return JsonResponse({'success': True, 'message': f'{supervisor.user.get_full_name()} removed as co-supervisor.'})

    except ResearcherProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Researcher not found'}, status=404)
    except StudentProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)




@login_required
@researcher_required
@require_http_methods(["POST"])
def api_update_supervision_record(request, record_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        record     = SupervisionRecord.objects.get(id=record_id, researcher=researcher)
        data       = json.loads(request.body)

        # ── reject empty payload ─────────────────────────
        if not data:
            return JsonResponse({'success': False, 'error': 'No data provided'}, status=400)

        updated = False

        # ── linked_student (manual override) ─────────────────────
        if 'linked_student_id' in data:
            sid = data.get('linked_student_id')
            if sid:
                # Only allow linking actual students, not researchers
                student = StudentProfile.objects.filter(
                    id=sid,
                    user__user_type='student'
                ).first()

                if not student:
                    return JsonResponse({
                        'success': False,
                        'error': 'Student not found or invalid account type.'
                    }, status=404)

                # Name similarity check
                record_name   = re.sub(r'[^a-zA-Z\s]', '', record.student_name.lower()).strip()
                student_name  = re.sub(r'[^a-zA-Z\s]', '', student.user.get_full_name().lower()).strip()
                record_parts  = set(record_name.split())
                student_parts = set(student_name.split())

                if not record_parts & student_parts:
                    return JsonResponse({
                        'success': False,
                        'error': f'Name mismatch — this record is for "{record.student_name}" '
                                f'but selected account belongs to "{student.user.get_full_name()}".'
                    }, status=400)

                if record.linked_student != student:
                    record.linked_student = student
                    updated = True
            else:
                if record.linked_student is not None:
                    record.linked_student = None
                    updated = True

        # ── department ────────────────────────────────────────
        if 'department' in data:
            new_val = (data.get('department') or '').strip() or None
            if record.department != new_val:
                record.department = new_val
                updated = True

        # ── expected_date ─────────────────────────────────────
        if 'expected_date' in data:
            from django.utils.dateparse import parse_date
            raw = data.get('expected_date') or ''
            if raw:
                parsed = parse_date(raw)
                if not parsed:
                    return JsonResponse({'success': False, 'error': 'Invalid date format'}, status=400)
            else:
                parsed = None
            if record.expected_date != parsed:
                record.expected_date = parsed
                updated = True

        # ── status ────────────────────────────────────────────
        if 'status' in data:
            new_val = data.get('status')
            if new_val in ('in_progress', 'completed') and record.status != new_val:
                record.status = new_val
                updated = True

        # ── degree_type ───────────────────────────────────────
        if 'degree_type' in data:
            valid   = {c[0] for c in SupervisionRecord.DEGREE_CHOICES}
            new_val = data.get('degree_type')
            if new_val in valid and record.degree_type != new_val:
                record.degree_type = new_val
                updated = True

        # ── only save and flag if something actually changed ──
        if updated:
            record.manually_overridden = True
            record.save()
            log_action(request, 'profile_updated', target=record,
                       summary=f'{request.user.get_full_name()} updated supervision record for "{record.student_name}"')

        return JsonResponse({
            'success': True,
            'updated': updated,
            'record': {
                'department':    record.department,
                'expected_date': str(record.expected_date) if record.expected_date else None,
                'status':        record.status,
                'degree_type':   record.degree_type,
            }
        })

    except SupervisionRecord.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Record not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)



@login_required
@require_POST
def api_review_supervisor_request(request, request_id):

    # ── Authorization: only the target supervisor or an admin may review ──
    if request.user.user_type == 'admin':
        req = get_object_or_404(SupervisorRequest, id=request_id)
    elif request.user.user_type == 'researcher':
        try:
            profile = ResearcherProfile.objects.get(user=request.user)
        except ResearcherProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
        req = get_object_or_404(SupervisorRequest, id=request_id, supervisor=profile)
    else:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    # ── End auth check ────────────────────────────────────────

    if req.status != "pending":
        return JsonResponse({
            "success": False,
            "error": "This request has already been reviewed."
        }, status=400)

    data   = json.loads(request.body)
    action = data.get("action")

    if action == "approve":
        req.status = "approved"
        student = req.student
        student.supervisor = req.supervisor
        student.save()
        StudentNotification.objects.create(
            user=student.user,
            message=f"{request.user.get_full_name()} approved your supervisor request."
        )
        log_action(request, 'supervisor_approved', target=req,
                summary=f'{request.user.get_full_name()} approved {req.student.user.get_full_name()} → {req.supervisor.user.get_full_name()}')

    elif action == "reject":
        req.status = "rejected"
        student = req.student
        StudentNotification.objects.create(
            user=student.user,
            message=f"{request.user.get_full_name()} rejected your supervisor request."
        )
        log_action(request, 'supervisor_rejected', target=req,
                summary=f'{request.user.get_full_name()} rejected {req.student.user.get_full_name()} → {req.supervisor.user.get_full_name()}')
    else:
        return JsonResponse({"success": False, "error": "Invalid action"}, status=400)

    req.save()
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["GET"])
def api_pending_supervisor_requests(request):
    """Researcher sees their pending requests. Admin sees all."""
    if request.user.user_type == 'admin':
        qs = SupervisorRequest.objects.filter(status='pending')
    elif request.user.user_type == 'researcher':
        try:
            profile = ResearcherProfile.objects.get(user=request.user)
            qs = SupervisorRequest.objects.filter(supervisor=profile, status='pending')
        except ResearcherProfile.DoesNotExist:
            return JsonResponse({'requests': []})
    else:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)

    qs = qs.select_related('student__user', 'supervisor__user').order_by('-created_at')
    return JsonResponse({'requests': [{
        'id': r.id,
        'student_name': r.student.user.get_full_name(),
        'student_email': r.student.user.email,
        'student_degree': r.student.get_degree_level_display() if r.student.degree_level else '',
        'student_department': r.student.department or '',
        'supervisor_name': r.supervisor.user.get_full_name(),
        'supervisor_id': r.supervisor.id,
        'submitted': r.created_at.strftime('%b %d, %Y'),
    } for r in qs]})

@login_required
@require_http_methods(["GET"])
def api_my_supervisor_requests(request):
    """Student sees their own supervisor requests and current status."""
    if request.user.user_type != 'student':
        return JsonResponse({'success': False, 'error': 'Students only'}, status=403)
    try:
        student_profile = StudentProfile.objects.get(user=request.user)
    except StudentProfile.DoesNotExist:
        return JsonResponse({'requests': [], 'current_supervisor': None})

    qs = SupervisorRequest.objects.filter(
        student=student_profile
    ).select_related('supervisor__user').order_by('-created_at')

    current_sup = None
    if student_profile.supervisor:
        current_sup = {
            'name': student_profile.supervisor.user.get_full_name(),
            'email': student_profile.supervisor.user.email,
        }
    return JsonResponse({
        'current_supervisor': current_sup,
        'requests': [{
            'id': r.id,
            'supervisor_name': r.supervisor.user.get_full_name(),
            'status': r.status,
            'submitted': r.created_at.strftime('%b %d, %Y'),
        } for r in qs],
    })


@login_required
@require_http_methods(["GET"])
def api_search_supervisors(request):
    """Search researchers available as supervisors."""
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})
    researchers = ResearcherProfile.objects.filter(
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(user__email__icontains=query) |
        Q(research_interests__icontains=query),
        user__user_type='researcher',
        user__approval_status='approved',
    ).select_related('user')[:10]
    return JsonResponse({'results': [{
        'id': r.id,
        'name': r.user.get_full_name(),
        'email': r.user.email,
        'title': r.title or '',
        'interests': (r.research_interests or '')[:120],
        'student_count': r.students.count(),
    } for r in researchers]})
