from django.contrib import admin
from .models import Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "sido", "sigungu", "dong", "region_code", "is_active")
    list_filter = ("sido", "sigungu", "is_active")
    search_fields = ("sido", "sigungu", "dong", "region_code")
    ordering = ("sido", "sigungu", "dong")