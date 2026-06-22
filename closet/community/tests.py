from django.test import TestCase
from rest_framework.test import APIRequestFactory

from accounts.models import User, UserProfile

from .models import Post
from .views import PostListCreateView


def create_user_with_profile(username, email, nickname, phone):
    user = User.objects.create_user(
        username=username,
        email=email,
        password="StrongPass123!",
    )
    UserProfile.objects.create(
        user=user,
        user_type=UserProfile.USER_TYPE_NORMAL,
        real_name=f"{username}-real",
        nickname=nickname,
        phone=phone,
        gender=UserProfile.GENDER_UNSELECTED,
    )
    return user


class PostAuthorFilterTests(TestCase):
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

        self.alice_post_1 = Post.objects.create(
            author=self.alice,
            board="fashion",
            title="Alice post 1",
            content="first",
        )
        self.alice_post_2 = Post.objects.create(
            author=self.alice,
            board="daily",
            title="Alice post 2",
            content="second",
        )
        self.bob_post = Post.objects.create(
            author=self.bob,
            board="fashion",
            title="Bob post",
            content="third",
        )

    def test_post_list_filters_by_author(self):
        request = self.factory.get(f"/api/community/posts/?author={self.alice.id}")

        response = PostListCreateView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            [item["id"] for item in response.data],
            [self.alice_post_1.id, self.alice_post_2.id],
        )
        self.assertTrue(all(item["author"] == self.alice.id for item in response.data))

    def test_post_list_rejects_invalid_author_filter(self):
        request = self.factory.get("/api/community/posts/?author=abc")

        response = PostListCreateView.as_view()(request)

        self.assertEqual(response.status_code, 400)
