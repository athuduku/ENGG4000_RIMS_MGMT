from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index_view, name="index"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("form/", views.form_view, name="form"),
    path("view_reports/", views.view_reports, name="view_reports"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("forgot_pass/", views.forgot_pass_view, name="forgot_pass"),
]
