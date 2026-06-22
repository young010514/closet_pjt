from rest_framework import serializers

from .models import Region


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ("id", "sido", "sigungu", "dong")
        read_only_fields = fields
