from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
import uuid
from core.models import Member, Organization


class Account(models.Model):
    class Kind(models.TextChoices):
        MEMBERSHIP = "membership", "Membership"
        SAVINGS = "savings", "Savings"
        WALLET = "wallet", "Wallet"
        OPERATIONS = "operations", "Operations"
        INVESTMENT = "investment", "Investment"
        LOAN = "loan", "Loan portfolio"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    member = models.ForeignKey(Member, null=True, blank=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    currency = models.CharField(max_length=3, default="KES")
    opening_balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "member", "kind"], name="unique_account_kind"
            )
        ]

    @property
    def balance(self):
        return self.opening_balance + sum(
            (entry.amount for entry in self.entries.filter(status=LedgerEntry.Status.POSTED)),
            Decimal("0"),
        )

    def __str__(self):
        return self.name


class LedgerEntry(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        POSTED = "posted", "Posted"
        VOID = "void", "Voided"

    account = models.ForeignKey(Account, related_name="entries", on_delete=models.PROTECT)
    reference = models.CharField(max_length=80)
    description = models.CharField(max_length=240)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.POSTED)
    posted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "reference"], name="unique_ledger_reference_per_account"
            )
        ]
        ordering = ["-posted_at"]


class ContributionProduct(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    frequency = models.CharField(max_length=20, default="monthly")
    account_kind = models.CharField(max_length=20, choices=Account.Kind.choices, default=Account.Kind.SAVINGS)
    is_active = models.BooleanField(default=True)


class Contribution(models.Model):
    class Status(models.TextChoices):
        DUE = "due", "Due"
        PARTIAL = "partial", "Partially paid"
        PAID = "paid", "Paid"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    product = models.ForeignKey(ContributionProduct, on_delete=models.PROTECT)
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=18, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DUE)

    @property
    def outstanding_amount(self):
        return max(self.amount_due - self.amount_paid, Decimal("0"))

    def apply_payment(self, amount):
        if amount <= 0 or self.amount_paid + amount > self.amount_due:
            raise ValueError("Payment must be positive and cannot exceed the outstanding amount.")
        self.amount_paid += amount
        self.status = self.Status.PAID if self.amount_paid == self.amount_due else self.Status.PARTIAL
        self.save(update_fields=["amount_paid", "status"])


class Cycle(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        RECRUITING = "recruiting", "Recruiting"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        SUSPENDED = "suspended", "Suspended"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    name = models.CharField(max_length=160)
    reference = models.CharField(max_length=40)
    contribution_amount = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    frequency = models.CharField(max_length=20, default="weekly")
    target_participants = models.PositiveIntegerField(validators=[MinValueValidator(2)])
    payout_amount = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "reference"], name="unique_cycle_reference")
        ]


class CycleParticipant(models.Model):
    cycle = models.ForeignKey(Cycle, related_name="participants", on_delete=models.PROTECT)
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    number = models.PositiveIntegerField()
    joined_at = models.DateTimeField(auto_now_add=True)
    is_eligible = models.BooleanField(default=False)
    has_received_payout = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cycle", "member"], name="unique_cycle_member"),
            models.UniqueConstraint(fields=["cycle", "number"], name="unique_cycle_number"),
        ]


class WalletWithdrawal(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SETTLED = "settled", "Settled"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    reference = models.CharField(max_length=80, unique=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    fee = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=240, blank=True)


class MpesaTransaction(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Successful"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="mpesa_transactions")
    contribution = models.ForeignKey(
        Contribution,
        on_delete=models.PROTECT,
        related_name="mpesa_transactions",
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    merchant_request_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    mpesa_receipt = models.CharField(max_length=50, blank=True)
    result_code = models.IntegerField(null=True, blank=True)
    result_description = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
