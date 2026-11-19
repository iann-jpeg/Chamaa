from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Member, Organization


class MemberRegistrationForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    middle_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150)
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    organization = forms.ModelChoiceField(queryset=Organization.objects.filter(is_active=True))
    invitation_code = forms.CharField(max_length=64, required=False)
    terms_accepted = forms.BooleanField()
    privacy_accepted = forms.BooleanField()

    def clean_username(self):
        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError("That email address is already registered.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        organization = cleaned.get("organization")
        code = cleaned.get("invitation_code")
        if organization and not organization.allow_public_registration and not code:
            self.add_error("invitation_code", "An organization invitation code is required.")
        if organization and code and not organization.memberinvitation_set.filter(
            code=code, is_active=True, uses_remaining__gt=0
        ).exists():
            self.add_error("invitation_code", "That invitation code is invalid or expired.")
        return cleaned

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        user = get_user_model().objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )
        member = Member.objects.create(
            organization=data["organization"],
            user=user,
            membership_number=f"{data['organization'].slug.upper()}-{user.pk:06d}",
            middle_name=data["middle_name"],
            phone=data["phone"],
            status=Member.Status.PENDING,
        )
        from .models import OrganizationMembership, MemberNotificationPreference
        OrganizationMembership.objects.create(
            organization=member.organization, user=user, role=OrganizationMembership.Role.MEMBER
        )
        MemberNotificationPreference.objects.create(member=member)
        if data.get("invitation_code"):
            invitation = member.organization.memberinvitation_set.select_for_update().get(
                code=data["invitation_code"]
            )
            invitation.uses_remaining -= 1
            if invitation.uses_remaining == 0:
                invitation.is_active = False
            invitation.save(update_fields=["uses_remaining", "is_active"])
        return member


class MemberAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Username, email, or mobile number")

    def clean(self):
        identifier = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        User = get_user_model()
        user = User.objects.filter(email__iexact=identifier).first()
        if not user:
            member = Member.objects.filter(phone=identifier).select_related("user").first()
            user = member.user if member else None
        username = user.username if user else identifier
        self.user_cache = authenticate(self.request, username=username, password=password)
        if self.user_cache is None:
            raise self.get_invalid_login_error()
        if not self.user_cache.is_active:
            raise ValidationError("This account is inactive.")
        member = getattr(self.user_cache, "member_profile", None)
        if member and member.status != Member.Status.ACTIVE:
            raise ValidationError("Your membership is awaiting approval or is not active.")
        return self.cleaned_data
