from __future__ import annotations

from pathlib import Path
import os
from loguru import logger


def get_base_dir() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def ensure_base_dir() -> Path:
    """Force current working directory to repository root."""
    base_dir = get_base_dir()
    try:
        os.chdir(base_dir)
    except Exception as exc:
        logger.error(f"Failed to set BASE_DIR: {exc}")
    return base_dir
