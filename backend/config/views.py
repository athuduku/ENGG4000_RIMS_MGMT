from django.shortcuts import render

def dashboard_view(request):
    return render(request, "dashboard.html")

def index_view(request):
    return render(request, "index.html")

def form_view(request):
    return render(request, "form.html")

def view_reports(request):
    return render(request, "view_report.html")

def signup_view(request): 
    return render(request, "User_Auth/signup.html")

def login_view(request): 
    return render(request, "User_Auth/login.html")

def forgot_pass_view(request): 
    return render(request, "User_Auth/forgot_pass.html")
