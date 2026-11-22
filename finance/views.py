import json
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from core.models import OrganizationMembership
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import connection
from .models import Account, WalletWithdrawal
from .services import (
    approve_withdrawal,
    get_or_create_member_account,
    initiate_mpesa_stk,
    post_entry,
    process_mpesa_callback,
)


@require_GET
def health(request):
    database_status = "sqlite"
    if getattr(settings, "MONGODB_URI", ""):
        database_status = "mongodb-atlas"
        try:
            connection.ensure_connection()
            write_status = "ok"
            try:
                database = connection.connection.get_database(settings.MONGODB_DB_NAME)
                probe = database["_health_probe"].insert_one({"probe": "account-write"})
                database["_health_probe"].delete_one({"_id": probe.inserted_id})
            except Exception as write_exc:
                write_status = f"{write_exc.__class__.__name__}: {write_exc}"
            orm_write_status = "ok"
            try:
                from django.contrib.auth import get_user_model
                import secrets
                probe_name = f"_health_probe_{secrets.token_hex(6)}"
                probe_user = get_user_model().objects.create(username=probe_name)
                probe_user.delete()
            except Exception as orm_write_exc:
                orm_write_status = f"{orm_write_exc.__class__.__name__}: {orm_write_exc}"
            from django.contrib.auth import get_user_model
            from core.models import Member, Organization, OrganizationMembership
            return JsonResponse({
                "service": "chamaa",
                "status": "ok" if write_status == "ok" and orm_write_status == "ok" else "degraded",
                "database": database_status,
                "write_probe": write_status,
                "orm_write_probe": orm_write_status,
                "mpesa_configured": bool(
                    getattr(settings, "MPESA_CONSUMER_KEY", "")
                    and getattr(settings, "MPESA_CONSUMER_SECRET", "")
                    and getattr(settings, "MPESA_SHORTCODE", "")
                    and getattr(settings, "MPESA_PASSKEY", "")
                    and getattr(settings, "MPESA_CALLBACK_URL", "")
                ),
                "models": {
                    "users": get_user_model().objects.count(),
                    "organizations": Organization.objects.count(),
                    "members": Member.objects.count(),
                    "memberships": OrganizationMembership.objects.count(),
                },
            })
        except Exception as exc:
            return JsonResponse({
                "service": "chamaa",
                "status": "degraded",
                "database": "mongodb-atlas",
                "error": "Database connection unavailable",
            }, status=503)
    return JsonResponse({
        "service": "chamaa",
        "status": "ok",
        "database": database_status,
    })


def visible_account(request, account_id):
    return get_object_or_404(
        Account.objects.filter(
            organization__organizationmembership__user=request.user,
            organization__organizationmembership__is_active=True,
        ),
        pk=account_id,
    )


@login_required
@require_GET
def account_detail(request, account_id):
    account = visible_account(request, account_id)
    return JsonResponse({
        "id": account.id,
        "name": account.name,
        "kind": account.kind,
        "currency": account.currency,
        "balance": str(account.balance),
    })


@login_required
@require_POST
def create_entry(request, account_id):
    try:
        account = visible_account(request, account_id)
        if not OrganizationMembership.objects.filter(
            organization=account.organization,
            user=request.user,
            role__in=[
                OrganizationMembership.Role.ADMIN,
                OrganizationMembership.Role.TREASURER,
            ],
            is_active=True,
        ).exists():
            return JsonResponse({"error": "Insufficient permission to post ledger entries."}, status=403)
        payload = json.loads(request.body)
        entry = post_entry(
            account=account,
            reference=payload["reference"],
            description=payload["description"],
            amount=payload["amount"],
        )
    except (KeyError, ValueError, Account.DoesNotExist, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(
        {"id": entry.id, "reference": entry.reference, "amount": str(entry.amount)},
        status=201,
    )


@login_required
@require_POST
def request_withdrawal(request):
    if not hasattr(request.user, "member_profile"):
        return JsonResponse({"error": "Only members can request withdrawals."}, status=403)
    try:
        payload = json.loads(request.body)
        amount = payload["amount"]
        withdrawal = WalletWithdrawal.objects.create(
            organization=request.user.member_profile.organization,
            member=request.user.member_profile,
            reference=payload["reference"],
            amount=amount,
            fee=payload.get("fee", 0),
        )
        wallet = get_or_create_member_account(request.user.member_profile, Account.Kind.WALLET)
        if wallet.balance < withdrawal.amount + withdrawal.fee:
            withdrawal.delete()
            return JsonResponse({"error": "Insufficient wallet balance."}, status=400)
    except (KeyError, ValueError, Account.DoesNotExist, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"id": withdrawal.id, "status": withdrawal.status}, status=201)


@login_required
@require_POST
def approve_withdrawal_view(request, withdrawal_id):
    withdrawal = get_object_or_404(
        WalletWithdrawal,
        pk=withdrawal_id,
        organization__organizationmembership__user=request.user,
        organization__organizationmembership__is_active=True,
    )
    try:
        approve_withdrawal(withdrawal, request.user)
    except (ValueError, PermissionError) as exc:
        return JsonResponse({"error": str(exc)}, status=403)
    return JsonResponse({"id": withdrawal.id, "status": withdrawal.status})


@login_required
@require_POST
def initiate_mpesa_payment(request):
    if not hasattr(request.user, "member_profile"):
        return JsonResponse({"error": "Only members can pay cycle contributions."}, status=403)

    contribution_id = request.POST.get("contribution")
    phone = request.POST.get("phone", "")
    amount = request.POST.get("amount", "")
    try:
        from .models import Contribution

        contribution = Contribution.objects.get(
            pk=contribution_id,
            member=request.user.member_profile,
        )
        transaction = initiate_mpesa_stk(
            member=request.user.member_profile,
            contribution=contribution,
            phone=phone,
            amount=amount,
        )
    except Contribution.DoesNotExist:
        return JsonResponse({"error": "Contribution not found."}, status=404)
    except (KeyError, ValueError, ArithmeticError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse(
        {
            "id": str(transaction.id),
            "checkout_request_id": transaction.checkout_request_id,
            "status": transaction.status,
        },
        status=202,
    )


@login_required
@require_GET
def mpesa_payment_status(request, transaction_id):
    transaction = get_object_or_404(
        request.user.member_profile.mpesa_transactions,
        pk=transaction_id,
    )
    return JsonResponse(
        {
            "id": str(transaction.id),
            "status": transaction.status,
            "result_description": transaction.result_description,
            "mpesa_receipt": transaction.mpesa_receipt,
        }
    )


@csrf_exempt
@require_POST
def mpesa_callback(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid JSON"}, status=400)
    process_mpesa_callback(payload)
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
