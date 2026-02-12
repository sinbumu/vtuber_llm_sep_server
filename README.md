# vtuber_llm_sep_server

Unity 기반 앱에서 사용할 **LLM 전용 백엔드 서버**입니다.  
Open-LLM-VTuber에서 **ASR/TTS/Live2D/프론트**를 제거하고,
텍스트 기반 대화(API/WS)만 제공하도록 분리했습니다.

## 목적
- Unity 클라이언트에서 **LLM 대화 기능만** 빠르게 붙일 수 있도록 제공
- **가벼운 배포/운영**을 위한 최소 의존성 구성
- LLM 호출 + 히스토리 저장 + 프롬프트 구성에 집중

## 개발 실행 (Windows / PowerShell)

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

## 참고
- 설정 파일: `conf.yaml`
- 실행 가이드 상세: `README_LLM_SERVER.md`