# accounts/utils.py
# 공통함수 담는 곳

def normalize_account_email(email: str) -> str:
    return email.strip().lower()