import json
from collections import defaultdict
from datetime import date, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.db.models import Sum, Count, Q
from django.db.models.functions import ExtractYear
from config.models import (
    CustomUser, ResearcherProfile, StudentProfile,
    Publication, Activity, Funding, Project,
    Education, Recognition, SupervisionRecord
)

# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────

@never_cache
@login_required(login_url="login")
def dashboard_view(request):
    from collections import defaultdict
    from django.db.models.functions import ExtractYear
    from datetime import timedelta
    import json

    context = {"user": request.user}

    if request.user.approval_status != "approved":
        return redirect("login")

    # ─────────────────────────────────────────────
    # Admin
    # ─────────────────────────────────────────────
    if request.user.user_type == 'admin':
        context['total_researchers'] = CustomUser.objects.filter(
            user_type='researcher', approval_status='approved'
        ).count()
        context['total_students'] = CustomUser.objects.filter(
            user_type='student', approval_status='approved'
        ).count()
        context['total_admins'] = CustomUser.objects.filter(
            user_type='admin'
        ).count()

        active_funding_filter = Q(status='awarded') & (
            Q(end_date__gte=date.today()) | Q(end_date__isnull=True)
        )
        funding_agg = Funding.objects.filter(active_funding_filter).aggregate(
            total=Sum('amount'),
            count=Count('id'),
        )
        context['total_funding']           = funding_agg['total'] or 0
        context['total_funding_formatted'] = f"{int(context['total_funding']):,}"
        context['total_grants']            = funding_agg['count'] or 0
        context['total_education']         = Education.objects.count()

        context['researcher_funding'] = ResearcherProfile.objects.annotate(
            total=Sum('funding__amount')
        ).filter(funding__isnull=False).values(
            'user__first_name', 'user__last_name', 'total'
        )[:10]

        context['org_stats'] = (
            Funding.objects.values('organization')
            .annotate(count=Count('id')).order_by('-count')[:10]
        )
        return render(request, "Pages/dashboard.html", context)

    # ─────────────────────────────────────────────
    # Student
    # ─────────────────────────────────────────────
    elif request.user.user_type == 'student':
        MIN_PEER_THRESHOLD = 2
        three_years_ago    = date.today() - timedelta(days=3 * 365)

        student, _ = StudentProfile.objects.get_or_create(user=request.user)
        researcher = ResearcherProfile.objects.filter(user=request.user).first()

        context['student']        = student
        context['student_profile'] = student
        context['researcher']     = researcher
        context['today']          = date.today()
        context['student_education'] = Education.objects.filter(
            researcher=researcher
        ).order_by('-expected_date') if researcher else []

        if researcher:

            activities_list = list(
                Activity.objects.filter(
                    researcher=researcher
                ).order_by('-date')
            )
            context['activity_count']    = len(activities_list)
            context['recent_activities'] = activities_list[:6]
            context['conference_count']  = sum(
                1 for a in activities_list if a.category == 'conference'    
            )
            context['km_count'] = sum(
                1 for a in activities_list if a.category == 'knowledge_mobilization'
            )

            publications_list = list(
                Publication.objects.filter(
                    researcher=researcher
                ).order_by('-publication_date')
            )
            context['publication_count']   = len(publications_list)
            context['recent_publications'] = publications_list[:6]
        else:
            context.update({
                'activity_count': 0, 'recent_activities': [],
                'conference_count': 0, 'km_count': 0,
                'publication_count': 0, 'recent_publications': [],
            })

        # ── Peer stats ────────────────────────────────────────────────
        if student.supervisor:
            peer_students = CustomUser.objects.filter(
                user_type='student',
                student_profile__supervisor=student.supervisor,
            ).exclude(id=request.user.id)
        else:
            peer_students = CustomUser.objects.none()

        peer_student_count = peer_students.count()
        context['peer_student_count'] = peer_student_count
        context['peer_supervisor'] = (
            student.supervisor.user.get_full_name() if student.supervisor else None
        )

        if peer_student_count >= MIN_PEER_THRESHOLD:
            student_researchers = ResearcherProfile.objects.filter(
                user__in=peer_students
            )

            # Single query — compute all peer stats in Python
            peer_activities = list(
                Activity.objects.filter(
                    researcher__in=student_researchers,
                    date__gte=three_years_ago,
                    category__in=['conference', 'knowledge_mobilization'],
                ).values('category', 'date')
            )

            context['peer_conference_total'] = sum(
                1 for a in peer_activities if a['category'] == 'conference'
            )
            context['peer_km_total'] = sum(
                1 for a in peer_activities if a['category'] == 'knowledge_mobilization'
            )

            year_counts = defaultdict(int)
            for a in peer_activities:
                if a['category'] == 'conference' and a['date']:
                    year_counts[a['date'].year] += 1

            context['peer_by_year'] = json.dumps([
                {'year': y, 'count': c}
                for y, c in sorted(year_counts.items())
            ])
            context['peer_stats_available'] = True

        else:
            context.update({
                'peer_conference_total': None,
                'peer_km_total':         None,
                'peer_by_year':          '[]',
                'peer_stats_available':  False,
                'peer_stats_hidden_reason': (
                    'Peer statistics require at least 2 other students under your supervisor.'
                    if student.supervisor
                    else 'Peer statistics are available once you are assigned a supervisor.'
                ),
            })

        return render(request, "Pages/student_dashboard.html", context)

    # ─────────────────────────────────────────────
    # Researcher
    # ─────────────────────────────────────────────
    else:
        context['researcher_funding'] = []
        context['org_stats']          = []

        researcher = ResearcherProfile.objects.filter(user=request.user).first()

        if researcher:
            three_years_ago = date.today() - timedelta(days=3 * 365)

            context['researcher'] = researcher

            context['publication_count'] = Publication.objects.filter(
                researcher=researcher, is_active=True, is_deleted=False
            ).count()

            context['projects_count'] = Project.objects.filter(
                researcher=researcher, is_deleted=False
            ).count()

            context['recent_publications'] = list(
                Publication.objects.filter(
                    researcher=researcher, is_active=True
                ).order_by('-publication_date')[:6]
            )

            # Single aggregation for active funding
            context['total_funding'] = Funding.objects.filter(
                researcher=researcher,
                status='awarded',
            ).filter(
                Q(end_date__gte=date.today()) | Q(end_date__isnull=True)
            ).aggregate(total=Sum('amount'))['total'] or 0
            context['total_funding_formatted'] = f"{int(context['total_funding']):,}"

            context['recent_activities'] = list(
                Activity.objects.filter(
                    researcher=researcher
                ).order_by('-date')[:5]
            )

            # Funding by year
            funding_by_year = list(
                Funding.objects.filter(
                    researcher=researcher,
                ).annotate(year=ExtractYear('start_date'))
                .values('year')
                .annotate(total=Sum('amount'))
                .order_by('year')
            )
            context['funding_by_year'] = [
                {'year': r['year'], 'total': float(r['total'] or 0)}
                for r in funding_by_year
            ]

            # Top funding organizations
            context['top_orgs'] = list(
                Funding.objects.filter(researcher=researcher)
                .values('organization')
                .annotate(total=Sum('amount'))
                .order_by('-total')[:5]
            )

            # Active projects — prefetch to avoid per-project queries
            active_qs = Project.objects.active().filter(
                researcher=researcher
            ).order_by('-start_date')

            active_projects_list = []
            for p in active_qs:
                p.received_percent = (
                    (p.funding_received / p.total_funding * 100)
                    if p.total_funding and p.total_funding > 0
                    and p.funding_received is not None
                    else 0
                )
                active_projects_list.append(p)

            context['active_projects'] = active_projects_list[:3]

            context['supervising_count'] = SupervisionRecord.objects.filter(
                researcher=researcher,
                status='in_progress',
            ).count()

            context['education_records'] = list(
                Education.objects.filter(
                    researcher=researcher
                ).order_by('-expected_date')[:6]
            )

            context['all_award_records'] = list(
                Recognition.objects.filter(
                    researcher=researcher
                ).order_by('-start_date')[:6]
            )

        return render(request, "Pages/dashboard.html", context)