import json
import csv
import re
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from config.decorators import researcher_required
from config.utils import log_action
from config.services.ccv_helpers import determine_activity_category
from config.models import (
    CustomUser, ResearcherProfile, StudentProfile,
    Activity, ActivityReview, StudentNotification,
    StrategicObjective, Conference
)

# ─────────────────────────────────────────────
# Activities
# ─────────────────────────────────────────────

from django.db.models import Q

@login_required
def view_activities(request):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        activities = Activity.objects.filter(
            Q(researcher=researcher) | Q(tagged_users=request.user),
            is_active=True
        ).prefetch_related('objectives').distinct()
    except ResearcherProfile.DoesNotExist:
        activities = Activity.objects.none()

    sort_by = request.GET.get("sort", "recent")
    order = {
        "oldest": "date",
        "title-asc": "title",
        "title-desc": "-title"
    }.get(sort_by, "-date")
    activities = activities.order_by(order)

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
        activities = activities.filter(q)

    return render(request, 'Pages/forms/view_activities.html', {
        'activities': activities
    })


@login_required
def api_get_objectives(request):
    return JsonResponse({
        'objectives': [
            {'id': o.id, 'name': o.name}
            for o in StrategicObjective.objects.all()
        ]
    })

@login_required
@require_http_methods(["POST"])
def api_log_activity(request):
    if request.user.user_type not in ('student', 'researcher'):
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    try:
        data          = json.loads(request.body)
        title         = data.get('title', '').strip()
        activity_type = data.get('activity_type', 'presentation')
        date_str      = data.get('date', '')
        location      = data.get('location', '')
        description   = data.get('description', '')
        invited       = data.get('invited')
        keynote       = data.get('keynote')
        conference_id = data.get('conference_id') or None
        co_presenters = data.get('co_presenters', '')
        force         = data.get('force', False)

        

        if not title or not date_str:
            return JsonResponse({'success': False, 'error': 'Title and date are required'}, status=400)

        try:
            activity_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'}, status=400)

        category = data.get('category', '').strip()
        category_was_inferred = False

        if not category:
            category = determine_activity_category(title, None, None, location)
            category_was_inferred = True

        # Only enforce conference requirement if user explicitly chose it
        if category == 'conference' and not conference_id and not category_was_inferred:
            return JsonResponse({
                'success': False,
                'error': 'Please select or create a conference for conference activities.'
            }, status=400)
        
        researcher = ResearcherProfile.objects.filter(user=request.user).first()
        if not researcher:
            researcher = ResearcherProfile.objects.create(
                user=request.user, research_interests=''
            )

        # ── Merged check: already owner OR tagged ─────────────
        already_associated = Activity.objects.filter(
            date=activity_date,
            title__iexact=title,
            is_active=True,
        ).filter(
            Q(researcher=researcher) | Q(tagged_users=request.user)
        ).first()

        if already_associated:
            return JsonResponse({
                'success': False,
                'error': 'This activity is already on your profile.',
            }, status=400)

        # ── Similar activity by someone else ──────────────────
        if not force:
            similar_qs = Activity.objects.filter(
                date=activity_date,
                title__iexact=title,
                is_active=True,
            ).exclude(researcher=researcher)

            # ──  include conference in match if provided ──
            if conference_id:
                similar_qs = similar_qs.filter(conference_id=conference_id)

            similar = similar_qs.first()

            if similar:
                return JsonResponse({
                    'success': False,
                    'similar_found': True,
                    'similar': {
                        'id':        similar.id,
                        'title':     similar.title,
                        'date':      str(similar.date),
                        'location':  similar.location or '',
                        'logged_by': similar.researcher.user.get_full_name(),
                    },
                    'message': 'A similar activity was found. Were you at the same event?'
                })

        # ── Create activity ───────────────────────────────────
        activity = Activity.objects.create(
            researcher=researcher,
            activity_type=activity_type,
            title=title,
            description=description,
            date=activity_date,
            location=location or None,
            invited=invited,
            keynote=keynote,
            category=category,
            source='manual',
            is_active=True,
            co_presenters=co_presenters or '',
            conference_id=conference_id or None,
        )

        objective_ids = data.get('objectives', [])

        if objective_ids:

            objs = StrategicObjective.objects.filter(id__in=objective_ids)
            activity.objectives.set(objs)

        log_action(request, 'activity_submitted', target=activity,
                   summary=f'{request.user.get_full_name()} logged "{activity.title}"')

        for admin_user in CustomUser.objects.filter(user_type='admin'):
            StudentNotification.objects.create(
                user=admin_user,
                message=f'{request.user.get_full_name()} logged a new activity "{activity.title}".',
            )

        tagged_ids = data.get('tagged_users', [])
        if tagged_ids:
            User = get_user_model()
            tagged = User.objects.filter(id__in=tagged_ids)
            activity.tagged_users.set(tagged)
            for u in tagged:
                StudentNotification.objects.create(
                    user=u,
                    message=f'{request.user.get_full_name()} tagged you in activity "{activity.title}".'
                )

        return JsonResponse({
            'success': True,
            'message': 'Activity logged successfully.',
            'activity_id': activity.id
        })

    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)
    


@login_required
@require_http_methods(["POST"])
def delete_activity(request, activity_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        activity = Activity.objects.get(id=activity_id, researcher=researcher)
        title = activity.title

        # Notify tagged users before deleting
        tagged_users = list(activity.tagged_users.all())
        for u in tagged_users:
            if u.user_type == 'researcher':
                msg = f'{request.user.get_full_name()} deleted "{title}" which you were tagged in.'
            else:
                msg = f'{request.user.get_full_name()} deleted "{title}" which you were tagged in. You may want to log it yourself.'
    
            StudentNotification.objects.create(user=u, message=msg)

        activity.soft_delete(user=request.user)
        log_action(request, 'activity_deleted', target=activity,
                   summary=f'{request.user.get_full_name()} deleted activity "{title}"')
        return JsonResponse({'success': True, 'message': f'Activity "{title}" deleted.'})
    except Activity.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Activity not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)



@login_required
def api_get_activity(request, activity_id):
    try:
        user = request.user

        # Get research profile safely
        researcher_profile = getattr(user, "researcherprofile", None)

        activity = Activity.objects.filter(
            Q(id=activity_id) &
            (
                Q(researcher=researcher_profile) | 
                Q(tagged_users=user)
            )
        ).distinct().first()

        if not activity:
            return JsonResponse({'error': 'Activity not found'}, status=404)

        tagged = [
            {'name': u.get_full_name() or u.username, 'user_type': u.user_type}
            for u in activity.tagged_users.all()
        ]

        return JsonResponse({
            'id': activity.id,
            'title': activity.title,
            'description': activity.description or '',
            'activity_type': activity.activity_type,
            'activity_type_display': activity.get_activity_type_display(),
            'category': activity.category or '',
            'category_display': activity.get_category_display() if activity.category else '',
            'date': activity.date.strftime('%b %d, %Y') if activity.date else None,
            'location': activity.location or '',
            'invited': activity.invited,
            'keynote': activity.keynote,
            'co_presenters': activity.co_presenters or '',
            'audience': activity.audience or '',
            'tagged_users': tagged,
            'source': activity.source, 
            'objectives': [o.name for o in activity.objectives.all()],
        })

    except Exception as e:
        print("API ERROR:", e)  # shows the real error in terminal
        return JsonResponse({'error': 'Internal server error'}, status=500)



@login_required
@require_http_methods(["POST"])
def api_tag_me_on_activity(request, activity_id):
    """Student confirms they attended the same event — tags themselves on existing activity."""
    try:
        activity = Activity.objects.get(id=activity_id, is_active=True)

        if activity.researcher.user == request.user:
            return JsonResponse({'success': False, 'error': 'This is your own activity.'}, status=400)

        # ──  explicit duplicate tag check ─────────────────
        if activity.tagged_users.filter(id=request.user.id).exists():
            return JsonResponse({
                'success': False,
                'error': 'You are already linked to this activity.'
            }, status=400)

        activity.tagged_users.add(request.user)

        StudentNotification.objects.create(
            user=activity.researcher.user,
            message=f'{request.user.get_full_name()} linked themselves to your activity "{activity.title}".'
        )

        return JsonResponse({
            'success': True,
            'message': f'You\'ve been linked to "{activity.title}".'
        })
    except Activity.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Activity not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
def api_search_conferences(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    conferences = Conference.objects.filter(
        Q(name__icontains=query) | Q(acronym__icontains=query)
    ).order_by('-year')[:10]
    return JsonResponse({'results': [{
        'id':       c.id,
        'name':     c.name,
        'acronym':  c.acronym or '',
        'year':     c.year or '',
        'location': c.location or '',
        'display':  str(c),
    } for c in conferences]})


@login_required
@require_http_methods(["POST"])
def api_create_conference(request):
    from .models import Conference
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'Name required'}, status=400)
        # parse year from name if present e.g. "EMBC 2024"
        import re
        year_match = re.search(r'\b(20\d{2})\b', name)
        year = int(year_match.group(1)) if year_match else None
        conf, created = Conference.objects.get_or_create(
            name=name,
            defaults={'year': year}
        )
        return JsonResponse({'success': True, 'id': conf.id, 'display': str(conf)})
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)
    


@login_required
def export_activities_csv(request):
    try:
        researcher = request.user.researcherprofile
    except ResearcherProfile.DoesNotExist:
        return HttpResponse("No researcher profile found.", status=404)

    activities = Activity.objects.filter(
        researcher=researcher,
        is_active=True
    ).order_by('-date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="activities.csv"'

    writer = csv.writer(response)

    writer.writerow([
        'Title',
        'Type',
        'Category',
        'Date',
        'Year',
        'Location',
        'Invited',
        'Keynote',
        'Co-presenters',
        'Audience',
        'Description',
    ])

    for a in activities:
        writer.writerow([
            a.title,
            a.get_activity_type_display(),
            a.get_category_display() if a.category else '',
            a.date or '',
            str(a.date)[:4] if a.date else '',
            a.location or '',
            'Yes' if a.invited else ('No' if a.invited is False else ''),
            'Yes' if a.keynote else ('No' if a.keynote is False else ''),
            a.co_presenters or '',
            a.audience or '',
            a.description or '',
        ])

    return response



@login_required
@require_http_methods(["POST"])
def api_review_activity(request, activity_id):
    from django.utils import timezone
    if request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': 'Admin only'}, status=403)
    try:
        review       = ActivityReview.objects.get(activity_id=activity_id)
        data         = json.loads(request.body)
        action       = data.get('action')
        reason       = data.get('reason', '').strip()
        student_user = review.activity.researcher.user

        if action == 'approve':
            review.status = 'approved'
            review.reviewed_by = request.user
            review.reviewed_at = timezone.now()
            review.save()

            log_action(request, 'activity_approved', target=review.activity,
                        summary=f'Approved "{review.activity.title}" by {student_user.get_full_name()}')

            StudentNotification.objects.create(
                user=student_user,
                message=f"Your activity \"{review.activity.title}\" was approved.",
            )

            # ── Copy to tagged researchers ─────────────────────────
            tagged_ids = review.activity.tagged_users.values_list('id', flat=True)
            for tagged_user in CustomUser.objects.filter(id__in=tagged_ids, user_type='researcher'):
                try:
                    researcher_profile = ResearcherProfile.objects.get(user=tagged_user)
                    obj, created = Activity.objects.get_or_create(
                        researcher=researcher_profile,
                        title=review.activity.title,
                        date=review.activity.date,
                        defaults={
                            'activity_type': review.activity.activity_type,
                            'category':      review.activity.category,
                            'description':   review.activity.description,
                            'location':      review.activity.location,
                            'invited':       review.activity.invited,
                            'keynote':       review.activity.keynote,
                            'co_presenters': review.activity.co_presenters,
                            'audience':      review.activity.audience,
                            'source':        'manual',
                            'is_active':     True,
                        }
                    )
                    if not created and not obj.is_active:
                        obj.is_active = True
                        obj.save(update_fields=['is_active'])
                except ResearcherProfile.DoesNotExist:
                    pass

            return JsonResponse({'success': True, 'message': 'Activity approved.'})

        elif action == 'reject':
            title = review.activity.title
            review.activity.delete()
            StudentNotification.objects.create(
                user=student_user,
                message=f"Your activity \"{title}\" was rejected. Reason: {reason or 'No reason provided'}",
            )
            return JsonResponse({'success': True, 'message': 'Activity rejected and deleted.'})

        return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)

    except ActivityReview.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Review not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


# ─────────────────────────────────────────────
# Peer Search
# ─────────────────────────────────────────────

@login_required
def api_peer_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'users': []})
    users = CustomUser.objects.filter(
        Q(first_name__icontains=query) | Q(last_name__icontains=query),
        user_type__in=['student', 'researcher'], is_active=True
    ).exclude(id=request.user.id)[:10]
    return JsonResponse({'users': [{
        'id': u.id, 'name': f"{u.first_name} {u.last_name}".strip() or u.username,
        'user_type': u.user_type, 'email': u.email,
    } for u in users]})