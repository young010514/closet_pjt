from django.db import models
from django.conf import settings


class Post(models.Model):
    BOARD_CHOICES = [
        ('fashion', '패션 정보 공유'),
        ('daily', '일상 & 소통'),
    ]
    GENDER_CHOICES = [
        ('male', '남성'),
        ('female', '여성'),
        ('kids', '키즈'),
    ]
    CATEGORY_CHOICES = [
        ('top', '상의'),
        ('bottom', '하의'),
        ('outer', '아우터'),
        ('shoes', '슈즈'),
        ('accessories', '잡화·악세사리'),
        ('lifestyle', '라이프스타일'),
        ('counseling', '고민·상담'),
    ]

    board = models.CharField(max_length=20, choices=BOARD_CHOICES, default='fashion')
    title = models.CharField(max_length=200)
    content = models.TextField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    hashtags = models.JSONField(default=list, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
