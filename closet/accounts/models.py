from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from regions.models import Region


class UserProfile(TimeStampedModel):
    USER_TYPE_CHOICES = [
        ("normal", "일반 사용자"),
        ("business", "사업자 사용자"),
    ]

    GENDER_CHOICES = [
        ("M", "남성"),
        ("F", "여성"),
        ("N", "선택 안 함"),
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

    real_name = models.CharField(max_length=30, verbose_name="실명")
    nickname = models.CharField(max_length=30, unique=True, verbose_name="닉네임")
    phone = models.CharField(max_length=20, verbose_name="전화번호", unique=True)
    birth_date = models.DateField(null=True, blank=True, verbose_name="생년월일")
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        default="N",
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

    # 지역 최대 3개까지 지정 가능 / ManyToManyField로 지정
    regions = models.ManyToManyField(
        Region,
        through="UserRegion",
        related_name="user_profiles",
        verbose_name="선택 지역",
    )

    class Meta:
        db_table = "user_profiles"
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필"

    def __str__(self):
        return f"{self.user.username} - {self.nickname}"

# 사용자 지역 등록을 위한 model
class UserRegion(TimeStampedModel):
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
        default=1,
        verbose_name="지역 우선순위",
    )

    class Meta:
        db_table = "user_regions"
        verbose_name = "사용자 선택 지역"
        verbose_name_plural = "사용자 선택 지역"
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
                condition=models.Q(priority__gte=1) & models.Q(priority__lte=3),
                name="check_user_region_priority_1_to_3",
            ),
        ]

    def __str__(self):
        return f"{self.user_profile.nickname} - {self.region} ({self.priority})"

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
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_profile",
        verbose_name="사용자",
    )

    business_email = models.EmailField(verbose_name="사업자 이메일")
    business_name = models.CharField(max_length=100, verbose_name="상호명")
    business_number = models.CharField(max_length=30, unique=True, verbose_name="사업자등록번호")
    business_phone = models.CharField(
    max_length=20,
    verbose_name="사업장 전화번호",
    )
    owner_name = models.CharField(max_length=30, verbose_name="대표자명")
    address = models.CharField(max_length=255, blank=True, verbose_name="사업장 주소")


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

    service_terms_agreed = models.BooleanField(default=False, verbose_name="서비스 이용약관 동의")
    privacy_agreed = models.BooleanField(default=False, verbose_name="개인정보 수집 동의")
    marketing_agreed = models.BooleanField(default=False, verbose_name="마케팅 수신 동의")

    service_terms_version = models.CharField(max_length=20, default="v1.0")
    privacy_terms_version = models.CharField(max_length=20, default="v1.0")

    class Meta:
        db_table = "terms_agreements"
        verbose_name = "약관 동의"
        verbose_name_plural = "약관 동의"

    def __str__(self):
        return f"{self.user.username} 약관 동의"