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

외부 설정 파일 경로를 직접 지정하려면:

```powershell
$env:LLM_SERVER_CONFIG_PATH = "C:\path\to\conf.yaml"
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

이미지 첨부도 가능합니다:
```json
{
  "conf_uid": "mao_pro_001",
  "history_uid": null,
  "text": "이 화면 보고 설명해줘",
  "images": [
    {
      "source": "screen",
      "mime_type": "image/jpeg",
      "data": "data:image/jpeg;base64,..."
    }
  ]
}
```

메모:
- `images`는 optional입니다.
- 현재 `/v1/chat`이 기본 권장 API이며 이미지 입력도 이 경로를 사용합니다.
- `/v1/ws/chat`은 레거시 스트리밍 경로로 유지합니다.
- `data`는 `data:image/...;base64,...` 형태의 data URL이어야 합니다.
- history에는 원본 이미지가 아니라 attachment 메타만 저장됩니다.
- vision 미지원 provider/model이면 요청이 실패할 수 있습니다.

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

## 7) EXE 빌드 (PyInstaller)

> Unity 앱에서 **자식 프로세스**로 실행하기 위한 Windows exe 빌드용.

### 7-1) PyInstaller 설치
```powershell
uv pip install pyinstaller
```

### 7-2) 빌드 실행
```powershell
pyinstaller llm_server.spec
```

결과:
- `dist/llm_server/llm_server.exe` 생성
- `conf.yaml`, `prompts/`, `mcp_servers.json`이 함께 포함됨

### 7-3) 실행
```powershell
.\dist\llm_server\llm_server.exe
```

옵션(환경변수):
- `LLM_SERVER_HOST` (기본: `127.0.0.1`)
- `LLM_SERVER_PORT` (기본: `8000`)
- `LLM_SERVER_LOG_LEVEL` (기본: `info`)
- `LLM_SERVER_ENABLE_MCP` (기본: `0`)
- `LLM_SERVER_CONFIG_PATH` (선택: 외부 `conf.yaml` 경로)

---

## 8) Context Compaction 설정

`basic_memory_agent` 아래에 다음 설정을 둘 수 있습니다:

```yaml
character_config:
  agent_config:
    agent_settings:
      basic_memory_agent:
        recent_message_window: 32
        context_compaction:
          enabled: true
          mode: "summary_recent_window"
          target_message_count: 24
          trigger_message_count: 28
          max_message_count: 32
          min_messages_to_compact: 4
          summarizer: "same_llm"
          summarizer_model: null
          summarizer_timeout_sec: 15
```

설명:
- `recent_message_window`: recent-window 경로에서 유지할 최근 메시지 수
- `context_compaction.enabled`: summary compaction on/off
- `mode`: `recent_window_only` 또는 `summary_recent_window`
- `target/trigger/max`: summary 후 목표치, 시작 기준, live buffer 상한
- summary는 응답 후 백그라운드에서 생성되며, history metadata에 저장됩니다.

---

## 9) 관리 API (초안)

### 8-1) 현재 설정 조회
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/admin/current-config" -Method Get
```

설명:
- 현재 적용 기준의 설정 요약을 반환합니다.
- 민감값(`api_key` 등)은 마스킹됩니다.
- 설정 파일 우선순위:
  1. `LLM_SERVER_CONFIG_PATH`
  2. exe/현재 실행 디렉토리의 `conf.yaml`
  3. 번들/리포 기본 `conf.yaml`

### 8-2) 설정 재로드 검증
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/admin/reload-config" -Method Post
```

설명:
- `conf.yaml`과 prompt 파일을 다시 읽어 검증합니다.
- 현재 구조에서는 **적용 가능한 항목은 다음 요청부터 반영**됩니다.
- `host`, `port`, `LLM_SERVER_ENABLE_MCP` 같은 항목은 재시작 필요로 반환됩니다.

---

## 참고

- LLM-only 서버는 **ASR/TTS/Live2D/VAD/OBS를 초기화하지 않습니다.**
- `mem0_agent`는 미구현 상태이므로 **기본 비활성화**됩니다.
- /v1/ws/chat 스트리밍은 LLM 응답 조각을 delta로 전송합니다.
- Unity 이식 가이드는 `UNITY_GUIDE.md`, Unity API 명세는 `UNITY_API_GUIDE.md`를 참고하세요.
