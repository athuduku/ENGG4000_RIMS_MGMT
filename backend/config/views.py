from django.shortcuts import render

def index_view(request):
    return render(request, "index.html")

def home_view(request):
    return render(request, "home.html")

def form_view(request):
    return render(request, "form.html")

def view_reports(request):
    return render(request, "view_report.html")
