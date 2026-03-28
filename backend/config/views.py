from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import PasswordResetForm
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from datetime import datetime
import json
import re
import xml.etree.ElementTree as ET

from .models import (
    CustomUser,
    Project,
    ProjectMember,
    ResearcherProfile,
    Education,
    Funding,
    Recognition,
    Report,
    Patent,
    Activity,
    Publication
)

User = get_user_model()

# =========================================================
# BASIC PAGES
# =========================================================

def index_view(request):
    return render(request, "Pages/home.html")


@login_required(login_url="login")
@never_cache
def dashboard_view(request):
    context = {"user": request.user}

    researcher = ResearcherProfile.objects.filter(user=request.user).first()

    if researcher:
        context['researcher'] = researcher
        context['education_count'] = Education.objects.filter(researcher=researcher).count()
        context['funding_count'] = Funding.objects.filter(researcher=researcher).count()
        context['awards_count'] = Recognition.objects.filter(researcher=researcher).count()

        total_funding = Funding.objects.filter(researcher=researcher).aggregate(
            total=Sum('amount')
        )['total'] or 0

        context['total_funding'] = total_funding
        context['total_funding_formatted'] = f"{int(total_funding):,}"

        context['recent_activities'] = Activity.objects.filter(
            researcher=researcher
        ).order_by('-date')[:5]

        all_projects = Project.objects.filter(
            researcher=researcher
        ).order_by('-start_date')

        context['active_projects'] = [p for p in all_projects if p.is_active][:3]
        context['projects_count'] = all_projects.count()

    return render(request, "Pages/dashboard.html", context)


# =========================================================
# AUTH
# =========================================================

@csrf_exempt
def signup_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(email=email).exists():
            return JsonResponse({"error": "Email already registered"}, status=400)

        user = User.objects.create_user(
            username=name,
            email=email,
            password=password,
            user_type="student",
            approval_status="approved"
        )
        return JsonResponse({"success": "Account created successfully!"})

    return render(request, "Pages/User_Auth/signup.html")


@csrf_exempt
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return JsonResponse({"redirect": "/dashboard/"})

        return JsonResponse({"error": "Invalid email or password."}, status=401)

    return render(request, "Pages/User_Auth/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# =========================================================
# PUBLICATIONS (UPDATED WITH AND / OR + SORT)
# =========================================================

@login_required
def view_publications(request):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        publications = Publication.objects.filter(researcher=researcher)
    except ResearcherProfile.DoesNotExist:
        publications = Publication.objects.none()

    # Sorting
    sort_by = request.GET.get("sort", "recent")

    if sort_by == "oldest":
        publications = publications.order_by("publication_date")
    elif sort_by == "title-asc":
        publications = publications.order_by("title")
    elif sort_by == "title-desc":
        publications = publications.order_by("-title")
    else:
        publications = publications.order_by("-publication_date")

    # Advanced Search
    search_query = request.GET.get("search")

    if search_query:
        query = Q()

        if " AND " in search_query:
            parts = search_query.split(" AND ")
            for part in parts:
                query &= (
                    Q(title__icontains=part.strip()) |
                    Q(authors__icontains=part.strip()) |
                    Q(journal__icontains=part.strip())
                )

        elif " OR " in search_query:
            parts = search_query.split(" OR ")
            for part in parts:
                query |= (
                    Q(title__icontains=part.strip()) |
                    Q(authors__icontains=part.strip()) |
                    Q(journal__icontains=part.strip())
                )
        else:
            query = (
                Q(title__icontains=search_query) |
                Q(authors__icontains=search_query) |
                Q(journal__icontains=search_query)
            )

        publications = publications.filter(query)

    return render(request, 'Pages/forms/view_publications.html', {
        'publications': publications,
        'publication_count': publications.count()
    })


@login_required
def add_publication(request):
    researcher, _ = ResearcherProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        Publication.objects.create(
            researcher=researcher,
            title=request.POST.get('title'),
            authors=request.POST.get('authors'),
            journal=request.POST.get('journal'),
            publication_date=request.POST.get('publication_date'),
            doi=request.POST.get('doi'),
            url=request.POST.get('url'),
            abstract=request.POST.get('abstract'),
            publication_type=request.POST.get('publication_type')
        )
        return JsonResponse({"success": True})

    return render(request, 'Pages/forms/add_publication.html')


@login_required
def delete_publication(request, publication_id):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        publication = Publication.objects.get(id=publication_id, researcher=researcher)
        publication.delete()
        return JsonResponse({"success": True})
    except:
        return JsonResponse({"success": False}, status=404)


# =========================================================
# PROJECTS (UPDATED WITH AND / OR + SORT)
# =========================================================

@login_required
def view_projects(request):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        projects = Project.objects.filter(researcher=researcher)
    except ResearcherProfile.DoesNotExist:
        projects = Project.objects.none()

    sort_by = request.GET.get("sort", "recent")

    if sort_by == "oldest":
        projects = projects.order_by("start_date")
    elif sort_by == "title-asc":
        projects = projects.order_by("title")
    elif sort_by == "title-desc":
        projects = projects.order_by("-title")
    else:
        projects = projects.order_by("-start_date")

    search_query = request.GET.get("search")

    if search_query:
        query = Q()

        if " AND " in search_query:
            parts = search_query.split(" AND ")
            for part in parts:
                query &= Q(title__icontains=part.strip())
        elif " OR " in search_query:
            parts = search_query.split(" OR ")
            for part in parts:
                query |= Q(title__icontains=part.strip())
        else:
            query = Q(title__icontains=search_query)

        projects = projects.filter(query)

    return render(request, 'Pages/projects/view_projects.html', {
        'projects': projects
    })


# =========================================================
# ACTIVITIES (UPDATED WITH AND / OR + SORT)
# =========================================================

@login_required
def view_activities(request):
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        activities = Activity.objects.filter(researcher=researcher)
    except ResearcherProfile.DoesNotExist:
        activities = Activity.objects.none()

    sort_by = request.GET.get("sort", "recent")

    if sort_by == "oldest":
        activities = activities.order_by("date")
    elif sort_by == "title-asc":
        activities = activities.order_by("title")
    elif sort_by == "title-desc":
        activities = activities.order_by("-title")
    else:
        activities = activities.order_by("-date")

    search_query = request.GET.get("search")

    if search_query:
        query = Q()

        if " AND " in search_query:
            parts = search_query.split(" AND ")
            for part in parts:
                query &= Q(title__icontains=part.strip())
        elif " OR " in search_query:
            parts = search_query.split(" OR ")
            for part in parts:
                query |= Q(title__icontains=part.strip())
        else:
            query = Q(title__icontains=search_query)

        activities = activities.filter(query)

    return render(request, 'Pages/forms/view_activities.html', {
        'activities': activities
    })
