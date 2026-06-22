from django.contrib import admin

from .models import Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "branch_name",
        "region",
        "category_name",
        "view_count",
        "is_active",
    )
    list_filter = ("is_active", "region")
    search_fields = (
        "name",
        "branch_name",
        "external_store_id",
        "category_name",
        "jibun_address",
        "road_address",
    )
    ordering = ("name", "branch_name", "id")
