# API_INVENTORY.md — 백엔드 API/WS 인벤토리

이 문서는 **Python 백엔드 서버** 기준으로 현재 노출되는 HTTP/WS 엔드포인트와
WebSocket 메시지 타입을 요약합니다.

소스 기준: `src/open_llm_vtuber/server.py`, `src/open_llm_vtuber/routes.py`,
`src/open_llm_vtuber/websocket_handler.py`, `src/open_llm_vtuber/conversations/*`.

---

## 1) HTTP 엔드포인트

### 기본 API
- `GET /web-tool`  
  - `/web-tool/index.html`로 302 리다이렉트
- `GET /web_tool`  
  - `/web-tool/index.html`로 302 리다이렉트
- `GET /live2d-models/info`  
  - Live2D 모델 폴더 스캔 결과 반환
  - 응답 형태: `{ type, count, characters: [{ name, avatar, model_path }] }`
- `POST /asr`  
  - 업로드된 WAV(16-bit PCM) 오디오를 텍스트로 변환
  - 요청: `multipart/form-data` (필드: `file`)
  - 응답: `{ text: "..." }` 또는 에러 JSON

### 정적 파일 마운트
- `GET /cache/*` (TTS 결과 캐시)
- `GET /live2d-models/*` (Live2D 에셋)
- `GET /bg/*` (배경 이미지)
- `GET /avatars/*` (캐릭터 아바타)
- `GET /web-tool/*` (웹툴)
- `GET /` (프론트 정적 빌드)

---

## 2) WebSocket 엔드포인트

- `WS /client-ws`  
  - 메인 실시간 대화 채널
- `WS /proxy-ws`  
  - 프록시 모드 전용 ( `system_config.enable_proxy: true` )
- `WS /tts-ws`  
  - 텍스트 → 음성 합성 전용 채널

---

## 3) WS 메시지 프로토콜

### 3-1) 클라이언트 → 서버 (type 기반)
다음 타입들은 `websocket_handler._init_message_handlers()`에서 처리됩니다.

- **그룹/세션**
  - `add-client-to-group` (`invitee_uid`)
  - `remove-client-from-group` (`target_uid`)
  - `request-group-info`
  - `request-init-config`
  - `heartbeat`
  - `frontend-playback-complete` (재생 완료 시점 알림)

- **대화 입력**
  - `mic-audio-data` (`audio`: float[] 버퍼)
  - `mic-audio-end`
  - `raw-audio-data`
  - `text-input` (`text`, `images` optional)
  - `ai-speak-signal`
  - `interrupt-signal` (`text` optional)
  - `audio-play-start`

- **기록/설정**
  - `fetch-history-list`
  - `fetch-and-set-history` (`history_uid`)
  - `create-new-history`
  - `delete-history` (`history_uid`)
  - `fetch-configs`
  - `switch-config` (`filename`)
  - `fetch-backgrounds`

### 3-2) 서버 → 클라이언트
서버가 보내는 주요 타입들:

- **시스템/제어**
  - `full-text` (상태 메시지)
  - `set-model-and-conf` (현재 모델/캐릭터 정보)
  - `control` (`start-mic`, `interrupt`, `mic-audio-end`, `conversation-chain-start`, `conversation-chain-end`)
  - `heartbeat-ack`
  - `error`

- **오디오/대화**
  - `audio` (base64 WAV + 볼륨 정보 + 표시 텍스트)
  - `user-input-transcription` (STT 결과)
  - `backend-synth-complete`
  - `force-new-message`

- **그룹/기록/설정**
  - `group-update`
  - `group-operation-result`
  - `history-list`
  - `history-data`
  - `new-history-created`
  - `history-deleted`
  - `config-files`
  - `config-switched`
  - `background-files`

### 3-3) `audio` 페이로드 구조
`utils/stream_audio.prepare_audio_payload()` 기준:

```json
{
  "type": "audio",
  "audio": "<base64 WAV or null>",
  "volumes": [0.0-1.0],
  "slice_length": 20,
  "display_text": { "name": "...", "text": "...", "avatar": "..." },
  "actions": { ... } | null,
  "forwarded": false
}
```

---

## 4) `/tts-ws` 프로토콜

### 요청
```json
{ "text": "문장 전체 텍스트" }
```

### 응답
부분 응답:
```json
{ "status": "partial", "audioPath": "cache/xxx.wav", "text": "문장" }
```

완료:
```json
{ "status": "complete" }
```

오류:
```json
{ "status": "error", "message": "..." }
```

