from django.test import TestCase

# Create your tests here.
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from core.models import Member, Organization, OrganizationMembership
from .models import Account
from .services import post_entry


class LedgerTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="SMCF", slug="smcf")
        self.user = User.objects.create_user(username="member", password="safe-password")
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.user, role="member"
        )
        self.member = Member.objects.create(
            organization=self.organization, user=self.user, membership_number="SMCF-0001"
        )
        self.account = Account.objects.create(
            organization=self.organization,
            member=self.member,
            name="SMCF-0001 Savings",
            kind=Account.Kind.SAVINGS,
        )

    def test_duplicate_reference_is_idempotent(self):
        post_entry(
            account=self.account,
            reference="PAY-1",
            description="Contribution",
            amount=Decimal("214.00"),
        )
        duplicate = post_entry(
            account=self.account,
            reference="PAY-1",
            description="Callback retry",
            amount=Decimal("214.00"),
        )
        self.assertEqual(self.account.entries.count(), 1)
        self.assertEqual(duplicate.amount, Decimal("214.00"))

    def test_account_endpoint_is_tenant_scoped(self):
        other_org = Organization.objects.create(name="Other", slug="other")
        other_account = Account.objects.create(
            organization=other_org, name="Other savings", kind=Account.Kind.SAVINGS
        )
        self.client.force_login(self.user)
        response = self.client.get(f"/api/accounts/{other_account.pk}/")
        self.assertEqual(response.status_code, 404)
