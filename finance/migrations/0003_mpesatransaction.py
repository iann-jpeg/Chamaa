import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0002_cycle_cycleparticipant_walletwithdrawal_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MpesaTransaction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("phone", models.CharField(max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=18)),
                ("merchant_request_id", models.CharField(blank=True, max_length=100)),
                ("checkout_request_id", models.CharField(max_length=100, unique=True)),
                ("mpesa_receipt", models.CharField(blank=True, max_length=50)),
                ("result_code", models.IntegerField(blank=True, null=True)),
                ("result_description", models.CharField(blank=True, max_length=300)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("success", "Successful"), ("failed", "Failed")], default="pending", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("contribution", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="mpesa_transactions", to="finance.contribution")),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="mpesa_transactions", to="core.member")),
            ],
        ),
    ]
