from __future__ import annotations

import os
import sys
from typing import Any, Dict

from loguru import logger

from .utils import get_base_dir, get_runtime_dir
from open_llm_vtuber.config_manager.utils import read_yaml, validate_config


RUNTIME_RELOAD_SUPPORTED_FIELDS = [
    "character_config.persona_prompt",
    "system_config.tool_prompts",
    "character_config.character_name",
    "character_config.human_name",
    "character_config.avatar",
    "character_config.agent_config.agent_settings.basic_memory_agent.llm_provider",
    "character_config.agent_config.agent_settings.basic_memory_agent.faster_first_response",
    "character_config.agent_config.agent_settings.basic_memory_agent.segment_method",
    "character_config.agent_config.agent_settings.basic_memory_agent.mcp_enabled_servers",
    "character_config.agent_config.llm_configs.*",
    "prompts/utils/*.txt",
    "mcp_servers.json (when MCP is already enabled)",
]

RESTART_REQUIRED_FIELDS = [
    "LLM_SERVER_HOST",
    "LLM_SERVER_PORT",
    "LLM_SERVER_LOG_LEVEL",
    "LLM_SERVER_ENABLE_MCP",
    "LLM_SERVER_CONFIG_PATH",
]


def resolve_config_path() -> str:
    """Resolve the active config path with external-file priority.

    Resolution order:
    1. `LLM_SERVER_CONFIG_PATH`
    2. `<runtime_dir>/conf.yaml`
    3. `<base_dir>/conf.yaml`

    Returns:
        The resolved config path as a string.

    Raises:
        FileNotFoundError: If no valid config file is found.
    """
    runtime_dir = get_runtime_dir()
    base_dir = get_base_dir()
    configured_path = os.getenv("LLM_SERVER_CONFIG_PATH")

    candidates: list[str] = []
    if configured_path:
        if os.path.isabs(configured_path):
            candidates.append(configured_path)
        else:
            candidates.append(str((runtime_dir / configured_path).resolve()))

    candidates.append(str((runtime_dir / "conf.yaml").resolve()))
    candidates.append(str((base_dir / "conf.yaml").resolve()))

    seen: set[str] = set()
    for candidate in candidates:
        normalized = os.path.normcase(os.path.normpath(candidate))
        if normalized in seen:
            continue
        seen.add(normalized)
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError(
        "No configuration file found. Checked: " + ", ".join(candidates)
    )


def load_config() -> Dict[str, Any]:
    """Load raw config from the resolved config path without engine initialization."""
    return read_yaml(resolve_config_path())


def override_llm_only_config(
    config: Dict[str, Any], enable_mcp: bool = False
) -> Dict[str, Any]:
    """Apply LLM-only overrides (optionally enable MCP)."""
    config = dict(config or {})
    character_config = dict(config.get("character_config", {}))
    agent_config = dict(character_config.get("agent_config", {}))
    agent_settings = dict(agent_config.get("agent_settings", {}))
    basic_memory = dict(agent_settings.get("basic_memory_agent", {}))

    if enable_mcp:
        if not basic_memory.get("use_mcpp", False):
            logger.info("LLM-only server: enabling MCP (use_mcpp=true)")
        basic_memory["use_mcpp"] = True
    else:
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
    llm_server_config = dict(config.get("llm_server", {}))
    llm_server_config["mcp_enabled"] = enable_mcp
    config["llm_server"] = llm_server_config
    return config


def validate_tool_prompts(config: Dict[str, Any]) -> None:
    """Validate tool prompt files; log errors but never raise."""
    base_dir = get_base_dir()
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    try:
        from prompts import prompt_loader
    except Exception as exc:
        logger.error(f"Failed to import prompts: {exc}")
        return

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


def _mask_sensitive_values(value: Any) -> Any:
    """Mask sensitive values in nested config structures.

    Args:
        value: Arbitrary config value.

    Returns:
        Config value with sensitive fields masked.
    """
    sensitive_markers = ("api_key", "token", "secret", "password")

    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, nested_value in value.items():
            if any(marker in key.lower() for marker in sensitive_markers):
                if nested_value:
                    masked[key] = "***"
                else:
                    masked[key] = nested_value
            else:
                masked[key] = _mask_sensitive_values(nested_value)
        return masked

    if isinstance(value, list):
        return [_mask_sensitive_values(item) for item in value]

    return value


def _collect_tool_prompt_warnings(config: Dict[str, Any]) -> list[str]:
    """Collect prompt validation warnings without raising.

    Args:
        config: Effective config dictionary.

    Returns:
        A list of human-readable warning messages.
    """
    warnings: list[str] = []
    base_dir = get_base_dir()
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))

    try:
        from prompts import prompt_loader
    except Exception as exc:
        return [f"Failed to import prompts: {exc}"]

    system_config = config.get("system_config", {}) if config else {}
    tool_prompts = system_config.get("tool_prompts", {}) if system_config else {}

    for prompt_name, prompt_file in tool_prompts.items():
        if not prompt_file:
            warnings.append(f"Tool prompt '{prompt_name}' is empty")
            continue
        try:
            prompt_loader.load_util(prompt_file)
        except FileNotFoundError:
            warnings.append(
                f"Tool prompt file not found: prompts/utils/{prompt_file}.txt"
            )
        except Exception as exc:
            warnings.append(f"Failed to load tool prompt '{prompt_name}': {exc}")

    return warnings


def _build_unity_config_summary(
    effective_config: Dict[str, Any], enable_mcp: bool
) -> Dict[str, Any]:
    """Build a compact config summary suitable for Unity DTOs.

    Args:
        effective_config: Effective config after overrides.
        enable_mcp: Whether MCP is enabled at process runtime.

    Returns:
        Compact summary dictionary.
    """
    character_config = effective_config.get("character_config", {})
    agent_config = character_config.get("agent_config", {})
    agent_settings = agent_config.get("agent_settings", {})
    basic_memory = agent_settings.get("basic_memory_agent", {})
    llm_provider = basic_memory.get("llm_provider")
    llm_configs = agent_config.get("llm_configs", {})
    llm_config = llm_configs.get(llm_provider, {}) if llm_provider else {}
    system_config = effective_config.get("system_config", {})
    persona_prompt = character_config.get("persona_prompt", "") or ""

    return {
        "character": {
            "confName": character_config.get("conf_name"),
            "confUid": character_config.get("conf_uid"),
            "characterName": character_config.get("character_name"),
            "humanName": character_config.get("human_name"),
            "avatar": character_config.get("avatar"),
        },
        "llm": {
            "provider": llm_provider,
            "model": llm_config.get("model"),
            "baseUrl": llm_config.get("base_url"),
            "temperature": llm_config.get("temperature"),
            "apiKeyConfigured": bool(llm_config.get("llm_api_key")),
        },
        "conversation": {
            "fasterFirstResponse": basic_memory.get("faster_first_response"),
            "segmentMethod": basic_memory.get("segment_method"),
            "mcpEnabled": enable_mcp,
            "mcpEnabledServers": basic_memory.get("mcp_enabled_servers", []),
        },
        "prompts": {
            "personaPromptLength": len(persona_prompt),
            "toolPrompts": system_config.get("tool_prompts", {}),
        },
    }


def get_current_config_report(enable_mcp: bool) -> Dict[str, Any]:
    """Build a safe summary of the current effective config.

    Args:
        enable_mcp: Whether MCP is enabled at process runtime.

    Returns:
        Safe config summary for admin APIs.
    """
    raw_config = load_config()
    effective_config = override_llm_only_config(raw_config, enable_mcp=enable_mcp)

    return {
        "status": "ok",
        "configPath": resolve_config_path(),
        "process": {
            "host": os.getenv("LLM_SERVER_HOST", "127.0.0.1"),
            "port": int(os.getenv("LLM_SERVER_PORT", "8000")),
            "log_level": os.getenv("LLM_SERVER_LOG_LEVEL", "info"),
        },
        "configSummary": _build_unity_config_summary(effective_config, enable_mcp),
        "reloadPolicy": {
            "runtimeAppliedOnNextRequest": RUNTIME_RELOAD_SUPPORTED_FIELDS,
            "restartRequired": RESTART_REQUIRED_FIELDS,
        },
    }


def reload_config_report(enable_mcp: bool) -> Dict[str, Any]:
    """Validate config reloadability and return an admin report.

    Args:
        enable_mcp: Whether MCP is enabled at process runtime.

    Returns:
        Result dictionary describing what can be applied now vs restart.
    """
    errors: list[str] = []

    try:
        raw_config = load_config()
        effective_config = override_llm_only_config(raw_config, enable_mcp=enable_mcp)
        validate_config(effective_config)
    except Exception as exc:
        errors.append(str(exc))
        effective_config = {}

    warnings = _collect_tool_prompt_warnings(effective_config) if effective_config else []

    return {
        "status": "ok" if not errors else "error",
        "success": not errors,
        "message": (
            "Config validated. Runtime-supported changes will apply on the next request."
            if not errors
            else "Config reload validation failed."
        ),
        "configPath": resolve_config_path() if not errors else None,
        "runtimeAppliedOnNextRequest": RUNTIME_RELOAD_SUPPORTED_FIELDS,
        "restartRequired": RESTART_REQUIRED_FIELDS,
        "warnings": warnings,
        "errors": errors,
        "configSummary": (
            _build_unity_config_summary(effective_config, enable_mcp)
            if not errors
            else None
        ),
    }
