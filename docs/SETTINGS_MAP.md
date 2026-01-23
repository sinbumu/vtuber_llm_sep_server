# SETTINGS_MAP.md — 설정/옵션/토글 키 맵

이 문서는 **사용자 UI 설계**를 위한 설정 맵입니다.  
기준 파일: `conf.yaml`, `config_templates/conf.default.yaml`

---

## 1) 설정 파일 위치

- 기본 설정: `conf.yaml`
- 기본 템플릿: `config_templates/conf.default.yaml`
- 캐릭터 프리셋: `characters/*.yaml`
- Live2D 감정 맵: `model_dict.json`
- MCP 서버 목록: `mcp_servers.json`

---

## 2) 설정 항목 테이블(핵심)

| 사람용 항목명 | 내부 키 | 타입 | 기본값(추정) | UI 추천 |
|---|---|---|---|---|
| 서버 호스트 | `system_config.host` | 텍스트 | `localhost` | 입력창 |
| 서버 포트 | `system_config.port` | 숫자 | `12393` | 숫자 입력 |
| 설정 프리셋 폴더 | `system_config.config_alts_dir` | 텍스트 | `characters` | 입력창 |
| Live2D 표현 프롬프트 | `system_config.tool_prompts.live2d_expression_prompt` | 선택 | `live2d_expression_prompt` | 드롭다운 |
| 그룹 대화 프롬프트 | `system_config.tool_prompts.group_conversation_prompt` | 선택 | `group_conversation_prompt` | 드롭다운 |
| MCP 프롬프트 | `system_config.tool_prompts.mcp_prompt` | 선택 | `mcp_prompt` | 드롭다운 |
| 선제 발화 프롬프트 | `system_config.tool_prompts.proactive_speak_prompt` | 선택 | `proactive_speak_prompt` | 드롭다운 |
| 캐릭터 설정 이름 | `character_config.conf_name` | 텍스트 | `mao_pro` | 입력창 |
| 캐릭터 UID | `character_config.conf_uid` | 텍스트 | `mao_pro_001` | 입력창 |
| Live2D 모델 이름 | `character_config.live2d_model_name` | 선택 | `mao_pro` | 드롭다운 |
| 캐릭터 표시명 | `character_config.character_name` | 텍스트 | `마오` | 입력창 |
| 아바타 이미지 | `character_config.avatar` | 파일 | `mao.png` | 파일 선택 |
| 사용자 표시명 | `character_config.human_name` | 텍스트 | `사용자` | 입력창 |
| 캐릭터 프롬프트 | `character_config.persona_prompt` | 멀티라인 | (한국어 프롬프트) | 텍스트 영역 |
| 에이전트 종류 | `character_config.agent_config.conversation_agent_choice` | 선택 | `basic_memory_agent` | 드롭다운 |
| LLM 제공자 | `character_config.agent_config.agent_settings.basic_memory_agent.llm_provider` | 선택 | `ollama_llm` | 드롭다운 |
| 빠른 첫 응답 | `character_config.agent_config.agent_settings.basic_memory_agent.faster_first_response` | 토글 | `true` | 토글 |
| 문장 분할 방식 | `character_config.agent_config.agent_settings.basic_memory_agent.segment_method` | 선택 | `pysbd` | 드롭다운 |
| MCP 사용 | `character_config.agent_config.agent_settings.basic_memory_agent.use_mcpp` | 토글 | `true` | 토글 |
| MCP 서버 목록 | `character_config.agent_config.agent_settings.basic_memory_agent.mcp_enabled_servers` | 리스트 | `["time","ddg-search"]` | 멀티선택 |
| Ollama URL | `character_config.agent_config.llm_configs.ollama_llm.base_url` | 텍스트 | `http://localhost:11434/v1` | 입력창 |
| Ollama 모델 | `character_config.agent_config.llm_configs.ollama_llm.model` | 텍스트 | `qwen2.5:latest` | 입력창 |
| ASR 엔진 | `character_config.asr_config.asr_model` | 선택 | `sherpa_onnx_asr` | 드롭다운 |
| TTS 엔진 | `character_config.tts_config.tts_model` | 선택 | `edge_tts` | 드롭다운 |
| TTS 보이스 | `character_config.tts_config.edge_tts.voice` | 선택 | `ko-KR-SunHiNeural` | 드롭다운 |
| VAD 엔진 | `character_config.vad_config.vad_model` | 선택 | `null` | 드롭다운 |
| 특수문자 제거 | `character_config.tts_preprocessor_config.remove_special_char` | 토글 | `true` | 토글 |
| 대괄호 무시 | `character_config.tts_preprocessor_config.ignore_brackets` | 토글 | `true` | 토글 |
| 괄호 무시 | `character_config.tts_preprocessor_config.ignore_parentheses` | 토글 | `true` | 토글 |
| 번역 사용 | `character_config.tts_preprocessor_config.translator_config.translate_audio` | 토글 | `false` | 토글 |
| 번역 제공자 | `character_config.tts_preprocessor_config.translator_config.translate_provider` | 선택 | `deeplx` | 드롭다운 |

---

## 3) UI 설계 팁

- **LLM/ASR/TTS 엔진 선택은 단계형 UI**가 사용성이 좋습니다.  
  (1) 엔진 선택 → (2) 상세 설정 노출
- **프롬프트 편집은 전용 화면**이 필요합니다.  
  (미리보기/버전관리/리셋 기능 권장)
- **권한 관련 토글**은 “처음 한 번만 요청” 흐름과 연결하세요.
