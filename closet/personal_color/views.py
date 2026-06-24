from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPageNumberPagination

from .exceptions import PersonalColorServiceError
from .models import PersonalColorAnalysis
from .serializers import (
    PersonalColorAnalysisCreateSerializer,
    PersonalColorAnalysisSerializer,
)


def _first_error_text(value):
    if isinstance(value, list) and value:
        return _first_error_text(value[0])
    if isinstance(value, dict) and value:
        return _first_error_text(next(iter(value.values())))
    if value is None:
        return ""
    return str(value)


def validation_error_response(errors):
    detail = ""
    code = "validation_error"

    if isinstance(errors, dict):
        if "detail" in errors:
            detail = _first_error_text(errors["detail"])
        else:
            detail = _first_error_text(next(iter(errors.values()), ""))

        if "code" in errors:
            code = _first_error_text(errors["code"]) or code
    elif isinstance(errors, list):
        detail = _first_error_text(errors)
    else:
        detail = str(errors)

    if not detail:
        detail = "요청을 처리하지 못했습니다."

    return Response(
        {
            "detail": detail,
            "code": code,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def service_error_response(error: PersonalColorServiceError) -> Response:
    return Response(
        {
            "detail": error.message,
            "code": error.code,
        },
        status=error.status_code,
    )


class PersonalColorAnalysisListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = StandardPageNumberPagination

    def get_queryset(self, request):
        return PersonalColorAnalysis.objects.filter(user=request.user).order_by(
            "-created_at"
        )

    def get(self, request):
        paginator = self.pagination_class()
        queryset = self.get_queryset(request)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = PersonalColorAnalysisSerializer(
            page,
            many=True,
            context={"request": request},
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = PersonalColorAnalysisCreateSerializer(
            data=request.data,
            context={"request": request},
        )

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            analysis = serializer.save()
        except PersonalColorServiceError as exc:
            return service_error_response(exc)

        output = PersonalColorAnalysisSerializer(
            analysis,
            context={"request": request},
        )
        return Response(output.data, status=status.HTTP_201_CREATED)


class PersonalColorAnalysisDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        return PersonalColorAnalysis.objects.filter(user=request.user).filter(
            pk=pk
        ).first()

    def get(self, request, pk):
        analysis = self.get_object(request, pk)
        if analysis is None:
            return Response(
                {
                    "detail": "진단 기록을 찾을 수 없습니다.",
                    "code": "analysis_not_found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PersonalColorAnalysisSerializer(
            analysis,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        analysis = self.get_object(request, pk)
        if analysis is None:
            return Response(
                {
                    "detail": "진단 기록을 찾을 수 없습니다.",
                    "code": "analysis_not_found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        analysis.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
