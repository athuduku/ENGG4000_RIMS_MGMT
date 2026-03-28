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
    
    # added random salt to the admin path
    path('admin-83bdc1b7/', admin.site.urls),

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

    path('bulk-upload/', views.bulk_upload, name='bulk_upload'),

    

    path('upload-report/', views.upload_report, name='upload_report'),

    path('api/reports/', views.get_reports, name='get_reports'),
    
    # Add these to your urls.py

    path('reports/', views.reports_list, name='reports_list'),
    path('reports/grad-completion/', views.grad_completion_report, name='grad_completion_report'),
    path('reports/export/<str:report_type>/', views.export_report_csv, name='export_report'),

    path('reports/enrollment-trends/', views.enrollment_trends_report, name='enrollment_trends_report'),

    path('reports/funding-analysis/', views.funding_analysis_report, name='funding_analysis_report'),

    path('reports/top-researchers/', views.top_researchers_report, name='top_researchers_report'),

    path('publications/add/', views.add_publication, name='add_publication'),
path('publications/', views.view_publications, name='view_publications'),
path('publications/<int:publication_id>/delete/', views.delete_publication, name='delete_publication'),
]

