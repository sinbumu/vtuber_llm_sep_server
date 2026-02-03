[Goal]
Open-LLM-VTuber 포크 저장소에서 Unity 클라이언트가 사용할 LLM 전용 Python 서버에
WebSocket 기반 스트리밍 채팅 엔드포인트를 추가한다.
ASR/TTS/OBS/Audio streaming 등은 Unity 측에서 처리하며, 서버는 텍스트 스트리밍만 담당한다.

[Migration Intent]
이 작업은 포크 저장소에서 먼저 안정화한 후,
향후 "새 저장소"를 생성하여 필요한 코드만 이관할 계획이다.
따라서 구현은 다음을 반드시 만족해야 한다:
- WebSocket 라우터/프로토콜, 대화 엔진(LLM 호출/메모리/히스토리) 로직을 분리한다.
- Unity 서버 전용 엔트리포인트/패키지 경계를 명확히 한다(추후 복사/이관 용이).
- 원본 프로젝트의 다른 기능(ASR/TTS/OBS/UI)과 의존을 최소화한다.

[Success Criteria]
1) WebSocket 엔드포인트를 제공한다: WS /v1/ws/chat
2) 클라이언트는 JSON 메시지를 보내고, 서버는 JSON 이벤트를 스트리밍으로 반환한다.
3) history_uid가 없으면 새로 생성하고, 있으면 해당 history를 로드하여 이어서 대화한다.
4) persona_prompt + tool_prompts 기반 system prompt를 그대로 사용한다.
5) 메시지 로그는 기존 chat_history_manager의 JSON 저장/로드를 재사용한다.
6) 스트리밍이 끝나면 assistant 전체 응답을 history에 저장한다.
7) 클라이언트가 연결을 끊어도 서버가 안전하게 정리한다.

[Protocol]
Client -> Server (JSON):
{
  "conf_uid": "string",
  "history_uid": "string | null",
  "text": "string",
  "metadata": { ... }  // optional, reserved for future
}

Server -> Client (JSON events):
1) session:
{
  "type": "session",
  "history_uid": "string"
}

2) delta (토큰/조각 스트리밍):
{
  "type": "delta",
  "text": "string"
}

3) done (정상 종료):
{
  "type": "done",
  "text": "full_response_text"
}

4) error (오류):
{
  "type": "error",
  "code": "string",
  "message": "string"
}

[Implementation Requirements]
A) FastAPI WebSocket을 사용한다.
   - 예: from fastapi import WebSocket
B) 기존 StatelessLLMInterface.chat_completion()이 AsyncIterator를 반환한다면,
   이를 그대로 순회하며 delta 이벤트를 전송하라.
   - AsyncIterator가 없다면, one-shot으로 호출 후 delta를 문장/단어 단위로 쪼개 전송해도 된다(최소 동작 우선).
C) 대화 엔진 로직(프롬프트 구성 + messages 생성 + LLM 호출 + history 저장)을
   "서비스 함수"로 분리하라. 예:
   - engine/chat_service.py:
       async def run_chat_stream(conf_uid, history_uid, text) -> (history_uid, async_iterator_of_text_chunks, final_text)
   WebSocket 라우터는 이 함수를 호출해 이벤트만 송신해야 한다.
   => 향후 새 저장소 이관 시 engine/와 app/만 복사하면 되도록 구조를 만든다.
D) history 처리:
   - history_uid 없으면 create_new_history(conf_uid) 호출 후 session 이벤트로 즉시 내려준다.
   - history_uid 있으면 get_history(conf_uid, history_uid)로 로드 후 agent.set_memory_from_history로 주입한다.
   - user 메시지는 즉시 store_message로 저장한다.
   - assistant 메시지는 스트리밍 완료 후 full_text로 1회 store_mes
