from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User, UserProfile

from .models import PersonalColorAnalysis
from .exceptions import AnalysisFailedError, AnalysisProviderUnavailableError
from .services_VER2 import (
    GmsPersonalColorProvider,
    get_personal_color_provider,
    prepare_uploaded_image,
    validate_normalized_result,
)


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

def make_gms_result(**overrides):
    result = {
        "result_type": "spring_warm",
        "result_subtype": "bright",
        "confidence": 91.2,
        "summary": "summary",
        "best_colors": [
            {"name": "coral", "hex": "#F49A8A", "reason": "good"},
        ],
        "avoid_colors": [
            {"name": "navy", "hex": "#233554", "reason": "bad"},
        ],
        "recommendations": {
            "clothing": ["ivory shirt"],
            "makeup": ["coral lip"],
            "accessories": ["gold accessory"],
        },
        "analysis_metrics": {
            "warmth": 0.8,
            "brightness": 0.7,
            "saturation": 0.6,
            "contrast": 0.5,
        },
    }
    result.update(overrides)
    return result


class FakeGmsResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.payload


class GmsPersonalColorProviderTests(TestCase):
    def test_get_provider_returns_gms_provider_when_configured(self):
        with override_settings(
            PERSONAL_COLOR_PROVIDER="gms",
            GMS_API_KEY="test-key",
            GMS_API_URL="https://gms.example/analyze",
            GMS_MODEL="test-model",
        ):
            provider = get_personal_color_provider()

        self.assertIsInstance(provider, GmsPersonalColorProvider)
        self.assertEqual(provider.model_version, "test-model")

    def test_gms_provider_requires_key_and_url(self):
        with override_settings(
            PERSONAL_COLOR_PROVIDER="gms",
            GMS_API_KEY="",
            GMS_API_URL="",
        ):
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(AnalysisProviderUnavailableError):
                    get_personal_color_provider()

    def test_gms_provider_posts_image_and_normalizes_chat_response(self):
        prepared_image = prepare_uploaded_image(make_image_file())
        content = json.dumps(
            make_gms_result(
                resultType="spring warm",
                confidence=0.91,
            )
        )
        provider = GmsPersonalColorProvider(
            api_url="https://gms.example/analyze",
            api_key="test-key",
            model="test-model",
        )

        with patch(
            "personal_color.services.urllib.request.urlopen",
            return_value=FakeGmsResponse(
                {"choices": [{"message": {"content": content}}]}
            ),
        ) as mocked_urlopen:
            result = provider.analyze(prepared_image)

        request = mocked_urlopen.call_args.args[0]
        request_body = json.loads(request.data.decode("utf-8"))

        self.assertEqual(request.full_url, "https://gms.example/analyze")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(request_body["model"], "test-model")
        self.assertIn("messages", request_body)
        self.assertEqual(request_body["max_completion_tokens"], 500)
        user_content = request_body["messages"][0]["content"]
        self.assertEqual(user_content[0]["type"], "text")
        self.assertIn("personal color recommendation", user_content[0]["text"].lower())
        self.assertEqual(user_content[1]["type"], "image_url")
        self.assertEqual(user_content[1]["image_url"]["detail"], "low")
        self.assertTrue(user_content[1]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(result["result_type"], PersonalColorAnalysis.ResultType.SPRING_WARM)
        self.assertEqual(result["confidence"], 91.0)
        self.assertEqual(result["provider_name"], "gms")
        self.assertEqual(result["model_version"], "test-model")
        validate_normalized_result(result)

    def test_gms_provider_maps_korean_recommendation_response(self):
        prepared_image = prepare_uploaded_image(make_image_file())
        content = json.dumps(
            {
                "추천색상": {
                    "색상": "쿨톤 핑크",
                    "이유": "피부가 밝고 깨끗한 느낌을 주며, 차가운 색 조화가 잘 어울립니다.",
                    "추천": "원피스나 스카프 같은 패션 아이템에 적용하세요.",
                }
            }
        )
        provider = GmsPersonalColorProvider(
            api_url="https://gms.example/analyze",
            api_key="test-key",
            model="test-model",
        )

        with patch(
            "personal_color.services.urllib.request.urlopen",
            return_value=FakeGmsResponse(
                {"choices": [{"message": {"content": content}}]}
            ),
        ) as mocked_urlopen:
            result = provider.analyze(prepared_image)

        request = mocked_urlopen.call_args.args[0]
        request_body = json.loads(request.data.decode("utf-8"))

        self.assertEqual(request.full_url, "https://gms.example/analyze")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(request_body["model"], "test-model")
        self.assertIn("messages", request_body)
        self.assertEqual(result["result_type"], PersonalColorAnalysis.ResultType.SUMMER_COOL)
        self.assertEqual(result["result_subtype"], "쿨톤 핑크")
        self.assertEqual(result["confidence"], 80.0)
        self.assertIn("쿨톤 핑크", result["summary"])
        self.assertEqual(result["best_colors"][0]["name"], "쿨톤 핑크")
        self.assertTrue(result["best_colors"][0]["hex"].startswith("#"))
        self.assertTrue(result["recommendations"]["clothing"])
        self.assertEqual(result["provider_name"], "gms")
        self.assertEqual(result["model_version"], "test-model")
        validate_normalized_result(result)

    def test_gms_http_error_is_provider_unavailable(self):
        prepared_image = prepare_uploaded_image(make_image_file())
        provider = GmsPersonalColorProvider(
            api_url="https://gms.example/analyze",
            api_key="test-key",
        )
        http_error = urllib.error.HTTPError(
            "https://gms.example/analyze",
            400,
            "Bad Request",
            None,
            BytesIO(b'{"message":"Invalid target domain"}'),
        )

        with patch(
            "personal_color.services.urllib.request.urlopen",
            side_effect=http_error,
        ):
            with self.assertRaises(AnalysisProviderUnavailableError):
                provider.analyze(prepared_image)

    def test_non_json_gms_response_fails_validation(self):
        prepared_image = prepare_uploaded_image(make_image_file())
        provider = GmsPersonalColorProvider(
            api_url="https://gms.example/analyze",
            api_key="test-key",
        )

        with patch(
            "personal_color.services.urllib.request.urlopen",
            return_value=FakeGmsResponse(
                {"choices": [{"message": {"content": "not json"}}]}
            ),
        ):
            with self.assertRaises(AnalysisFailedError):
                provider.analyze(prepared_image)


class GmsPersonalColorAnalysisApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user_with_profile(
            "gms-user",
            "gms@example.com",
            "gms",
            "01011112222",
        )
        self.client.force_login(self.user)

    @override_settings(
        PERSONAL_COLOR_PROVIDER="gms",
        GMS_API_KEY="test-key",
        GMS_API_URL="https://gms.example/analyze",
    )
    def test_invalid_gms_response_does_not_create_record(self):
        with patch(
            "personal_color.services.urllib.request.urlopen",
            return_value=FakeGmsResponse(
                {"choices": [{"message": {"content": "not json"}}]}
            ),
        ):
            response = self.client.post(
                "/api/personal-color/analyses/",
                {"image": make_image_file()},
                format="multipart",
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "analysis_result_invalid")
        self.assertEqual(PersonalColorAnalysis.objects.count(), 0)
