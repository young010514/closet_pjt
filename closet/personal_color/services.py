from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import random
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError

from .exceptions import (
    AnalysisFailedError,
    AnalysisProviderUnavailableError,
    FaceNotDetectedError,
    InvalidImageError,
)
from .models import PersonalColorAnalysis


logger = logging.getLogger(__name__)


ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MIME_TYPE_EXTENSIONS = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}

ALLOWED_IMAGE_EXTENSIONS = {
    extension
    for extensions in MIME_TYPE_EXTENSIONS.values()
    for extension in extensions
}

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
MIN_IMAGE_DIMENSION = 256
MAX_IMAGE_DIMENSION = 4096

RESULT_TYPE_ORDER = [
    PersonalColorAnalysis.ResultType.SPRING_WARM,
    PersonalColorAnalysis.ResultType.SUMMER_COOL,
    PersonalColorAnalysis.ResultType.AUTUMN_WARM,
    PersonalColorAnalysis.ResultType.WINTER_COOL,
]

GMS_PERSONAL_COLOR_PROMPT = """
Analyze the uploaded face image for personal color styling.
Return only one JSON object. Do not wrap it in markdown.
Use Korean text for summaries, color names, reasons, and recommendations.
The JSON schema must be:
{
  "result_type": "spring_warm | summer_cool | autumn_warm | winter_cool",
  "result_subtype": "string",
  "confidence": 0-100,
  "summary": "string",
  "best_colors": [{"name": "string", "hex": "#RRGGBB", "reason": "string"}],
  "avoid_colors": [{"name": "string", "hex": "#RRGGBB", "reason": "string"}],
  "recommendations": {
    "clothing": ["string"],
    "makeup": ["string"],
    "accessories": ["string"]
  },
  "analysis_metrics": {
    "warmth": 0-1,
    "brightness": 0-1,
    "saturation": 0-1,
    "contrast": 0-1
  }
}
""".strip()


def color_item(name: str, hex_value: str, reason: str) -> dict[str, str]:
    return {
        "name": name,
        "hex": hex_value,
        "reason": reason,
    }


SEASON_CONFIGS: dict[str, dict[str, Any]] = {
    PersonalColorAnalysis.ResultType.SPRING_WARM: {
        "subtypes": ["브라이트", "라이트", "클리어", "트루"],
        "summary": (
            "밝고 맑은 색이 얼굴에 생기를 더합니다. "
            "{subtype} 계열의 산뜻한 톤이 특히 잘 어울립니다."
        ),
        "best_colors": [
            color_item("피치 코랄", "#F49A8A", "얼굴에 생기를 더해 주는 따뜻한 색상입니다."),
            color_item("웜 옐로우", "#F6D86B", "부드러운 밝기를 살려 화사해 보이게 합니다."),
            color_item("라이트 민트", "#CDE8C8", "깨끗하고 산뜻한 인상을 강조합니다."),
            color_item("아쿠아 샌드", "#A6D8D4", "맑은 피부 톤과 조화를 이루기 좋습니다."),
        ],
        "avoid_colors": [
            color_item("차가운 블루 그레이", "#718096", "안색이 다소 창백해 보일 수 있습니다."),
            color_item("딥 네이비", "#233554", "무게감이 강해 생기가 묻힐 수 있습니다."),
            color_item("진한 와인", "#7A2E3A", "피부 톤의 밝고 따뜻한 느낌을 약하게 만듭니다."),
        ],
        "recommendations": {
            "clothing": [
                "아이보리 셔츠",
                "살구·코랄 상의",
                "가벼운 트위드 재킷",
            ],
            "makeup": [
                "피치 블러셔",
                "코랄 립",
                "맑은 피부 표현 중심의 베이스",
            ],
            "accessories": [
                "골드 톤 액세서리",
                "진주 포인트",
                "투명 또는 가벼운 프레임 안경",
            ],
        },
        "metrics": {
            "warmth": (0.82, 0.08),
            "brightness": (0.78, 0.1),
            "saturation": (0.66, 0.1),
            "contrast": (0.52, 0.08),
        },
    },
    PersonalColorAnalysis.ResultType.SUMMER_COOL: {
        "subtypes": ["라이트", "소프트", "뮤트", "쿨"],
        "summary": (
            "차분하고 부드러운 색이 잘 어울립니다. "
            "{subtype} 감도의 색감이 얼굴을 편안하게 보이게 합니다."
        ),
        "best_colors": [
            color_item("라벤더", "#C8B5F5", "피부의 맑고 부드러운 느낌을 살려 줍니다."),
            color_item("더스티 블루", "#8EA4C8", "차분한 분위기와 안정감을 더합니다."),
            color_item("로즈 핑크", "#E6A7B5", "자연스러운 생기와 부드러운 인상을 줍니다."),
            color_item("소프트 그레이", "#B8BFC9", "과하지 않게 전체 톤을 정리해 줍니다."),
        ],
        "avoid_colors": [
            color_item("오렌지 코랄", "#F58B64", "따뜻한 기운이 강해 대비가 생길 수 있습니다."),
            color_item("머스터드", "#D9A441", "피부의 맑은 느낌이 둔해질 수 있습니다."),
            color_item("올리브", "#687A3D", "탁한 인상을 강하게 만들 수 있습니다."),
        ],
        "recommendations": {
            "clothing": [
                "라이트 그레이 니트",
                "블루 계열 셔츠",
                "차분한 로맨틱 무드의 원피스",
            ],
            "makeup": [
                "쿨 로즈 블러셔",
                "투명감 있는 립",
                "소프트 매트 피부 표현",
            ],
            "accessories": [
                "실버 톤 액세서리",
                "얇은 메탈 프레임 안경",
                "과하지 않은 미니멀 장식",
            ],
        },
        "metrics": {
            "warmth": (0.28, 0.08),
            "brightness": (0.74, 0.08),
            "saturation": (0.48, 0.08),
            "contrast": (0.36, 0.08),
        },
    },
    PersonalColorAnalysis.ResultType.AUTUMN_WARM: {
        "subtypes": ["뮤트", "딥", "소프트", "웜"],
        "summary": (
            "깊고 따뜻한 색이 안정적인 인상을 만듭니다. "
            "{subtype}한 톤의 자연스러운 색감이 잘 어울립니다."
        ),
        "best_colors": [
            color_item("테라코타", "#C76A4A", "피부의 깊이감을 자연스럽게 살려 줍니다."),
            color_item("카멜", "#C19A6B", "부드럽고 고급스러운 분위기를 만듭니다."),
            color_item("올리브", "#6F7B3B", "자연스럽고 안정감 있는 인상을 줍니다."),
            color_item("딥 베이지", "#D8B58B", "따뜻한 무드를 편안하게 연결합니다."),
        ],
        "avoid_colors": [
            color_item("이시 핑크", "#F5C2D7", "색감이 떠 보일 수 있습니다."),
            color_item("코발트 블루", "#2E58B8", "차가운 대비가 강하게 느껴질 수 있습니다."),
            color_item("실버 그레이", "#C0C7D1", "따뜻한 질감이 약해질 수 있습니다."),
        ],
        "recommendations": {
            "clothing": [
                "브라운 계열 코트",
                "울 소재 니트",
                "오렌지 브릭 톤 상의",
            ],
            "makeup": [
                "브론즈 아이 메이크업",
                "코랄 브라운 립",
                "선명하지만 부드러운 음영",
            ],
            "accessories": [
                "골드 액세서리",
                "가죽 소재 포인트",
                "따뜻한 우드 톤 소품",
            ],
        },
        "metrics": {
            "warmth": (0.78, 0.08),
            "brightness": (0.48, 0.08),
            "saturation": (0.58, 0.08),
            "contrast": (0.62, 0.08),
        },
    },
    PersonalColorAnalysis.ResultType.WINTER_COOL: {
        "subtypes": ["비비드", "딥", "클리어", "트루"],
        "summary": (
            "선명하고 또렷한 색이 얼굴을 깨끗하게 살려 줍니다. "
            "{subtype}한 대비감이 인상을 선명하게 보여 줍니다."
        ),
        "best_colors": [
            color_item("코발트 블루", "#2D5BFF", "깨끗하고 선명한 인상을 강조합니다."),
            color_item("마젠타", "#D63B9B", "생동감과 세련된 대비를 더합니다."),
            color_item("퓨어 화이트", "#FFFFFF", "전체 분위기를 가장 또렷하게 정리합니다."),
            color_item("차콜", "#2F343F", "강한 대비를 받쳐 주는 안정적인 색상입니다."),
        ],
        "avoid_colors": [
            color_item("피치", "#F7B18A", "따뜻한 기운이 강해 선명함이 약해질 수 있습니다."),
            color_item("올리브", "#76824A", "탁해 보이거나 무거워 보일 수 있습니다."),
            color_item("캠엘", "#B98F6B", "톤이 흐려지고 또렷함이 줄어들 수 있습니다."),
        ],
        "recommendations": {
            "clothing": [
                "블랙·화이트 대비 코디",
                "선명한 블루 계열 재킷",
                "미니멀하고 구조적인 실루엣",
            ],
            "makeup": [
                "맑은 레드 립",
                "또렷한 아이라인",
                "채도 있는 블러셔 포인트",
            ],
            "accessories": [
                "실버 액세서리",
                "광택감 있는 메탈 소재",
                "미니멀한 직선형 디자인",
            ],
        },
        "metrics": {
            "warmth": (0.22, 0.08),
            "brightness": (0.58, 0.08),
            "saturation": (0.78, 0.08),
            "contrast": (0.74, 0.08),
        },
    },
}


@dataclass(frozen=True)
class PreparedPersonalColorImage:
    original_name: str
    content_type: str
    size: int
    width: int
    height: int
    normalized_bytes: bytes
    sha256_hex: str
    image_format: str


class PersonalColorProvider:
    name = ""
    model_version = ""
    supports_face_detection = False

    def analyze(self, prepared_image: PreparedPersonalColorImage) -> dict[str, Any]:
        raise NotImplementedError

    def ensure_face_present(self, prepared_image: PreparedPersonalColorImage) -> None:
        return None


class MockPersonalColorProvider(PersonalColorProvider):
    name = "mock"
    model_version = "mock-v1"

    def analyze(self, prepared_image: PreparedPersonalColorImage) -> dict[str, Any]:
        seed = int(prepared_image.sha256_hex, 16)
        rng = random.Random(seed)
        result_type = RESULT_TYPE_ORDER[seed % len(RESULT_TYPE_ORDER)]
        config = SEASON_CONFIGS[result_type]
        subtype = rng.choice(config["subtypes"])

        best_colors = [dict(item) for item in config["best_colors"]]
        avoid_colors = [dict(item) for item in config["avoid_colors"]]
        rng.shuffle(best_colors)
        rng.shuffle(avoid_colors)

        return {
            "result_type": result_type,
            "result_subtype": subtype,
            "confidence": round(78 + rng.random() * 18, 2),
            "summary": config["summary"].format(subtype=subtype),
            "best_colors": best_colors,
            "avoid_colors": avoid_colors,
            "recommendations": {
                key: list(value)
                for key, value in config["recommendations"].items()
            },
            "analysis_metrics": _build_metrics(result_type, seed),
            "provider_name": self.name,
            "model_version": self.model_version,
        }

def _get_setting(name: str, default: Any = "") -> Any:
    value = getattr(settings, name, None)
    if value not in (None, ""):
        return value
    return os.getenv(name, default)


def _get_gms_timeout() -> float:
    try:
        timeout = float(_get_setting("GMS_TIMEOUT_SECONDS", 30.0))
    except (TypeError, ValueError):
        timeout = 30.0
    return max(timeout, 1.0)


def _strip_json_markdown(value: str) -> str:
    text = value.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_json_text(value: str) -> Any:
    try:
        return json.loads(_strip_json_markdown(value))
    except json.JSONDecodeError as exc:
        raise AnalysisFailedError(
            "GMS analysis result was not valid JSON.",
            code="analysis_result_invalid",
        ) from exc


def _extract_gms_result(value: Any) -> Any:
    if isinstance(value, str):
        return _extract_gms_result(_parse_json_text(value))

    if not isinstance(value, dict):
        return value

    if any(
        key in value
        for key in (
            "result_type",
            "resultType",
            "season",
            "personal_color",
            "personalColor",
        )
    ):
        return value

    choices = value.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict) and "content" in message:
                return _extract_gms_result(message["content"])
            for key in ("content", "text"):
                if key in first_choice:
                    return _extract_gms_result(first_choice[key])

    candidates = []
    for key in ("result", "analysis", "data", "output", "content", "text"):
        if key in value:
            candidates.append(value[key])

    for candidate in candidates:
        if isinstance(candidate, (dict, str)):
            extracted = _extract_gms_result(candidate)
            if extracted is not candidate or isinstance(extracted, dict):
                return extracted

    return value


def _normalize_result_type_alias(value: Any) -> str:
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in RESULT_TYPE_ORDER:
        return normalized
    if "spring" in normalized:
        return PersonalColorAnalysis.ResultType.SPRING_WARM
    if "summer" in normalized:
        return PersonalColorAnalysis.ResultType.SUMMER_COOL
    if "autumn" in normalized or "fall" in normalized:
        return PersonalColorAnalysis.ResultType.AUTUMN_WARM
    if "winter" in normalized:
        return PersonalColorAnalysis.ResultType.WINTER_COOL
    return str(value).strip()


def _normalize_gms_result_shape(
    value: Any,
    *,
    provider_name: str,
    model_version: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AnalysisFailedError(
            "GMS analysis result format was invalid.",
            code="analysis_result_invalid",
        )

    result = dict(value)
    aliases = {
        "resultType": "result_type",
        "resultSubtype": "result_subtype",
        "subtype": "result_subtype",
        "bestColors": "best_colors",
        "avoidColors": "avoid_colors",
        "analysisMetrics": "analysis_metrics",
        "metrics": "analysis_metrics",
        "providerName": "provider_name",
        "modelVersion": "model_version",
    }
    for source, target in aliases.items():
        if source in result and target not in result:
            result[target] = result[source]

    for source in ("season", "personal_color", "personalColor"):
        if source in result and "result_type" not in result:
            result["result_type"] = result[source]

    if "result_type" in result:
        result["result_type"] = _normalize_result_type_alias(result["result_type"])

    confidence = result.get("confidence")
    if isinstance(confidence, (int, float)) and 0 <= confidence <= 1:
        result["confidence"] = round(confidence * 100, 2)

    result.setdefault("provider_name", provider_name)
    result.setdefault("model_version", model_version)
    return result


class GmsPersonalColorProvider(PersonalColorProvider):
    name = "gms"

    def __init__(
        self,
        *,
        api_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        api_style: str | None = None,
        timeout: float | None = None,
    ):
        self.api_url = (api_url or str(_get_setting("GMS_API_URL", ""))).strip()
        self.api_key = (api_key or str(_get_setting("GMS_API_KEY", ""))).strip()
        self.model = (model or str(_get_setting("GMS_MODEL", ""))).strip()
        self.api_style = (
            api_style or str(_get_setting("GMS_API_STYLE", "openai")) or "openai"
        ).strip().lower()
        self.timeout = timeout or _get_gms_timeout()
        self.model_version = self.model or "gms"

        if not self.api_url or not self.api_key:
            raise AnalysisProviderUnavailableError(
                "GMS API configuration is missing.",
                code="analysis_provider_unavailable",
            )

    def analyze(self, prepared_image: PreparedPersonalColorImage) -> dict[str, Any]:
        request = urllib.request.Request(
            self.api_url,
            data=json.dumps(
                self._build_payload(prepared_image),
                ensure_ascii=False,
            ).encode("utf-8"),
            headers=self._build_headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_body = response.read()
        except urllib.error.HTTPError as exc:
            self._raise_for_http_error(exc)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            raise AnalysisProviderUnavailableError(
                "GMS API request failed.",
                code="analysis_provider_unavailable",
            ) from exc

        try:
            response_json = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AnalysisFailedError(
                "GMS API response was not valid JSON.",
                code="analysis_result_invalid",
            ) from exc

        extracted = _extract_gms_result(response_json)
        return _normalize_gms_result_shape(
            extracted,
            provider_name=self.name,
            model_version=self.model_version,
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        key_header = str(_get_setting("GMS_API_KEY_HEADER", "Authorization")).strip()
        auth_prefix = str(_get_setting("GMS_API_AUTH_PREFIX", "Bearer")).strip()
        if key_header:
            value = self.api_key
            if key_header.lower() == "authorization" and auth_prefix:
                value = f"{auth_prefix} {self.api_key}"
            headers[key_header] = value
        return headers

    def _build_payload(self, prepared_image: PreparedPersonalColorImage) -> dict[str, Any]:
        image_base64 = base64.b64encode(prepared_image.normalized_bytes).decode("ascii")

        if self.api_style == "gemini":
            return {
                "contents": [
                    {
                        "parts": [
                            {"text": GMS_PERSONAL_COLOR_PROMPT},
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": image_base64,
                                }
                            },
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json",
                },
            }

        if self.api_style == "raw":
            payload = {
                "prompt": GMS_PERSONAL_COLOR_PROMPT,
                "image": {
                    "mime_type": "image/png",
                    "data": image_base64,
                },
            }
            if self.model:
                payload["model"] = self.model
            return payload

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a personal color analysis assistant.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": GMS_PERSONAL_COLOR_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                            },
                        },
                    ],
                },
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        if self.model:
            payload["model"] = self.model
        return payload

    def _raise_for_http_error(self, exc: urllib.error.HTTPError) -> None:
        try:
            response_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            response_body = ""

        logger.warning(
            "GMS API request failed: status=%s body=%s",
            exc.code,
            response_body[:1000],
        )
        raise AnalysisProviderUnavailableError(
            "GMS API request failed.",
            code="analysis_provider_unavailable",
        ) from exc

def _build_metrics(result_type: str, seed: int) -> dict[str, float]:
    config = SEASON_CONFIGS[result_type]["metrics"]
    rng = random.Random(seed ^ 0x5F3759DF)
    return {
        metric: _clamp(
            round(base + (rng.random() - 0.5) * spread, 2),
            0.0,
            1.0,
        )
        for metric, (base, spread) in config.items()
    }


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _normalize_extension(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def _normalize_content_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    return content_type.split(";", 1)[0].strip().lower()


def _normalize_to_png(image: Image.Image) -> bytes:
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    if image.mode == "RGBA":
        background = Image.new("RGBA", image.size, (255, 255, 255, 255))
        background.alpha_composite(image)
        image = background.convert("RGB")
    else:
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _ensure_within_dimension_bounds(width: int, height: int) -> None:
    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        raise InvalidImageError(
            "이미지 크기는 최소 256 x 256이어야 합니다.",
            code="image_too_small",
        )

    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise InvalidImageError(
            "이미지 크기는 최대 4096 x 4096을 초과할 수 없습니다.",
            code="image_too_large",
        )


def _build_invalid_image_error(message: str, code: str) -> InvalidImageError:
    return InvalidImageError(message, code=code)


def prepare_uploaded_image(image_file) -> PreparedPersonalColorImage:
    if image_file is None:
        raise _build_invalid_image_error(
            "이미지 파일을 선택해 주세요.",
            "image_required",
        )

    original_name = getattr(image_file, "name", "") or ""
    content_type = _normalize_content_type(getattr(image_file, "content_type", None))
    extension = _normalize_extension(original_name)
    size = int(getattr(image_file, "size", 0) or 0)

    if size <= 0:
        raise _build_invalid_image_error(
            "이미지 파일을 확인할 수 없습니다.",
            "invalid_image",
        )

    if size > MAX_UPLOAD_SIZE_BYTES:
        raise _build_invalid_image_error(
            "파일 크기는 10MB 이하여야 합니다.",
            "file_too_large",
        )

    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise _build_invalid_image_error(
            "JPEG, PNG, WEBP 이미지 파일만 업로드할 수 있습니다.",
            "unsupported_image_type",
        )

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise _build_invalid_image_error(
            "JPEG, PNG, WEBP 이미지 파일만 업로드할 수 있습니다.",
            "unsupported_image_type",
        )

    if extension not in MIME_TYPE_EXTENSIONS.get(content_type, set()):
        raise _build_invalid_image_error(
            "파일 확장자와 MIME 형식이 일치하지 않습니다.",
            "image_type_mismatch",
        )

    if hasattr(image_file, "seek"):
        image_file.seek(0)

    try:
        raw_bytes = image_file.read()
    finally:
        if hasattr(image_file, "seek"):
            image_file.seek(0)

    if len(raw_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise _build_invalid_image_error(
            "파일 크기는 10MB 이하여야 합니다.",
            "file_too_large",
        )

    try:
        with Image.open(io.BytesIO(raw_bytes)) as preview_image:
            preview_image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise _build_invalid_image_error(
            "손상된 이미지 파일입니다.",
            "corrupted_image",
        ) from exc

    try:
        with Image.open(io.BytesIO(raw_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            image.load()
            width, height = image.size
            _ensure_within_dimension_bounds(width, height)
            normalized_bytes = _normalize_to_png(image)
            sha256_hex = hashlib.sha256(normalized_bytes).hexdigest()
            return PreparedPersonalColorImage(
                original_name=original_name,
                content_type=content_type,
                size=size,
                width=width,
                height=height,
                normalized_bytes=normalized_bytes,
                sha256_hex=sha256_hex,
                image_format="PNG",
            )
    except InvalidImageError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise _build_invalid_image_error(
            "손상된 이미지 파일입니다.",
            "corrupted_image",
        ) from exc


def get_personal_color_provider() -> PersonalColorProvider:
    configured_provider = (
        getattr(settings, "PERSONAL_COLOR_PROVIDER", "")
        or os.getenv("PERSONAL_COLOR_PROVIDER", "")
    ).strip().lower()

    if configured_provider == "mock":
        return MockPersonalColorProvider()

    if configured_provider == "gms":
        return GmsPersonalColorProvider()

    if not configured_provider and settings.DEBUG:
        return MockPersonalColorProvider()

    raise AnalysisProviderUnavailableError(
        "AI 분석 제공자가 설정되지 않았습니다.",
        code="analysis_provider_unavailable",
    )


def validate_normalized_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise AnalysisFailedError(
            "분석 결과 형식이 올바르지 않습니다.",
            code="analysis_result_invalid",
        )

    required_keys = {
        "result_type",
        "result_subtype",
        "confidence",
        "summary",
        "best_colors",
        "avoid_colors",
        "recommendations",
        "analysis_metrics",
        "provider_name",
        "model_version",
    }

    missing = sorted(required_keys - set(result))
    if missing:
        raise AnalysisFailedError(
            "분석 결과에 필요한 항목이 누락되었습니다.",
            code="analysis_result_invalid",
        )

    result_type = str(result["result_type"]).strip()
    if result_type not in RESULT_TYPE_ORDER:
        raise AnalysisFailedError(
            "분석 결과 타입이 올바르지 않습니다.",
            code="analysis_result_invalid",
        )

    result_subtype = str(result["result_subtype"]).strip()
    if not result_subtype:
        raise AnalysisFailedError(
            "분석 결과 세부 타입이 비어 있습니다.",
            code="analysis_result_invalid",
        )

    summary = str(result["summary"]).strip()
    if not summary:
        raise AnalysisFailedError(
            "분석 요약이 비어 있습니다.",
            code="analysis_result_invalid",
        )

    normalized = {
        "result_type": result_type,
        "result_subtype": result_subtype,
        "confidence": _normalize_confidence(result["confidence"]),
        "summary": summary,
        "best_colors": _normalize_color_entries(result["best_colors"], "best_colors"),
        "avoid_colors": _normalize_color_entries(result["avoid_colors"], "avoid_colors"),
        "recommendations": _normalize_recommendations(result["recommendations"]),
        "analysis_metrics": _normalize_metrics(result["analysis_metrics"]),
        "provider_name": str(result["provider_name"]).strip(),
        "model_version": str(result["model_version"]).strip(),
    }

    return normalized


def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise AnalysisFailedError(
            "신뢰도 값이 올바르지 않습니다.",
            code="analysis_result_invalid",
        ) from exc

    if confidence < 0 or confidence > 100:
        raise AnalysisFailedError(
            "신뢰도는 0에서 100 사이여야 합니다.",
            code="analysis_result_invalid",
        )

    return round(confidence, 2)


def _normalize_color_entries(value: Any, field_name: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise AnalysisFailedError(
            f"{field_name} 형식이 올바르지 않습니다.",
            code="analysis_result_invalid",
        )

    normalized_entries: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise AnalysisFailedError(
                f"{field_name} 항목 형식이 올바르지 않습니다.",
                code="analysis_result_invalid",
            )

        name = str(item.get("name", "")).strip()
        hex_value = str(item.get("hex", "")).strip().upper()
        reason = str(item.get("reason", "")).strip()

        if not name or not hex_value or not reason:
            raise AnalysisFailedError(
                f"{field_name} 항목이 비어 있습니다.",
                code="analysis_result_invalid",
            )

        if not _is_valid_hex_color(hex_value):
            raise AnalysisFailedError(
                f"{field_name} 색상 코드가 올바르지 않습니다.",
                code="analysis_result_invalid",
            )

        normalized_entries.append(
            {
                "name": name,
                "hex": hex_value,
                "reason": reason,
            }
        )

    return normalized_entries


def _is_valid_hex_color(value: str) -> bool:
    if len(value) != 7 or not value.startswith("#"):
        return False

    try:
        int(value[1:], 16)
    except ValueError:
        return False

    return True


def _normalize_recommendations(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        raise AnalysisFailedError(
            "recommendations 형식이 올바르지 않습니다.",
            code="analysis_result_invalid",
        )

    normalized: dict[str, list[str]] = {}
    for key in ("clothing", "makeup", "accessories"):
        items = value.get(key)
        if not isinstance(items, list):
            raise AnalysisFailedError(
                f"recommendations.{key} 형식이 올바르지 않습니다.",
                code="analysis_result_invalid",
            )

        normalized[key] = []
        for item in items:
            text = str(item).strip()
            if not text:
                raise AnalysisFailedError(
                    f"recommendations.{key} 항목이 비어 있습니다.",
                    code="analysis_result_invalid",
                )
            normalized[key].append(text)

    return normalized


def _normalize_metrics(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        raise AnalysisFailedError(
            "analysis_metrics 형식이 올바르지 않습니다.",
            code="analysis_result_invalid",
        )

    normalized: dict[str, float] = {}
    for key in ("warmth", "brightness", "saturation", "contrast"):
        if key not in value:
            raise AnalysisFailedError(
                f"analysis_metrics.{key} 값이 없습니다.",
                code="analysis_result_invalid",
            )

        try:
            metric_value = float(value[key])
        except (TypeError, ValueError) as exc:
            raise AnalysisFailedError(
                f"analysis_metrics.{key} 값이 올바르지 않습니다.",
                code="analysis_result_invalid",
            ) from exc

        if metric_value < 0 or metric_value > 1:
            raise AnalysisFailedError(
                f"analysis_metrics.{key} 값은 0에서 1 사이여야 합니다.",
                code="analysis_result_invalid",
            )

        normalized[key] = round(metric_value, 2)

    return normalized


def analyze_prepared_image(prepared_image: PreparedPersonalColorImage) -> dict[str, Any]:
    provider = get_personal_color_provider()

    # Real providers can opt into face detection later.
    if getattr(provider, "supports_face_detection", False):
        provider.ensure_face_present(prepared_image)

    try:
        raw_result = provider.analyze(prepared_image)
    except (
        InvalidImageError,
        FaceNotDetectedError,
        AnalysisProviderUnavailableError,
        AnalysisFailedError,
    ):
        raise
    except Exception as exc:
        raise AnalysisFailedError(
            "분석 요청을 처리하지 못했습니다.",
            code="analysis_failed",
        ) from exc

    try:
        return validate_normalized_result(raw_result)
    except AnalysisFailedError as exc:
        if getattr(provider, "name", "") == "gms" and exc.code == "analysis_result_invalid":
            logger.warning("GMS API returned invalid analysis result: %s", exc.message)
            raise AnalysisProviderUnavailableError(
                exc.message,
                code=exc.code,
            ) from exc
        raise


def analyze_personal_color(image_file) -> dict[str, Any]:
    prepared_image = prepare_uploaded_image(image_file)
    return analyze_prepared_image(prepared_image)


def _to_decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def build_analysis_model_kwargs(normalized_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "result_type": normalized_result["result_type"],
        "result_subtype": normalized_result["result_subtype"],
        "confidence": _to_decimal(normalized_result["confidence"]),
        "summary": normalized_result["summary"],
        "best_colors": normalized_result["best_colors"],
        "avoid_colors": normalized_result["avoid_colors"],
        "recommendations": normalized_result["recommendations"],
        "analysis_metrics": normalized_result["analysis_metrics"],
        "provider_name": normalized_result["provider_name"],
        "model_version": normalized_result["model_version"],
    }


@transaction.atomic
def create_personal_color_analysis(
    *,
    user,
    image_file=None,
    prepared_image: PreparedPersonalColorImage | None = None,
):
    if prepared_image is None:
        prepared_image = prepare_uploaded_image(image_file)

    normalized_result = analyze_prepared_image(prepared_image)
    return PersonalColorAnalysis.objects.create(
        user=user,
        **build_analysis_model_kwargs(normalized_result),
    )

