from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Case
from django.db.models import Count
from django.db.models import IntegerField
from django.db.models import Q
from django.db.models import Value
from django.db.models import When
from django.db.models.functions import Lower
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPageNumberPagination

from .serializers import (
    BusinessSignupSerializer,
    CurrentUserSerializer,
    LoginSerializer,
    NormalSignupSerializer,
    PublicUserSerializer,
    SelectedRegionSerializer,
    UpdateBusinessProfileSerializer,
    UpdateProfileSerializer,
    UserRegionReorderSerializer,
)
from .models import Follow


User = get_user_model()
MAX_PUBLIC_USER_SEARCH_LENGTH = 100


SIGNUP_CONFLICT_RESPONSE = {
    "detail": (
        "이미 사용 중인 회원 정보가 있습니다. "
        "아이디, 이메일, 닉네임, 전화번호 등을 확인해 주세요."
    )
}


@api_view(["GET"])
@permission_classes([AllowAny])
def csrf_token(request):
    """Expose a CSRF token for the Vue frontend."""

    return Response(
        {"csrfToken": get_token(request)},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def signup_select(request):
    return Response(
        {
            "signup_types": [
                {
                    "type": "normal",
                    "label": "일반 회원",
                    "endpoint": "/api/accounts/signup/normal/",
                },
                {
                    "type": "business",
                    "label": "사업자 회원",
                    "endpoint": "/api/accounts/signup/business/",
                },
            ]
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def normal_signup(request):
    serializer = NormalSignupSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    try:
        user = serializer.save()
    except IntegrityError:
        return Response(
            SIGNUP_CONFLICT_RESPONSE,
            status=status.HTTP_409_CONFLICT,
        )

    auth_login(request, user)

    return Response(
        {
            "message": "일반 회원가입이 완료되었습니다.",
            "user": CurrentUserSerializer(user, context={"request": request}).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def business_signup(request):
    serializer = BusinessSignupSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    try:
        user = serializer.save()
    except IntegrityError:
        return Response(
            SIGNUP_CONFLICT_RESPONSE,
            status=status.HTTP_409_CONFLICT,
        )

    auth_login(request, user)

    return Response(
        {
            "message": "사업자 회원가입이 완료되었습니다.",
            "user": CurrentUserSerializer(user, context={"request": request}).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def login_view(request):
    serializer = LoginSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    user = serializer.validated_data["user"]
    auth_login(request, user)

    return Response(
        {
            "message": "로그인 성공",
            "user": CurrentUserSerializer(user, context={"request": request}).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    auth_logout(request)

    return Response(
        {"message": "로그아웃되었습니다."},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mypage(request):
    return Response(
        CurrentUserSerializer(request.user, context={"request": request}).data,
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@csrf_protect
def update_profile(request):
    try:
        profile = request.user.profile
    except Exception:
        return Response({"detail": "프로필이 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

    serializer = UpdateProfileSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.update(profile, serializer.validated_data)

    return Response(
        CurrentUserSerializer(request.user, context={"request": request}).data,
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@csrf_protect
def update_business_profile(request):
    try:
        business_profile = request.user.business_profile
    except Exception:
        return Response({"detail": "사업자 프로필이 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

    serializer = UpdateBusinessProfileSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.update(business_profile, serializer.validated_data)

    return Response(
        CurrentUserSerializer(request.user, context={"request": request}).data,
        status=status.HTTP_200_OK,
    )


class MyRegionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = (
            request.user.selected_regions.select_related("region")
            .order_by("priority")
        )
        return Response(
            {"regions": SelectedRegionSerializer(queryset, many=True).data},
            status=status.HTTP_200_OK,
        )

    def put(self, request):
        serializer = UserRegionReorderSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        regions = serializer.save()
        return Response(
            {
                "message": "선택 지역이 저장되었습니다.",
                "regions": SelectedRegionSerializer(
                    regions,
                    many=True,
                ).data,
            },
            status=status.HTTP_200_OK,
        )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def reorder_user_regions(request):
    serializer = UserRegionReorderSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    regions = serializer.save()
    return Response(
        {
            "message": "선택 지역이 저장되었습니다.",
            "regions": SelectedRegionSerializer(
                regions,
                many=True,
            ).data,
        },
        status=status.HTTP_200_OK,
    )


def build_public_user_queryset(queryset):
    return queryset.select_related("profile").annotate(
        follower_count=Count("followers", distinct=True),
        following_count=Count("following", distinct=True),
    )


def build_public_user_search_queryset(queryset, search_term):
    if not search_term:
        return queryset.none()

    if len(search_term) > MAX_PUBLIC_USER_SEARCH_LENGTH:
        raise ValidationError(
            {"q": "검색어는 100자 이내로 입력해 주세요."}
        )

    search_filter = Q(username__icontains=search_term) | Q(
        profile__nickname__icontains=search_term
    )
    exact_filter = Q(username__iexact=search_term) | Q(
        profile__nickname__iexact=search_term
    )
    prefix_filter = Q(username__istartswith=search_term) | Q(
        profile__nickname__istartswith=search_term
    )

    queryset = build_public_user_queryset(
        queryset.filter(
            is_active=True,
            profile__isnull=False,
        ).filter(search_filter)
    ).distinct()

    return queryset.annotate(
        search_rank=Case(
            When(exact_filter, then=Value(0)),
            When(prefix_filter, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        ),
        nickname_sort=Lower("profile__nickname"),
        username_sort=Lower("username"),
    ).order_by("search_rank", "nickname_sort", "username_sort", "id")


def serialize_public_users(request, queryset):
    serializer = PublicUserSerializer(
        queryset,
        many=True,
        context={"request": request},
    )
    return serializer.data


def serialize_public_user(request, user):
    serializer = PublicUserSerializer(
        user,
        context={"request": request},
    )
    return serializer.data


@api_view(["GET"])
@permission_classes([AllowAny])
def user_search(request):
    search_term = (request.query_params.get("q") or "").strip()
    paginator = StandardPageNumberPagination()

    if search_term:
        queryset = build_public_user_search_queryset(User.objects.all(), search_term)
    else:
        queryset = User.objects.none()

    page = paginator.paginate_queryset(queryset, request, view=None)
    return paginator.get_paginated_response(
        serialize_public_users(request, page),
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def user_profile(request, user_id):
    target_user = get_object_or_404(
        build_public_user_queryset(User.objects.all()),
        pk=user_id,
    )

    return Response(
        serialize_public_user(request, target_user),
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_follow(request, user_id):
    target_user = get_object_or_404(
        User.objects.select_related("profile"),
        pk=user_id,
    )

    if target_user.pk == request.user.pk:
        return Response(
            {"detail": "자기 자신은 팔로우할 수 없습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        follow, created = Follow.objects.get_or_create(
            follower=request.user,
            following=target_user,
        )

        if created:
            is_following = True
        else:
            follow.delete()
            is_following = False

    return Response(
        {
            "is_following": is_following,
            "follower_count": target_user.followers.count(),
            "following_count": target_user.following.count(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def user_followers(request, user_id):
    target_user = get_object_or_404(
        User.objects.select_related("profile"),
        pk=user_id,
    )
    queryset = build_public_user_queryset(
        User.objects.filter(following__following=target_user).order_by("username")
    )
    return Response(
        serialize_public_users(request, queryset),
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def user_following(request, user_id):
    target_user = get_object_or_404(
        User.objects.select_related("profile"),
        pk=user_id,
    )
    queryset = build_public_user_queryset(
        User.objects.filter(followers__follower=target_user).order_by("username")
    )
    return Response(
        serialize_public_users(request, queryset),
        status=status.HTTP_200_OK,
    )
