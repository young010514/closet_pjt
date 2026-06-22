from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Region
from .serializers import RegionSerializer


def active_regions():
    return Region.objects.filter(is_active=True)


class SidoListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        sidos = list(
            active_regions()
            .order_by("sido")
            .values_list("sido", flat=True)
            .distinct()
        )

        return Response({"sidos": sidos}, status=status.HTTP_200_OK)


class SigunguListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        sido = (request.query_params.get("sido") or "").strip()
        if not sido:
            return Response({"sigungus": []}, status=status.HTTP_200_OK)

        sigungus = list(
            active_regions()
            .filter(sido=sido)
            .order_by("sigungu")
            .values_list("sigungu", flat=True)
            .distinct()
        )

        return Response({"sigungus": sigungus}, status=status.HTTP_200_OK)


class DongListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        sido = (request.query_params.get("sido") or "").strip()
        sigungu = (request.query_params.get("sigungu") or "").strip()

        if not sido or not sigungu:
            return Response({"regions": []}, status=status.HTTP_200_OK)

        queryset = (
            active_regions()
            .filter(sido=sido, sigungu=sigungu)
            .exclude(dong="")
            .exclude(dong__isnull=True)
            .order_by("dong", "id")
        )

        return Response(
            {"regions": RegionSerializer(queryset, many=True).data},
            status=status.HTTP_200_OK,
        )
