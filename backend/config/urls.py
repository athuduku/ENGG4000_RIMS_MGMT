from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

handler403 = 'config.views.handler_403'

urlpatterns = [

    # ─────────────────────────────────────────────
    # Admin
    # ─────────────────────────────────────────────
    path('admin-portal/', admin.site.urls),
    path('admin-portal/logout/', views.logout_view, name='admin_logout'),

    # ─────────────────────────────────────────────
    # Pages
    # ─────────────────────────────────────────────
    path('', views.index_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # ─────────────────────────────────────────────
    # Authentication
    # ─────────────────────────────────────────────
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('login/2fa/', views.login_2fa_view, name='login_2fa'),
    path('setup/2fa/', views.setup_2fa_view, name='setup_2fa'),
    path('logout/', views.logout_view, name='logout'),
    path('set-password/', views.set_password, name='set_password'),

    # Password Reset
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='Pages/User_Auth/reset_confirm.html'
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='Pages/User_Auth/reset_done.html'
        ),
        name='password_reset_complete',
    ),

    # ─────────────────────────────────────────────
    # Profile
    # ─────────────────────────────────────────────
    path('profile/', views.profile_view, name='profile'),
    path('api/profile/update-basic/', views.api_update_basic_info, name='api_update_basic_info'),
    path('api/profile/update-academic/', views.api_update_student_academic_info, name='api_update_student_academic_info'),
    path('api/profile/update-research-interests/', views.api_update_research_interests, name='api_update_research_interests'),
    path('api/profile/update-edi/', views.api_update_edi, name='api_update_edi'),
    path('api/profile/update-consent/', views.api_update_consent, name='api_update_consent'),

    # ─────────────────────────────────────────────
    # Admin User Management
    # ─────────────────────────────────────────────
    path('api/admin/create-user/', views.api_create_user_with_temp_password, name='api_create_user'),
    path('api/admin/reset-2fa/<int:user_id>/', views.api_reset_user_2fa, name='api_reset_user_2fa'),
    path('api/admin/pending-activities/', views.api_pending_activities, name='api_admin_pending_activities'),

    # ─────────────────────────────────────────────
    # Publications
    # ─────────────────────────────────────────────
    path('publications/', views.view_publications, name='view_publications'),
    path('publications/add/', views.add_publication, name='add_publication'),
    path('publications/linked/', views.view_linked_publications, name='view_linked_publications'),
    path('publications/<int:publication_id>/delete/', views.delete_publication, name='delete_publication'),
    path('api/publications/<int:publication_id>/update-status/', views.api_update_publication_status, name='api_update_publication_status'),
    path('export/publications/', views.export_publications_csv, name='export_publications_csv'),

    # ─────────────────────────────────────────────
    # Activities
    # ─────────────────────────────────────────────
    path('activities/', views.view_activities, name='view_activities'),
    path('activities/log/', views.log_activity_page, name='log_activity'),
    path('activities/export/', views.export_activities_csv, name='export_activities_csv'),
    path('api/activities/log/', views.api_log_activity, name='api_log_activity'),
    path('api/activities/<int:activity_id>/', views.api_get_activity, name='api_get_activity'),
    path('api/activities/<int:activity_id>/tag-me/', views.api_tag_me_on_activity, name='api_tag_me_on_activity'),
    path('api/activities/delete/<int:activity_id>/', views.delete_activity, name='delete_activity'),
    path('api/activities/review/<int:activity_id>/', views.api_review_activity, name='api_review_activity'),
    path('api/objectives/', views.api_get_objectives, name='api_get_objectives'),
    path('api/peers/search/', views.api_peer_search, name='api_peer_search'),

    # Conferences
    path('api/conferences/search/', views.api_search_conferences, name='api_search_conferences'),
    path('api/conferences/create/', views.api_create_conference, name='api_create_conference'),

    # ─────────────────────────────────────────────
    # Projects
    # ─────────────────────────────────────────────
    path('projects/', views.view_projects, name='view_projects'),
    path('projects/add/', views.add_project, name='add_project'),
    path('export/projects/', views.export_projects_csv, name='export_projects_csv'),
    path('api/projects/<int:id>/', views.api_get_project, name='api_get_project'),
    path('api/projects/<int:project_id>/update-status/', views.api_update_project_status, name='api_update_project_status'),
    path('api/projects/<int:project_id>/update-funding/', views.api_update_project_funding),
    path('api/projects/<int:project_id>/update-kept-by-unb/', views.api_update_project_kept_by_unb, name='api_update_kept_by_unb'),
    path('api/projects/<int:project_id>/update-ip/', views.update_project_ip, name='api_update_project_ip'),
    path('api/projects/<int:id>/update-next-steps/', views.api_update_project_next_steps, name='api_update_next_steps'),
    path('api/projects/<int:id>/update-conception/', views.api_update_project_conception, name='api_update_project_conception'),
    path('api/projects/delete/<int:project_id>/', views.delete_project, name='delete_project'),
    path('api/project/<int:project_id>/funding/', views.api_project_funding, name='api_project_funding'),

    # Project Members
    path('api/projects/<int:project_id>/add-member/', views.api_add_project_member, name='api_add_project_member'),
    path('api/projects/<int:project_id>/remove-member/<int:member_id>/', views.api_remove_project_member, name='api_remove_project_member'),
    path('api/projects/<int:project_id>/team-members/', views.api_get_team_members, name='api_get_team_members'),
    path('api/projects/<int:project_id>/tag-member/<int:user_id>/', views.api_tag_project_member, name='api_tag_project_member'),
    path('api/projects/<int:project_id>/untag-member/<int:user_id>/', views.api_untag_project_member, name='api_untag_project_member'),
    path('api/projects/<int:project_id>/tagged-members/', views.api_get_tagged_members, name='api_get_tagged_members'),

    # Project ↔ Publication / Activity Linking
    path('api/projects/<int:project_id>/linked/', views.api_get_linked_items, name='api_get_linked_items'),
    path('api/projects/<int:project_id>/search-pubs/', views.api_search_publications, name='api_search_publications'),
    path('api/projects/<int:project_id>/search-acts/', views.api_search_activities, name='api_search_activities'),
    path('api/projects/<int:project_id>/link-pub/<int:pub_id>/', views.api_link_publication, name='api_link_publication'),
    path('api/projects/<int:project_id>/unlink-pub/<int:pub_id>/', views.api_unlink_publication, name='api_unlink_publication'),
    path('api/projects/<int:project_id>/link-act/<int:act_id>/', views.api_link_activity, name='api_link_activity'),
    path('api/projects/<int:project_id>/unlink-act/<int:act_id>/', views.api_unlink_activity, name='api_unlink_activity'),

    # ─────────────────────────────────────────────
    # Supervision
    # ─────────────────────────────────────────────
    path('api/supervisor/request/', views.api_request_supervisor, name='api_request_supervisor'),
    path('api/supervisor/review/<int:request_id>/', views.api_review_supervisor_request, name='api_review_supervisor_request'),
    path('api/supervisor/pending/', views.api_pending_supervisor_requests, name='api_pending_supervisor_requests'),
    path('api/supervisor/my-requests/', views.api_my_supervisor_requests, name='api_my_supervisor_requests'),
    path('api/supervisor/search/', views.api_search_supervisors, name='api_search_supervisors'),
    path('api/co-supervisor/request/', views.api_request_co_supervisor, name='api_request_co_supervisor'),
    path('api/co-supervisor/remove/', views.api_remove_co_supervisor, name='api_remove_co_supervisor'),
    path('api/supervision/<int:record_id>/update/', views.api_update_supervision_record, name='api_update_supervision_record'),

    # ─────────────────────────────────────────────
    # Notifications
    # ─────────────────────────────────────────────
    path('notifications/', views.notifications_view, name='notifications'),
    path('api/notifications/', views.api_get_notifications, name='api_get_notifications'),
    path('api/notifications/unread-count/', views.api_unread_count, name='api_unread_count'),
    path('api/notifications/read/', views.api_mark_notifications_read, name='mark_notif_read'),
    path('api/notifications/clear/', views.api_clear_notifications, name='clear_notif'),
    path('api/notifications/dismiss/<int:notif_id>/', views.api_dismiss_notification, name='dismiss_notif'),

    # ─────────────────────────────────────────────
    # CCV Upload
    # ─────────────────────────────────────────────
    path('bulk-upload/', views.bulk_upload, name='bulk_upload'),
    path('student/upload-ccv/', views.student_upload_ccv, name='student_upload_ccv'),
    path('researcher/upload-ccv/', views.researcher_upload_ccv, name='researcher_upload_ccv'),

    # ─────────────────────────────────────────────
    # Reports
    # ─────────────────────────────────────────────
    path('reports/', views.reports_list, name='reports_list'),
    path('reports/grad-completion/', views.grad_completion_report, name='grad_completion_report'),
    path('reports/enrollment-trends/', views.enrollment_trends_report, name='enrollment_trends_report'),
    path('reports/funding-analysis/', views.funding_analysis_report, name='funding_analysis_report'),
    path('reports/activity_report/', views.activity_report, name='activity_report'),
    path('reports/active-projects/', views.active_projects_report, name='active_projects_report'),
    path('reports/conference-equity/', views.conference_equity_report, name='conference_equity_report'),
    path('reports/conference-equity-summary/', views.conference_equity_summary, name='conference_equity_summary'),
    path('pi-report/', views.pi_report_view, name='pi_report'),

    # Report Exports
    path('api/enrollment/pi/<int:pi_id>/students/', views.api_enrollment_pi_students, name='api_enrollment_pi_students'),
    path('export/conference-equity/', views.export_conference_equity_csv, name='export_conference_equity_csv'),

]