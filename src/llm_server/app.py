from __future__ import annotations

from fastapi import FastAPI, HTTPException
from loguru import logger

from open_llm_vtuber.chat_history_manager import create_new_history, store_message

from .models import ChatRequest, ChatResponse
from .utils import ensure_base_dir
from .config import load_config, override_llm_only_config, validate_tool_prompts, get_character_meta
from .chat_service import run_chat_once, history_exists, LLMError, LLMTimeoutError

app = FastAPI(title="Open-LLM-VTuber LLM-only Server")


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
    LLM-only chat endpoint.
    - Creates/validates history.
    - Stores user/assistant messages.
    - Calls LLM (one-shot) and returns response.
    """
    conf_uid = request.conf_uid.strip()
    history_uid = request.history_uid.strip() if request.history_uid else None
    text = request.text

    if history_uid and not history_exists(conf_uid, history_uid):
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

    try:
        assistant_text = await run_chat_once(
            conf_uid=conf_uid,
            history_uid=history_uid,
            text=text,
            config=config,
        )
    except LLMTimeoutError as exc:
        logger.error(f"LLM timeout: {exc}")
        raise HTTPException(status_code=502, detail="llm_timeout")
    except LLMError as exc:
        logger.error(f"LLM error: {exc}")
        raise HTTPException(status_code=502, detail="llm_error")
    except Exception as exc:
        logger.error(f"Unexpected LLM failure: {exc}")
        raise HTTPException(status_code=502, detail="llm_error")

    store_message(
        conf_uid=conf_uid,
        history_uid=history_uid,
        role="ai",
        content=assistant_text,
        name=meta["character_name"],
        avatar=meta["avatar"],
    )

    return ChatResponse(history_uid=history_uid, text=assistant_text)
