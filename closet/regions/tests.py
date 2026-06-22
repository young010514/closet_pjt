from django.test import TestCase
from rest_framework.test import APIClient

from .models import Region


class RegionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        Region.objects.create(
            sido="경기도",
            sigungu="수원시",
            dong="",
            is_active=True,
        )
        Region.objects.create(
            sido="서울특별시",
            sigungu="강남구",
            dong="",
            is_active=True,
        )
        self.dong_1 = Region.objects.create(
            sido="서울특별시",
            sigungu="강남구",
            dong="삼성동",
            is_active=True,
        )
        self.dong_2 = Region.objects.create(
            sido="서울특별시",
            sigungu="강남구",
            dong="역삼동",
            is_active=True,
        )
        Region.objects.create(
            sido="서울특별시",
            sigungu="서초구",
            dong="",
            is_active=True,
        )

    def test_sido_list_returns_distinct_sorted_values(self):
        response = self.client.get("/api/regions/sidos/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sidos"], ["경기도", "서울특별시"])

    def test_sigungu_list_returns_empty_without_query(self):
        response = self.client.get("/api/regions/sigungus/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sigungus"], [])

    def test_dong_list_returns_only_matching_dong_regions(self):
        response = self.client.get(
            "/api/regions/dongs/",
            {"sido": "서울특별시", "sigungu": "강남구"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["regions"]],
            [self.dong_1.id, self.dong_2.id],
        )
        self.assertEqual(
            [item["dong"] for item in response.data["regions"]],
            ["삼성동", "역삼동"],
        )
