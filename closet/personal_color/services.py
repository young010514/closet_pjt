import base64
import http.client
import json
import mimetypes
import urllib.error
import urllib.request
from io import BytesIO
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from PIL import Image, UnidentifiedImageError

from .exceptions import (
    AnalysisFailedError,
    AnalysisProviderUnavailableError,
    InvalidImageError,
)
from .models import PersonalColorAnalysis


GMS_PERSONAL_COLOR_JSON_PROMPT = (
    "Return only valid JSON. No markdown. No explanation. "
    "Analyze this face image for personal color. Use Korean text except result_type. "
    "Keep every value concise. "
    "JSON keys: result_type, confidence, summary, best_colors, avoid_colors, recommendations. "
    "result_type must be exactly one of: spring_warm, summer_cool, autumn_warm, winter_cool. "
    "confidence must be a number from 0 to 100. "
    "best_colors must be an array of 5 Korean color objects. "
    "avoid_colors must be an array of 5 Korean color objects. "
    'Each color object must be {"name":"string","hex":"#RRGGBB","reason":"string"}. '
    "hex must be a valid 6-digit HEX color used for UI swatches and copy buttons. "
    "recommendations must be an object with keys: clothing, makeup, accessories. "
    "recommendations.clothing must be an array of 3 Korean strings for clothing styles and colors. "
    "recommendations.makeup must be an array of 3 Korean strings for makeup colors and tones. "
    "recommendations.accessories must be an array of 3 Korean strings for accessories, jewelry, or styling items. "
    'Return this JSON shape with 5 best_colors and 5 avoid_colors: {"result_type":"spring_warm","confidence":90,'
    '"summary":"string","best_colors":[{"name":"string","hex":"#RRGGBB","reason":"string"}],'
    '"avoid_colors":[{"name":"string","hex":"#RRGGBB","reason":"string"}],'
    '"recommendations":{"clothing":["string","string","string"],'
    '"makeup":["string","string","string"],'
    '"accessories":["string","string","string"]}}'
)

ALLOWED_IMAGE_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)
MAX_IMAGE_BYTES = 10 * 1024 * 1024


_GMS_RESULT_TYPE_KEYWORDS = (
    (("spring_warm", "spring"), "spring_warm"),
    (("summer_cool", "summer"), "summer_cool"),
    (("autumn_warm", "autumn", "fall"), "autumn_warm"),
    (("winter_cool", "winter"), "winter_cool"),
)

def _required_setting(name: str) -> str:
    value = getattr(settings, name, None)
    if value is None:
        raise ImproperlyConfigured(f"{name} setting is required for GMS API requests.")

    value = str(value).strip()
    if not value:
        raise ImproperlyConfigured(f"{name} setting is required for GMS API requests.")

    return value


def _optional_setting(name: str, default: str) -> str:
    value = getattr(settings, name, default)
    value = str(value).strip()
    return value or default


def _gms_timeout_seconds() -> float:
    value = getattr(settings, "GMS_TIMEOUT_SECONDS", None)
    if value is None:
        raise ImproperlyConfigured(
            "GMS_TIMEOUT_SECONDS setting is required for GMS API requests."
        )

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            "GMS_TIMEOUT_SECONDS setting must be a number."
        ) from exc


def _read_response_body(response: Any) -> bytes:
    try:
        return response.read()
    except http.client.IncompleteRead as exc:
        if not exc.partial:
            raise
        return exc.partial


def _loads_response_json(response_body: bytes) -> dict[str, Any]:
    response_text = response_body.decode("utf-8")
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as exc:
        stripped_text = response_text.lstrip()
        candidate_starts = [
            stripped_text.find(key)
            for key in (
                '"object"',
                '"created"',
                '"model"',
                '"choices"',
                '"usage"',
                '"service_tier"',
                '"system_fingerprint"',
            )
            if stripped_text.find(key) != -1
        ]
        if candidate_starts:
            start = min(candidate_starts)
            try:
                return json.loads("{" + stripped_text[start:])
            except json.JSONDecodeError:
                pass
        raise exc


def _guess_image_mime_type(image_file: Any) -> str:
    content_type = str(getattr(image_file, "content_type", "") or "").strip()
    if content_type:
        return content_type

    name = str(getattr(image_file, "name", "") or "")
    guessed_type = mimetypes.guess_type(name)[0]
    return guessed_type or "image/jpeg"


def _read_image_bytes(image_file: Any) -> bytes:
    if not hasattr(image_file, "read"):
        raise TypeError("image_file must be a file-like object with a read() method.")

    if hasattr(image_file, "seek"):
        try:
            image_file.seek(0)
        except (OSError, ValueError):
            pass

    image_bytes = image_file.read()
    if isinstance(image_bytes, bytearray):
        image_bytes = bytes(image_bytes)
    if not isinstance(image_bytes, bytes):
        raise TypeError("image_file.read() must return bytes.")
    if not image_bytes:
        raise ValueError("image_file must not be empty.")

    return image_bytes


def _build_image_data_url(image_file: Any) -> str:
    mime_type = _guess_image_mime_type(image_file)
    image_base64 = base64.b64encode(_read_image_bytes(image_file)).decode("ascii")
    return f"data:{mime_type};base64,{image_base64}"


def validate_uploaded_image(image_file: Any) -> Any:
    mime_type = _guess_image_mime_type(image_file).lower()
    if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise InvalidImageError(
            "Unsupported image type.",
            code="unsupported_image_type",
        )

    size = getattr(image_file, "size", None)
    if size is not None and int(size) > MAX_IMAGE_BYTES:
        raise InvalidImageError(
            "Image file is too large.",
            code="file_too_large",
        )

    try:
        image_bytes = _read_image_bytes(image_file)
    except (TypeError, ValueError) as exc:
        raise InvalidImageError(
            "Image file is invalid.",
            code="corrupted_image",
        ) from exc

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise InvalidImageError(
            "Image file is too large.",
            code="file_too_large",
        )

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError(
            "Image file is corrupted.",
            code="corrupted_image",
        ) from exc

    if hasattr(image_file, "seek"):
        try:
            image_file.seek(0)
        except (OSError, ValueError):
            pass

    return image_file

def _normalize_gms_result_type(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("result_type is required in GMS personal color result.")

    normalized_text = text.casefold().replace("-", "_").replace(" ", "_")
    for keywords, result_type in _GMS_RESULT_TYPE_KEYWORDS:
        if normalized_text == result_type:
            return result_type

        for keyword in keywords:
            if keyword.casefold() in normalized_text:
                return result_type

    raise ValueError(
        "result_type must map to one of: "
        "spring_warm, summer_cool, autumn_warm, winter_cool."
    )


def _normalize_gms_list(value: Any, field_name: str, notes: list[str]) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        notes.append(f"{field_name}: tuple converted to list")
        return list(value)

    notes.append(f"{field_name}: scalar converted to list")
    return [value]


def _normalize_gms_recommendations(
    value: Any,
    notes: list[str],
) -> dict[str, list[Any]]:
    recommendations = {
        "clothing": [],
        "makeup": [],
        "accessories": [],
    }

    if value is None or value == "":
        return recommendations

    if isinstance(value, dict):
        for key in recommendations:
            recommendations[key] = _normalize_gms_list(
                value.get(key),
                f"recommendations.{key}",
                notes,
            )
        return recommendations

    recommendations["clothing"] = _normalize_gms_list(
        value,
        "recommendations",
        notes,
    )
    notes.append("recommendations: non-object stored as clothing recommendations")
    return recommendations


def _normalize_gms_confidence(
    result: dict[str, Any],
    notes: list[str] | None = None,
) -> float:
    if "confidence" not in result:
        raise ValueError("confidence is required in GMS personal color result.")

    raw_confidence = result["confidence"]
    try:
        if isinstance(raw_confidence, str):
            confidence_text = raw_confidence.strip()
            if confidence_text.endswith("%"):
                confidence = float(confidence_text[:-1].strip())
                if notes is not None:
                    notes.append("confidence: percent string converted to number")
            else:
                confidence = float(confidence_text)
        else:
            confidence = float(raw_confidence)
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence must be a number.") from exc

    if 0 <= confidence <= 1:
        confidence *= 100
        if notes is not None:
            notes.append("confidence: 0-1 value converted to 0-100 scale")

    if not 0 <= confidence <= 100:
        raise ValueError("confidence must be between 0 and 100.")

    return confidence


def normalize_gms_personal_color_result(result: dict[str, Any]) -> dict[str, Any]:
    """Normalize GMS personal color JSON into PersonalColorAnalysis fields."""

    if not isinstance(result, dict):
        raise TypeError("result must be a dict.")

    notes: list[str] = []
    avoid_colors_source = result.get("avoid_colors")
    if avoid_colors_source is None:
        avoid_colors_source = result.get("worst_colors")

    best_colors = _normalize_gms_list(
        result.get("best_colors"),
        "best_colors",
        notes,
    )
    avoid_colors = _normalize_gms_list(
        avoid_colors_source,
        "avoid_colors",
        notes,
    )
    recommendations = _normalize_gms_recommendations(
        result.get("recommendations"),
        notes,
    )
    confidence = _normalize_gms_confidence(result, notes)

    analysis_metrics: dict[str, Any] = {"raw_result": result}
    if notes:
        analysis_metrics["normalization_notes"] = notes

    return {
        "result_type": _normalize_gms_result_type(result.get("result_type")),
        "result_subtype": result.get("result_subtype") or "",
        "confidence": confidence,
        "summary": result.get("summary") or "",
        "best_colors": best_colors,
        "avoid_colors": avoid_colors,
        "recommendations": recommendations,
        "analysis_metrics": analysis_metrics,
        "provider_name": "gms",
        "model_version": _required_setting("GMS_MODEL"),
    }

def request_gms_json(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    max_completion_tokens: int = 500,
) -> dict[str, Any]:
    """Send a minimal Chat Completions JSON request to GMS and return its JSON body."""

    api_url = _required_setting("GMS_API_URL")
    api_key = _required_setting("GMS_API_KEY")
    if model is None:
        resolved_model = _required_setting("GMS_MODEL")
    else:
        resolved_model = str(model).strip()
        if not resolved_model:
            raise ImproperlyConfigured(
                "GMS_MODEL setting is required for GMS API requests."
            )

    key_header = _optional_setting("GMS_API_KEY_HEADER", "Authorization")
    auth_prefix = _optional_setting("GMS_API_AUTH_PREFIX", "Bearer")
    auth_value = f"{auth_prefix} {api_key}" if auth_prefix else api_key

    payload = {
        "model": resolved_model,
        "messages": messages,
        "max_completion_tokens": max_completion_tokens,
    }
    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            key_header: auth_value,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=_gms_timeout_seconds()) as response:
            response_body = _read_response_body(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise AnalysisProviderUnavailableError(
            "GMS API request failed.",
            code="analysis_provider_unavailable",
        ) from exc

    try:
        return _loads_response_json(response_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AnalysisFailedError(
            "GMS API response was not valid JSON.",
            code="analysis_failed",
        ) from exc


def request_gms_personal_color_json(
    image_file: Any,
    *,
    max_completion_tokens: int = 1500,
) -> dict[str, Any]:
    image_url = _build_image_data_url(image_file)
    response = request_gms_json(
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": GMS_PERSONAL_COLOR_JSON_PROMPT,
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
        max_completion_tokens=max_completion_tokens,
    )
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AnalysisFailedError(
            "GMS API response did not include message content.",
            code="analysis_failed",
        ) from exc

    try:
        result = json.loads(content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise AnalysisFailedError(
            "GMS personal color content was not valid JSON.",
            code="analysis_failed",
        ) from exc

    if not isinstance(result, dict):
        raise AnalysisFailedError(
            "GMS personal color result must be a JSON object.",
            code="analysis_failed",
        )

    return result



def create_gms_personal_color_analysis(
    user: Any,
    image_file: Any,
) -> PersonalColorAnalysis:
    raw_result = request_gms_personal_color_json(image_file)
    try:
        normalized_result = normalize_gms_personal_color_result(raw_result)
    except (TypeError, ValueError) as exc:
        raise AnalysisFailedError(
            "GMS personal color result is missing required fields.",
            code="analysis_failed",
        ) from exc
    return PersonalColorAnalysis.objects.create(user=user, **normalized_result)

__all__ = [
    "validate_uploaded_image",
    "create_gms_personal_color_analysis",
    "normalize_gms_personal_color_result",
    "request_gms_json",
    "request_gms_personal_color_json",
]
