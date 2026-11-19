from django.urls import path
from . import views

urlpatterns = [
    path("my-workspace/", views.my_administration_workspace, name="my-administration-workspace"),
    path("platform/", views.platform_dashboard, name="platform-dashboard"),
    path("platform/organizations/<int:organization_id>/", views.organization_detail, name="platform-organization-detail"),
    path("platform/organizations/<int:organization_id>/<str:action>/", views.organization_status, name="platform-organization-status"),
    path("platform/announcements/", views.platform_announcement, name="platform-announcement"),
    path("organization/<int:organization_id>/", views.organization_dashboard, name="organization-dashboard"),
]
