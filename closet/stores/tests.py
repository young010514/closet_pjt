from django.test import TestCase
from rest_framework.test import APIClient

from regions.models import Region

from .models import Store


class StoreListApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.region_1 = Region.objects.create(
            sido="서울특별시",
            sigungu="종로구",
            dong="사직동",
            is_active=True,
        )
        self.region_2 = Region.objects.create(
            sido="서울특별시",
            sigungu="종로구",
            dong="삼청동",
            is_active=True,
        )
        self.region_3 = Region.objects.create(
            sido="경기도",
            sigungu="수원시",
            dong="팔달동",
            is_active=True,
        )

        self.store_1 = Store.objects.create(
            external_store_id="store-1",
            name="가나옷가게",
            branch_name="",
            category_code="G20902",
            category_name="여성 의류 소매업",
            region=self.region_1,
            jibun_address="서울특별시 종로구 사직동 1",
            road_address="서울특별시 종로구 세종대로 1",
            longitude=126.9666432,
            latitude=37.5658574,
            phone="02-000-0001",
            website_url="",
            data_source="fixture",
            view_count=5,
        )
        self.store_2 = Store.objects.create(
            external_store_id="store-2",
            name="가나옷가게",
            branch_name="종로점",
            category_code="G20905",
            category_name="기타 의류 소매업",
            region=self.region_2,
            jibun_address="서울특별시 종로구 삼청동 2",
            road_address="서울특별시 종로구 삼청로 2",
            longitude=126.9623508,
            latitude=37.5708566,
            phone="02-000-0002",
            website_url="",
            data_source="fixture",
            view_count=20,
        )
        self.store_3 = Store.objects.create(
            external_store_id="store-3",
            name="다라마켓",
            branch_name="",
            category_code="G20901",
            category_name="남성 의류 소매업",
            region=self.region_1,
            jibun_address="서울특별시 종로구 사직동 3",
            road_address="서울특별시 종로구 세종대로 3",
            longitude=126.9591957,
            latitude=37.606688,
            phone="02-000-0003",
            website_url="",
            data_source="fixture",
            view_count=1,
        )
        Store.objects.create(
            external_store_id="store-4",
            name="비활성가게",
            branch_name="",
            category_code="G20901",
            category_name="남성 의류 소매업",
            region=self.region_3,
            jibun_address="경기도 수원시 팔달동 4",
            road_address="경기도 수원시 팔달로 4",
            longitude=127.0000000,
            latitude=37.2000000,
            phone="02-000-0004",
            website_url="",
            data_source="fixture",
            is_active=False,
            view_count=99,
        )

    def test_returns_paginated_results(self):
        response = self.client.get("/api/stores/", {"page_size": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(response.data["page"], 1)
        self.assertEqual(response.data["page_size"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_filters_by_region_exact_match(self):
        response = self.client.get(
            "/api/stores/",
            {
                "sido": "서울특별시",
                "sigungu": "종로구",
                "dong": "삼청동",
                "page_size": 20,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.store_2.id])

    def test_search_matches_name_and_branch_name(self):
        branch_response = self.client.get(
            "/api/stores/",
            {"search": "종로", "page_size": 20},
        )
        name_response = self.client.get(
            "/api/stores/",
            {"search": "다라", "page_size": 20},
        )

        self.assertEqual(branch_response.status_code, 200)
        self.assertEqual([item["id"] for item in branch_response.data["results"]], [self.store_2.id])
        self.assertEqual(name_response.status_code, 200)
        self.assertEqual([item["id"] for item in name_response.data["results"]], [self.store_3.id])

    def test_orders_by_view_count_descending(self):
        response = self.client.get(
            "/api/stores/",
            {"ordering": "view_count", "page_size": 20},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [self.store_2.id, self.store_1.id, self.store_3.id],
        )

    def test_supports_map_bounds_filtering(self):
        response = self.client.get(
            "/api/stores/",
            {
                "min_lat": "37.5700",
                "max_lat": "37.5710",
                "min_lng": "126.9620",
                "max_lng": "126.9630",
                "page_size": 20,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.store_2.id])

    def test_rejects_partial_bounds(self):
        response = self.client.get(
            "/api/stores/",
            {
                "min_lat": "37.5700",
                "page_size": 20,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_view_count_defaults_to_zero(self):
        store = Store.objects.create(
            external_store_id="store-5",
            name="새가게",
            branch_name="",
            category_code="G20905",
            category_name="기타 의류 소매업",
            region=self.region_1,
            jibun_address="서울특별시 종로구 사직동 5",
            road_address="서울특별시 종로구 세종대로 5",
            longitude=126.9600000,
            latitude=37.5600000,
            phone="02-000-0005",
            website_url="",
            data_source="fixture",
        )

        self.assertEqual(store.view_count, 0)

    def test_legacy_list_path_still_responds(self):
        response = self.client.get("/api/stores/list/", {"page_size": 20})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)

