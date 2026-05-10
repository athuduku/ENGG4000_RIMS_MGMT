import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django_ratelimit.decorators import ratelimit
from defusedxml import ElementTree as ET
from config.decorators import researcher_required
from config.utils import log_action
from config.services.ccv_parser import (
    parse_xml_education, parse_xml_funding, parse_xml_recognitions,
    parse_xml_publications, parse_xml_activities, parse_xml_projects,
    parse_xml_supervision, parse_xml_student_profile,
    validate_ccv_structure, process_xml_file,
)
from config.models import (
    CustomUser, ResearcherProfile, StudentNotification
)


# TODO: This view processes XML files synchronously.
# For production, bulk processing should be moved to a Celery background task.
# A Celery-ready task (process_ccv_async) has been drafted in services/ccv_parser.py.
# Requires Redis + Celery workers to be configured at deploy time.
@ratelimit(key='ip', rate='2/m', block=True)
@login_required(login_url='login')
@require_http_methods(["POST"])
def bulk_upload(request):
    if getattr(request.user, 'user_type', None) != 'admin':
        return JsonResponse({'success': False, 'error': 'Admins only'}, status=403)

    files = request.FILES.getlist('files')
    if not files:
        return JsonResponse({'success': False, 'error': 'No files provided'}, status=400)

    # File count limit
    MAX_FILES = 10
    if len(files) > MAX_FILES:
        return JsonResponse({'success': False, 'error': f'Maximum {MAX_FILES} files per upload.'}, status=400)

    results = []
    successful = failed = 0

    for file_obj in files:
        filename = file_obj.name

        # Reject non-XML
        if not filename.lower().endswith('.xml'):
            results.append({
                'filename': filename,
                'success': False,
                'error': 'Only XML files are allowed'
            })
            failed += 1
            continue

        # Reject large files
        if file_obj.size > 5 * 1024 * 1024:
            results.append({
                'filename': filename,
                'success': False,
                'error': 'File too large (max 5MB)'
            })
            failed += 1
            continue

        try:
            tree = ET.parse(file_obj)
            xml_root = tree.getroot()

            if "generic-cv" not in xml_root.tag:
                raise ValueError("Invalid CCV XML format")

            is_valid, error = validate_ccv_structure(xml_root)
            if not is_valid:
                results.append({
                    'filename': filename,
                    'success': False,
                    'error': error
                })
                failed += 1
                continue

            file_obj.seek(0)

            # Process as researcher (pending approval handled inside) in atomic transactions

            try:
                with transaction.atomic():
                    result = process_xml_file(file_obj)
                    if not result['success']:
                        raise ValueError(result.get('error', 'Processing failed'))
            except ValueError as e:
                result = {
                    'filename': filename,
                    'success': False,
                    'error': str(e)
                }

        except Exception as e:
            result = {
                'filename': filename,
                'success': False,
                'error': f'Invalid XML: {str(e)}'
            }

        results.append(result)

        if result['success']:
            log_action(
                request,
                'ccv_uploaded',
                summary=f"CCV uploaded: {result.get('researcher', 'Unknown')}",
                details={
                    'filename': filename,
                    'records': result.get('total_records', 0)
                }
            )
            successful += 1
        else:
            failed += 1

    summary = f"Processed {len(files)} file(s): {successful} successful, {failed} failed"

    return JsonResponse({
        'success': successful > 0,
        'message': summary,
        'results': results,
    })

@ratelimit(key='ip', rate='3/m', block=True)
@login_required
@require_http_methods(["POST"])
def student_upload_ccv(request):

    if request.user.user_type != "student":
        return JsonResponse({'success': False, 'error': 'Students only'}, status=403)

    files = request.FILES.getlist('files')
    if not files:
        return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)

    file_obj = files[0]

    if file_obj.content_type not in ['text/xml', 'application/xml']:
        return JsonResponse({'error': 'Invalid file type'}, status=400)

    if file_obj.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'error': 'File too large (max 5MB)'}, status=400)

    # ── Parse XML ───────────────────────────────
    try:
        tree = ET.parse(file_obj)
        xml_root = tree.getroot()

        for elem in xml_root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]

        if "generic-cv" not in xml_root.tag:
            return JsonResponse({'success': False, 'error': 'Invalid CCV format'}, status=400)

    except ET.ParseError as e:
        return JsonResponse({'success': False, 'error': f'Invalid XML: {e}'}, status=400)

    # ── Validate ownership before processing ────
    xml_email_field = xml_root.find('.//field[@label="Email Address"]/value')

    if xml_email_field is None or not xml_email_field.text:
        return JsonResponse({
            'success': False,
            'error': 'Could not verify CCV ownership'
        }, status=403)

    if xml_email_field.text.strip().lower() != request.user.email.strip().lower():
        return JsonResponse({
            'success': False,
            'error': 'CCV ownership could not be verified'
        }, status=403)

    # ── Validate CCV structure ───────────────────
    is_valid, error = validate_ccv_structure(xml_root, user_type='student')
    if not is_valid:
        return JsonResponse({'success': False, 'error': error}, status=400)

    # ── Process XML ──────────────────────────────
    try:
        result = parse_xml_student_profile(request.user, xml_root)

        log_action(
            request,
            'ccv_student_uploaded',
            summary=f'{request.user.get_full_name()} uploaded CCV',
            details={
                'activities':   result['activities'],
                'publications': result['publications'],
                'recognitions': result['recognitions'],
            }
        )

        for admin_user in CustomUser.objects.filter(user_type='admin'):
            StudentNotification.objects.create(
                user=admin_user,
                message=(
                    f'{request.user.get_full_name()} uploaded their CCV | '
                    f"{result['activities']} activities, "
                    f"{result['publications']} publications, "
                    f"{result['recognitions']} recognitions imported."
                )
            )

        return JsonResponse({
            'success': True,
            'message': (
                f"Profile updated — {result['activities']} activities, "
                f"{result['publications']} publications, "
                f"{result['recognitions']} recognitions imported."
            ),
            'degree_level': result['degree_level'] or '',
            'department':   result['department'] or '',
        })

    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)

@ratelimit(key='ip', rate='3/m', block=True)
@login_required
@researcher_required
@require_http_methods(["POST"])
def researcher_upload_ccv(request):

    files = request.FILES.getlist('files')
    if not files:
        return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)

    file_obj = files[0]

    if file_obj.content_type not in ['text/xml', 'application/xml']:
        return JsonResponse({'error': 'Invalid file type'}, status=400)

    if file_obj.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'error': 'File too large'}, status=400)

    # ── Parse XML ───────────────────────────────
    try:
        tree = ET.parse(file_obj)
        xml_root = tree.getroot()

        for elem in xml_root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]

        if "generic-cv" not in xml_root.tag:
            return JsonResponse({'success': False, 'error': 'Invalid CCV format'}, status=400)

    except ET.ParseError as e:
        return JsonResponse({'success': False, 'error': f'Invalid XML: {e}'}, status=400)

    # ── Validate ownership before processing ────
    xml_email_field = xml_root.find('.//field[@label="Email Address"]/value')

    if xml_email_field is None or not xml_email_field.text:
        return JsonResponse({
            'success': False,
            'error': 'Could not verify CCV ownership.'
        }, status=403)

    if xml_email_field.text.strip().lower() != request.user.email.strip().lower():
        return JsonResponse({
            'success': False,
            'error': 'CCV ownership could not be verified.'
        }, status=403)

    # ── Validate CCV structure ───────────────────
    is_valid, error = validate_ccv_structure(xml_root, user_type='researcher')
    if not is_valid:
        return JsonResponse({'success': False, 'error': error}, status=400)

    # ── Process XML ──────────────────────────────
    try:
        researcher, _ = ResearcherProfile.objects.get_or_create(user=request.user)

        total = 0

        try:
            with transaction.atomic():
                total += parse_xml_education(researcher, xml_root)
                total += parse_xml_recognitions(researcher, xml_root)
                total += parse_xml_projects(researcher, xml_root)
                total += parse_xml_funding(researcher, xml_root)
                total += parse_xml_publications(researcher, xml_root)
                total += parse_xml_activities(researcher, xml_root)
                total += parse_xml_supervision(researcher, xml_root)
        except Exception as e:
            return JsonResponse({'error': 'Import failed and was rolled back. Please try again.'}, status=500)

        log_action(
            request,
            'ccv_uploaded',
            summary=f'CCV uploaded: {request.user.get_full_name()}',
            details={'records': total, 'filename': file_obj.name}
        )

        for admin_user in CustomUser.objects.filter(user_type='admin'):
            StudentNotification.objects.create(
                user=admin_user,
                message=f'{request.user.get_full_name()} uploaded their CCV | {total} records imported.'
            )

        return JsonResponse({
            'success': True,
            'message': f'Profile updated — {total} records imported.'
        })

    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)