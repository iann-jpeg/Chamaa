from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import Member, Organization, OrganizationMembership
from .models import AdministrativeAuditLog

User = get_user_model()


class AdministrationSecurityTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_superuser("platform-owner", "owner@example.com", "Strong-password-123")
        self.organization_a = Organization.objects.create(name="Chama A", slug="chama-a", status=Organization.Status.ACTIVE)
        self.organization_b = Organization.objects.create(name="Chama B", slug="chama-b", status=Organization.Status.ACTIVE)
        self.admin_a = User.objects.create_user("admin-a", password="Strong-password-123")
        OrganizationMembership.objects.create(
            organization=self.organization_a, user=self.admin_a, role=OrganizationMembership.Role.ADMIN
        )

    def test_super_admin_platform_dashboard(self):
        self.client.force_login(self.super_admin)
        response = self.client.get("/administration/platform/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Platform overview")

    def test_organization_admin_cannot_access_other_organization(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(f"/administration/organization/{self.organization_b.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_organization_admin_can_only_view_assigned_organization(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(f"/administration/organization/{self.organization_a.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chama A")

    def test_audit_logs_are_immutable(self):
        log = AdministrativeAuditLog.objects.create(actor=self.admin_a, action="member_approved")
        with self.assertRaises(PermissionError):
            log.save()
        with self.assertRaises(PermissionError):
            log.delete()

    def test_super_admin_using_organization_url_is_redirected_to_detail(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(f"/administration/organization/{self.organization_a.pk}/")
        self.assertRedirects(
            response,
            f"/administration/platform/organizations/{self.organization_a.pk}/",
            fetch_redirect_response=False,
        )

    def test_super_admin_login_redirects_to_platform(self):
        response = self.client.post("/account/login/", {
            "username": "platform-owner",
            "password": "Strong-password-123",
        })
        self.assertRedirects(
            response,
            "/administration/platform/",
            fetch_redirect_response=False,
        )

    def test_organization_admin_login_redirects_to_assigned_organization(self):
        response = self.client.post("/account/login/", {
            "username": "admin-a",
            "password": "Strong-password-123",
        })
        self.assertRedirects(
            response,
            f"/administration/organization/{self.organization_a.pk}/",
            fetch_redirect_response=False,
        )
