from django.urls import path

from .views import (
    PersonalColorAnalysisDetailView,
    PersonalColorAnalysisListCreateView,
)


urlpatterns = [
    path("analyses/", PersonalColorAnalysisListCreateView.as_view(), name="personal-color-analysis-list"),
    path(
        "analyses/<int:pk>/",
        PersonalColorAnalysisDetailView.as_view(),
        name="personal-color-analysis-detail",
    ),
]

