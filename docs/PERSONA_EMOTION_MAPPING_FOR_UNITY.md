# PERSONA_EMOTION_MAPPING_FOR_UNITY.md

이 문서는 Open-LLM-VTuber 계열 코드에서 **캐릭터 페르소나**와 **감정(표정) 매핑**이 어떻게 동작하는지 정리하고,  
현재 분리한 **LLM-only 서버** 기준으로 Unity의 "캐릭터 창작 모드"에 어떤 인터페이스를 제공하면 좋은지 제안합니다.

---

## 1) 원본 프로젝트의 페르소나/감정 처리 방식

### 1-1) 페르소나 입력 소스
- 핵심 페르소나: `conf.yaml`의 `character_config.persona_prompt`
- 보조 프롬프트: `system_config.tool_prompts.*`가 `prompts/utils/*.txt`와 연결
  - 예: `live2d_expression_prompt`, `mcp_prompt`, `group_conversation_prompt`

### 1-2) 시스템 프롬프트 합성
- 원본 흐름(`ServiceContext.construct_system_prompt`)은:
  1. `persona_prompt` 시작
  2. `tool_prompts` 순회하며 텍스트를 append
  3. `live2d_expression_prompt`는 `[<insert_emomap_keys>]`를 실제 감정 키 목록으로 치환

### 1-3) 감정 키 소스
- `Live2dModel`이 `model_dict.json`의 `emotionMap`을 로드
- `emo_str`를 `[joy], [sadness], [surprise] ...` 형태 문자열로 생성
- 이 키 목록이 프롬프트에 삽입되어 LLM이 합법 태그만 쓰도록 유도됨

### 1-3-1) 감정 태그는 고정인가?
- **전역 고정 목록이 아니라, 모델별 확장 가능 구조**입니다.
- 실제 허용 태그는 각 모델의 `emotionMap` key에 의해 결정됩니다.
- 즉, `emotionMap`에 키를 추가/변경하면 허용 태그도 함께 바뀝니다.

참고(코드 주석 예시):
- `live2d_model.py`에는 예시로 아래 태그 문자열이 언급됩니다.
  - `[fear], [anger], [disgust], [sadness], [joy], [neutral], [surprise]`
- 이 목록은 "예시"이며, 실제 기준은 항상 `emotionMap`입니다.

### 1-4) 응답에서 감정 추출
- LLM 텍스트 예: `"좋아! [joy] 해보자."`
- `Live2dModel.extract_emotion()`이 `[joy]` 같은 태그를 스캔해 정수 인덱스 리스트로 변환
- `actions_extractor()`가 이를 `Actions.expressions`에 담음
- 원본 오디오/WS 페이로드에 `actions`가 포함되어 프론트에서 표정 반영

---

## 2) 현재 LLM-only 서버에서의 상태 (중요)

현재 분리 서버(`src/llm_server`)는 Live2D 파이프라인을 의도적으로 비활성화합니다.

- `chat_service._build_system_prompt()`에서 `live2d_expression_prompt`를 스킵
- `BasicMemoryAgent` 생성 시 `live2d_model=None`
- `/v1/chat`, `/v1/ws/chat` 응답은 텍스트 중심이며 `actions`를 내보내지 않음

즉, **지금 상태에서는 서버가 감정 태그를 공식적으로 추출/전달하지 않습니다.**

---

## 3) Unity 캐릭터 창작 모드 설계 시 반영 포인트

### 3-1) 최소 입력 항목(권장)
- 캐릭터 이름(`character_name`)
- 사용자 호칭(`human_name`)
- 페르소나 본문(`persona_prompt`)
- LLM 모델 설정(provider/model/base_url/api_key)

### 3-2) 감정 매핑 UI(Phase 2 권장)
Live2D를 다시 붙일 가능성을 고려해, 지금부터 데이터 구조는 준비해두는 게 좋습니다.

- 감정 태그 목록 (예: `joy`, `sadness`, `angry`, `surprised`)
- 태그별 표정/모션 ID 매핑 (int 또는 string)
- 유효 태그 미리보기: `[joy], [sadness], ...`
- 샘플 문장 테스트: 태그 포함 텍스트를 넣고 Unity에서 실제 표정 트리거 확인

권장 UI 정책:
- 태그 입력 자유 텍스트를 허용하지 말고, **`emotionMap`에서 불러온 태그 목록 기반 선택 UI** 제공
- 허용 태그는 자동으로 `[]` 포맷 미리보기 제공 (예: `[joy]`)
- 태그 추가/삭제는 캐릭터의 `emotion_map` 편집에서만 가능하게 제한

권장 데이터 형태(예시):
```json
{
  "character_id": "mao_pro_001",
  "emotion_map": {
    "joy": 4,
    "sadness": 3,
    "angry": 1,
    "surprised": 6
  }
}
```

### 3-3) UX 가이드
- 태그 입력은 항상 `[]` 문법으로 안내 (`[joy]`)
- 허용되지 않은 태그는 즉시 경고
- "텍스트 출력용"과 "모션 트리거용"을 분리 표시
  - 예: 사용자에게는 태그 제거된 문장 표시
  - 엔진 내부 처리에는 태그 유지

---

## 4) 구현 전략 제안 (LLM-only 기준)

### MVP (지금)
- 페르소나 편집/저장 중심
- 감정 매핑 UI는 숨기거나 "준비중"으로 표시
- 필요 시 Unity 클라이언트에서 임시 규칙 기반 태그 파싱

### 확장 (차기)
- 서버에 감정 추출 옵션 추가:
  - `live2d_expression_prompt` 재활성화 옵션
  - 응답에 `actions.expressions` 포함
- 또는 Unity 측 파서 고도화:
  - 서버 응답 텍스트에서 태그 파싱
  - 태그 제거 후 표시 텍스트로 렌더
  - 태그 기반 애니메이션 실행

### 4-1) "LLM에 허용 태그를 전달" 가이드
감정 태그를 completion에 포함시키려면, 시스템 프롬프트에 허용 목록을 명시해야 합니다.

- 기본 패턴(원본 프로젝트):
  1. `prompts/utils/live2d_expression_prompt.txt` 로드
  2. `[<insert_emomap_keys>]`를 실제 태그 목록으로 치환
  3. 최종 system prompt에 append
- 결과적으로 모델은 "허용된 태그만 사용" 지시를 받게 됩니다.

실무 권장 문구(요지):
- "아래 목록 외 태그 사용 금지"
- "태그는 반드시 대괄호 포함(`[tag]`)"
- "문장 1개에 태그 0~N개 가능"

Unity 기획 포인트:
- 캐릭터 저장 시 `emotion_map`을 기준으로 허용 태그 문자열을 생성
- 서버 재시작 시 해당 문자열이 system prompt에 반영되도록 설계
- 추후 런타임 재설정 도입 시에는 `reload-config` 계열 API로 즉시 반영

---

## 5) 기획 체크리스트

- [ ] 캐릭터 창작 모드에서 페르소나 편집/버전 관리 필요 여부
- [ ] 감정 태그를 사용자에게 노출할지(고급 옵션) 결정
- [ ] 태그-모션 매핑을 서버 보관할지 Unity 보관할지 결정
- [ ] LLM-only 단계에서 감정 기능 비활성 정책 명시
- [ ] 차기 단계에서 서버/클라이언트 중 어느 쪽에 감정 파서를 둘지 확정

