from django.contrib.auth.models import User
from django.test import TestCase
from django.conf import settings
from pathlib import Path
from .models import Member, Organization, SupportTicket


class MemberAccountTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Smart Moves", slug="smcf", require_admin_approval=True
        )

    def test_registration_creates_member_identity_and_membership(self):
        response = self.client.post("/account/register/", {
            "first_name": "Amina",
            "middle_name": "",
            "last_name": "Otieno",
            "username": "amina",
            "email": "amina@example.com",
            "phone": "+254700000001",
            "password": "Strong-password-123",
            "confirm_password": "Strong-password-123",
            "organization": self.organization.pk,
            "terms_accepted": "on",
            "privacy_accepted": "on",
        })
        self.assertRedirects(response, "/account/login/")
        member = Member.objects.get(user__username="amina")
        self.assertTrue(member.membership_number.startswith("SMCF-"))
        self.assertEqual(member.user.email, "amina@example.com")
        self.assertTrue(member.user.organizationmembership_set.exists())

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(username="amina", email="old@example.com", password="safe-password")
        response = self.client.post("/account/register/", {
            "first_name": "Amina", "last_name": "Otieno", "username": "amina",
            "email": "new@example.com", "phone": "+254700000002",
            "password": "Strong-password-123", "confirm_password": "Strong-password-123",
            "organization": self.organization.pk, "terms_accepted": "on", "privacy_accepted": "on",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already in use")

    def test_member_can_login_by_email_and_submit_support_ticket(self):
        user = User.objects.create_user(
            username="amina", email="amina@example.com", password="Strong-password-123",
            first_name="Amina",
        )
        member = Member.objects.create(
            organization=self.organization, user=user, membership_number="SMCF-000001",
            status=Member.Status.PENDING,
        )
        login_response = self.client.post("/account/login/", {
            "username": "amina@example.com", "password": "Strong-password-123",
        })
        self.assertEqual(login_response.status_code, 200)
        member.status = Member.Status.ACTIVE
        member.save(update_fields=["status"])
        self.client.post("/account/login/", {
            "username": "amina@example.com", "password": "Strong-password-123",
        })
        response = self.client.post("/account/support/", {
            "subject": "Missing receipt", "description": "Please review my payment receipt."
        })
        self.assertRedirects(response, "/account/dashboard/")
        self.assertTrue(SupportTicket.objects.filter(member=member).exists())


class LandingPageTests(TestCase):
    def test_landing_page_and_auth_links(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your Chama. Your Cycle.")
        self.assertContains(response, 'href="/account/register/"')
        self.assertContains(response, 'href="/account/login/"')
        self.assertContains(response, "Questions, Answered.")
        self.assertContains(response, "Super Admin")
        self.assertContains(response, "Organization Admin")

    def test_static_assets_are_resolvable(self):
        css = Path(settings.BASE_DIR) / "static" / "css" / "landing.css"
        script = Path(settings.BASE_DIR) / "static" / "js" / "landing.js"
        favicon = Path(settings.BASE_DIR) / "static" / "favicon.svg"
        self.assertTrue(css.is_file())
        self.assertTrue(script.is_file())
        self.assertTrue(favicon.is_file())
