from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import User, UserProfile

from .models import Post
from .views import PostLikeView, PostListCreateView


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


class PostCreatePermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.author = create_user_with_profile(
            "creator",
            "creator@example.com",
            "작성자",
            "01011110099",
        )

    def test_anonymous_post_create_requires_login(self):
        request = self.factory.post(
            "/api/community/posts/",
            {
                "board": "fashion",
                "title": "Guest post",
                "content": "should not be created",
            },
            format="json",
        )

        response = PostListCreateView.as_view()(request)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Post.objects.count(), 0)

    def test_authenticated_post_create_succeeds(self):
        request = self.factory.post(
            "/api/community/posts/",
            {
                "board": "fashion",
                "title": "New post",
                "content": "post body",
            },
            format="json",
        )
        force_authenticate(request, user=self.author)

        response = PostListCreateView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Post.objects.count(), 1)
        post = Post.objects.first()
        self.assertIsNotNone(post)
        self.assertEqual(post.author, self.author)
        self.assertEqual(post.title, "New post")


class PostLikeViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.author = create_user_with_profile(
            "author",
            "author@example.com",
            "작성자",
            "01011110010",
        )
        self.liker = create_user_with_profile(
            "liker",
            "liker@example.com",
            "좋아요유저",
            "01011110011",
        )
        self.post = Post.objects.create(
            author=self.author,
            board="fashion",
            title="Like me",
            content="post content",
        )

    def test_like_toggle_updates_like_count_and_state(self):
        request = self.factory.post(
            f"/api/community/posts/{self.post.id}/like/",
            {},
            format="json",
        )
        force_authenticate(request, user=self.liker)

        response = PostLikeView.as_view()(request, pk=self.post.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_liked"])
        self.assertEqual(response.data["like_count"], 1)

        self.post.refresh_from_db()
        self.assertEqual(self.post.like_count, 1)
        self.assertTrue(self.post.liked_users.filter(pk=self.liker.pk).exists())

        second_request = self.factory.post(
            f"/api/community/posts/{self.post.id}/like/",
            {},
            format="json",
        )
        force_authenticate(second_request, user=self.liker)

        second_response = PostLikeView.as_view()(second_request, pk=self.post.id)

        self.assertEqual(second_response.status_code, 200)
        self.assertFalse(second_response.data["is_liked"])
        self.assertEqual(second_response.data["like_count"], 0)

        self.post.refresh_from_db()
        self.assertEqual(self.post.like_count, 0)
        self.assertFalse(self.post.liked_users.filter(pk=self.liker.pk).exists())
