from rest_framework import serializers

from .exceptions import InvalidImageError
from .models import PersonalColorAnalysis
from .services_VER2 import (
    create_personal_color_analysis,
    prepare_uploaded_image,
)


class PersonalColorAnalysisSerializer(serializers.ModelSerializer):
    result_label = serializers.SerializerMethodField()
    confidence = serializers.SerializerMethodField()

    class Meta:
        model = PersonalColorAnalysis
        fields = (
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
        )
        read_only_fields = fields

    def get_result_label(self, obj):
        return obj.get_result_type_display()

    def get_confidence(self, obj):
        return float(obj.confidence)


class PersonalColorAnalysisCreateSerializer(serializers.Serializer):
    image = serializers.FileField(required=False, allow_empty_file=False)

    def validate(self, attrs):
        image = attrs.get("image")
        if image is None:
            raise serializers.ValidationError(
                {
                    "detail": "이미지 파일을 선택해 주세요.",
                    "code": "image_required",
                }
            )

        try:
            prepared_image = prepare_uploaded_image(image)
        except InvalidImageError as exc:
            raise serializers.ValidationError(
                {
                    "detail": exc.message,
                    "code": exc.code,
                }
            ) from exc

        attrs["_prepared_image"] = prepared_image
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError(
                {
                    "detail": "로그인이 필요합니다.",
                    "code": "not_authenticated",
                }
            )

        prepared_image = validated_data["_prepared_image"]
        return create_personal_color_analysis(
            user=request.user,
            prepared_image=prepared_image,
        )
