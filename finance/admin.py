from django.contrib import admin
from .models import Account, Contribution, ContributionProduct, LedgerEntry

admin.site.register([Account, LedgerEntry, ContributionProduct, Contribution])
