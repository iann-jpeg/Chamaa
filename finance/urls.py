from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("accounts/<int:account_id>/", views.account_detail, name="account-detail"),
    path("accounts/<int:account_id>/entries/", views.create_entry, name="account-entry"),
    path("withdrawals/", views.request_withdrawal, name="withdrawal-request"),
    path("withdrawals/<int:withdrawal_id>/approve/", views.approve_withdrawal_view, name="withdrawal-approve"),
]
