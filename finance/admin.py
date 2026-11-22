from django.contrib import admin
from .models import Account, Contribution, ContributionProduct, LedgerEntry, MpesaTransaction

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "member", "kind", "currency", "is_active")
    list_filter = ("organization", "kind", "currency", "is_active")
    search_fields = ("name", "member__membership_number")


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("reference", "account", "amount", "status", "posted_at")
    list_filter = ("status", "account__kind", "posted_at")
    search_fields = ("reference", "description", "account__name")
    readonly_fields = ("posted_at",)


@admin.register(ContributionProduct)
class ContributionProductAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "amount", "frequency", "account_kind", "is_active")
    list_filter = ("organization", "frequency", "account_kind", "is_active")


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ("member", "product", "due_date", "amount_due", "amount_paid", "status")
    list_filter = ("organization", "status", "due_date")


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ("member", "phone", "amount", "status", "mpesa_receipt", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("phone", "checkout_request_id", "mpesa_receipt", "member__membership_number")
