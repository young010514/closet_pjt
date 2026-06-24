---
date: 2026-06-24
tags: [clean-cycle, board-category-injection, 409-conflict, duplicate-check, experience-status, access-control]
category: review | test | verify | coding
---

## [2026-06-24] Phase 4 — 체험단 모집 및 제약사항 예외 처리 시스템

### 발견된 문제

- **[NIT / PUT 시 store_location 재주입 없음]** `closet/business/views.py` `ExperiencePostDetailView.put()` — POST와 달리 PUT에서 `store_location` 재주입 로직이 없음. 의도적 설계(수정 시 위치 변경 불필요)로 판단되어 BLOCKING 미승격. 단, 향후 위치 변경 요구사항이 추가될 경우 일관성 확보가 필요하다.

- **[NIT / SerializerMethodField 포함 여부 미확인]** `experience_status`가 `PostSerializer`에 `SerializerMethodField`로 포함되는지 review 단계에서 확인 권고됨. 실제로는 정상 포함되어 있어 문제 없음.

### 피드백 루프

- 발생 횟수: 0회
- review PASS (NIT만 존재) → test 5/5 PASS → verify 7/7 PASS
- 수정 재실행 없이 단일 사이클 완료

### 핵심 구현 패턴 (정상 작동 확인)

- `board='experience'`, `category='recruit'` 값을 POST/PUT 시 `data.copy()` 후 주입 + `serializer.save()`로 이중 고정 → 클라이언트 임의 변경 차단
- 신청자 명단: `post.author_id != request.user.pk` 조건으로 타인 접근 403 처리
- 중복 신청: DB `unique_together` 충돌 전에 ORM 사전 검사 후 409 Conflict 반환
- 기간 마감 판단: `experience_status != 'recruiting'` Python property 기반 — DB 쿼리 없이 판단

### 반복 패턴 여부

- **board/category 강제 서버 주입**: Phase 3 `store_location` 강제 저장 패턴(2026-06-24)과 동일 계열. **반복** — 클라이언트 입력 무시 + 서버 강제 주입 패턴이 이번 사이클에서도 올바르게 적용됨. 정착된 패턴으로 확인.
- **중복 신청 409 처리**: 신규. `unique_together` 에러를 ORM 사전 검사로 회피하고 명시적 409 반환하는 패턴.
- **`experience_status` property 기반 마감 판단**: 신규. DB 애노테이션 없이 Python property만으로 상태 판단.

### 최종 결과

| # | 항목 | 결과 |
|---|------|------|
| 1 | 커뮤니티 연동 (board/category 강제 고정) | PASS |
| 2 | 신청자 명단 보안 (403 처리) | PASS |
| 3 | 사업자 신청 차단 (user_type 검사 + 403) | PASS |
| 4 | 기간 마감 차단 (experience_status property) | PASS |
| 5 | 중복 신청 409 반환 | PASS |
| verify 종합 판정 | PASS (7/7) | |

### 수정/생성된 파일

- `closet/community/views.py` — 중복 신청 HTTP 400 → 409 Conflict 변경
- `closet/business/views.py` — `ExperiencePostListCreateView`, `ExperiencePostDetailView`, `ExperienceApplicantListView` 구현 (기존 stub 대체)
- `closet_frontend/src/api/business.js` — 체험단 API 함수 6개 추가
- `closet_frontend/src/views/business/ExperiencePostListView.vue` — 신규 생성
- `closet_frontend/src/views/business/ExperiencePostFormView.vue` — 신규 생성 (등록/수정 겸용)
- `closet_frontend/src/views/business/ExperienceApplicantView.vue` — 신규 생성
- `closet_frontend/src/router/index.js` — 라우트 4개 추가

### 개선 조치

1. **CLAUDE.md 체크 항목 추가 제안**
   - [ ] POST/PUT 시 `board`, `category` 등 서버 고정값은 `data.copy()` + 직접 할당으로 강제 주입하고 클라이언트 값을 신뢰하지 않는다 (Phase 3 store_location 패턴 동일)
   - [ ] `unique_together` 제약이 있는 모델에 INSERT 전 ORM 사전 검사를 수행하고, 충돌 시 409를 명시적으로 반환한다 (IntegrityError를 그대로 500으로 노출하지 않는다)
   - [ ] Python property 기반 상태 판단(experience_status 등)을 serializer에 포함할 때 `SerializerMethodField` 누락 여부를 review 단계에서 반드시 확인한다

2. **정착된 패턴 (재사용 권장)**
   - 서버 강제 주입: `data = request.data.copy(); data['field'] = server_value; serializer = Serializer(data=data)`
   - 중복 체크 후 409: `if Model.objects.filter(...).exists(): return Response(..., status=409)`

---

---
date: 2026-06-24
tags: [verify-fail, input-validation, store-location, address-integrity, readonly-field, forced-server-value]
category: review | test | verify | coding
---

## [2026-06-24] Phase 3 — 가게 게시물 CRUD 및 주소 정합성 보장

### 발견된 문제

- **[VERIFY FAIL / 주소 정합성 위반]** `closet_frontend/src/views/business/StorePostFormView.vue` — `store_location` 필드가 `<input v-model>`로 구현되어 사용자가 임의로 수정 가능했음. 백엔드도 사용자 입력값을 그대로 저장하여 사업자 프로필 주소와 불일치 위험 발생. Phase 3 요구사항 "임의의 텍스트 오타 입력 방지"를 충족하지 못함.

- **[NIT / 불필요한 .then 체이닝]** `closet_frontend/src/api/business.js` — `deleteStorePost`의 `.then(r => r.data)` 처리가 불필요함. DELETE 204 No Content 응답에는 body가 없으므로 `.then(r => r.data)`는 `undefined`를 반환. 단순히 Promise를 그대로 반환하면 충분.

- **[NIT / None 방어 코드 누락]** `closet/business/views.py` — `store_location` 값을 `request.user.business_profile.address`에서 읽을 때 `business_profile`이나 `address`가 None인 경우에 대한 방어 코드 부재. 위험도는 낮으나 권고됨.

### 피드백 루프

- 발생 횟수: 1회
- review PASS (NIT만 존재) → verify FAIL (항목 4: 주소 매칭 정합성) → coding 수정 → test/verify PASS

### 수정 내용

- 백엔드 POST/PUT: `store_location`을 사용자 입력 무시, `request.user.business_profile.address` 공백 정제값으로 강제 저장
- 프론트: `store_location` 필드를 `v-model` → `:value` + `readonly`로 변경

### 반복 패턴 여부

- **주소/필드 강제 서버값 처리**: 신규 (첫 발생) — 프론트 입력 허용 → 백엔드에서 재검증 없이 저장하는 패턴이 원인
- **DELETE 204에 .then(r => r.data) 체이닝**: 신규 (첫 발생)

### 최종 결과

| # | 항목 | 결과 |
|---|------|------|
| 1 | 커뮤니티 자동 노출 | PASS |
| 2 | 타인 접근 차단 (403) | PASS |
| 3 | 이미지 교체 로직 | PASS |
| 4 | 주소 매칭 정합성 | PASS |
| verify 종합 판정 | PASS (4/4) | |

### 수정된 파일

- `closet/business/views.py` — StorePostListCreateView, StorePostDetailView CRUD 구현, DashboardView store_address 추가, store_location 강제 저장 로직
- `closet_frontend/src/api/business.js` — CRUD 함수 6개 추가
- `closet_frontend/src/views/business/StorePostListView.vue` — 신규 생성
- `closet_frontend/src/views/business/StorePostFormView.vue` — 신규 생성, store_location readonly 처리
- `closet_frontend/src/router/index.js` — 라우트 3개 추가 (business-store, business-store-new, business-store-edit)

### 개선 조치

1. **CLAUDE.md 주의사항 추가 제안**
   - 서버에서 권위 있는 값(사업자 주소, 사용자 ID 등)을 저장하는 필드는 클라이언트 입력을 그대로 사용하지 않는다. 백엔드에서 `request.user` 또는 관련 프로필에서 직접 읽어 강제 저장한다.
   - 프론트에서 readonly로 표시하더라도 백엔드 검증 없이 신뢰해서는 안 된다. 백엔드가 최종 권위자여야 한다.
   - DELETE 응답(204 No Content)에는 `.then(r => r.data)` 체이닝을 하지 않는다.

2. **체크 항목 (향후 동일 실수 방지)**
   - [ ] 게시물/폼 POST/PUT 시 서버 파생값(주소, 소유자 ID 등)을 클라이언트 입력 대신 서버에서 강제 주입하는지 확인
   - [ ] 프론트 readonly 필드가 백엔드에서도 무시/재설정되는지 확인
   - [ ] DELETE API 함수에 `.then(r => r.data)` 체이닝 여부 점검
   - [ ] `business_profile.address` 접근 시 None 안전성 확인 (try/except 또는 hasattr)

---

---
date: 2026-06-24
tags: [blocking, django, onetoonefield, reverse-accessor, getattr-fallback, RelatedObjectDoesNotExist]
category: review | test | verify | coding
---

## [2026-06-24] Phase 2 — Business 대시보드 통계 API 및 Vue UI 구현

### 발견된 문제

- **[BLOCKING / ORM 역참조 fallback 오동작]** `closet/business/views.py:29` — `getattr(user, 'business_profile', None)` 패턴이 `OneToOneField` 역참조 누락 시 `RelatedObjectDoesNotExist`를 잡지 못해 500 오류 발생. `RelatedObjectDoesNotExist`는 `ObjectDoesNotExist`의 서브클래스이며 `AttributeError`의 서브클래스가 아니므로 `getattr`의 세 번째 인자(default) 경로로 진입하지 않는다. 수정: `try/except (ObjectDoesNotExist, Exception)` 블록으로 명시적 예외 처리.

### 피드백 루프

- 발생 횟수: 1회
- review FAIL → coding에서 `try/except Exception` 수정 → test/verify 재실행 → PASS

### 반복 패턴 여부

- **ORM 역참조 getattr fallback**: 신규 (첫 발생)

### 최종 결과

| 항목 | 결과 |
|------|------|
| API 포맷 키 일치 | PASS |
| experience_status @property Python 레벨 연산 | PASS |
| applicant_count DB annotate 집계 | PASS |
| recent_posts 최신순 5개 제한 | PASS |
| verify 종합 판정 | PASS (4/4) |

### 수정된 파일

- `closet/business/views.py` — DashboardView.get() 실제 통계 구현
- `closet_frontend/src/api/business.js` — 신규 생성 (getDashboard 함수)
- `closet_frontend/src/views/business/BusinessDashboardView.vue` — 전면 재작성 (4개 섹션 UI)

### 개선 조치

1. **CLAUDE.md 주의사항 추가 제안**
   - Django `OneToOneField` 역참조 존재 여부를 `getattr(instance, 'related_name', None)` 으로 확인하지 않는다. `RelatedObjectDoesNotExist`는 `AttributeError` 서브클래스가 아니므로 `getattr` default가 동작하지 않는다. 반드시 `try/except ObjectDoesNotExist` (또는 `RelatedObjectDoesNotExist`) 블록으로 처리한다.

2. **체크 항목 (향후 동일 실수 방지)**
   - [ ] `OneToOneField` 역방향 접근자를 사용하는 뷰/시리얼라이저 코드에서 `getattr` fallback 패턴 사용 여부 점검
   - [ ] 해당 위치를 `try/except ObjectDoesNotExist` 또는 `hasattr` + 예외처리 조합으로 대체 여부 확인
   - [ ] 신규 통계 API 작성 시 `annotate`/`aggregate` 쿼리와 Python 레벨 연산 혼용 여부 및 None 안전성 확인

---

---
date: 2026-06-24
tags: [blocking, auth, 401-403-split, duplicate-route, route-guard, permission]
category: review | test | verify | coding
---

## [2026-06-24] Phase 1 — Business 앱 기본 구조 및 권한 설계

### 발견된 문제

- **[BLOCKING / 중복 라우트]** `closet/closet/urls.py` — `api/community/` 경로가 중복 등록됨. urlpatterns에 동일 prefix를 두 번 include하면 첫 번째 항목만 유효하므로 두 번째 앱의 라우트가 무시된다.

- **[BLOCKING / 401-403 분리 위반]** `closet/business/permissions.py` — `IsBusinessUser` 클래스 내에서 `is_authenticated` 검사를 직접 수행함. DRF 기본 동작에서 `has_permission`이 `False`를 반환하면 인증 여부와 무관하게 403을 돌려주기 때문에 비인증 접근에도 403이 발생하여 401/403 분리 원칙이 위반된다. 수정 방법: `is_authenticated` 검사를 permission에서 제거하고 별도 `authentication.py`에서 `authenticate_header`를 구현해 401을 강제한다.

- **[BLOCKING / 라우트 가드 비인증 분기 누락]** `router/index.js` — `requiresBusiness` 메타 가드만 단독으로 적용 시, 비인증 사용자가 business 라우트에 접근할 경우 401 처리 없이 조용히 다른 경로로 리다이렉트되는 잠재 취약점이 존재한다. 비인증과 권한 부족을 분기하는 로직이 명시적으로 있어야 한다.

### 피드백 루프

- 발생 횟수: 1회
- review FAIL 후 coding 에이전트로 3건 수정 → test/verify 재실행
- test 에이전트가 항목 1(401 검증) 초기 실패 후 `closet/business/authentication.py` 신규 생성으로 수정 (`SessionAuthentication` 상속, `authenticate_header` → `'Session'` 반환)

### 반복 패턴 여부

- **중복 라우트**: 신규 (첫 발생)
- **401/403 분리 위반**: 신규 (첫 발생) — permission 클래스에서 인증 검사를 겸하는 구현 패턴이 원인
- **라우트 가드 비인증 분기 누락**: 신규 (첫 발생)

### 최종 결과

| 항목 | 결과 |
|------|------|
| 비로그인 → 401 | PASS |
| normal 유저 → 403 | PASS |
| business 유저 → 200 | PASS |
| Vue 라우트 가드 커뮤니티 리다이렉트 | PASS |
| verify 종합 판정 | PASS (4/4) |

### 개선 조치

1. **CLAUDE.md 주의사항 추가 제안**
   - DRF permission 클래스에서 `is_authenticated` 검사를 직접 수행하지 않는다. 인증은 `authentication_classes`, 권한은 `permission_classes`로 분리하며, 401/403을 명확히 구분하기 위해 `authenticate_header`를 구현한 커스텀 authenticator를 병용한다.
   - `urls.py`에 새 앱 라우트를 추가할 때 기존 `urlpatterns` 전체를 검토하여 동일 prefix 중복 여부를 확인한다.

2. **PHASE 파일 지침 보완 제안**
   - Vue 라우트 가드 작성 시 `requiresAuth`(비인증 차단)와 `requiresBusiness`(권한 부족 차단)를 항상 함께 명시하도록 가이드 추가. 비인증 분기와 권한 분기를 분리하는 예시 코드를 PHASE 파일에 포함한다.

3. **체크 항목 (향후 동일 실수 방지)**
   - [ ] permission 클래스 신규 작성 시 `has_permission` 내 `is_authenticated` 직접 호출 여부 검토
   - [ ] `urls.py` 수정 후 동일 prefix 중복 등록 여부 grep 확인
   - [ ] 라우트 가드 추가 시 비인증/권한부족 두 분기가 모두 처리되는지 확인
   - [ ] 커스텀 permission이 401을 요구하는 경우 `authenticate_header` 반환값이 있는 authenticator와 짝을 이루는지 확인

---
