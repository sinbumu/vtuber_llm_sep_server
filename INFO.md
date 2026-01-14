### 한 줄 요약
- **Open-LLM-VTuber는 FastAPI(WebSocket) 기반의 음성 대화 파이프라인(마이크/VAD→ASR→LLM→TTS→프론트 재생)과 Live2D “감정 태그([joy] 등)” 기반 표정 매핑을 제공하며, 코드 라이선스는 MIT이지만 Live2D 샘플 모델 자산은 별도 라이선스라 상용 사용 시 분리가 핵심 리스크입니다.**

---

### 0) 분석 대상/기준
- **현재 워크스페이스(fork) HEAD**: `85ba613c5c1c3daad11c963872441ebe8a4cdcb3` (`main`)
- **업스트림 태그(v1.2.0에 해당)**: 태그명이 `v1.2.0`이 아니라 **`1.2.0`** 로 존재
  - **태그 `1.2.0` 커밋 SHA**: `4826a10c2993f86260e030ae355a9f92f90c4a47`
- **주의(환경 제약)**: 이 환경은 GitHub fetch 시 CA 경로 문제로 TLS 검증이 실패하여, 태그 fetch를 일회성으로 `GIT_SSL_NO_VERIFY=true`로 우회함. (정상 환경에서는 `git fetch --tags upstream` 권장)

---

### 1) 라이선스 결론(안전 기준점)
- **코드 라이선스**: **MIT**
  - 근거: `LICENSE` (현재 브랜치), `git show 1.2.0:LICENSE` (태그 `1.2.0`) 모두 MIT
- **중요 예외(상용 리스크)**: **Live2D 샘플 모델/자산은 MIT가 아님**
  - 근거: `LICENSE` 하단 예외 문구 + `LICENSE-Live2D.md` + `README.md` / `README.KR.md`의 “Third-Party Licenses / Live2D Sample Models Notice”
  - 의미: 상용 제품(특히 중견/대기업)에서 샘플 모델 사용 시 **추가 라이선스 요구/제한** 가능 → 실무적으로는 **샘플 모델을 제거/대체(자체 모델 또는 상용 라이선스 확보)** 하는 쪽이 안전
- **“Open-LLM-VTuber License 1.0” 여부**:
  - 이 코드베이스(현재 워크스페이스 + upstream/main + 태그 `1.2.0`)에서 해당 문구/파일을 발견하지 못함 → **현 시점 코드 기준으로는 MIT 유지로 판단**

---

### 2) 전체 구조 맵(핵심 컴포넌트 위치)
- **서버 엔트리포인트**
  - `run_server.py`: 설정 로드/검증 → `WebSocketServer` 생성/초기화 → Uvicorn 실행
  - `src/open_llm_vtuber/server.py`: FastAPI 앱 생성, 라우트 등록, 정적 파일 mount
- **라우팅(WebSocket/프록시/웹툴)**
  - `src/open_llm_vtuber/routes.py`: `/client-ws` (메인), `/proxy-ws` (옵션), 웹툴/정적 관련 라우트
  - `src/open_llm_vtuber/websocket_handler.py`: 클라이언트 메시지 라우팅/상태 관리/오디오 수신/대화 트리거/그룹 브로드캐스트
- **설정/검증(Pydantic)**
  - `src/open_llm_vtuber/config_manager/main.py` 및 하위 모듈들
  - 템플릿: `config_templates/conf.default.yaml`, `config_templates/conf.ZH.default.yaml`
- **대화 파이프라인**
  - 트리거/인터럽트: `src/open_llm_vtuber/conversations/conversation_handler.py`
  - 단일 대화: `src/open_llm_vtuber/conversations/single_conversation.py`
  - 그룹 대화: `src/open_llm_vtuber/conversations/group_conversation.py`
  - 출력 처리/전송: `src/open_llm_vtuber/conversations/conversation_utils.py`, `src/open_llm_vtuber/conversations/tts_manager.py`
- **LLM/에이전트**
  - 에이전트 생성: `src/open_llm_vtuber/agent/agent_factory.py`
  - 기본 에이전트: `src/open_llm_vtuber/agent/agents/basic_memory_agent.py`
  - LLM 백엔드: `src/open_llm_vtuber/agent/stateless_llm/*`
- **ASR / TTS / VAD**
  - ASR: `src/open_llm_vtuber/asr/asr_factory.py`
  - TTS: `src/open_llm_vtuber/tts/tts_factory.py`
  - VAD: `src/open_llm_vtuber/vad/*` (예: Silero 기반)
- **Live2D 정보/감정 매핑**
  - 모델 메타/감정맵: `model_dict.json`
  - 매핑/태그 추출: `src/open_llm_vtuber/live2d_model.py`
  - 프롬프트 삽입: `prompts/utils/live2d_expression_prompt.txt`

---

### 3) LLM 파이프라인(입력→처리→출력)
- **입력 구성(프롬프트)**
  - `ServiceContext.construct_system_prompt()`가 **persona_prompt + tool_prompts**를 결합
  - `tool_prompts` 예: Live2D 표정 태그 안내(`live2d_expression_prompt`), MCP 프롬프트 등 (`config_templates/conf.default.yaml` 참고)
- **LLM 호출**
  - `BasicMemoryAgent`가 선택된 LLM provider를 통해 streaming 응답을 받음 (OpenAI-compatible, Ollama, Claude 등)
- **출력(스트리밍 토큰) → 문장 단위 변환**
  - `src/open_llm_vtuber/agent/transformers.py`
    - `sentence_divider(...)`: 토큰 스트림을 문장 단위로 쪼갬
    - `actions_extractor(live2d_model)`: 문장 텍스트에서 감정 태그를 추출하여 `Actions.expressions`에 저장
    - `tts_filter(...)`: TTS에 부적합한 문자를 제거(설정에 따라 `[]` 등을 무시 가능)
- **출력 포맷 결론**
  - “JSON 스키마 강제”보다는, **텍스트 내 태그([joy] 등) 방식**으로 감정/표정 힌트를 전달하는 구조가 기본
  - MCP 도구 호출은 별도의 툴 콜 JSON/상태 이벤트로 스트리밍 중간에 섞여 전달될 수 있음

---

### 4) STT/TTS 파이프라인 + 인터럽트
- **마이크 입력**
  - 클라이언트가 `/client-ws`로 오디오를 전송
  - `websocket_handler.py`에서 `audio` 또는 `raw_audio` 형태로 처리
- **VAD**
  - `WebSocketHandler._handle_raw_audio_data()`에서 VAD가 speech 구간을 검출
  - VAD가 `<|PAUSE|>`를 내보내면 프론트에 **interrupt control** 송신
- **ASR(음성→텍스트)**
  - `conversation_utils.process_user_input()`에서 numpy 오디오를 ASR 엔진으로 전사
  - 엔진 선택: `ASRFactory`가 `sherpa_onnx_asr`, `faster_whisper`, `whisper_cpp`, `azure_asr` 등으로 분기
- **TTS(텍스트→음성) + 순서 보장**
  - `TTSTaskManager`가 문장 단위 TTS 생성 작업을 병렬로 돌리되, `_payload_queue`로 **전송 순서를 보장**
  - 오디오 전송 포맷은 `prepare_audio_payload()`가 생성 (base64 wav + volumes + actions + display_text)
- **인터럽트(말 끊기)**
  - `handle_individual_interrupt()` / `handle_group_interrupt()`가 진행 중 task를 cancel하고, 에이전트 메모리에 “[Interrupted by user]”를 기록

---

### 5) Live2D/캐릭터 반응 연결 방식(가장 중요)
- **감정/표정 태그의 “정의”**
  - `model_dict.json`의 각 모델 항목에 `emotionMap`이 존재 (예: `neutral:0`, `joy:3` 등)
- **LLM에게 태그 사용을 유도하는 프롬프트**
  - `prompts/utils/live2d_expression_prompt.txt`가 system prompt 뒤에 붙고,
  - `ServiceContext.construct_system_prompt()`에서 `[<insert_emomap_keys>]`가 모델의 지원 태그 목록으로 치환됨
- **태그 → Live2D 표현으로 변환**
  - `live2d_model.py`의 `extract_emotion()`이 텍스트에서 `[joy]` 같은 태그를 찾아 **정수 인덱스 리스트**로 변환
  - `agent/transformers.py`의 `actions_extractor()`가 이를 `Actions.expressions`에 넣음
  - 최종적으로 `prepare_audio_payload()`의 `actions` 필드로 프론트에 전달됨
- **실무 관찰 포인트**
  - “태그를 화면에 그대로 노출”할지 여부는 TTS/표시 전처리 설정에 따라 달라질 수 있음(태그는 원문 텍스트에 섞여 들어오기 때문)

---

### 6) 우리(Unity 데스크탑 AI 비서) 관점 “즉시 재사용/참고 Top5”
> Unity 레포(Open-LLM-VTuber-Unity)는 이 워크스페이스에 없어서 Unity C# 코드는 직접 추출하지 못했지만, Unity↔백엔드 연동/설계에 바로 가져갈 수 있는 “백엔드 핵심 구간” Top5입니다.

- **Top1 — WebSocket 프로토콜/트리거/그룹 브로드캐스트**
  - 파일: `src/open_llm_vtuber/websocket_handler.py`, `src/open_llm_vtuber/routes.py`
  - 이유: Unity 쪽에서 `/client-ws`로 어떤 메시지를 보내고 어떤 타입의 응답(control/audio/full-text)을 받는지 “프로토콜 기준”이 됨
- **Top2 — 오디오 payload 포맷(볼륨/립싱크 힌트 포함)**
  - 파일: `src/open_llm_vtuber/utils/stream_audio.py`
  - 이유: `audio(base64 wav) + volumes + slice_length + actions`는 Unity에서 재생/립싱크/표정 적용을 붙이기 좋은 단위
- **Top3 — “감정 태그([joy]) → Actions.expressions” 변환 파이프라인**
  - 파일: `src/open_llm_vtuber/agent/transformers.py`, `src/open_llm_vtuber/live2d_model.py`, `model_dict.json`
  - 이유: LLM 출력에 구조화 JSON을 강제하지 않고도 Live2D 반응을 안정적으로 뽑아내는 패턴(간단하고 이식 용이)
- **Top4 — TTS 작업 병렬화 + 전송 순서 보장(레이턴시/UX에 직접 영향)**
  - 파일: `src/open_llm_vtuber/conversations/tts_manager.py`
  - 이유: “먼저 생성된 오디오부터 재생” 같은 UX를 유지하면서도 생성은 병렬로 돌리는 구조를 Unity에서도 그대로 재현 가능
- **Top5 — ASR/TTS/VAD/LLM 팩토리 분기(엔진 스왑 구조)**
  - 파일: `src/open_llm_vtuber/asr/asr_factory.py`, `src/open_llm_vtuber/tts/tts_factory.py`, `src/open_llm_vtuber/service_context.py`
  - 이유: Unity MVP에서 “엔진 교체 가능” 구조로 가려면, 이 레이어 분리가 그대로 참고됨

---

### 7) 참고만 할 요소 Top5(우리 상용 MVP 관점 리스크/비용)
- **Live2D 샘플 모델/자산**: 상용/재배포에서 리스크가 크므로 기본 포함 금지(대체 필요)
- **프론트엔드(React) 서브모듈**: Unity UI로 갈 경우 그대로 쓰기 어렵고, 프로토콜만 참고하는 편이 효율적
- **클라우드 기반 LLM/ASR/TTS 설정**: 오프라인/개인정보 요구사항이 있으면 로컬 엔진(Ollama, sherpa-onnx 등) 중심으로 재구성 필요
- **MCP 도구 연동**: 제품 범위에 따라 공격 표면/권한 설계가 필요(실무에서는 화이트리스트/샌드박스가 필수)
- **다중 플랫폼 오디오 권한/장치 처리**: Unity에서는 OS별 마이크/오디오 디바이스 차이가 크므로 별도 설계/테스트 필요

---

### 8) 리스크(배포/의존성/라이선스)
- **라이선스 리스크(최우선)**: Live2D 샘플 모델은 MIT 범위 밖 → 상용은 “모델 제거/대체” 전제로 설계 권장
- **배포 리스크**: Unity 앱 + 로컬 백엔드(Python) 2프로세스 구성 시 설치/실행/권한/업데이트 복잡도 상승
- **저지연 목표(500ms 이하)**: STT/LLM/TTS 조합에 따라 달성 난이도 크게 변동. “스트리밍 + 문장 분할 + 선제 TTS” 구조는 유리

---

### 9) 우리 적용안 결론(A/B/C)
- **추천: B 또는 A(상황별)**
  - **B(추천, MVP 빠름)**: Unity에서 UI/캐릭터/오디오를 자체 구현하고, 이 레포에서는 **프로토콜/파이프라인 패턴(Top5)** 을 참고 + 백엔드는 경량화
  - **A(재사용 극대화)**: 이 레포(태그 `1.2.0` 기준)를 **로컬 백엔드 서비스**로 붙이고 Unity는 클라이언트 역할만 수행
  - **C(참고만)**: Live2D/배포/보안 요구로 인해 복잡도가 과도하면 아이디어만 차용

---

### 10) 다음 액션(PoC)
- **(필수) Unity 레포 라이선스/코드 추출**
  - Unity 레포의 `LICENSE`(MIT 여부) + 네트워크(WS/HTTP) + Live2D 제어 스크립트 Top5를 동일 포맷으로 정리
- **(필수) Live2D 샘플 모델 제거 빌드**
  - 상용 전제라면 샘플 모델 제거/대체한 “클린 패키징” 절차를 먼저 정의
- **(선택) Unity↔백엔드 프로토콜 고정**
  - `/client-ws` 메시지 타입/페이로드 스키마를 문서화(버전 관리)하고, Unity에서 동일 스키마로 구현