# Generated manually to migrate UserRegion from UserProfile to User.

from django.conf import settings
from django.db import migrations, models


def forwards_copy_user_regions(apps, schema_editor):
    UserRegion = apps.get_model("accounts", "UserRegion")

    for user_region in UserRegion.objects.select_related("user_profile"):
        user_profile = getattr(user_region, "user_profile", None)
        if not user_profile or not getattr(user_profile, "user_id", None):
            user_region.delete()
            continue

        user_region.user_id = user_profile.user_id
        user_region.save(update_fields=["user"])


class Migration(migrations.Migration):

    dependencies = [
        (
            "accounts",
            "0002_alter_businessprofile_id_alter_follow_id_and_more",
        ),
        ("regions", "0002_alter_region_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="userregion",
            name="user",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.CASCADE,
                related_name="selected_regions",
                to=settings.AUTH_USER_MODEL,
                verbose_name="사용자",
            ),
        ),
        migrations.RunPython(
            forwards_copy_user_regions,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveConstraint(
            model_name="userregion",
            name="unique_user_profile_region",
        ),
        migrations.RemoveConstraint(
            model_name="userregion",
            name="unique_user_profile_region_priority",
        ),
        migrations.AddConstraint(
            model_name="userregion",
            constraint=models.UniqueConstraint(
                fields=("user", "region"),
                name="unique_user_region",
            ),
        ),
        migrations.AddConstraint(
            model_name="userregion",
            constraint=models.UniqueConstraint(
                fields=("user", "priority"),
                name="unique_user_region_priority",
            ),
        ),
        migrations.AlterField(
            model_name="userregion",
            name="user",
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name="selected_regions",
                to=settings.AUTH_USER_MODEL,
                verbose_name="사용자",
            ),
        ),
        migrations.AlterField(
            model_name="userregion",
            name="region",
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name="user_regions",
                to="regions.region",
                verbose_name="지역",
            ),
        ),
        migrations.AlterField(
            model_name="userregion",
            name="priority",
            field=models.PositiveIntegerField(
                default=1,
                verbose_name="지역 우선순위",
            ),
        ),
        migrations.RemoveField(
            model_name="userregion",
            name="user_profile",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="regions",
        ),
    ]
