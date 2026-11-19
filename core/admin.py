from django.contrib import admin
from .models import Member, Organization, OrganizationMembership

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "allow_public_registration", "require_admin_approval")
    list_filter = ("is_active", "allow_public_registration", "require_admin_approval")
    search_fields = ("name", "slug", "registration_number")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "is_active")
    list_filter = ("organization", "role", "is_active")
    search_fields = ("user__username", "user__email", "organization__name")


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("membership_number", "get_full_name", "organization", "phone", "status", "created_at")
    list_filter = ("organization", "status")
    search_fields = ("membership_number", "user__first_name", "user__last_name", "user__email", "phone")
    autocomplete_fields = ("user", "organization")
    readonly_fields = ("membership_number", "created_at")
    actions = ("approve_members", "suspend_members", "reactivate_members")

    @admin.display(description="Full name")
    def get_full_name(self, member):
        return member.user.get_full_name() or member.user.username

    @admin.action(description="Approve selected members")
    def approve_members(self, request, queryset):
        queryset.update(status=Member.Status.ACTIVE)

    @admin.action(description="Suspend selected members")
    def suspend_members(self, request, queryset):
        queryset.update(status=Member.Status.SUSPENDED)

    @admin.action(description="Reactivate selected members")
    def reactivate_members(self, request, queryset):
        queryset.update(status=Member.Status.ACTIVE)
