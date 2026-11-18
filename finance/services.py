from decimal import Decimal
from django.db import IntegrityError, transaction
from .models import Account, LedgerEntry


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
