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

## 참고
- 설정 파일: `conf.yaml`
- 실행 가이드 상세: `README_LLM_SERVER.md`
## 신규 서버 개발용 포크 프젝

#### https://letspl.me/project/2560/shortcut

위 프로젝트 팀 리딩을 진행중이고, 관련해서 오픈소스를 참고해서 서버 개발중.