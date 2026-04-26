import csv
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from config.decorators import researcher_required
from config.utils import log_action
from config.services.ccv_parser import auto_link_publication_authors
from config.models import (
    CustomUser, ResearcherProfile, StudentProfile,
    Publication, StudentNotification
)

@login_required
def add_publication(request):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
    except ResearcherProfile.DoesNotExist:
        researcher = ResearcherProfile.objects.create(user=request.user)

    if request.method == 'POST':
        try:
            title            = request.POST.get('title', '').strip()
            authors          = request.POST.get('authors', '').strip()
            journal          = request.POST.get('journal', '').strip()
            publication_date = request.POST.get('publication_date', '').strip()

            if not all([title, authors, journal, publication_date]):
                return JsonResponse({'success': False,
                                     'error': 'Title, Authors, Journal, and Date are required'}, status=400)

            # ── Duplicate check ───────────────────────────────
            existing = Publication.objects.filter(
                researcher=researcher,
                title__iexact=title,
                publication_date=publication_date,
                is_active=True,
            ).first()

            if existing:
                return JsonResponse({
                    'success': False,
                    'error': 'You already have a publication with this title and date.'
                }, status=400)

            pub = Publication.objects.create(
                researcher=researcher,
                title=title,
                authors=authors,
                journal=journal,
                publication_date=publication_date,
                doi=request.POST.get('doi'),
                url=request.POST.get('url'),
                abstract=request.POST.get('abstract'),
                publication_type=request.POST.get('publication_type', 'journal'),
                status=request.POST.get('status', 'published'),
                source='manual',
            )

            log_action(request, 'publication_added', target=pub,
                        summary=f'{request.user.get_full_name()} added "{title}"')
            
            for admin_user in CustomUser.objects.filter(user_type='admin'):
                StudentNotification.objects.create(
                    user=admin_user,
                    message=f'{request.user.get_full_name()} added a publication "{title}".',
                )

            auto_link_publication_authors(pub)
            
            return JsonResponse({'success': True, 'message': f'Publication "{title}" added!'})
        
        except Exception as e:
            return JsonResponse({'error': 'Internal server error'}, status=500)

    return render(request, 'Pages/forms/add_publication.html', {'researcher': researcher})


from django.shortcuts import render

@login_required
def view_linked_publications(request):
    if request.user.user_type != 'student':
        return redirect('dashboard')

    try:
        student = StudentProfile.objects.get(user=request.user)
    except StudentProfile.DoesNotExist:
        return render(request, 'Pages/forms/linked_publications.html', {
            'publications': [], 'count': 0, 'peer_count': 0,
        })

    VISIBLE_STATUSES = ['published', 'accepted', 'under_review']

    if student.supervisor:
        peer_students = StudentProfile.objects.filter(
            supervisor=student.supervisor
        ).exclude(user=request.user)

        peer_researcher_ids = list(
            peer_students.values_list('user__researcherprofile__id', flat=True)
        )

        co_supervisor_ids = list(
            student.co_supervisors.values_list('id', flat=True)
        )

        group_ids = [student.supervisor.id] + co_supervisor_ids + [r for r in peer_researcher_ids if r]

        publications = Publication.objects.filter(
            is_active=True,
            researcher__id__in=group_ids,
            status__in=VISIBLE_STATUSES,
        ).distinct().select_related(
            'researcher__user'
        ).order_by('-publication_date')

        peer_count = peer_students.count()

    elif student.department:
        publications = Publication.objects.filter(
            is_active=True,
            researcher__user__student_profile__department=student.department,
            status__in=VISIBLE_STATUSES,
        ).distinct().select_related(
            'researcher__user'
        ).order_by('-publication_date')

        peer_count = StudentProfile.objects.filter(
            department=student.department
        ).exclude(user=request.user).count()

    else:
        publications = Publication.objects.none()
        peer_count = 0

    return render(request, 'Pages/forms/linked_publications.html', {
        'publications': publications,
        'count':        publications.count(),
        'peer_count':   peer_count,
        'supervisor':   student.supervisor,
        'no_context':   not student.supervisor and not student.department,
    })

@login_required
def view_publications(request):
    try:
        researcher   = ResearcherProfile.objects.get(user=request.user)
        publications = Publication.objects.filter(researcher=researcher).distinct()
    except ResearcherProfile.DoesNotExist:
        publications = Publication.objects.none()

    sort_by = request.GET.get("sort", "recent")
    order   = {"oldest": "publication_date", "title-asc": "title",
               "title-desc": "-title"}.get(sort_by, "-publication_date")
    publications = publications.order_by(order)

    search_query = request.GET.get("search")
    if search_query:
        q = Q()
        if " AND " in search_query:
            for part in search_query.split(" AND "):
                q &= Q(title__icontains=part.strip()) | Q(authors__icontains=part.strip()) | Q(journal__icontains=part.strip())
        elif " OR " in search_query:
            for part in search_query.split(" OR "):
                q |= Q(title__icontains=part.strip()) | Q(authors__icontains=part.strip()) | Q(journal__icontains=part.strip())
        else:
            q = Q(title__icontains=search_query) | Q(authors__icontains=search_query) | Q(journal__icontains=search_query)
        publications = publications.filter(q)

    return render(request, 'Pages/forms/view_publications.html', {
        'publications': publications, 'publication_count': publications.count()
    })


@login_required
def delete_publication(request, publication_id):
    try:
        researcher  = ResearcherProfile.objects.get(user=request.user)
        publication = Publication.objects.get(id=publication_id, researcher=researcher)
        title       = publication.title
        publication.soft_delete(user=request.user)
        log_action(request, 'publication_deleted', target=publication,
            summary=f'{request.user.get_full_name()} deleted "{title}"')
        return JsonResponse({'success': True, 'message': f'Publication "{title}" deleted.'})
    except Publication.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Publication not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
def export_publications_csv(request):
    try:
        researcher = request.user.researcherprofile
    except ResearcherProfile.DoesNotExist:
        return HttpResponse("No researcher profile found.", status=404)

    publications = Publication.objects.filter(
        researcher=researcher, is_active=True
    ).order_by('-publication_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="publications.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Title', 'Authors', 'Type', 'Status', 'Journal / Conference / Publisher',
        'Publication Date', 'Year', 'Volume', 'Issue', 'Pages', 'DOI', 'Language',
        'Refereed', 'Open Access', 'Contribution Role', 'Conference Location',
        'Book Title', 'Editors', 'Patent Number', 'Country', 'Filing Date',
    ])
    for p in publications:
        writer.writerow([
            p.title, p.authors or '', p.get_publication_type_display(), p.get_status_display(),
            p.journal or '', p.publication_date or '',
            str(p.publication_date)[:4] if p.publication_date else '',
            p.volume or '', p.issue or '', p.pages or '', p.doi or '', p.language or '',
            'Yes' if p.refereed else ('No' if p.refereed is False else ''),
            'Yes' if p.open_access else ('No' if p.open_access is False else ''),
            p.contribution_role or '', p.conference_location or '', p.book_title or '',
            p.editors or '', p.patent_number or '', p.country or '', p.filing_date or '',
        ])
    return response


@login_required
@require_http_methods(["POST"])
def api_update_publication_status(request, publication_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        pub = Publication.objects.get(id=publication_id, researcher=researcher)
        data = json.loads(request.body)
        new_status = data.get('status', '')
        valid = ['published', 'accepted', 'under_review', 'revision_requested', 'rejected', 'pending', 'draft', 'granted']
        if new_status in valid:
            pub.status = new_status
            pub.save()
            log_action(request, 'publication_updated', target=pub,
                       summary=f'{request.user.get_full_name()} updated status of "{pub.title}" to {new_status}')
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    except Publication.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)
    

