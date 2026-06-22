from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from regions.models import Region

from .models import Follow, User, UserProfile, UserRegion
from .serializers import NormalSignupSerializer
from .views import MyRegionView, mypage, toggle_follow, user_followers, user_following


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


def create_user_with_profile(username, email, nickname, phone, user_type="normal"):
    user = User.objects.create_user(
        username=username,
        email=email,
        password="StrongPass123!",
    )
    UserProfile.objects.create(
        user=user,
        user_type=user_type,
        real_name=f"{username}-real",
        nickname=nickname,
        phone=phone,
        gender=UserProfile.GENDER_UNSELECTED,
    )
    return user


class FollowViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.alice = create_user_with_profile(
            "alice",
            "alice@example.com",
            "앨리스",
            "01011110000",
        )
        self.bob = create_user_with_profile(
            "bob",
            "bob@example.com",
            "밥",
            "01011110001",
        )
        self.charlie = create_user_with_profile(
            "charlie",
            "charlie@example.com",
            "찰리",
            "01011110002",
        )

    def test_toggle_follow_creates_follow_and_updates_counts(self):
        request = self.factory.post(
            f"/api/accounts/users/{self.bob.id}/follow/",
            {},
            format="json",
        )
        force_authenticate(request, user=self.alice)

        response = toggle_follow(request, self.bob.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_following"])
        self.assertEqual(response.data["follower_count"], 1)
        self.assertEqual(response.data["following_count"], 0)
        self.assertTrue(
            Follow.objects.filter(
                follower=self.alice,
                following=self.bob,
            ).exists()
        )

    def test_toggle_follow_again_unfollows(self):
        Follow.objects.create(
            follower=self.alice,
            following=self.bob,
        )

        request = self.factory.post(
            f"/api/accounts/users/{self.bob.id}/follow/",
            {},
            format="json",
        )
        force_authenticate(request, user=self.alice)

        response = toggle_follow(request, self.bob.id)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_following"])
        self.assertEqual(response.data["follower_count"], 0)
        self.assertEqual(response.data["following_count"], 0)
        self.assertFalse(
            Follow.objects.filter(
                follower=self.alice,
                following=self.bob,
            ).exists()
        )

    def test_toggle_follow_rejects_self_follow(self):
        request = self.factory.post(
            f"/api/accounts/users/{self.alice.id}/follow/",
            {},
            format="json",
        )
        force_authenticate(request, user=self.alice)

        response = toggle_follow(request, self.alice.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)

    def test_toggle_follow_returns_404_for_missing_user(self):
        request = self.factory.post(
            "/api/accounts/users/9999/follow/",
            {},
            format="json",
        )
        force_authenticate(request, user=self.alice)

        response = toggle_follow(request, 9999)

        self.assertEqual(response.status_code, 404)

    def test_follow_lists_return_public_users_and_follow_state(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        Follow.objects.create(follower=self.alice, following=self.charlie)
        Follow.objects.create(follower=self.bob, following=self.charlie)

        followers_request = self.factory.get(
            f"/api/accounts/users/{self.charlie.id}/followers/"
        )
        force_authenticate(followers_request, user=self.alice)
        followers_response = user_followers(followers_request, self.charlie.id)

        self.assertEqual(followers_response.status_code, 200)
        self.assertEqual(
            [item["username"] for item in followers_response.data],
            ["alice", "bob"],
        )
        alice_summary = followers_response.data[0]
        bob_summary = followers_response.data[1]
        self.assertFalse(alice_summary["is_following"])
        self.assertTrue(bob_summary["is_following"])
        self.assertIn("profile_image", bob_summary)
        self.assertIn("follower_count", bob_summary)
        self.assertIn("following_count", bob_summary)

        following_request = self.factory.get(
            f"/api/accounts/users/{self.bob.id}/following/"
        )
        force_authenticate(following_request, user=self.alice)
        following_response = user_following(following_request, self.bob.id)

        self.assertEqual(following_response.status_code, 200)
        self.assertEqual(
            [item["username"] for item in following_response.data],
            ["charlie"],
        )
        self.assertTrue(following_response.data[0]["is_following"])

    def test_mypage_profile_includes_follow_counts(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        Follow.objects.create(follower=self.alice, following=self.charlie)

        request = self.factory.get("/api/accounts/mypage/")
        force_authenticate(request, user=self.alice)

        response = mypage(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"]["follower_count"], 0)
        self.assertEqual(response.data["profile"]["following_count"], 2)
        self.assertFalse(response.data["profile"]["is_following"])
