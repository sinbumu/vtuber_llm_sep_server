from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional

from loguru import logger
import sys

from open_llm_vtuber.agent.stateless_llm_factory import LLMFactory
from open_llm_vtuber.agent.input_types import BatchInput, TextData, TextSource
from open_llm_vtuber.agent.agents.basic_memory_agent import BasicMemoryAgent
from open_llm_vtuber.chat_history_manager import _get_safe_history_path
from .utils import get_base_dir
from .mcp_bridge import MCPComponents, init_mcp_components
from open_llm_vtuber.agent.output_types import SentenceOutput


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
    persona_prompt: str,
    tool_prompts: Dict[str, str],
    enable_mcp: bool,
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
        }:
            continue
        if prompt_name == "mcp_prompt" and not enable_mcp:
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


def _build_agent(
    conf_uid: str,
    history_uid: str,
    system_prompt: str,
    agent_config: Dict[str, Any],
    tool_prompts: Dict[str, str],
    use_mcpp: bool,
    mcp_components: Optional[MCPComponents],
) -> BasicMemoryAgent:
    """Create BasicMemoryAgent with optional MCP support."""
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
        use_mcpp=use_mcpp,
        tool_prompts=tool_prompts,
        tool_manager=mcp_components.tool_manager if mcp_components else None,
        tool_executor=mcp_components.tool_executor if mcp_components else None,
        mcp_prompt_string=mcp_components.mcp_prompt_string if mcp_components else "",
    )

    if history_uid:
        agent.set_memory_from_history(conf_uid, history_uid)

    return agent


def _build_batch_input(text: str) -> BatchInput:
    return BatchInput(
        texts=[TextData(source=TextSource.INPUT, content=text, from_name="Human")],
        images=None,
        metadata=None,
    )


def _extract_text_chunk(output: Any) -> Optional[str]:
    if isinstance(output, str):
        return output
    if isinstance(output, SentenceOutput):
        return output.display_text.text
    if isinstance(output, dict) and output.get("type") == "text_delta":
        return output.get("text", "")
    return None


def _get_mcp_settings(config: Dict[str, Any]) -> tuple[bool, List[str]]:
    llm_server = config.get("llm_server", {}) if config else {}
    enable_mcp = bool(llm_server.get("mcp_enabled", False))
    character_config = config.get("character_config", {}) if config else {}
    agent_config = character_config.get("agent_config", {}) if character_config else {}
    agent_settings = agent_config.get("agent_settings", {}) if agent_config else {}
    basic_memory = agent_settings.get("basic_memory_agent", {}) if agent_settings else {}
    enabled_servers = list(basic_memory.get("mcp_enabled_servers", []) or [])
    return enable_mcp, enabled_servers


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


async def _collect_agent_response(agent: BasicMemoryAgent, batch_input: BatchInput) -> str:
    output_text = ""
    async for output in agent.chat(batch_input):
        chunk = _extract_text_chunk(output)
        if chunk:
            output_text += chunk
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

    enable_mcp, enabled_servers = _get_mcp_settings(config)
    mcp_components = None
    if enable_mcp:
        mcp_components = await init_mcp_components(get_base_dir(), enabled_servers)
        if not mcp_components:
            logger.warning("LLM-only server: MCP init failed, falling back to no-MCP.")
            enable_mcp = False

    system_prompt = _build_system_prompt(persona_prompt, tool_prompts, enable_mcp)

    agent = _build_agent(
        conf_uid=conf_uid,
        history_uid=history_uid,
        system_prompt=system_prompt,
        agent_config=agent_config,
        tool_prompts=tool_prompts,
        use_mcpp=enable_mcp,
        mcp_components=mcp_components,
    )
    batch_input = _build_batch_input(text)
    messages = agent._to_messages(batch_input)

    async def stream_iter() -> AsyncIterator[str]:
        try:
            if enable_mcp:
                async for output in agent.chat(batch_input):
                    chunk = _extract_text_chunk(output)
                    if chunk:
                        yield chunk
            else:
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
        finally:
            if mcp_components:
                await mcp_components.mcp_client.aclose()

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

    enable_mcp, enabled_servers = _get_mcp_settings(config)
    mcp_components = None
    if enable_mcp:
        mcp_components = await init_mcp_components(get_base_dir(), enabled_servers)
        if not mcp_components:
            logger.warning("LLM-only server: MCP init failed, falling back to no-MCP.")
            enable_mcp = False

    system_prompt = _build_system_prompt(persona_prompt, tool_prompts, enable_mcp)

    agent = _build_agent(
        conf_uid=conf_uid,
        history_uid=history_uid,
        system_prompt=system_prompt,
        agent_config=agent_config,
        tool_prompts=tool_prompts,
        use_mcpp=enable_mcp,
        mcp_components=mcp_components,
    )
    batch_input = _build_batch_input(text)
    messages = agent._to_messages(batch_input)

    try:
        if enable_mcp:
            response_text = await _collect_agent_response(agent, batch_input)
        else:
            response_text = await asyncio.wait_for(
                _collect_llm_response(agent._llm, messages, system_prompt),
                timeout=DEFAULT_LLM_TIMEOUT_SECONDS,
            )
    except asyncio.TimeoutError as exc:
        raise LLMTimeoutError("LLM request timed out") from exc
    except Exception as exc:
        raise LLMError("LLM request failed") from exc
    finally:
        if mcp_components:
            await mcp_components.mcp_client.aclose()

    if not response_text:
        logger.warning("LLM returned empty response")
        return ""
    return response_text
