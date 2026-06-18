# accounts/serializers.py

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import (
    validate_password as django_validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from regions.models import Region

from .models import (
    BusinessProfile,
    Follow,
    TermsAgreement,
    UserProfile,
    UserRegion,
)
from .utils import normalize_account_email


User = get_user_model()


# =========================================================
# 공통 함수
# =========================================================


def get_request_profile(serializer):
    """현재 로그인 사용자의 UserProfile을 반환한다."""
    request = serializer.context.get("request")

    if request is None or not request.user.is_authenticated:
        raise serializers.ValidationError(
            {"detail": "인증된 사용자 정보가 필요합니다."}
        )

    try:
        return request.user.profile
    except UserProfile.DoesNotExist:
        raise serializers.ValidationError(
            {"detail": "사용자 프로필이 존재하지 않습니다."}
        )


def create_user_regions(user_profile, regions_data):
    """검증된 지역 목록으로 UserRegion을 생성한다."""
    for item in regions_data:
        UserRegion.objects.create(
            user_profile=user_profile,
            region=item["region"],
            priority=item["priority"],
        )


def validate_unique_account_email(value):
    """계정 이메일을 정규화하고 중복을 사전 검사한다."""
    email = normalize_account_email(value)

    if User.objects.filter(email=email).exists():
        raise serializers.ValidationError(
            "이미 사용 중인 이메일입니다."
        )

    return email


# =========================================================
# 지역 Serializer
# =========================================================


class RegionSummarySerializer(serializers.ModelSerializer):
    """사용자 지역 응답에 포함할 지역 요약 정보."""

    class Meta:
        model = Region
        fields = (
            "id",
            "sido",
            "sigungu",
            "dong",
        )
        read_only_fields = fields


class UserRegionInputSerializer(serializers.Serializer):
    """
    회원가입 시 사용하는 지역 입력 형식.

    요청 예시:
    {
        "region_id": 10,
        "priority": 1
    }
    """

    region_id = serializers.PrimaryKeyRelatedField(
        source="region",
        queryset=Region.objects.all(),
    )

    priority = serializers.IntegerField(
        min_value=1,
        max_value=3,
    )


# =========================================================
# 회원가입 공통 Serializer
# =========================================================


class BaseSignupSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    service_terms_agreed = serializers.BooleanField()
    privacy_agreed = serializers.BooleanField()
    marketing_agreed = serializers.BooleanField(default=False)

    regions = UserRegionInputSerializer(
        many=True,
        default=list,
    )

    def validate_username(self, value):
        username = value.strip()

        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError(
                "이미 사용 중인 아이디입니다."
            )

        return username

    def validate_regions(self, value):
        """
        지역은 최대 3개까지 허용하고,
        지역과 우선순위의 중복을 막는다.
        """
        if len(value) > 3:
            raise serializers.ValidationError(
                "지역은 최대 3개까지 선택할 수 있습니다."
            )

        region_ids = [item["region"].pk for item in value]
        priorities = [item["priority"] for item in value]

        if len(region_ids) != len(set(region_ids)):
            raise serializers.ValidationError(
                "동일한 지역을 중복해서 선택할 수 없습니다."
            )

        if len(priorities) != len(set(priorities)):
            raise serializers.ValidationError(
                "지역 우선순위는 중복될 수 없습니다."
            )

        expected_priorities = list(range(1, len(value) + 1))

        if sorted(priorities) != expected_priorities:
            raise serializers.ValidationError(
                "지역 우선순위는 1부터 순서대로 지정해야 합니다."
            )

        return value

    def validate(self, attrs):
        errors = {}

        if attrs["password"] != attrs["password_confirm"]:
            errors["password_confirm"] = (
                "비밀번호가 일치하지 않습니다."
            )

        if not attrs["service_terms_agreed"]:
            errors["service_terms_agreed"] = (
                "서비스 이용약관에 동의해야 합니다."
            )

        if not attrs["privacy_agreed"]:
            errors["privacy_agreed"] = (
                "개인정보 수집 및 이용에 동의해야 합니다."
            )

        candidate_user = User(
            username=attrs["username"],
            email=attrs.get("email", ""),
        )

        try:
            django_validate_password(
                attrs["password"],
                user=candidate_user,
            )
        except DjangoValidationError as error:
            errors["password"] = list(error.messages)

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


# =========================================================
# 일반 사용자 회원가입
# =========================================================


class NormalSignupSerializer(BaseSignupSerializer):
    email = serializers.EmailField()
    real_name = serializers.CharField(max_length=30)
    nickname = serializers.CharField(max_length=30)
    phone = serializers.CharField(max_length=20)

    birth_date = serializers.DateField(
        required=False,
        allow_null=True,
    )

    gender = serializers.ChoiceField(
        choices=UserProfile.GENDER_CHOICES,
        default=UserProfile.GENDER_UNSELECTED,
    )

    def validate_email(self, value):
        return validate_unique_account_email(value)

    def validate_nickname(self, value):
        nickname = value.strip()

        if UserProfile.objects.filter(nickname=nickname).exists():
            raise serializers.ValidationError(
                "이미 사용 중인 닉네임입니다."
            )

        return nickname

    def validate_phone(self, value):
        phone = value.strip()

        if UserProfile.objects.filter(phone=phone).exists():
            raise serializers.ValidationError(
                "이미 등록된 전화번호입니다."
            )

        return phone

    @transaction.atomic
    def create(self, validated_data):
        regions_data = validated_data.pop("regions", [])

        terms_data = {
            "service_terms_agreed": validated_data.pop(
                "service_terms_agreed"
            ),
            "privacy_agreed": validated_data.pop("privacy_agreed"),
            "marketing_agreed": validated_data.pop(
                "marketing_agreed"
            ),
        }

        username = validated_data.pop("username")
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        validated_data.pop("password_confirm")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        user_profile = UserProfile.objects.create(
            user=user,
            user_type=UserProfile.USER_TYPE_NORMAL,
            **validated_data,
        )

        TermsAgreement.objects.create(
            user=user,
            **terms_data,
        )

        create_user_regions(
            user_profile=user_profile,
            regions_data=regions_data,
        )

        return user


# =========================================================
# 사업자 사용자 회원가입
# =========================================================


class BusinessSignupSerializer(BaseSignupSerializer):
    # 로그인 계정에 저장되는 이메일이며 DB에서 고유값이다.
    email = serializers.EmailField()

    # 공개 연락 이메일이다. 생략하면 계정 이메일을 그대로 사용한다.
    business_contact_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        default="",
    )

    # UserProfile에 저장되는 커뮤니티 활동용 닉네임이다.
    nickname = serializers.CharField(max_length=30)

    business_name = serializers.CharField(max_length=100)
    business_number = serializers.CharField(max_length=30)
    business_phone = serializers.CharField(max_length=20)
    owner_name = serializers.CharField(max_length=30)

    address = serializers.CharField(
        max_length=255,
        allow_blank=True,
        default="",
    )

    def validate_email(self, value):
        return validate_unique_account_email(value)

    def validate_business_contact_email(self, value):
        if not value:
            return ""
        return normalize_account_email(value)

    def validate_nickname(self, value):
        nickname = value.strip()

        if UserProfile.objects.filter(nickname=nickname).exists():
            raise serializers.ValidationError(
                "이미 사용 중인 닉네임입니다."
            )

        return nickname

    def validate_business_number(self, value):
        business_number = value.strip()

        if BusinessProfile.objects.filter(
            business_number=business_number
        ).exists():
            raise serializers.ValidationError(
                "이미 등록된 사업자등록번호입니다."
            )

        return business_number

    def validate_business_phone(self, value):
        business_phone = value.strip()

        # 사업자 전화번호를 UserProfile.phone에도 저장하므로
        # UserProfile의 unique 제약조건을 사전 검사한다.
        if UserProfile.objects.filter(phone=business_phone).exists():
            raise serializers.ValidationError(
                "이미 등록된 전화번호입니다."
            )

        return business_phone

    @transaction.atomic
    def create(self, validated_data):
        regions_data = validated_data.pop("regions", [])

        terms_data = {
            "service_terms_agreed": validated_data.pop(
                "service_terms_agreed"
            ),
            "privacy_agreed": validated_data.pop("privacy_agreed"),
            "marketing_agreed": validated_data.pop(
                "marketing_agreed"
            ),
        }

        username = validated_data.pop("username")
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        validated_data.pop("password_confirm")

        nickname = validated_data.pop("nickname")
        business_contact_email = validated_data.pop(
            "business_contact_email"
        ) or email

        business_profile_data = {
            "business_contact_email": business_contact_email,
            "business_name": validated_data.pop("business_name"),
            "business_number": validated_data.pop("business_number"),
            "business_phone": validated_data.pop("business_phone"),
            "owner_name": validated_data.pop("owner_name"),
            "address": validated_data.pop("address"),
        }

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        user_profile = UserProfile.objects.create(
            user=user,
            user_type=UserProfile.USER_TYPE_BUSINESS,
            real_name=business_profile_data["owner_name"],
            nickname=nickname,
            phone=business_profile_data["business_phone"],
            gender=UserProfile.GENDER_UNSELECTED,
        )

        BusinessProfile.objects.create(
            user=user,
            **business_profile_data,
        )

        TermsAgreement.objects.create(
            user=user,
            **terms_data,
        )

        create_user_regions(
            user_profile=user_profile,
            regions_data=regions_data,
        )

        return user


# =========================================================
# 로그인
# =========================================================


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )

        if user is None:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "아이디 또는 비밀번호가 올바르지 않습니다."
                    )
                }
            )

        return {"user": user}


# =========================================================
# 사용자 지역 등록·조회·수정용 Serializer
# =========================================================


class UserRegionSerializer(serializers.ModelSerializer):
    region_id = serializers.PrimaryKeyRelatedField(
        source="region",
        queryset=Region.objects.all(),
        write_only=True,
    )

    region = RegionSummarySerializer(read_only=True)

    priority = serializers.IntegerField(
        min_value=1,
        max_value=3,
    )

    class Meta:
        model = UserRegion
        fields = (
            "id",
            "region_id",
            "region",
            "priority",
        )
        validators = []

    def validate(self, attrs):
        user_profile = get_request_profile(self)

        if (
            self.instance is not None
            and self.instance.user_profile_id != user_profile.id
        ):
            raise serializers.ValidationError(
                {
                    "detail": (
                        "본인에게 등록된 지역만 수정할 수 있습니다."
                    )
                }
            )

        region = attrs.get(
            "region",
            self.instance.region if self.instance is not None else None,
        )

        priority = attrs.get(
            "priority",
            self.instance.priority if self.instance is not None else None,
        )

        queryset = UserRegion.objects.filter(
            user_profile=user_profile
        )

        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if self.instance is None and queryset.count() >= 3:
            raise serializers.ValidationError(
                {
                    "region_id": (
                        "지역은 최대 3개까지 등록할 수 있습니다."
                    )
                }
            )

        if queryset.filter(region=region).exists():
            raise serializers.ValidationError(
                {"region_id": "이미 등록된 지역입니다."}
            )

        if queryset.filter(priority=priority).exists():
            raise serializers.ValidationError(
                {"priority": "이미 사용 중인 우선순위입니다."}
            )

        return attrs

    def create(self, validated_data):
        return UserRegion.objects.create(
            user_profile=get_request_profile(self),
            **validated_data,
        )


class UserRegionReorderSerializer(serializers.Serializer):
    """
    등록된 지역 전체를 region_id 순서로 받아 priority를 재배치한다.

    요청 예시:
    {
        "region_ids": [30, 10, 20]
    }
    """

    region_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=3,
    )

    def validate_region_ids(self, region_ids):
        if len(region_ids) != len(set(region_ids)):
            raise serializers.ValidationError(
                "동일한 지역을 중복해서 전달할 수 없습니다."
            )

        user_profile = get_request_profile(self)

        saved_region_ids = list(
            UserRegion.objects.filter(
                user_profile=user_profile
            ).values_list("region_id", flat=True)
        )

        if (
            len(region_ids) != len(saved_region_ids)
            or set(region_ids) != set(saved_region_ids)
        ):
            raise serializers.ValidationError(
                "현재 등록된 지역 전체를 순서대로 전달해야 합니다."
            )

        return region_ids

    @transaction.atomic
    def create(self, validated_data):
        request_profile = get_request_profile(self)

        # 지원되는 DB에서는 동일 사용자에 대한 동시 순서 변경을 막는다.
        user_profile = (
            UserProfile.objects.select_for_update()
            .get(pk=request_profile.pk)
        )

        region_ids = validated_data["region_ids"]

        current_region_ids = list(
            UserRegion.objects.filter(
                user_profile=user_profile
            ).values_list("region_id", flat=True)
        )

        if (
            len(region_ids) != len(current_region_ids)
            or set(region_ids) != set(current_region_ids)
        ):
            raise serializers.ValidationError(
                {
                    "region_ids": (
                        "지역 정보가 변경되었습니다. "
                        "목록을 다시 조회한 뒤 시도해 주세요."
                    )
                }
            )

        # 1↔2처럼 priority를 교환할 때 중간 UNIQUE 충돌이 생기므로
        # 연결 행을 트랜잭션 안에서 재생성한다.
        UserRegion.objects.filter(
            user_profile=user_profile
        ).delete()

        for priority, region_id in enumerate(region_ids, start=1):
            UserRegion.objects.create(
                user_profile=user_profile,
                region_id=region_id,
                priority=priority,
            )

        return list(
            UserRegion.objects.filter(
                user_profile=user_profile
            )
            .select_related("region")
            .order_by("priority")
        )


# =========================================================
# 팔로우용 Serializer
# =========================================================


class UserProfileSummarySerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)

    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    class Meta:
        model = UserProfile
        fields = (
            "id",
            "user_id",
            "username",
            "nickname",
            "user_type",
        )
        read_only_fields = fields


class FollowSerializer(serializers.ModelSerializer):
    follower = UserProfileSummarySerializer(read_only=True)

    following_profile_id = serializers.PrimaryKeyRelatedField(
        source="following",
        queryset=UserProfile.objects.select_related("user").all(),
        write_only=True,
    )

    following = UserProfileSummarySerializer(read_only=True)

    class Meta:
        model = Follow
        fields = (
            "id",
            "follower",
            "following_profile_id",
            "following",
        )
        validators = []

    def validate_following_profile_id(self, following_profile):
        follower_profile = get_request_profile(self)

        if follower_profile.pk == following_profile.pk:
            raise serializers.ValidationError(
                "자기 자신을 팔로우할 수 없습니다."
            )

        if Follow.objects.filter(
            follower=follower_profile,
            following=following_profile,
        ).exists():
            raise serializers.ValidationError(
                "이미 팔로우 중인 사용자입니다."
            )

        return following_profile

    def create(self, validated_data):
        return Follow.objects.create(
            follower=get_request_profile(self),
            **validated_data,
        )


# =========================================================
# 사용자 응답용 Serializer
# =========================================================


class BusinessProfileDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = (
            "business_contact_email",
            "business_name",
            "business_number",
            "business_phone",
            "owner_name",
            "address",
        )
        read_only_fields = fields


class UserProfileDetailSerializer(serializers.ModelSerializer):
    regions = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = (
            "id",
            "user_type",
            "real_name",
            "nickname",
            "phone",
            "birth_date",
            "gender",
            "regions",
        )
        read_only_fields = fields

    def get_regions(self, profile):
        queryset = (
            profile.user_regions.select_related("region")
            .order_by("priority")
        )
        return UserRegionSerializer(queryset, many=True).data


class CurrentUserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    business_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "profile",
            "business_profile",
        )
        read_only_fields = fields

    def get_profile(self, user):
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return None

        return UserProfileDetailSerializer(profile).data

    def get_business_profile(self, user):
        try:
            business_profile = user.business_profile
        except BusinessProfile.DoesNotExist:
            return None

        return BusinessProfileDetailSerializer(
            business_profile
        ).data
