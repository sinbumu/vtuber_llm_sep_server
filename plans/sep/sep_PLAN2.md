위 계획에 따라 FastAPI 서버 엔트리포인트를 추가하라.

작업:
1) 새 디렉토리/모듈을 만들고(FastAPI app), 다음 엔드포인트를 구현:
   - GET /health -> {"ok": true}
   - POST /v1/chat -> 입력을 에코하거나("stub"), history_uid 생성/반환까지는 실제로 동작
2) chat_history_manager.py를 재사용하여:
   - history_uid 없으면 create_new_history 호출
   - history_uid 있으면 파일 존재 여부 체크(없으면 404)
   - user 메시지를 store_message로 저장(assistant는 stub 응답도 저장)
3) 설정(conf_uid 기반 폴더) 상대경로 문제 없이 동작하도록 BASE_DIR 처리
4) 실행 방법(uvicorn)과 curl 예제를 README에 추가
5) 불필요한 기존 런타임 진입점은 건드리지 말고 "새 서버만" 추가

주의:
- 이 단계에서는 LLM 호출을 붙이지 말고(오류 리스크), 서버 기동 + history 저장까지 보장하라.
- 코드 변경은 가능한 작은 범위로 커밋 가능하게 구성하라.
