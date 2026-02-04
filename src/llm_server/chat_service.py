from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List

from loguru import logger
import sys

from open_llm_vtuber.agent.stateless_llm_factory import LLMFactory
from open_llm_vtuber.agent.input_types import BatchInput, TextData, TextSource
from open_llm_vtuber.agent.agents.basic_memory_agent import BasicMemoryAgent
from open_llm_vtuber.chat_history_manager import _get_safe_history_path
from .utils import get_base_dir


DEFAULT_LLM_TIMEOUT_SECONDS = 60


class LLMError(RuntimeError):
    """Raised when LLM invocation fails."""


class LLMTimeoutError(TimeoutError):
    """Raised when LLM invocation times out."""


def history_exists(conf_uid: str, history_uid: str) -> bool:
    """Check if history file exists."""
    try:
        history_path = _get_safe_history_path(conf_uid, history_uid)
    except Exception as exc:
        logger.warning(f"Invalid history path: {exc}")
        return False
    return history_path.exists()


def _build_system_prompt(
    persona_prompt: str, tool_prompts: Dict[str, str]
) -> str:
    """Build system prompt without Live2D dependency."""
    base_dir = get_base_dir()
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    try:
        from prompts import prompt_loader
    except Exception as exc:
        logger.error(f"Failed to import prompts: {exc}")
        return persona_prompt or ""

    system_prompt = persona_prompt or ""
    for prompt_name, prompt_file in (tool_prompts or {}).items():
        if prompt_name in {
            "group_conversation_prompt",
            "proactive_speak_prompt",
            "mcp_prompt",
        }:
            continue
        if prompt_name == "live2d_expression_prompt":
            logger.warning("LLM-only server: skipping live2d_expression_prompt")
            continue
        try:
            prompt_content = prompt_loader.load_util(prompt_file)
            system_prompt = f"{system_prompt}\n\n{prompt_content}"
        except FileNotFoundError:
            logger.error(
                f"Tool prompt file not found: prompts/utils/{prompt_file}.txt"
            )
        except Exception as exc:
            logger.error(f"Failed to load tool prompt '{prompt_name}': {exc}")
    return system_prompt


def _build_messages(
    text: str,
    conf_uid: str,
    history_uid: str,
    system_prompt: str,
    agent_config: Dict[str, Any],
) -> tuple[List[Dict[str, Any]], BasicMemoryAgent]:
    """Create BasicMemoryAgent and build messages array."""
    agent_settings = agent_config.get("agent_settings", {})
    llm_configs = agent_config.get("llm_configs", {})
    basic_memory_settings = agent_settings.get("basic_memory_agent", {})
    llm_provider = basic_memory_settings.get("llm_provider")
    llm_config = dict(llm_configs.get(llm_provider, {}))

    if not llm_provider or not llm_config:
        raise LLMError("LLM provider configuration missing")

    llm = LLMFactory.create_llm(
        llm_provider=llm_provider,
        system_prompt=system_prompt,
        **llm_config,
    )

    agent = BasicMemoryAgent(
        llm=llm,
        system=system_prompt,
        live2d_model=None,
        tts_preprocessor_config=None,
        faster_first_response=basic_memory_settings.get("faster_first_response", True),
        segment_method=basic_memory_settings.get("segment_method", "pysbd"),
        use_mcpp=False,
    )

    if history_uid:
        agent.set_memory_from_history(conf_uid, history_uid)

    batch_input = BatchInput(
        texts=[TextData(source=TextSource.INPUT, content=text, from_name="Human")],
        images=None,
        metadata=None,
    )

    messages = agent._to_messages(batch_input)
    return messages, agent


async def _collect_llm_response(
    llm, messages: List[Dict[str, Any]], system_prompt: str
) -> str:
    """Collect full text from streaming LLM."""
    output_text = ""
    async for event in llm.chat_completion(messages, system_prompt, tools=None):
        if isinstance(event, str):
            output_text += event
        elif isinstance(event, list):
            logger.warning("Tool calls received but tools are disabled")
            continue
    return output_text.strip()


async def run_chat_stream(
    conf_uid: str,
    history_uid: str,
    text: str,
    config: Dict[str, Any],
) -> tuple[str, AsyncIterator[str], BasicMemoryAgent]:
    """Run streaming chat and return history_uid + async iterator."""
    character_config = config.get("character_config", {})
    agent_config = character_config.get("agent_config", {})
    system_config = config.get("system_config", {})
    persona_prompt = character_config.get("persona_prompt", "")
    tool_prompts = system_config.get("tool_prompts", {})

    system_prompt = _build_system_prompt(persona_prompt, tool_prompts)

    messages, agent = _build_messages(
        text=text,
        conf_uid=conf_uid,
        history_uid=history_uid,
        system_prompt=system_prompt,
        agent_config=agent_config,
    )

    async def stream_iter() -> AsyncIterator[str]:
        try:
            async for event in agent._llm.chat_completion(
                messages, system_prompt, tools=None
            ):
                if isinstance(event, str):
                    yield event
                elif isinstance(event, list):
                    logger.warning("Tool calls received but tools are disabled")
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError("LLM request timed out") from exc
        except Exception as exc:
            raise LLMError("LLM request failed") from exc

    return history_uid, stream_iter(), agent


async def run_chat_once(
    conf_uid: str,
    history_uid: str,
    text: str,
    config: Dict[str, Any],
) -> str:
    """Run one-shot chat with LLM and return response text."""
    character_config = config.get("character_config", {})
    agent_config = character_config.get("agent_config", {})
    system_config = config.get("system_config", {})
    persona_prompt = character_config.get("persona_prompt", "")
    tool_prompts = system_config.get("tool_prompts", {})

    system_prompt = _build_system_prompt(persona_prompt, tool_prompts)

    messages, agent = _build_messages(
        text=text,
        conf_uid=conf_uid,
        history_uid=history_uid,
        system_prompt=system_prompt,
        agent_config=agent_config,
    )

    try:
        response_text = await asyncio.wait_for(
            _collect_llm_response(agent._llm, messages, system_prompt),
            timeout=DEFAULT_LLM_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise LLMTimeoutError("LLM request timed out") from exc
    except Exception as exc:
        raise LLMError("LLM request failed") from exc

    if not response_text:
        logger.warning("LLM returned empty response")
        return ""
    return response_text
