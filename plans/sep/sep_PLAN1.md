위 [Goal]/[Success Criteria]/[Constraints]를 만족시키기 위한 분리 계획을 작성하라.

1) 현재 레포에서 서버 엔트리포인트(실행 파일/모듈)가 무엇인지 찾아라.
2) Unity용 LLM 서버 엔트리포인트를 새로 만든다면 파일 경로를 제안하라. (예: src/unity_llm_server/app.py)
3) "반드시 재사용"할 파일/모듈 목록과 "제거/비활성화"할 목록을 작성하라.
4) /v1/chat 구현에 필요한 호출 흐름을 함수 단위로 매핑하라:
   - history_uid 없을 때 create_new_history
   - history_uid 있을 때 get_history -> set_memory_from_history
   - messages 구성 -> LLM 호출 -> 응답 수집
   - store_message로 user/assistant 저장
5) requirements를 최소화하기 위한 제거 후보를 나열하라(ASR/TTS/OBS/프론트 관련).
6) 구현 리스크(상대경로, 설정 로딩, import side-effects)를 미리 지적하고 해결책을 제안하라.

출력 형식:
- Architecture sketch (text)
- Keep list / Remove list
- Call flow (bullet)
- Risks & mitigations
- Proposed file changes (high level)
