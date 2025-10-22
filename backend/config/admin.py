from django.contrib import admin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'user_type', 'approval_status', 'organization', 'consent_to_share')

    list_filter = ('user_type', 'approval_status')
    search_fields = ('username', 'email', 'organization')
    list_editable = ('user_type', 'organization')

    fields = (
        'username',
        'email',
        'user_type',
        'organization',
        'approval_status',
        'consent_to_share',
        'is_active',
        'is_staff',
        'is_superuser',
    )

    readonly_fields = ('last_login', 'date_joined')

    actions = ['approve_users', 'reject_users']

    @admin.action(description="Approve selected users")
    def approve_users(self, request, queryset):
        updated = queryset.update(approval_status='approved')
        self.message_user(request, f"{updated} user(s) successfully approved.")

    @admin.action(description="Reject selected users")
    def reject_users(self, request, queryset):
        updated = queryset.update(approval_status='rejected')
        self.message_user(request, f"{updated} user(s) rejected.")
