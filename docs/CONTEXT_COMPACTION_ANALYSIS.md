# CONTEXT_COMPACTION_ANALYSIS.md

## 목적

현재 프로젝트의 대화 컨텍스트 누적 구조를 코드 기준으로 분석하고,  
장시간 대화에서 **페르소나와 중요한 맥락은 유지**하면서도  
모델 입력은 **주기적으로 경량화**할 수 있는 현실적인 구조를 제안한다.

이번 문서는 즉시 구현안이 아니라, **현재 구조 분석 + 안전한 삽입 지점 + MVP 권고안** 정리에 초점을 둔다.

---

## 확인 범위 / 전제

- 주로 확인한 경로:
  - `src/open_llm_vtuber/chat_history_manager.py`
  - `src/open_llm_vtuber/agent/agents/basic_memory_agent.py`
  - `src/open_llm_vtuber/service_context.py`
  - `src/open_llm_vtuber/websocket_handler.py`
  - upstream `src/open_llm_vtuber/conversations/conversation_handler.py`
  - upstream `src/open_llm_vtuber/conversations/single_conversation.py`
  - upstream `src/open_llm_vtuber/conversations/group_conversation.py`
  - upstream `src/open_llm_vtuber/conversations/conversation_utils.py`
  - `src/open_llm_vtuber/agent/agents/hume_ai.py`
  - `src/open_llm_vtuber/agent/agents/letta_agent.py`
  - `src/llm_server/app.py`
  - `src/llm_server/chat_service.py`
- 현재 워크스페이스에는 `src/open_llm_vtuber/conversations/*`가 없지만, upstream 공개 저장소의 원본 파일을 추가 확인했다.
- 따라서 원본 WebSocket 서버의 단일 대화, 그룹 대화, proactive speak, interrupt 시 히스토리 저장 시점까지 보강 분석이 가능했다.
- 히스토리 저장/로드, 메모리 구조, system/persona/tool prompt 주입, `conf_uid`/`history_uid` 흐름, LLM-only 경로는 로컬 코드와 upstream 원본을 함께 대조했다.

---

## A. 현재 대화 컨텍스트 구조 요약

### 1) 히스토리 누적 방식

- 공통 히스토리 저장 계층은 `chat_history/<conf_uid>/<history_uid>.json` 파일이다.
- 생성은 `create_new_history(conf_uid)`가 담당한다.
- 대화 본문 로드는 `get_history(conf_uid, history_uid)`가 담당하며, 첫 번째 `metadata` 레코드는 제외하고 반환한다.
- 메타데이터는 `get_metadata()` / `update_metadate()`로 읽고 쓴다.
- upstream 원본 기준으로 단일 대화의 사용자 입력은 `process_single_conversation()`에서, AI 응답은 같은 함수의 turn 종료 시 `store_message()`로 저장된다.
- 그룹 대화에서는 `process_group_conversation()`이 시작 시 사용자 입력을 모든 멤버의 history에 저장하고, 각 AI 턴이 끝날 때 응답을 모든 멤버의 history에 저장한다.
- interrupt 시에는 `handle_individual_interrupt()` / `handle_group_interrupt()`가 잘린 AI 응답과 `[Interrupted by user]`를 history에 저장한다.

### 2) 메모리 구조

- 기본 메모리 구조는 `BasicMemoryAgent._memory` 리스트다.
- `set_memory_from_history()`가 파일 히스토리를 읽어 `_memory`로 재구성한다.
- `BasicMemoryAgent._to_messages()`가 `_memory.copy()`를 시작점으로, 현재 사용자 입력을 추가해 LLM 입력용 `messages`를 만든다.
- 시스템 프롬프트는 `_memory`와 별도로 `self._system`에 보관된다.

### 3) 모델 호출 직전 컨텍스트 조립

- 원본 공통 경로에서 메시지 조립의 핵심 지점은 `BasicMemoryAgent._to_messages()`다.
- 실제 LLM 호출은 `BasicMemoryAgent._chat_function_factory()` 내부에서 이뤄진다.
- OpenAI 계열 어댑터는 `system`을 `messages` 앞에 prepend하고, Claude 계열은 별도 `system=` 인자로 전달한다.
- upstream 단일 대화 경로는 `process_single_conversation()` -> `create_batch_input()` -> `context.agent_engine.chat(batch_input)` 순서로 흐른다.
- upstream 그룹 대화 경로는 `GroupConversationState.conversation_history`에 `"name: text"` 형식 문자열을 누적하고, 각 멤버 턴마다 `memory_index[uid]` 이후의 새 문자열만 이어붙여 `new_context`를 만든 뒤 `create_batch_input(input_text=new_context, ...)`로 전달한다.

### 4) system / persona / tool prompt 주입 방식

- 원본 경로에서는 `ServiceContext.construct_system_prompt()`가 `character_config.persona_prompt`를 시작점으로 삼는다.
- 여기에 `system_config.tool_prompts`가 가리키는 `prompts/utils/*.txt`들을 이어 붙인다.
- `live2d_expression_prompt`는 `Live2dModel.emo_str`를 삽입해 감정 태그 허용 목록을 만든다.
- `mcp_prompt`는 별도 처리 경로를 가진다.
- LLM-only 경로에서는 `llm_server.chat_service._build_system_prompt()`가 유사한 역할을 하되, `live2d_expression_prompt`는 의도적으로 생략한다.

### 5) `conf_uid` / `history_uid` 흐름

- `conf_uid`는 히스토리 네임스페이스이자 캐릭터/설정 구분자 역할을 한다.
- `history_uid`는 특정 세션 히스토리 식별자다.
- 원본 WebSocket 경로는 `fetch-and-set-history` / `create-new-history`에서 이를 서비스 컨텍스트와 에이전트에 연결하고, 실제 대화 turn에서는 `process_single_conversation()` / `process_group_conversation()`가 이 값을 이용해 파일 history를 append한다.
- LLM-only 경로는 `/v1/chat`, `/v1/ws/chat` 요청마다 `history_uid`를 확인 또는 생성하고, 파일 히스토리를 다시 읽어 매 요청마다 agent memory를 복원한다.

### 6) 특이 사항

- `HumeAIAgent`는 일반 메시지 메모리보다 `metadata.resume_id`를 더 중요하게 다룬다.
- `LettaAgent`는 서버 자체 저장소를 전제로 하므로 `set_memory_from_history()`가 사실상 비어 있다.
- 따라서 "컨텍스트 축약"의 핵심 대상은 대부분 `BasicMemoryAgent` 경로다.
- upstream 원본에는 proactive speak가 있으며, `conversation_handler.handle_conversation_trigger()`가 `skip_memory=True`, `skip_history=True` 메타데이터를 넣어 메모리/로컬 히스토리에서 모두 제외하려고 한다.
- 그룹 대화는 `BasicMemoryAgent._memory`만 쓰는 것이 아니라, 별도 `GroupConversationState.conversation_history`와 `memory_index`를 함께 사용한다. 따라서 그룹 경로 compaction은 agent memory만 보면 불충분하다.

---

## B. 문제점 정리

### 1) 장시간 대화에 취약한 이유

- `_memory` 전체를 그대로 `messages`에 넣는 구조라서 명시적 슬라이딩 윈도우나 요약 단계가 없다.
- 오래된 잡담, 반복 대화, 중요도가 낮은 대화도 최신 핵심 맥락과 같은 가중치로 계속 포함된다.
- 컨텍스트 길이 초과, 응답 품질 저하, 지연 증가, 비용 증가 가능성이 높다.

### 2) 현재 구조의 구조적 리스크

- 시스템 프롬프트와 대화 히스토리가 분리되어 있지 않아 보이는 것이 아니라, 실제로는 잘 분리되어 있다. 따라서 축약 대상은 주로 history/messages 쪽이어야 한다.
- `ServiceContext.load_cache()`는 세션 컨텍스트에 `agent_engine`를 참조로 넘긴다. 원본 경로에서 `_memory` 자체를 공격적으로 변형하는 로직은 세션 간 간섭 위험을 만들 수 있다.
- LLM-only 서버는 매 요청마다 agent를 새로 만들기 때문에 구조가 더 단순하지만, 현재 구현상 사용자 메시지를 파일에 먼저 저장하고 다시 로드한 뒤 `_to_messages()`에서 같은 턴을 또 append하는 경로가 있어 최신 사용자 턴이 중복 주입될 가능성이 있다.
- `llm_server.chat_service.history_exists()`는 `_get_safe_history_path()`가 문자열을 반환하는데 `.exists()`를 호출하고 있어 현재 구현 기준으로는 동작 이상 가능성이 있다.
- upstream proactive speak는 `skip_memory` / `skip_history`를 쓰므로, compaction 로직이 metadata 플래그를 무시하면 원래 history에 남지 않아야 할 turn을 summary에 잘못 포함할 수 있다.
- upstream 그룹 대화는 `conversation_history`를 문자열 리스트로 관리하고 AI별 `memory_index`를 따로 둔다. 따라서 그룹 경로에서는 "최근 N턴" 기준을 `_memory`가 아니라 `conversation_history` 기준으로 따로 정의해야 한다.

### 3) Unity 연동 관점 문제

- 현재 Unity용 LLM-only 경로는 `history_uid`를 중심으로 "이어서 대화"를 구현하므로, compaction이 히스토리 재개 품질을 깨면 UX에 바로 영향이 간다.
- 설정 reload 이후 persona가 바뀌었는데 오래된 summary가 남아 있으면 응답 스타일이 뒤섞일 수 있다.
- 추후 감정 태그를 다시 사용할 경우, 요약 과정에서 감정 태그나 중요한 상태 전이가 사라질 수 있다.

---

## C. 축약 가능한 정보 / 유지해야 할 정보 표

| 정보 종류 | 현재 저장 방식 | 유지 필요성 | 축약 가능 여부 | 비고 |
|-----------|----------------|-------------|----------------|------|
| `persona_prompt` | `conf.yaml` / config 로드 후 system prompt로 합성 | 절대 유지 | 히스토리 축약 대상 아님 | history와 분리 유지해야 함 |
| tool prompt 텍스트 | `prompts/utils/*.txt` -> system prompt append | 높음 | 히스토리 축약 대상 아님 | MCP/그룹/표정 prompt는 개별 정책 필요 |
| Live2D emotion map | `model_dict.json` -> `Live2dModel.emo_str` | 원본 경로에서 중요 | 요약 가능하지 않음 | LLM-only는 현재 비활성 |
| `conf_uid` | 히스토리 폴더 네임스페이스 / 설정 구분자 | 절대 유지 | 불가 | 요약/메타는 반드시 `conf_uid` 단위 분리 |
| `history_uid` | 히스토리 파일 식별자 | 절대 유지 | 불가 | 이어하기 UX의 핵심 |
| Hume `resume_id`, `agent_type` | history metadata | Hume 경로에서 절대 유지 | 불가 | 누락 시 이어하기 실패 가능 |
| 최근 대화 5~20턴 | history 파일 + `_memory` | 매우 높음 | 부분 축약 가능 | 최신 세부 문맥 유지 구간 |
| 오래된 일반 잡담 | history 파일 + `_memory` | 낮음 | 높음 | 요약 또는 입력 제외 가능 |
| 사용자 핵심 선호/금지사항 | 현재는 일반 대화 속 텍스트에 섞임 | 매우 높음 | 요약은 가능하나 삭제 금지 | 별도 추출 블록 후보 |
| 현재 세션의 목표/약속/해야 할 일 | 일반 대화 속 텍스트 | 높음 | 요약 가능 | summary에 남겨야 함 |
| 인터럽트 흔적 (`[Interrupted by user]`) | `_memory`에 일반 메시지로 누적 | 중간~높음 | 신중히 축약 | turn 상태 왜곡 가능 |
| 그룹 대화 컨텍스트 | `_memory`에 user role로 주입 | 높음 | 요약 가능 | 참가자 문맥을 잃지 않게 해야 함 |
| 표시용 `name`, `avatar`, `timestamp` | history JSON 필드 | LLM 입력 기준 낮음 | 높음 | UI용 보존값, 모델 입력에는 불필요 |
| 원문 transcript 전체 | history JSON | 원본 보존 권장 | 모델 입력 기준 축약 가능 | "보존"과 "입력 포함"은 분리해야 함 |

### 분류 요약

- 절대 유지해야 하는 정보
  - `persona_prompt`
  - `conf_uid`
  - `history_uid`
  - Hume `resume_id` / `agent_type`
  - 현재 캐릭터/설정 식별에 필요한 정보
- 최근 몇 턴만 유지하면 되는 정보
  - 최신 대화 N턴
  - 현재 질문과 직접 연결되는 최근 답변들
  - 직전 인터럽트, 직전 합의/계획
- 주기적으로 요약 가능한 정보
  - 오래된 일반 대화
  - 이전 세션에서 반복된 설정 확인 대화
  - 장기 목표, 선호, 금지사항, 약속, 진행상태
- 버려도 되는 정보
  - UI 표시 전용 메타(`avatar`, 일부 `name`, `timestamp`)
  - 모델 판단에 도움이 거의 없는 짧은 반복 잡담

---

## D. 구현 후보안 비교표

| 안 | 설명 | 구현 난이도 | 위험도 | 품질 기대 | 추천도 |
|----|------|-------------|--------|----------|--------|
| A. Recent window만 유지 | 최근 N개 대화만 model input에 넣고 나머지는 원본 history에만 남김 | 낮음 | 낮음 | 중간 | 높음 |
| B. Summary + recent window | 오래된 대화는 summary로 압축하고, 최근 대화만 원문 유지 | 중간 | 중간 | 높음 | 매우 높음 |
| C. 중요 정보 분리 + recent window | 핵심 정보만 별도 memory block으로 추출하고 최근 대화만 유지 | 중간~높음 | 중간~높음 | 높음 | 중간 |

### 안 A. Recent window만 유지

- 현재 코드 적합성: 매우 높음
- 구현 난이도: 가장 낮음
- 장점:
  - `BasicMemoryAgent._to_messages()` 전후에 쉽게 넣을 수 있다.
  - 원본 history JSON 포맷을 거의 건드리지 않는다.
  - Unity 이어하기 계약을 깨지 않기 쉽다.
- 단점:
  - 오래된 중요한 맥락도 같이 사라질 수 있다.
  - 장기 세션 품질 유지에는 한계가 있다.

### 안 B. Summary + recent window

- 현재 코드 적합성: 높음
- 구현 난이도: 중간
- 장점:
  - 원문 history는 보존하고, 모델 입력은 경량화할 수 있다.
  - 장기 맥락을 유지하면서도 최근 상호작용 품질을 지키기 좋다.
  - `history metadata`를 summary 저장소로 재활용하기 쉽다.
- 단점:
  - summary 생성 시점, 갱신 정책, persona 변경 시 무효화 정책이 필요하다.
  - 요약 품질이 낮으면 오히려 사실 왜곡 위험이 있다.

### 안 C. 중요 정보 분리 + recent window

- 현재 코드 적합성: 중간
- 구현 난이도: 중간~높음
- 장점:
  - 장기적으로 가장 깔끔한 구조가 될 수 있다.
  - 사용자 선호, 설정, 약속 등을 명시적 블록으로 관리하기 좋다.
- 단점:
  - "무엇이 중요한 정보인가"를 안정적으로 추출하는 로직이 필요하다.
  - 현재 코드 구조를 거의 그대로 활용하기보다는 별도 규약을 도입해야 한다.
  - 잘못 추출하면 persona leakage 또는 기억 누락이 생긴다.

### 비교 결론

- **최종적으로 가장 적합한 방향은 B. `summary + recent window`**다.
- 다만 **MVP 구현 부담이 가장 낮은 것은 A. `recent window only`**다.
- 따라서 실무 권장 흐름은 다음과 같다.
  - 1차: A를 먼저 넣어 모델 입력을 즉시 가볍게 한다.
  - 2차: 저장소/계약은 유지한 채 B로 확장한다.

---

## E. 코드 삽입 지점 제안

### 후보 1. `BasicMemoryAgent._to_messages()` 직전 또는 내부 helper

- 관련 위치:
  - `src/open_llm_vtuber/agent/agents/basic_memory_agent.py`
  - LLM-only 호출부: `src/llm_server/chat_service.py`

- 제안 방식:
  - `_memory` 원본은 유지하고, LLM에 전달할 `messages`만 축약한다.
  - 예: `_to_messages()` 내부에서 `messages = compact_context(self._memory, input_data, policy)` 식 helper 호출

- 장점:
  - 현재 코드 변경이 가장 적다.
  - 원본 history 보존과 모델 입력 경량화를 명확히 분리할 수 있다.
  - 원본 경로와 LLM-only 경로에 동시에 적용 가능하다.

- 위험성:
  - `_memory`는 계속 커질 수 있다.
  - 원본 WebSocket 경로는 `agent_engine` 공유 가능성이 있어 `_memory` 자체를 직접 mutate하면 위험하다.
- upstream 그룹 대화는 `GroupConversationState.conversation_history`라는 별도 누적 버퍼를 사용하므로, 공통 compaction helper를 넣더라도 그룹 경로 전용 보완이 필요하다.

- 구현 난이도:
  - 낮음

- 평가:
  - **MVP 1순위 삽입 지점**

### 후보 2. `BasicMemoryAgent.set_memory_from_history()` 이후

- 관련 위치:
  - `src/open_llm_vtuber/agent/agents/basic_memory_agent.py`

- 제안 방식:
  - history 파일에서 로드한 뒤 summary + recent window 형태로 `_memory`를 구성한다.

- 장점:
  - 이어하기 시점에서 한 번만 정리하면 된다.
  - LLM-only는 매 요청마다 여기로 들어오기 때문에 효과가 즉시 반영된다.

- 위험성:
  - 원본 live session에서 이후 turn이 계속 누적되므로 단독 해법으로는 부족하다.
  - Hume/Letta는 같은 계약을 쓰지 않는다.

- 구현 난이도:
  - 중간

- 평가:
  - resume-time 보조 지점으로 좋다.

### 후보 3. `chat_history_manager` 계층

- 관련 위치:
  - `src/open_llm_vtuber/chat_history_manager.py`

- 제안 방식:
  - `metadata` 첫 레코드에 summary와 compaction 상태를 저장한다.
  - 예: `metadata.context_summary`, `metadata.summary_turn_count`, `metadata.persona_hash`

- 장점:
  - 원문 history와 별도 요약 저장소를 같은 파일에서 관리할 수 있다.
  - LLM-only와 원본 경로가 공통으로 접근하는 저장 계층이다.

- 위험성:
  - upstream 기준으로 단일/그룹/interrupt 저장 경로는 확인됐지만, 그룹 대화의 실시간 입력 구성은 `conversation_history` 버퍼도 같이 보므로 이 계층만 수정해서는 그룹 입력 경량화가 끝나지 않는다.
  - history JSON 포맷 확장을 잘못하면 기존 클라이언트/도구와 충돌할 수 있다.

- 구현 난이도:
  - 중간

- 평가:
  - **summary 영속화 저장소로 강력 추천**

### 후보 4. LLM-only 전용 `run_chat_once()` / `run_chat_stream()`

- 관련 위치:
  - `src/llm_server/chat_service.py`

- 제안 방식:
  - Unity용 LLM-only 서버에 한해 먼저 compaction을 적용한다.
  - 특히 현재 request-per-agent 구조와 잘 맞는다.

- 장점:
  - Unity MVP를 가장 빠르게 안정화할 수 있다.
  - 현재 중복 user turn 문제 같은 관련 정리도 같이 하기 쉽다.

- 위험성:
  - 원본 경로와 로직이 분기된다.
  - 장기적으로 compaction 규칙이 이중화될 수 있다.

- 구현 난이도:
  - 낮음~중간

- 평가:
  - **LLM-only 우선 MVP라면 현실적**

---

## Summary 저장 위치 제안

### 권장안: `history metadata` 내부에 저장

- 추천 위치: `chat_history/<conf_uid>/<history_uid>.json`의 첫 번째 `metadata` 레코드
- 추천 필드 예시:
  - `context_summary`
  - `summary_message_count`
  - `summary_updated_at`
  - `summary_policy`
  - `persona_hash`

### 이유

- 이미 metadata 구조가 존재한다.
- 원문 메시지 배열과 summary를 분리 저장할 수 있다.
- LLM-only의 매 요청 rehydrate 구조와도 잘 맞는다.
- 별도 파일을 늘리지 않아 Unity 배포/백업/이동이 단순하다.

### 비권장안

- `BasicMemoryAgent._memory` 내부에만 summary 유지
  - LLM-only는 매 요청 새 agent를 생성하므로 지속성이 약하다.
- 별도 summary 파일
  - 파일 동기화/이동/삭제 정책이 더 복잡해진다.

---

## Compaction 실행 트리거 후보

| 트리거 | 장점 | 단점 | MVP 적합성 |
|--------|------|------|------------|
| 메시지 개수 기준 | 구현이 가장 단순 | 토큰 길이를 정확히 반영하지 못함 | 매우 높음 |
| 토큰 수 기준 | 가장 정교 | provider별 토크나이저/추정 로직 필요 | 중간 |
| 세션 길이 기준 | UX 관점 설명이 쉬움 | 실제 입력량과 어긋날 수 있음 | 낮음 |
| 수동 호출 기준 | 디버깅/관리 용이 | 자동 보호가 안 됨 | 중간 |

### 권장 순서

1. 메시지 개수 기준
2. 수동 호출 기준
3. 토큰 수 기준

### MVP 권장 트리거

- 최근 N턴 유지 정책
- 예: 전체 메시지 수가 24~40개를 넘으면 오래된 구간을 compaction 후보로 본다
- 관리자/Unity가 명시적으로 재요약을 요청하는 수동 API는 2차로 고려 가능

---

## Unity 앱 UX 영향 포인트

### 1) history 이어하기 품질

- recent window만 쓰면 오래된 약속이나 장기 목표가 사라질 수 있다.
- summary가 있으면 이어하기 품질은 좋아지지만, summary 품질에 따라 기억 왜곡이 생길 수 있다.

### 2) 응답 스타일 변화

- persona는 system prompt에 있으므로 원칙상 축약 대상이 아니다.
- 다만 오래된 summary가 과거 persona 상태를 반영한 채 남아 있으면 설정 변경 후 톤이 어색해질 수 있다.
- 이를 막으려면 `persona_hash` 같은 무효화 기준이 필요하다.

### 3) 세션 재시작 시 기억 유지 정도

- LLM-only 서버는 매 요청마다 history를 다시 읽어 memory를 재구성하므로, summary 저장 구조가 곧 재시작 후 기억 품질을 좌우한다.
- 즉 "runtime memory only"보다 "history metadata summary"가 Unity 친화적이다.

### 4) 감정 태그 / 액션 연동

- 현재 LLM-only는 감정 태그를 공식 처리하지 않지만, 차후 다시 쓸 수 있다.
- 따라서 summary 설계 시 감정 태그 자체를 핵심 정보로 보존할지 여부를 미리 결정해야 한다.
- 최소한 감정 상태 변화가 중요한 캐릭터라면, summary에서 감정 관련 상태를 자연어로 남기는 편이 안전하다.

---

## F. 최종 권고안

### 1) 현재 프로젝트에 가장 적합한 컨텍스트 축약 방식은 무엇인가?

**최종 목표로는 `summary + recent window`가 가장 적합하다.**

이유:

- 원본 history는 그대로 보존할 수 있다.
- 최근 대화의 디테일과 장기 맥락을 동시에 유지할 수 있다.
- 현재 코드 구조에서 system/persona/tool prompt를 건드리지 않고, 대화 messages만 경량화하기 쉽다.
- Unity의 "세션 이어하기"와도 잘 맞는다.

### 2) 그 방식을 어디에 넣는 것이 가장 안전한가?

**가장 안전한 1차 삽입점은 `BasicMemoryAgent._to_messages()` 계열의 pre-LLM 단계다.**

보조적으로:

- summary 저장은 `chat_history_manager`의 metadata에 둔다.
- resume 시점 최적화는 `set_memory_from_history()`에서 보조 적용한다.
- Unity LLM-only 우선 작업이라면 `llm_server/chat_service.py`에서 먼저 얇게 적용해도 된다.

### 3) 어떤 정보는 반드시 유지해야 하는가?

- `persona_prompt`
- 현재 캐릭터/설정 식별 정보
- `conf_uid`
- `history_uid`
- Hume `resume_id`, `agent_type`
- 최신 대화의 직접 문맥
- 사용자 핵심 선호, 금지사항, 관계 설정, 약속, 진행 중인 목표

### 4) MVP에서는 어느 수준까지 구현하는 것이 적절한가?

**MVP는 "원본 history 보존 + model input recent window 경량화" 수준이 적절하다.**

구체적으로:

- `_to_messages()` 직전 helper를 도입한다.
- 최근 N턴만 LLM 입력에 포함한다.
- 원문 history JSON은 그대로 저장한다.
- summary 저장 필드는 metadata에 미리 예약만 해두거나, 아주 단순한 수동 summary부터 시작한다.

즉, MVP는 **A안으로 시작하되 B안으로 확장 가능한 형태**가 가장 현실적이다.

### 5) 차후 고도화는 어떤 순서로 가는 것이 좋은가?

1. `recent window only`를 먼저 도입한다.
2. `history metadata`에 summary 저장 구조를 추가한다.
3. `summary + recent window`로 확장한다.
4. 필요 시 사용자 핵심 정보만 별도 블록으로 추출한다.
5. 마지막 단계에서 토큰 수 기반 자동 compaction과 수동 관리 API를 붙인다.

---

## 권장 구현 로드맵

### Phase 1. 가장 얇은 MVP

- 대상:
  - `BasicMemoryAgent._to_messages()` 또는 `llm_server/chat_service.py`
- 내용:
  - recent N턴만 LLM 입력에 포함
  - raw history는 그대로 저장
  - 정책은 메시지 개수 기준
  - 단, proactive speak는 기존 `skip_memory` / `skip_history` 의미를 유지해야 한다.

### Phase 2. 장기 대화 품질 보강

- 대상:
  - `chat_history_manager.py`
  - `BasicMemoryAgent.set_memory_from_history()`
- 내용:
  - metadata에 summary 저장
  - summary + recent window hydrate
  - 그룹 대화용 `GroupConversationState.conversation_history`에도 동일 정책을 별도로 적용

### Phase 3. Unity 운영성 보강

- 대상:
  - LLM-only admin API 또는 별도 compaction 관리 API
- 내용:
  - 수동 compaction
  - summary invalidation
  - config/persona 변경 시 summary 재생성 정책

---

## 한 줄 결론

현재 코드 기준으로 가장 현실적인 방향은  
**"원본 history는 보존하고, 모델 입력만 `summary + recent window`로 가볍게 만들되, MVP는 `recent window only`부터 시작"** 하는 것이다.

---

## MVP Implementation Note

- MVP 구현 방향은 `recent window only`로 선택한다.
- 첫 적용 지점은 `BasicMemoryAgent._to_messages()` 직전의 pre-LLM message assembly다.
- 기본 recent window 값은 `16`개 메시지다.
- 원본 history JSON은 그대로 저장하고, 모델 입력만 줄인다.
