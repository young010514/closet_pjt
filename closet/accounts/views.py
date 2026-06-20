# accounts/views.py

from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

# 안전하지 않은 HTTP 요청에 CSRF 토큰을 포함해야한다고 안내하는 ?
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect

from .serializers import (
    BusinessSignupSerializer,
    CurrentUserSerializer,
    LoginSerializer,
    NormalSignupSerializer,
    UserRegionReorderSerializer,
    UserRegionSerializer,
)


SIGNUP_CONFLICT_RESPONSE = {
    "detail": (
        "이미 사용 중인 회원 정보가 있습니다. "
        "아이디, 이메일, 닉네임, 전화번호 등을 확인해 주세요."
    )
}

@api_view(["GET"])
@permission_classes([AllowAny])
def csrf_token(request):
    """Vue 클라이언트에 CSRF 쿠키와 토큰을 발급한다."""
    return Response(
        {"csrfToken": get_token(request)},
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([AllowAny])
def signup_select(request):
    """회원가입 유형 목록 API."""
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
    """일반 회원가입 API."""
    serializer = NormalSignupSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    try:
        user = serializer.save()
    except IntegrityError:
        # serializer의 사전 중복 검사와 DB INSERT 사이에
        # 동일 값이 동시에 저장된 경우 DB UNIQUE 제약이 최종 차단한다.
        return Response(
            SIGNUP_CONFLICT_RESPONSE,
            status=status.HTTP_409_CONFLICT,
        )

    # 현재는 Django 세션 인증을 사용한다.
    auth_login(request, user)

    return Response(
        {
            "message": "일반 회원가입이 완료되었습니다.",
            "user": CurrentUserSerializer(user).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def business_signup(request):
    """사업자 회원가입 API."""
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
            "user": CurrentUserSerializer(user).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def login_view(request):
    """아이디와 비밀번호를 사용하는 세션 로그인 API."""
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
            "user": CurrentUserSerializer(user).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """현재 세션을 종료하는 로그아웃 API."""
    auth_logout(request)

    return Response(
        {"message": "로그아웃되었습니다."},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mypage(request):
    """현재 로그인 사용자의 계정·프로필·지역 정보를 반환한다."""
    return Response(
        CurrentUserSerializer(request.user).data,
        status=status.HTTP_200_OK,
    )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def reorder_user_regions(request):
    """현재 사용자가 등록한 지역의 우선순위를 일괄 변경한다."""
    serializer = UserRegionReorderSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    user_regions = serializer.save()

    return Response(
        {
            "message": "지역 우선순위가 변경되었습니다.",
            "regions": UserRegionSerializer(
                user_regions,
                many=True,
            ).data,
        },
        status=status.HTTP_200_OK,
    )
