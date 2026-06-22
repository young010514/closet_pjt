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


def get_request_user(serializer):
    request = serializer.context.get("request")

    if request is None or not request.user.is_authenticated:
        raise serializers.ValidationError(
            {"detail": "인증된 사용자가 필요합니다."}
        )

    return request.user


def get_request_profile(serializer):
    request_user = get_request_user(serializer)

    try:
        return request_user.profile
    except UserProfile.DoesNotExist as exc:
        raise serializers.ValidationError(
            {"detail": "사용자 프로필이 존재하지 않습니다."}
        ) from exc


def validate_unique_account_email(value):
    email = normalize_account_email(value)

    if User.objects.filter(email=email).exists():
        raise serializers.ValidationError("이미 사용 중인 이메일입니다.")

    return email


def save_user_regions(user, region_ids):
    """Create UserRegion rows in the given order."""

    if not region_ids:
        return []

    user_regions = [
        UserRegion(
            user=user,
            region_id=region_id,
            priority=priority,
        )
        for priority, region_id in enumerate(region_ids, start=1)
    ]

    return UserRegion.objects.bulk_create(user_regions)


def normalize_legacy_region_item(item):
    if isinstance(item, int):
        return item

    if isinstance(item, str) and item.isdigit():
        return int(item)

    if isinstance(item, dict):
        if item.get("region_id") is not None:
            return item["region_id"]

        region = item.get("region")
        if isinstance(region, dict) and region.get("id") is not None:
            return region["id"]

        if item.get("id") is not None:
            return item["id"]

    raise serializers.ValidationError(
        {"region_ids": "지역 정보 형식이 올바르지 않습니다."}
    )


class RegionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ("id", "sido", "sigungu", "dong")
        read_only_fields = fields


class SelectedRegionSerializer(serializers.ModelSerializer):
    region_id = serializers.IntegerField(source="region.id", read_only=True)
    sido = serializers.CharField(source="region.sido", read_only=True)
    sigungu = serializers.CharField(source="region.sigungu", read_only=True)
    dong = serializers.CharField(source="region.dong", read_only=True)

    class Meta:
        model = UserRegion
        fields = ("id", "region_id", "sido", "sigungu", "dong", "priority")
        read_only_fields = fields


class UserRegionSerializer(serializers.ModelSerializer):
    region_id = serializers.PrimaryKeyRelatedField(
        source="region",
        queryset=Region.objects.filter(is_active=True),
        write_only=True,
    )
    region = RegionSummarySerializer(read_only=True)
    priority = serializers.IntegerField(min_value=1, max_value=3)

    class Meta:
        model = UserRegion
        fields = ("id", "region_id", "region", "priority")
        validators = []

    def validate(self, attrs):
        user = get_request_user(self)

        if self.instance is not None and self.instance.user_id != user.id:
            raise serializers.ValidationError(
                {"detail": "본인의 선택 지역만 수정할 수 있습니다."}
            )

        region = attrs.get("region")
        priority = attrs.get("priority")

        queryset = UserRegion.objects.filter(user=user)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.filter(region=region).exists():
            raise serializers.ValidationError(
                {"region_id": "이미 선택한 지역입니다."}
            )

        if queryset.filter(priority=priority).exists():
            raise serializers.ValidationError(
                {"priority": "이미 사용 중인 우선순위입니다."}
            )

        if self.instance is None and queryset.count() >= 3:
            raise serializers.ValidationError(
                {"region_id": "지역은 최대 3개까지 등록할 수 있습니다."}
            )

        return attrs

    def create(self, validated_data):
        return UserRegion.objects.create(
            user=get_request_user(self),
            **validated_data,
        )


class UserRegionReorderSerializer(serializers.Serializer):
    region_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
        max_length=3,
    )

    def validate_region_ids(self, region_ids):
        if len(region_ids) != len(set(region_ids)):
            raise serializers.ValidationError(
                "같은 지역은 중복 선택할 수 없습니다."
            )

        if not region_ids:
            return region_ids

        existing_region_ids = set(
            Region.objects.filter(
                id__in=region_ids,
                is_active=True,
            ).values_list("id", flat=True)
        )

        if existing_region_ids != set(region_ids):
            raise serializers.ValidationError(
                "존재하지 않거나 비활성화된 지역이 포함되어 있습니다."
            )

        return region_ids

    @transaction.atomic
    def create(self, validated_data):
        request_user = get_request_user(self)
        user = User.objects.select_for_update().get(pk=request_user.pk)
        region_ids = validated_data.get("region_ids", [])

        UserRegion.objects.filter(user=user).delete()
        save_user_regions(user, region_ids)

        return (
            UserRegion.objects.filter(user=user)
            .select_related("region")
            .order_by("priority")
        )


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

    region_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
        write_only=True,
    )

    regions = serializers.ListField(
        child=serializers.JSONField(),
        required=False,
        default=list,
        write_only=True,
    )

    def validate_username(self, value):
        username = value.strip()

        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError("이미 사용 중인 아이디입니다.")

        return username

    def _resolve_region_ids(self, attrs):
        region_ids = list(attrs.get("region_ids") or [])

        if not region_ids:
            region_ids = [
                normalize_legacy_region_item(item)
                for item in attrs.get("regions") or []
            ]

        return [int(region_id) for region_id in region_ids]

    def validate(self, attrs):
        errors = {}

        if attrs["password"] != attrs["password_confirm"]:
            errors["password_confirm"] = "비밀번호가 일치하지 않습니다."

        if not attrs["service_terms_agreed"]:
            errors["service_terms_agreed"] = (
                "서비스 이용약관에 동의해 주세요."
            )

        if not attrs["privacy_agreed"]:
            errors["privacy_agreed"] = (
                "개인정보 수집 및 이용에 동의해 주세요."
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

        region_ids = self._resolve_region_ids(attrs)

        if len(region_ids) < 1:
            errors["region_ids"] = "지역을 최소 1개 선택해 주세요."
        elif len(region_ids) > 3:
            errors["region_ids"] = "지역은 최대 3개까지 선택할 수 있습니다."
        elif len(region_ids) != len(set(region_ids)):
            errors["region_ids"] = "같은 지역은 중복 선택할 수 없습니다."
        else:
            existing_region_ids = set(
                Region.objects.filter(
                    id__in=region_ids,
                    is_active=True,
                ).values_list("id", flat=True)
            )

            if existing_region_ids != set(region_ids):
                errors["region_ids"] = (
                    "존재하지 않거나 비활성화된 지역이 포함되어 있습니다."
                )

        if errors:
            raise serializers.ValidationError(errors)

        attrs["region_ids"] = region_ids
        attrs.pop("regions", None)
        return attrs


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
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")

        return nickname

    def validate_phone(self, value):
        phone = value.strip()

        if UserProfile.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("이미 등록된 전화번호입니다.")

        return phone

    @transaction.atomic
    def create(self, validated_data):
        region_ids = validated_data.pop("region_ids", [])
        validated_data.pop("regions", None)

        terms_data = {
            "service_terms_agreed": validated_data.pop("service_terms_agreed"),
            "privacy_agreed": validated_data.pop("privacy_agreed"),
            "marketing_agreed": validated_data.pop("marketing_agreed"),
        }

        username = validated_data.pop("username")
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        validated_data.pop("password_confirm", None)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        UserProfile.objects.create(
            user=user,
            user_type=UserProfile.USER_TYPE_NORMAL,
            **validated_data,
        )

        TermsAgreement.objects.create(
            user=user,
            **terms_data,
        )

        save_user_regions(user, region_ids)
        return user


class BusinessSignupSerializer(BaseSignupSerializer):
    email = serializers.EmailField()
    business_contact_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        default="",
    )

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
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")

        return nickname

    def validate_business_number(self, value):
        business_number = value.strip()

        if BusinessProfile.objects.filter(
            business_number=business_number
        ).exists():
            raise serializers.ValidationError("이미 등록된 사업자번호입니다.")

        return business_number

    def validate_business_phone(self, value):
        business_phone = value.strip()

        if UserProfile.objects.filter(phone=business_phone).exists():
            raise serializers.ValidationError("이미 등록된 전화번호입니다.")

        return business_phone

    @transaction.atomic
    def create(self, validated_data):
        region_ids = validated_data.pop("region_ids", [])
        validated_data.pop("regions", None)

        terms_data = {
            "service_terms_agreed": validated_data.pop("service_terms_agreed"),
            "privacy_agreed": validated_data.pop("privacy_agreed"),
            "marketing_agreed": validated_data.pop("marketing_agreed"),
        }

        username = validated_data.pop("username")
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        validated_data.pop("password_confirm", None)

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

        UserProfile.objects.create(
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

        save_user_regions(user, region_ids)
        return user


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


class UserProfileSummarySerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    class Meta:
        model = UserProfile
        fields = ("id", "user_id", "username", "nickname", "user_type")
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
        fields = ("id", "follower", "following_profile_id", "following")
        validators = []

    def validate_following_profile_id(self, following_profile):
        follower_profile = get_request_profile(self)

        if follower_profile.pk == following_profile.pk:
            raise serializers.ValidationError("자기 자신은 팔로우할 수 없습니다.")

        if Follow.objects.filter(
            follower=follower_profile,
            following=following_profile,
        ).exists():
            raise serializers.ValidationError("이미 팔로우 중인 사용자입니다.")

        return following_profile

    def create(self, validated_data):
        return Follow.objects.create(
            follower=get_request_profile(self),
            **validated_data,
        )


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
        queryset = profile.regions.select_related("region").order_by("priority")
        return UserRegionSerializer(queryset, many=True, context=self.context).data


class CurrentUserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    business_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "profile", "business_profile")
        read_only_fields = fields

    def get_profile(self, user):
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return None

        return UserProfileDetailSerializer(profile, context=self.context).data

    def get_business_profile(self, user):
        try:
            business_profile = user.business_profile
        except BusinessProfile.DoesNotExist:
            return None

        return BusinessProfileDetailSerializer(
            business_profile,
            context=self.context,
        ).data
