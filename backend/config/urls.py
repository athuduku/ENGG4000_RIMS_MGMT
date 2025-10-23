from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Pages
    path("", views.index_view, name="home"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("form/", views.form_view, name="form"),
    path("view_reports/", views.view_reports, name="view_reports"),

    # Authentication
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Forgot password request
    path("forgot_pass/", views.forgot_password_view, name="forgot_pass"),

    # Secure token-based password reset
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="Pages/User_Auth/reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="Pages/User_Auth/reset_done.html"
        ),
        name="password_reset_complete",
    ),
]
