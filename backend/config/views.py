from django.shortcuts import render

def dashboard_view(request):
    return render(request, "dashboard.html")

def index_view(request):
    return render(request, "index.html")

def form_view(request):
    return render(request, "form.html")

def view_reports(request):
    return render(request, "view_report.html")
