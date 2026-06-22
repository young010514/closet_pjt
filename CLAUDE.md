# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Closet**는 Django + Vue 3 기반의 패션 커뮤니티 플랫폼으로, 일반 유저와 비즈니스 유저를 지원하는 모노레포 구조입니다.

## Tech Stack

- **Backend**: Django 5.2, Django REST Framework 3.17, SQLite (개발용)
- **Frontend**: Vue 3 (Composition API), Vite 8, Vue Router 5, Pinia, Axios

## Development Commands

### Backend — `closet/` 디렉토리에서 실행

```bash
pip install -r ../requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000   # http://localhost:8000
```

### Frontend — `closet_frontend/` 디렉토리에서 실행

```bash
npm install
npm run dev     # http://localhost:5173 (Vite, /api → localhost:8000 프록시)
npm run build
```

## Architecture

### 인증 흐름 (Session + CSRF)

1. 앱 로드 시 라우터 가드가 `authStore.initializeAuth()` 호출
2. `/api/accounts/csrf/` 에서 CSRF 토큰 획득
3. `/api/accounts/mypage/` 로 현재 유저 확인 → 401이면 비로그인, 성공이면 store에 저장
4. Axios 인스턴스(`api/http.js`)가 쿠키에서 `csrftoken` 자동 주입 (헤더: `X-CSRFToken`)

### Frontend 상태 관리 (Pinia)

- **`stores/auth.js`**: `user`, `isAuthenticated`, `isBusinessUser` / `initializeAuth()`, `login()`, `logout()`, `signupNormal()`, `signupBusiness()`
- **`stores/community.js`**: `posts`, `currentPost` / CRUD + `likePost()`, 필터·정렬 쿼리 파라미터 지원

### 유저 유형 권한

- **normal**: 일반 커뮤니티 게시물, 체험단 후기 작성 가능
- **business**: 체험단 모집 게시물 작성 가능 (후기 불가)
- 권한 검사: `check_experience_permission()` (views.py)

### 주요 DB 관계

- `User` 1:1 `UserProfile` (필수) → 1:1 `BusinessProfile` (비즈니스 유저만)
- `UserProfile` ↔ `Region`: `UserRegion` 조인 테이블, priority 1~3 (unique 제약)
- `UserProfile` 자기 참조 `Follow` (follower, following 쌍 unique)
- `Post` → `PostImage` (order 필드로 순서 유지), `Post.experience_status`는 날짜 기반 computed 속성

### 공통 추상 모델 (`common/models.py`)

- `TimeStampedModel`: `created_at`, `updated_at`
- `SoftDeleteModel`: `is_deleted`, `deleted_at`, `soft_delete()`, `restore()`
- `ActiveModel`: `is_active`

## API Endpoints

### Accounts `/api/accounts/`

| Method | Path | Auth |
|--------|------|------|
| GET | `/csrf/` | 누구나 |
| POST | `/signup/normal/` | 누구나 |
| POST | `/signup/business/` | 누구나 |
| POST | `/login/` | 누구나 |
| POST | `/logout/` | 인증 필요 |
| GET | `/mypage/` | 인증 필요 |
| PUT | `/regions/reorder/` | 인증 필요 |

### Community `/api/community/`

| Method | Path | 설명 |
|--------|------|------|
| GET | `/posts/` | 목록 (board, gender, category, ordering 쿼리 파라미터) |
| POST | `/posts/` | 생성 (이미지: FormData) |
| GET | `/posts/{pk}/` | 상세 (view_count 증가) |
| PUT | `/posts/{pk}/` | 수정 (이미지 전체 교체) |
| DELETE | `/posts/{pk}/` | 삭제 |
| POST | `/posts/{pk}/like/` | 좋아요 |

## Frontend Routing

- `/login`, `/signup/**` — `guestOnly` (인증 시 `/mypage` 리다이렉트)
- `/mypage` — `requiresAuth`
- `/community`, `/community/new`, `/community/:pk`, `/community/:pk/edit`

## Key Patterns

- **새 API 엔드포인트**: `views.py` (APIView) → `urls.py` → `serializers.py`
- **새 페이지**: `src/views/` → `router/index.js` 등록 → 필요 시 store action 추가
- **API 호출 추가**: `src/api/[module].js` 함수 → store action에서 호출
- **이미지 업로드**: `buildFormData()` 유틸로 FormData 변환, 수정 시 기존 이미지 전부 삭제 후 재저장
- **이메일**: `normalize_account_email()`로 저장 전 소문자 정규화
- **회원가입**: transaction 안에서 User → UserProfile → TermsAgreement → (BusinessProfile) 순서로 생성 후 자동 로그인
