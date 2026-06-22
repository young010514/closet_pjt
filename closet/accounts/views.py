from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.db import IntegrityError
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    BusinessSignupSerializer,
    CurrentUserSerializer,
    LoginSerializer,
    NormalSignupSerializer,
    SelectedRegionSerializer,
    UserRegionReorderSerializer,
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
