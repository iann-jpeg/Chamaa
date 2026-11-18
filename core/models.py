from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    registration_number = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Organization administrator"
        MANAGER = "manager", "Group manager"
        TREASURER = "treasurer", "Treasurer"
        MEMBER = "member", "Member"
        AUDITOR = "auditor", "Auditor"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="member_profile")
    membership_number = models.CharField(max_length=32)
    phone = models.CharField(max_length=30, blank=True)
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
