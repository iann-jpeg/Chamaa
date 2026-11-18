import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from core.models import OrganizationMembership
from django.views.decorators.http import require_GET, require_POST
from .models import Account
from .services import post_entry


@require_GET
def health(request):
    return JsonResponse({"service": "chamapilot", "status": "ok"})


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
