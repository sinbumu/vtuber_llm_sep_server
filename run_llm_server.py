"""Executable entrypoint for the LLM-only server."""

from __future__ import annotations

import os
import sys

import uvicorn


def _get_port(value: str | None, default: int = 8000) -> int:
    """Parse port from string with fallback.

    Args:
        value: Raw port string from environment.
        default: Fallback port when parsing fails.

    Returns:
        Parsed port as integer.
    """
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def main() -> None:
    """Run the FastAPI server via uvicorn.

    Args:
        None

    Returns:
        None
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS
        src_dir = os.path.join(base_dir, "src")
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

    from llm_server.utils import ensure_base_dir

    ensure_base_dir()
    host = os.getenv("LLM_SERVER_HOST", "127.0.0.1")
    port = _get_port(os.getenv("LLM_SERVER_PORT"), 8000)
    log_level = os.getenv("LLM_SERVER_LOG_LEVEL", "info")

    app_dir = None if getattr(sys, "frozen", False) else "src"

    from llm_server.app import app

    uvicorn.run(
        app,
        app_dir=app_dir,
        host=host,
        port=port,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
