이제 /v1/chat stub을 실제 LLM 호출로 교체하라.

요구사항:
1) ServiceContext.construct_system_prompt()를 사용해 system prompt를 구성하고,
2) BasicMemoryAgent를 사용해 messages를 구성한다.
   - history_uid가 있으면 get_history(conf_uid, history_uid) -> agent.set_memory_from_history(...)로 로드
   - 이번 user input을 포함하여 agent._to_messages(...) 또는 equivalent 로 messages를 생성
3) agent/stateless_llm/* 인터페이스를 통해 one-shot 응답을 얻는다.
   - 스트리밍 구현이 어렵다면 우선 one-shot으로 전체 텍스트를 모아서 반환해도 된다.
4) user/assistant 메시지를 chat_history_manager.store_message로 저장한다.
5) persona 적용 검증용 간단 테스트를 README에 추가한다:
   - "너 누구야?" 질문 시 persona 기반 응답이 나오는지 확인하는 예시
6) ASR/TTS/OBS 관련 import 및 side-effect가 새 서버에서 발생하지 않게 정리한다.
7) 에러 처리:
   - history_uid 파일 없으면 404
   - LLM 호출 실패 시 502 + 에러 메시지 최소화

추가(선택):
- /v1/chat/stream (SSE) 구현 가능하면 구현하되, Unity는 일단 one-shot로도 붙을 수 있게 유지하라.
