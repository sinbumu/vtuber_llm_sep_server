from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from loguru import logger


@dataclass
class MCPComponents:
    tool_manager: "ToolManager"
    tool_executor: "ToolExecutor"
    mcp_client: "MCPClient"
    mcp_prompt_string: str


async def init_mcp_components(
    base_dir: Path, enabled_servers: List[str]
) -> Optional[MCPComponents]:
    """Initialize MCP components for LLM-only server (optional)."""
    if not enabled_servers:
        logger.warning("LLM-only server: MCP enabled but no servers configured.")
        return None

    config_path = base_dir / "mcp_servers.json"
    if not config_path.exists():
        logger.error(
            f"LLM-only server: MCP enabled but mcp_servers.json not found at {config_path}"
        )
        return None

    try:
        from open_llm_vtuber.mcpp.server_registry import ServerRegistry
        from open_llm_vtuber.mcpp.tool_adapter import ToolAdapter
        from open_llm_vtuber.mcpp.tool_manager import ToolManager
        from open_llm_vtuber.mcpp.tool_executor import ToolExecutor
        from open_llm_vtuber.mcpp.mcp_client import MCPClient
    except Exception as exc:
        logger.error(f"LLM-only server: MCP dependencies unavailable: {exc}")
        return None

    try:
        server_registry = ServerRegistry(config_path)
        tool_adapter = ToolAdapter(server_registery=server_registry)

        servers_info, raw_tools_dict = await tool_adapter.get_server_and_tool_info(
            enabled_servers
        )
        mcp_prompt_string = tool_adapter.construct_mcp_prompt_string(servers_info)
        openai_tools, claude_tools = tool_adapter.format_tools_for_api(raw_tools_dict)

        tool_manager = ToolManager(
            formatted_tools_openai=openai_tools,
            formatted_tools_claude=claude_tools,
            initial_tools_dict=raw_tools_dict,
        )
        mcp_client = MCPClient(server_registry)
        tool_executor = ToolExecutor(mcp_client, tool_manager)

        logger.info(
            "LLM-only server: MCP initialized with "
            f"{len(openai_tools)} OpenAI tools and {len(claude_tools)} Claude tools."
        )
        return MCPComponents(
            tool_manager=tool_manager,
            tool_executor=tool_executor,
            mcp_client=mcp_client,
            mcp_prompt_string=mcp_prompt_string,
        )
    except Exception as exc:
        logger.error(f"LLM-only server: MCP init failed: {exc}")
        return None
