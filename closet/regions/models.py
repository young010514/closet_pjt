from django.db import models
from common.models import TimeStampedModel,ActiveModel


class Region(TimeStampedModel, ActiveModel):
    sido = models.CharField(max_length=30, verbose_name="시/도")
    sigungu = models.CharField(max_length=30, verbose_name="시/군/구")
    dong = models.CharField(max_length=30, blank=True, verbose_name="읍/면/동")

    region_code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="지역 코드",
    )

    class Meta:
        db_table = "regions"
        verbose_name = "지역"
        verbose_name_plural = "지역"
        ordering = ["sido", "sigungu", "dong"]
        constraints = [
            models.UniqueConstraint(
                fields=["sido", "sigungu", "dong"],
                name="unique_region_sido_sigungu_dong",
            )
        ]

    def __str__(self):
        if self.dong:
            return f"{self.sido} {self.sigungu} {self.dong}"
        return f"{self.sido} {self.sigungu}"

    @property
    def full_name(self):
        if self.dong:
            return f"{self.sido} {self.sigungu} {self.dong}"
        return f"{self.sido} {self.sigungu}"