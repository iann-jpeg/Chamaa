from django.test import TestCase

# Create your tests here.
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import Member, Organization, OrganizationMembership
from .models import Account, Contribution, ContributionProduct, WalletWithdrawal
from .services import approve_withdrawal, post_entry
from django.utils import timezone
from unittest.mock import patch
from .models import MpesaTransaction
from .services import process_mpesa_callback

User = get_user_model()


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

    def test_withdrawal_requires_approval_role_and_balance(self):
        wallet = Account.objects.create(
            organization=self.organization,
            member=self.member,
            name="SMCF-0001 Wallet",
            kind=Account.Kind.WALLET,
        )
        post_entry(account=wallet, reference="DEP-1", description="Deposit", amount="100")
        withdrawal = WalletWithdrawal.objects.create(
            organization=self.organization,
            member=self.member,
            reference="WD-1",
            amount=Decimal("75"),
        )
        with self.assertRaises(PermissionError):
            approve_withdrawal(withdrawal, self.user)
        OrganizationMembership.objects.filter(
            organization=self.organization, user=self.user
        ).update(role=OrganizationMembership.Role.TREASURER)
        approve_withdrawal(withdrawal, self.user)
        self.assertEqual(withdrawal.status, WalletWithdrawal.Status.APPROVED)

    def test_mpesa_success_callback_records_receipt(self):
        transaction = MpesaTransaction.objects.create(
            member=self.member,
            phone="254700000001",
            amount=Decimal("500"),
            checkout_request_id="checkout-test-123",
        )
        process_mpesa_callback({
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "checkout-test-123",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 500},
                            {"Name": "MpesaReceiptNumber", "Value": "TESTRECEIPT1"},
                        ]
                    },
                }
            }
        })
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, MpesaTransaction.Status.SUCCESS)
        self.assertEqual(transaction.mpesa_receipt, "TESTRECEIPT1")

    def test_mpesa_callback_retry_is_idempotent(self):
        product = ContributionProduct.objects.create(
            organization=self.organization,
            name="Weekly savings",
            amount=Decimal("500"),
        )
        contribution = Contribution.objects.create(
            organization=self.organization,
            member=self.member,
            product=product,
            due_date=timezone.now().date(),
            amount_due=Decimal("500"),
        )
        transaction = MpesaTransaction.objects.create(
            member=self.member,
            contribution=contribution,
            phone="254700000001",
            amount=Decimal("500"),
            checkout_request_id="checkout-retry-123",
        )
        payload = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "checkout-retry-123",
                    "ResultCode": 0,
                    "ResultDesc": "Success",
                    "CallbackMetadata": {"Item": [
                        {"Name": "Amount", "Value": 500},
                        {"Name": "MpesaReceiptNumber", "Value": "RETRY1"},
                    ]},
                }
            }
        }
        process_mpesa_callback(payload)
        process_mpesa_callback(payload)
        contribution.refresh_from_db()
        self.assertEqual(contribution.amount_paid, Decimal("500.00"))
