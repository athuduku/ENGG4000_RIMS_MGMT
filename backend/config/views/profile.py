import json
import re
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from config.utils import log_action
from config.models import (
    CustomUser, ResearcherProfile, StudentProfile,
    Education, Recognition, SupervisionRecord, StudentNotification
)


@login_required
def profile_view(request):
    student_profile    = None
    researcher_profile = None
    education          = []
    all_award_records  = []
    researchers        = []
    current_students   = []
    all_students       = []
    linked_student_ids = set()

    if request.user.user_type == 'student':
        student_profile = StudentProfile.objects.filter(user=request.user).first()
        researchers = ResearcherProfile.objects.select_related("user").filter(
            user__user_type="researcher"
        ).order_by("user__last_name")

    elif request.user.user_type == 'researcher':
        researcher_profile = ResearcherProfile.objects.filter(user=request.user).first()
        if researcher_profile:
            education = Education.objects.filter(
                researcher=researcher_profile
            ).order_by('-expected_date')

            all_award_records = Recognition.objects.filter(
                researcher=researcher_profile
            ).order_by('-start_date')

            current_students = SupervisionRecord.objects.filter(
                researcher=researcher_profile,
                status='in_progress',
            ).select_related(
                'linked_student__user'
            ).order_by('student_name')

            # IDs of students already linked to a record for this researcher
            linked_student_ids = set(
                SupervisionRecord.objects.filter(
                    researcher=researcher_profile,
                    linked_student__isnull=False,
                ).values_list('linked_student_id', flat=True)
            )

            all_supervised_names = SupervisionRecord.objects.filter(
                researcher=researcher_profile,
            ).values_list('student_name', flat=True)

            name_filters = Q()
            for name in all_supervised_names:
                parts = name.strip().split()
                if len(parts) >= 2:
                    name_filters |= Q(
                        user__first_name__iexact=parts[0],
                        user__last_name__iexact=parts[-1],
                    ) | Q(
                        user__first_name__iexact=parts[-1],
                        user__last_name__iexact=parts[0],
                    )

            all_students = StudentProfile.objects.select_related('user').filter(
                name_filters,
                user__approval_status='approved',
                user__user_type='student',
            ).order_by(
                'user__last_name', 'user__first_name'
            ) if name_filters else StudentProfile.objects.none()

    return render(request, 'Pages/editable/profile.html', {
        'student_profile':    student_profile,
        'researcher_profile': researcher_profile,
        'education':          education,
        'all_award_records':  all_award_records,
        'researchers':        researchers,
        'current_students':   current_students,
        'all_students':       all_students,
        'linked_student_ids': linked_student_ids,
    })


@login_required
@require_http_methods(["POST"])
def api_update_student_academic_info(request):
    if request.user.user_type != 'student':
        return JsonResponse({'success': False, 'error': 'Students only'}, status=403)
    try:
        data    = json.loads(request.body)
        profile = StudentProfile.objects.get(user=request.user)

        from django.utils.dateparse import parse_date

        def safe_date(val):
            if not val:
                return None
            parsed = parse_date(val)
            if not parsed:
                raise ValueError(f'Invalid date: {val}')
            return parsed

        valid_degrees = [c[0] for c in StudentProfile.DEGREE_CHOICES]

        degree_level = data.get('degree_level')
        if degree_level and degree_level not in valid_degrees:
            return JsonResponse({'success': False, 'error': 'Invalid degree level.'}, status=400)

        if 'degree_level' in data:
            profile.degree_level = degree_level or None
        if 'department' in data:
            profile.department = (data.get('department') or '').strip() or None
        if 'start_date' in data:
            profile.start_date = safe_date(data.get('start_date'))
        if 'expected_end_date' in data:
            profile.expected_end_date = safe_date(data.get('expected_end_date'))
        if 'thesis_title' in data:
            profile.thesis_title = (data.get('thesis_title') or '').strip() or None
        if 'graduation_date' in data:
            profile.graduation_date = safe_date(data.get('graduation_date'))

        profile.manually_overridden = True
        profile.save(update_fields=[
            'degree_level',
            'department',
            'start_date',
            'expected_end_date',
            'graduation_date',
            'thesis_title',
            'manually_overridden',
        ])

        log_action(request, 'profile_updated', target=profile,
                   summary=f'{request.user.get_full_name()} updated academic info')

        return JsonResponse({'success': True})

    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except StudentProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_update_basic_info(request):
    try:
        data = json.loads(request.body)
        user = request.user

        def sanitize_name(value, fallback):
            value = (value or fallback or '').strip()
            # Strip anything that isn't letters, spaces, hyphens, apostrophes
            value = re.sub(r"[^a-zA-Z\s\-\']", '', value)
            return value[:50]  # hard length cap

        user.first_name = sanitize_name(data.get('first_name'), user.first_name)
        user.last_name  = sanitize_name(data.get('last_name'),  user.last_name)

        # Email is not user-editable — only admins can change it via admin panel
        if user.user_type == 'researcher':
            org = data.get('organization', user.organization or '').strip()
            user.organization = org[:50]

        user.save()
        log_action(request, 'profile_updated', target=user,
                   summary=f'{user.get_full_name()} updated their profile')
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_update_research_interests(request):
    if request.user.user_type != 'researcher':
        return JsonResponse({'success': False, 'error': 'Not a researcher'}, status=403)
    try:
        data    = json.loads(request.body)
        profile = ResearcherProfile.objects.get(user=request.user)
        profile.research_interests = data.get('research_interests', '')
        profile.save()
        log_action(request, 'profile_updated', target=profile,
                   summary=f'{request.user.get_full_name()} updated research interests')
        return JsonResponse({'success': True})
    except ResearcherProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_update_edi(request):
    if request.user.user_type != 'student':
        return JsonResponse({'success': False, 'error': 'Students only'}, status=403)
    try:
        data    = json.loads(request.body)
        profile = StudentProfile.objects.get(user=request.user)
        profile.gender              = data.get('gender') or None
        profile.residency_status    = data.get('residency_status') or None
        profile.indigenous_identity = data.get('indigenous_identity') or None
        profile.race_ethnicity      = data.get('race_ethnicity') or None
        profile.edi_profile_completed = True
        profile.save()

        # ── Audit log — note what was provided (not the values) ──
        provided = [
            f for f, v in {
                'gender':              profile.gender,
                'residency_status':    profile.residency_status,
                'indigenous_identity': profile.indigenous_identity,
                'race_ethnicity':      profile.race_ethnicity,
            }.items() if v and v != 'prefer_not'
        ]
        summary = (
            f'{request.user.get_full_name()} updated EDI profile. '
            f'Fields provided: {", ".join(provided) if provided else "none (all prefer not to say)"}'
        )
        log_action(request, 'edi_updated', target=profile, summary=summary)
        return JsonResponse({'success': True})
    except StudentProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_update_consent(request):
    try:
        data = json.loads(request.body)
        request.user.consent_to_share = bool(data.get('consent_to_share', False))
        request.user.save()
        log_action(request, 'consent_updated', target=request.user,
                    summary=f'{request.user.get_full_name()} consent={request.user.consent_to_share}')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)