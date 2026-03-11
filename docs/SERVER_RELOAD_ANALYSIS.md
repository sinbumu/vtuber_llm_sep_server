# SERVER_RELOAD_ANALYSIS.md

`docs/SERVER_RELOAD_ANALYSIS_TASK.md` 요구사항에 따라, 현재 분리된 **LLM-only Python 서버**의
초기화 구조와 설정 반영 시점을 코드 기준으로 분석한 결과입니다.

분석 기준:
- 현재 구조를 기준으로 판단
- 근거 없는 추정 금지
- 불확실한 항목은 보수적으로 분류
- MVP는 Unity 연동 단순성과 안정성을 우선

---

## 1. 현재 초기화 구조 요약

### 1-1) 설정 로딩 흐름

현재 서버는 설정을 두 단계에서 읽습니다.

1. **프로세스 시작 시**
   - `run_llm_server.py`
     - `LLM_SERVER_HOST`
     - `LLM_SERVER_PORT`
     - `LLM_SERVER_LOG_LEVEL`
   - `src/llm_server/app.py` startup
     - `LLM_SERVER_ENABLE_MCP`
     - `conf.yaml` 로드
     - tool prompt 파일 존재 여부 점검

2. **실제 chat 요청마다**
   - `POST /v1/chat`
   - `WS /v1/ws/chat`
   - 두 경로 모두 요청 시작 시 `load_config()`를 다시 호출
   - 즉, `conf.yaml` 기반 LLM 설정/프롬프트는 **요청 단위로 재적용**됨

### 1-2) 객체 생성 흐름

현재 LLM-only 서버는 **대부분의 핵심 객체를 요청마다 새로 생성**합니다.

요청 흐름:
1. `app.py`에서 `load_config()` 호출
2. `override_llm_only_config()`로 LLM-only 정책 적용
3. `run_chat_once()` 또는 `run_chat_stream()` 호출
4. `chat_service.py`에서:
   - `persona_prompt` + `tool_prompts`로 system prompt 구성
   - `LLMFactory.create_llm()`로 LLM 인스턴스 생성
   - `BasicMemoryAgent` 생성
   - 필요 시 history 파일 로드
   - 필요 시 MCP 구성 요소 생성

즉, **LLM / agent / system prompt / MCP 구성은 프로세스 전역 캐시가 아니라 요청 단위 생명주기**입니다.

### 1-3) 프로세스 생명주기 요약

#### 프로세스 레벨에서 고정되는 것
- `uvicorn` bind 정보 (`host`, `port`)
- `log_level`
- `app.state.mcp_enabled`
- 현재 `BASE_DIR` 해석 방식

#### 요청 단위로 다시 계산되는 것
- `conf.yaml`
- `persona_prompt`
- `tool_prompts`
- LLM provider / model / base_url / api_key / temperature
- `BasicMemoryAgent`
- history 로딩
- MCP 서버 목록 기반 초기화 (단, `app.state.mcp_enabled`가 켜져 있을 때만)

### 1-4) 중요 관찰

현재 구조는 “재로드 API가 아직 없을 뿐”, 이미 상당수 설정이 **다음 요청부터 자동 반영되는 구조**입니다.

특히 아래는 다음 요청 시 반영됩니다.
- `conf.yaml`의 provider / model / base_url / api_key
- `persona_prompt`
- `tool_prompts` 항목
- `prompts/utils/*.txt` 파일 내용

반대로 아래는 프로세스 재시작이 필요합니다.
- `LLM_SERVER_HOST`
- `LLM_SERVER_PORT`
- `LLM_SERVER_LOG_LEVEL`
- `LLM_SERVER_ENABLE_MCP`

---

## 2. 설정 항목별 분류표

| 설정 항목 | 현재 반영 시점 | 런타임 변경 가능 여부 | 재시작 필요 여부 | 근거 코드 위치 | 비고 |
|----------|----------------|----------------------|------------------|----------------|------|
| `LLM_SERVER_HOST` | 프로세스 시작 시 | 불가 | 필요 | `run_llm_server.py` | `uvicorn.run()` bind 정보 |
| `LLM_SERVER_PORT` | 프로세스 시작 시 | 불가 | 필요 | `run_llm_server.py` | 소켓 bind 재생성 필요 |
| `LLM_SERVER_LOG_LEVEL` | 프로세스 시작 시 | 사실상 별도 구현 필요 | 필요(현 구조) | `run_llm_server.py` | 현재는 startup 이후 재설정 경로 없음 |
| `LLM_SERVER_ENABLE_MCP` | startup 시 | 불가(현 구조) | 필요 | `src/llm_server/app.py` | `app.state.mcp_enabled`에 고정 |
| `conf.yaml` 경로 자체 | 코드 고정 | 불가(현 구조) | 필요 또는 코드 수정 필요 | `src/llm_server/config.py` | `load_config()`가 `read_yaml("conf.yaml")` 고정 호출 |
| YAML 내 `${ENV_VAR}` 치환 결과 | `conf.yaml` 읽을 때마다 | 가능 | 불필요 | `config_manager/utils.py` | 다음 요청에서 재반영 가능 |
| LLM provider | 요청마다 | 가능 | 불필요 | `app.py` + `chat_service.py` | 매 요청 `load_config()` 후 `LLMFactory.create_llm()` |
| LLM model | 요청마다 | 가능 | 불필요 | `chat_service.py` | 매 요청 새 LLM 생성 |
| LLM base_url | 요청마다 | 가능 | 불필요 | `chat_service.py` | 매 요청 새 LLM 생성 |
| LLM api_key | 요청마다 | 가능 | 불필요 | `chat_service.py` | 다음 요청부터 적용 |
| temperature | 요청마다 | 가능 | 불필요 | `chat_service.py` | 다음 요청부터 적용 |
| `persona_prompt` | 요청마다 | 가능 | 불필요 | `chat_service.py` | system prompt 재생성 |
| `tool_prompts` 매핑 | 요청마다 | 가능 | 불필요 | `chat_service.py`, `config.py` | prompt 이름 변경도 다음 요청 반영 |
| `prompts/utils/*.txt` 내용 | 요청마다 파일 로드 | 가능 | 불필요 | `chat_service.py` | prompt 파일 내용 수정 즉시 반영 가능 |
| `human_name` / `character_name` / `avatar` | 요청마다 | 가능 | 불필요 | `app.py`, `config.py` | history 저장 메타에 사용 |
| `faster_first_response` | 요청마다 | 가능 | 불필요 | `chat_service.py` | agent 생성 시 주입 |
| `segment_method` | 요청마다 | 가능 | 불필요 | `chat_service.py` | agent 생성 시 주입 |
| `conversation_agent_choice` | 요청마다 | 부분 가능 | 사실상 불필요 | `config.py` | 단, `mem0_agent`는 강제로 `basic_memory_agent`로 override |
| `use_mcpp` in `conf.yaml` | 요청마다 override | 부분 가능 | 조건부 | `config.py` | 실제 최종값은 `LLM_SERVER_ENABLE_MCP`에 좌우됨 |
| `mcp_enabled_servers` | 요청마다 | 가능(단 MCP가 이미 켜져 있을 때) | 조건부 | `chat_service.py`, `mcp_bridge.py` | env로 MCP off면 반영 안 됨 |
| `mcp_servers.json` 내용 | 요청마다 MCP init 시 | 가능(단 MCP on일 때) | 불필요 | `mcp_bridge.py` | 다음 요청에서 다시 읽힘 |
| history 파일 내용 | 요청마다 | 가능 | 불필요 | `chat_history_manager.py`, `chat_service.py` | agent memory는 파일에서 다시 로드 |
| TTS 설정 | 현재 LLM-only에서는 미사용 | 미확인/무의미 | 불필요 | `chat_service.py` | `tts_preprocessor_config=None` |
| 감정 처리 / Live2D | 현재 비활성 | 불가(현 구조) | 코드 복구 필요 | `chat_service.py` | `live2d_expression_prompt` 스킵, `live2d_model=None` |

---

## 3. 현재 구조에서 설정 파일 재로드 방식이 실현 가능한가?

### 결론
**가능합니다.** 다만 “전체 재로드 API”가 반드시 필요한 구조는 아닙니다.

이유:
- 현재도 `conf.yaml`은 chat 요청마다 다시 읽습니다.
- LLM/provider/persona/tool prompt는 이미 **다음 요청부터 자동 재반영**됩니다.

즉, `POST /admin/reload-config`는 “없으면 동작 불가”가 아니라:
- Unity가 설정 저장 후 반영 성공 여부를 확인하고 싶을 때
- 설정 유효성 검사/실패 응답을 받고 싶을 때
- 어떤 항목이 재시작 필요인지 명시적으로 받고 싶을 때  
유용한 **운영/관리용 API**에 가깝습니다.

### 어디까지 가능한가?

#### 현재 구조만으로 가능한 범위
- `conf.yaml` 수정
- `prompts/utils/*.txt` 수정
- `mcp_servers.json` 수정 (단 MCP on 상태)
- 이후 다음 `/v1/chat` 또는 `/v1/ws/chat` 요청 시 반영

#### 추가 API를 만들면 더 좋아지는 범위
- 수정된 설정에 대한 유효성 검사
- 현재 적용값 조회
- 변경 결과를 `applied` / `restart_required`로 분류해 반환

### 불가능하거나 위험한 항목
- bind 정보(`host`, `port`)
- startup env 기반 옵션(`LLM_SERVER_ENABLE_MCP`, `LLM_SERVER_LOG_LEVEL`)
- 현재 비활성화된 Live2D/TTS 파이프라인 복구 없는 감정/오디오 관련 재설정

---

## 4. 설정 파일 재로드 시나리오 분석

시나리오:
- Unity가 설정 파일 수정
- 서버가 `/admin/reload-config` 수신
- 적용 가능한 항목만 재반영
- 불가능한 항목은 restart required 반환

### 4-1) 재로드 진입점

가장 적절한 위치:
- `src/llm_server/app.py`

이유:
- FastAPI 엔드포인트 정의가 이미 이 파일에 모여 있음
- `load_config()`, `override_llm_only_config()`, `validate_tool_prompts()`를 바로 재사용 가능

### 4-2) 재로드 시 실제로 다시 만들어야 하는 객체

현재 구조상 “즉시 다시 생성해야 하는 전역 객체”는 거의 없습니다.

다음 요청에서 자동 재생성되는 것:
- LLM 인스턴스
- BasicMemoryAgent
- system prompt
- MCP components

즉 `/admin/reload-config`는 아래 정도만 해도 충분합니다.
- `conf.yaml` 재읽기
- 필요 시 `validate_config()`로 Pydantic 검증
- `override_llm_only_config()` 적용
- `validate_tool_prompts()` 실행
- 결과 반환

### 4-3) 세션 / history / memory 충돌

현재 LLM-only 서버는 유리한 구조입니다.

- history는 파일 기반
- memory는 `BasicMemoryAgent` 내부 메모리지만 요청마다 새 인스턴스
- WS도 현재는 장기 세션이 아니라 **1회 요청 후 종료되는 형태**

따라서 설정 재로드가:
- 기존 전역 세션 상태를 오염시키거나
- 오래 살아 있는 agent를 바꾸는 문제는 상대적으로 적습니다

### 4-4) 재로드 실패 시 처리

가능합니다.

권장 방식:
1. `conf.yaml` 읽기
2. `validate_config()`로 검증
3. tool prompt 존재 검사
4. 실패 시 `success=false`, `errors=[...]` 반환
5. 성공 시 `applied=[...]`, `restart_required=[...]` 반환

### 4-5) concurrent request 중 재로드 시 안전성

현재 구조에서는 비교적 안전하지만 주의점이 있습니다.

안전한 이유:
- 요청 시작 시 config snapshot을 읽고 로컬 변수로 사용
- 이후 LLM/agent도 요청 로컬 인스턴스

주의할 점:
- Unity가 `conf.yaml`을 쓰는 도중 다른 요청이 읽으면 YAML 파싱 실패 가능
- 따라서 Unity는 **임시 파일 저장 후 atomic rename** 방식이 좋습니다

권장:
- `conf.tmp.yaml` 작성
- 검증 후 `conf.yaml` 교체

---

## 5. Unity 연동용 관리 API 제안

### 5-1) `GET /health`

필요 이유:
- 프로세스 기동 완료 확인
- Unity가 백그라운드 서버 readiness 확인 가능

현재 난이도:
- 이미 구현됨

주의:
- readiness는 확인되지만 config validity나 LLM backend connectivity까지는 보장하지 않음

### 5-2) `GET /admin/current-config`

필요 이유:
- 현재 실제 적용 기준을 Unity가 조회 가능
- UI와 서버 상태 싱크에 도움

구현 난이도:
- 낮음

권장 반환:
- 현재 `conf.yaml` 요약
- runtime env 기반값 (`mcp_enabled`, host/port/log_level)
- 민감값은 마스킹 (`api_key`)

주의:
- API key 전체 노출 금지
- 외부 공개 환경이면 인증 필요

### 5-3) `POST /admin/reload-config`

필요 이유:
- Unity가 “저장 후 적용” 버튼을 제공할 수 있음
- 성공/실패/재시작 필요 항목을 명확히 반환 가능

구현 난이도:
- 낮음 ~ 중간

권장 반환:
```json
{
  "success": true,
  "applied": ["provider", "model", "persona_prompt"],
  "restart_required": ["LLM_SERVER_PORT", "LLM_SERVER_ENABLE_MCP"],
  "warnings": []
}
```

주의:
- 현재 구조에서는 실질 적용이 “다음 요청부터”라는 점을 명시해야 함

### 5-4) `POST /admin/set-runtime-options`

필요 이유:
- 파일 편집 없이 제한된 런타임 옵션 조정 가능

구현 난이도:
- 중간

현재 권장 여부:
- **MVP에서는 비권장**

이유:
- 현재 구조는 파일 기반 재반영이 이미 충분히 유연함
- 잘못 설계하면 conf.yaml과 메모리 상태가 달라지는 “이중 진실(source of truth)” 문제가 생김

---

## 6. 최소 개조안

### 6-1) 어떤 파일을 어떻게 바꾸면 되는가

#### `src/llm_server/app.py`
- 신규 관리 API 추가
  - `GET /admin/current-config`
  - `POST /admin/reload-config`

#### `src/llm_server/config.py`
- reload helper 추가
  - config load
  - `validate_config()` 수행
  - tool prompt 검사
  - restart-required 필드 계산

#### 선택: `run_llm_server.py` / `utils.py`
- exe 기준 외부 설정 파일 경로 지원

### 6-2) 새로운 reload 경로를 어디에 둘지

권장:
- `src/llm_server/app.py`

이유:
- 현재 엔드포인트 집중 위치
- 구현 가장 단순

### 6-3) Unity는 어떻게 호출하면 되는가

MVP 권장 흐름:
1. Unity가 `conf.yaml` 저장
2. 서버 재시작이 필요한 항목인지 Unity가 자체 분류
3. 재시작 필요면 프로세스 재기동
4. 재시작 불필요 항목이면 그냥 다음 채팅 요청 진행
5. 선택적으로 `/admin/reload-config` 호출하여 검증/피드백 수신

---

## 7. 권장 구현안 비교

### 안 A. 재시작 중심

- 설정 변경 시 서버 종료 후 재기동
- 런타임 변경 최소화

#### 평가
- 구현 난이도: 가장 낮음
- 안정성: 가장 높음
- Unity 연동 편의성: 높음
- 유지보수성: 높음

#### 장점
- host/port/env/MCP 등 모든 케이스를 동일 방식으로 처리 가능
- 운영 모델이 단순함
- 디버깅이 쉬움

#### 단점
- 설정 변경 때 UX가 다소 무거움
- 짧지만 서버 재기동 공백이 생김

### 안 B. 부분 재로드 중심

- 가능한 항목만 런타임 재로드
- 불가능 항목은 재시작 필요로 분리

#### 평가
- 구현 난이도: 중간
- 안정성: 중간 이상
- Unity 연동 편의성: 높음
- 유지보수성: 중간

#### 장점
- provider/model/persona/tool prompts는 이미 구조상 잘 맞음
- UX 개선 여지 큼

#### 단점
- “무엇이 즉시 반영되고 무엇이 재시작 필요한가”를 UI/서버 모두 명확히 유지해야 함
- conf 파일 쓰기 경쟁/검증 실패 처리 설계 필요

---

## 8. 최종 권고

### MVP 권고
**안 A(재시작 중심)** 을 먼저 채택하는 것이 가장 합리적입니다.

이유:
1. Unity와의 연동이 가장 단순함
2. startup env / bind / MCP 토글까지 일관되게 처리 가능
3. 현재 구조 변경을 최소화함

### 차후 확장 권고
그 다음 단계로 **안 B(부분 재로드 중심)** 를 추가하는 것이 좋습니다.

우선순위:
1. `GET /health` 유지
2. `GET /admin/current-config` 추가
3. `POST /admin/reload-config` 추가
4. 정말 필요할 때만 `POST /admin/set-runtime-options`

---

## 9. EXE 배포 관점 추가 관찰

현재 exe 구조는 추가 검토가 필요합니다.

- `llm_server.utils.get_base_dir()`는 frozen 환경에서 `sys._MEIPASS`를 기준으로 동작
- `load_config()`는 상대 경로 `conf.yaml`를 읽음

즉, 현재 exe는 **Unity가 exe 옆의 외부 `conf.yaml`를 수정하는 구조와 바로 일치하지 않을 가능성**이 있습니다.

이 부분은 Unity 연동 전 별도 개조가 필요합니다.

권장 방향:
- 외부 설정 경로를 우선 탐색
  - 예: `exe_dir/conf.yaml`
- 없으면 번들 기본 설정 fallback

이 수정이 들어가면:
- Unity가 exe와 같은 폴더의 설정 파일을 직접 관리
- `/admin/reload-config`와 조합해 재시작 없는 반영도 더 자연스러워짐

---

## 10. 최종 질문에 대한 명확한 답

### 1. 현재 구조에서 설정 파일 재로드 방식이 실현 가능한가?
- **예. 실현 가능함**

### 2. 가능하다면 어디까지 가능한가?
- 다음 요청부터 반영되는 수준으로는 이미 상당수 가능
- provider / model / base_url / api_key / persona / tool prompts / prompt 파일 / history 관련 설정

### 3. 불가능하거나 위험한 항목은 무엇인가?
- `host`, `port`, `log_level`, `LLM_SERVER_ENABLE_MCP`
- exe 외부 설정 경로 미정 상태
- 파일 쓰기 경쟁 중 YAML 파싱 실패 위험

### 4. MVP에서는 어떤 방식이 가장 합리적인가?
- **재시작 중심**

### 5. Unity 앱과의 연동 관점에서 어떤 관리 API가 최소로 필요할까?
- 필수: `GET /health`
- 권장 최소 추가:
  - `GET /admin/current-config`
  - `POST /admin/reload-config`

