from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index_view, name="index"),
    path("home/", views.home_view, name="home"),
    path("form/", views.form_view, name="form"),
    path("reports/", views.view_reports, name="view_reports"),
]
