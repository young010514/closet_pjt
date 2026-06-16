from django.db import models
from common.models import TimeStampedModel


class Region(TimeStampedModel):
    sido = models.CharField(max_length=30, verbose_name="시/도")
    sigungu = models.CharField(max_length=30, verbose_name="시/군/구")
    # 시/도 시/군/구 까지만 필요한 정보일 거같은데 !? 나중에 추가하게 된다면 ..
    # dong = models.CharField(max_length=30, blank=True, verbose_name="읍/면/동")

    class Meta:
        db_table = "regions"
        constraints = [
            models.UniqueConstraint(
                fields=["sido", "sigungu"],
                name="unique_region"
            )
        ]

    def __str__(self):
        # if self.dong:
        #     return f"{self.sido} {self.sigungu} {self.dong}"
        return f"{self.sido} {self.sigungu}"