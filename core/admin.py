from django.contrib import admin
from django import forms
from .models import Member, MemberInvitation, Organization, OrganizationMembership


class MemberInvitationAdminForm(forms.ModelForm):
    code = forms.CharField(
        required=False,
        min_length=8,
        max_length=64,
        help_text="Enter at least 8 characters. Existing codes remain unchanged unless replaced.",
    )

    class Meta:
        model = MemberInvitation
        fields = ("organization", "code", "email", "expires_at", "uses_remaining", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["code"].required = self.instance.pk is None

    def clean_code(self):
        code = self.cleaned_data.get("code", "").strip()
        if self.instance.pk is None and len(code) < 8:
            raise forms.ValidationError("Invitation codes must contain at least 8 characters.")
        if code and len(code) < 8:
            raise forms.ValidationError("Invitation codes must contain at least 8 characters.")
        return code

    def save(self, commit=True):
        original_code = MemberInvitation.objects.filter(pk=self.instance.pk).values_list("code", flat=True).first() if self.instance.pk else None
        invitation = super().save(commit=False)
        raw_code = self.cleaned_data.get("code", "").strip()
        if raw_code:
            invitation.set_code(raw_code)
        elif original_code:
            invitation.code = original_code
        if commit:
            invitation.save()
            self.save_m2m()
        return invitation


@admin.register(MemberInvitation)
class MemberInvitationAdmin(admin.ModelAdmin):
    form = MemberInvitationAdminForm
    list_display = ("organization", "email", "expires_at", "uses_remaining", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("organization__name", "email")

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
