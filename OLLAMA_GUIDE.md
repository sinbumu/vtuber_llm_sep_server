# OLLAMA_GUIDE.md — Windows 로컬 Ollama 간단 사용법

이 문서는 **Ollama를 인스톨러로 설치한 상태**를 전제로,
로컬에서 기본적인 사용 흐름만 빠르게 정리합니다.

---

## 1) 설치 확인

PowerShell에서 버전 확인:

```powershell
ollama --version
```

`ollama` 명령이 인식되지 않으면 PATH 문제이므로,
Ollama 재실행 또는 PATH 등록이 필요합니다.

---

## 2) 서버 실행/종료

서버 실행:

```powershell
ollama serve
```

서버 종료:
- 실행 중인 PowerShell 창에서 `Ctrl + C`
- 또는 해당 창을 닫기

> Ollama 앱(트레이)으로 실행했다면 앱 종료로 서버가 꺼집니다.

---

## 3) 모델 다운로드 / 목록 확인

모델 다운로드:

```powershell
ollama pull qwen2.5:latest
```

모델 목록:

```powershell
ollama list
```

---

## 4) 모델 실행(빠른 테스트)

```powershell
ollama run qwen2.5:latest
```

프롬프트가 뜨면 바로 대화가 가능합니다.

---

## 5) 모델 저장 위치

기본 경로:

```
C:\Users\<사용자>\.ollama\models
```

SSD 용량이 줄어드는 이유는 이 경로에 모델 파일이 저장되기 때문입니다.

---

## 6) Open-LLM-VTuber 연동 체크

`conf.yaml`에서 아래 값이 Ollama 설정과 일치해야 합니다:

```yaml
character_config:
  agent_config:
    agent_settings:
      basic_memory_agent:
        llm_provider: 'ollama_llm'
    llm_configs:
      ollama_llm:
        base_url: 'http://localhost:11434/v1'
        model: 'qwen2.5:latest'
```

Ollama 서버가 꺼지면 LLM 응답이 실패하니 항상 서버를 켜둬야 합니다.
