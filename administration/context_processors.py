from django.contrib.auth import get_user_model


def superadmin_setup(request):
    User = get_user_model()
    return {
        "superadmin_setup_available": not User.objects.filter(is_superuser=True).exists(),
    }
