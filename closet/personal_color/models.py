from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import TimeStampedModel


class PersonalColorAnalysis(TimeStampedModel):
    class ResultType(models.TextChoices):
        SPRING_WARM = "spring_warm", "봄 웜톤"
        SUMMER_COOL = "summer_cool", "여름 쿨톤"
        AUTUMN_WARM = "autumn_warm", "가을 웜톤"
        WINTER_COOL = "winter_cool", "겨울 쿨톤"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="personal_color_analyses",
    )

    result_type = models.CharField(
        max_length=20,
        choices=ResultType.choices,
        db_index=True,
    )

    result_subtype = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("100")),
        ],
    )

    summary = models.TextField()

    best_colors = models.JSONField(default=list)
    avoid_colors = models.JSONField(default=list)
    recommendations = models.JSONField(default=dict)

    analysis_metrics = models.JSONField(
        default=dict,
        blank=True,
    )

    provider_name = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    model_version = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    class Meta:
        db_table = "personal_color_analyses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "created_at"],
                name="pcolor_user_created_idx",
            ),
            models.Index(
                fields=["result_type"],
                name="pcolor_result_type_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.get_result_type_display()}"

