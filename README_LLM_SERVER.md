# README_LLM_SERVER.md — LLM-only 서버 실행 가이드

이 문서는 **LLM-only 서버(ASR/TTS/Live2D 제외)** 실행 방법을 정리합니다.

---

## 0) venv 환경에서 할거라면.

```powershell
python -m venv .venv   
.venv\Scripts\activate
```

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
uv run uvicorn llm_server.app:app --app-dir src --host 127.0.0.1 --port 8000
```

만약 `prompts` 모듈 import 오류가 난다면, 아래처럼 `PYTHONPATH`를 추가해 실행하세요:

```powershell
$env:PYTHONPATH = "$PWD"
uv run uvicorn llm_server.app:app --app-dir src --host 127.0.0.1 --port 8000
```

MCP 기능을 쓰고 싶다면:

```powershell
$env:LLM_SERVER_ENABLE_MCP = "1"
uv run uvicorn llm_server.app:app --app-dir src --host 127.0.0.1 --port 8000
```

조건:
- `mcp_servers.json` 파일이 저장소 루트에 있어야 합니다.
- MCP 서버 런타임(`npx`, `uvx`, `node`) 및 관련 파이썬 의존성이 설치되어 있어야 합니다.

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
$body = @{
  conf_uid    = "mao_pro_001"
  history_uid = $null
  text        = "안녕"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/chat" -Method Post -ContentType "application/json" -Body $body
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
