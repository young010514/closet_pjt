# CODEX 작업 명세 — GMS 기반 AI 퍼스널 컬러 분석

아래 작업을 현재 저장소 루트에서 직접 수행하라. 단순 분석이나 제안으로 끝내지 말고, 현재 코드와 로컬 Git 상태를 먼저 확인한 뒤 필요한 코드 수정, 문서화, 테스트까지 완료하라.

## 1. 최종 목표

로그인한 사용자가 프론트엔드에서 얼굴 사진을 업로드하면 Django 백엔드가 GMS API를 호출하고, AI가 반환한 퍼스널 컬러 결과를 검증한 뒤 DB에 저장하여 프론트엔드에 반환하도록 구현한다.

런타임 전제는 다음과 같다.

```env
PERSONAL_COLOR_PROVIDER=gms
GMS_API_URL=https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions
GMS_API_KEY=<실제 GMS 키>
GMS_MODEL=gpt-4o-mini
GMS_API_STYLE=chat
GMS_TIMEOUT_SECONDS=90
```

중요 제약:

- 실제 런타임에서는 `mock`을 사용하지 않는다.
- `PERSONAL_COLOR_PROVIDER=gms`일 때 어떤 오류가 발생해도 mock 결과로 조용히 대체하지 않는다.
- 테스트 코드에서 외부 통신을 차단하기 위한 mocking은 허용한다.
- 실제 API 키는 백엔드 `.env`에서만 읽고, 프론트엔드·응답·로그·테스트 fixture·문서·Git diff에 노출하지 않는다.
- 현재 Django 설정이 읽는 키 이름은 `GMS_API_KEY`로 통일한다. `GMS_KEY`와 혼용하지 않는다.
- 실제 `.env`를 placeholder로 덮어쓰거나 Git에 추가하지 않는다.
- 사용자가 업로드한 원본 사진과 base64 문자열을 DB, media 디렉터리, 로그에 저장하지 않는다.

## 2. 작업 안전 수칙

가장 먼저 아래 명령으로 로컬 작업 상태를 확인하라.

```bash
git status --short --branch
git branch --show-current
git log -5 --oneline --decorate
git diff --stat
git diff
git ls-files --others --exclude-standard
```

규칙:

- 기존 수정 사항과 미추적 파일을 먼저 파악하고 보존한다.
- 퍼스널 컬러 작업과 무관한 사용자 변경을 덮어쓰거나 되돌리지 않는다.
- `git reset --hard`, `git clean`, `git restore .`, `git checkout --`, 강제 checkout, 강제 push를 사용하지 않는다.
- 임의로 commit 또는 push하지 않는다.
- `.env` 내용을 출력하거나 문서에 복사하지 않는다.
- Git 상태 기록에는 브랜치, 변경 파일명, 최신 커밋만 적고 비밀값은 적지 않는다.

## 3. PHASE 문서부터 생성

코드를 수정하기 전에 저장소 루트의 `PHASE/` 아래에 다음 Markdown 파일을 생성하라.

```text
PHASE/
├─ README.md
├─ 00-current-state.md
├─ 01-frontend-backend-contract.md
├─ 02-env-and-gms-config.md
├─ 03-gms-provider.md
├─ 04-api-and-persistence.md
└─ 05-tests-and-verification.md
```

각 파일은 최소한 다음 항목을 포함해야 한다.

```md
# Phase 제목

## 목표
## 현재 확인 결과
## 수정 예정 파일
## 세부 작업
## 완료 조건
## 검증 명령
## 실제 수행 결과
## 남은 위험 요소
```

추가 규칙:

- `PHASE/README.md`에는 전체 Phase 상태표를 만들고 `대기 / 진행 중 / 완료 / 차단` 상태를 기록한다.
- 각 Phase 시작 전 계획을 먼저 기록하고, 완료 후 실제 수정 파일·테스트 결과·판단 근거를 갱신한다.
- 현재 `.gitignore`가 `PHASE/` 전체를 무시한다면, 이번 문서가 산출물로 추적되도록 `.gitignore`의 `PHASE/` 규칙만 제거한다.
- `.env`, `closet/.env`, 키 파일에 대한 ignore 규칙은 유지한다.
- PHASE 문서에는 API 키, base64 이미지, 쿠키, 세션값을 절대 기록하지 않는다.

## 4. Phase 00 — 현재 코드와 Git 상태 감사

다음 파일과 관련 import를 실제로 읽고 현재 흐름을 문서화하라.

### 백엔드

```text
closet/closet/settings.py
closet/closet/urls.py
closet/personal_color/models.py
closet/personal_color/serializers.py
closet/personal_color/services.py
closet/personal_color/service.py
closet/personal_color/services_VER1.py
closet/personal_color/exceptions.py
closet/personal_color/views.py
closet/personal_color/urls.py
closet/personal_color/tests.py
closet/personal_color/migrations/
```

### 프론트엔드

```text
closet_frontend/src/api/http.js
closet_frontend/src/api/personalColor.js
closet_frontend/src/stores/auth.js
closet_frontend/src/views/PersonalColorView.vue
closet_frontend/src/router/index.js
closet_frontend/vite.config.js
```

관련 참조를 찾는다.

```bash
rg -n "PERSONAL_COLOR_PROVIDER|GMS_|personal[_-]?color|PersonalColor" closet closet_frontend
rg -n "from \.service|from \.services|services_VER1|personal_color\.service" closet
```

반드시 확인할 내용:

1. 사진 업로드부터 `POST /api/personal-color/analyses/`까지의 전체 호출 흐름
2. multipart 필드명이 프론트와 백엔드 모두 `image`인지
3. 로그인 세션과 CSRF 초기화가 실제 요청 전에 수행되는지
4. 성공 응답 필드와 Vue 화면이 사용하는 필드가 일치하는지
5. `services.py`, `service.py`, `services_VER1.py` 중 실제 import되는 파일
6. 현재 모델과 migration만으로 결과 저장이 가능한지
7. 현재 테스트가 mock provider만 검증하는지, GMS request contract까지 검증하는지
8. 현재 로컬 변경과 충돌 가능성이 있는 파일

## 5. Phase 01 — 프론트엔드·백엔드 계약 확정

### 요청 계약

```http
POST /api/personal-color/analyses/
Content-Type: multipart/form-data
Cookie/CSRF: 기존 세션 인증 방식 사용

image=<JPEG | PNG | WEBP 파일>
```

### 성공 응답 계약

HTTP `201 Created`이며 다음 필드를 유지한다.

```json
{
  "id": 1,
  "result_type": "spring_warm",
  "result_label": "봄 웜톤",
  "result_subtype": "브라이트",
  "confidence": 91.2,
  "summary": "...",
  "best_colors": [
    {"name": "코랄 핑크", "hex": "#F49A8A", "reason": "..."}
  ],
  "avoid_colors": [
    {"name": "딥 네이비", "hex": "#233554", "reason": "..."}
  ],
  "recommendations": {
    "clothing": ["..."],
    "makeup": ["..."],
    "accessories": ["..."]
  },
  "analysis_metrics": {
    "warmth": 0.8,
    "brightness": 0.7,
    "saturation": 0.6,
    "contrast": 0.5
  },
  "provider_name": "gms",
  "model_version": "gpt-5.4-nano",
  "created_at": "..."
}
```

허용하는 `result_type`은 아래 네 개뿐이다.

```text
spring_warm
summer_cool
autumn_warm
winter_cool
```

정규화 규칙:

- `confidence`는 최종적으로 `0~100` 범위로 통일한다.
- `analysis_metrics` 값은 `0~1` 범위로 통일한다.
- `hex`는 `#RRGGBB` 형식이어야 한다.
- 결과 타입의 영문 공백/하이픈 표기 또는 한국어 계절명 같은 명확한 alias는 정규화할 수 있다.
- 핵심 결과가 누락된 응답을 계절 preset으로 임의 보충하여 정상 결과처럼 저장하지 않는다.
- 특히 GMS 응답에 `result_type`이나 필수 배열이 없을 때 mock용 preset으로 결과 전체를 만들어 내지 않는다.
- mock provider의 고정 preset은 테스트 또는 명시적 mock 모드에서만 사용할 수 있다.

### 프론트엔드 판단 기준

현재 프론트가 아래를 모두 충족하면 디자인이나 구조를 다시 작성하지 말고 그대로 유지한다.

- JPEG/PNG/WEBP 선택 및 drag-and-drop
- 10MB·최소/최대 해상도 검증
- 미리보기, 교체, 제거
- `FormData.append('image', file)`
- `/api/personal-color/analyses/` POST
- 분석 중 중복 클릭 방지와 loading UI
- 성공 결과 표시
- 오류 코드별 사용자 메시지
- 기록 조회·상세 선택·삭제
- 인증 만료 시 로그인 이동

프론트 수정은 실제 계약 불일치가 확인된 경우에만 최소 범위로 수행한다. `Content-Type: multipart/form-data`를 직접 고정하여 boundary를 깨뜨리지 않는다.

## 6. Phase 02 — `.env` 및 GMS 설정 정리

주요 수정 후보는 `closet/closet/settings.py`와 새로 추가할 `closet/.env.example`이다.

### 필수 설정

```env
PERSONAL_COLOR_PROVIDER=gms
GMS_API_URL=https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions
GMS_API_KEY=replace_with_real_key
GMS_MODEL=gpt-5.4-nano
GMS_API_STYLE=chat
GMS_TIMEOUT_SECONDS=90
GMS_API_KEY_HEADER=Authorization
GMS_API_AUTH_PREFIX=Bearer
```

구현 기준:

- `closet/.env` 즉 `BASE_DIR / '.env'`가 확실히 로드되어야 한다.
- 저장소 루트 `.env`가 없어도 동작해야 한다.
- 불필요하게 중복된 수동 `.env` parser가 있다면 동작과 우선순위를 검토하고, 가능하면 `python-dotenv` 기반의 단일하고 예측 가능한 로딩으로 정리한다.
- 이미 OS 환경변수로 주입된 값을 덮어쓸지 여부를 명시적으로 결정하고 문서화한다. 로컬 개발에서는 현재 프로세스의 오래된 `GMS_MODEL` 값 때문에 `.env` 설정이 무시되지 않는지 확인한다.
- 서비스 계층은 가능하면 `django.conf.settings`를 단일 설정 소스로 사용하고 같은 값을 다시 `os.getenv()`로 읽어 서로 다른 값이 섞이지 않도록 한다.
- `PERSONAL_COLOR_PROVIDER`, URL, key, model 값을 `strip()` 처리한다.
- `PERSONAL_COLOR_PROVIDER=gms`인데 URL·key·model 중 하나라도 비어 있으면 즉시 명확한 provider configuration 오류로 처리한다.
- 설정 확인 시 키는 값이 아니라 `configured=True/False`만 출력한다.
- `.env` 변경 후 Django 프로세스를 재시작해야 함을 PHASE 문서에 기록한다.

설정 확인 예시에서는 비밀값을 출력하지 않는다.

```bash
cd closet
python manage.py shell -c "from django.conf import settings; print({'provider': settings.PERSONAL_COLOR_PROVIDER, 'url': settings.GMS_API_URL, 'model': settings.GMS_MODEL, 'key_configured': bool(settings.GMS_API_KEY)})"
```

## 7. Phase 03 — GMS provider 구현 및 강화

주 구현 파일은 `closet/personal_color/services.py`로 통일한다.

- `services.py`를 canonical 구현으로 사용한다.
- `service.py`가 기존 import 호환을 위한 re-export라면 그 역할만 유지하고 신규 로직을 넣지 않는다.
- `services_VER1.py`는 실제 import 여부를 먼저 확인한다. 참조가 없더라도 이번 기능 수정과 무관하게 성급히 삭제하지 말고 legacy 파일임을 문서화한다.

### GMS 요청 계약

GMS Chat Completions 요청은 아래 구조를 정확히 사용한다.

```json
{
  "model": "gpt-5.4-nano",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "퍼스널 컬러 분석 지시문"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,...",
            "detail": "low"
          }
        }
      ]
    }
  ],
  "max_completion_tokens": 500
}
```

HTTP 헤더:

```http
Content-Type: application/json
Authorization: Bearer <GMS_API_KEY>
```

구현 요구사항:

1. 업로드 이미지를 기존 검증 규칙에 따라 검사한다.
2. EXIF 방향을 보정하고 RGB PNG로 정규화한다.
3. 정규화된 바이트를 `data:image/png;base64,` URL로 변환한다.
4. endpoint는 정확히 `GMS_API_URL`을 사용하고 URL을 임의로 재조합하지 않는다.
5. `GMS_API_STYLE=chat`이면 반드시 Chat Completions payload를 사용한다.
6. timeout은 `GMS_TIMEOUT_SECONDS`를 적용한다.
7. 외부 API 호출은 DB transaction 바깥에서 수행한다.
8. API 키, Authorization 전체 값, base64, 원본 이미지 바이트를 로그에 남기지 않는다.
9. 로그에는 provider, model, HTTP status, 예외 종류와 redacted/truncated 오류 메시지만 남긴다.
10. GMS의 비정상 응답을 클라이언트에 그대로 전달하지 않는다.

### AI 지시문 요구사항

모델에 다음을 명확히 지시한다.

- 얼굴 이미지의 가시적 색조·명도·채도·대비를 바탕으로 퍼스널 컬러를 분류한다.
- 사람의 신원, 인종, 민감 특성을 추정하지 않는다.
- Markdown이나 코드 펜스 없이 JSON 객체 하나만 반환한다.
- 한국어로 설명한다.
- 위 성공 응답 계약의 AI 결과 필드를 모두 채운다.
- 색상 배열과 추천 배열을 비워 두지 않는다.

### GMS 응답 파싱

우선 `choices[0].message.content`를 읽는다.

다음 형태는 안전하게 처리한다.

- JSON 문자열
- 앞뒤 공백이 있는 JSON
- 실수로 붙은 ```json 코드 펜스
- 명확한 alias 표기
- confidence가 `0~1` 또는 `0~100`으로 온 경우

다음은 실패로 처리한다.

- HTTP body가 JSON이 아님
- `choices` 또는 message content가 없음
- content가 JSON 객체로 파싱되지 않음
- `result_type` 등 핵심 필드 누락
- 잘못된 hex
- 필수 배열 또는 추천 카테고리가 비어 있음
- 범위를 벗어난 수치
- 응답이 중간에 잘린 것으로 보임

검증 실패 시 DB record를 생성하지 않는다.

## 8. Phase 04 — API, 예외 처리, DB 저장

우선 기존 `models.py`, migration, serializer, view, URL이 계약을 충족하는지 확인한다. 현재 스키마로 충분하다면 모델과 migration을 변경하지 않는다.

주요 수정 후보:

```text
closet/personal_color/exceptions.py
closet/personal_color/serializers.py
closet/personal_color/services.py
closet/personal_color/views.py
```

요구사항:

- 로그인 사용자만 생성·조회·삭제 가능하다.
- 각 사용자는 자신의 분석 기록만 접근할 수 있다.
- 이미지 검증은 API 호출 전에 완료한다.
- GMS 응답 정규화와 전체 schema 검증이 끝난 뒤에만 DB 저장을 시작한다.
- DB 생성은 짧은 `transaction.atomic()` 안에서 수행한다.
- 저장 시 `provider_name='gms'`, `model_version=settings.GMS_MODEL`이 정확히 기록되어야 한다.
- 원본 이미지용 `ImageField`나 파일 경로를 새로 추가하지 않는다.

오류 응답 계약:

| 상황 | HTTP | code |
|---|---:|---|
| 이미지 누락/형식·용량·해상도 오류 | 400 | 기존 이미지 오류 코드 유지 |
| 비로그인/세션 만료 | 401 또는 403 | 인증 계층과 기존 프론트 처리 유지 |
| GMS 설정 누락 | 503 | `analysis_provider_unavailable` |
| GMS 400/401/403/404/429/5xx | 503 | `analysis_provider_unavailable` |
| timeout/DNS/network 오류 | 503 | `analysis_provider_unavailable` |
| 응답 JSON 또는 schema 오류 | 503 | `analysis_result_invalid` |
| 기타 분석 실패 | 503 | `analysis_failed` |

GMS가 반환한 `Invalid target domain`, `Model not found`, key 관련 원문은 서버 로그에서 원인 파악이 가능하도록 redacted된 범위로 남기되, 클라이언트에는 내부 구현과 키 정보를 노출하지 않는다.

## 9. Phase 05 — 테스트와 검증

기존 테스트를 보존하면서 아래 케이스를 추가 또는 강화한다.

### provider 선택 및 설정

- `PERSONAL_COLOR_PROVIDER=gms`이면 `GmsPersonalColorProvider`가 선택된다.
- gms 모드에서 mock으로 fallback하지 않는다.
- key, URL, model 중 하나라도 없으면 provider unavailable 오류가 발생한다.
- `.env`의 `GMS_MODEL=gpt-5.4-nano`가 request body와 저장 record에 반영된다.

### GMS request contract

mocked HTTP 호출을 검사하여 아래를 assert한다.

- URL이 정확하다.
- `Authorization: Bearer ...` 헤더가 존재한다.
- request body 최상위에 `model`이 존재한다.
- `messages[0].content`가 text + image_url 배열이다.
- `image_url.url`이 `data:image/png;base64,`로 시작한다.
- `detail`은 `low`이다.
- `max_completion_tokens`는 500이다.
- secret과 base64가 로그에 남지 않는다.

### 응답 처리

- 정상 JSON → 201 및 DB 1건
- code fence JSON → 정상 파싱
- 명확한 result type alias → 정규화
- confidence 0.91 → 91.0
- 잘못된 JSON → 503, `analysis_result_invalid`, DB 0건
- 필수 필드 누락 → 503, DB 0건
- preset을 이용해 누락 응답을 가짜 정상 결과로 만들지 않음
- GMS HTTP 400/401/429/500 → 503, DB 0건
- timeout/network 오류 → 503, DB 0건

### API와 보안

- 비로그인 업로드 차단
- 지원하지 않는 확장자, MIME 불일치, 10MB 초과, 손상 파일, 최소·최대 해상도 오류
- 성공 응답 필드 전체 검증
- 사용자별 list/detail/delete 격리
- 원본 이미지가 media 또는 DB에 저장되지 않음

### 필수 검증 명령

백엔드:

```bash
cd closet
python manage.py check
python manage.py makemigrations --check
python manage.py test personal_color
```

프론트엔드:

```bash
cd closet_frontend
npm run build
```

저장소 최종 검증:

```bash
git diff --check
git status --short --branch
git diff --stat
```

의존성 설치가 필요한 경우 기존 lockfile을 우선 사용하고, 이 기능 때문에 불필요한 패키지를 추가하지 않는다.

### 실제 GMS smoke test

`.env`에 실제 key가 있고 네트워크가 허용되는 경우에만 외부 GMS 호출을 최대 1회 수행한다.

- 먼저 key 값이 아니라 `key_configured=True`만 확인한다.
- 저장소에 적절한 테스트 이미지가 있을 때 service 계층 또는 실제 API 흐름으로 확인한다.
- 실제 개인 사진을 저장소에 추가하지 않는다.
- 반복 재시도하여 API 사용량을 낭비하지 않는다.
- 성공 시 `provider_name`, `model_version`, result type, DB 저장 여부만 기록한다.
- 실패 시 status와 redacted 오류만 기록한다.
- key 또는 테스트 이미지가 없어 실호출하지 못해도 unit/integration test는 모두 완료하고 그 사유를 최종 보고에 명시한다.

## 10. 예상 수정 파일 우선순위

### 반드시 점검하고 수정 가능성이 높은 파일

```text
.gitignore
closet/closet/settings.py
closet/personal_color/services.py
closet/personal_color/tests.py
closet/.env.example
PHASE/*.md
```

### 계약 또는 오류 처리 불일치가 있을 때만 수정

```text
closet/personal_color/exceptions.py
closet/personal_color/serializers.py
closet/personal_color/views.py
closet_frontend/src/api/personalColor.js
closet_frontend/src/views/PersonalColorView.vue
closet_frontend/src/stores/auth.js
```

### 특별한 근거가 없으면 수정하지 않음

```text
closet/personal_color/models.py
closet/personal_color/migrations/
closet/personal_color/urls.py
closet/closet/urls.py
closet_frontend/src/router/index.js
```

## 11. 완료 조건

아래 조건을 모두 만족해야 완료다.

1. `PERSONAL_COLOR_PROVIDER=gms`에서 mock fallback이 없다.
2. Django가 `closet/.env`의 GMS 설정을 정확히 읽는다.
3. GMS 요청이 알려진 정상 Chat Completions 형식과 일치한다.
4. 모델명은 request body 최상위 `model`로 전달된다.
5. 사진은 `image_url.url`의 data URL로 전달된다.
6. 정상 GMS 결과만 검증 후 DB에 저장된다.
7. 비정상 GMS 응답이나 통신 실패 시 record가 생성되지 않는다.
8. 성공 record에 `provider_name='gms'`와 실제 모델명이 저장된다.
9. 프론트 업로드·결과·기록 UI가 기존 API 계약으로 정상 동작한다.
10. 원본 사진과 API key가 저장·로그·Git에 남지 않는다.
11. PHASE 문서가 실제 수행 결과로 갱신되어 있다.
12. Django check, personal_color tests, frontend build, diff check가 통과한다.

## 12. 최종 보고 형식

작업을 마친 뒤 다음 순서로 보고하라.

```md
# 작업 결과

## 시작 시 Git 상태
- branch:
- HEAD:
- 기존 변경 사항:

## 생성한 PHASE 문서
- ...

## 수정 파일과 이유
- path: 이유

## 프론트엔드 판단
- 수정 여부:
- 근거:

## 백엔드 구현 결과
- env 로딩:
- GMS request 형식:
- 응답 검증:
- DB 저장:
- 오류 처리:

## 테스트 결과
- python manage.py check:
- makemigrations --check:
- python manage.py test personal_color:
- npm run build:
- git diff --check:
- 실제 GMS smoke test:

## 남은 문제
- 없음 또는 구체적인 차단 사유

## 최종 Git 상태
- 변경 파일 목록
```

최종 보고에서도 API key, Authorization 값, base64 이미지, 세션·쿠키를 출력하지 않는다.
