from django.urls import path
from . import views

app_name = "regions"

urlpatterns = [
    path("", views.region_list, name="region_list"),
]