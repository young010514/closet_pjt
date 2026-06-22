from django.urls import path

from . import views


app_name = "regions"


urlpatterns = [
    path("sidos/", views.SidoListView.as_view(), name="sido_list"),
    path("sigungus/", views.SigunguListView.as_view(), name="sigungu_list"),
    path("dongs/", views.DongListView.as_view(), name="dong_list"),
]
