from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("mpesa/pay/", views.initiate_mpesa_payment, name="mpesa-pay"),
    path("mpesa/callback/", views.mpesa_callback, name="mpesa-callback"),
    path("mpesa/status/<uuid:transaction_id>/", views.mpesa_payment_status, name="mpesa-status"),
    path("accounts/<int:account_id>/", views.account_detail, name="account-detail"),
    path("accounts/<int:account_id>/entries/", views.create_entry, name="account-entry"),
    path("withdrawals/", views.request_withdrawal, name="withdrawal-request"),
    path("withdrawals/<int:withdrawal_id>/approve/", views.approve_withdrawal_view, name="withdrawal-approve"),
]
