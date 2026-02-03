from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from loguru import logger

from open_llm_vtuber.chat_history_manager import (
    create_new_history,
    store_message,
    _get_safe_history_path,
)

from .models import ChatRequest, ChatResponse
from .utils import ensure_base_dir
from .config import load_config, override_llm_only_config, validate_tool_prompts, get_character_meta

DEFAULT_TIMEOUT_SECONDS = 60

app = FastAPI(title="Open-LLM-VTuber LLM-only Server")


def _history_exists(conf_uid: str, history_uid: str) -> bool:
    try:
        history_path = _get_safe_history_path(conf_uid, history_uid)
    except Exception as exc:
        logger.warning(f"Invalid history path: {exc}")
        return False
    return os.path.exists(history_path)


@app.on_event("startup")
async def on_startup() -> None:
    ensure_base_dir()
    config = load_config()
    config = override_llm_only_config(config)
    validate_tool_prompts(config)
    logger.info("LLM-only server initialized (ASR/TTS/VAD/Live2D disabled).")


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    LLM-only chat endpoint (stub).
    - Creates/validates history.
    - Stores user/assistant messages.
    - Returns stub response.
    """
    conf_uid = request.conf_uid.strip()
    history_uid = request.history_uid.strip() if request.history_uid else None
    text = request.text

    if history_uid and not _history_exists(conf_uid, history_uid):
        raise HTTPException(status_code=404, detail="history_not_found")

    if not history_uid:
        history_uid = create_new_history(conf_uid)

    config = override_llm_only_config(load_config())
    meta = get_character_meta(config)

    store_message(
        conf_uid=conf_uid,
        history_uid=history_uid,
        role="human",
        content=text,
        name=meta["human_name"],
    )

    # Stub response (Plan2 단계). LLM 호출은 Plan3에서 연결.
    assistant_text = f"[stub] {text}"

    store_message(
        conf_uid=conf_uid,
        history_uid=history_uid,
        role="ai",
        content=assistant_text,
        name=meta["character_name"],
        avatar=meta["avatar"],
    )

    return ChatResponse(history_uid=history_uid, text=assistant_text)
