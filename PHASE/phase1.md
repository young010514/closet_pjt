## 목표
현재 진행 단계: Phase 1 (기반 인프라 및 보안 권한 확립)
주의 사항: Phase 2~4에 해당하는 대시보드 통계 계산, 게시글 CRUD, 체험단 신청 예외 처리 로직은 본 단계에서 구현하지 마세요. 오직 라우팅 구조와 접근 권한 격리에만 집중합니다.

## 백엔드(Django) 구현 지침

- business 앱 인프라 연동: 메인 URL 설정(closet/closet/urls.py)에 api/business/ 경로를 추가하고,  business/urls.py로 라우팅이 이어지도록 구조를 짜주세요

- 엔드포인트 뼈대 선언: business/urls.py에 기술 명세서의 6가지 엔드포인트(대시보드, 가게 관리 목록/상세, 체험단 목록/상세, 신청자 목록)를 빈 APIView나 임시 뷰 형태로 매핑해 두세요.

- 커스텀 권한 클래스 구현: business/permissions.py 파일에 IsBusinessUser 권한을 생성하세요. accounts/models.py를 참조하여 유저의 profile.user_type이 'business'일 때만 True를 반환해야 합니다. 비인증 사용자는 401, 비사업자 사용자는 403 에러가 명확히 리턴되도록 설정하세요.

## 프론트엔드(Vue 3) 구현 지침

- 로그인 라우팅 분기: 로그인 성공 시 응답받은 유저 프로필 데이터(user.profile.user_type)를 확인하여, 사업자(business)인 경우 /business/dashboard로, 일반 유저(normal)인 경우 /community로 이동하는 내비게이션 로직을 작성하세요

- 라우트 가드(Route Guard) 적용: Vue Router의 beforeEach를 활용하여 사업자 전용 페이지(/business/)에 접근할 때 유저 타입을 검증하고, 사업자가 아니라면 접근을 차단한 뒤 커뮤니티 메인으로 리다이렉트하는 가드 로직을 작성하세요.

## 완료 기준 체크리스트
- 비로그인 상태로 GET /api/business/dashboard/ 호출 시 401 Unauthorized가 뜨는가?
- user_type='normal'인 일반 유저 계정으로 GET /api/business/dashboard/ 호출 시 403 Forbidden이 뜨는가?
- user_type='business'인 사업자 계정으로 호출 시 임시 뷰의 응답(200 OK)이 정상적으로 리턴되는가?
- Vue 3 브라우저 주소창에 일반 유저 상태로 /business/dashboard를 강제 입력했을 때 커뮤니티 페이지로 튕겨 나가는가?