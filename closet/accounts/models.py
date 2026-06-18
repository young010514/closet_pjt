from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models

from common.models import TimeStampedModel
from regions.models import Region

from .utils import normalize_account_email


class UserManager(DjangoUserManager):
    """
    프로젝트의 커스텀 User manager.

    Django 기본 UserManager는 이메일 도메인 부분만 소문자로 정규화한다.
    이 프로젝트에서는 이메일 전체를 소문자로 통일하고 이메일 입력을 필수로 한다.
    """

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
    """
    Django 기본 User를 확장한 프로젝트 사용자 모델.

    로그인 식별자는 기존처럼 username을 사용하고,
    email은 모든 회원 유형에서 필수이며 DB 수준에서 중복을 금지한다.
    """

    email = models.EmailField(
        unique=True,
        verbose_name="이메일",
    )

    objects = UserManager()

    # createsuperuser 실행 시 username/password 외에 email도 입력받는다.
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "users"
        verbose_name = "사용자"
        verbose_name_plural = "사용자"

    def clean(self):
        super().clean()
        self.email = User.objects.normalize_email(self.email)

    def save(self, *args, **kwargs):
        # admin, shell 등 serializer를 거치지 않는 저장도 동일하게 정규화한다.
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

    following = models.ManyToManyField(
        "self",
        through="Follow",
        through_fields=("follower", "following"),
        symmetrical=False,
        related_name="followers",
        blank=True,
        verbose_name="팔로잉",
    )

    # 지역은 선택 사항이며 최대 3개까지 UserRegion을 통해 등록한다.
    regions = models.ManyToManyField(
        Region,
        through="UserRegion",
        related_name="user_profiles",
        blank=True,
        verbose_name="선택 지역",
    )

    class Meta:
        db_table = "user_profiles"
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필"

    def __str__(self):
        return f"{self.user.username} - {self.nickname}"


class UserRegion(TimeStampedModel):
    """사용자가 선택한 지역과 우선순위를 저장하는 중간 모델."""

    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="user_regions",
        verbose_name="사용자 프로필",
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="user_regions",
        verbose_name="지역",
    )

    priority = models.PositiveSmallIntegerField(
        verbose_name="지역 우선순위",
    )

    class Meta:
        db_table = "user_regions"
        verbose_name = "사용자 선택 지역"
        verbose_name_plural = "사용자 선택 지역"
        ordering = ["priority"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_profile", "region"],
                name="unique_user_profile_region",
            ),
            models.UniqueConstraint(
                fields=["user_profile", "priority"],
                name="unique_user_profile_region_priority",
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
        return (
            f"{self.user_profile.nickname} - "
            f"{self.region} ({self.priority})"
        )


class Follow(TimeStampedModel):
    follower = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="following_relations",
        verbose_name="팔로우를 건 사용자",
    )

    following = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="follower_relations",
        verbose_name="팔로우 당한 사용자",
    )

    class Meta:
        db_table = "follows"
        verbose_name = "팔로우"
        verbose_name_plural = "팔로우"
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

    def __str__(self):
        return f"{self.follower.nickname} → {self.following.nickname}"


class BusinessProfile(TimeStampedModel):
    """사업자 회원에게만 생성되는 추가 프로필."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_profile",
        verbose_name="사용자",
    )

    # 계정 이메일(User.email)과 별개인 사업장 공개 연락용 이메일이다.
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
        verbose_name="사업장 전화번호",
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
        verbose_name="서비스 이용약관 버전",
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
