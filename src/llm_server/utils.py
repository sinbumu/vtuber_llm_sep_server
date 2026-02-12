from __future__ import annotations

from pathlib import Path
import os
import sys
from loguru import logger


def get_base_dir() -> Path:
    """Return repository root directory."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parents[2]


def ensure_base_dir() -> Path:
    """Force current working directory to repository root."""
    base_dir = get_base_dir()
    try:
        os.chdir(base_dir)
        if str(base_dir) not in sys.path:
            sys.path.insert(0, str(base_dir))
    except Exception as exc:
        logger.error(f"Failed to set BASE_DIR: {exc}")
    return base_dir
