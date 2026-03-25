# UNITY_API_GUIDE.md

이 문서는 Unity 클라이언트가 `llm_server`와 통신할 때 필요한 API 명세를 기능 문서 형태로 정리합니다.

## 문서 목적

- Unity 개발자가 서버 API를 빠르게 이해하고 바로 연동할 수 있게 함
- 엔드포인트별 요청/응답 형식과 실패 케이스를 명확히 함
- 현재 권장 경로인 `POST /v1/chat` 중심으로 사용 규칙을 정리함

## 기본 원칙

- 기본 대화 API는 `POST /v1/chat`입니다.
- 이미지가 포함된 대화도 `POST /v1/chat`을 사용합니다.
- `/v1/ws/chat`은 스트리밍이 필요한 레거시 경로로 봅니다.
- `history_uid`를 유지하면 같은 대화 세션으로 이어집니다.
- 서버는 history에 원본 이미지 데이터를 저장하지 않습니다.

## 엔드포인트 요약

### 1) `GET /health`

기능:
- 서버 프로세스 생존 확인
- 초기 기동 완료 여부 확인

권장 사용 시점:
- Unity가 `llm_server.exe` 실행 직후
- 주기적인 헬스체크

성공 응답 예:
```json
{
  "ok": true
}
```

Unity 처리 규칙:
- 200 응답이 오면 API 호출 가능 상태로 간주
- 일정 시간 안에 응답이 없으면 서버 기동 실패 또는 포트 문제로 처리

### 2) `GET /admin/current-config`

기능:
- 현재 적용 중인 설정 요약 조회
- Unity UI와 실제 서버 적용 상태 비교

주요 확인 대상:
- `provider`
- `model`
- `host`
- `port`
- `recentMessageWindow`
- `contextCompaction`

성공 응답 예:
```json
{
  "status": "ok",
  "configPath": "C:/path/to/conf.yaml",
  "process": {
    "host": "127.0.0.1",
    "port": 8000
  },
  "configSummary": {
    "character": {
      "confUid": "mao_pro_001"
    },
    "llm": {
      "provider": "google_genai",
      "model": "gemini-2.5-flash"
    },
    "conversation": {
      "recentMessageWindow": 32,
      "contextCompaction": {
        "enabled": true,
        "mode": "summary_recent_window",
        "targetMessageCount": 24,
        "triggerMessageCount": 28,
        "maxMessageCount": 32
      }
    }
  }
}
```

Unity 처리 규칙:
- 설정 UI 초기값 표시용으로 사용 가능
- 민감값은 마스킹될 수 있으므로 그대로 저장 원본으로 쓰지 않는 편이 안전

### 3) `POST /admin/reload-config`

기능:
- 외부 `conf.yaml` 변경 사항을 다시 읽고 검증
- 즉시 반영 가능한 항목과 재시작 필요한 항목을 구분

권장 사용 시점:
- Unity가 설정 파일을 저장한 직후
- 서버 재시작 없이 반영 가능한지 확인할 때

성공 응답 예:
```json
{
  "status": "ok",
  "success": true,
  "message": "Config validated. Runtime-supported changes will apply on the next request.",
  "configPath": "C:/path/to/conf.yaml",
  "warnings": [],
  "errors": [],
  "runtimeAppliedOnNextRequest": [
    "character_config.llm_configs.<provider>.model"
  ],
  "restartRequired": [
    "LLM_SERVER_PORT"
  ],
  "configSummary": {}
}
```

Unity 처리 규칙:
- `errors`가 비어 있지 않으면 사용자에게 설정 오류를 표시
- `restartRequired`가 비어 있지 않으면 서버 재시작 UI를 띄우는 편이 안전
- `recent_message_window`, `context_compaction.*`, provider/model, persona 쪽은 다음 요청부터 반영 가능

### 4) `POST /v1/chat`

기능:
- 단일 요청/응답 방식 텍스트 대화
- 이미지 snapshot 포함 대화
- history 생성 및 이어쓰기

현재 권장도:
- 가장 권장되는 기본 채팅 API
- Unity 신규 연동은 이 엔드포인트 기준으로 구현 권장

요청 헤더:
```http
Content-Type: application/json
```

요청 본문:
```json
{
  "conf_uid": "mao_pro_001",
  "history_uid": null,
  "text": "안녕",
  "images": null
}
```

필드 설명:
- `conf_uid`: 사용할 캐릭터/설정 UID
- `history_uid`: 기존 대화 세션 ID, 새 대화면 `null`
- `text`: 사용자 입력 문자열
- `images`: 선택 필드, 이미지 첨부 목록

`images[]` 항목 형식:
```json
{
  "source": "screen",
  "mime_type": "image/jpeg",
  "data": "data:image/jpeg;base64,..."
}
```

`images[]` 필드 설명:
- `source`: `screen`, `camera`, `clipboard`, `upload`
- `mime_type`: 예: `image/jpeg`, `image/png`
- `data`: `data:image/...;base64,...` 형태의 data URL

텍스트 전용 요청 예:
```json
{
  "conf_uid": "mao_pro_001",
  "history_uid": null,
  "text": "안녕"
}
```

텍스트 + 이미지 요청 예:
```json
{
  "conf_uid": "mao_pro_001",
  "history_uid": "2026-03-25_23-18-54_267fbf30643c425bbb1f6c5713d26f98",
  "text": "이 캐릭터 알아? 내가 좋아하는 캐릭이야.",
  "images": [
    {
      "source": "upload",
      "mime_type": "image/jpeg",
      "data": "data:image/jpeg;base64,..."
    }
  ]
}
```

성공 응답 예:
```json
{
  "history_uid": "2026-03-25_23-18-54_267fbf30643c425bbb1f6c5713d26f98",
  "text": "응답 텍스트"
}
```

Unity 처리 규칙:
- 새 대화 시작 시 `history_uid = null`로 보냄
- 응답의 `history_uid`를 저장했다가 다음 요청에 다시 사용
- 이미지 첨부는 1~2장 수준의 snapshot 사용을 권장
- 화면공유/카메라는 연속 스트리밍보다 필요 시점 snapshot 첨부 방식 권장

실패 가능 케이스:
- `400 Bad Request`
  - 잘못된 JSON
  - 잘못된 `images[].data` 형식
  - 지원하지 않는 `source` 값
- `404 Not Found`
  - 없는 `history_uid`
- `502 Bad Gateway`
  - upstream LLM provider 오류
  - vision 입력 처리 실패
- `504 Gateway Timeout`
  - LLM 응답 시간 초과

주의 사항:
- vision 미지원 provider/model이면 이미지 요청이 실패할 수 있음
- history에는 원본 이미지 대신 attachment 메타데이터만 저장됨
- 긴 대화 품질은 `recent_message_window`와 `context_compaction` 설정 영향을 받음

### 5) `WS /v1/ws/chat`

기능:
- 텍스트 응답을 delta 이벤트로 받는 WebSocket 경로

현재 위치:
- 레거시 스트리밍 경로
- 신규 Unity 연동의 기본값으로는 권장하지 않음

현재 차이점:
- 통신 방식이 WebSocket 이벤트 스트림임
- 텍스트 스트리밍에는 유리함
- 현재 이미지 입력은 `POST /v1/chat` 중심으로 지원

요청 예:
```json
{
  "conf_uid": "mao_pro_001",
  "history_uid": null,
  "text": "안녕"
}
```

응답 이벤트 예:
```json
{ "type": "session", "history_uid": "..." }
{ "type": "delta", "text": "..." }
{ "type": "done", "text": "full response" }
```

에러 이벤트 예:
```json
{ "type": "error", "code": "history_not_found" }
{ "type": "error", "code": "llm_timeout" }
{ "type": "error", "code": "llm_error" }
```

Unity 처리 규칙:
- 정말 delta 표시가 필요할 때만 선택
- 기능 확장 우선순위는 `POST /v1/chat`보다 낮게 보는 편이 안전

## Unity 연동 추천 플로우

1. `llm_server.exe` 실행
2. `GET /health` 폴링
3. 설정 UI가 있으면 `GET /admin/current-config`로 초기 상태 표시
4. 일반 채팅은 `POST /v1/chat`
5. 새 `history_uid`를 저장해 세션 유지
6. 설정 저장 후 필요 시 `POST /admin/reload-config`
7. `restartRequired`가 있으면 서버 재시작

## 이미지 입력 운영 권장

- Unity가 화면/카메라를 직접 캡처하고 서버에는 snapshot만 전달
- 이미지 데이터는 파일 경로보다 data URL이 이식에 유리
- 너무 잦은 이미지 첨부는 비용과 지연을 증가시킬 수 있음
- vision 응답 품질은 서버보다 실제 사용 모델 성능에 더 크게 좌우됨

## 관련 문서

- `UNITY_GUIDE.md`
- `README.md`
- `README_LLM_SERVER.md`
