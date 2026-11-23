from django.urls import path
from . import views

urlpatterns = [
    path("setup/", views.superadmin_setup, name="superadmin-setup"),
    path("login/", views.administration_login, name="administration-login"),
    path("my-workspace/", views.my_administration_workspace, name="my-administration-workspace"),
    path("platform/", views.platform_dashboard, name="platform-dashboard"),
    path("platform/organizations/<int:organization_id>/", views.organization_detail, name="platform-organization-detail"),
    path("platform/organizations/<int:organization_id>/<str:action>/", views.organization_status, name="platform-organization-status"),
    path("platform/announcements/", views.platform_announcement, name="platform-announcement"),
    path("platform/organization-admins/assign/", views.platform_assign_organization_admin, name="platform-organization-admin-assign"),
    path("platform/organization-admins/<int:membership_id>/remove/", views.platform_remove_organization_admin, name="platform-organization-admin-remove"),
    path("organization/<int:organization_id>/", views.organization_dashboard, name="organization-dashboard"),
    path("organization/<int:organization_id>/invitations/create/", views.organization_invitation_create, name="organization-invitation-create"),
    path("organization/<int:organization_id>/invitations/<int:invitation_id>/deactivate/", views.organization_invitation_deactivate, name="organization-invitation-deactivate"),
]
