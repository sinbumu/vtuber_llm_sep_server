# sep_MCP_SPLIT_PLAN.md — MCP 분리 준비 계획

이 문서는 **LLM-only 서버에서 MCP 기능을 가져갈 전제**로,
새 저장소 이관 전에 **경계/의존/설정 분리**를 안전하게 준비하는 체크리스트입니다.

---

## 1) 목표
- MCP 모듈을 LLM-only 서버에서 **옵션 기능**으로 유지
- 이관 시 MCP 관련 파일만 별도로 복사 가능하도록 구조 정리
- MCP 미사용 시 서버가 **부작용 없이 동작**하도록 보장

---

## 2) 현재 MCP 관련 구성 요소 (요약)

### 코드
- `src/open_llm_vtuber/mcpp/` 전체
  - `server_registry.py`
  - `tool_adapter.py`
  - `tool_manager.py`
  - `tool_executor.py`
  - `mcp_client.py`
  - `json_detector.py`

### 설정
- `mcp_servers.json`
- `prompts/utils/mcp_prompt.txt`

---

## 3) 분리 준비 단계 (지금 할 일)

### A) LLM-only 서버에서 MCP on/off 분리
- `llm_server/config.py`에서 **MCP 기본 비활성화** 유지
- MCP를 사용할 경우에만:
  - `mcp_servers.json` 로드
  - MCP ToolAdapter/Manager 초기화
  - system prompt에 `mcp_prompt` 삽입

### B) MCP 설정 경로 명확화
- LLM-only 기준의 설정 경로를 명확히 고정:
  - `BASE_DIR/mcp_servers.json`
  - `BASE_DIR/prompts/utils/mcp_prompt.txt`
- 경로가 없으면 **에러 로그만 남기고 계속 실행**

### C) MCP 통합 지점 단일화
- MCP 연동을 `llm_server/chat_service.py` 한 곳으로 모으기
  - system prompt 구성
  - tool_call 결과 반환 처리

---

## 4) 이관 후 파일 구조 제안

```
new-llm-server/
  src/
    llm_server/
      app.py
      chat_service.py
      mcp_bridge.py        # MCP 초기화/연결 전담 (옵션)
  prompts/
    utils/
      mcp_prompt.txt
  mcp_servers.json
```

---

## 5) 위험 요소 및 완화

- **MCP disabled인데 prompt만 들어가는 문제**
  - prompt 삽입은 MCP가 활성일 때만 수행
- **mcp_servers.json 누락**
  - 로그만 남기고 서버는 계속 실행
- **Tool 결과 처리 불명확**
  - tool 실행 결과는 `tool_executor` → LLM 응답 흐름에만 포함

---

## 6) 이관 체크리스트 (MCP 포함 시)

- MCP 비활성 상태에서 `/v1/chat` 정상 동작
- MCP 활성 상태에서 `mcp_prompt` 포함됨을 로그로 확인
- `mcp_servers.json`의 최소 예제(time, ddg-search) 동작 확인
- MCP 관련 실패 시 서버 중단 없음 확인

---

필요하면 위 내용을 기준으로 **실제 코드 분리 작업**까지 바로 진행할게요.
