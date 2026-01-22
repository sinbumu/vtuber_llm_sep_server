# LOCAL_GUIDE.md — Windows 로컬 서버 실행 가이드

이 문서는 **Windows 데스크탑(PowerShell)** 에서 Open-LLM-VTuber의 **파이썬 서버**를 로컬로 띄우는 최소 절차를 정리합니다.  
클라이언트(브라우저/데스크톱 앱)와 붙이는 단계는 뒤에 포함되어 있습니다.

---

## 1) 사전 준비

- **Python 3.10~3.12** 설치 (64-bit 권장)
- **uv** 설치 (프로젝트 표준 패키지 매니저)
- (권장) **ffmpeg** 설치 후 PATH 등록  
  - 오디오 처리에서 사용됩니다. 없으면 일부 기능이 동작하지 않을 수 있습니다.

PowerShell에서 uv 설치:

```powershell
python -m pip install uv
```

---

## 2) 프로젝트 폴더로 이동

```powershell
cd C:\Users\sinbu\Documents\GitHub\Open-LLM-VTuber_fork
```

---

## 3) 의존성 설치 (uv)

```powershell
uv sync
```

> 이미 설치가 끝났다면 변경된 의존성만 갱신됩니다.

---

## 4) 설정 파일 준비 (`conf.yaml`)

처음 실행 시 `conf.yaml`이 없다면 템플릿을 복사합니다.

```powershell
Copy-Item .\config_templates\conf.default.yaml .\conf.yaml
```

한국어/중국어 템플릿을 쓰고 싶다면:

```powershell
Copy-Item .\config_templates\conf.ZH.default.yaml .\conf.yaml
```

### 최소로 확인할 항목 (중요)

`conf.yaml`에서 아래 항목은 **환경에 맞게 꼭 확인/수정**하세요.

- **서버 주소/포트**
  - `system_config.host` (로컬만 쓸 땐 `localhost` 유지)
  - `system_config.port` (기본 `12393`)

- **LLM 공급자**
  - `character_config.agent_config.agent_settings.basic_memory_agent.llm_provider`
  - 예: `ollama_llm`, `openai_llm`, `openai_compatible_llm`

- **ASR/TTS 엔진**
  - `character_config.asr_config.asr_model`
  - `character_config.tts_config.tts_model` (파일 내 위치 참고)
  - 선택한 엔진이 필요한 모델/키를 제대로 갖추지 않으면, 대화 시 오류가 납니다.

> 기본 템플릿은 `ollama` 기반 예시가 들어 있습니다.  
> 로컬에서 **Ollama를 쓰지 않는다면** 해당 LLM 섹션을 다른 공급자로 변경하세요.

---

## 4-1) 언어 지원/설정 가이드

이 프로젝트는 **LLM / STT / TTS 엔진에 따라 지원 언어가 달라집니다.**  
즉, “프로젝트 자체가 지원하는 언어”라기보다 **선택한 엔진/모델이 지원하는 언어 범위가 곧 지원 언어**입니다.

### A) LLM(대화 언어)
- **결정 요인**: Ollama/클라우드 등에서 쓰는 **LLM 모델 자체**
- **설정 위치**: `character_config.agent_config.llm_configs.ollama_llm.model`
- **권장**: 한국어를 쓰려면 **멀티링구얼 LLM**(예: Qwen, Llama 최신 버전 등)을 선택하고,
  `persona_prompt`를 **한국어로 작성**하세요.

### B) STT(음성 → 텍스트)
- **결정 요인**: `asr_config.asr_model` 및 해당 모델/엔진의 언어 지원
- **기본값**: `sherpa_onnx_asr` + `sense_voice` (한국어 포함 다국어 지원)
- **설정 위치**:
  - `character_config.asr_config.asr_model`
  - `character_config.asr_config.sherpa_onnx_asr.*`
  - `character_config.asr_config.faster_whisper.language` 등
- **팁**:
  - `sense_voice`는 **ko/ja/zh/en** 등을 포함한 멀티링구얼 모델입니다.
  - `faster_whisper`를 사용할 경우 `language: 'ko'`처럼 **명시**하면 인식 정확도가 좋아집니다.

### C) TTS(텍스트 → 음성)
- **결정 요인**: `tts_config.tts_model`과 선택한 TTS 엔진의 보이스/언어 지원
- **기본값**: `edge_tts` (클라우드, 다국어 보이스 지원)
- **설정 위치**:
  - `character_config.tts_config.tts_model`
  - `character_config.tts_config.edge_tts.voice`
- **한국어 예시**:
  - `ko-KR-SunHiNeural`, `ko-KR-InJoonNeural` 등
  - 보이스 목록 확인: `edge-tts --list-voices`

### D) UI/자막 언어
- **결정 요인**: LLM 출력 언어 + 프롬프트 언어
- **설정 위치**: `character_config.persona_prompt`
- **팁**: UI에 표시되는 텍스트는 **LLM 응답 그대로**이므로, 프롬프트 언어가 중요합니다.

### E) 번역 옵션(선택)
- **기능**: 자막/음성 번역을 별도 엔진으로 처리
- **설정 위치**: `tts_preprocessor_config.translator_config`
- **주의**: `deeplx`는 별도 서버가 필요하며, 없으면 오류가 날 수 있습니다.

---

## 5) 서버 실행

```powershell
uv run run_server.py
```

디버그 로그를 보고 싶다면:

```powershell
uv run run_server.py --verbose
```

실행 후 콘솔에 `Starting server on host:port` 로그가 나오면 정상입니다.

---

## 6) 접속 확인

브라우저에서 아래 주소로 접속합니다.

```
http://localhost:12393
```

> 포트를 바꿨다면 해당 포트로 접속하세요.

---

## 7) 흔한 문제 & 빠른 체크

### 1) 첫 화면이 `Not Found`로 나옴
- `frontend/` 서브모듈이 비어 있을 수 있습니다.
- 아래 명령 실행 후 다시 시도:

```powershell
git submodule update --init --recursive
```

### 2) LLM/ASR/TTS 초기화 실패
- `conf.yaml`에서 엔진 설정과 API 키/모델 경로를 다시 확인하세요.
- 로컬 모델(예: Ollama, Whisper 등)을 쓰려면 해당 모델이 **이미 다운로드**되어 있어야 합니다.

### 3) 마이크가 동작하지 않음
- 브라우저는 **localhost 또는 https** 에서만 마이크 사용이 가능합니다.
- 원격 접속 시에는 https 설정이 필요합니다.

---

## 8) 빠른 리셋 팁

설정을 꼬이게 만들었을 때, 다음처럼 초기화해서 다시 시작할 수 있습니다.

```powershell
Remove-Item .\conf.yaml
Copy-Item .\config_templates\conf.default.yaml .\conf.yaml
```

---

## 9) 다음 단계(선택)

- LLM: 로컬(ollama/LM Studio) vs 클라우드(OpenAI/Claude 등) 결정
- ASR/TTS: 로컬 모델 or 클라우드 API 선택
- 캐릭터/Live2D 모델 교체 시 `model_dict.json` 및 `characters/` 폴더 참고

---

필요하면 **내 환경에 맞는 `conf.yaml` 최적화 예시**도 정리해 드릴게요.
