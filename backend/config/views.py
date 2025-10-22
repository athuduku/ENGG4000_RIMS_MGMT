from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache



@login_required(login_url='login')
def dashboard_view(request):
    return render(request, "Pages/dashboard.html", {"user": request.user})

def index_view(request):
    return render(request, "Pages/home.html")

def form_view(request):
    return render(request, "Pages/form.html")

def view_reports(request):
    return render(request, "Pages/view_report.html")

def signup_view(request): 
    return render(request, "User_Auth/signup.html")

def login_view(request): 
    return render(request, "User_Auth/login.html")

def forgot_pass_view(request): 
    return render(request, "Pages/User_Auth/forgot_pass.html")



def logout_view(request):
    logout(request)
    messages.success(request, "You’ve been logged out successfully.")
    return redirect('login')

@never_cache
@login_required(login_url='/login/')
def dashboard_view(request):
    return render(request, 'Pages/dashboard.html')

User = get_user_model()

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
            user_type="student"
        )
        user.save()

        return JsonResponse({"success": "Account created successfully!"})

    return render(request, "Pages/User_Auth/signup.html")


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.approval_status == "approved":
                login(request, user)
                return JsonResponse({'redirect': '/dashboard/'})
            else:
                return JsonResponse({'error': 'Your account is awaiting approval.'}, status=403)
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)

    return render(request, 'Pages/User_Auth/login.html')


