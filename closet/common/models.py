from django.db import models
from django.utils import timezone

# Create your models here.

# 생성일, 수정일을 여러 모델에서 반복해서 쓰기 위한 공통 부모 모델
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        abstract = True

# db에서 실제 삭제하지 않고 숨기는 방식
class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, verbose_name="삭제 여부")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="삭제일")

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])

# 활성/비활성이 필요한 모델에서 활용
class ActiveModel(models.Model):
    is_active = models.BooleanField(default=True, verbose_name="활성화 여부")

    class Meta:
        abstract = True