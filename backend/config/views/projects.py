# ─────────────────────────────────────────────
# Projects
# ─────────────────────────────────────────────

import csv
import json
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Q, Prefetch, Sum, Count
from django.db.models import Case, When, IntegerField
from config.decorators import admin_required, researcher_required
from config.utils import log_action, generate_project_summary, mask_financial_fields
from config.models import (
    CustomUser, ResearcherProfile,
    Project, ProjectMember, Funding,
    Publication, Activity, StudentNotification
)

@login_required
@researcher_required
def add_project(request):

    def parse_date(d):
        try:
            return datetime.strptime(d, "%Y-%m-%d").date() if d else None
        except:
            return None

    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            title                = data.get('title', '').strip()
            description          = data.get('description', '').strip()
            funding_organization = data.get('funding_organization', '').strip()
            funding_type         = data.get('funding_type', '').strip()
            total_funding        = data.get('total_funding')
            funding_received     = data.get('funding_received')
            start_date           = data.get('start_date')
            end_date             = data.get('end_date')
            role                 = data.get('role', 'pi')
            status               = data.get('status', 'awarded')
            conception           = data.get('conception', '').strip()
            next_steps           = data.get('next_steps', '').strip()
            members              = data.get('members', [])
            hqp_ids              = data.get('hqp_ids', [])
            currency             = data.get('currency', 'CAD')

            if not title:
                return JsonResponse({'success': False, 'error': 'Title is required'}, status=400)

            researcher, _ = ResearcherProfile.objects.get_or_create(user=request.user)

            VALID_PARTNER_TYPES = ['academic', 'industry', 'community', 'government', 'other']
            VALID_ROLES = ['pi', 'co_pi', 'pa', 'co_app', 'other']

            with transaction.atomic():

                # ── Create Project ─────────────────────────────
                project = Project.objects.create(
                    researcher           = researcher,
                    title                = title,
                    description          = description or None,
                    funding_organization = funding_organization or None,
                    funding_type         = funding_type or None,
                    total_funding        = Decimal(total_funding) if total_funding else None,
                    funding_received     = Decimal(funding_received) if funding_received else None,
                    start_date           = parse_date(start_date),
                    end_date             = parse_date(end_date),
                    role                 = role,
                    status               = status,
                    conception           = conception or None,
                    next_steps           = next_steps or None,
                    source               = 'manual',
                    ccv_active           = True,
                    currency = currency,
                )

                # ── External collaborators / partners ─────────
                seen = set()

                for m in members:
                    name = (m.get('name') or '').strip()
                    key = name.lower()

                    if not name or key in seen:
                        continue
                    seen.add(key)

                    member_role  = m.get('role', 'other')
                    partner_type = m.get('partner_type', 'academic')

                    if member_role not in VALID_ROLES:
                        member_role = 'other'

                    if partner_type not in VALID_PARTNER_TYPES:
                        partner_type = 'other'

                    ProjectMember.objects.create(
                        project      = project,
                        name         = name,
                        role         = member_role,
                        partner_type = partner_type,
                        is_academic_collaborator = (partner_type == 'academic'),
                    )

                # ── HQP tagging ───────────────────────────────
                if hqp_ids:
                    tagged = CustomUser.objects.filter(
                        id__in=hqp_ids,
                        user_type='student',
                        approval_status='approved'
                    )

                    project.tagged_members.set(tagged)

                    for u in tagged:
                        StudentNotification.objects.create(
                            user=u,
                            message=f'{request.user.get_full_name()} has added you as HQP on the project "{title}".'
                        )

                # ── Logging ───────────────────────────────────
                log_action(
                    request,
                    'project_created',
                    target=project,
                    summary=f'{request.user.get_full_name()} created project "{title}"'
                )

                # ── Notify admins ─────────────────────────────────
                for admin_user in CustomUser.objects.filter(user_type='admin'):
                    StudentNotification.objects.create(
                        user=admin_user,
                        message=f'{request.user.get_full_name()} created a new project "{title}".'
                    )

            return JsonResponse({
                'success': True,
                'message': f'Project "{title}" created successfully.',
                'project_id': project.id,
            })

        except Exception as e:
            return JsonResponse({'error': 'Internal server error'}, status=500)

    # ── GET ──────────────────────────────────────────────────
    students = CustomUser.objects.filter(
        user_type='student',
        approval_status='approved',
    ).order_by('last_name', 'first_name')

    return render(request, 'Pages/projects/add_project.html', {
        'students': students,
    })


@login_required
@researcher_required
@require_http_methods(["POST"])
def delete_project(request, project_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        project = Project.objects.get(id=project_id, researcher=researcher)
        title = project.title
        project.soft_delete(user=request.user)
        log_action(request, 'project_deleted', target=project,
                   summary=f'{request.user.get_full_name()} deleted project "{title}"')
        return JsonResponse({'success': True, 'message': f'Project "{title}" deleted.'})
    except Project.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@researcher_required
def view_projects(request):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        projects   = Project.objects.filter(researcher=researcher, is_deleted=False)
    except ResearcherProfile.DoesNotExist:
        projects = Project.objects.none()

    sort_by = request.GET.get("sort", "recent")
    order   = {"oldest": "start_date", "title-asc": "title",
               "title-desc": "-title"}.get(sort_by, "-start_date")
    projects = projects.order_by(order)

    search_query = request.GET.get("search")
    if search_query:
        q = Q()
        if " AND " in search_query:
            for part in search_query.split(" AND "):
                q &= Q(title__icontains=part.strip())
        elif " OR " in search_query:
            for part in search_query.split(" OR "):
                q |= Q(title__icontains=part.strip())
        else:
            q = Q(title__icontains=search_query)
        projects = projects.filter(q)

    projects_list = []
    for project in projects:
        project.total_funding_received = project.funding_received or 0
        projects_list.append(project)

    return render(request, 'Pages/projects/view_projects.html', {'projects': projects_list})


@login_required
@researcher_required
def api_get_project(request, id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        project    = Project.objects.get(id=id, researcher=researcher)

        funding_type = project.funding_type

        # ── CCV team members ──────────────────────────────────
        team_members = [{
            'id':                       m.id,
            'name':                     m.name,
            'role':                     m.role,
            'role_display':             m.get_role_display(),
            'is_academic_collaborator': m.is_academic_collaborator,
            'partner_type':             m.partner_type or 'academic',
            'partner_type_display':     m.get_partner_type_display() if m.partner_type else 'Academic',
            'manually_added':           not m.is_academic_collaborator,  # ← CCV ones have is_academic_collaborator=True
        } for m in project.team_members.all()]

        # ── Tagged RIMS members ───────────────────────────────
        tagged_members = []
        for u in project.tagged_members.all():
            try:
                sp             = u.student_profile
                degree_level   = sp.degree_level or ''
                degree_display = sp.degree_label or ''
                department     = sp.department or ''
            except Exception:
                degree_level = degree_display = department = ''

            tagged_members.append({
                'id':             u.id,
                'name':           u.get_full_name(),
                'user_type':      u.user_type,
                'is_hqp':         u.user_type == 'student',
                'degree_level':   degree_level,
                'degree_display': degree_display,
                'department':     department,
            })


        project_data = {
            'id':                   project.id,
            'title':                project.title,
            'summary':              generate_project_summary(project),
            'description':          project.description or '',
            'status':               project.status,
            'is_active':            project.is_active,
            'funding_type':         funding_type,
            'role':                 project.role,
            'role_display':         project.get_role_display(),
            'start_date':           project.start_date.isoformat() if project.start_date else None,
            'end_date':             project.end_date.isoformat()   if project.end_date   else None,
            'funding_organization': project.funding_organization,
            'total_funding':        int(project.total_funding)       if project.total_funding       else None,
            'funding_received':     int(project.funding_received)    if project.funding_received    else None,
            'funding_kept_by_unb':  int(project.funding_kept_by_unb) if project.funding_kept_by_unb else None,
            'next_steps':           project.next_steps or '',
            'conception':           project.conception or '',
            'ip_activities':        project.ip_activities or '',
            'team_members':         team_members,
            'tagged_members':       tagged_members,
            'currency':             project.currency or 'CAD', 
        }

        return JsonResponse(mask_financial_fields(project_data, request.user))
    
    except Exception as e:
        return JsonResponse({'error': str(e), 'type': type(e).__name__}, status=404)




@login_required
@researcher_required
@require_http_methods(["POST"])
def api_update_project_status(request, project_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        project = Project.objects.get(id=project_id, researcher=researcher)
        data = json.loads(request.body)
        new_status = data.get('status', '')
        valid_statuses = ['awarded', 'completed', 'pending', 'submitted', 'rejected']
        if new_status in valid_statuses:
            project.status = new_status
            project.manually_overridden = True
            project.save()
            log_action(request, 'project_updated', target=project,
                       summary=f'{request.user.get_full_name()} updated status of "{project.title}" to {new_status}')
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    except Project.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@researcher_required
@require_http_methods(["POST"])
def api_update_project_funding(request, project_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        project = Project.objects.get(id=project_id, researcher=researcher)
        data = json.loads(request.body)

        def to_decimal(val):
            try:
                return Decimal(str(val)) if val not in (None, '', 'null') else None
            except InvalidOperation:
                return None

        def to_date(val):
            try:
                return datetime.strptime(val, '%Y-%m-%d').date() if val else None
            except ValueError:
                return None

        project.funding_organization = data.get('funding_organization') or None
        project.funding_type         = data.get('funding_type') or None
        project.total_funding        = to_decimal(data.get('total_funding'))
        project.funding_received     = to_decimal(data.get('funding_received'))
        project.start_date           = to_date(data.get('start_date'))
        project.end_date             = to_date(data.get('end_date'))
        project.currency = data.get('currency') or 'CAD'

        project.manually_overridden = True

        project.save()

        log_action(request, 'project_updated', target=project,
                   summary=f'{request.user.get_full_name()} updated funding for "{project.title}"')
        return JsonResponse({'success': True})

    except Project.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)



@login_required
@researcher_required
def api_project_funding(request, project_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        project    = Project.objects.get(id=project_id, researcher=researcher)

        records = Funding.objects.filter(
            researcher=researcher,
            project=project,
        ).order_by('start_date')

        result = []
        for f in records:
            result.append({
                'organization':   f.organization  or '',
                'funding_type':   f.funding_type   or '',
                'program_name':   f.program_name   or '',
                'amount':         float(f.amount or 0),
                'grant_total':    float(f.grant_total or f.amount or 0),  # ← ADD
                'amount_to_ibme': float(f.amount_to_ibme) if f.amount_to_ibme else None,
                'start_date':     str(f.start_date) if f.start_date else None,
                'end_date':       str(f.end_date)   if f.end_date   else None,
                'currency':       f.currency or 'CAD',
            })

        return JsonResponse({
            'funding_records': mask_financial_fields(result, request.user),
            'computed_total':  sum(r['grant_total'] for r in result),   # ← use grant_total
            'computed_ibme':   sum(r['amount_to_ibme'] or 0 for r in result),
        })

    except ResearcherProfile.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_update_project_kept_by_unb(request, project_id):
    try:
        project = Project.objects.get(id=project_id, researcher__user=request.user)
        data    = json.loads(request.body)
        val     = data.get('funding_kept_by_unb')
        
        project.funding_kept_by_unb = Decimal(str(val)) if val else None
        project.manually_overridden = True  # ← add this
        project.save()
        log_action(request, 'project_updated', target=project,
                   summary=f'{request.user.get_full_name()} updated kept by UNB for "{project.title}"')
        return JsonResponse({'success': True})
    except Project.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
@researcher_required
def api_update_project_conception(request, id):
    """
    Researcher edits conception on their own projects via the modal.
    Admin can edit any project (also has Django admin access).
    Students are blocked.
    """
    if request.user.user_type == 'student':
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    try:
        if request.user.user_type == 'admin':
            project = get_object_or_404(Project, id=id)
        else:
            researcher = ResearcherProfile.objects.get(user=request.user)
            project    = get_object_or_404(Project, id=id, researcher=researcher)

        project.conception = json.loads(request.body).get('conception', '')
        project.save()
        log_action(request, 'project_updated', target=project,
                    summary=f'{request.user.get_full_name()} updated conception for "{project.title}"')
        return JsonResponse({'success': True})
    except ResearcherProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)

@login_required
@researcher_required
def api_update_project_next_steps(request, id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    try:
        researcher    = ResearcherProfile.objects.get(user=request.user)
        project       = Project.objects.get(id=id, researcher=researcher)
        project.next_steps = json.loads(request.body).get('next_steps', '')
        project.save()
        log_action(request, 'project_updated', target=project,
                   summary=f'{request.user.get_full_name()} updated next steps for "{project.title}"')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
@researcher_required
def update_project_ip(request, project_id):
    try:
        project = Project.objects.get(id=project_id, researcher__user=request.user)
        project.ip_activities = json.loads(request.body).get('ip_activities', '')
        project.save()
        log_action(request, 'project_updated', target=project,
                   summary=f'{request.user.get_full_name()} updated IP activities for "{project.title}"')
        return JsonResponse({'success': True})
    except Project.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)

@login_required
@researcher_required
@require_http_methods(["POST"])
def api_add_project_member(request, project_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        project    = Project.objects.get(id=project_id, researcher=researcher)
        data       = json.loads(request.body)

        name         = data.get('name', '').strip()
        role         = data.get('role', 'other')
        partner_type = data.get('partner_type', 'other')

        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required'}, status=400)

        member = ProjectMember.objects.create(
            project      = project,
            name         = name,
            role         = role,
            partner_type = partner_type,
            is_academic_collaborator = False,
        )

        log_action(request, 'project_updated', target=project,
                   summary=f'{request.user.get_full_name()} added external member "{name}" to "{project.title}"')

        return JsonResponse({
            'success': True,
            'member': {
                'id':           member.id,
                'name':         member.name,
                'role':         member.role,
                'role_display': member.get_role_display(),
                'partner_type': member.partner_type,
                'partner_type_display': member.get_partner_type_display(),
            }
        })
    except Project.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)



@login_required
@researcher_required
@require_http_methods(["POST"])
def api_tag_project_member(request, project_id, user_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        project    = Project.objects.get(id=project_id, researcher=researcher)
        user       = CustomUser.objects.get(id=user_id)

        project.tagged_members.add(user)

        StudentNotification.objects.create(
            user=user,
            message=f'{request.user.get_full_name()} has added you as HQP on the project "{project.title}".'
        )

        log_action(request, 'hqp_tagged', target=project,
                   summary=f'{request.user.get_full_name()} tagged {user.get_full_name()} as HQP on "{project.title}"',
                   details={'user_id': user.id, 'user_name': user.get_full_name(), 'project_id': project.id})

        return JsonResponse({'success': True})
    except Project.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)
    


@login_required
@researcher_required
@require_http_methods(["POST"])
def api_untag_project_member(request, project_id, user_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        project    = Project.objects.get(id=project_id, researcher=researcher)
        user       = CustomUser.objects.get(id=user_id)

        project.tagged_members.remove(user)

        StudentNotification.objects.create(
            user=user,
            message=f'{request.user.get_full_name()} has removed you from the project "{project.title}".'
        )

        log_action(request, 'hqp_untagged', target=project,
                   summary=f'{request.user.get_full_name()} removed {user.get_full_name()} from "{project.title}"',
                   details={'user_id': user.id, 'user_name': user.get_full_name(), 'project_id': project.id})

        return JsonResponse({'success': True})
    except Project.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)



@login_required
@researcher_required
@require_http_methods(["POST"])
def api_remove_project_member(request, project_id, member_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        project    = Project.objects.get(id=project_id, researcher=researcher)
        member     = ProjectMember.objects.get(id=member_id, project=project)
        name       = member.name
        member.delete()

        log_action(request, 'project_updated', target=project,
                   summary=f'{request.user.get_full_name()} removed "{name}" from "{project.title}"')

        return JsonResponse({'success': True})
    except (Project.DoesNotExist, ProjectMember.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)
    


@login_required
def api_get_team_members(request, project_id):
    try:
        project = get_object_or_404(
            Project,
            id=project_id,
            researcher__user=request.user
        )
        members = [{
            'id':                       m.id,
            'name':                     m.name,
            'role':                     m.role,
            'role_display':             m.get_role_display(),
            'partner_type':             m.partner_type or 'academic',
            'partner_type_display':     m.get_partner_type_display() if m.partner_type else 'Academic',
            'is_academic_collaborator': m.is_academic_collaborator,
            'manually_added':           not m.is_academic_collaborator,  # CCV = is_academic_collaborator=True
        } for m in project.team_members.all()]
        return JsonResponse({'members': members})
    except Project.DoesNotExist:
        return JsonResponse({'members': []})


@login_required
@researcher_required
def api_get_tagged_members(request, project_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        project    = Project.objects.get(id=project_id, researcher=researcher)
        members    = []

        for u in project.tagged_members.all():
            try:
                sp             = u.student_profile
                degree_level   = sp.degree_level or ''
                degree_display = sp.degree_label or ''
                department     = sp.department or ''
            except Exception:
                degree_level = degree_display = department = ''

            members.append({
                'id':             u.id,
                'name':           u.get_full_name(),
                'user_type':      u.user_type,
                'is_hqp':         u.user_type == 'student',
                'degree_level':   degree_level,
                'degree_display': degree_display,
                'department':     department,
            })

        return JsonResponse({'members': members})
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)
    

@login_required
@researcher_required
def export_projects_csv(request):
    researcher = request.user.researcherprofile
    projects   = Project.objects.filter(
        researcher=researcher,
        is_deleted=False,
    ).prefetch_related('team_members').order_by('-start_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="grants_projects.csv"'
    writer = csv.writer(response)
    writer.writerow(['Title','Status','Your Role','Funding Organization','Funding Type',
                     'Start Date','End Date', 'Currency', 'Total Funding','Amount Awarded to IBME', 'Amount Kept by IBME',
                     'Team Members','Academic Collaborators','Community / Industry Partners',
                     'Description','Next Steps','Linked Publications (count)','Linked KM Activities (count)'])
    for project in projects:
        team      = project.team_members.all()
        pub_count = project.linked_publications.filter(is_active=True).count()
        km_count  = project.linked_activities.filter(
            is_active=True, category='knowledge_mobilization').count()
        writer.writerow([
            project.title, project.get_status_display(), project.get_role_display(),
            project.funding_organization or '', project.funding_type or '',
            project.start_date or '', project.end_date or '',
            project.currency or 'CAD',
            project.total_funding or '', 
            project.funding_received or '',
            project.funding_kept_by_unb or '',
            '; '.join(m.name for m in team),
            '; '.join(m.name for m in team.filter(partner_type='academic')),
            '; '.join(m.name for m in team.exclude(partner_type='academic').exclude(partner_type=None)),
            project.description or '', project.next_steps or '',
            pub_count, km_count,
        ])
    return response


# ─────────────────────────────────────────────
# Project ↔ Publication / Activity Linking
# ─────────────────────────────────────────────

@login_required
@researcher_required
def api_search_publications(request, project_id):
    query  = request.GET.get('q', '').strip()
    recent = request.GET.get('recent') == '1'
    project    = get_object_or_404(Project, id=project_id, researcher=request.user.researcherprofile)
    researcher = project.researcher
    if not query and recent:
        pubs = Publication.objects.filter(researcher=researcher, is_active=True).order_by('-publication_date')[:10]
    elif len(query) >= 2:
        pubs = Publication.objects.filter(researcher=researcher, is_active=True,
                                          title__icontains=query).order_by('-publication_date')[:10]
    else:
        return JsonResponse({'results': []})
    linked_ids = set(project.linked_publications.values_list('id', flat=True))
    return JsonResponse({'results': [{
        'id': p.id, 'title': p.title, 'type': p.get_publication_type_display(),
        'year': str(p.publication_date)[:4] if p.publication_date else '',
        'journal': p.journal or '', 'linked': p.id in linked_ids,
    } for p in pubs]})


@login_required
@researcher_required
def api_search_activities(request, project_id):
    query  = request.GET.get('q', '').strip()
    recent = request.GET.get('recent') == '1'
    project    = get_object_or_404(Project, id=project_id, researcher=request.user.researcherprofile)
    researcher = project.researcher
    if not query and recent:
        acts = Activity.objects.filter(researcher=researcher, is_active=True).order_by('-date')[:10]
    elif len(query) >= 2:
        acts = Activity.objects.filter(researcher=researcher, is_active=True,
                                       title__icontains=query).order_by('-date')[:10]
    else:
        return JsonResponse({'results': []})
    linked_ids = set(project.linked_activities.values_list('id', flat=True))
    return JsonResponse({'results': [{
        'id': a.id, 'title': a.title, 'type': a.get_activity_type_display(),
        'category': a.get_category_display() if hasattr(a, 'get_category_display') else a.category,
        'date': a.date.strftime('%b %d, %Y') if a.date else '',
        'linked': a.id in linked_ids,
    } for a in acts]})


@login_required
@researcher_required
@require_http_methods(["POST"])
def api_link_publication(request, project_id, pub_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        Project.objects.get(id=project_id, researcher=researcher).linked_publications.add(
            Publication.objects.get(id=pub_id, researcher=researcher))
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=404)


@login_required
@require_http_methods(["POST"])
@researcher_required
def api_unlink_publication(request, project_id, pub_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        Project.objects.get(id=project_id, researcher=researcher).linked_publications.remove(
            Publication.objects.get(id=pub_id, researcher=researcher))
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=404)


@login_required
@require_http_methods(["POST"])
@researcher_required
def api_link_activity(request, project_id, act_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        Project.objects.get(id=project_id, researcher=researcher).linked_activities.add(
            Activity.objects.get(id=act_id, researcher=researcher))
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=404)


@login_required
@require_http_methods(["POST"])
@researcher_required
def api_unlink_activity(request, project_id, act_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        Project.objects.get(id=project_id, researcher=researcher).linked_activities.remove(
            Activity.objects.get(id=act_id, researcher=researcher))
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=404)


@login_required
@researcher_required
def api_get_linked_items(request, project_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        project    = Project.objects.get(id=project_id, researcher=researcher)
    except (ResearcherProfile.DoesNotExist, Project.DoesNotExist):
        return JsonResponse({'error': 'Not found'}, status=404)

    return JsonResponse({
        'publications': [{
            'id': p.id, 'title': p.title, 'type': p.get_publication_type_display(),
            'year': str(p.publication_date)[:4] if p.publication_date else '',
            'journal': p.journal or '',
        } for p in project.linked_publications.filter(is_active=True)],
        'activities': [{
            'id': a.id, 'title': a.title, 'type': a.get_activity_type_display(),
            'category': a.get_category_display() if hasattr(a, 'get_category_display') else a.category,
            'date': a.date.strftime('%b %d, %Y') if a.date else '',
        } for a in project.linked_activities.filter(is_active=True)],
    })

