# sep_MIGRATION_CHECKLIST.md — 이관 전 체크리스트 & 정리/삭제 대상

이 문서는 **백앤드 LLM 서버만 별도 저장소로 이관하기 전** 확인해야 할 항목과
현재 포크 레포에서 **정리/삭제 후보**를 정리합니다.

---

## 1) 이관 전 체크리스트 (필수)

### 실행/기능
- `/health` 200 OK 확인
- `/v1/chat` 정상 응답 확인 (history_uid 생성/저장)
- `/v1/ws/chat` 정상 스트리밍 확인 (session → delta → done)
- `history_uid` 없는/있는 케이스 모두 테스트
- Gemini/Ollama 중 최소 1개 LLM 정상 호출 확인

### 설정/환경
- `conf.yaml`의 **LLM-only 설정** 정상 적용 확인
- `base_url`/`model`/`llm_api_key`가 실제로 적용되는지 확인
- `BASE_DIR`/`PYTHONPATH` 문제 없이 실행되는지 확인
- MCP 관련 프롬프트 제거 상태 확인

### 로그/에러
- 429/401 등 오류 시 **502 또는 WS error**로 처리되는지 확인
- tool_prompts 누락 시 **서버가 죽지 않고 로그만 남기는지** 확인

### 문서/배포
- `README_LLM_SERVER.md` 최신화 (실행/테스트/WS 포함)
- `requirements-llm-server.txt`로 **최소 설치 테스트** 완료

---

## 2) 정리/삭제 대상 리스트 (LLM-only 기준)

아래는 LLM-only 서버 분리 시 **새 레포에는 필요 없는** 요소들입니다.

### 프론트/UI/데스크톱 관련
- `frontend/` (웹 프론트 빌드)
- `web_tool/`
- `assets/`
- `docs/` 중 UI 설계 문서
- 데스크톱 펫 모드 관련 문서/스크립트

### 음성/멀티미디어
- `src/open_llm_vtuber/asr/`
- `src/open_llm_vtuber/tts/`
- `src/open_llm_vtuber/vad/`
- `src/open_llm_vtuber/utils/stream_audio.py`
- `src/open_llm_vtuber/conversations/` (오디오/Live2D 경로 의존)

### Live2D/캐릭터 리소스
- `live2d-models/`
- `model_dict.json`
- `avatars/`, `backgrounds/`

### MCP/툴 관련 (LLM-only에서는 비활성)
- `src/open_llm_vtuber/mcpp/`
- `mcp_servers.json`

### OBS/라이브 관련
- `src/open_llm_vtuber/live/`

### 기타 문서/설정
- `LOCAL_GUIDE*.md` (로컬 풀스택용)
- `OLLAMA_GUIDE.md` (선택: LLM-only 가이드에 병합 가능)
- `config_templates/conf.ZH.default.yaml` (필요시 유지)

---

## 3) 이관 대상 (새 레포에 포함)

### 코드
- `src/llm_server/` 전체
- `src/open_llm_vtuber/agent/` (LLM/BasicMemoryAgent)
- `src/open_llm_vtuber/chat_history_manager.py`
- `src/open_llm_vtuber/config_manager/` (YAML 로딩/모델)
- `prompts/utils/` (tool_prompts가 사용하는 파일)

### 설정/문서
- `conf.yaml` (LLM-only 기준)
- `requirements-llm-server.txt`
- `README_LLM_SERVER.md`
- `LICENSE`

---

## 4) 이관 후 권장 정리

- `conf.yaml`에서 **필요 없는 키 제거** (ASR/TTS/VAD/Live2D)
- `config_manager`를 LLM-only로 축소 (선택)
- `README`를 새 레포 기준으로 재작성

---

필요하면 이 체크리스트를 **실행 단계별 QA 스크립트**로 변환해 드릴게요.
