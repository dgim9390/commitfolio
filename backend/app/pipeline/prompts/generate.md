아래는 한 개발자가 한 레포에서 한 작업들의 요약이다. 이것으로 **채용 담당자와 개발자 면접관이 읽을** 두 가지 결과물을 만들어라.
요약과 README에 없는 내용은 쓰지 마라. 숫자는 요약의 facts나 README에 있는 것만 쓸 수 있다.

근거(evidence) 표시 방법:
- 작업에 대한 문장은 근거 커밋 ID(C01 형식)를 붙인다
- 프로젝트가 무엇인지처럼 README·레포 설명에서 온 문장은 "README"를 붙인다

## 1. portfolio: 포트폴리오 소개글 (빠르게 훑어 읽히도록)
- tagline: 프로젝트를 한 줄로 (25자 안팎, 명사형으로 끝냄. 예: "실제 치수 기반 데스크 셋업 시뮬레이터")
- overview: 무엇이고 누구를 위한 것인지, 핵심 기능이 무엇인지 2~3문장
- contributions: 주요 기여 4~6개. significance가 major인 작업 우선, 관련된 작은 작업은 합친다
  - title: 기여 제목 (15자 안팎, 예: "three.js 3D 데스크 뷰")
  - summary: 무엇을 왜 만들었는지 한 문장 + evidence
  - points: 구체적인 구현 내용 2~3개. 각 한 문장, "무엇을 + 어떤 기술/방법으로" + evidence. 요약의 key_points·decisions를 활용한다
  - technologies: 이 기여에 쓴 기술 2~5개
- tech_stack: 실제로 쓴 기술을 분야별로 묶는다 (예: "Frontend", "3D·그래픽", "Backend·인프라", "Desktop"). 요약의 technologies와 언어 통계에 있는 것만

## 2. slides: 기술 발표 자료 8~10장 (포트폴리오 면접·기술 발표 수준)
각 장:
- layout: 아래 중 하나
- title: 짧은 제목 (15자 이내)
- headline: **이 장의 핵심 메시지 한 문장** (주장형. 예: "사진 한 장으로 제품을 입체로 보여 주도록 높이 지도를 만들었다")
- points: 2~4개. heading은 굵게 보일 짧은 키워드(10자 이내), text는 한 문장 설명 + evidence
- highlights: 근거가 있는 수치 0~3개를 큰 숫자 카드로 (value 예: "19종", "50단계", label은 무엇의 수치인지). facts에 없는 숫자는 절대 넣지 마라
  - 기능의 규모를 보여주는 수치만 (지원 개수, 종류 수, 단계 수, 제한 값 등). 카메라 거리·픽셀·색상 값 같은 코드 내부 상수는 넣지 마라. 마땅한 수치가 없으면 빈 목록
- flow: architecture 장에서만, 데이터나 처리의 흐름 3~6단계 (예: ["Expo 웹 빌드", "Electron 래퍼", "app:// 프로토콜 로드", "원격 번들 확인"])
- notes: 발표자가 말로 할 내용 2~4문장. 기술적 판단의 이유를 설명하되 근거 없는 성과·수치는 쓰지 마라

순서와 layout:
1. cover: title은 프로젝트 이름, headline은 tagline, points는 비워도 된다
2. agenda: 발표 순서. points의 heading에 각 장 제목, text에 한 줄 설명 (근거 "README" 또는 관련 커밋)
3. problem: 이 프로젝트가 해결하려는 문제/동기
4~7. feature 또는 architecture: 핵심 작업마다 1장. 단순 나열이 아니라 "문제 → 접근 → 구현" 흐름이 보이게. 구조가 핵심인 작업은 architecture로 flow를 채운다
8. tech: 기술 스택과 선택 이유. points의 heading은 분야, text는 쓴 기술과 그 기술로 한 일
9. summary: 정리. 핵심 성과 3개 (근거 있는 것만)

"배운 점", "향후 계획", "성능 향상"처럼 입력으로 확인할 수 없는 내용은 만들지 마라.

{{input}}
