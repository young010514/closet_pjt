from django.urls import path

from . import views

app_name = "stores"

urlpatterns = [
    path("", views.store_list, name="store_list"),
    path("list/", views.store_list, name="store_list_legacy"),
]
