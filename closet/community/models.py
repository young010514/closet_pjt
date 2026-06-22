from django.db import models
from django.conf import settings


class Post(models.Model):
    BOARD_CHOICES = [
        ('fashion', '패션 정보 공유'),
        ('daily', '일상 & 소통'),
        ('local_shop', '우리 동네 가게'),
        ('experience', '체험단'),
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
        ('recruit', '체험단 모집'),
        ('review', '체험단 후기'),
    ]

    EXPERIENCE_STATUS_RECRUITING = 'recruiting'
    EXPERIENCE_STATUS_CLOSED = 'closed'
    EXPERIENCE_STATUS_ENDED = 'ended'

    board = models.CharField(max_length=20, choices=BOARD_CHOICES, default='fashion')
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True, default='')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, blank=True, default='')
    hashtags = models.JSONField(default=list, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # 체험단 공통
    store_name = models.CharField(max_length=100, blank=True, default='')

    # 체험단 모집 전용
    store_location = models.CharField(max_length=255, blank=True, default='')
    product_description = models.TextField(blank=True, default='')
    notice = models.TextField(blank=True, default='')
    recruit_start = models.DateField(null=True, blank=True)
    recruit_end = models.DateField(null=True, blank=True)
    experience_end = models.DateField(null=True, blank=True)

    # 체험단 후기 전용
    experience_participation_start = models.DateField(null=True, blank=True)
    experience_participation_end = models.DateField(null=True, blank=True)

    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def experience_status(self):
        if self.board != 'experience' or self.category != 'recruit':
            return None
        from django.utils import timezone
        today = timezone.localdate()
        if self.experience_end and today > self.experience_end:
            return self.EXPERIENCE_STATUS_ENDED
        if self.recruit_end and today > self.recruit_end:
            return self.EXPERIENCE_STATUS_CLOSED
        if self.recruit_start and today >= self.recruit_start:
            return self.EXPERIENCE_STATUS_RECRUITING
        return None

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='post_images/')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.post.title} - image {self.order}'
