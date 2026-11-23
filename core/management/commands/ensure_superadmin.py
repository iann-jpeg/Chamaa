import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from core.models import Organization, OrganizationMembership
from finance.models import Cycle


class Command(BaseCommand):
    help = "Create or promote the configured platform super administrator."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

        if username and password:
            User = get_user_model()
            user = User.objects.filter(username__iexact=username).first()
            created = user is None
            if user is None:
                user = User(
                    username=username,
                    email=email,
                )
            user.username = username
            user.email = email or user.email
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.set_password(password)
            user.save()

            action = "created" if created else "promoted and updated"
            self.stdout.write(
                self.style.SUCCESS(f"Super admin {username} {action}.")
            )
        else:
            self.stdout.write(
                "Super-admin bootstrap skipped: username or password environment variable is missing."
            )

        organization = Organization.objects.filter(slug="smcf").first()
        if organization is None:
            organization = Organization.objects.filter(
                slug="smart-moves-community-finance"
            ).first()
        if organization is None:
            organization = Organization.objects.filter(
                name="SMART MOVES COMMUNITY FINANCE"
            ).order_by("pk").first()
        organization_created = organization is None
        if organization is None:
            organization = Organization(
                slug="smart-moves-community-finance",
                name="SMART MOVES COMMUNITY FINANCE",
                status="active",
                is_active=True,
                allow_public_registration=True,
                require_admin_approval=True,
                country="Kenya",
            )
            organization.save()
        if not organization.is_active or organization.status != "active":
            organization.is_active = True
            organization.status = "active"
            organization.save(update_fields=["is_active", "status"])
        for duplicate in Organization.objects.filter(
            name="SMART MOVES COMMUNITY FINANCE"
        ).exclude(pk=organization.pk):
            if (
                not duplicate.member_set.exists()
                and not OrganizationMembership.objects.filter(organization=duplicate).exists()
                and not Cycle.objects.filter(organization=duplicate).exists()
            ):
                duplicate.delete()
        action = "created" if organization_created else "verified"
        self.stdout.write(
            self.style.SUCCESS(
                f"Organization SMART MOVES COMMUNITY FINANCE {action}."
            )
        )
