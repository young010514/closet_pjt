from rest_framework import serializers

from regions.serializers import RegionSerializer

from .models import Store


class StoreListSerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)
    display_name = serializers.SerializerMethodField()
    region_label = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = (
            "id",
            "external_store_id",
            "name",
            "branch_name",
            "display_name",
            "category_code",
            "category_name",
            "region",
            "region_label",
            "address",
            "jibun_address",
            "road_address",
            "longitude",
            "latitude",
            "phone",
            "website_url",
            "view_count",
        )
        read_only_fields = fields

    def get_display_name(self, obj):
        return str(obj)

    def get_region_label(self, obj):
        return obj.region.full_name if obj.region_id else ""

    def get_address(self, obj):
        return obj.full_address

