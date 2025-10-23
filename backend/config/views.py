from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib.auth.forms import PasswordResetForm

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

        if User.objects.filter(email=email).exists():
            return JsonResponse({"error": "Email already registered"}, status=400)

        user = User.objects.create_user(
            username=name,          # still needed for AbstractUser
            email=email,
            password=password,
            user_type="student"
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

@never_cache
@login_required(login_url="login")
def dashboard_view(request):
    return render(request, "Pages/dashboard.html", {"user": request.user})

@csrf_exempt
def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email").strip()
        form = PasswordResetForm({"email": email})

        if form.is_valid():
            # ✅ Sends reset email securely with a token
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
