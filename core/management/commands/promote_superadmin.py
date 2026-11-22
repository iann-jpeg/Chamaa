from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Assign an existing user as the platform super administrator."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        username = options["username"].strip()
        User = get_user_model()
        user = User.objects.filter(username__iexact=username).first()
        if not user:
            raise CommandError(f'No user named "{username}" exists.')
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save(update_fields=["is_superuser", "is_staff", "is_active"])
        self.stdout.write(self.style.SUCCESS(f"{user.username} is now the platform super administrator."))
