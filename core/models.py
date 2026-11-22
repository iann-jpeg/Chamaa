from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import MinLengthValidator
from django.db import models


class Organization(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        UNDER_REVIEW = "under_review", "Under review"
        APPROVED = "approved", "Approved"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        REJECTED = "rejected", "Rejected"
        DEACTIVATED = "deactivated", "Deactivated"

    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    registration_number = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    official_email = models.EmailField(blank=True)
    official_phone = models.CharField(max_length=30, blank=True)
    physical_address = models.CharField(max_length=240, blank=True)
    county = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, default="Kenya")
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    allow_public_registration = models.BooleanField(default=True)
    require_admin_approval = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Organization administrator"
        MANAGER = "manager", "Group manager"
        CHAIRPERSON = "chairperson", "Chairperson"
        SECRETARY = "secretary", "Secretary"
        TREASURER = "treasurer", "Treasurer"
        CYCLE_MANAGER = "cycle_manager", "Cycle manager"
        PAYMENT_OFFICER = "payment_officer", "Payment verification officer"
        PAYOUT_OFFICER = "payout_officer", "Payout approval officer"
        SUPPORT_OFFICER = "support_officer", "Member support officer"
        MEMBER = "member", "Member"
        AUDITOR = "auditor", "Auditor"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "user"], name="unique_org_user")
        ]


class Member(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Application pending"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        EXITED = "exited", "Exited"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="member_profile")
    membership_number = models.CharField(max_length=32)
    phone = models.CharField(max_length=30, blank=True)
    middle_name = models.CharField(max_length=150, blank=True)
    profile_photo = models.ImageField(upload_to="member-photos/", blank=True)
    residential_location = models.CharField(max_length=180, blank=True)
    emergency_contact = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    joined_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "membership_number"],
                name="unique_membership_number_per_org",
            )
        ]
        ordering = ["membership_number"]

    def __str__(self):
        return f"{self.membership_number} - {self.user.get_full_name() or self.user.username}"


class MemberInvitation(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    code = models.CharField(max_length=128, unique=True, validators=[MinLengthValidator(8)])
    email = models.EmailField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    uses_remaining = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def set_code(self, raw_code):
        raw_code = raw_code.strip()
        if len(raw_code) < 8:
            raise ValueError("Invitation codes must contain at least 8 characters.")
        self.code = make_password(raw_code)

    def matches_code(self, raw_code):
        return bool(raw_code) and check_password(raw_code.strip(), self.code)

    def is_available(self, email=None, now=None):
        from django.utils import timezone
        now = now or timezone.now()
        if not self.is_active or self.uses_remaining < 1:
            return False
        if self.expires_at and self.expires_at <= now:
            return False
        if self.email and email and self.email.lower() != email.strip().lower():
            return False
        if self.email and not email:
            return False
        return True

    def __str__(self):
        return f"{self.organization.name} invitation"


class MemberVerification(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"

    member = models.ForeignKey(Member, related_name="verifications", on_delete=models.CASCADE)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)


class MemberNotificationPreference(models.Model):
    member = models.OneToOneField(Member, related_name="notification_preferences", on_delete=models.CASCADE)
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)
    payment_notifications = models.BooleanField(default=True)
    cycle_notifications = models.BooleanField(default=True)
    security_notifications = models.BooleanField(default=True)


class MemberNotification(models.Model):
    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    member = models.ForeignKey(Member, related_name="notifications", on_delete=models.CASCADE)
    title = models.CharField(max_length=180)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class MemberActivityLog(models.Model):
    member = models.ForeignKey(Member, related_name="activity_logs", on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=120)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MemberDocument(models.Model):
    member = models.ForeignKey(Member, related_name="documents", on_delete=models.PROTECT)
    name = models.CharField(max_length=180)
    file = models.FileField(upload_to="member-documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under review"
        AWAITING_MEMBER = "awaiting_member", "Awaiting member"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    member = models.ForeignKey(Member, related_name="support_tickets", on_delete=models.PROTECT)
    subject = models.CharField(max_length=180)
    category = models.CharField(max_length=60, default="general")
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SupportMessage(models.Model):
    ticket = models.ForeignKey(SupportTicket, related_name="messages", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
