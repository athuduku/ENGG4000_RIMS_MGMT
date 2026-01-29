from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib.auth.forms import PasswordResetForm
from django.db.models import Sum, Count

User = get_user_model()

def index_view(request):
    return render(request, "Pages/home.html")

def form_view(request):
    return render(request, "Pages/form.html")

def view_reports(request):
    return render(request, "Pages/view_report.html")

def forgot_pass_view(request):
    return render(request, "Pages/User_Auth/forgot_pass.html")

@csrf_exempt
def signup_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        consent = request.POST.get("consent") == "true"

        if User.objects.filter(email=email).exists():
            return JsonResponse({"error": "Email already registered"}, status=400)

        user = User.objects.create_user(
            username=name,
            email=email,
            password=password,
            user_type="student",
            consent_to_share=consent  
        )
        user.save()

        return JsonResponse({"success": "Account created successfully!"})

    return render(request, "Pages/User_Auth/signup.html")



@csrf_exempt
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            if user.approval_status.lower() != "approved":
                return JsonResponse({
                    "error": "Your account is pending approval. Please wait for admin confirmation."
                }, status=403)

            login(request, user)
            return JsonResponse({"redirect": "/dashboard/"})

        return JsonResponse({"error": "Invalid email or password."}, status=401)

    return render(request, "Pages/User_Auth/login.html")



def logout_view(request):
    logout(request)
    messages.success(request, "You’ve been logged out successfully.")
    return redirect("login")

# views.py

@never_cache
@login_required(login_url="login")
def dashboard_view(request):
    from django.db.models import Sum, Count
    
    context = {"user": request.user}
    
    # If user is admin, show admin stats
    if request.user.user_type == 'admin':
        context['total_researchers'] = ResearcherProfile.objects.count()
        context['total_funding'] = Funding.objects.aggregate(total=Sum('amount'))['total'] or 0
        context['total_funding_formatted'] = f"{int(context['total_funding']):,}"
        context['total_grants'] = Funding.objects.count()
        context['total_education'] = Education.objects.count()
        
        researcher_funding = ResearcherProfile.objects.annotate(
            total=Sum('funding__amount')
        ).filter(funding__isnull=False).values('user__first_name', 'user__last_name', 'total')[:10]
        
        org_stats = Funding.objects.values('organization').annotate(count=Count('id')).order_by('-count')[:10]
        
        context['researcher_funding'] = researcher_funding
        context['org_stats'] = org_stats
    else:
        # Default empty data for non-admin
        context['researcher_funding'] = []
        context['org_stats'] = []
    
    # If user is researcher, show their stats
    researcher = ResearcherProfile.objects.filter(user=request.user).first()
    if researcher:
        context['researcher'] = researcher
        context['education_count'] = Education.objects.filter(researcher=researcher).count()
        context['funding_count'] = Funding.objects.filter(researcher=researcher).count()
        context['awards_count'] = Recognition.objects.filter(researcher=researcher).count()
        context['total_funding'] = Funding.objects.filter(researcher=researcher).aggregate(total=Sum('amount'))['total'] or 0
        context['total_funding_formatted'] = f"{int(context['total_funding']):,}"
        context['education_records'] = Education.objects.filter(researcher=researcher)
        context['funding_records'] = Funding.objects.filter(researcher=researcher).order_by('-start_date')[:5]
        context['award_records'] = Recognition.objects.filter(researcher=researcher).order_by('-start_date')
    
    return render(request, "Pages/dashboard.html", context)

@csrf_exempt
def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email").strip()
        form = PasswordResetForm({"email": email})

        if form.is_valid():
            form.save(
                request=request,
                use_https=True,
                from_email="no-reply@yourdomain.com",
                email_template_name="emails/password_reset_email.html"
            )
        
        # Always return the same message (to prevent email enumeration)
        return JsonResponse({
            "success": "If an account with that email exists, a password reset link has been sent."
        })
    
    return render(request, "Pages/User_Auth/forgot_pass.html")


# CORRECTED BULK UPLOAD HANDLER
# Add this to backend/config/views.py

import xml.etree.ElementTree as ET
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import CustomUser, ResearcherProfile, Education, Funding, Recognition


def extract_field_value(section, label_name):
    """Extract any field value from XML section by label - handles value/lov/refTable"""
    for field in section.findall('field'):
        if field.get('label') == label_name:
            # Try <value> tag
            value_elem = field.find('value')
            if value_elem is not None and value_elem.text:
                return value_elem.text.strip()
            # Try <lov> tag (list of values)
            lov_elem = field.find('lov')
            if lov_elem is not None and lov_elem.text:
                return lov_elem.text.strip()
    return None


def parse_xml_identification(user, xml_root):
    """Update CustomUser from CCV Identification section"""
    for section in xml_root.findall('.//section[@label="Identification"]'):
        first_name = extract_field_value(section, 'First Name')
        last_name = extract_field_value(section, 'Family Name')
        email = extract_field_value(section, 'Email Address')
        title = extract_field_value(section, 'Title')
        
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if email:
            user.email = email
        user.save()
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'title': title
        }
    return {}


def parse_xml_education(researcher, xml_root):
    """Create Education records from CCV - handles nested Degrees sections"""
    # Delete old education records - XML is source of truth
    Education.objects.filter(researcher=researcher).delete()
    
    count = 0
    for edu_section in xml_root.findall('.//section[@label="Education"]'):
        # Find all Degrees subsections
        for degree_section in edu_section.findall('section[@label="Degrees"]'):
            degree_type = extract_field_value(degree_section, 'Degree Type')
            degree_name = extract_field_value(degree_section, 'Degree Name')
            specialization = extract_field_value(degree_section, 'Specialization')
            organization = extract_field_value(degree_section, 'Organization')
            thesis_title = extract_field_value(degree_section, 'Thesis Title')
            start_date = extract_field_value(degree_section, 'Degree Start Date')
            completion_date = extract_field_value(degree_section, 'Degree Received Date')
            
            if degree_type and degree_name:
                Education.objects.create(
                    researcher=researcher,
                    degree_type=degree_type[:100],
                    specialization=specialization or '',
                    institution=organization or '',
                    thesis_title=thesis_title or '',
                    expected_date=completion_date or ''
                )
                count += 1
    
    return count


def parse_xml_funding(researcher, xml_root):
    """Create Funding records from CCV - handles nested Funding Sources"""
    # Delete old funding records - XML is source of truth
    Funding.objects.filter(researcher=researcher).delete()
    
    count = 0
    for funding_section in xml_root.findall('.//section[@label="Research Funding History"]'):
        # Skip "Under Review" grants
        status = extract_field_value(funding_section, 'Funding Status')
        if status == 'Under Review':
            continue
        
        title = extract_field_value(funding_section, 'Funding Title')
        if not title:
            continue
        
        # CRITICAL: Get org and amount from nested Funding Sources section
        org = None
        amount = None
        for source_section in funding_section.findall('section[@label="Funding Sources"]'):
            org = extract_field_value(source_section, 'Funding Organization')
            amount_str = extract_field_value(source_section, 'Total Funding')
            if amount_str:
                try:
                    amount = int(amount_str)
                except:
                    amount = None
            break
        
        if not org:
            continue
        
        # Parse dates: yyyy/MM format
        start_date = extract_field_value(funding_section, 'Funding Start Date')
        end_date = extract_field_value(funding_section, 'Funding End Date')
        role = extract_field_value(funding_section, 'Funding Role')
        
        Funding.objects.create(
            researcher=researcher,
            title=title,
            organization=org,
            amount=amount,
            start_date=start_date or '',
            end_date=end_date or ''
        )
        count += 1
    
    return count


def parse_xml_recognitions(researcher, xml_root):
    """Extract awards/recognitions from CCV"""
    # Delete old recognitions - XML is source of truth
    Recognition.objects.filter(researcher=researcher).delete()
    
    count = 0
    for recog_section in xml_root.findall('.//section[@label="Recognitions"]'):
        award_name = extract_field_value(recog_section, 'Recognition Name')
        if not award_name:
            continue
        
        award_type = extract_field_value(recog_section, 'Recognition Type')
        organization = extract_field_value(recog_section, 'Other Organization')
        date_str = extract_field_value(recog_section, 'Effective Date')
        amount_str = extract_field_value(recog_section, 'Amount')
        description = extract_field_value(recog_section, 'Description')
        
        # Try to convert amount to decimal
        amount = None
        if amount_str:
            try:
                amount = float(amount_str)
            except:
                amount = None
        
        Recognition.objects.create(
            researcher=researcher,
            name=award_name,
            organization=organization or '',
            amount=amount,
            start_date=date_str or '',
            description=description or ''
        )
        count += 1
    
    return count


def process_xml_file(file_obj):
    """Process a single CCV XML file and return results"""
    try:
        tree = ET.parse(file_obj)
        xml_root = tree.getroot()
    except ET.ParseError as e:
        return {
            'filename': file_obj.name,
            'success': False,
            'error': f'Invalid XML: {str(e)}'
        }
    
    try:
        # Get researcher name from Identification section
        ident_data = {}
        for section in xml_root.findall('.//section[@label="Identification"]'):
            ident_data = {
                'first_name': extract_field_value(section, 'First Name'),
                'last_name': extract_field_value(section, 'Family Name'),
                'email': extract_field_value(section, 'Email Address'),
                'title': extract_field_value(section, 'Title')
            }
            break
        
        first_name = ident_data.get('first_name')
        last_name = ident_data.get('last_name')
        email = ident_data.get('email')
        
        if not first_name or not last_name:
            return {
                'filename': file_obj.name,
                'success': False,
                'error': 'Could not find researcher name in XML'
            }
        
        # Generate email if not present
        if not email:
            email = f"{first_name.lower()}.{last_name.lower()}@unb.ca".replace(' ', '')
        
        # Get or create user
        username = f"{first_name.lower()}.{last_name.lower()}".replace(' ', '')
        
        user, user_created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'user_type': 'researcher',
                'organization': 'University of New Brunswick',
                'approval_status': 'approved'
            }
        )
        
        if not user_created:
            # Update existing user
            user.first_name = first_name
            user.last_name = last_name
            user.save()
        
        # Get or create researcher profile
        researcher, _ = ResearcherProfile.objects.get_or_create(
            user=user,
            defaults={'research_interests': ''}
        )
        
        # Parse all sections
        education_count = parse_xml_education(researcher, xml_root)
        funding_count = parse_xml_funding(researcher, xml_root)
        recognition_count = parse_xml_recognitions(researcher, xml_root)
        
        return {
            'filename': file_obj.name,
            'success': True,
            'researcher': f"{first_name} {last_name}",
            'email': email,
            'education': education_count,
            'funding': funding_count,
            'recognitions': recognition_count,
            'total_records': education_count + funding_count + recognition_count
        }
    
    except Exception as e:
        import traceback
        return {
            'filename': file_obj.name,
            'success': False,
            'error': f'Processing error: {str(e)}'
        }


def process_csv_file(file_obj):
    """Process a CSV file - placeholder for your CSV format"""
    # TODO: Implement based on your CSV structure
    return {
        'filename': file_obj.name,
        'success': False,
        'error': 'CSV processing not yet implemented. Please use XML files.'
    }


@login_required(login_url='login')
@require_http_methods(["POST"])
def bulk_upload(request):
    """Handle bulk upload of CSV/XML files"""
    
    # Check if user is admin
    if not hasattr(request.user, 'user_type') or request.user.user_type != 'admin':
        return JsonResponse({
            'success': False,
            'error': 'Only admins can perform bulk uploads'
        }, status=403)
    
    files = request.FILES.getlist('files')
    
    if not files:
        return JsonResponse({
            'success': False,
            'error': 'No files provided'
        }, status=400)
    
    results = []
    successful = 0
    failed = 0
    
    for file_obj in files:
        filename_lower = file_obj.name.lower()
        
        if filename_lower.endswith('.xml'):
            result = process_xml_file(file_obj)
        elif filename_lower.endswith('.csv'):
            result = process_csv_file(file_obj)
        else:
            result = {
                'filename': file_obj.name,
                'success': False,
                'error': 'Unsupported file type. Use .csv or .xml'
            }
        
        results.append(result)
        if result['success']:
            successful += 1
        else:
            failed += 1
    
    # Build response message
    summary = f"Processed {len(files)} file(s): {successful} successful, {failed} failed"
    
    if failed == 0:
        return JsonResponse({
            'success': True,
            'message': summary,
            'results': results
        })
    else:
        return JsonResponse({
            'success': False if successful == 0 else True,
            'message': summary,
            'error': 'Some files failed to process',
            'results': results
        }, status=200)  # Return 200 even with some failures to show partial results
    
    import os
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from .models import Report, ResearcherProfile
from PyPDF2 import PdfReader
import re

@login_required(login_url='login')
@require_http_methods(["POST"])
def upload_report(request):
    """Handle report PDF upload and auto-extraction"""
    
    try:
        # Get uploaded file
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)
        
        file = request.FILES['file']
        
        # Validation
        if file.size > 50 * 1024 * 1024:  # 50MB limit
            return JsonResponse({'success': False, 'error': 'File too large (max 50MB)'}, status=400)
        
        allowed_types = ['application/pdf', 'application/msword', 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        if file.content_type not in allowed_types:
            return JsonResponse({'success': False, 'error': 'Invalid file type. Use PDF or DOC'}, status=400)
        
        # Extract data from PDF
        extracted_data = extract_pdf_data(file)
        
        # Get or create researcher
        researcher = ResearcherProfile.objects.filter(user=request.user).first()
        if not researcher:
            researcher = ResearcherProfile.objects.create(user=request.user)
        
        # Save report
        report = Report.objects.create(
            researcher=researcher,
            title=extracted_data.get('title', 'Untitled'),
            date=extracted_data.get('date'),
            authors=', '.join(extracted_data.get('authors', ['Unknown'])),
            doc_type='Research Paper',
            subject=', '.join(extracted_data.get('keywords', [])),
            description=extracted_data.get('abstract', ''),
            report_file=file,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Report "{report.title}" uploaded successfully',
            'report_id': report.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def extract_pdf_data(file):
    """Extract metadata from PDF file"""
    
    try:
        # Read PDF
        pdf_reader = PdfReader(file)
        metadata = pdf_reader.metadata
        
        # Extract text from first 3 pages
        text = ""
        for page_num in range(min(3, len(pdf_reader.pages))):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        
        # Parse data
        result = {
            'title': extract_title(text, metadata),
            'authors': extract_authors(text),
            'date': extract_date(text, metadata),
            'abstract': extract_abstract(text),
            'keywords': extract_keywords(text)
        }
        
        return result
        
    except Exception as e:
        return {
            'title': 'Untitled Report',
            'authors': ['Unknown'],
            'date': None,
            'abstract': '',
            'keywords': []
        }


def extract_title(text, metadata):
    """Extract title"""
    if metadata and metadata.title:
        return metadata.title
    
    lines = text.split('\n')
    for line in lines:
        cleaned = line.strip()
        if 50 < len(cleaned) < 200:
            return cleaned
    
    return "Untitled Report"


def extract_authors(text):
    """Extract authors"""
    authors = []
    name_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
    matches = re.findall(name_pattern, text[:1000])
    
    if matches:
        authors = list(set(matches))[:5]
    
    return authors if authors else ['Unknown']


def extract_date(text, metadata):
    """Extract date"""
    if metadata and metadata.creation_date:
        return metadata.creation_date.date()
    
    year_pattern = r'(20\d{2})'
    matches = re.findall(year_pattern, text)
    
    if matches:
        return f"{matches[0]}-01-01"
    
    return None


def extract_abstract(text):
    """Extract abstract"""
    abstract_pattern = r'(?:abstract|summary)(.*?)(?:introduction|keywords|1\.|\n\n)'
    match = re.search(abstract_pattern, text, re.IGNORECASE | re.DOTALL)
    
    if match:
        return match.group(1).strip()[:500]
    
    return text[:300]


def extract_keywords(text):
    """Extract keywords"""
    keyword_pattern = r'(?:keywords?)(.*?)(?:\n\n|introduction|1\.)'
    match = re.search(keyword_pattern, text, re.IGNORECASE | re.DOTALL)
    
    if match:
        keywords_text = match.group(1)
        keywords = [k.strip() for k in keywords_text.split(',')]
        return keywords[:10]
    
    return []

@login_required
def get_reports(request):
    """Get reports - user's own and all reports"""
    researcher = ResearcherProfile.objects.filter(user=request.user).first()
    
    if researcher:
        user_reports = Report.objects.filter(researcher=researcher).order_by('-created_at')
    else:
        user_reports = []
    
    all_reports = Report.objects.all().order_by('-created_at')
    
    data = {
        'my_reports': format_reports(user_reports),
        'all_reports': format_reports(all_reports)
    }
    return JsonResponse(data)

def format_reports(reports):
    """Format reports for API response"""
    return [
        {
            'id': r.id,
            'title': r.title,
            'authors': r.authors,
            'doc_type': r.doc_type,
            'subject': (r.subject.lstrip(': ')[:80].rstrip() + '...') if r.subject else 'N/A',            'description': r.description,
            'date': r.date,
            'created_at': r.created_at,
            'report_file': r.report_file.url if r.report_file else None,
            'researcher': f"{r.researcher.user.first_name} {r.researcher.user.last_name}"
        }
        for r in reports
    ]

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Avg, Count, F, ExpressionWrapper, fields
from datetime import datetime
from .models import Education, ResearcherProfile

@login_required
def reports_list(request):
    """List all available reports"""
    return render(request, 'Pages/reports/reports_list.html')


@login_required
def grad_completion_report(request):
    """Generate Grad Completion Time Report"""
    
    # Get all education records
    education_records = Education.objects.all()
    
    if not education_records.exists():
        return render(request, 'Pages/reports/grad_completion_report.html', {
            'error': 'No education data available',
            'average_time': 0,
            'by_degree': {},
            'by_year': {}
        })
    
    # Calculate completion times
    completion_data = []
    
    for edu in education_records:
        try:
            degree_type = edu.degree_type or 'Unknown'
            
            # Estimate completion time based on degree type
            if 'master' in degree_type.lower():
                years = 2.0
            elif 'phd' in degree_type.lower():
                years = 5.0
            else:
                years = 3.5
            
            # Try to extract year from expected_date
            try:
                if edu.expected_date:
                    date_str = str(edu.expected_date)
                    year = int(date_str[:4])  # Get first 4 chars (year)
                else:
                    year = 2024
            except:
                year = 2024
            
            researcher_name = edu.researcher.user.get_full_name() if edu.researcher and edu.researcher.user else 'Unknown'
            
            completion_data.append({
                'degree_type': degree_type,
                'year': year,
                'duration': years,
                'researcher': researcher_name,
                'date': edu.expected_date
            })
        except Exception as e:
            print(f"Error processing education record: {e}")
            continue
    
    if not completion_data:
        return render(request, 'Pages/reports/grad_completion_report.html', {
            'error': 'Could not process education data',
            'average_time': 0,
            'by_degree': {},
            'by_year': {}
        })
    
    # Calculate statistics
    total_time = sum(d['duration'] for d in completion_data)
    average_time = total_time / len(completion_data) if completion_data else 0
    
    # By degree type
    by_degree = {}
    for degree in set(d['degree_type'] for d in completion_data):
        times = [d['duration'] for d in completion_data if d['degree_type'] == degree]
        by_degree[degree] = {
            'average': sum(times) / len(times),
            'count': len(times),
            'min': min(times),
            'max': max(times)
        }
    
    # By year
    by_year = {}
    for year in sorted(set(d['year'] for d in completion_data)):
        times = [d['duration'] for d in completion_data if d['year'] == year]
        by_year[year] = {
            'average': sum(times) / len(times),
            'count': len(times),
            'students': [d['researcher'] for d in completion_data if d['year'] == year]
        }
    
    context = {
        'average_time': round(average_time, 2),
        'by_degree': by_degree,
        'by_year': by_year,
        'total_students': len(completion_data),
        'completion_data': completion_data
    }
    
    return render(request, 'Pages/reports/grad_completion_report.html', context)


@login_required
def export_report_csv(request, report_type):
    """Export report as CSV"""
    import csv
    
    if report_type == 'grad_completion':
        # Get data
        education_records = Education.objects.filter(
            expected_date__isnull=False
        ).exclude(expected_date='')
        
        # Create CSV
        response = JsonResponse({
            'error': 'Export feature coming soon'
        })
        return response
    
    return JsonResponse({'error': 'Unknown report type'}, status=400)


@login_required
def enrollment_trends_report(request):
    """Generate Enrollment Trends Report"""
    
    # Get all education records
    education_records = Education.objects.all()
    
    if not education_records.exists():
        return render(request, 'Pages/reports/enrollment_trends_report.html', {
            'error': 'No education data available',
            'total_students': 0,
            'by_year': {},
            'by_degree': {}
        })
    
    try:
        # Process enrollment data
        enrollment_data = []
        
        for edu in education_records:
            try:
                degree_type = edu.degree_type or 'Unknown'
                
                # Extract year from expected_date (graduation year)
                try:
                    if edu.expected_date:
                        date_str = str(edu.expected_date)
                        year = int(date_str[:4])
                    else:
                        year = 2024
                except:
                    year = 2024
                
                researcher_name = edu.researcher.user.get_full_name() if edu.researcher and edu.researcher.user else 'Unknown'
                
                enrollment_data.append({
                    'degree_type': degree_type,
                    'year': year,
                    'researcher': researcher_name
                })
            except Exception as e:
                continue
        
        if not enrollment_data:
            return render(request, 'Pages/reports/enrollment_trends_report.html', {
                'error': 'Could not process enrollment data',
                'total_students': 0,
                'by_year': {},
                'by_degree': {}
            })
        
        # By Year
        by_year = {}
        for year in sorted(set(d['year'] for d in enrollment_data)):
            students = [d for d in enrollment_data if d['year'] == year]
            by_year[year] = {
                'count': len(students),
                'by_degree': {}
            }
            # Count by degree type for this year
            for degree in set(s['degree_type'] for s in students):
                degree_count = len([s for s in students if s['degree_type'] == degree])
                by_year[year]['by_degree'][degree] = degree_count
        
        # By Degree Type (overall)
        by_degree = {}
        for degree in set(d['degree_type'] for d in enrollment_data):
            students = [d for d in enrollment_data if d['degree_type'] == degree]
            by_degree[degree] = {
                'count': len(students),
                'percentage': round((len(students) / len(enrollment_data)) * 100, 1)
            }
        
        # Calculate growth rate
        years_sorted = sorted(by_year.keys())
        growth_rate = None
        if len(years_sorted) > 1:
            first_year_count = by_year[years_sorted[0]]['count']
            last_year_count = by_year[years_sorted[-1]]['count']
            if first_year_count > 0:
                growth_rate = round(((last_year_count - first_year_count) / first_year_count) * 100, 1)
        
        context = {
            'total_students': len(enrollment_data),
            'by_year': by_year,
            'by_degree': by_degree,
            'growth_rate': growth_rate,
            'year_range': f"{years_sorted[0]}-{years_sorted[-1]}" if years_sorted else "N/A"
        }
        
        return render(request, 'Pages/reports/enrollment_trends_report.html', context)
    
    except Exception as e:
        print(f"Error in enrollment_trends_report: {e}")
        return render(request, 'Pages/reports/enrollment_trends_report.html', {
            'error': f'Error processing data: {str(e)}',
            'total_students': 0,
            'by_year': {},
            'by_degree': {}
        })
    
@login_required
def funding_analysis_report(request):
    """Generate Funding Analysis Report"""
    
    # Get all funding records
    funding_records = Funding.objects.all()
    
    if not funding_records.exists():
        return render(request, 'Pages/reports/funding_analysis_report.html', {
            'error': 'No funding data available',
            'total_funding': 0,
            'by_organization': {},
            'by_year': {},
            'top_orgs': []
        })
    
    try:
        # Calculate funding by organization
        by_organization = {}
        by_year = {}
        total_funding_amount = 0
        
        for funding in funding_records:
            org = funding.organization or 'Unknown'
            amount = funding.amount or 0
            total_funding_amount += amount
            
            # By Organization
            if org not in by_organization:
                by_organization[org] = {'amount': 0, 'count': 0}
            by_organization[org]['amount'] += amount
            by_organization[org]['count'] += 1
            
            # By Year
            try:
                if funding.start_date:
                    date_str = str(funding.start_date)
                    year = int(date_str[:4])
                else:
                    year = 2024
            except:
                year = 2024
            
            if year not in by_year:
                by_year[year] = {'amount': 0, 'count': 0}
            by_year[year]['amount'] += amount
            by_year[year]['count'] += 1
        
        # Calculate statistics
        total_grants = funding_records.count()
        average_grant = total_funding_amount / total_grants if total_grants > 0 else 0
        
        # Top organizations (sorted by amount)
        top_orgs = sorted(
            by_organization.items(),
            key=lambda x: x[1]['amount'],
            reverse=True
        )[:10]
        
        # Format currency
        total_funding_formatted = f"${total_funding_amount:,.0f}"
        average_grant_formatted = f"${average_grant:,.0f}"
        
        context = {
            'total_funding': total_funding_formatted,
            'total_funding_raw': total_funding_amount,
            'total_grants': total_grants,
            'average_grant': average_grant_formatted,
            'by_organization': by_organization,
            'by_year': by_year,
            'top_orgs': top_orgs
        }
        
        return render(request, 'Pages/reports/funding_analysis_report.html', context)
    
    except Exception as e:
        print(f"Error in funding_analysis_report: {e}")
        return render(request, 'Pages/reports/funding_analysis_report.html', {
            'error': f'Error processing data: {str(e)}',
            'total_funding': 0,
            'by_organization': {},
            'by_year': {},
            'top_orgs': []
        })


@login_required
def top_researchers_report(request):
    """Generate Top Researchers Report - ranked by funding"""
    
    from django.core.paginator import Paginator
    
    # Get all researcher profiles with funding
    researchers = ResearcherProfile.objects.all()
    
    if not researchers.exists():
        return render(request, 'Pages/reports/top_researchers_report.html', {
            'error': 'No researcher data available',
            'top_researchers': [],
            'total_researchers': 0
        })
    
    try:
        researcher_data = []
        
        for researcher in researchers:
            # Calculate funding
            total_funding = Funding.objects.filter(researcher=researcher).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            grant_count = Funding.objects.filter(researcher=researcher).count()
            education_count = Education.objects.filter(researcher=researcher).count()
            award_count = Recognition.objects.filter(researcher=researcher).count()
            
            researcher_data.append({
                'researcher': researcher,
                'name': researcher.user.get_full_name(),
                'email': researcher.user.email,
                'total_funding': total_funding,
                'grant_count': grant_count,
                'education_count': education_count,
                'award_count': award_count
            })
        
        # Sort by total funding (descending)
        researcher_data.sort(key=lambda x: x['total_funding'], reverse=True)
        
        # Paginate - 5 per page
        paginator = Paginator(researcher_data, 5)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        # Calculate overall stats
        total_funding_all = sum(r['total_funding'] for r in researcher_data)
        total_grants_all = sum(r['grant_count'] for r in researcher_data)
        average_funding = total_funding_all / len(researcher_data) if researcher_data else 0
        
        context = {
            'page_obj': page_obj,
            'total_researchers': len(researcher_data),
            'total_funding': f"${total_funding_all:,.0f}",
            'total_grants': total_grants_all,
            'average_funding': f"${average_funding:,.0f}",
            'total_funding_raw': total_funding_all
        }
        
        return render(request, 'Pages/reports/top_researchers_report.html', context)
    
    except Exception as e:
        print(f"Error in top_researchers_report: {e}")
        return render(request, 'Pages/reports/top_researchers_report.html', {
            'error': f'Error processing data: {str(e)}',
            'top_researchers': [],
            'total_researchers': 0
        })
    

@login_required
def add_publication(request):
    """Add a new publication"""
    
    # Get researcher profile
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
    except ResearcherProfile.DoesNotExist:
        researcher = ResearcherProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            authors = request.POST.get('authors')
            journal = request.POST.get('journal')
            publication_date = request.POST.get('publication_date')
            doi = request.POST.get('doi')
            url = request.POST.get('url')
            abstract = request.POST.get('abstract')
            publication_type = request.POST.get('publication_type', 'journal')
            
            if not all([title, authors, journal, publication_date]):
                return JsonResponse({
                    'success': False,
                    'error': 'Title, Authors, Journal, and Date are required'
                }, status=400)
            
            publication = Publication.objects.create(
                researcher=researcher,
                title=title,
                authors=authors,
                journal=journal,
                publication_date=publication_date,
                doi=doi,
                url=url,
                abstract=abstract,
                publication_type=publication_type
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Publication "{title}" added successfully!',
                'publication_id': publication.id
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return render(request, 'Pages/forms/add_publication.html', {
        'researcher': researcher
    })


@login_required
def view_publications(request):
    """View all publications for current researcher"""
    
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        publications = Publication.objects.filter(researcher=researcher)
    except ResearcherProfile.DoesNotExist:
        publications = []
    
    return render(request, 'Pages/forms/view_publications.html', {
        'publications': publications,
        'publication_count': publications.count()
    })


@login_required
def delete_publication(request, publication_id):
    """Delete a publication"""
    
    try:
        researcher = ResearcherProfile.objects.get(user=request.user)
        publication = Publication.objects.get(id=publication_id, researcher=researcher)
        title = publication.title
        publication.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Publication "{title}" deleted successfully'
        })
    except Publication.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Publication not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
