# vtuber_llm_sep_server

Unity 기반 앱에서 사용할 **LLM 전용 백엔드 서버**입니다.  
Open-LLM-VTuber에서 **ASR/TTS/Live2D/프론트**를 제거하고,
텍스트 기반 대화(API/WS)만 제공하도록 분리했습니다.

## 목적
- Unity 클라이언트에서 **LLM 대화 기능만** 빠르게 붙일 수 있도록 제공
- **가벼운 배포/운영**을 위한 최소 의존성 구성
- LLM 호출 + 히스토리 저장 + 프롬프트 구성에 집중

## 개발 실행 (Windows / PowerShell)

### 0) venv 환경에서 할 경우
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 1) 의존성 설치
```powershell
uv sync
```

최소 의존성만 설치하려면:
```powershell
uv pip install -r requirements-llm-server.txt
```

### 2) 서버 실행
```powershell
uv run uvicorn llm_server.app:app --app-dir src --host 127.0.0.1 --port 8000
```

외부 설정 파일을 지정하려면:
```powershell
$env:LLM_SERVER_CONFIG_PATH = "C:\path\to\conf.yaml"
uv run uvicorn llm_server.app:app --app-dir src --host 127.0.0.1 --port 8000
```

### 3) 테스트
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
```

```powershell
$body = @{
  conf_uid    = "mao_pro_001"
  history_uid = $null
  text        = "안녕"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/chat" -Method Post -ContentType "application/json" -Body $body
```

## EXE 빌드 (Windows)

### 1) PyInstaller 설치
```powershell
uv pip install pyinstaller
```

### 2) 빌드
```powershell
pyinstaller llm_server.spec
```

### 3) 실행
```powershell
.\dist\llm_server\llm_server.exe
```

옵션(환경변수):
- `LLM_SERVER_HOST` (기본: `127.0.0.1`)
- `LLM_SERVER_PORT` (기본: `8000`)
- `LLM_SERVER_LOG_LEVEL` (기본: `info`)
- `LLM_SERVER_ENABLE_MCP` (기본: `0`)
- `LLM_SERVER_CONFIG_PATH` (선택: 외부 `conf.yaml` 경로)

설정 파일 우선순위:
1. `LLM_SERVER_CONFIG_PATH`
2. exe/현재 실행 디렉토리의 `conf.yaml`
3. 번들/리포 기본 `conf.yaml`

권장 배포:
- Unity 프로젝트 또는 배포 폴더에 `llm_server.exe`와 외부 `conf.yaml`를 함께 둠
- Unity가 설정 변경 시 외부 `conf.yaml`를 수정
- MVP에서는 설정 변경 후 서버 재시작
- 일부 설정은 `/admin/reload-config`로 다음 요청부터 반영 가능

### 장기 대화 설정

현재 기본 `conf.yaml`은 장기 대화를 위해 `summary + recent window`를 사용합니다.

- 경로: `character_config.agent_config.agent_settings.basic_memory_agent.context_compaction`
- 현재 QA 기준값: `target=24`, `trigger=28`, `max=32`
- `recent_message_window: 32`로 최근 메시지는 넉넉하게 유지합니다.
- 이 값들은 `/admin/reload-config` 검증 후 **다음 요청부터 반영 가능**합니다.

## Unity 연동

- Unity 포함/프로세스 실행/설정 파일 관리 가이드: `UNITY_GUIDE.md`
- Unity용 API 기능 명세서: `UNITY_API_GUIDE.md`
- 참고용 외부 설정 예시: `conf.unity.example.yaml`

## 참고
- 설정 파일: `conf.yaml`
- 실행 가이드 상세: `README_LLM_SERVER.md`