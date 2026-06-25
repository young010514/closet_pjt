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
from urllib.parse import urlparse

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

DEFAULT_MAX_COMPLETION_TOKENS = 500

RESULT_TYPE_ORDER = [
    PersonalColorAnalysis.ResultType.SPRING_WARM,
    PersonalColorAnalysis.ResultType.SUMMER_COOL,
    PersonalColorAnalysis.ResultType.AUTUMN_WARM,
    PersonalColorAnalysis.ResultType.WINTER_COOL,
]


def color_item(name: str, hex_value: str, reason: str) -> dict[str, str]:
    return {
        "name": name,
        "hex": hex_value,
        "reason": reason,
    }


SEASON_PRESETS: dict[str, dict[str, Any]] = {
    PersonalColorAnalysis.ResultType.SPRING_WARM: {
        "label": "봄 웜톤",
        "subtypes": ["라이트", "브라이트", "코랄", "피치"],
        "summary": "맑고 따뜻한 색감이 얼굴을 생기 있게 살려 줍니다.",
        "best_colors": [
            color_item("코랄 핑크", "#F49A8A", "얼굴빛을 건강하고 화사하게 보여 줍니다."),
            color_item("버터 옐로", "#F6D86B", "밝고 부드러운 인상을 만듭니다."),
            color_item("민트", "#CDE8C8", "산뜻하고 깨끗한 분위기를 더합니다."),
            color_item("아쿠아", "#A6D8D4", "맑은 느낌을 유지하면서 생기를 줍니다."),
        ],
        "avoid_colors": [
            color_item("쿨 그레이", "#718096", "얼굴빛이 다소 칙칙해 보일 수 있습니다."),
            color_item("딥 네이비", "#233554", "무거운 느낌이 강해질 수 있습니다."),
            color_item("와인", "#7A2E3A", "따뜻한 봄 느낌을 덜어낼 수 있습니다."),
        ],
        "recommendations": {
            "clothing": [
                "아이보리 톱",
                "연한 베이지 니트",
                "코랄 포인트 블라우스",
            ],
            "makeup": [
                "코랄 블러셔",
                "피치 립",
                "가벼운 글로우 베이스",
            ],
            "accessories": [
                "골드 액세서리",
                "투명 프레임 안경",
                "진주 포인트",
            ],
        },
        "analysis_metrics": {
            "warmth": 0.82,
            "brightness": 0.78,
            "saturation": 0.66,
            "contrast": 0.52,
        },
    },
    PersonalColorAnalysis.ResultType.SUMMER_COOL: {
        "label": "여름 쿨톤",
        "subtypes": ["라이트", "소프트", "뮤트", "쿨"],
        "summary": "차분하고 부드러운 색감이 얼굴을 더 맑아 보이게 합니다.",
        "best_colors": [
            color_item("라벤더", "#C8B5F5", "부드럽고 우아한 분위기를 살려 줍니다."),
            color_item("소프트 블루", "#8EA4C8", "청량한 인상을 유지해 줍니다."),
            color_item("로즈 핑크", "#E6A7B5", "자연스럽고 생기 있는 느낌을 줍니다."),
            color_item("미스트 그레이", "#B8BFC9", "부담 없이 정돈된 느낌을 줍니다."),
        ],
        "avoid_colors": [
            color_item("오렌지", "#F58B64", "과한 온기로 대비가 강해질 수 있습니다."),
            color_item("머스타드", "#D9A441", "부드러운 인상이 깨질 수 있습니다."),
            color_item("올리브", "#687A3D", "탁해 보일 가능성이 있습니다."),
        ],
        "recommendations": {
            "clothing": [
                "라이트 블루 셔츠",
                "은은한 그레이 재킷",
                "소프트 핑크 니트",
            ],
            "makeup": [
                "쿨 로즈 블러셔",
                "맑은 립 틴트",
                "소프트 매트 베이스",
            ],
            "accessories": [
                "실버 액세서리",
                "얇은 메탈 프레임",
                "유리 같은 광택 포인트",
            ],
        },
        "analysis_metrics": {
            "warmth": 0.28,
            "brightness": 0.74,
            "saturation": 0.48,
            "contrast": 0.36,
        },
    },
    PersonalColorAnalysis.ResultType.AUTUMN_WARM: {
        "label": "가을 웜톤",
        "subtypes": ["뮤트", "딥", "소프트", "웜"],
        "summary": "깊고 안정적인 색감이 얼굴에 자연스러운 분위기를 더합니다.",
        "best_colors": [
            color_item("테라코타", "#C76A4A", "따뜻하고 성숙한 분위기를 살려 줍니다."),
            color_item("카멜", "#C19A6B", "고급스럽고 안정적인 느낌을 줍니다."),
            color_item("올리브", "#6F7B3B", "자연스럽고 깊이 있는 인상을 만듭니다."),
            color_item("베이지", "#D8B58B", "부드럽고 편안한 분위기를 유지합니다."),
        ],
        "avoid_colors": [
            color_item("파스텔 핑크", "#F5C2D7", "얼굴이 붕 떠 보일 수 있습니다."),
            color_item("코발트 블루", "#2E58B8", "강한 차가움이 대비를 키울 수 있습니다."),
            color_item("쿨 그레이", "#C0C7D1", "따뜻한 기운이 약해질 수 있습니다."),
        ],
        "recommendations": {
            "clothing": [
                "브라운 계열 코트",
                "머스타드 니트",
                "올리브 셔츠",
            ],
            "makeup": [
                "브론즈 메이크업",
                "코랄 브라운 립",
                "음영감 있는 아이 메이크업",
            ],
            "accessories": [
                "골드 액세서리",
                "가죽 소재 포인트",
                "우드 톤 아이템",
            ],
        },
        "analysis_metrics": {
            "warmth": 0.78,
            "brightness": 0.48,
            "saturation": 0.58,
            "contrast": 0.62,
        },
    },
    PersonalColorAnalysis.ResultType.WINTER_COOL: {
        "label": "겨울 쿨톤",
        "subtypes": ["비비드", "딥", "브라이트", "클리어"],
        "summary": "선명하고 대비가 있는 색이 얼굴을 또렷하고 시원하게 보이게 합니다.",
        "best_colors": [
            color_item("코발트 블루", "#2D5BFF", "선명하고 또렷한 인상을 강조합니다."),
            color_item("마젠타", "#D63B9B", "강렬하고 세련된 분위기를 더합니다."),
            color_item("퓨어 화이트", "#FFFFFF", "전체 인상을 맑고 깨끗하게 정리합니다."),
            color_item("차콜", "#2F343F", "강한 대비를 안정적으로 받쳐 줍니다."),
        ],
        "avoid_colors": [
            color_item("피치", "#F7B18A", "선명한 대비가 흐려질 수 있습니다."),
            color_item("올리브", "#76824A", "탁하고 무거워 보일 수 있습니다."),
            color_item("베이지", "#B98F6B", "입체감이 줄어들 수 있습니다."),
        ],
        "recommendations": {
            "clothing": [
                "블랙 앤 화이트 조합",
                "강한 블루 재킷",
                "선명한 컬러 포인트 셔츠",
            ],
            "makeup": [
                "맑은 레드 립",
                "선명한 아이라인",
                "차가운 톤의 하이라이트",
            ],
            "accessories": [
                "실버 액세서리",
                "광택 있는 메탈 포인트",
                "미니멀한 블랙 아이템",
            ],
        },
        "analysis_metrics": {
            "warmth": 0.22,
            "brightness": 0.58,
            "saturation": 0.78,
            "contrast": 0.74,
        },
    },
}


GMS_PERSONAL_COLOR_PROMPT = """
Analyze the provided face image for personal color recommendation.
Return only one JSON object. Do not wrap it in markdown or code fences.
Use Korean text for summary, color names, reasons, and recommendations.
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
If you are uncertain, keep the JSON valid and choose the closest single season.
""".strip()


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


def _get_setting(name: str, default: Any = "") -> Any:
    value = getattr(settings, name, None)
    if value not in (None, ""):
        return value
    return os.getenv(name, default)


def _env_float(name: str, default: float) -> float:
    try:
        return float(_get_setting(name, default))
    except (TypeError, ValueError):
        return default


def _get_gms_timeout() -> float:
    return max(_env_float("GMS_TIMEOUT_SECONDS", 30.0), 1.0)


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
            "Image dimensions must be at least 256 x 256 pixels.",
            code="image_too_small",
        )

    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise InvalidImageError(
            "Image dimensions must not exceed 4096 x 4096 pixels.",
            code="image_too_large",
        )


def _build_invalid_image_error(message: str, code: str) -> InvalidImageError:
    return InvalidImageError(message, code=code)


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
    text = _strip_json_markdown(value)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise AnalysisFailedError(
            "GMS analysis result was not valid JSON.",
            code="analysis_result_invalid",
        )


def _textify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        for item in value:
            text = _textify(item)
            if text:
                return text
        return ""
    if isinstance(value, dict):
        for key in (
            "text",
            "summary",
            "reason",
            "이유",
            "추천",
            "recommendation",
            "name",
            "색상",
            "label",
            "title",
            "content",
        ):
            if key in value:
                text = _textify(value[key])
                if text:
                    return text
        return ""
    return str(value)


def _extract_response_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        for item in value:
            text = _extract_response_text(item)
            if text is not None:
                return text
        return None

    if not isinstance(value, dict):
        return None

    if value.get("type") in {"output_text", "text"} and "text" in value:
        text = _extract_response_text(value["text"])
        if text is not None:
            return text

    for key in ("content", "text", "output_text"):
        if key in value:
            text = _extract_response_text(value[key])
            if text is not None:
                return text

    message = value.get("message")
    if isinstance(message, dict) and "content" in message:
        text = _extract_response_text(message["content"])
        if text is not None:
            return text

    output = value.get("output")
    if output is not None:
        text = _extract_response_text(output)
        if text is not None:
            return text

    choices = value.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            return _extract_response_text(first_choice)

    return None


def _extract_gms_result(value: Any) -> Any:
    if isinstance(value, str):
        return _extract_gms_result(_parse_json_text(value))

    if isinstance(value, list):
        for item in value:
            extracted = _extract_gms_result(item)
            if extracted is not item:
                return extracted
        return value

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
            "추천색상",
        )
    ):
        return value

    response_text = _extract_response_text(value)
    if response_text is not None and response_text != value:
        return _extract_gms_result(response_text)

    for key in ("result", "analysis", "data", "output", "content", "text"):
        if key in value:
            extracted = _extract_gms_result(value[key])
            if extracted is not value[key] or isinstance(extracted, dict):
                return extracted

    return value


def _normalize_gms_api_style(value: Any) -> str:
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    normalized = normalized.replace("/", "_")

    if normalized in {"", "openai", "chat", "chat_completions"}:
        return "chat"
    if normalized in {"response", "responses"}:
        return "responses"
    return normalized


def _resolve_gms_request_style(api_url: str, configured_style: str) -> str:
    path = urlparse(api_url or "").path.rstrip("/").lower()

    if path.endswith("/responses"):
        return "responses"
    if path.endswith("/chat/completions"):
        return "chat"
    return configured_style


def _normalize_result_type_alias(value: Any) -> str:
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")

    if normalized in RESULT_TYPE_ORDER:
        return normalized
    if "spring" in normalized or "봄" in normalized:
        return PersonalColorAnalysis.ResultType.SPRING_WARM
    if "summer" in normalized or "여름" in normalized:
        return PersonalColorAnalysis.ResultType.SUMMER_COOL
    if "autumn" in normalized or "fall" in normalized or "가을" in normalized:
        return PersonalColorAnalysis.ResultType.AUTUMN_WARM
    if "winter" in normalized or "겨울" in normalized:
        return PersonalColorAnalysis.ResultType.WINTER_COOL
    if "cool" in normalized or "쿨" in normalized:
        if any(keyword in normalized for keyword in ("deep", "vivid", "clear", "winter", "블랙", "화이트", "차콜")):
            return PersonalColorAnalysis.ResultType.WINTER_COOL
        return PersonalColorAnalysis.ResultType.SUMMER_COOL
    if "warm" in normalized or "웜" in normalized:
        if any(keyword in normalized for keyword in ("autumn", "fall", "가을", "브라운", "카키", "올리브", "머스타드")):
            return PersonalColorAnalysis.ResultType.AUTUMN_WARM
        return PersonalColorAnalysis.ResultType.SPRING_WARM
    return PersonalColorAnalysis.ResultType.SPRING_WARM


def _season_preset(result_type: str) -> dict[str, Any]:
    preset = SEASON_PRESETS.get(result_type) or SEASON_PRESETS[
        PersonalColorAnalysis.ResultType.SPRING_WARM
    ]
    return {
        "label": preset["label"],
        "subtypes": list(preset["subtypes"]),
        "summary": preset["summary"],
        "best_colors": [dict(item) for item in preset["best_colors"]],
        "avoid_colors": [dict(item) for item in preset["avoid_colors"]],
        "recommendations": {
            key: list(value)
            for key, value in preset["recommendations"].items()
        },
        "analysis_metrics": dict(preset["analysis_metrics"]),
    }


def _default_reason_for_color(name: str, result_type: str) -> str:
    preset = _season_preset(result_type)
    if preset["best_colors"]:
        return f"{name}은(는) {preset['label']}에 잘 어울리는 색입니다."
    return f"{name}은(는) 개인 컬러 추천 색상입니다."


def _guess_hex_from_text(text: str, result_type: str) -> str:
    normalized = str(text or "").strip().lower()
    keyword_map = [
        ("코랄", "#F49A8A"),
        ("피치", "#F7B18A"),
        ("핑크", "#E6A7B5"),
        ("라벤더", "#C8B5F5"),
        ("보라", "#C8B5F5"),
        ("퍼플", "#C8B5F5"),
        ("블루", "#8EA4C8"),
        ("하늘", "#8EA4C8"),
        ("스카이", "#8EA4C8"),
        ("민트", "#CDE8C8"),
        ("연두", "#CDE8C8"),
        ("그린", "#CDE8C8"),
        ("그레이", "#B8BFC9"),
        ("회색", "#B8BFC9"),
        ("화이트", "#FFFFFF"),
        ("흰", "#FFFFFF"),
        ("블랙", "#2F343F"),
        ("검정", "#2F343F"),
        ("브라운", "#C19A6B"),
        ("갈색", "#C19A6B"),
        ("카멜", "#C19A6B"),
        ("베이지", "#D8B58B"),
        ("카키", "#6F7B3B"),
        ("올리브", "#6F7B3B"),
        ("옐로", "#F6D86B"),
        ("노랑", "#F6D86B"),
        ("오렌지", "#F58B64"),
        ("레드", "#D63B9B"),
        ("자홍", "#D63B9B"),
        ("버건디", "#7A2E3A"),
    ]

    for keyword, hex_value in keyword_map:
        if keyword in normalized:
            return hex_value

    preset = _season_preset(result_type)
    best_colors = preset["best_colors"]
    if best_colors:
        return best_colors[0]["hex"]
    return "#8EA4C8"


def _select_text(source: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = source.get(key)
        text = _textify(value).strip()
        if text:
            return text
    return ""


def _normalize_color_entry(
    item: Any,
    *,
    result_type: str,
    field_name: str,
) -> dict[str, str] | None:
    if isinstance(item, str):
        name = item.strip()
        if not name:
            return None
        return color_item(
            name,
            _guess_hex_from_text(name, result_type),
            _default_reason_for_color(name, result_type),
        )

    if not isinstance(item, dict):
        return None

    name = _select_text(item, ("name", "색상", "color", "label", "title"))
    hex_value = _select_text(item, ("hex", "색상코드", "color_hex", "colorCode"))
    reason = _select_text(
        item,
        ("reason", "이유", "description", "설명", "note", "추천"),
    )

    if not name and hex_value:
        name = hex_value

    if not name:
        return None

    if not hex_value:
        hex_value = _guess_hex_from_text(name, result_type)
    else:
        hex_value = hex_value.upper()
        if not hex_value.startswith("#") or len(hex_value) != 7:
            hex_value = _guess_hex_from_text(name, result_type)

    if not reason:
        reason = _default_reason_for_color(name, result_type)

    return color_item(name, hex_value, reason)


def _normalize_color_entries(
    value: Any,
    *,
    result_type: str,
    field_name: str,
    fallback: list[dict[str, str]],
) -> list[dict[str, str]]:
    if value is None or value == "":
        return [dict(item) for item in fallback]

    items = value if isinstance(value, list) else [value]
    normalized_entries: list[dict[str, str]] = []

    for item in items:
        normalized = _normalize_color_entry(
            item,
            result_type=result_type,
            field_name=field_name,
        )
        if normalized is not None:
            normalized_entries.append(normalized)

    if not normalized_entries:
        return [dict(item) for item in fallback]

    return normalized_entries


def _normalize_recommendations(
    value: Any,
    *,
    fallback: dict[str, list[str]],
    primary_text: str = "",
) -> dict[str, list[str]]:
    normalized = {
        key: list(items)
        for key, items in fallback.items()
    }

    if isinstance(value, dict):
        for key in ("clothing", "makeup", "accessories"):
            items = value.get(key)
            if items is None:
                continue
            if isinstance(items, str):
                items = [items]
            if not isinstance(items, list):
                continue

            cleaned = []
            for item in items:
                text = _textify(item).strip()
                if text:
                    cleaned.append(text)

            if cleaned:
                normalized[key] = cleaned

    if primary_text:
        cleaned_primary = primary_text.strip()
        if cleaned_primary and cleaned_primary not in normalized["clothing"]:
            normalized["clothing"] = [cleaned_primary, *normalized["clothing"]]

    return normalized


def _normalize_metrics(value: Any, *, fallback: dict[str, float]) -> dict[str, float]:
    if not isinstance(value, dict):
        return dict(fallback)

    normalized: dict[str, float] = {}
    for key in ("warmth", "brightness", "saturation", "contrast"):
        raw_value = value.get(key)
        try:
            metric_value = float(raw_value)
        except (TypeError, ValueError):
            metric_value = fallback[key]

        if 0 <= metric_value <= 1:
            normalized[key] = round(metric_value, 2)
        elif 0 <= metric_value <= 100:
            normalized[key] = round(metric_value / 100, 2)
        else:
            normalized[key] = fallback[key]

    return normalized


def _normalize_confidence(value: Any, *, default: float = 80.0) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return round(default, 2)

    if 0 <= confidence <= 1:
        confidence *= 100

    if confidence < 0:
        confidence = 0
    if confidence > 100:
        confidence = 100

    return round(confidence, 2)


def _build_primary_color_bundle(
    bundle: Any,
    *,
    result_type: str,
) -> list[dict[str, str]]:
    if bundle is None:
        return []

    if isinstance(bundle, list):
        source = bundle[0] if bundle else None
    else:
        source = bundle

    normalized = _normalize_color_entry(
        source,
        result_type=result_type,
        field_name="best_colors",
    )
    if normalized is None:
        return []
    return [normalized]


def _infer_result_type_from_text(text: str) -> str:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return PersonalColorAnalysis.ResultType.SPRING_WARM

    if "winter" in normalized or "겨울" in normalized:
        return PersonalColorAnalysis.ResultType.WINTER_COOL
    if "autumn" in normalized or "fall" in normalized or "가을" in normalized:
        return PersonalColorAnalysis.ResultType.AUTUMN_WARM
    if "spring" in normalized or "봄" in normalized:
        return PersonalColorAnalysis.ResultType.SPRING_WARM
    if "summer" in normalized or "여름" in normalized:
        return PersonalColorAnalysis.ResultType.SUMMER_COOL

    if "쿨" in normalized or "cool" in normalized:
        if any(
            keyword in normalized
            for keyword in ("딥", "vivid", "clear", "블랙", "화이트", "차콜", "네이비")
        ):
            return PersonalColorAnalysis.ResultType.WINTER_COOL
        return PersonalColorAnalysis.ResultType.SUMMER_COOL

    if "웜" in normalized or "warm" in normalized:
        if any(
            keyword in normalized
            for keyword in ("브라운", "카키", "올리브", "머스타드", "테라코타", "deep")
        ):
            return PersonalColorAnalysis.ResultType.AUTUMN_WARM
        return PersonalColorAnalysis.ResultType.SPRING_WARM

    if any(keyword in normalized for keyword in ("핑크", "코랄", "피치")):
        return PersonalColorAnalysis.ResultType.SPRING_WARM

    return PersonalColorAnalysis.ResultType.SPRING_WARM


def _extract_primary_recommendation(result: dict[str, Any]) -> dict[str, Any] | None:
    for key in (
        "추천색상",
        "recommendation",
        "recommendations",
        "best_color",
        "bestColor",
        "primary_color",
    ):
        candidate = result.get(key)
        if candidate is None:
            continue
        if isinstance(candidate, list):
            if not candidate:
                continue
            candidate = candidate[0]
        if isinstance(candidate, dict):
            return candidate
        if isinstance(candidate, str):
            return {"색상": candidate}
    return None


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

    primary_bundle = _extract_primary_recommendation(result)
    if "best_colors" not in result and primary_bundle is not None:
        result["best_colors"] = [primary_bundle]

    summary_source = _select_text(
        result,
        ("summary", "요약", "analysis_summary", "description"),
    )
    primary_reason = ""
    if primary_bundle is not None:
        primary_reason = _select_text(
            primary_bundle,
            ("reason", "이유", "recommendation", "추천", "description", "설명"),
        )

    color_name = ""
    if primary_bundle is not None:
        color_name = _select_text(
            primary_bundle,
            ("name", "색상", "color", "label", "title"),
        )
    if not color_name:
        color_name = _select_text(
            result,
            ("result_subtype", "subtype", "추천색상", "best_color"),
        )

    if "result_type" in result:
        result["result_type"] = _normalize_result_type_alias(result["result_type"])
    else:
        infer_text = " ".join(
            text
            for text in (
                color_name,
                summary_source,
                _textify(primary_bundle),
                _textify(result.get("best_colors")),
            )
            if text
        )
        result["result_type"] = _infer_result_type_from_text(infer_text)

    preset = _season_preset(result["result_type"])

    result["result_subtype"] = _select_text(
        result,
        ("result_subtype", "subtype", "resultSubtype"),
    ) or color_name or preset["label"]

    result["confidence"] = _normalize_confidence(
        result.get("confidence"),
        default=80.0,
    )

    summary = summary_source.strip()
    if not summary:
        if color_name and primary_bundle is not None:
            summary = f"{color_name}이 잘 어울립니다."
            if primary_reason:
                summary = f"{summary} {primary_reason}"
        else:
            summary = preset["summary"]
    result["summary"] = summary

    result["best_colors"] = _normalize_color_entries(
        result.get("best_colors"),
        result_type=result["result_type"],
        field_name="best_colors",
        fallback=preset["best_colors"],
    )

    if not result["best_colors"] and color_name:
        result["best_colors"] = _build_primary_color_bundle(
            primary_bundle or {"색상": color_name},
            result_type=result["result_type"],
        )

    result["avoid_colors"] = _normalize_color_entries(
        result.get("avoid_colors"),
        result_type=result["result_type"],
        field_name="avoid_colors",
        fallback=preset["avoid_colors"],
    )

    primary_recommendation_text = ""
    if primary_bundle is not None:
        primary_recommendation_text = _select_text(
            primary_bundle,
            ("recommendation", "추천", "reason", "이유", "description", "설명"),
        )
    result["recommendations"] = _normalize_recommendations(
        result.get("recommendations"),
        fallback=preset["recommendations"],
        primary_text=primary_recommendation_text,
    )

    result["analysis_metrics"] = _normalize_metrics(
        result.get("analysis_metrics"),
        fallback=preset["analysis_metrics"],
    )

    result["provider_name"] = str(result.get("provider_name") or provider_name).strip()
    result["model_version"] = str(result.get("model_version") or model_version).strip()

    return result


class MockPersonalColorProvider(PersonalColorProvider):
    name = "mock"
    model_version = "mock-v1"

    def analyze(self, prepared_image: PreparedPersonalColorImage) -> dict[str, Any]:
        seed = int(prepared_image.sha256_hex, 16)
        rng = random.Random(seed)
        result_type = RESULT_TYPE_ORDER[seed % len(RESULT_TYPE_ORDER)]
        preset = _season_preset(result_type)
        subtype = rng.choice(preset["subtypes"])

        best_colors = [dict(item) for item in preset["best_colors"]]
        avoid_colors = [dict(item) for item in preset["avoid_colors"]]
        rng.shuffle(best_colors)
        rng.shuffle(avoid_colors)

        return {
            "result_type": result_type,
            "result_subtype": subtype,
            "confidence": round(78 + rng.random() * 18, 2),
            "summary": preset["summary"],
            "best_colors": best_colors,
            "avoid_colors": avoid_colors,
            "recommendations": {
                key: list(value)
                for key, value in preset["recommendations"].items()
            },
            "analysis_metrics": _build_metrics(result_type, seed),
            "provider_name": self.name,
            "model_version": self.model_version,
        }


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
        configured_style = _normalize_gms_api_style(
            api_style or str(_get_setting("GMS_API_STYLE", "chat")) or "chat"
        )
        self.api_style = configured_style
        self.request_style = _resolve_gms_request_style(self.api_url, configured_style)
        self.timeout = timeout or _get_gms_timeout()
        self.model_version = self.model or "gms"

        missing = []
        if not self.api_url:
            missing.append("GMS_API_URL")
        if not self.api_key:
            missing.append("GMS_API_KEY")
        if not self.model:
            missing.append("GMS_MODEL")

        if missing:
            raise AnalysisProviderUnavailableError(
                f"GMS API configuration is missing: {', '.join(missing)}",
                code="analysis_provider_unavailable",
            )

        if self.request_style not in {"chat", "responses"}:
            raise AnalysisProviderUnavailableError(
                f"Unsupported GMS API style: {self.request_style!r}",
                code="analysis_provider_unavailable",
            )

    def analyze(self, prepared_image: PreparedPersonalColorImage) -> dict[str, Any]:
        payload = self._build_payload(prepared_image)

        logger.info(
            "Sending GMS personal color request: url=%s configured_style=%s request_style=%s model=%s",
            self.api_url,
            self.api_style,
            self.request_style,
            self.model or "<missing>",
        )

        request = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
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
        normalized = _normalize_gms_result_shape(
            extracted,
            provider_name=self.name,
            model_version=self.model_version,
        )
        return validate_normalized_result(normalized)

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
        image_url = _build_image_data_url(prepared_image)

        if self.request_style == "responses":
            return {
                "model": self.model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": GMS_PERSONAL_COLOR_PROMPT,
                            },
                            {
                                "type": "input_image",
                                "image_url": image_url,
                            },
                        ],
                    }
                ],
            }

        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": GMS_PERSONAL_COLOR_PROMPT,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            "max_completion_tokens": DEFAULT_MAX_COMPLETION_TOKENS,
        }

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

        message = "GMS API request failed."
        body_lower = response_body.lower()
        if exc.code == 400 and "model not found" in body_lower:
            message = (
                "GMS API rejected the model for this domain. "
                f"url={self.api_url} model={self.model or '<missing>'}."
            )
        elif exc.code == 403 and "target domain" in body_lower:
            message = (
                "GMS API rejected the target domain. "
                f"url={self.api_url}."
            )

        raise AnalysisProviderUnavailableError(
            message,
            code="analysis_provider_unavailable",
        ) from exc


def _build_image_data_url(prepared_image: PreparedPersonalColorImage) -> str:
    return f"data:image/png;base64,{base64.b64encode(prepared_image.normalized_bytes).decode('ascii')}"


def _build_metrics(result_type: str, seed: int) -> dict[str, float]:
    config = SEASON_PRESETS[result_type]["analysis_metrics"]
    rng = random.Random(seed ^ 0x5F3759DF)
    return {
        metric: _clamp(
            round(base + (rng.random() - 0.5) * spread, 2),
            0.0,
            1.0,
        )
        for metric, (base, spread) in {
            "warmth": (config["warmth"], 0.08),
            "brightness": (config["brightness"], 0.08),
            "saturation": (config["saturation"], 0.08),
            "contrast": (config["contrast"], 0.08),
        }.items()
    }


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def prepare_uploaded_image(image_file) -> PreparedPersonalColorImage:
    if image_file is None:
        raise _build_invalid_image_error(
            "An image file is required.",
            "image_required",
        )

    original_name = getattr(image_file, "name", "") or ""
    content_type = _normalize_content_type(getattr(image_file, "content_type", None))
    extension = _normalize_extension(original_name)
    size = int(getattr(image_file, "size", 0) or 0)

    if size <= 0:
        raise _build_invalid_image_error(
            "The uploaded image is invalid.",
            "invalid_image",
        )

    if size > MAX_UPLOAD_SIZE_BYTES:
        raise _build_invalid_image_error(
            "The file must be 10MB or smaller.",
            "file_too_large",
        )

    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise _build_invalid_image_error(
            "Only JPEG, PNG, and WEBP images are supported.",
            "unsupported_image_type",
        )

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise _build_invalid_image_error(
            "Only JPEG, PNG, and WEBP images are supported.",
            "unsupported_image_type",
        )

    if extension not in MIME_TYPE_EXTENSIONS.get(content_type, set()):
        raise _build_invalid_image_error(
            "The file extension does not match the MIME type.",
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
            "The file must be 10MB or smaller.",
            "file_too_large",
        )

    try:
        with Image.open(io.BytesIO(raw_bytes)) as preview_image:
            preview_image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise _build_invalid_image_error(
            "The image file is corrupted.",
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
            "The image file is corrupted.",
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
        "AI analysis provider is not configured.",
        code="analysis_provider_unavailable",
    )


def validate_normalized_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise AnalysisFailedError(
            "Personal color analysis result format was invalid.",
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
            "Personal color analysis result is missing required fields.",
            code="analysis_result_invalid",
        )

    result_type = _normalize_result_type_alias(result["result_type"])
    if result_type not in RESULT_TYPE_ORDER:
        raise AnalysisFailedError(
            "Personal color analysis result type is invalid.",
            code="analysis_result_invalid",
        )

    result_subtype = str(result["result_subtype"]).strip()
    if not result_subtype:
        raise AnalysisFailedError(
            "Personal color analysis result subtype is empty.",
            code="analysis_result_invalid",
        )

    summary = str(result["summary"]).strip()
    if not summary:
        raise AnalysisFailedError(
            "Personal color analysis summary is empty.",
            code="analysis_result_invalid",
        )

    best_colors = _normalize_color_entries(
        result["best_colors"],
        result_type=result_type,
        field_name="best_colors",
        fallback=[],
    )
    avoid_colors = _normalize_color_entries(
        result["avoid_colors"],
        result_type=result_type,
        field_name="avoid_colors",
        fallback=[],
    )
    recommendations = _normalize_recommendations(
        result["recommendations"],
        fallback={key: [] for key in ("clothing", "makeup", "accessories")},
    )
    analysis_metrics = _normalize_metrics(
        result["analysis_metrics"],
        fallback={
            "warmth": 0.5,
            "brightness": 0.5,
            "saturation": 0.5,
            "contrast": 0.5,
        },
    )

    if not best_colors:
        raise AnalysisFailedError(
            "Personal color analysis best colors are missing.",
            code="analysis_result_invalid",
        )

    normalized = {
        "result_type": result_type,
        "result_subtype": result_subtype,
        "confidence": _normalize_confidence(result["confidence"]),
        "summary": summary,
        "best_colors": best_colors,
        "avoid_colors": avoid_colors,
        "recommendations": recommendations,
        "analysis_metrics": analysis_metrics,
        "provider_name": str(result["provider_name"]).strip(),
        "model_version": str(result["model_version"]).strip(),
    }

    return normalized


def analyze_prepared_image(prepared_image: PreparedPersonalColorImage) -> dict[str, Any]:
    provider = get_personal_color_provider()

    if getattr(provider, "supports_face_detection", False):
        provider.ensure_face_present(prepared_image)

    try:
        raw_result = provider.analyze(prepared_image)
    except (
        InvalidImageError,
        FaceNotDetectedError,
        AnalysisProviderUnavailableError,
    ):
        raise
    except AnalysisFailedError as exc:
        if getattr(provider, "name", "") == "gms":
            logger.warning("GMS API returned invalid analysis result: %s", exc.message)
            raise AnalysisProviderUnavailableError(
                exc.message,
                code=exc.code,
            ) from exc
        raise
    except Exception as exc:
        raise AnalysisFailedError(
            "Personal color analysis request failed.",
            code="analysis_failed",
        ) from exc

    if not isinstance(raw_result, dict):
        raise AnalysisFailedError(
            "Personal color analysis result format was invalid.",
            code="analysis_result_invalid",
        )

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
