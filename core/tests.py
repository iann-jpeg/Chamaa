from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.conf import settings
from pathlib import Path
from django.utils import timezone
from django.db import DatabaseError
from datetime import timedelta
from .models import Member, MemberInvitation, Organization, SupportTicket
from unittest.mock import patch
from finance.models import Contribution, ContributionProduct, Cycle, CycleParticipant

User = get_user_model()


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

    def test_registration_enrolls_member_in_open_cycle_with_payment_record(self):
        cycle = Cycle.objects.create(
            organization=self.organization,
            name="Weekly Chama",
            reference="WEEKLY-1",
            contribution_amount=100,
            frequency="weekly",
            target_participants=10,
            payout_amount=1000,
            status=Cycle.Status.RECRUITING,
        )
        response = self.client.post("/account/register/", {
            "first_name": "Amina",
            "last_name": "Otieno",
            "username": "amina-cycle",
            "email": "amina-cycle@example.com",
            "phone": "+254700000011",
            "password": "Strong-password-123",
            "confirm_password": "Strong-password-123",
            "organization": self.organization.pk,
            "terms_accepted": "on",
            "privacy_accepted": "on",
        })
        self.assertRedirects(response, "/account/login/")
        member = Member.objects.get(user__username="amina-cycle")
        self.assertTrue(CycleParticipant.objects.filter(cycle=cycle, member=member).exists())
        contribution = Contribution.objects.get(member=member)
        self.assertEqual(contribution.amount_due, cycle.contribution_amount)

    def test_existing_member_can_join_recruiting_cycle_and_get_payment_record(self):
        user = User.objects.create_user(username="existing", password="safe-password")
        member = Member.objects.create(
            organization=self.organization,
            user=user,
            membership_number="SMCF-EXISTING",
        )
        cycle = Cycle.objects.create(
            organization=self.organization,
            name="Open cycle",
            reference="OPEN-1",
            contribution_amount=250,
            frequency="monthly",
            target_participants=10,
            payout_amount=2500,
            status=Cycle.Status.RECRUITING,
        )
        self.client.force_login(user)
        response = self.client.post(f"/account/cycles/{cycle.pk}/join/")
        self.assertRedirects(response, "/account/dashboard/")
        self.assertTrue(CycleParticipant.objects.filter(cycle=cycle, member=member).exists())
        self.assertTrue(Contribution.objects.filter(member=member, amount_due=250).exists())

    @override_settings(DEBUG=True)
    def test_registration_save_error_is_reported_without_redirecting(self):
        with patch("core.forms.MemberRegistrationForm.save", side_effect=RuntimeError("mongo write failed")):
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
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "RuntimeError: mongo write failed", status_code=400)

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

    def test_duplicate_phone_is_rejected(self):
        user = User.objects.create_user(username="existing", email="existing@example.com", password="safe-password")
        Member.objects.create(
            organization=self.organization,
            user=user,
            membership_number="SMCF-EXISTING",
            phone="+254700000003",
        )
        response = self.client.post("/account/register/", {
            "first_name": "Amina", "last_name": "Otieno", "username": "amina",
            "email": "amina@example.com", "phone": "+254700000003",
            "password": "Strong-password-123", "confirm_password": "Strong-password-123",
            "organization": self.organization.pk, "terms_accepted": "on", "privacy_accepted": "on",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already registered")

    def test_invitation_code_accepts_matching_active_invitation(self):
        invitation = MemberInvitation.objects.create(
            organization=self.organization,
            email="amina@example.com",
            expires_at=timezone.now() + timedelta(days=1),
            uses_remaining=1,
            is_active=True,
        )
        invitation.set_code("SMART2026")
        invitation.save(update_fields=["code"])

        response = self.client.post("/account/register/", {
            "first_name": "Amina", "middle_name": "", "last_name": "Otieno",
            "username": "amina", "email": "amina@example.com", "phone": "+254700000001",
            "password": "Strong-password-123", "confirm_password": "Strong-password-123",
            "organization": self.organization.pk, "invitation_code": "SMART2026",
            "terms_accepted": "on", "privacy_accepted": "on",
        })
        self.assertRedirects(response, "/account/login/")
        invitation.refresh_from_db()
        self.assertFalse(invitation.is_active)
        self.assertEqual(invitation.uses_remaining, 0)

    def test_invitation_code_is_optional_for_wrong_email(self):
        invitation = MemberInvitation.objects.create(
            organization=self.organization,
            email="invited@example.com",
            uses_remaining=1,
            is_active=True,
        )
        invitation.set_code("SMART2026")
        invitation.save(update_fields=["code"])

        response = self.client.post("/account/register/", {
            "first_name": "Amina", "middle_name": "", "last_name": "Otieno",
            "username": "amina", "email": "other@example.com", "phone": "+254700000001",
            "password": "Strong-password-123", "confirm_password": "Strong-password-123",
            "organization": self.organization.pk, "invitation_code": "SMART2026",
            "terms_accepted": "on", "privacy_accepted": "on",
        })
        self.assertRedirects(response, "/account/login/")
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_active)
        self.assertEqual(invitation.uses_remaining, 1)

    def test_invitation_code_is_optional_for_expired_code(self):
        invitation = MemberInvitation.objects.create(
            organization=self.organization,
            expires_at=timezone.now() - timedelta(minutes=1),
            uses_remaining=1,
            is_active=True,
        )
        invitation.set_code("SMART2026")
        invitation.save(update_fields=["code"])

        response = self.client.post("/account/register/", {
            "first_name": "Amina", "middle_name": "", "last_name": "Otieno",
            "username": "amina", "email": "amina@example.com", "phone": "+254700000001",
            "password": "Strong-password-123", "confirm_password": "Strong-password-123",
            "organization": self.organization.pk, "invitation_code": "SMART2026",
            "terms_accepted": "on", "privacy_accepted": "on",
        })
        self.assertRedirects(response, "/account/login/")
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_active)
        self.assertEqual(invitation.uses_remaining, 1)

    @patch("core.forms.authenticate", side_effect=DatabaseError("database unavailable"))
    def test_login_database_error_is_shown_as_a_form_error(self, authenticate_mock):
        response = self.client.post("/account/login/", {
            "username": "amina@example.com",
            "password": "Strong-password-123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign-in is temporarily unavailable")

    def test_pending_member_can_log_in_before_approval(self):
        user = User.objects.create_user(
            username="pending-member",
            email="pending@example.com",
            password="Strong-password-123",
        )
        Member.objects.create(
            organization=self.organization,
            user=user,
            membership_number="SMCF-PENDING",
            status=Member.Status.PENDING,
        )

        response = self.client.post("/account/login/", {
            "username": "pending@example.com",
            "password": "Strong-password-123",
        })
        self.assertRedirects(response, "/account/dashboard/")

    def test_member_can_login_by_mobile_number(self):
        user = User.objects.create_user(
            username="mobile-member",
            email="mobile@example.com",
            password="Strong-password-123",
        )
        Member.objects.create(
            organization=self.organization,
            user=user,
            membership_number="SMCF-MOBILE",
            phone="+254700000004",
            status=Member.Status.PENDING,
        )
        response = self.client.post("/account/login/", {
            "username": "+254700000004",
            "password": "Strong-password-123",
        })
        self.assertRedirects(response, "/account/dashboard/")

    def test_member_can_login_with_username_case_difference(self):
        user = User.objects.create_user(
            username="Ian_Abungana",
            email="admin@example.com",
            password="Strong-password-123",
        )
        Member.objects.create(
            organization=self.organization,
            user=user,
            membership_number="SMCF-ADMIN-CASE",
        )
        response = self.client.post("/account/login/", {
            "username": "ian_abungana",
            "password": "Strong-password-123",
        })
        self.assertRedirects(response, "/account/dashboard/")

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
        self.assertRedirects(login_response, "/account/dashboard/")
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

    def test_dashboard_exposes_live_financial_summary(self):
        user = User.objects.create_user(
            username="dashboard-member",
            password="safe-password",
            first_name="Amina",
        )
        member = Member.objects.create(
            organization=self.organization,
            user=user,
            membership_number="SMCF-DASHBOARD",
            status=Member.Status.ACTIVE,
        )
        cycle = Cycle.objects.create(
            organization=self.organization,
            name="Growth cycle",
            reference="GROWTH-1",
            contribution_amount=500,
            frequency="monthly",
            target_participants=2,
            payout_amount=1000,
            status=Cycle.Status.ACTIVE,
        )
        CycleParticipant.objects.create(cycle=cycle, member=member, number=1)
        Contribution.objects.create(
            organization=self.organization,
            member=member,
            product=ContributionProduct.objects.create(
                organization=self.organization,
                name="Growth contribution",
                amount=500,
                frequency="monthly",
            ),
            due_date=timezone.localdate(),
            amount_due=500,
            amount_paid=300,
            status=Contribution.Status.PARTIAL,
        )

        self.client.force_login(user)
        response = self.client.get("/account/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_paid"], 300)
        self.assertEqual(response.context["outstanding_total"], 200)
        self.assertEqual(response.context["contribution_progress"], 60)
        self.assertEqual(response.context["next_payout"].number, 1)


class LandingPageTests(TestCase):
    def test_landing_page_and_auth_links(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your Chama. Your Cycle.")
        self.assertContains(response, 'href="/account/register/"')
        self.assertContains(response, 'href="/account/login/"')
        self.assertContains(response, "Questions, Answered.")
        self.assertNotContains(response, "Super Admin")
        self.assertNotContains(response, "Organization Admin")
        self.assertNotContains(response, "Administration Login")
        self.assertNotContains(response, "/admin/login/")

    def test_static_assets_are_resolvable(self):
        css = Path(settings.BASE_DIR) / "static" / "css" / "landing.css"
        script = Path(settings.BASE_DIR) / "static" / "js" / "landing.js"
        favicon = Path(settings.BASE_DIR) / "static" / "favicon.svg"
        react_script = Path(settings.BASE_DIR) / "static" / "react" / "assets" / "react.js"
        react_css = Path(settings.BASE_DIR) / "static" / "react" / "assets" / "react.css"
        self.assertTrue(css.is_file())
        self.assertTrue(script.is_file())
        self.assertTrue(favicon.is_file())
        self.assertTrue(react_script.is_file())
        self.assertTrue(react_css.is_file())
