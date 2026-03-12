# UNITY_GUIDE.md

이 문서는 Unity 개발자가 `llm_server.exe` 형태의 Python 서버를
Unity 프로젝트 또는 배포 폴더에 포함할 때 필요한 최소 가이드를 정리합니다.

## 목적

- Unity 앱이 LLM 백엔드 서버를 **자식 프로세스**로 실행
- Unity 앱이 외부 설정 파일을 관리
- 서버 상태 확인, 설정 반영, 재시작 정책을 단순하게 유지

## 권장 폴더 구조

예시:
```text
YourUnityApp/
  YourUnityApp.exe
  llm_server/
    llm_server.exe
    conf.yaml
```

또는 개발 중:
```text
YourUnityProject/
  Assets/
  StreamingAssets/
    llm_server/
      llm_server.exe
      conf.yaml
```

## 설정 파일 관리 방식

권장 방식:
- Unity가 `llm_server.exe`와 **같은 폴더의 `conf.yaml`**를 관리
- 서버는 다음 우선순위로 설정 파일을 찾음:
  1. `LLM_SERVER_CONFIG_PATH`
  2. exe 실행 디렉토리의 `conf.yaml`
  3. 번들 기본 `conf.yaml`

즉, Unity에서 가장 쉬운 방식은:
- `llm_server.exe`와 같은 경로에 `conf.yaml` 배치
- 필요 시 해당 파일을 수정
- MVP에서는 서버 재시작

## 참고 예시 설정 파일

루트의 `conf.unity.example.yaml`을 참고해 외부 설정 파일을 만들 수 있습니다.

권장 절차:
1. `conf.unity.example.yaml` 복사
2. 이름을 `conf.yaml`로 변경
3. Unity 배포 폴더의 `llm_server.exe` 옆에 배치
4. API key / model / persona만 우선 수정

## Unity에서 서버 실행 시 권장 환경변수

필요 시 Unity에서 자식 프로세스 시작 전에 설정:

- `LLM_SERVER_HOST`
- `LLM_SERVER_PORT`
- `LLM_SERVER_LOG_LEVEL`
- `LLM_SERVER_ENABLE_MCP`
- `LLM_SERVER_CONFIG_PATH`

MVP 권장:
- `LLM_SERVER_CONFIG_PATH`는 생략 가능
- exe 옆 `conf.yaml` 방식 사용
- `LLM_SERVER_PORT`만 명시적으로 관리

## 어떤 설정이 재시작이 필요한가

재시작 필요:
- `LLM_SERVER_HOST`
- `LLM_SERVER_PORT`
- `LLM_SERVER_LOG_LEVEL`
- `LLM_SERVER_ENABLE_MCP`
- `LLM_SERVER_CONFIG_PATH`

다음 요청부터 반영 가능:
- LLM provider / model / base_url / api_key
- `persona_prompt`
- `tool_prompts`
- 일부 대화 관련 설정

권장 MVP:
- 사용자가 설정 변경
- Unity가 `conf.yaml` 저장
- Unity가 서버 재시작

## Unity가 호출하면 좋은 API

### 1) 서버 생존 확인
```http
GET /health
```

용도:
- 서버가 정상 기동했는지 확인
- 포트 충돌/기동 실패 감지

### 2) 현재 적용 설정 요약
```http
GET /admin/current-config
```

용도:
- Unity UI와 실제 적용 설정 비교
- 현재 provider/model/port 등 표시

### 3) 설정 재로드 검증
```http
POST /admin/reload-config
```

용도:
- `conf.yaml` 저장 후 검증
- 어떤 항목이 재시작 필요한지 확인

## Unity 쪽 기본 플로우

1. Unity가 `llm_server.exe` 실행
2. `/health` 폴링으로 준비 완료 확인
3. `/v1/chat` 또는 `/v1/ws/chat` 사용
4. 사용자가 설정 변경
5. Unity가 외부 `conf.yaml` 저장
6. MVP에서는 서버 재시작
7. 추후 확장 시 `/admin/reload-config` 사용

## 실패 대응

### 포트 충돌 / 서버 기동 실패
- Unity가 프로세스 실행 후 `/health` 응답을 기다림
- 일정 시간 내 응답 없으면:
  - 프로세스 종료 여부 확인
  - 에러 로그 출력
  - 포트 충돌 또는 서버 기동 실패 안내

### 설정 파일 오류
- `/admin/reload-config` 응답의 `errors`, `warnings` 확인
- 또는 서버 시작 실패 시 stdout/stderr 로그 표시

## 권장 사항

- API key는 Unity 프로젝트 원본에 하드코딩하지 않는 편이 좋음
- 사용자 수정 가능한 `conf.yaml`는 UTF-8 저장 권장
- 파일 저장 시 가능하면 임시 파일 작성 후 교체 방식 사용
- 포트는 앱 내에서 고정하거나, 저장된 설정을 기준으로 관리

## 같이 보면 좋은 문서

- `README.md`
- `README_LLM_SERVER.md`
- `docs/UNITY_LLM_SERVER_SETTINGS.md`
- `docs/SERVER_RELOAD_ANALYSIS.md`
