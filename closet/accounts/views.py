# 검증 필요

from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
# 필요한 폼이 있다면 여기에 import 하세요
# from .forms import NormalUserCreationForm, BusinessUserCreationForm, CustomLoginForm

def signup_select(request):
    """
    회원가입 유형 선택 페이지 (일반 회원 / 기업 회원)
    """
    return render(request, "accounts/signup_select.html")


def normal_signup(request):
    """
    일반 회원가입 처리
    """
    if request.method == "POST":
        # 폼 데이터 검증 및 저장 로직 구현 필요
        pass
    else:
        # 폼 생성
        pass
    return render(request, "accounts/normal_signup.html")


def business_signup(request):
    """
    기업 회원가입 처리
    """
    if request.method == "POST":
        # 폼 데이터 검증 및 저장 로직 구현 필요
        pass
    else:
        # 폼 생성
        pass
    return render(request, "accounts/business_signup.html")


def login_view(request):
    """
    로그인 처리
    """
    if request.method == "POST":
        # 로그인 인증 로직 구현 필요
        pass
    else:
        # 로그인 폼 생성
        pass
    return render(request, "accounts/login.html")


def logout_view(request):
    """
    로그아웃 처리 후 메인 페이지 등으로 리다이렉트
    """
    auth_logout(request)
    return redirect("index")  # 'index'는 메인 페이지 url name에 맞게 변경하세요.


def mypage(request):
    """
    마이페이지 (일반적으로 로그인 필요)
    """
    # @login_required 데코레이터를 붙이거나 request.user.is_authenticated 확인 필요
    return render(request, "accounts/mypage.html")