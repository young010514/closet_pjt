# 지켜야할 사항
1. pip install 하면 requirements.txt 업데이트 해놓기
2. common/models.py
    L 여러 앱에서 공통적으로 사용할 모델들

# 프로젝트 구조
프로젝트 명 : closet
closet
 L settings.py
 L urls.py
commons (기본 템플릿 관리)
 L models.py
 L forms.py
 L urls.py
 L views.py
accounts (회원 관리)
 L models.py
 L forms.py
 L urls.py
 L views.py
regions (지역)
 L models.py
 L forms.py
 L urls.py
 L views.py
community (커뮤니티)
 L models.py
 L forms.py
 L urls.py
 L views.py
