📌 0️⃣ 분석 목적 정의

이 저장소에서 LLM 대화 컨텍스트 관리 방식을 분석하라.
특히 다음 항목을 중점적으로 추적하라:

대화 로그 저장 구조

모델에 실제로 들어가는 context 구성 로직

context 길이 초과 시 처리 방식 (요약, 삭제, 슬라이딩 윈도우 등)

장기 메모리/지식 저장소 존재 여부

RAG / 임베딩 검색 사용 여부

실시간 스트리밍 vs 배치 처리 구조

🧠 1️⃣ 코드 레벨 추적 지시
코드 전체에서 다음 키워드를 우선 검색하고 관련 파일들을 트리 형태로 정리하라:

keywords:
- memory
- history
- context
- conversation
- messages
- summarize
- token
- window
- embedding
- vector
- store
- session
- chat


출력 형식:

파일경로
 └─ 역할 요약
 └─ 관련 함수 목록
 └─ context 처리 관련 코드 스니펫 설명

🧩 2️⃣ 컨텍스트 구성 로직 추출
"모델 호출 직전"에 실행되는 코드를 찾아라.
다음 정보를 구조적으로 설명하라:

1. messages 배열을 어디서 만드는가
2. system prompt는 어디서 정의되는가
3. 이전 대화 몇 턴이 들어가는가
4. 파일/설정 기반 메모리를 추가하는가
5. 유저 프로필/VTuber 설정이 프롬프트에 포함되는가


출력은 표 형태:

항목	구현 위치	동작 방식
🗃 3️⃣ 메모리/로그 저장 구조
대화 로그가 저장되는 저장소를 찾아라:
- 파일 (json, sqlite, txt)
- DB
- 메모리 캐시
- 외부 서비스

그리고 세션 단위 관리인지, 전역 관리인지 구분하라.

🔄 4️⃣ 컨텍스트 초과 처리 방식
토큰 초과 상황을 처리하는 로직이 있는지 확인하라.
있다면 어떤 방식인가?

- 오래된 메시지 삭제
- 요약 후 대체
- sliding window
- 아무 처리 없음

🧬 5️⃣ "가상 메모리" 구조 여부 판별
이 프로젝트가 다음과 같은 구조를 가지는지 판단하라:

[대화 로그 전체 저장] → [요약본 생성] → [현재 컨텍스트 재조립]

있다면 흐름도를 만들어라.
없다면 "단순 최근 대화 기반 구조"로 분류하라.

📊 6️⃣ 전체 구조 다이어그램 생성
LLM 호출까지의 데이터 흐름을 Mermaid 다이어그램으로 출력하라.

포함 요소:
User input
↓
Memory system
↓
Prompt builder
↓
LLM call
↓
Response handler
↓
Memory update

🎯 최종 산출 요구

분석 결과를 다음 형식으로 정리:

이 프로젝트의 메모리 아키텍처 유형 (택 1)

Sliding window

Summary buffer

RAG memory

Virtual memory (MemGPT style)

None

컨텍스트 관리 수준 (낮음 / 중간 / 고급)

IDE 코파일럿류 구조와 비교 평가