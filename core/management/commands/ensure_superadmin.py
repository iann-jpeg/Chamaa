import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from core.models import Organization


class Command(BaseCommand):
    help = "Create or promote the configured platform super administrator."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

        if username and password:
            User = get_user_model()
            user, created = User.objects.get_or_create(
                username__iexact=username,
                defaults={
                    "username": username,
                    "email": email,
                },
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

        organization, organization_created = Organization.objects.get_or_create(
            slug="smart-moves-community-finance",
            defaults={
                "name": "SMART MOVES COMMUNITY FINANCE",
                "status": "active",
                "is_active": True,
                "allow_public_registration": True,
                "require_admin_approval": True,
                "country": "Kenya",
            },
        )
        if not organization.is_active or organization.status != "active":
            organization.is_active = True
            organization.status = "active"
            organization.save(update_fields=["is_active", "status"])
        action = "created" if organization_created else "verified"
        self.stdout.write(
            self.style.SUCCESS(
                f"Organization SMART MOVES COMMUNITY FINANCE {action}."
            )
        )
