from django.db import models

# Create your models here.

# 생성일, 수정일을 여러 모델에서 반복해서 쓰기 위한 공통 부모 모델
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        abstract = True
