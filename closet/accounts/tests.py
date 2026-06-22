from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from regions.models import Region

from .models import User, UserRegion
from .serializers import NormalSignupSerializer
from .views import MyRegionView


class NormalSignupRegionTests(TestCase):
    def setUp(self):
        self.region_1 = Region.objects.create(
            sido="서울특별시",
            sigungu="강남구",
            dong="역삼동",
            is_active=True,
        )
        self.region_2 = Region.objects.create(
            sido="서울특별시",
            sigungu="서초구",
            dong="반포동",
            is_active=True,
        )

    def test_normal_signup_saves_selected_regions(self):
        serializer = NormalSignupSerializer(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "real_name": "테스터",
                "nickname": "테스터닉",
                "phone": "01012345678",
                "birth_date": "1999-01-01",
                "gender": "N",
                "service_terms_agreed": True,
                "privacy_agreed": True,
                "marketing_agreed": False,
                "region_ids": [self.region_1.id, self.region_2.id],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(
            list(
                user.selected_regions.order_by("priority").values_list(
                    "region_id",
                    flat=True,
                )
            ),
            [self.region_1.id, self.region_2.id],
        )

    def test_normal_signup_rejects_duplicate_region_ids(self):
        serializer = NormalSignupSerializer(
            data={
                "username": "testuser2",
                "email": "test2@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "real_name": "테스터",
                "nickname": "테스터닉2",
                "phone": "01012345679",
                "service_terms_agreed": True,
                "privacy_agreed": True,
                "marketing_agreed": False,
                "region_ids": [self.region_1.id, self.region_1.id],
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("region_ids", serializer.errors)


class MyRegionViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="StrongPass123!",
        )
        self.region_1 = Region.objects.create(
            sido="서울특별시",
            sigungu="강남구",
            dong="역삼동",
            is_active=True,
        )
        self.region_2 = Region.objects.create(
            sido="서울특별시",
            sigungu="서초구",
            dong="반포동",
            is_active=True,
        )
        self.region_3 = Region.objects.create(
            sido="경기도",
            sigungu="수원시",
            dong="매탄동",
            is_active=True,
        )

    def test_get_returns_selected_regions(self):
        UserRegion.objects.create(
            user=self.user,
            region=self.region_1,
            priority=1,
        )
        UserRegion.objects.create(
            user=self.user,
            region=self.region_2,
            priority=2,
        )

        request = self.factory.get("/api/accounts/me/regions/")
        force_authenticate(request, user=self.user)

        response = MyRegionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["region_id"] for item in response.data["regions"]],
            [self.region_1.id, self.region_2.id],
        )

    def test_put_replaces_selected_regions_and_priorities(self):
        UserRegion.objects.create(
            user=self.user,
            region=self.region_1,
            priority=1,
        )

        request = self.factory.put(
            "/api/accounts/me/regions/",
            {"region_ids": [self.region_2.id, self.region_3.id]},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = MyRegionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["region_id"] for item in response.data["regions"]],
            [self.region_2.id, self.region_3.id],
        )
        self.assertEqual(
            list(
                UserRegion.objects.filter(user=self.user)
                .order_by("priority")
                .values_list("region_id", flat=True)
            ),
            [self.region_2.id, self.region_3.id],
        )
        self.assertEqual(
            list(
                UserRegion.objects.filter(user=self.user)
                .order_by("priority")
                .values_list("priority", flat=True)
            ),
            [1, 2],
        )
