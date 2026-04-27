"""
Authentication Views
--------------------
Handles login, signup, 2FA setup/verification,
logout, and password management.
"""

import base64
import secrets
import string
import uuid
import io
import json
import re
import time as time_module

from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
from jsonschema import ValidationError

from config.models import CustomUser, ResearcherProfile, StudentProfile, StudentNotification
from config.decorators import admin_required
from config.utils import log_action

User = get_user_model()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    pwd = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%"),
    ]
    pwd += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(pwd)
    return ''.join(pwd)


# ─────────────────────────────────────────────
# Basic Pages
# ─────────────────────────────────────────────

def index_view(request):
    return render(request, "Pages/home.html")


@login_required
def log_activity_page(request):
    return render(request, 'Pages/forms/log_activity.html')


# ─────────────────────────────────────────────
# Signup
# ─────────────────────────────────────────────

@ratelimit(key='ip', rate='3/m', block=True, method=['POST'])
@ratelimit(key='post:email', rate='3/m', block=True, method=['POST'])
def signup_view(request):
    if request.method == "POST":
        name             = request.POST.get("name", "").strip()
        email            = request.POST.get("email", "").strip().lower()
        password         = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        consent          = request.POST.get("consent") == "true"

        try:
            validate_email(email)
        except ValidationError:
            time_module.sleep(1)
            return JsonResponse({"error": "Invalid email format."}, status=400)

        if not name or not email or not password or not confirm_password:
            time_module.sleep(1)
            return JsonResponse({"error": "All required fields must be provided."}, status=400)

        if password != confirm_password:
            time_module.sleep(1)
            return JsonResponse({"error": "Passwords do not match."}, status=400)

        if User.objects.filter(email=email).exists():
            time_module.sleep(1)
            return JsonResponse({"message": "If valid, your account will be created."})

        PENDING_CAP = 20
        if CustomUser.objects.filter(approval_status='pending').count() >= PENDING_CAP:
            time_module.sleep(1)
            return JsonResponse({"message": "If valid, your account will be created."})

        try:
            validate_password(password)
        except ValidationError as e:
            time_module.sleep(1)
            return JsonResponse({"error": list(e.messages)}, status=400)

        username = f"{email.split('@')[0]}_{uuid.uuid4().hex[:6]}"
        user = User.objects.create_user(
            username=username, email=email, password=password,
            user_type="student", consent_to_share=consent,
        )

        parts     = name.split()
        raw_first = parts[0] if parts else ''
        raw_last  = ' '.join(parts[1:]) if len(parts) > 1 else ''
        user.first_name = re.sub(r"[^a-zA-Z\s\-\']", '', raw_first).strip()[:100]
        user.last_name  = re.sub(r"[^a-zA-Z\s\-\']", '', raw_last).strip()[:100]
        user.save()

        for admin_user in CustomUser.objects.filter(user_type='admin'):
            StudentNotification.objects.create(
                user=admin_user,
                message=f'{user.get_full_name()} ({user.email}) has registered and is awaiting approval.',
            )

        log_action(request, 'user_registered', target=user,
                   summary=f'{user.get_full_name()} registered as {user.user_type}')

        return JsonResponse({"success": True, "message": "Account created. Awaiting admin approval."})

    return render(request, "Pages/User_Auth/signup.html")


# ─────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────

@ratelimit(key='ip', rate='5/m', block=True, method=['POST'])
@ratelimit(key='post:email', rate='5/m', block=True, method=['POST'])
def login_view(request):
    if request.method == "POST":
        email    = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            if user.approval_status.lower() != "approved":
                time_module.sleep(1)
                log_action(request, 'login_pending', target=user,
                           summary=f'{user.get_full_name()} attempted login (pending approval)')
                return JsonResponse({
                    "error": "Your account is pending approval. Please wait for admin confirmation."
                }, status=403)

            from django.utils import timezone

            if user.temp_password_expires_at and user.temp_password_expires_at < timezone.now():
                time_module.sleep(1)
                log_action(request, 'login_failed',
                           summary=f'{user.get_full_name()} temp password expired')
                return JsonResponse({
                    "error": "Your temporary password has expired. Please contact an administrator."
                }, status=403)

            if user.force_password_change:
                login(request, user)
                return JsonResponse({"redirect": "/set-password/"})

            from django_otp.plugins.otp_totp.models import TOTPDevice
            confirmed_devices = TOTPDevice.objects.filter(user=user, confirmed=True)

            if confirmed_devices.exists():
                request.session['pre_2fa_user_id'] = user.id
                request.session['pre_2fa_email']   = email
                return JsonResponse({"redirect": "/login/2fa/"})

            login(request, user)
            log_action(request, 'user_login', target=user,
                       summary=f'{user.get_full_name()} logged in')
            return JsonResponse({"redirect": "/setup/2fa/"})

        time_module.sleep(1)
        log_action(request, 'login_failed',
                   summary=f'Failed login attempt for {email}')
        return JsonResponse({"error": "Invalid email or password."}, status=401)

    return render(request, "Pages/User_Auth/login.html")


# ─────────────────────────────────────────────
# 2FA Verification
# ─────────────────────────────────────────────

def handler_403(request, exception=None):
    from django_ratelimit.exceptions import Ratelimited
    if isinstance(exception, Ratelimited):
        return render(request, 'Pages/User_Auth/ratelimited.html', status=429)
    return render(request, 'Pages/errors/403.html', status=403)


@ratelimit(key='ip', rate='10/m', block=True, method=['POST'])
def login_2fa_view(request):
    user_id = request.session.get('pre_2fa_user_id')
    if not user_id:
        return redirect('login')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('login')

    # ── 2FA attempt limit ─────────────────────────────────────
    attempts = request.session.get('2fa_attempts', 0)
    if attempts >= 5:
        request.session.flush()
        log_action(request, 'login_failed',
                   summary=f'{user.get_full_name()} exceeded 2FA attempts and session cleared')
        return redirect('login')

    error = None

    if request.method == 'POST':
        token = request.POST.get('token', '').strip().replace(' ', '')

        from django_otp import devices_for_user
        from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

        verified = False

        for device in devices_for_user(user):
            if not getattr(device, 'confirmed', True):
                continue
            if device.verify_token(token):
                verified = True
                break

        if not verified:
            static_device = StaticDevice.objects.filter(user=user, name='backup').first()
            if static_device:
                static_token = StaticToken.objects.filter(
                    device=static_device, token=token
                ).first()
                if static_token:
                    static_token.delete()
                    verified = True

        if verified:
            request.session.pop('pre_2fa_user_id', None)
            request.session.pop('pre_2fa_email', None)
            request.session.pop('2fa_attempts', None)
            login(request, user)
            log_action(request, 'user_login', target=user,
                       summary=f'{user.get_full_name()} logged in with 2FA')
            return redirect('dashboard')
        else:
            request.session['2fa_attempts'] = attempts + 1
            log_action(request, 'login_failed',
                       summary=f'{user.get_full_name()} failed 2FA attempt ({attempts + 1}/5)')
            error = f'Invalid code. Please try again. ({attempts + 1}/5 attempts)'

    return render(request, 'Pages/User_Auth/login_2fa.html', {
        'error': error,
        'email': request.session.get('pre_2fa_email', ''),
    })


# ─────────────────────────────────────────────
# 2FA Setup
# ─────────────────────────────────────────────

@login_required
def setup_2fa_view(request):
    from django_otp.plugins.otp_totp.models import TOTPDevice
    from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
    from django.utils import timezone
    import qrcode

    TOTP_SETUP_EXPIRY_MINUTES = 10

    existing_confirmed = TOTPDevice.objects.filter(
        user=request.user, confirmed=True
    ).first()
    if existing_confirmed:
        return redirect('dashboard')

    device, created = TOTPDevice.objects.get_or_create(
        user=request.user, name='default', defaults={'confirmed': False}
    )

    TOTPDevice.objects.filter(user=request.user).exclude(id=device.id).delete()

    if created:
        request.user.totp_setup_started_at = timezone.now()
        request.user.save(update_fields=['totp_setup_started_at'])

    if not device.confirmed and request.user.totp_setup_started_at:
        elapsed = timezone.now() - request.user.totp_setup_started_at
        if elapsed.total_seconds() > TOTP_SETUP_EXPIRY_MINUTES * 60:
            device.delete()
            request.user.totp_setup_started_at = None
            request.user.save(update_fields=['totp_setup_started_at'])
            return render(request, 'Pages/User_Auth/setup_2fa.html', {
                'qr_b64': None, 'device': None,
                'error': 'Your QR code expired after 10 minutes. Refresh the page to generate a new one.',
                'success': None, 'backup_codes': [], 'show_backup_codes': False, 'expired': True,
            })

    error = success = qr_b64 = None
    backup_codes      = []
    show_backup_codes = False

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'verify':
            token = request.POST.get('token', '').strip()
            if device.verify_token(token):
                device.confirmed = True
                device.save()

                request.user.totp_setup_started_at = None
                request.user.save(update_fields=['totp_setup_started_at'])

                success = '2FA enabled successfully.'
                log_action(request, 'other', target=request.user,
                           summary=f'{request.user.get_full_name()} enabled 2FA')

                static_device, _ = StaticDevice.objects.get_or_create(
                    user=request.user, name='backup'
                )
                backup_codes      = list(static_device.token_set.values_list('token', flat=True))
                show_backup_codes = True

                return render(request, 'Pages/User_Auth/setup_2fa.html', {
                    'qr_b64': None, 'device': device, 'error': None,
                    'success': success, 'backup_codes': backup_codes,
                    'show_backup_codes': show_backup_codes, 'expired': False,
                })
            else:
                error = 'Invalid code — please scan the QR code again and try.'
                log_action(request, 'login_failed', target=request.user,
                           summary=f'{request.user.get_full_name()} failed 2FA setup attempt')

    if not device.confirmed:
        img = qrcode.make(device.config_url)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

        static_device, _ = StaticDevice.objects.get_or_create(
            user=request.user, name='backup'
        )
        if static_device.token_set.count() < 8:
            static_device.token_set.all().delete()
            for _ in range(8):
                StaticToken.objects.create(
                    device=static_device, token=secrets.token_hex(4)
                )

    return render(request, 'Pages/User_Auth/setup_2fa.html', {
        'qr_b64': qr_b64, 'device': device, 'error': error,
        'success': success, 'backup_codes': backup_codes,
        'show_backup_codes': show_backup_codes, 'expired': False,
    })


@login_required
@require_http_methods(["POST"])
def api_reset_user_2fa(request, user_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)

    from django_otp.plugins.otp_totp.models import TOTPDevice
    from django_otp.plugins.otp_static.models import StaticDevice

    try:
        target_user = CustomUser.objects.get(id=user_id)
        TOTPDevice.objects.filter(user=target_user).delete()
        StaticDevice.objects.filter(user=target_user).delete()

        StudentNotification.objects.create(
            user=target_user,
            message='Your 2FA has been reset by an administrator. You will be asked to set it up again on next login.'
        )

        log_action(request, 'other', target=target_user,
                   summary=f'{request.user.get_full_name()} reset 2FA for {target_user.get_full_name()}')

        return JsonResponse({'success': True})
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)


# ─────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────

def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("login")


# ─────────────────────────────────────────────
# Force Password Change
# ─────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def set_password(request):
    if not getattr(request.user, 'force_password_change', False):
        return redirect('dashboard')

    if request.method == 'GET':
        return render(request, 'Pages/User_Auth/set_password.html')

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)

    temp_pw = data.get('temp_password', '').strip()
    new_pw  = data.get('new_password', '').strip()
    conf_pw = data.get('confirm_password', '').strip()

    if not temp_pw:
        return JsonResponse({'success': False, 'error': 'Please enter your temporary password.'}, status=400)
    if not request.user.check_password(temp_pw):
        return JsonResponse({'success': False, 'error': 'Temporary password is incorrect.'}, status=400)
    if new_pw != conf_pw:
        return JsonResponse({'success': False, 'error': 'New passwords do not match.'}, status=400)
    if new_pw == temp_pw:
        return JsonResponse({'success': False, 'error': 'New password cannot be the same as your temporary password.'}, status=400)

    try:
        validate_password(new_pw, user=request.user)
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': list(e.messages)}, status=400)

    request.user.set_password(new_pw)
    request.user.force_password_change   = False
    request.user.temp_password_expires_at = None
    request.user.save()
    update_session_auth_hash(request, request.user)

    StudentNotification.objects.create(
        user=request.user,
        message="Your password was changed successfully. If this wasn't you, contact your administrator immediately."
    )

    log_action(request, 'password_changed', target=request.user,
               summary=f'{request.user.get_full_name()} set their password for the first time')

    return JsonResponse({'success': True, 'redirect': '/dashboard/'})


# ─────────────────────────────────────────────
# Change Password
# ─────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def api_change_password(request):
    try:
        data       = json.loads(request.body)
        current_pw = data.get('current_password', '').strip()
        new_pw     = data.get('new_password', '').strip()
        conf_pw    = data.get('confirm_password', '').strip()

        if not request.user.check_password(current_pw):
            return JsonResponse({'success': False, 'error': 'Current password is incorrect.'}, status=400)
        if new_pw != conf_pw:
            return JsonResponse({'success': False, 'error': 'New passwords do not match.'}, status=400)
        if new_pw == current_pw:
            return JsonResponse({'success': False, 'error': 'New password cannot be the same as your current password.'}, status=400)

        try:
            validate_password(new_pw, user=request.user)
        except ValidationError as e:
            return JsonResponse({'success': False, 'error': list(e.messages)}, status=400)

        request.user.set_password(new_pw)
        request.user.save()

        StudentNotification.objects.create(
            user=request.user,
            message="Your password was changed. If this wasn't you, contact your administrator immediately."
        )

        update_session_auth_hash(request, request.user)
        log_action(request, 'password_changed', target=request.user,
                   summary=f'{request.user.get_full_name()} changed their password')

        return JsonResponse({'success': True})

    except Exception:
        return JsonResponse({'success': False, 'error': 'Internal server error.'}, status=500)


# ─────────────────────────────────────────────
# Admin Create User
# ─────────────────────────────────────────────

@login_required
@admin_required
@require_http_methods(["POST"])
def api_create_user_with_temp_password(request):
    try:
        data       = json.loads(request.body)
        first_name = data.get('first_name', '').strip()
        last_name  = data.get('last_name', '').strip()
        email      = data.get('email', '').strip().lower()
        user_type  = data.get('user_type', '').strip()

        if not all([first_name, last_name, email, user_type]):
            return JsonResponse({'success': False, 'error': 'All fields are required.'}, status=400)

        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'success': False, 'error': 'Invalid email format.'}, status=400)

        if user_type not in ('researcher', 'student'):
            return JsonResponse({'success': False, 'error': 'Invalid user type.'}, status=400)

        if CustomUser.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'A user with this email already exists.'}, status=400)

        from django.utils import timezone
        from datetime import timedelta

        temp_password = generate_temp_password()
        username = f"{first_name.lower()}.{last_name.lower()}.{uuid.uuid4().hex[:6]}".replace(' ', '')

        user = CustomUser.objects.create_user(
            username=username, email=email,
            first_name=first_name, last_name=last_name,
            password=temp_password, user_type=user_type,
            approval_status='approved', force_password_change=True,
        )

        user.temp_password_expires_at = timezone.now() + timedelta(hours=24)
        user.save()

        if user_type == 'researcher':
            ResearcherProfile.objects.get_or_create(user=user, defaults={'research_interests': ''})
        elif user_type == 'student':
            StudentProfile.objects.get_or_create(user=user)

        log_action(request, 'user_created_by_admin', target=user,
                   summary=f'{request.user.get_full_name()} created account for {user.get_full_name()} ({email})')

        return JsonResponse({
            'success': True,
            'message': f'Account created for {first_name} {last_name}.',
            'temp_password': temp_password,
            'email': email,
        })

    except Exception:
        return JsonResponse({'success': False, 'error': 'Internal server error.'}, status=500)