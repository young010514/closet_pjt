from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models

from common.models import TimeStampedModel
from regions.models import Region

from .utils import normalize_account_email


class UserManager(DjangoUserManager):
    """Custom user manager used by the project."""

    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        if not email:
            return ""
        return normalize_account_email(email)

    def create_user(self, username, email=None, password=None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")

        return super().create_user(
            username=username,
            email=self.normalize_email(email),
            password=password,
            **extra_fields,
        )

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")

        return super().create_superuser(
            username=username,
            email=self.normalize_email(email),
            password=password,
            **extra_fields,
        )


class User(AbstractUser):
    """Project user model with normalized email uniqueness."""

    email = models.EmailField(
        unique=True,
        verbose_name="이메일",
    )

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "users"
        verbose_name = "사용자"
        verbose_name_plural = "사용자"

    def clean(self):
        super().clean()
        self.email = User.objects.normalize_email(self.email)

    def save(self, *args, **kwargs):
        self.email = User.objects.normalize_email(self.email)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class UserProfile(TimeStampedModel):
    USER_TYPE_NORMAL = "normal"
    USER_TYPE_BUSINESS = "business"

    USER_TYPE_CHOICES = [
        (USER_TYPE_NORMAL, "일반 사용자"),
        (USER_TYPE_BUSINESS, "사업자 사용자"),
    ]

    GENDER_MALE = "M"
    GENDER_FEMALE = "F"
    GENDER_UNSELECTED = "N"

    GENDER_CHOICES = [
        (GENDER_MALE, "남성"),
        (GENDER_FEMALE, "여성"),
        (GENDER_UNSELECTED, "선택 안 함"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="사용자",
    )

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        verbose_name="회원 유형",
    )

    real_name = models.CharField(
        max_length=30,
        verbose_name="실명",
    )

    nickname = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="닉네임",
    )

    phone = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="전화번호",
    )

    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="생년월일",
    )

    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        default=GENDER_UNSELECTED,
        verbose_name="성별",
    )

    class Meta:
        db_table = "user_profiles"
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필"

    @property
    def regions(self):
        """Compatibility accessor for selected regions."""

        if not getattr(self, "user_id", None):
            return UserRegion.objects.none()

        return self.user.selected_regions

    def __str__(self):
        return f"{self.user.username} - {self.nickname}"


class UserRegion(TimeStampedModel):
    """Stores a user's selected region and its priority."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="selected_regions",
        verbose_name="사용자",
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name="user_regions",
        verbose_name="지역",
    )

    priority = models.PositiveIntegerField(
        default=1,
        verbose_name="지역 우선순위",
    )

    class Meta:
        db_table = "user_regions"
        verbose_name = "사용자 선택 지역"
        verbose_name_plural = "사용자 선택 지역"
        ordering = ["priority"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "region"],
                name="unique_user_region",
            ),
            models.UniqueConstraint(
                fields=["user", "priority"],
                name="unique_user_region_priority",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(priority__gte=1)
                    & models.Q(priority__lte=3)
                ),
                name="check_user_region_priority_1_to_3",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.region} ({self.priority})"


class Follow(TimeStampedModel):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",
        verbose_name="팔로우한 사용자",
    )

    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers",
        verbose_name="팔로워 대상 사용자",
    )

    class Meta:
        db_table = "follows"
        verbose_name = "팔로우"
        verbose_name_plural = "팔로우"
        indexes = [
            models.Index(fields=["follower"], name="follow_follower_idx"),
            models.Index(fields=["following"], name="follow_following_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="unique_follow_relation",
            ),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F("following")),
                name="prevent_self_follow",
            ),
        ]

    @staticmethod
    def _display_name(user):
        profile = getattr(user, "profile", None)
        nickname = getattr(profile, "nickname", None)
        return nickname or getattr(user, "username", str(user))

    def __str__(self):
        return (
            f"{self._display_name(self.follower)} -> "
            f"{self._display_name(self.following)}"
        )


class BusinessProfile(TimeStampedModel):
    """Additional profile information for business accounts."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_profile",
        verbose_name="사용자",
    )

    business_contact_email = models.EmailField(
        blank=True,
        default="",
        verbose_name="사업자 연락 이메일",
    )

    business_name = models.CharField(
        max_length=100,
        verbose_name="상호명",
    )

    business_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="사업자등록번호",
    )

    business_phone = models.CharField(
        max_length=20,
        verbose_name="사업자 전화번호",
    )

    owner_name = models.CharField(
        max_length=30,
        verbose_name="대표자명",
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="사업장 주소",
    )

    class Meta:
        db_table = "business_profiles"
        verbose_name = "사업자 프로필"
        verbose_name_plural = "사업자 프로필"

    def __str__(self):
        return self.business_name


class TermsAgreement(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="terms_agreement",
        verbose_name="사용자",
    )

    service_terms_agreed = models.BooleanField(
        default=False,
        verbose_name="서비스 이용약관 동의",
    )

    privacy_agreed = models.BooleanField(
        default=False,
        verbose_name="개인정보 수집 동의",
    )

    marketing_agreed = models.BooleanField(
        default=False,
        verbose_name="마케팅 수신 동의",
    )

    service_terms_version = models.CharField(
        max_length=20,
        default="v1.0",
        verbose_name="서비스 약관 버전",
    )

    privacy_terms_version = models.CharField(
        max_length=20,
        default="v1.0",
        verbose_name="개인정보 처리방침 버전",
    )

    class Meta:
        db_table = "terms_agreements"
        verbose_name = "약관 동의"
        verbose_name_plural = "약관 동의"

    def __str__(self):
        return f"{self.user.username} 약관 동의"
