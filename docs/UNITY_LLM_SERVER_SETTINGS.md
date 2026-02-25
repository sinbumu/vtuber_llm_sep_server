# UNITY_LLM_SERVER_SETTINGS.md — Unity 앱용 LLM 서버 설정 정의 (LLM-only 기준)

이 문서는 **분리된 LLM-only Python 서버**를 Unity 앱에서 사용할 때,
사용자 설정 화면에 어떤 항목을 두고 언제 반영할지(기동 전 / 런타임)를 정리합니다.

전제:
- 현재 MVP 정책: **설정 변경은 서버 재시작으로 반영**
- 추후 필요 시: 일부 항목을 **런타임 재설정 API**로 확장 가능

---

## 1) 반영 타이밍 기준

### A. 기동 전(또는 재시작 시) 반영
다음 항목은 서버 프로세스 시작 시점에 확정되므로, 변경 시 재시작이 필요합니다.

- 서버 실행 옵션
  - `LLM_SERVER_HOST`
  - `LLM_SERVER_PORT`
  - `LLM_SERVER_LOG_LEVEL`
  - `LLM_SERVER_ENABLE_MCP`
- `conf.yaml` 기반 설정
  - LLM provider / model / base_url / api_key
  - `persona_prompt`
  - `tool_prompts` 구성
  - `conversation_agent_choice`, `use_mcpp`, `mcp_enabled_servers`

### B. 런타임 반영 가능 (현재 구현)
다음 항목은 API 요청 페이로드 단위로 전달되므로 즉시 반영됩니다.

- `POST /v1/chat` 요청
  - `conf_uid`
  - `history_uid`
  - `text`
- `WS /v1/ws/chat` 요청
  - `conf_uid`
  - `history_uid`
  - `text`

주의:
- 현재 서버는 “설정 수정 전용 API(예: /admin/reload)”가 없습니다.
- 따라서 설정 UI에서 모델/프롬프트를 바꿔도 **즉시 반영되지 않고 재시작 필요**합니다.

---

## 2) Unity 설정 화면 권장 구조 (MVP)

### 2-1) 서버 실행 설정 (기동 전)
- 서버 사용 여부 토글
- 서버 host / port
- MCP 사용 토글
- 로그 레벨
- (고급) 서버 실행 파일 경로 (`llm_server.exe`)

### 2-2) LLM 설정 (기동 전)
- Provider 선택 (`ollama_llm`, `gemini_llm` 등)
- Model
- Base URL
- API Key
- Temperature
- Persona Prompt (멀티라인)

### 2-3) 대화 실행 설정 (런타임)
- 현재 `conf_uid`
- 대화 시작/이어하기 (`history_uid` 관리)
- 사용자 입력 텍스트

---

## 3) Unity-서버 연동 권장 플로우 (MVP)

1. Unity 앱 시작
2. 저장된 설정으로 환경변수 구성
3. `llm_server.exe` 자식 프로세스 실행
4. `/health` 폴링으로 준비 완료 확인
5. 채팅 요청(`/v1/chat` 또는 `/v1/ws/chat`) 시작
6. 사용자가 기동 전 설정(모델/API 키/포트 등) 변경 시:
   - 서버 종료
   - 설정 저장
   - 서버 재기동

---

## 4) 추후 확장 포인트 (런타임 재설정)

필요 시 다음 API를 추가해 재시작 없는 반영으로 확장할 수 있습니다.

- `POST /admin/reload-config`
  - `conf.yaml` 재로드
  - 모델/프롬프트 교체
- `POST /admin/set-runtime-options`
  - 로그 레벨 등 일부 옵션 동적 변경
- `GET /admin/current-config`
  - 현재 적용 설정 조회

권장 순서:
1) MVP(재시작 반영) 안정화  
2) 자주 바뀌는 항목만 런타임 API로 점진 확장

---

## 5) 기획 체크리스트

- [ ] 사용자가 변경하는 항목을 “재시작 필요/불필요”로 명확히 라벨링
- [ ] 재시작 필요 항목 변경 시 UX 제공 (저장 후 재시작 안내/자동 재시작)
- [ ] 서버 상태 표시 (중지/기동중/실행중/오류)
- [ ] `/health` 실패 시 재시도 및 오류 메시지 정책 정의
- [ ] API Key 저장 정책(암호화/OS 보안 저장소) 정의

