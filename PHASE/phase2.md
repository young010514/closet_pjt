## 목표
현재 진행 단계: Phase 2 (대시보드 통계 및 데이터 가공 API 구축)
주의 사항: 가게 관리(local_shop)나 체험단 모집(experience)의 생성·수정·삭제(CRUD) 기능은 다음 단계에서 진행합니다. 본 단계에서는 오직 대시보드 전용 조회 API 구현과 데이터 집계에만 집중하세요

## 백엔드(Django) 구현 지침

- 엔드포인트 연동: business/urls.py에 선언해 둔 dashboard/ 경로에 실제 통계 데이터를 반환할 DashboardView(APIView)를 연결하세요.  
- 권한 적용: 이 뷰에는 Phase 1에서 만든 IsAuthenticated와 IsBusinessUser 권한 클래스를 반드시 적용해야 합니다.

## 데이터 집계 및 가공 로직 구현
- 가게 요약 (store_summary): 로그인한 사업자(request.user)가 작성한 board='local_shop' 게시글의 총 개수를 구하세요.

- 체험단 요약 (experience_summary): board='experience', category='recruit'인 게시글을 가져온 뒤, DB 필드가 아닌 Python @property로 선언된 experience_status 값을 기준(recruiting, closed, ended)으로 삼아 각 상태별 개수와 총합(total)을 Python 레벨에서 연산하세요.  

- 신청자 현황 요약 (applicant_summary): ExperienceApplication 모델을 필터링 및 그룹화(values, annotate)하여, 해당 사업자가 작성한 체험단 게시글별 제목(post__title)과 신청자 수(Count('id')) 목록을 집계하세요.  

- 최근 게시글 목록 (recent_posts): 해당 사업자가 작성한 모든 게시글 중 가장 최근에 작성된 5개(order_by('-created_at')[:5])를 추출하고, 필요한 필드만 직렬화하세요. 

- 응답 규격 준수: 기술 명세서 5.1절에 명시된 JSON Response 200 포맷과 Key 명칭이 정확히 일치하도록 딕셔너리를 구성하여 반환하세요

## 프론트엔드(Vue 3) 구현 지침
- 대시보드 컴포넌트 데이터 연동: /api/business/dashboard/ API를 호출하여 받아온 데이터를 Vue 3 상태(state)에 저장하고 대시보드 레이아웃에 바인딩하세요.  
- UI 컴포넌트 배치: 가게 기본 정보, 체험단 상태별 카드, 게시글별 신청자 수 테이블, 그리고 최근 게시글 목록(최대 5개)이 화면에 시각적으로 정돈되어 나타나도록 컴포넌트를 구성하세요. 

## 완료 기준 체크리스트
- API 포맷 검증: GET /api/business/dashboard/ 호출 시 반환되는 데이터의 Key 명칭(store_summary, experience_summary, applicant_summary, recent_posts)이 명세서와 완전히 일치하는가?  
- Property 연산 검증: 체험단 글 중 모집 기간이 지난 글이 있을 때, DB 에러 없이 closed 나 ended 카운트가 Python 레벨에서 정확히 올라가는가?  
- 신청자 집계 검증: 특정 체험단 공고에 일반 회원이 신청서를 접수했을 때, applicant_summary 내부의 applicant_count 숫자가 정확하게 매칭되어 올라가는가?  
- 최근 게시글 제한 검증: 사업자가 작성한 글이 6개 이상일 때, 대시보드 화면 및 API 응답에는 정확히 최신순으로 5개까지만 노출되는가?