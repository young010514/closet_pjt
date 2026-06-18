# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    User,
    UserProfile,
    UserRegion,
    Follow,
    BusinessProfile,
    TermsAgreement,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # 관리자 페이지에서 사용자 추가 시 이메일도 입력
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "필수 정보",
            {
                "fields": (
                    "email",
                )
            },
        ),
    )


admin.site.register(UserProfile)
admin.site.register(UserRegion)
admin.site.register(Follow)
admin.site.register(BusinessProfile)
admin.site.register(TermsAgreement)