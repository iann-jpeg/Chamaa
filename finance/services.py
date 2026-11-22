from decimal import Decimal
import base64
import json
import os
from datetime import datetime
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from django.db import IntegrityError, transaction
from django.utils import timezone
from .models import Account, LedgerEntry, MpesaTransaction, WalletWithdrawal


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


def normalize_mpesa_phone(phone):
    digits = "".join(character for character in str(phone) if character.isdigit())
    if digits.startswith("0"):
        digits = "254" + digits[1:]
    if not digits.startswith("254") or len(digits) != 12:
        raise ValueError("Enter a valid Kenyan mobile number in 2547XXXXXXXX format.")
    return digits


def _mpesa_post(url, payload, access_token):
    body = json.dumps(payload).encode("utf-8")
    http_request = urllib_request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib_request.urlopen(http_request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"M-Pesa request failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise RuntimeError("M-Pesa could not be reached. Please try again.") from exc


def initiate_mpesa_stk(*, member, contribution, phone, amount):
    amount = Decimal(amount)
    outstanding = contribution.amount_due - contribution.amount_paid
    if amount <= 0 or amount > outstanding:
        raise ValueError("The payment amount must be positive and cannot exceed the outstanding balance.")

    consumer_key = os.environ.get("MPESA_CONSUMER_KEY", "").strip()
    consumer_secret = os.environ.get("MPESA_CONSUMER_SECRET", "").strip()
    shortcode = os.environ.get("MPESA_SHORTCODE", "").strip()
    passkey = os.environ.get("MPESA_PASSKEY", "").strip()
    callback_url = os.environ.get("MPESA_CALLBACK_URL", "").strip()
    if not all((consumer_key, consumer_secret, shortcode, passkey, callback_url)):
        raise RuntimeError("M-Pesa is not configured. Contact the organization administrator.")

    environment = os.environ.get("MPESA_ENVIRONMENT", "sandbox").lower()
    base_url = (
        "https://sandbox.safaricom.co.ke"
        if environment == "sandbox"
        else "https://api.safaricom.co.ke"
    )
    credentials = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode("utf-8")).decode("ascii")
    oauth_request = urllib_request.Request(
        f"{base_url}/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": f"Basic {credentials}"},
        method="GET",
    )
    try:
        with urllib_request.urlopen(oauth_request, timeout=30) as response:
            token_data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError("M-Pesa authentication failed. Check the Daraja credentials.") from exc
    except URLError as exc:
        raise RuntimeError("M-Pesa authentication could not be reached.") from exc

    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError("M-Pesa authentication did not return an access token.")

    phone = normalize_mpesa_phone(phone)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode("utf-8")).decode("ascii")
    account_reference = contribution.product.name[:12].replace(" ", "") or member.membership_number[:12]
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": "Chama contribution",
    }
    response = _mpesa_post(
        f"{base_url}/mpesa/stkpush/v1/processrequest",
        payload,
        access_token,
    )
    if response.get("ResponseCode") != "0" and str(response.get("ResponseCode")) != "0":
        raise RuntimeError(response.get("ResponseDescription", "M-Pesa rejected the payment request."))

    return MpesaTransaction.objects.create(
        member=member,
        contribution=contribution,
        phone=phone,
        amount=amount,
        merchant_request_id=response.get("MerchantRequestID", ""),
        checkout_request_id=response["CheckoutRequestID"],
        status=MpesaTransaction.Status.PENDING,
    )


@transaction.atomic
def process_mpesa_callback(payload):
    callback = payload.get("Body", {}).get("stkCallback", {})
    checkout_request_id = callback.get("CheckoutRequestID")
    if not checkout_request_id:
        return None

    mpesa_transaction = MpesaTransaction.objects.filter(
        checkout_request_id=checkout_request_id
    ).first()
    if mpesa_transaction is None:
        return None

    result_code = callback.get("ResultCode")
    mpesa_transaction.result_code = result_code
    mpesa_transaction.result_description = callback.get("ResultDesc", "")
    mpesa_transaction.completed_at = timezone.now()
    if result_code != 0:
        mpesa_transaction.status = MpesaTransaction.Status.FAILED
        mpesa_transaction.save(
            update_fields=["result_code", "result_description", "completed_at", "status"]
        )
        return mpesa_transaction

    receipt = ""
    metadata = callback.get("CallbackMetadata", {}).get("Item", [])
    for item in metadata:
        name = item.get("Name")
        if name == "MpesaReceiptNumber":
            receipt = str(item.get("Value", ""))
        elif name == "Amount" and mpesa_transaction.status == MpesaTransaction.Status.PENDING:
            try:
                paid_amount = Decimal(str(item.get("Value", "0")))
                mpesa_transaction.amount = paid_amount
            except Exception:
                pass

    mpesa_transaction.mpesa_receipt = receipt
    mpesa_transaction.status = MpesaTransaction.Status.SUCCESS
    mpesa_transaction.save(
        update_fields=[
            "amount",
            "mpesa_receipt",
            "result_code",
            "result_description",
            "completed_at",
            "status",
        ]
    )
    if mpesa_transaction.contribution_id:
        contribution = mpesa_transaction.contribution
        if contribution.amount_paid < contribution.amount_due:
            remaining = contribution.amount_due - contribution.amount_paid
            contribution.apply_payment(min(mpesa_transaction.amount, remaining))
    return mpesa_transaction
