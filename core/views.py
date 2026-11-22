from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
import logging
import os
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import MemberAuthenticationForm, MemberRegistrationForm
from .models import Member, MemberNotification, SupportTicket
from finance.models import Contribution, CycleParticipant

logger = logging.getLogger(__name__)


def ensure_production_accounts():
    from django.contrib.auth import get_user_model
    from .models import Organization

    organization = Organization.objects.filter(
        slug="smart-moves-community-finance"
    ).first()
    if organization is None:
        try:
            organization = Organization.objects.create(
                name="SMART MOVES COMMUNITY FINANCE",
                slug="smart-moves-community-finance",
                status=Organization.Status.ACTIVE,
                is_active=True,
                allow_public_registration=True,
                require_admin_approval=True,
                country="Kenya",
            )
        except IntegrityError:
            organization = Organization.objects.filter(
                slug="smart-moves-community-finance"
            ).first()
    elif not organization.is_active or organization.status != Organization.Status.ACTIVE:
        organization.is_active = True
        organization.status = Organization.Status.ACTIVE
        organization.save(update_fields=["is_active", "status"])

    username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
    if username and password:
        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if user is None:
            user = User(username=username, email=email)
        else:
            user.email = email or user.email
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.set_password(password)
        user.save()


class MemberLoginView(LoginView):
    authentication_form = MemberAuthenticationForm
    template_name = "core/login.html"

    def dispatch(self, request, *args, **kwargs):
        ensure_production_accounts()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser:
            return "/administration/platform/"
        membership = getattr(user, "organizationmembership_set", None)
        if membership is not None:
            organization_admin = membership.filter(
                is_active=True,
                role="admin",
            ).select_related("organization").first()
            if organization_admin:
                return f"/administration/organization/{organization_admin.organization_id}/"
        return super().get_success_url()

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.POST.get("remember") != "on":
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(60 * 60 * 24 * 14)
        return response


def register(request):
    ensure_production_accounts()
    form = MemberRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            member = form.save()
        except Exception as exc:
            logger.exception("Member registration failed")
            if getattr(settings, "DEBUG", False):
                messages.error(request, f"Registration failed: {exc.__class__.__name__}: {exc}")
            else:
                messages.error(request, "Registration could not be completed. Please try again.")
            return render(request, "core/register.html", {"form": form}, status=400)
        messages.success(request, "Registration received. Your application is awaiting approval.")
        return redirect("member-login")
    return render(request, "core/register.html", {"form": form})


@login_required
def dashboard(request):
    member = get_object_or_404(Member, user=request.user)
    participations = CycleParticipant.objects.filter(member=member).select_related("cycle")
    contributions = Contribution.objects.filter(member=member).select_related("product").order_by("-due_date")[:6]
    return render(request, "core/dashboard.html", {
        "member": member,
        "notifications": member.notifications.all()[:5],
        "tickets": member.support_tickets.all()[:5],
        "participations": participations,
        "contributions": contributions,
    })


@login_required
@require_POST
def create_support_ticket(request):
    member = get_object_or_404(Member, user=request.user)
    subject = request.POST.get("subject", "").strip()
    description = request.POST.get("description", "").strip()
    if not subject or not description:
        messages.error(request, "Subject and description are required.")
    else:
        SupportTicket.objects.create(member=member, subject=subject, description=description)
        messages.success(request, "Support ticket submitted.")
    return redirect("member-dashboard")


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        MemberNotification, pk=notification_id, member__user=request.user
    )
    from django.utils import timezone
    notification.read_at = timezone.now()
    notification.save(update_fields=["read_at"])
    return redirect("member-dashboard")
