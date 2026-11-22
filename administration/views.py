from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Sum
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
import secrets
import string

from core.models import Member, MemberInvitation, Organization, OrganizationMembership
from finance.models import Cycle, LedgerEntry, WalletWithdrawal
from .models import AdministrativeAuditLog, ApprovalRequest, PlatformAnnouncement


def super_admin_required(view):
    @login_required
    def guarded(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise Http404
        return view(request, *args, **kwargs)
    return guarded


def audit(request, action, organization=None, target_type="", target_id="", before=None, after=None, reason=""):
    return AdministrativeAuditLog.objects.create(
        actor=request.user,
        organization=organization,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before=before or {},
        after=after or {},
        reason=reason,
        ip_address=request.META.get("REMOTE_ADDR"),
    )


@super_admin_required
def platform_dashboard(request):
    organizations = Organization.objects.all()
    context = {
        "organizations": organizations.order_by("-created_at")[:8],
        "total_organizations": organizations.count(),
        "active_organizations": organizations.filter(status=Organization.Status.ACTIVE).count(),
        "pending_organizations": organizations.filter(status__in=[Organization.Status.PENDING, Organization.Status.UNDER_REVIEW]).count(),
        "suspended_organizations": organizations.filter(status=Organization.Status.SUSPENDED).count(),
        "total_users": User.objects.count(),
        "active_members": Member.objects.filter(status=Member.Status.ACTIVE).count(),
        "total_cycles": Cycle.objects.count(),
        "active_cycles": Cycle.objects.filter(status=Cycle.Status.ACTIVE).count(),
        "completed_cycles": Cycle.objects.filter(status=Cycle.Status.COMPLETED).count(),
        "confirmed_contributions": LedgerEntry.objects.filter(status=LedgerEntry.Status.POSTED).count(),
        "payouts": WalletWithdrawal.objects.filter(status=WalletWithdrawal.Status.SETTLED).count(),
        "pending_withdrawals": WalletWithdrawal.objects.filter(status=WalletWithdrawal.Status.PENDING).count(),
        "open_support": 0,
        "audit_logs": AdministrativeAuditLog.objects.select_related("actor", "organization")[:12],
        "announcements": PlatformAnnouncement.objects.filter(is_active=True).order_by("-created_at")[:5],
    }
    return render(request, "administration/platform_dashboard.html", context)


@super_admin_required
def organization_detail(request, organization_id):
    organization = get_object_or_404(Organization, pk=organization_id)
    members = Member.objects.filter(organization=organization)
    cycles = Cycle.objects.filter(organization=organization)
    context = {
        "organization": organization,
        "members": members.select_related("user").order_by("-created_at")[:20],
        "cycles": cycles.order_by("-pk")[:20],
        "member_count": members.count(),
        "active_members": members.filter(status=Member.Status.ACTIVE).count(),
        "administrators": OrganizationMembership.objects.filter(
            organization=organization, role__in=["admin", "chairperson", "treasurer"]
        ).select_related("user"),
        "audit_logs": AdministrativeAuditLog.objects.filter(organization=organization)[:20],
    }
    return render(request, "administration/organization_detail.html", context)


@super_admin_required
@require_POST
@transaction.atomic
def organization_status(request, organization_id, action):
    organization = Organization.objects.select_for_update().get(pk=organization_id)
    before = {"status": organization.status, "is_active": organization.is_active}
    reason = request.POST.get("reason", "").strip()
    if action == "approve":
        organization.status = Organization.Status.ACTIVE
        organization.is_active = True
    elif action == "suspend":
        organization.status = Organization.Status.SUSPENDED
        organization.is_active = False
    elif action == "reactivate":
        organization.status = Organization.Status.ACTIVE
        organization.is_active = True
    elif action == "reject":
        organization.status = Organization.Status.REJECTED
        organization.is_active = False
    else:
        raise Http404
    organization.save(update_fields=["status", "is_active"])
    audit(request, f"organization_{action}", organization, "organization", str(organization.pk), before, {"status": organization.status, "is_active": organization.is_active}, reason)
    return redirect("platform-organization-detail", organization_id=organization.pk)


@super_admin_required
@require_POST
def platform_announcement(request):
    title = request.POST.get("title", "").strip()
    message = request.POST.get("message", "").strip()
    if title and message:
        announcement = PlatformAnnouncement.objects.create(title=title, message=message, created_by=request.user)
        audit(request, "platform_announcement_created", target_type="platform_announcement", target_id=str(announcement.pk), after={"title": title})
    return redirect("platform-dashboard")


def organization_admin_membership_required(request, organization_id):
    membership = get_object_or_404(
        OrganizationMembership,
        organization_id=organization_id,
        user=request.user,
        is_active=True,
    )
    if membership.role != OrganizationMembership.Role.ADMIN:
        raise PermissionDenied("Only organization administrators can manage invitations.")
    return membership


@login_required
@require_POST
@transaction.atomic
def organization_invitation_create(request, organization_id):
    membership = organization_admin_membership_required(request, organization_id)
    organization = membership.organization
    raw_code = request.POST.get("code", "").strip()
    email = request.POST.get("email", "").strip().lower()
    expires_at = request.POST.get("expires_at", "").strip()
    uses_remaining = request.POST.get("uses_remaining", "1").strip()

    if len(raw_code) < 8:
        from django.contrib import messages
        messages.error(request, "Invitation codes must contain at least 8 characters.")
        return redirect("organization-dashboard", organization_id=organization.pk)

    try:
        uses = max(1, int(uses_remaining))
    except ValueError:
        uses = 1

    expires = None
    if expires_at:
        from django.utils.dateparse import parse_datetime
        expires = parse_datetime(expires_at)
        if expires is None:
            from django.contrib import messages
            messages.error(request, "The invitation expiry is invalid.")
            return redirect("organization-dashboard", organization_id=organization.pk)

    alphabet = string.ascii_uppercase + string.digits
    if raw_code.lower() == "generate":
        raw_code = "".join(secrets.choice(alphabet) for _ in range(12))

    invitation = MemberInvitation(
        organization=organization,
        email=email,
        expires_at=expires,
        uses_remaining=uses,
        is_active=True,
    )
    invitation.set_code(raw_code)
    invitation.save()
    audit(
        request,
        "member_invitation_created",
        organization,
        "member_invitation",
        str(invitation.pk),
        after={"email": email, "uses_remaining": uses, "expires_at": expires_at},
    )

    from django.contrib import messages
    messages.success(request, f"Invitation code created: {raw_code}")
    return redirect("organization-dashboard", organization_id=organization.pk)


@login_required
@require_POST
@transaction.atomic
def organization_invitation_deactivate(request, organization_id, invitation_id):
    membership = organization_admin_membership_required(request, organization_id)
    invitation = get_object_or_404(
        MemberInvitation,
        pk=invitation_id,
        organization=membership.organization,
    )
    before = {"is_active": invitation.is_active, "uses_remaining": invitation.uses_remaining}
    invitation.is_active = False
    invitation.save(update_fields=["is_active"])
    audit(
        request,
        "member_invitation_deactivated",
        membership.organization,
        "member_invitation",
        str(invitation.pk),
        before=before,
        after={"is_active": False},
    )
    from django.contrib import messages
    messages.success(request, "Invitation code deactivated.")
    return redirect("organization-dashboard", organization_id=organization.pk)


@login_required
def my_administration_workspace(request):
    if request.user.is_superuser:
        return redirect("platform-dashboard")
    membership = OrganizationMembership.objects.filter(
        user=request.user,
        is_active=True,
        role__in=[
            OrganizationMembership.Role.ADMIN,
            OrganizationMembership.Role.CHAIRPERSON,
            OrganizationMembership.Role.SECRETARY,
            OrganizationMembership.Role.TREASURER,
            OrganizationMembership.Role.CYCLE_MANAGER,
            OrganizationMembership.Role.PAYMENT_OFFICER,
            OrganizationMembership.Role.PAYOUT_OFFICER,
            OrganizationMembership.Role.SUPPORT_OFFICER,
        ],
    ).select_related("organization").order_by("organization__name").first()
    if membership:
        return redirect("organization-dashboard", organization_id=membership.organization_id)
    if hasattr(request.user, "member_profile"):
        return redirect("member-dashboard")
    raise PermissionDenied("This account does not have an administration workspace.")


@login_required
def organization_dashboard(request, organization_id):
    if request.user.is_superuser:
        return redirect("platform-organization-detail", organization_id=organization_id)
    membership = get_object_or_404(
        OrganizationMembership,
        organization_id=organization_id,
        user=request.user,
        is_active=True,
    )
    if membership.role not in {
        OrganizationMembership.Role.ADMIN,
        OrganizationMembership.Role.CHAIRPERSON,
        OrganizationMembership.Role.SECRETARY,
        OrganizationMembership.Role.TREASURER,
        OrganizationMembership.Role.CYCLE_MANAGER,
        OrganizationMembership.Role.PAYMENT_OFFICER,
        OrganizationMembership.Role.PAYOUT_OFFICER,
        OrganizationMembership.Role.SUPPORT_OFFICER,
    }:
        raise PermissionDenied("This account has no assigned organization administration role.")
    organization = membership.organization
    members = Member.objects.filter(organization=organization)
    cycles = Cycle.objects.filter(organization=organization)
    context = {
        "organization": organization,
        "membership": membership,
        "invitations": MemberInvitation.objects.filter(
            organization=organization
        ).order_by("-pk"),
        "member_count": members.count(),
        "active_members": members.filter(status=Member.Status.ACTIVE).count(),
        "pending_members": members.filter(status=Member.Status.PENDING).count(),
        "cycles": cycles.order_by("-pk")[:8],
        "active_cycles": cycles.filter(status=Cycle.Status.ACTIVE).count(),
        "completed_cycles": cycles.filter(status=Cycle.Status.COMPLETED).count(),
        "pending_payouts": WalletWithdrawal.objects.filter(organization=organization, status=WalletWithdrawal.Status.PENDING).count(),
        "pending_approvals": ApprovalRequest.objects.filter(organization=organization, status=ApprovalRequest.Status.PENDING).count(),
        "audit_logs": AdministrativeAuditLog.objects.filter(organization=organization).select_related("actor")[:10],
    }
    return render(request, "administration/organization_dashboard.html", context)
