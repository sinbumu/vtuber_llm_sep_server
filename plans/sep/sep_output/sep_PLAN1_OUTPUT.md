# sep_PLAN1_OUTPUT.md — 분리 계획 산출물

이 문서는 `sep_PLAN1.md` 요구사항에 따라 **LLM 전용 백엔드 분리 계획**을 정리한 산출물입니다.

---

## Architecture sketch (text)

```
[Unity Client]
   |
   |  HTTP/WS (text only)
   v
[LLM-only FastAPI Server]
   - /health
   - /v1/chat (one-shot)
   - /v1/ws/chat (stream)
   |
   +--> Config Loader (conf.yaml + prompts/utils)
   +--> History Manager (chat_history/*.json)
   +--> Prompt Builder (persona + tool_prompts)
   +--> BasicMemoryAgent (messages 구성)
   +--> Stateless LLM (Ollama/OpenAI-compatible)
```

핵심 원칙:
- **ASR/TTS/Live2D/VAD/OBS**는 완전 제외
- **LLM 호출 + context + history**만 담당
- 기존 코어 모듈 재사용 (최소 수정)

---

## Keep list (반드시 재사용)

- `src/open_llm_vtuber/agent/agents/basic_memory_agent.py`  
  - messages 구성, memory 로직
- `src/open_llm_vtuber/agent/stateless_llm/*`  
  - LLM 호출 인터페이스
- `src/open_llm_vtuber/chat_history_manager.py`  
  - history 생성/저장/로드
- `src/open_llm_vtuber/config_manager/*`  
  - `SystemConfig`, `CharacterConfig`, `AgentConfig`, `read_yaml()` 등
- `prompts/utils/*.txt`  
  - system prompt 구성에 필요
- `conf.yaml` + `config_templates/*.yaml`

---

## Remove / Disable list (분리 시 제외)

- `src/open_llm_vtuber/asr/*`
- `src/open_llm_vtuber/tts/*`
- `src/open_llm_vtuber/vad/*`
- `src/open_llm_vtuber/live2d_model.py`, `live2d-models/`
- `src/open_llm_vtuber/conversations/*` (오디오/Live2D 경로 의존)
- `routes.py`의 `/asr`, `/tts-ws`, `/live2d-models/info`
- OBS/overlay/desktop pet 관련 코드/리소스
- Frontend 서브모듈 및 정적 자산 (`frontend/`, `web_tool/`)

---

## Call flow (LLM-only /v1/chat)

1) **입력 수신**  
   - `{ conf_uid, history_uid?, text }`
2) **BASE_DIR 고정**  
   - `chat_history` / `prompts` / `conf.yaml` 절대경로 기준
3) **history 처리**  
   - `history_uid` 없음 → `create_new_history(conf_uid)`
   - 있으면 파일 존재 검증, 없으면 404
4) **system prompt 구성**  
   - `ServiceContext.construct_system_prompt(persona_prompt)` 사용  
   - `prompts/utils/*.txt` 로드 실패 시 로그만 남기고 계속
5) **memory 로드**  
   - `agent.set_memory_from_history(conf_uid, history_uid)`
6) **messages 구성**  
   - `BasicMemoryAgent._to_messages()` or equivalent
7) **LLM 호출**  
   - `StatelessLLMInterface.chat_completion()`  
   - timeout 적용
8) **history 저장**  
   - user/assistant 각각 `store_message()`  
9) **응답 반환**  
   - `{ history_uid, text }`

---

## Risks & mitigations

- **ServiceContext가 ASR/TTS/VAD/Live2D를 초기화**  
  → LLM-only init 경로 추가 (load_from_config 미사용)
- **상대 경로 문제** (`chat_history`, `prompts`)  
  → 엔트리포인트에서 `BASE_DIR` 고정
- **tool_prompts 파일 누락**  
  → 에러 로그만 남기고 서버는 계속 동작
- **history_uid 파일 없음**  
  → 404 반환 또는 WS error(code="history_not_found")
- **MCP 자동 활성화 부작용**  
  → LLM-only 서버에서 `use_mcpp` 강제 false
- **mem0_agent 미구현**  
  → 기본 비활성화 + README 명시
- **LLM 호출 타임아웃**  
  → timeout 설정 + 실패 시 502 / WS error(code="llm_error")
- **의존성 과다**  
  → `requirements-llm-server.txt`로 최소 의존성 분리

---

## Proposed file changes (high level)

### 신규
- `src/llm_server/` (or `src/unity_llm_server/`)
  - `app.py` (FastAPI entry)
  - `chat_service.py` (prompt + memory + llm 호출)
- `requirements-llm-server.txt` (최소 의존성)
- `README_LLM_SERVER.md` (실행법 + curl 예시)

### 수정 (최소)
- `config_manager/utils.py`  
  - BASE_DIR 기반 경로 처리 보조
- `basic_memory_agent.py`  
  - 필요 시 LLM-only 경로에 맞춘 helper 추가

---

## 추가 적용 요구사항 (요약)

1) ServiceContext LLM-only init 경로  
2) BASE_DIR 절대경로화  
3) tool_prompts 누락 시 안전 처리  
4) history_uid 검증 + 404 / WS error  
5) MCP 기본 비활성화  
6) mem0_agent 비활성화 + README 명시  
7) `requirements-llm-server.txt` 추가  
8) LLM timeout + 502 / WS error 처리
