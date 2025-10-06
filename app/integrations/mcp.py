from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from langchain_core.tools import BaseTool

try:  # pragma: no cover - import guard mirrors runtime dependency availability
    from langchain_mcp_adapters import MultiServerMCPClient  # type: ignore[attr-defined]
except ImportError:  # noqa: F401
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore[attr-defined]
    except ImportError:  # noqa: F401
        MultiServerMCPClient = None  # type: ignore[assignment]

from app.core.logging import logger


async def load_mcp_tools(
    servers_cfg: Dict[str, Any],
    allowed_tools: Optional[Iterable[str]] = None,
) -> List[BaseTool]:
    """Load MCP tools from the configured servers.

    Parameters
    ----------
    servers_cfg:
        Mapping of server aliases to their configuration dictionaries.
    allowed_tools:
        Optional iterable of tool names to retain. When omitted, all tools from the
        configured MCP servers are returned.
    """

    if not servers_cfg:
        return []

    whitelist = {tool_name for tool_name in (allowed_tools or []) if tool_name}

    if MultiServerMCPClient is None:
        logger.warning(
            "langchain-mcp-adapters is not available; ignoring MCP tool configuration"
        )
        return []

    try:
        client = MultiServerMCPClient(servers_cfg)
        tools = await client.get_tools()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load MCP tools", error=str(exc))
        return []

    if whitelist:
        filtered_tools = [
            tool
            for tool in tools
            if getattr(tool, "name", None) in whitelist
        ]
        return filtered_tools

    return tools
