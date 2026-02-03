from __future__ import annotations

from typing import Any, Dict
from loguru import logger

from prompts import prompt_loader
from open_llm_vtuber.config_manager.utils import read_yaml


def load_config() -> Dict[str, Any]:
    """Load raw config from conf.yaml without engine initialization."""
    return read_yaml("conf.yaml")


def override_llm_only_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply LLM-only overrides to disable MCP and mem0."""
    config = dict(config or {})
    character_config = dict(config.get("character_config", {}))
    agent_config = dict(character_config.get("agent_config", {}))
    agent_settings = dict(agent_config.get("agent_settings", {}))
    basic_memory = dict(agent_settings.get("basic_memory_agent", {}))

    if basic_memory.get("use_mcpp", False):
        logger.warning("LLM-only server: forcing use_mcpp=false")
        basic_memory["use_mcpp"] = False

    agent_settings["basic_memory_agent"] = basic_memory
    agent_config["agent_settings"] = agent_settings

    if agent_config.get("conversation_agent_choice") == "mem0_agent":
        logger.warning("LLM-only server: forcing conversation_agent_choice=basic_memory_agent")
        agent_config["conversation_agent_choice"] = "basic_memory_agent"

    character_config["agent_config"] = agent_config
    config["character_config"] = character_config
    return config


def validate_tool_prompts(config: Dict[str, Any]) -> None:
    """Validate tool prompt files; log errors but never raise."""
    system_config = config.get("system_config", {})
    tool_prompts = system_config.get("tool_prompts", {}) if system_config else {}

    for prompt_name, prompt_file in tool_prompts.items():
        if not prompt_file:
            logger.warning(f"Tool prompt '{prompt_name}' is empty")
            continue
        try:
            prompt_loader.load_util(prompt_file)
        except FileNotFoundError:
            logger.error(
                f"Tool prompt file not found: prompts/utils/{prompt_file}.txt"
            )
        except Exception as exc:
            logger.error(f"Failed to load tool prompt '{prompt_name}': {exc}")


def get_character_meta(config: Dict[str, Any]) -> Dict[str, str]:
    """Return display meta for history storage."""
    character = config.get("character_config", {}) if config else {}
    return {
        "character_name": character.get("character_name", "AI"),
        "human_name": character.get("human_name", "Human"),
        "avatar": character.get("avatar", ""),
    }
