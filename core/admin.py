from django.contrib import admin
from .models import Member, Organization, OrganizationMembership

admin.site.register([Organization, OrganizationMembership, Member])
