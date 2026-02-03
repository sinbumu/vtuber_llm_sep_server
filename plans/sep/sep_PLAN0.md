[Goal]
Open-LLM-VTuber에서 Unity 클라이언트가 사용할 "LLM 전용 Python 서버"를 분리/추출한다.
ASR/TTS/OBS/Overlay/Audio streaming 등 클라이언트(유니티) I/O 요소는 모두 제외한다.

[Success Criteria]
1) FastAPI 기반 서버가 단독 실행된다.
2) POST /v1/chat (one-shot) 를 제공한다: {conf_uid, history_uid(optional), text} -> {history_uid, text}
3) (선택) SSE 또는 WebSocket로 텍스트 스트리밍 엔드포인트를 제공한다.
4) persona_prompt + tool_prompts 기반 system prompt를 그대로 사용한다.
5) chat_history(JSON) 저장/로드는 기존 chat_history_manager를 재사용한다.
6) 서버는 "LLM 호출 + 메시지 구성 + 히스토리"만 담당한다. ASR/TTS/오디오/카메라/OBS 관련 코드는 모두 제거 또는 비활성화한다.
7) 최소 의존성으로 requirements를 정리한다(불필요 패키지 제거).
8) README에 실행 방법과 curl 테스트를 포함한다.

[Constraints]
- 기존 코어 로직(service_context.py, basic_memory_agent.py, stateless_llm, chat_history_manager.py)은 가능하면 "수정 최소 + 재사용"한다.
- 큰 리팩토링보다 "새 엔트리포인트 추가 → 코어 import 재사용 → 슬림화" 방식(strangler)으로 진행한다.
