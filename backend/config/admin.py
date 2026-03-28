"""
RIMS — Comprehensive Django Admin
Replaces admin.py entirely.

Key design decisions:
- CustomUser approval + profile auto-creation in one action
- StudentProfile inline shows supervisor requests
- ResearcherProfile inline shows students
- All bulk actions clearly labeled
- Audit log is read-only and filterable
- SupervisorRequest has approve/reject actions
- Password reset directly on user change page
"""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.db.models import Sum, Max, Count
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, redirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect

from .models import (
    CustomUser,
    ResearcherProfile, Education, Recognition, Funding,
    Publication, Activity, Report, Project, ProjectMember,
    StudentProfile, SupervisorRequest, StudentNotification, AuditLog,
)


admin.site.site_url = '/dashboard/'

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def ensure_profile_exists(user):
    """Create the appropriate profile if it doesn't exist yet."""
    if user.user_type == 'student':
        StudentProfile.objects.get_or_create(user=user)
    elif user.user_type == 'researcher':
        ResearcherProfile.objects.get_or_create(user=user)


# ─────────────────────────────────────────────────────────────
# Custom Admin Site — clean title and nav
# ─────────────────────────────────────────────────────────────

from django.contrib.auth import logout
from django.shortcuts import redirect

class RIMSAdminSite(admin.AdminSite):
    site_header  = 'RIMS Administration'
    site_title   = 'RIMS Admin'
    index_title  = 'Research Information Management System'
    site_url     = '/dashboard/'

    def logout(self, request, extra_context=None):
        logout(request)
        return redirect('/')


# ─────────────────────────────────────────────────────────────
# CustomUser Admin
# — approval + type change + password reset on one screen
# ─────────────────────────────────────────────────────────────

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # ── List view ────────────────────────────────────────────
    list_display  = (
        'email', 'get_full_name_display', 'user_type',
        'approval_status_badge', 'organization',
        'profile_status', 'date_joined',
    )
    list_filter   = ('user_type', 'approval_status', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'organization')
    ordering      = ('-date_joined',)
    list_per_page = 30

    # Editable directly from list — most common admin tasks
    list_editable = ('user_type',)

    # ── Detail view ──────────────────────────────────────────
    fieldsets = (
        ('Account', {
            'fields': ('username', 'email', 'first_name', 'last_name', 'password')
        }),
        ('RIMS Role', {
            'fields': ('user_type', 'approval_status', 'organization', 'consent_to_share'),
            'description': (
                'Changing <b>User Type</b> and then saving will automatically '
                'create the matching profile (StudentProfile / ResearcherProfile) '
                'if one does not already exist.'
            ),
        }),
        ('Permissions', {
            'classes': ('collapse',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Dates', {
            'classes': ('collapse',),
            'fields': ('last_login', 'date_joined'),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name',
                       'user_type', 'approval_status', 'organization',
                       'password1', 'password2'),
        }),
    )

    # Django's built-in password change form — shows "Change Password" link
    change_password_form = AdminPasswordChangeForm

    # ── Bulk actions ─────────────────────────────────────────
    actions = [
        'approve_and_create_profiles',
        'reject_users',
        'make_researcher',
        'make_student',
        'reset_to_temp_password',
        'fix_missing_profiles',
    ]

    @admin.action(description='✓ Approve selected users (auto-creates profiles)')
    def approve_and_create_profiles(self, request, queryset):
        count = 0
        created_profiles = 0
        for user in queryset:
            user.approval_status = 'approved'
            user.save()
            before = (
                StudentProfile.objects.filter(user=user).exists()
                or ResearcherProfile.objects.filter(user=user).exists()
            )
            ensure_profile_exists(user)
            after = (
                StudentProfile.objects.filter(user=user).exists()
                or ResearcherProfile.objects.filter(user=user).exists()
            )
            if not before and after:
                created_profiles += 1
            count += 1
        self.message_user(
            request,
            f'{count} user(s) approved. {created_profiles} profile(s) auto-created.',
            messages.SUCCESS,
        )

    @admin.action(description='✗ Reject selected users')
    def reject_users(self, request, queryset):
        updated = queryset.update(approval_status='rejected')
        self.message_user(request, f'{updated} user(s) rejected.', messages.WARNING)

    @admin.action(description='→ Set type: Researcher')
    def make_researcher(self, request, queryset):
        for user in queryset:
            user.user_type = 'researcher'
            user.save()
            ensure_profile_exists(user)
        self.message_user(request, f'{queryset.count()} user(s) set to Researcher.', messages.SUCCESS)

    @admin.action(description='→ Set type: Student')
    def make_student(self, request, queryset):
        for user in queryset:
            user.user_type = 'student'
            user.save()
            ensure_profile_exists(user)
        self.message_user(request, f'{queryset.count()} user(s) set to Student.', messages.SUCCESS)

    @admin.action(description='🔑 Reset password to temporary password')
    def reset_to_temp_password(self, request, queryset):
        import secrets
        for user in queryset:
            temp = secrets.token_urlsafe(10)
            user.set_password(temp)
            user.save()
            self.message_user(request, f'{user.email} → {temp}', messages.WARNING)
        self.message_user(
            request,
            f"{queryset.count()} password(s) reset. Temporary passwords shown above. Please notify affected users to change it on next login.",
            messages.WARNING,
        )

    @admin.action(description='⚡ Fix missing profiles for approved users')
    def fix_missing_profiles(self, request, queryset):
        fixed = 0
        for user in queryset.filter(approval_status='approved'):
            had_profile = (
                StudentProfile.objects.filter(user=user).exists()
                or ResearcherProfile.objects.filter(user=user).exists()
            )
            ensure_profile_exists(user)
            has_profile_now = (
                StudentProfile.objects.filter(user=user).exists()
                or ResearcherProfile.objects.filter(user=user).exists()
            )
            if not had_profile and has_profile_now:
                fixed += 1
        self.message_user(
            request,
            f'{fixed} missing profile(s) created. '
            f'{queryset.count() - fixed} already had profiles.',
            messages.SUCCESS,
        )

    # ── Auto-create profile on save ──────────────────────────
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.approval_status == 'approved':
            ensure_profile_exists(obj)

    # ── Display helpers ──────────────────────────────────────
    def get_full_name_display(self, obj):
        return obj.get_full_name() or '—'
    get_full_name_display.short_description = 'Name'

    def approval_status_badge(self, obj):
        colors = {
            'approved': ('#166534', '#dcfce7'),
            'pending':  ('#854d0e', '#fef9c3'),
            'rejected': ('#991b1b', '#fee2e2'),
        }
        color, bg = colors.get(obj.approval_status, ('#64748b', '#f1f5f9'))
        return format_html(
            '<span style="padding:2px 10px;border-radius:4px;font-size:11px;'
            'font-weight:700;background:{};color:{}">{}</span>',
            bg, color, obj.approval_status.capitalize()
        )
    approval_status_badge.short_description = 'Status'

    def profile_status(self, obj):
        if obj.user_type == 'student':
            exists = StudentProfile.objects.filter(user=obj).exists()
        elif obj.user_type == 'researcher':
            exists = ResearcherProfile.objects.filter(user=obj).exists()
        else:
            return format_html('<span style="color:#94a3b8;font-size:11px">N/A</span>')

        if exists:
            return format_html(
                '<span style="color:#166534;font-size:11px;font-weight:600">✓ Profile exists</span>'
            )
        return format_html(
            '<span style="color:#991b1b;font-size:11px;font-weight:600">⚠ No profile</span>'
        )
    profile_status.short_description = 'Profile'


# ─────────────────────────────────────────────────────────────
# StudentProfile Admin
# — everything about a student in one place
# ─────────────────────────────────────────────────────────────

class SupervisorRequestInline(admin.TabularInline):
    """Shows pending/historical supervisor requests on the student's page."""
    model         = SupervisorRequest
    fk_name       = 'student'
    extra         = 0
    can_delete    = False
    fields        = ('supervisor', 'status', 'created_at')
    readonly_fields = ('supervisor', 'created_at')
    verbose_name  = 'Supervisor Request'
    verbose_name_plural = 'Supervisor Requests'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    # ── List view ────────────────────────────────────────────
    list_display  = (
        'get_name', 'get_email', 'degree_level',
        'department', 'get_supervisor', 'start_date',
        'expected_end_date', 'graduation_date', 'get_status',
    )
    list_filter   = ('degree_level', 'graduation_date')
    search_fields = (
        'user__first_name', 'user__last_name', 'user__email',
        'department', 'thesis_title',
        'supervisor__user__first_name', 'supervisor__user__last_name',
    )
    list_per_page = 30
    list_editable = ('degree_level', 'graduation_date')

    # ── Detail view ──────────────────────────────────────────
    fieldsets = (
        ('Account', {
            'fields': ('user',),
            'description': 'The linked user account for this student.',
        }),
        ('Academic Information', {
            'fields': (
                'supervisor', 'degree_level', 'department',
                'thesis_title', 'start_date', 'expected_end_date', 'graduation_date',
            ),
        }),
        ('EDI Profile', {
            'classes': ('collapse',),
            'fields': (
                'gender', 'residency_status', 'indigenous_identity', 'edi_profile_completed',
            ),
        }),
    )

    inlines = [SupervisorRequestInline]

    # Supervisor dropdown only shows approved researchers
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'supervisor':
            kwargs['queryset'] = (
                ResearcherProfile.objects
                .filter(user__user_type='researcher', user__approval_status='approved')
                .select_related('user')
                .order_by('user__last_name', 'user__first_name')
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # ── Bulk actions ─────────────────────────────────────────
    actions = ['mark_graduated', 'clear_supervisor']

    @admin.action(description='✓ Mark selected students as graduated (sets graduation date to today)')
    def mark_graduated(self, request, queryset):
        from datetime import date
        updated = queryset.filter(graduation_date__isnull=True).update(graduation_date=date.today())
        self.message_user(request, f'{updated} student(s) marked as graduated.', messages.SUCCESS)

    @admin.action(description='✗ Clear supervisor assignment')
    def clear_supervisor(self, request, queryset):
        updated = queryset.update(supervisor=None)
        self.message_user(request, f'{updated} student(s) had their supervisor cleared.', messages.WARNING)

    # ── Display helpers ──────────────────────────────────────
    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_name.short_description = 'Name'
    get_name.admin_order_field = 'user__last_name'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def get_supervisor(self, obj):
        if obj.supervisor:
            return obj.supervisor.user.get_full_name()
        return format_html('<span style="color:#94a3b8">—</span>')
    get_supervisor.short_description = 'Supervisor'

    def get_status(self, obj):
        if obj.graduation_date:
            return format_html(
                '<span style="padding:2px 8px;border-radius:4px;font-size:11px;'
                'font-weight:700;background:#f1f5f9;color:#64748b">Graduated</span>'
            )
        return format_html(
            '<span style="padding:2px 8px;border-radius:4px;font-size:11px;'
            'font-weight:700;background:#dcfce7;color:#166534">Active</span>'
        )
    get_status.short_description = 'Status'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'supervisor__user')


# ─────────────────────────────────────────────────────────────
# ResearcherProfile Admin
# — researcher with all related data inline
# ─────────────────────────────────────────────────────────────

class EducationInline(admin.TabularInline):
    model   = Education
    extra   = 0
    fields  = ('degree_type', 'specialization', 'institution', 'start_date', 'expected_date', 'thesis_title')
    verbose_name_plural = 'Education'

class RecognitionInline(admin.TabularInline):
    model  = Recognition
    extra  = 0
    fields = ('name', 'organization', 'amount', 'start_date', 'description')
    verbose_name_plural = 'Awards & Recognitions'

class PublicationInline(admin.TabularInline):
    model  = Publication
    extra  = 0
    fields = ('title', 'publication_type', 'journal', 'publication_date', 'status', 'doi')
    verbose_name_plural = 'Publications'

class ActivityInline(admin.TabularInline):
    model  = Activity
    extra  = 0
    fields = ('title', 'activity_type', 'category', 'date', 'description')
    verbose_name_plural = 'Activities'

class ProjectInline(admin.TabularInline):
    model           = Project
    extra           = 0
    fields          = ('title', 'role', 'status', 'funding_organization', 'total_funding', 'start_date', 'end_date')
    show_change_link = True
    verbose_name_plural = 'Projects'

class StudentInline(admin.TabularInline):
    """Shows all students supervised by this researcher."""
    model           = StudentProfile
    fk_name         = 'supervisor'
    extra           = 0
    can_delete      = False
    fields          = ('user', 'degree_level', 'department', 'start_date', 'expected_end_date', 'graduation_date')
    readonly_fields = ('user',)
    show_change_link = True
    verbose_name_plural = 'Supervised Students'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ResearcherProfile)
class ResearcherProfileAdmin(admin.ModelAdmin):
    list_display  = (
        'get_name', 'get_email', 'title',
        'ccv_identifier', 'get_student_count', 'get_funding_total',
    )
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name', 'ccv_identifier',
    )
    list_per_page = 30

    fieldsets = (
        ('Account', {'fields': ('user',)}),
        ('Profile', {
            'fields': ('ccv_identifier', 'title', 'sex', 'language', 'residency_status', 'research_interests'),
        }),
    )

    inlines = [
        StudentInline,
        EducationInline,
        RecognitionInline,
        PublicationInline,
        ActivityInline,
        ProjectInline,
    ]

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_name.short_description = 'Name'
    get_name.admin_order_field = 'user__last_name'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def get_student_count(self, obj):
        return obj.student_count or 0
    get_student_count.short_description = 'Students'

    def get_funding_total(self, obj):
        return f'${obj.funding_total or 0:,.0f}'
    get_funding_total.short_description = 'Total Funding'

    def get_queryset(self, request):
            return super().get_queryset(request).filter(
                user__user_type='researcher'
            ).select_related('user').annotate(
                student_count=Count('students'),
                funding_total=Sum('funding__amount')
            )

# ─────────────────────────────────────────────────────────────
# SupervisorRequest Admin
# — approve/reject directly from list or detail
# ─────────────────────────────────────────────────────────────

@admin.register(SupervisorRequest)
class SupervisorRequestAdmin(admin.ModelAdmin):
    list_display  = (
        'get_student', 'get_supervisor', 'status_badge', 'created_at',
    )
    list_filter   = ('status',)
    search_fields = (
        'student__user__first_name', 'student__user__last_name',
        'supervisor__user__first_name', 'supervisor__user__last_name',
    )
    ordering      = ('-created_at',)
    list_per_page = 30
    readonly_fields = ('student', 'supervisor', 'created_at')

    actions = ['approve_requests', 'reject_requests']

    @admin.action(description='✓ Approve selected supervisor requests')
    def approve_requests(self, request, queryset):
        approved = 0
        for req in queryset.filter(status='pending').select_related('student', 'supervisor__user', 'student__user'):
            req.status = 'approved'
            req.save()
            req.student.supervisor = req.supervisor
            req.student.save()
            StudentNotification.objects.create(
                user=req.student.user,
                message=f'{req.supervisor.user.get_full_name()} has been assigned as your supervisor by admin.',
            )
            approved += 1
        self.message_user(request, f'{approved} request(s) approved and supervisors assigned.', messages.SUCCESS)

    @admin.action(description='✗ Reject selected supervisor requests')
    def reject_requests(self, request, queryset):
        rejected = 0
        for req in queryset.filter(status='pending').select_related('student__user', 'supervisor__user'):
            req.status = 'rejected'
            req.save()
            StudentNotification.objects.create(
                user=req.student.user,
                message=f'Your supervisor request to {req.supervisor.user.get_full_name()} was declined by admin.',
            )
            rejected += 1
        self.message_user(request, f'{rejected} request(s) rejected.', messages.WARNING)

    def get_student(self, obj):
        return obj.student.user.get_full_name()
    get_student.short_description = 'Student'
    get_student.admin_order_field = 'student__user__last_name'

    def get_supervisor(self, obj):
        return obj.supervisor.user.get_full_name()
    get_supervisor.short_description = 'Supervisor'

    def status_badge(self, obj):
        colors = {
            'approved': ('#166534', '#dcfce7'),
            'pending':  ('#854d0e', '#fef9c3'),
            'rejected': ('#991b1b', '#fee2e2'),
        }
        color, bg = colors.get(obj.status, ('#64748b', '#f1f5f9'))
        return format_html(
            '<span style="padding:2px 10px;border-radius:4px;font-size:11px;'
            'font-weight:700;background:{};color:{}">{}</span>',
            bg, color, obj.status.capitalize()
        )
    status_badge.short_description = 'Status'


# ─────────────────────────────────────────────────────────────
# Funding Admin
# ─────────────────────────────────────────────────────────────

@admin.register(Funding)
class FundingAdmin(admin.ModelAdmin):
    list_display  = ('title', 'get_researcher', 'organization', 'funding_type', 'get_total', 'get_year_range')
    list_filter   = ('funding_type', 'organization')
    search_fields = ('title', 'organization', 'researcher__user__email')

    def get_researcher(self, obj):
        return obj.researcher.user.get_full_name() or obj.researcher.user.username
    get_researcher.short_description = 'Researcher'

    def get_total(self, obj):
        total = Funding.objects.filter(
            researcher=obj.researcher, title=obj.title
        ).aggregate(t=Sum('amount'))['t'] or 0
        return f'${total:,.0f}'
    get_total.short_description = 'Total Received'

    def get_year_range(self, obj):
        records = Funding.objects.filter(
            researcher=obj.researcher, title=obj.title
        ).order_by('start_date').values_list('start_date', flat=True)
        years = [str(d)[:4] for d in records if d]
        if not years:
            return '—'
        return f'{years[0]} → {years[-1]}' if years[0] != years[-1] else years[0]
    get_year_range.short_description = 'Year Range'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        latest_ids = (
            qs.values('researcher', 'title')
            .annotate(max_id=Max('id'))
            .values_list('max_id', flat=True)
        )
        return qs.filter(id__in=latest_ids)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = get_object_or_404(Funding, pk=object_id)
        return redirect(
            reverse('admin:config_researcherprofile_change', args=[obj.researcher.pk])
        )


# ─────────────────────────────────────────────────────────────
# Publication Admin
# ─────────────────────────────────────────────────────────────

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display  = ('title', 'get_researcher', 'publication_type', 'journal', 'status', 'publication_date')
    list_filter   = ('publication_type', 'status')
    search_fields = ('title', 'authors', 'journal', 'researcher__user__email')
    list_per_page = 30

    def get_researcher(self, obj):
        return obj.researcher.user.get_full_name() or obj.researcher.user.username
    get_researcher.short_description = 'Researcher'


# ─────────────────────────────────────────────────────────────
# Activity Admin
# ─────────────────────────────────────────────────────────────

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display  = ('title', 'get_researcher', 'activity_type', 'category', 'date', 'status_badge')
    list_filter   = ('activity_type', 'category', 'is_active')
    search_fields = ('title', 'researcher__user__email')
    list_per_page = 30

    def get_researcher(self, obj):
        return obj.researcher.user.get_full_name() or obj.researcher.user.username
    get_researcher.short_description = 'Researcher'

    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color:#166534;font-size:11px;font-weight:600">✓ Active</span>'
            )
        return format_html(
            '<span style="color:#991b1b;font-size:11px;font-weight:600">Inactive</span>'
        )
    status_badge.short_description = 'Status'


# ─────────────────────────────────────────────────────────────
# Project Admin
# ─────────────────────────────────────────────────────────────

class ProjectMemberInline(admin.TabularInline):
    model  = ProjectMember
    extra  = 0
    fields = ('name', 'role')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display  = (
        'title', 'get_researcher', 'role', 'status',
        'funding_organization', 'total_funding', 'start_date', 'end_date',
    )
    list_filter   = ('status', 'role')
    search_fields = ('title', 'funding_organization', 'researcher__user__email')
    inlines       = [ProjectMemberInline]
    list_per_page = 30

    def get_researcher(self, obj):
        return obj.researcher.user.get_full_name() or obj.researcher.user.username
    get_researcher.short_description = 'Researcher'


# ─────────────────────────────────────────────────────────────
# Recognition Admin
# ─────────────────────────────────────────────────────────────

@admin.register(Recognition)
class RecognitionAdmin(admin.ModelAdmin):
    list_display  = ('name', 'get_researcher', 'organization', 'amount', 'start_date')
    search_fields = ('name', 'organization', 'researcher__user__email')
    list_filter   = ('organization',)

    def get_researcher(self, obj):
        return obj.researcher.user.get_full_name() or obj.researcher.user.username
    get_researcher.short_description = 'Researcher'



# ─────────────────────────────────────────────────────────────
# Student Notification Admin
# ─────────────────────────────────────────────────────────────

@admin.register(StudentNotification)
class StudentNotificationAdmin(admin.ModelAdmin):
    list_display  = ('get_user', 'message_preview', 'is_read', 'created_at')
    list_filter   = ('is_read',)
    search_fields = ('user__email', 'user__first_name', 'message')
    list_editable = ('is_read',)
    ordering      = ('-created_at',)
    list_per_page = 50

    def get_user(self, obj):
        return obj.user.get_full_name() or obj.user.email
    get_user.short_description = 'User'

    def message_preview(self, obj):
        return obj.message[:80] + '…' if len(obj.message) > 80 else obj.message
    message_preview.short_description = 'Message'


# ─────────────────────────────────────────────────────────────
# Audit Log Admin — fully read-only
# ─────────────────────────────────────────────────────────────

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = (
        'created_at', 'get_user', 'action_badge',
        'summary', 'target_type', 'target_id', 'ip_address',
    )
    list_filter   = ('action',)
    search_fields = ('user__email', 'user__first_name', 'summary', 'action')
    ordering      = ('-created_at',)
    list_per_page = 50
    date_hierarchy = 'created_at'

    readonly_fields = (
        'user', 'action', 'target_type', 'target_id',
        'summary', 'details', 'ip_address', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_user(self, obj):
        return obj.user.get_full_name() if obj.user else 'System'
    get_user.short_description = 'User'

    def action_badge(self, obj):
        action = obj.action or ''
        if 'approved' in action:
            color, bg = '#166534', '#dcfce7'
        elif 'rejected' in action:
            color, bg = '#991b1b', '#fee2e2'
        elif 'uploaded' in action:
            color, bg = '#7c3aed', '#f3e8ff'
        elif 'updated' in action or 'profile' in action:
            color, bg = '#b45309', '#fef3e2'
        elif 'deleted' in action:
            color, bg = '#991b1b', '#fee2e2'
        else:
            color, bg = '#1a56db', '#e8f0fe'
        display = obj.get_action_display() if hasattr(obj, 'get_action_display') else action
        return format_html(
            '<span style="padding:2px 8px;border-radius:4px;font-size:11px;'
            'font-weight:700;background:{};color:{};white-space:nowrap">{}</span>',
            bg, color, display
        )
    action_badge.short_description = 'Action'
