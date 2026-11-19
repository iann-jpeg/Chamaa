from django.contrib import admin
from .models import AdministrativeAuditLog, ApprovalRequest, PlatformAnnouncement, RoleAssignment


@admin.register(AdministrativeAuditLog)
class AdministrativeAuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "organization", "target_type", "target_id", "created_at")
    list_filter = ("organization", "target_type", "created_at")
    search_fields = ("action", "target_id", "reason", "actor__username")
    readonly_fields = [field.name for field in AdministrativeAuditLog._meta.fields]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "is_active", "created_at")
    list_filter = ("organization", "role", "is_active")


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("request_type", "organization", "requester", "status", "created_at", "decided_at")
    list_filter = ("organization", "request_type", "status")


@admin.register(PlatformAnnouncement)
class PlatformAnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "starts_at", "ends_at", "created_by", "created_at")
    list_filter = ("is_active", "created_at")
