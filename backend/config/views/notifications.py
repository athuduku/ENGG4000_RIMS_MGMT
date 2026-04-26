import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from config.utils import log_action
from config.models import (
    CustomUser, StudentProfile,
    StudentNotification, ActivityReview,
    SupervisorRequest
)

@login_required
def notifications_view(request):
    context = {}
    if request.user.user_type == 'student':
        context['student'] = getattr(request.user, 'student_profile', None)
    return render(request, 'Pages/notifications.html', context)


@login_required
@require_http_methods(["GET"])
def api_get_notifications(request):
    notifications = StudentNotification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    unread_count = notifications.filter(is_read=False).count()

    data = []
    for n in notifications:
        item = {
            'id':          n.id,
            'message':     n.message,
            'is_read':     n.is_read,
            'created_at':  n.created_at.strftime('%b %d, %Y'),
            'request_id':  None,
            'activity_id': None,
        }

        # fixed: removed fragile message string check, just use request_id directly
        if n.request_id:
            try:
                req = SupervisorRequest.objects.get(id=n.request_id, status='pending')
                item['request_id'] = req.id
            except SupervisorRequest.DoesNotExist:
                pass

        data.append(item)

    notifications.filter(is_read=False).update(is_read=True)

    return JsonResponse({'notifications': data, 'unread_count': unread_count})


@login_required
@require_http_methods(["POST"])
def api_mark_notifications_read(request):
    try:
        StudentNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def api_clear_notifications(request):
    try:
        deleted_count, _ = StudentNotification.objects.filter(user=request.user).delete()
        return JsonResponse({'success': True, 'deleted': deleted_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def api_dismiss_notification(request, notif_id):
    try:
        deleted_count, _ = StudentNotification.objects.filter(id=notif_id, user=request.user).delete()
        if deleted_count == 0:
            return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_unread_count(request):
    count = StudentNotification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    return JsonResponse({'unread': count})



@login_required
def api_pending_activities(request):
    if request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': 'Admin only'}, status=403)
    reviews = ActivityReview.objects.filter(
        status='pending').select_related('activity__researcher__user').order_by('-created_at')
    return JsonResponse({'activities': [{
        'review_id':     r.id,
        'activity_id':   r.activity.id,
        'title':         r.activity.title,
        'type':          r.activity.get_activity_type_display(),
        'date':          r.activity.date.strftime('%b %d, %Y') if r.activity.date else '',
        'student':       r.activity.researcher.user.get_full_name(),
        'student_email': r.activity.researcher.user.email,
        'description':   r.activity.description or '',
        'submitted':     r.created_at.strftime('%b %d, %Y'),
        'location':      r.activity.location or '',
        'invited':       r.activity.invited,
        'keynote':       r.activity.keynote,
        'co_presenters': r.activity.co_presenters or '',
        'audience':      r.activity.audience or '',
        'tagged_users': [
            f"{u.first_name} {u.last_name}".strip()
            for u in r.activity.tagged_users.all()
        ]
    } for r in reviews]})
