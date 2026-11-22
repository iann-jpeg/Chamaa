from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.utils import timezone
import logging
import secrets
import string
from .models import Member, Organization, MemberInvitation

logger = logging.getLogger(__name__)


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

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if Member.objects.filter(phone=phone).exists():
            raise ValidationError("That mobile number is already registered.")
        return phone

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        organization = cleaned.get("organization")
        code = cleaned.get("invitation_code")
        email = cleaned.get("email")
        # Invitations are optional while registration is being opened to members.
        # A valid code is still applied when supplied; an invalid code does not
        # prevent account creation.
        if organization and code:
            matched = False
            for invitation in organization.memberinvitation_set.filter(is_active=True, uses_remaining__gt=0):
                if invitation.matches_code(code) and invitation.is_available(email=email):
                    matched = True
                    break
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
        alphabet = string.ascii_uppercase + string.digits
        while True:
            membership_number = (
                f"{data['organization'].slug.upper()}-{''.join(secrets.choice(alphabet) for _ in range(8))}"
            )
            if not Member.objects.filter(
                organization=data["organization"],
                membership_number=membership_number,
            ).exists():
                break
        member = Member.objects.create(
            organization=data["organization"],
            user=user,
            membership_number=membership_number,
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
            matched_invitation = None
            for invitation in member.organization.memberinvitation_set.filter(
                is_active=True, uses_remaining__gt=0
            ):
                if invitation.matches_code(data["invitation_code"]) and invitation.is_available(
                    email=data["email"], now=timezone.now()
                ):
                    matched_invitation = invitation
                    break
            if matched_invitation:
                matched_invitation.uses_remaining -= 1
                if matched_invitation.uses_remaining == 0:
                    matched_invitation.is_active = False
                matched_invitation.save(update_fields=["uses_remaining", "is_active"])
        return member


class MemberAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Username, email, or mobile number")

    def clean(self):
        identifier = (self.cleaned_data.get("username") or "").strip()
        password = self.cleaned_data.get("password")
        User = get_user_model()
        try:
            user = User.objects.filter(email__iexact=identifier).first()
            if not user:
                member = Member.objects.filter(phone=identifier).select_related("user").first()
                user = member.user if member else None
            username = user.username if user else identifier
            self.user_cache = authenticate(self.request, username=username, password=password)
        except DatabaseError as exc:
            logger.exception("Authentication database lookup failed")
            raise ValidationError("Sign-in is temporarily unavailable. Please try again.") from exc
        if self.user_cache is None:
            raise self.get_invalid_login_error()
        if not self.user_cache.is_active:
            raise ValidationError("This account is inactive.")
        member = getattr(self.user_cache, "member_profile", None)
        if member and member.status in {Member.Status.SUSPENDED, Member.Status.EXITED}:
            raise ValidationError("Your membership is suspended or inactive.")
        return self.cleaned_data
