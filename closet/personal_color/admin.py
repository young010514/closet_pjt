from django.contrib import admin

from .models import PersonalColorAnalysis


@admin.register(PersonalColorAnalysis)
class PersonalColorAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "result_type",
        "result_subtype",
        "confidence",
        "provider_name",
        "created_at",
    )
    list_select_related = ("user",)
    list_filter = ("result_type", "provider_name", "created_at")
    search_fields = ("user__username", "user__email", "result_subtype", "provider_name")
    ordering = ("-created_at",)

