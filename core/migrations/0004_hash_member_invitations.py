from django.contrib.auth.hashers import make_password
from django.core.validators import MinLengthValidator
from django.db import migrations, models


def hash_existing_codes(apps, schema_editor):
    MemberInvitation = apps.get_model("core", "MemberInvitation")
    for invitation in MemberInvitation.objects.all().iterator():
        if invitation.code and not invitation.code.startswith(("pbkdf2_", "argon2$", "bcrypt$", "scrypt$")):
            invitation.code = make_password(invitation.code)
            invitation.save(update_fields=["code"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_member_emergency_contact_member_middle_name_and_more"),
        ("core", "0003_organization_country_organization_county_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="memberinvitation",
            name="code",
            field=models.CharField(
                max_length=128,
                unique=True,
                validators=[MinLengthValidator(8)],
            ),
        ),
        migrations.RunPython(hash_existing_codes, migrations.RunPython.noop),
    ]
