# CONFIG_INVENTORY.md — 설정/소스 인벤토리

이 문서는 **백엔드 서버 설정이 어디서 들어오는지**와
**주요 키/파일**을 정리합니다.

소스 기준: `conf.yaml`, `config_templates/*.yaml`, `src/open_llm_vtuber/config_manager/*`,
`model_dict.json`, `mcp_servers.json`.

---

## 1) 설정 입력 소스 (우선순위 개념)

1. **`conf.yaml`**  
   - 서버 실행 시 가장 먼저 로드되는 메인 설정
   - `config_templates/conf.default.yaml`에서 복사해 생성

2. **`characters/*.yaml` (대체 설정)**  
   - `system_config.config_alts_dir` 기준 폴더
   - UI에서 `switch-config`로 교체 가능

3. **JSON 설정 파일**  
   - `model_dict.json` : Live2D 모델/감정 매핑
   - `mcp_servers.json` : MCP 서버 레지스트리

4. **환경 변수 (YAML 내 치환)**  
   - `${ENV_VAR}` 형식으로 치환 가능
   - `config_manager/utils.py`에서 처리

5. **런타임 디렉토리/파일**  
   - `chat_history/<conf_uid>/*.json` : 대화 기록
   - `backgrounds/`, `avatars/`, `live2d-models/` : UI 에셋
   - `cache/` : TTS 결과 캐시

---

## 2) 핵심 설정 키 (요약)

### A) `system_config`
- `conf_version`
- `host`
- `port`
- `config_alts_dir`
- `tool_prompts` (프롬프트 키 → `prompts/utils/*.txt` 연결)
- `enable_proxy`

### B) `character_config`
- `conf_name`, `conf_uid`
- `live2d_model_name`
- `character_name`, `human_name`
- `avatar`
- `persona_prompt`

#### `character_config.agent_config`
- `conversation_agent_choice`
- `agent_settings.*`  
  - `basic_memory_agent.llm_provider` 등
  - `use_mcpp`, `mcp_enabled_servers`
- `llm_configs.*`  
  - `ollama_llm`, `openai_llm`, `claude_llm`, `openai_compatible_llm` 등

#### `character_config.asr_config`
- `asr_model`
- 엔진별 상세 키:  
  - `faster_whisper.*`, `whisper_cpp.*`, `whisper.*`, `fun_asr.*`,
  - `azure_asr.*`, `groq_whisper_asr.*`, `sherpa_onnx_asr.*`

#### `character_config.tts_config`
- `tts_model`
- 엔진별 상세 키:  
  - `edge_tts.*`, `azure_tts.*`, `coqui_tts.*`, `melo_tts.*`,
  - `bark_tts.*`, `cosyvoice*.*`, `gpt_sovits.*`, `fish_audio.*`, `piper_tts.*` 등

#### `character_config.vad_config`
- `vad_model`
- `silero_vad.*`

#### `character_config.tts_preprocessor_config`
- `remove_special_char`
- `ignore_brackets`, `ignore_parentheses`, `ignore_asterisks`, `ignore_angle_brackets`
- `translator_config.*`

### C) `live_config`
- `bilibili_live.room_ids`
- `bilibili_live.sessdata`

---

## 3) JSON 설정 파일

### `model_dict.json`
- Live2D 모델 메타 정보
- 주요 키:
  - `name`, `url`, `kScale`, `initialXshift`, `initialYshift`, `kXOffset`
  - `emotionMap` (감정 → 인덱스)
  - `tapMotions`

### `mcp_servers.json`
- MCP 서버 목록 및 실행 커맨드
- 주요 키:
  - `mcp_servers.<server_id>.command`
  - `mcp_servers.<server_id>.args`
  - (옵션) `env`, `cwd`

---

## 4) 환경 변수 사용 (직접/간접)

### YAML 치환
- `${ENV_VAR}` 형태로 `conf.yaml`에서 직접 사용 가능

### 코드에서 직접 참조하는 ENV
- `HF_HOME`, `MODELSCOPE_CACHE` (런타임에서 모델 캐시 경로 지정)
- `HF_ENDPOINT` (미러 설정, `run_server.py --hf_mirror`)
- `AZURE_API_Key`, `AZURE_REGION` (Azure ASR)
- Azure TTS는 `conf.yaml`의 `azure_tts` 설정을 사용

---

## 5) 프롬프트/리소스 파일

### 프롬프트 텍스트
- 위치: `prompts/utils/*.txt`
- `system_config.tool_prompts` 값과 연결됨

### UI 리소스
- `backgrounds/`, `avatars/`, `live2d-models/`
- `/live2d-models/info` API로 목록 조회 가능

