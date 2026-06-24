from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User, UserProfile

from .models import PersonalColorAnalysis
from .exceptions import AnalysisProviderUnavailableError


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


def make_image_file(
    name="face.jpg",
    size=(512, 512),
    image_format="JPEG",
    color=(200, 120, 100),
    content_type=None,
):
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format=image_format)
    buffer.seek(0)
    extension = image_format.lower()
    if extension == "jpeg":
        extension = "jpg"
    filename = name if name else f"sample.{extension}"
    mime_type = content_type or f"image/{'jpeg' if image_format == 'JPEG' else image_format.lower()}"
    return SimpleUploadedFile(filename, buffer.getvalue(), content_type=mime_type)


@override_settings(PERSONAL_COLOR_PROVIDER="mock")
class PersonalColorAnalysisApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
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

    def login(self, user):
        self.client.force_login(user)

    def post_analysis(self, image_file=None, extra_data=None):
        payload = {}
        if image_file is not None:
            payload["image"] = image_file
        if extra_data:
            payload.update(extra_data)
        return self.client.post(
            "/api/personal-color/analyses/",
            payload,
            format="multipart",
        )

    def test_anonymous_user_cannot_create_analysis(self):
        response = self.post_analysis(make_image_file())

        self.assertIn(response.status_code, [401, 403])
        self.assertEqual(PersonalColorAnalysis.objects.count(), 0)

    def test_anonymous_user_cannot_list_analyses(self):
        response = self.client.get("/api/personal-color/analyses/")

        self.assertIn(response.status_code, [401, 403])

    def test_creates_analysis_for_authenticated_user(self):
        self.login(self.alice)

        response = self.post_analysis(make_image_file())

        self.assertEqual(response.status_code, 201)
        self.assertEqual(PersonalColorAnalysis.objects.count(), 1)
        analysis = PersonalColorAnalysis.objects.first()
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.user, self.alice)
        self.assertEqual(response.data["id"], analysis.id)
        self.assertEqual(response.data["result_label"], analysis.get_result_type_display())

    def test_request_user_is_used_even_if_client_sends_user_id(self):
        self.login(self.alice)

        response = self.post_analysis(
            make_image_file(),
            extra_data={"user": self.bob.id},
        )

        self.assertEqual(response.status_code, 201)
        analysis = PersonalColorAnalysis.objects.get(pk=response.data["id"])
        self.assertEqual(analysis.user, self.alice)

    def test_multiple_analyses_can_be_saved(self):
        self.login(self.alice)

        first = self.post_analysis(make_image_file(name="spring.jpg", color=(240, 180, 120)))
        second = self.post_analysis(make_image_file(name="winter.jpg", color=(90, 90, 180)))

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(PersonalColorAnalysis.objects.filter(user=self.alice).count(), 2)

    def test_list_does_not_expose_other_users_records(self):
        first = PersonalColorAnalysis.objects.create(
            user=self.alice,
            result_type=PersonalColorAnalysis.ResultType.SPRING_WARM,
            result_subtype="브라이트",
            confidence=86.4,
            summary="summary",
            best_colors=[{"name": "코랄", "hex": "#F49A8A", "reason": "good"}],
            avoid_colors=[{"name": "네이비", "hex": "#233554", "reason": "bad"}],
            recommendations={"clothing": [], "makeup": [], "accessories": []},
            analysis_metrics={"warmth": 0.8, "brightness": 0.7, "saturation": 0.6, "contrast": 0.5},
            provider_name="mock",
            model_version="mock-v1",
        )
        PersonalColorAnalysis.objects.create(
            user=self.bob,
            result_type=PersonalColorAnalysis.ResultType.WINTER_COOL,
            result_subtype="트루",
            confidence=91.2,
            summary="summary",
            best_colors=[{"name": "화이트", "hex": "#FFFFFF", "reason": "good"}],
            avoid_colors=[{"name": "베이지", "hex": "#E2C8AA", "reason": "bad"}],
            recommendations={"clothing": [], "makeup": [], "accessories": []},
            analysis_metrics={"warmth": 0.2, "brightness": 0.6, "saturation": 0.8, "contrast": 0.7},
            provider_name="mock",
            model_version="mock-v1",
        )
        self.login(self.alice)

        response = self.client.get("/api/personal-color/analyses/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual([item["id"] for item in response.data["results"]], [first.id])

    def test_detail_does_not_allow_other_users_records(self):
        analysis = PersonalColorAnalysis.objects.create(
            user=self.bob,
            result_type=PersonalColorAnalysis.ResultType.WINTER_COOL,
            result_subtype="트루",
            confidence=91.2,
            summary="summary",
            best_colors=[{"name": "화이트", "hex": "#FFFFFF", "reason": "good"}],
            avoid_colors=[{"name": "베이지", "hex": "#E2C8AA", "reason": "bad"}],
            recommendations={"clothing": [], "makeup": [], "accessories": []},
            analysis_metrics={"warmth": 0.2, "brightness": 0.6, "saturation": 0.8, "contrast": 0.7},
            provider_name="mock",
            model_version="mock-v1",
        )
        self.login(self.alice)

        response = self.client.get(f"/api/personal-color/analyses/{analysis.id}/")

        self.assertEqual(response.status_code, 404)

    def test_delete_does_not_allow_other_users_records(self):
        analysis = PersonalColorAnalysis.objects.create(
            user=self.bob,
            result_type=PersonalColorAnalysis.ResultType.WINTER_COOL,
            result_subtype="트루",
            confidence=91.2,
            summary="summary",
            best_colors=[{"name": "화이트", "hex": "#FFFFFF", "reason": "good"}],
            avoid_colors=[{"name": "베이지", "hex": "#E2C8AA", "reason": "bad"}],
            recommendations={"clothing": [], "makeup": [], "accessories": []},
            analysis_metrics={"warmth": 0.2, "brightness": 0.6, "saturation": 0.8, "contrast": 0.7},
            provider_name="mock",
            model_version="mock-v1",
        )
        self.login(self.alice)

        response = self.client.delete(f"/api/personal-color/analyses/{analysis.id}/")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(PersonalColorAnalysis.objects.filter(pk=analysis.id).exists())

    def test_latest_records_appear_first(self):
        self.login(self.alice)
        first = self.post_analysis(make_image_file(name="first.jpg", color=(220, 160, 120)))
        second = self.post_analysis(make_image_file(name="second.jpg", color=(80, 120, 220)))

        PersonalColorAnalysis.objects.filter(pk=first.data["id"]).update(
            created_at=timezone.now() - timezone.timedelta(minutes=5)
        )
        PersonalColorAnalysis.objects.filter(pk=second.data["id"]).update(
            created_at=timezone.now()
        )

        response = self.client.get("/api/personal-color/analyses/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["id"], second.data["id"])

    def test_missing_image_returns_400(self):
        self.login(self.alice)

        response = self.post_analysis()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "image_required")
        self.assertEqual(PersonalColorAnalysis.objects.count(), 0)

    def test_unsupported_format_returns_400(self):
        self.login(self.alice)
        file = SimpleUploadedFile(
            "face.bmp",
            b"not-a-valid-bmp",
            content_type="image/bmp",
        )

        response = self.post_analysis(file)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "unsupported_image_type")
        self.assertEqual(PersonalColorAnalysis.objects.count(), 0)

    def test_size_over_ten_mb_is_blocked(self):
        self.login(self.alice)
        file = SimpleUploadedFile(
            "big.jpg",
            b"0" * (10 * 1024 * 1024 + 1),
            content_type="image/jpeg",
        )

        response = self.post_analysis(file)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "file_too_large")
        self.assertEqual(PersonalColorAnalysis.objects.count(), 0)

    def test_corrupted_image_is_blocked(self):
        self.login(self.alice)
        file = SimpleUploadedFile(
            "broken.jpg",
            b"this-is-not-an-image",
            content_type="image/jpeg",
        )

        response = self.post_analysis(file)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "corrupted_image")
        self.assertEqual(PersonalColorAnalysis.objects.count(), 0)

    def test_provider_failure_does_not_create_record(self):
        self.login(self.alice)

        with patch("personal_color.services.get_personal_color_provider") as mocked_provider:
            provider = mocked_provider.return_value
            provider.analyze.side_effect = AnalysisProviderUnavailableError(
                "AI 분석 제공자를 사용할 수 없습니다.",
                code="analysis_provider_unavailable",
            )

            response = self.post_analysis(make_image_file())

        self.assertEqual(response.status_code, 503)
        self.assertEqual(PersonalColorAnalysis.objects.count(), 0)

    def test_production_without_provider_returns_503_and_skips_save(self):
        self.login(self.alice)

        with override_settings(DEBUG=False, PERSONAL_COLOR_PROVIDER=""):
            with patch.dict("os.environ", {}, clear=True):
                response = self.post_analysis(make_image_file())

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "analysis_provider_unavailable")
        self.assertEqual(PersonalColorAnalysis.objects.count(), 0)

    def test_result_json_structure_is_valid(self):
        self.login(self.alice)

        response = self.post_analysis(make_image_file())

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            set(response.data.keys()),
            {
                "id",
                "result_type",
                "result_label",
                "result_subtype",
                "confidence",
                "summary",
                "best_colors",
                "avoid_colors",
                "recommendations",
                "analysis_metrics",
                "provider_name",
                "model_version",
                "created_at",
            },
        )
        self.assertIsInstance(response.data["best_colors"], list)
        self.assertTrue(response.data["best_colors"])
        self.assertEqual(
            set(response.data["best_colors"][0].keys()),
            {"name", "hex", "reason"},
        )
        self.assertEqual(
            set(response.data["recommendations"].keys()),
            {"clothing", "makeup", "accessories"},
        )
        self.assertEqual(
            set(response.data["analysis_metrics"].keys()),
            {"warmth", "brightness", "saturation", "contrast"},
        )

    def test_delete_removes_record_from_current_users_list(self):
        self.login(self.alice)
        response = self.post_analysis(make_image_file())
        analysis_id = response.data["id"]

        delete_response = self.client.delete(
            f"/api/personal-color/analyses/{analysis_id}/"
        )

        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(
            PersonalColorAnalysis.objects.filter(user=self.alice, pk=analysis_id).exists()
        )

        list_response = self.client.get("/api/personal-color/analyses/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 0)
