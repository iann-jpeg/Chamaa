from django.contrib.auth.views import LogoutView, PasswordResetDoneView, PasswordResetView
from django.urls import path
from .views import MemberLoginView, create_support_ticket, dashboard, mark_notification_read, register

urlpatterns = [
    path("register/", register, name="member-register"),
    path("login/", MemberLoginView.as_view(), name="member-login"),
    path("logout/", LogoutView.as_view(), name="member-logout"),
    path("password-reset/", PasswordResetView.as_view(template_name="core/password_reset.html"), name="password-reset"),
    path("password-reset/done/", PasswordResetDoneView.as_view(template_name="core/password_reset_done.html"), name="password-reset-done"),
    path("dashboard/", dashboard, name="member-dashboard"),
    path("support/", create_support_ticket, name="support-ticket"),
    path("notifications/<int:notification_id>/read/", mark_notification_read, name="notification-read"),
]
