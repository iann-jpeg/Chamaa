import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or promote the configured platform super administrator."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

        if not username or not password:
            self.stdout.write(
                "Super-admin bootstrap skipped: username or password environment variable is missing."
            )
            return

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
