from decimal import Decimal
from django.db import IntegrityError, transaction
from django.utils import timezone
from .models import Account, LedgerEntry, WalletWithdrawal


@transaction.atomic
def post_entry(*, account, reference, description, amount):
    """Post an idempotent entry; duplicate payment references never post twice."""
    amount = Decimal(amount)
    if amount == 0:
        raise ValueError("Ledger amount cannot be zero.")
    try:
        with transaction.atomic():
            entry = LedgerEntry.objects.create(
                account=account,
                reference=reference,
                description=description,
                amount=amount,
            )
    except IntegrityError:
        entry = LedgerEntry.objects.get(account=account, reference=reference)
        if entry.amount != amount:
            raise ValueError("Reference already exists with a different amount.")
    return entry


def get_or_create_member_account(member, kind):
    return Account.objects.get_or_create(
        organization=member.organization,
        member=member,
        kind=kind,
        defaults={"name": f"{member.membership_number} {kind.title()}"},
    )[0]


@transaction.atomic
def approve_withdrawal(withdrawal, approver):
    if withdrawal.status != WalletWithdrawal.Status.PENDING:
        raise ValueError("Only pending withdrawals can be approved.")
    if not withdrawal.organization.organizationmembership_set.filter(
        user=approver, role__in=["admin", "treasurer"], is_active=True
    ).exists():
        raise PermissionError("Only an administrator or treasurer may approve withdrawals.")
    wallet = get_or_create_member_account(withdrawal.member, Account.Kind.WALLET)
    if wallet.balance < Decimal(withdrawal.amount) + Decimal(withdrawal.fee):
        raise ValueError("Insufficient wallet balance.")
    withdrawal.status = WalletWithdrawal.Status.APPROVED
    withdrawal.approved_at = timezone.now()
    withdrawal.save(update_fields=["status", "approved_at"])
    return withdrawal
