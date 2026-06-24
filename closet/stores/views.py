from decimal import Decimal, InvalidOperation

from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import BusinessProfile
from common.pagination import StandardPageNumberPagination
from community.models import Post
from community.serializers import PostSerializer

from .models import Store
from .serializers import StoreListSerializer


ORDERING_MAP = {
    "name": ("name", "branch_name", "id"),
    "view_count": ("-view_count", "name", "id"),
    "-view_count": ("-view_count", "name", "id"),
}


def clean_query_value(value):
    return (value or "").strip()


def parse_bounds(query_params):
    raw_bounds = {
        "min_lat": clean_query_value(query_params.get("min_lat")),
        "max_lat": clean_query_value(query_params.get("max_lat")),
        "min_lng": clean_query_value(query_params.get("min_lng")),
        "max_lng": clean_query_value(query_params.get("max_lng")),
    }

    provided = [bool(value) for value in raw_bounds.values()]
    if not any(provided):
        return None

    if not all(provided):
        raise ValidationError(
            {
                "detail": (
                    "지도 영역 필터는 min_lat, max_lat, min_lng, max_lng를 "
                    "모두 함께 보내야 합니다."
                )
            }
        )

    try:
        bounds = {key: Decimal(value) for key, value in raw_bounds.items()}
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(
            {"detail": "지도 영역 필터 값이 올바르지 않습니다."}
        ) from exc

    if bounds["min_lat"] > bounds["max_lat"] or bounds["min_lng"] > bounds["max_lng"]:
        raise ValidationError(
            {"detail": "지도 영역 필터의 범위가 올바르지 않습니다."}
        )

    return bounds


class StoreListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardPageNumberPagination
    serializer_class = StoreListSerializer

    def get_queryset(self, request):
        queryset = Store.objects.select_related("region").filter(is_active=True)

        search = clean_query_value(request.query_params.get("search"))
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(branch_name__icontains=search)
            )

        sido = clean_query_value(request.query_params.get("sido"))
        sigungu = clean_query_value(request.query_params.get("sigungu"))
        dong = clean_query_value(request.query_params.get("dong"))

        if sido:
            queryset = queryset.filter(region__sido=sido)
        if sigungu:
            queryset = queryset.filter(region__sigungu=sigungu)
        if dong:
            queryset = queryset.filter(region__dong=dong)

        bounds = parse_bounds(request.query_params)
        if bounds:
            queryset = queryset.filter(
                latitude__gte=bounds["min_lat"],
                latitude__lte=bounds["max_lat"],
                longitude__gte=bounds["min_lng"],
                longitude__lte=bounds["max_lng"],
            )

        ordering = clean_query_value(request.query_params.get("ordering")) or "name"
        queryset = queryset.order_by(*ORDERING_MAP.get(ordering, ORDERING_MAP["name"]))

        return queryset

    def get(self, request):
        queryset = self.get_queryset(request)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


store_list = StoreListView.as_view()


class StoreLinkedPostsView(APIView):
    """가게에 연결된 사업자의 local_shop 게시글을 반환한다."""

    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            store = Store.objects.select_related("business_profile__user").get(
                pk=pk, is_active=True
            )
        except Store.DoesNotExist:
            return Response({"posts": []})

        bp = store.business_profile

        if bp is None:
            addresses = [
                a for a in [store.jibun_address, store.road_address] if a.strip()
            ]
            if addresses:
                bp = (
                    BusinessProfile.objects.select_related("user")
                    .filter(address__in=addresses)
                    .first()
                )

        if bp is None:
            return Response({"posts": []})

        posts = (
            Post.objects.filter(author=bp.user, board="local_shop")
            .order_by("-created_at")[:5]
        )
        return Response(
            {"posts": PostSerializer(posts, many=True, context={"request": request}).data}
        )


store_linked_posts = StoreLinkedPostsView.as_view()
