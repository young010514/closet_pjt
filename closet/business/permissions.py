from rest_framework.permissions import BasePermission


class IsBusinessUser(BasePermission):
    message = '사업자 회원만 접근할 수 있습니다.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.user_type == 'business'
        except Exception:
            return False
