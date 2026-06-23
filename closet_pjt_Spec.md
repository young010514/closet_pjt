# Closet PJT - 사업자 기능 기술 명세서 (Technical Spec)

> 작성 대상: 백엔드/프론트엔드 개발자
> 작성일: 2026년 6월
> 기준 코드: accounts/models.py, accounts/views.py, posts/models.py, posts/views.py

---

## 1. 기술 스택

| 구분 | 기술 |
|------|------|
| 백엔드 프레임워크 | Django 4.x + Django REST Framework |
| 인증 방식 | Session 기반 인증 (CSRF 포함) |
| 데이터베이스 | 기존 DB 그대로 활용 (별도 명시 없음) |
| 파일 스토리지 | Django 기본 FileField (post_images/, post_videos/) |
| 권한 관리 | DRF Permission 클래스 커스텀 |
| 프론트 엔드 | Vue3.0 + JavaScripts |

---

## 2. 앱 구조

```
closet_pjt/
├── accounts/         # 사용자 인증, 프로필, 팔로우
├── posts/            # 커뮤니티 게시글, 댓글, 체험단 신청 (기존)
├── business/         # 사업자 전용 기능 (신규)
│   ├── __init__.py
│   ├── views.py
│   ├── urls.py
│   ├── permissions.py
│   └── serializers.py
├── regions/          # 지역 데이터
└── common/           # 공통 모델 (TimeStampedModel 등)
```

---

## 3. 데이터 모델

### 3.1 기존 모델 활용 방침

사업자 기능은 **신규 모델 없이 기존 `Post` 모델을 그대로 활용**합니다.
`board`와 `category` 필드 값으로 사업자 게시글을 구분합니다.

| 기능 | board | category |
|------|-------|----------|
| 가게 관리 - 신제품 홍보 | `local_shop` | `top` 등 기존 카테고리 활용 |
| 가게 관리 - 기본 제품 홍보 | `local_shop` | 위 동일 |
| 가게 관리 - 가게 홍보 | `local_shop` | `lifestyle` 등 |
| 가게 관리 - 오는 길/운영시간 | `local_shop` | `lifestyle` 등 |
| 체험단 모집 | `experience` | `recruit` |

### 3.2 기존 모델 주요 필드 참조

**Post 모델 (posts/models.py)**

```python
class Post(models.Model):
    board         # 'local_shop' | 'experience' 사용
    category      # 'recruit' 등
    title
    content
    author        # FK → User (사업자 유저)
    store_name    # 체험단 공통
    store_location        # 체험단 모집 전용
    product_description   # 체험단 모집 전용
    notice                # 체험단 모집 전용
    recruit_start / recruit_end / experience_end  # 체험단 모집 전용
    experience_status     # property: recruiting | closed | ended
    images        # related_name (PostImage)
    videos        # related_name (PostVideo)
```

**ExperienceApplication 모델 (posts/models.py)**

```python
class ExperienceApplication(models.Model):
    post          # FK → Post (체험단 모집 글)
    applicant     # FK → User (신청자, normal 유저)
    name
    phone
    sns_account
    motivation
    created_at
```

**UserProfile 모델 (accounts/models.py)**

```python
class UserProfile(models.Model):
    user_type     # 'normal' | 'business' → 사업자 판별 기준
```

---

## 4. 권한 처리

### 4.1 사업자 권한 클래스 (신규 작성)

```python
# business/permissions.py
from rest_framework.permissions import BasePermission

class IsBusinessUser(BasePermission):
    """
    사업자 회원(user_type='business')만 허용하는 권한 클래스.
    posts/views.py의 check_experience_permission 함수와 동일한 로직을 클래스화.
    """
    message = '사업자 회원만 접근할 수 있습니다.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.user_type == 'business'
        except Exception:
            return False
```

### 4.2 적용 방식

```python
# business/views.py
from .permissions import IsBusinessUser
from rest_framework.permissions import IsAuthenticated

class DashboardView(APIView):
    permission_classes = [IsAuthenticated, IsBusinessUser]
    ...
```

---

## 5. API 명세

### 공통 사항

- **Base URL**: `/api/business/`
- **인증**: 세션 인증 필수 (미인증 시 `401`), 비사업자 접근 시 `403`
- **Content-Type**: `application/json` (파일 업로드 시 `multipart/form-data`)

---

### 5.1 대시보드

#### GET `/api/business/dashboard/`

사업자의 운영 현황 요약 정보를 반환합니다.

**Permission**: `IsAuthenticated` + `IsBusinessUser`

**Response 200**
```json
{
  "store_summary": {
    "store_name": "홍길동 패션",
    "local_shop_post_count": 12
  },
  "experience_summary": {
    "recruiting": 2,
    "closed": 1,
    "ended": 5,
    "total": 8
  },
  "applicant_summary": [
    {
      "post_id": 3,
      "title": "여름 체험단 모집",
      "applicant_count": 7
    }
  ],
  "recent_posts": [
    {
      "id": 10,
      "title": "신제품 입고 안내",
      "board": "local_shop",
      "created_at": "2026-06-01T09:00:00Z"
    }
  ]
}
```

**구현 참고**
```python
# 가게 게시글 수
local_shop_count = Post.objects.filter(author=request.user, board='local_shop').count()

# 체험단 상태별 수 (experience_status property 활용)
experience_posts = Post.objects.filter(
    author=request.user, board='experience', category='recruit'
)
# experience_status는 property이므로 Python 레벨에서 분류
recruiting = sum(1 for p in experience_posts if p.experience_status == 'recruiting')

# 신청자 수
from django.db.models import Count
applicant_summary = ExperienceApplication.objects.filter(
    post__author=request.user
).values('post_id', 'post__title').annotate(count=Count('id'))

# 최근 게시글
recent_posts = Post.objects.filter(author=request.user).order_by('-created_at')[:5]
```

---

### 5.2 가게 관리

#### GET `/api/business/store/posts/`

본인이 작성한 `local_shop` 게시글 목록을 반환합니다.

**Permission**: `IsAuthenticated` + `IsBusinessUser`

**Query Parameters**

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| ordering | string | `latest`(기본) \| `popular` \| `viewed` |

**Response 200**
```json
[
  {
    "id": 10,
    "title": "신제품 입고 안내",
    "board": "local_shop",
    "category": "top",
    "view_count": 32,
    "like_count": 5,
    "created_at": "2026-06-01T09:00:00Z",
    "images": []
  }
]
```

---

#### POST `/api/business/store/posts/`

가게 홍보 게시글을 작성합니다. 작성 즉시 커뮤니티 `local_shop` 게시판에 노출됩니다.

**Permission**: `IsAuthenticated` + `IsBusinessUser`

**Request Body** (`multipart/form-data`)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| title | string | ✅ | 게시글 제목 |
| content | string | ✅ | 게시글 내용 |
| board | string | ✅ | 항상 `local_shop` 고정 |
| category | string | | 기존 카테고리 중 선택 |
| gender | string | | `male` \| `female` \| `kids` |
| hashtags | array | | 해시태그 목록 |
| images | file[] | | 이미지 파일 (복수 가능) |
| videos | file[] | | 영상 파일 (복수 가능) |

**Response 201**: 생성된 Post 객체 반환

**구현 참고**
```python
# business/views.py
# 기존 posts/views.py의 PostListCreateView.post() 로직을 그대로 활용
# board를 'local_shop'으로 강제 설정하고 author를 request.user로 고정

serializer = PostSerializer(data=request.data, context={'request': request})
if serializer.is_valid():
    post = serializer.save(author=request.user, board='local_shop')
    ...
```

---

#### GET `/api/business/store/posts/{id}/`

게시글 상세 조회.

**Response 200**: Post 객체 (작성자 본인 것만 조회 가능, 타인 접근 시 `403`)

---

#### PUT `/api/business/store/posts/{id}/`

게시글 수정. 이미지 교체 시 기존 이미지 전체 삭제 후 재업로드.

**구현 참고**
```python
# 기존 posts/views.py PostDetailView.put() 로직 활용
if new_images:
    post.images.all().delete()
    save_images(post, new_images)
```

---

#### DELETE `/api/business/store/posts/{id}/`

게시글 삭제. 작성자 본인만 삭제 가능.

**Response 204**: No Content

---

### 5.3 체험단 관리

#### GET `/api/business/experience/posts/`

본인이 작성한 체험단 모집 글 목록을 반환합니다.

**Response 200**
```json
[
  {
    "id": 3,
    "title": "여름 체험단 모집",
    "experience_status": "recruiting",
    "recruit_start": "2026-06-01",
    "recruit_end": "2026-06-15",
    "experience_end": "2026-06-30",
    "applicant_count": 7,
    "created_at": "2026-05-28T10:00:00Z"
  }
]
```

---

#### POST `/api/business/experience/posts/`

체험단 모집 공고를 작성합니다. 작성 즉시 커뮤니티 `experience` 게시판에 노출됩니다.

**Request Body** (`multipart/form-data`)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| title | string | ✅ | 공고 제목 |
| content | string | ✅ | 공고 내용 |
| board | string | ✅ | 항상 `experience` 고정 |
| category | string | ✅ | 항상 `recruit` 고정 |
| store_name | string | ✅ | 가게명 |
| store_location | string | ✅ | 가게 주소 |
| product_description | string | ✅ | 체험 제품 설명 |
| notice | string | | 유의사항 |
| recruit_start | date | ✅ | 모집 시작일 (YYYY-MM-DD) |
| recruit_end | date | ✅ | 모집 종료일 (YYYY-MM-DD) |
| experience_end | date | ✅ | 체험 종료일 (YYYY-MM-DD) |
| images | file[] | | 이미지 파일 |
| videos | file[] | | 영상 파일 |

**Response 201**: 생성된 Post 객체 반환

**구현 참고**
```python
# board='experience', category='recruit' 강제 설정
# 기존 check_experience_permission 대신 IsBusinessUser Permission으로 대체
post = serializer.save(
    author=request.user,
    board='experience',
    category='recruit'
)
```

---

#### GET `/api/business/experience/posts/{id}/applicants/`

특정 체험단의 신청자 목록을 반환합니다. 작성자 본인만 조회 가능.

**Permission**: `IsAuthenticated` + `IsBusinessUser` + 게시글 작성자 본인 확인

**Response 200**
```json
[
  {
    "id": 1,
    "applicant_id": 25,
    "name": "김철수",
    "phone": "010-1234-5678",
    "sns_account": "@chulsoo_kim",
    "motivation": "평소 린넨 소재를 좋아합니다.",
    "created_at": "2026-06-05T14:30:00Z"
  }
]
```

**구현 참고**
```python
# business/views.py
class ExperienceApplicantListView(APIView):
    permission_classes = [IsAuthenticated, IsBusinessUser]

    def get(self, request, pk):
        post = get_object_or_404(Post, pk=pk, board='experience', category='recruit')
        if post.author != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        applications = ExperienceApplication.objects.filter(post=post)
        serializer = ExperienceApplicationSerializer(applications, many=True)
        return Response(serializer.data)
```

---

## 6. URL 설계

```python
# business/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 대시보드
    path('dashboard/', views.DashboardView.as_view(), name='business-dashboard'),

    # 가게 관리
    path('store/posts/', views.StorePostListCreateView.as_view(), name='store-post-list'),
    path('store/posts/<int:pk>/', views.StorePostDetailView.as_view(), name='store-post-detail'),

    # 체험단 관리
    path('experience/posts/', views.ExperiencePostListCreateView.as_view(), name='experience-post-list'),
    path('experience/posts/<int:pk>/', views.ExperiencePostDetailView.as_view(), name='experience-post-detail'),
    path('experience/posts/<int:pk>/applicants/', views.ExperienceApplicantListView.as_view(), name='experience-applicants'),
]
```

```python
# closet_pjt/urls.py 에 추가
path('api/business/', include('business.urls')),
```

---

## 7. 프론트엔드 연동 사항

### 로그인 후 라우팅

```javascript
// 로그인 응답의 user.profile.user_type 값으로 분기
if (user.profile.user_type === 'business') {
  router.push('/business/dashboard')
} else {
  router.push('/community')
}
```

### 사업자 전용 라우트 가드

```javascript
// 사업자 페이지 접근 시 user_type 확인
// 'business'가 아니면 커뮤니티 메인으로 리다이렉트
```

---

## 8. 에러 코드 정리

| HTTP 코드 | 상황 |
|----------|------|
| 401 | 로그인하지 않은 사용자 접근 |
| 403 | 일반 회원이 사업자 페이지 접근, 타인 게시글 수정/삭제 시도 |
| 404 | 존재하지 않는 게시글 또는 체험단 |
| 409 | 중복 신청 (ExperienceApplication unique_together 위반) |

---

## 9. 구현 시 주의사항

- `experience_status`는 `Post` 모델의 `@property`로 DB 컬럼이 아님. 필터링 시 Python 레벨에서 처리 필요.
- 가게 관리 및 체험단 게시글은 기존 `PostSerializer`를 재사용하되, `board`/`category`/`author` 필드는 View에서 강제 설정.
- 기존 `posts/views.py`의 `save_images()`, `save_videos()` 헬퍼 함수를 `business/views.py`에서 import하여 재사용.
- 사업자가 작성한 게시글은 일반 커뮤니티 API(`/api/posts/`)에서도 그대로 조회됨 (별도 처리 불필요).
- 우리 동네 가게 게시판에서 특정 가게의 홍보 게시글을 조회할 때, Post.store_location 필드와 BusinessProfile.address 필드를 주소 기준으로 매칭하여 연관 게시글을 필터링한다. 두 테이블은 외래키 관계가 없으므로 주소 문자열 비교(store_location=business_profile.address)로 연관성을 구성하며, 주소 입력 시 정확한 일치를 보장하기 위해 프론트엔드에서 주소 자동완성 또는 사업자 등록 주소를 자동으로 불러오는 방식을 권장한다.