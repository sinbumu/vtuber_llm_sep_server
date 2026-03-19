from __future__ import annotations

import asyncio
import hashlib
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from loguru import logger

from open_llm_vtuber.agent.agents.basic_memory_agent import BasicMemoryAgent
from open_llm_vtuber.agent.stateless_llm_factory import LLMFactory
from open_llm_vtuber.agent.input_types import BatchInput, TextData, TextSource
from open_llm_vtuber.chat_history_manager import (
    _get_safe_history_path,
    get_history,
    get_metadata,
    update_metadate,
)

from .utils import get_base_dir
from .mcp_bridge import MCPComponents, init_mcp_components
from open_llm_vtuber.agent.output_types import SentenceOutput


DEFAULT_LLM_TIMEOUT_SECONDS = 60
SUMMARY_PROMPT = """You are a conversation memory compressor.

Merge the existing summary and the new conversation chunk into a compact running summary.
Keep only durable context that helps future replies:
- user preferences and constraints
- assistant promises or pending follow-ups
- important facts, goals, unresolved questions, and task progress
- stable relationship/context details

Drop filler small talk, repeated greetings, and low-value repetition.
Return plain text bullet points only.
Do not mention that this is a summary.
"""
SUMMARY_BLOCK_PREFIX = "Conversation summary so far:\n"
_SUMMARY_TASKS: dict[str, asyncio.Task[None]] = {}


class LLMError(RuntimeError):
    """Raised when LLM invocation fails."""


class LLMTimeoutError(TimeoutError):
    """Raised when LLM invocation times out."""


@dataclass(slots=True)
class ContextCompactionPolicy:
    """Configuration for context compaction behavior."""

    enabled: bool
    mode: str
    target_message_count: int
    trigger_message_count: int
    max_message_count: int
    min_messages_to_compact: int
    summarizer: str
    summarizer_model: str | None
    summarizer_timeout_sec: int


@dataclass(slots=True)
class SummaryPlan:
    """A pending summary compaction plan."""

    existing_summary: str
    pending_from_index: int
    pending_to_index: int
    pending_messages: list[dict[str, Any]]
    persona_hash: str


def history_exists(conf_uid: str, history_uid: str) -> bool:
    """Check if history file exists."""
    try:
        history_path = _get_safe_history_path(conf_uid, history_uid)
    except Exception as exc:
        logger.warning(f"Invalid history path: {exc}")
        return False
    return Path(history_path).exists()


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
        recent_message_window=basic_memory_settings.get(
            "recent_message_window",
            BasicMemoryAgent.DEFAULT_RECENT_MESSAGE_WINDOW,
        ),
    )

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


def _get_context_compaction_policy(config: Dict[str, Any]) -> ContextCompactionPolicy:
    """Parse context compaction policy from config."""
    character_config = config.get("character_config", {}) if config else {}
    agent_config = character_config.get("agent_config", {}) if character_config else {}
    agent_settings = agent_config.get("agent_settings", {}) if agent_config else {}
    basic_memory = agent_settings.get("basic_memory_agent", {}) if agent_settings else {}
    context_compaction = basic_memory.get("context_compaction", {}) or {}

    default_recent_window = int(
        basic_memory.get(
            "recent_message_window",
            BasicMemoryAgent.DEFAULT_RECENT_MESSAGE_WINDOW,
        )
    )
    max_message_count = max(
        1,
        int(context_compaction.get("max_message_count", default_recent_window)),
    )
    target_message_count = max(
        1,
        int(context_compaction.get("target_message_count", min(24, max_message_count))),
    )
    target_message_count = min(target_message_count, max_message_count)

    trigger_message_count = int(
        context_compaction.get("trigger_message_count", max(target_message_count + 4, 28))
    )
    trigger_message_count = max(target_message_count + 1, trigger_message_count)
    trigger_message_count = min(trigger_message_count, max_message_count)

    min_messages_to_compact = max(
        1, int(context_compaction.get("min_messages_to_compact", 4))
    )

    return ContextCompactionPolicy(
        enabled=bool(context_compaction.get("enabled", False)),
        mode=str(context_compaction.get("mode", "recent_window_only")),
        target_message_count=target_message_count,
        trigger_message_count=trigger_message_count,
        max_message_count=max_message_count,
        min_messages_to_compact=min_messages_to_compact,
        summarizer=str(context_compaction.get("summarizer", "same_llm")),
        summarizer_model=context_compaction.get("summarizer_model"),
        summarizer_timeout_sec=max(
            1, int(context_compaction.get("summarizer_timeout_sec", 15))
        ),
    )


def _compute_persona_hash(system_prompt: str) -> str:
    """Compute a stable hash for the active system prompt."""
    return hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()


def _get_active_summary(metadata: dict[str, Any], persona_hash: str) -> tuple[str, int]:
    """Return the active summary text and coverage range."""
    summary = metadata.get("summary", {}) if metadata else {}
    summary_text = str(summary.get("text") or "").strip()
    summary_upto_index = int(summary.get("summary_upto_index") or 0)
    stored_hash = summary.get("persona_hash")

    if stored_hash and stored_hash != persona_hash:
        logger.info("Ignoring stored summary because persona hash changed.")
        return "", 0

    return summary_text, summary_upto_index


def _append_summary_to_system_prompt(system_prompt: str, summary_text: str) -> str:
    """Append the stored summary to the active system prompt."""
    if not summary_text:
        return system_prompt
    return f"{system_prompt}\n\n{SUMMARY_BLOCK_PREFIX}{summary_text}"


def _convert_history_message_to_memory(message: dict[str, Any]) -> dict[str, Any] | None:
    """Convert history JSON entry to agent memory format."""
    role = message.get("role")
    content = message.get("content")
    if not isinstance(content, str) or not content:
        return None

    if role == "human":
        mapped_role = "user"
    elif role == "ai":
        mapped_role = "assistant"
    elif role == "system":
        mapped_role = "system"
    else:
        return None

    return {
        "role": mapped_role,
        "content": content,
    }


def _get_unsummarized_messages(
    history_messages: list[dict[str, Any]], summary_upto_index: int
) -> list[dict[str, Any]]:
    """Return messages not yet folded into summary."""
    return [
        message
        for message in history_messages
        if int(message.get("message_index", 0) or 0) > summary_upto_index
    ]


def _prepare_agent_context(
    agent: BasicMemoryAgent,
    conf_uid: str,
    history_uid: str,
    system_prompt: str,
    config: Dict[str, Any],
) -> str:
    """Load history into the agent using the active compaction policy."""
    if not history_uid:
        agent.set_system(system_prompt)
        return system_prompt

    policy = _get_context_compaction_policy(config)
    if not policy.enabled or policy.mode != "summary_recent_window":
        agent.set_memory_from_history(conf_uid, history_uid)
        agent.set_system(system_prompt)
        return system_prompt

    metadata = get_metadata(conf_uid, history_uid)
    history_messages = get_history(conf_uid, history_uid)
    persona_hash = _compute_persona_hash(system_prompt)
    summary_text, summary_upto_index = _get_active_summary(metadata, persona_hash)
    unsummarized_messages = _get_unsummarized_messages(history_messages, summary_upto_index)
    live_messages = unsummarized_messages[-policy.max_message_count :]

    agent._memory = [
        converted
        for message in live_messages
        if (converted := _convert_history_message_to_memory(message)) is not None
    ]
    agent._recent_message_window = 0
    effective_system_prompt = _append_summary_to_system_prompt(system_prompt, summary_text)
    agent.set_system(effective_system_prompt)
    return effective_system_prompt


def _build_summary_task_key(conf_uid: str, history_uid: str) -> str:
    """Build a unique in-memory task key for summary jobs."""
    return f"{conf_uid}:{history_uid}"


def _build_summary_user_prompt(
    existing_summary: str, pending_messages: list[dict[str, Any]]
) -> str:
    """Build the user message for summary generation."""
    lines = ["Existing summary:", existing_summary or "(none)", "", "New messages:"]
    for message in pending_messages:
        message_index = message.get("message_index")
        role = message.get("role")
        content = str(message.get("content") or "").strip()
        lines.append(f"[{message_index}] {role}: {content}")
    return "\n".join(lines).strip()


def _build_summary_plan(
    conf_uid: str,
    history_uid: str,
    policy: ContextCompactionPolicy,
    persona_hash: str,
) -> SummaryPlan | None:
    """Plan the next summary job if thresholds are met."""
    metadata = get_metadata(conf_uid, history_uid)
    history_messages = get_history(conf_uid, history_uid)
    existing_summary, summary_upto_index = _get_active_summary(metadata, persona_hash)
    unsummarized_messages = _get_unsummarized_messages(history_messages, summary_upto_index)

    if len(unsummarized_messages) < policy.trigger_message_count:
        return None

    compact_count = len(unsummarized_messages) - policy.target_message_count
    if compact_count < policy.min_messages_to_compact:
        return None

    pending_messages = unsummarized_messages[:compact_count]
    if not pending_messages:
        return None

    return SummaryPlan(
        existing_summary=existing_summary,
        pending_from_index=int(pending_messages[0]["message_index"]),
        pending_to_index=int(pending_messages[-1]["message_index"]),
        pending_messages=pending_messages,
        persona_hash=persona_hash,
    )


def _build_summary_llm(config: Dict[str, Any], policy: ContextCompactionPolicy):
    """Build the LLM used for summary generation."""
    character_config = config.get("character_config", {})
    agent_config = character_config.get("agent_config", {})
    agent_settings = agent_config.get("agent_settings", {})
    basic_memory = agent_settings.get("basic_memory_agent", {})
    llm_provider = basic_memory.get("llm_provider")
    llm_configs = agent_config.get("llm_configs", {})
    llm_config = dict(llm_configs.get(llm_provider, {}))

    if not llm_provider or not llm_config:
        raise LLMError("LLM provider configuration missing for summarizer")

    if policy.summarizer != "same_llm":
        logger.warning(
            f"Unsupported summarizer '{policy.summarizer}', falling back to same_llm."
        )

    if policy.summarizer_model:
        llm_config["model"] = policy.summarizer_model

    return LLMFactory.create_llm(
        llm_provider=llm_provider,
        system_prompt=SUMMARY_PROMPT,
        **llm_config,
    )


async def _generate_summary_text(
    config: Dict[str, Any],
    policy: ContextCompactionPolicy,
    plan: SummaryPlan,
) -> str:
    """Generate new summary text for a compacted history chunk."""
    llm = _build_summary_llm(config, policy)
    messages = [
        {
            "role": "user",
            "content": _build_summary_user_prompt(
                plan.existing_summary,
                plan.pending_messages,
            ),
        }
    ]
    summary_text = await asyncio.wait_for(
        _collect_llm_response(llm, messages, SUMMARY_PROMPT),
        timeout=policy.summarizer_timeout_sec,
    )
    summary_text = summary_text.strip()
    if not summary_text:
        raise LLMError("Summary generation returned empty text")
    return summary_text


async def _run_summary_job(
    conf_uid: str,
    history_uid: str,
    config: Dict[str, Any],
    policy: ContextCompactionPolicy,
    plan: SummaryPlan,
) -> None:
    """Run a single summary job and persist the result."""
    try:
        update_metadate(
            conf_uid,
            history_uid,
            {
                "summary_job": {
                    "status": "running",
                    "started_at": datetime.now().isoformat(timespec="seconds"),
                    "last_error": None,
                }
            },
        )
        summary_text = await _generate_summary_text(config, policy, plan)
        update_metadate(
            conf_uid,
            history_uid,
            {
                "summary": {
                    "text": summary_text,
                    "summary_upto_index": plan.pending_to_index,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                    "source_message_range": {
                        "start": plan.pending_from_index,
                        "end": plan.pending_to_index,
                    },
                    "persona_hash": plan.persona_hash,
                    "version": 1,
                },
                "summary_job": {
                    "status": "succeeded",
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                    "last_error": None,
                    "pending_from_index": None,
                    "pending_to_index": None,
                },
            },
        )
    except Exception as exc:
        logger.error(f"Summary job failed for {history_uid}: {exc}")
        update_metadate(
            conf_uid,
            history_uid,
            {
                "summary_job": {
                    "status": "failed",
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                    "last_error": str(exc),
                }
            },
        )


def queue_summary_job(conf_uid: str, history_uid: str, config: Dict[str, Any]) -> None:
    """Queue a summary job if compaction thresholds are met."""
    policy = _get_context_compaction_policy(config)
    if not policy.enabled or policy.mode != "summary_recent_window":
        return

    character_config = config.get("character_config", {})
    system_config = config.get("system_config", {})
    persona_prompt = character_config.get("persona_prompt", "")
    tool_prompts = system_config.get("tool_prompts", {})
    enable_mcp, _ = _get_mcp_settings(config)
    system_prompt = _build_system_prompt(persona_prompt, tool_prompts, enable_mcp)
    persona_hash = _compute_persona_hash(system_prompt)

    plan = _build_summary_plan(conf_uid, history_uid, policy, persona_hash)
    if not plan:
        return

    task_key = _build_summary_task_key(conf_uid, history_uid)
    existing_task = _SUMMARY_TASKS.get(task_key)
    if existing_task and not existing_task.done():
        return

    update_metadate(
        conf_uid,
        history_uid,
        {
            "summary_job": {
                "status": "queued",
                "requested_at": datetime.now().isoformat(timespec="seconds"),
                "pending_from_index": plan.pending_from_index,
                "pending_to_index": plan.pending_to_index,
                "last_error": None,
            }
        },
    )

    task = asyncio.create_task(
        _run_summary_job(
            conf_uid=conf_uid,
            history_uid=history_uid,
            config=config,
            policy=policy,
            plan=plan,
        )
    )
    _SUMMARY_TASKS[task_key] = task
    task.add_done_callback(lambda _: _SUMMARY_TASKS.pop(task_key, None))


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
    effective_system_prompt = _prepare_agent_context(
        agent=agent,
        conf_uid=conf_uid,
        history_uid=history_uid,
        system_prompt=system_prompt,
        config=config,
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
                    messages, effective_system_prompt, tools=None
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
    effective_system_prompt = _prepare_agent_context(
        agent=agent,
        conf_uid=conf_uid,
        history_uid=history_uid,
        system_prompt=system_prompt,
        config=config,
    )
    batch_input = _build_batch_input(text)
    messages = agent._to_messages(batch_input)

    try:
        if enable_mcp:
            response_text = await _collect_agent_response(agent, batch_input)
        else:
            response_text = await asyncio.wait_for(
                _collect_llm_response(agent._llm, messages, effective_system_prompt),
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
