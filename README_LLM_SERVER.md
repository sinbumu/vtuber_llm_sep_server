# README_LLM_SERVER.md — LLM-only 서버 실행 가이드

이 문서는 **LLM-only 서버(ASR/TTS/Live2D 제외)** 실행 방법을 정리합니다.

---

## 1) 설치

```powershell
uv sync
```

최소 의존성만 설치하고 싶다면:

```powershell
uv pip install -r requirements-llm-server.txt
```

---

## 2) 실행

```powershell
uv run uvicorn llm_server.app:app --host 127.0.0.1 --port 8000
```

---

## 3) 건강 체크

```powershell
curl http://127.0.0.1:8000/health
```

---

## 4) /v1/chat

```powershell
curl -X POST http://127.0.0.1:8000/v1/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"conf_uid\":\"mao_pro_001\",\"history_uid\":null,\"text\":\"안녕\"}"
```

응답:
```json
{"history_uid":"...","text":"..."}
```

---

## 5) Persona 적용 테스트 (Plan3 이후)

```powershell
curl -X POST http://127.0.0.1:8000/v1/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"conf_uid\":\"mao_pro_001\",\"history_uid\":null,\"text\":\"너 누구야?\"}"
```

의도: `conf.yaml`의 `persona_prompt`가 반영된 응답이 나오는지 확인

---

## 6) WebSocket 스트리밍 (Plan4)

요청(JSON):
```json
{
  "conf_uid": "mao_pro_001",
  "history_uid": null,
  "text": "안녕"
}
```

응답(JSON events):
```json
{ "type": "session", "history_uid": "..." }
{ "type": "delta", "text": "..." }
{ "type": "done", "text": "full response" }
```

에러:
```json
{ "type": "error", "code": "history_not_found" }
{ "type": "error", "code": "llm_timeout" }
{ "type": "error", "code": "llm_error" }
```

---

## 참고

- LLM-only 서버는 **ASR/TTS/Live2D/VAD/OBS를 초기화하지 않습니다.**
- `mem0_agent`는 미구현 상태이므로 **기본 비활성화**됩니다.
- /v1/ws/chat 스트리밍은 LLM 응답 조각을 delta로 전송합니다.
