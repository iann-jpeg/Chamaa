from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
import logging
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import MemberAuthenticationForm, MemberRegistrationForm
from .models import Member, MemberNotification, SupportTicket
from finance.models import Contribution, CycleParticipant

logger = logging.getLogger(__name__)


class MemberLoginView(LoginView):
    authentication_form = MemberAuthenticationForm
    template_name = "core/login.html"

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
    form = MemberRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except Exception:
            logger.exception("Member registration failed")
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
