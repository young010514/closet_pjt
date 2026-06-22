from django.urls import path

from . import views


app_name = "accounts"


urlpatterns = [
    path("csrf/", views.csrf_token, name="csrf_token"),
    path("signup/", views.signup_select, name="signup_select"),
    path("signup/normal/", views.normal_signup, name="normal_signup"),
    path("signup/business/", views.business_signup, name="business_signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("mypage/", views.mypage, name="mypage"),
    path("me/regions/", views.MyRegionView.as_view(), name="my_regions"),
    path(
        "regions/reorder/",
        views.reorder_user_regions,
        name="reorder_user_regions",
    ),
]
