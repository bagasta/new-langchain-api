from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from copy import deepcopy
from urllib.parse import urlsplit, urlunsplit

from langchain_core.tools import BaseTool
from httpx import HTTPStatusError

try:  # pragma: no cover - import guard mirrors runtime dependency availability
    from langchain_mcp_adapters import MultiServerMCPClient  # type: ignore[attr-defined]
except ImportError:  # noqa: F401
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore[attr-defined]
    except ImportError:  # noqa: F401
        MultiServerMCPClient = None  # type: ignore[assignment]

from app.core.logging import logger


class MCPConnectionError(RuntimeError):
    """Raised when MCP servers cannot be contacted or authenticated."""


TRANSPORT_ALIASES = {
    "streamable_http": "sse",
    "sse": "sse",
    "stdio": "stdio",
    "websocket": "websocket",
}


def _prepare_connections(raw_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise transports while keeping the user's configuration intact."""
    prepared: Dict[str, Any] = {}

    for alias, cfg in raw_cfg.items():
        if not isinstance(cfg, dict):
            logger.warning(
                "Skipping MCP server config because it is not a mapping",
                alias=alias,
                value_type=type(cfg).__name__,
            )
            continue

        config = deepcopy(cfg)
        transport_key = str(config.get("transport", "stdio")) or "stdio"
        transport = TRANSPORT_ALIASES.get(transport_key.lower())
        if not transport:
            logger.warning(
                "Unsupported MCP transport; skipping server",
                alias=alias,
                transport=transport_key,
            )
            continue

        config["transport"] = transport
        prepared[alias] = config

    return prepared


def _redact_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None

    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _append_sse_suffix(url: Optional[str]) -> Optional[str]:
    if not url:
        return None

    parts = urlsplit(url)
    path = parts.path or ""
    if path.rstrip("/").endswith("/sse"):
        return None

    base_path = path.rstrip("/")
    new_path = f"{base_path}/sse" if base_path else "/sse"
    return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))


async def _load_tools_for_alias(alias: str, config: Dict[str, Any]) -> List[BaseTool]:
    async def _connect(cfg: Dict[str, Any]) -> List[BaseTool]:
        async with MultiServerMCPClient({alias: cfg}) as client:
            return client.get_tools()

    try:
        return await _connect(config)
    except HTTPStatusError as exc:
        transport = (config.get("transport") or "").lower()
        redacted_url = _redact_url(config.get("url"))

        if transport == "sse" and exc.response.status_code == 404:
            fallback_url = _append_sse_suffix(config.get("url"))
            if fallback_url and fallback_url != config.get("url"):
                fallback_cfg = dict(config)
                fallback_cfg["url"] = fallback_url
                redacted_fallback = _redact_url(fallback_url)
                logger.info(
                    "Retrying MCP server with '/sse' suffix",
                    alias=alias,
                    url=redacted_fallback,
                )
                try:
                    tools = await _connect(fallback_cfg)
                    logger.info(
                        "Connected to MCP server using '/sse' suffix",
                        alias=alias,
                        url=redacted_fallback,
                    )
                    return tools
                except HTTPStatusError as retry_exc:
                    logger.warning(
                        "Fallback MCP request still failed",
                        alias=alias,
                        status_code=retry_exc.response.status_code,
                        url=redacted_fallback,
                    )
                    message = (
                        f"MCP server '{alias}' returned HTTP {retry_exc.response.status_code}"
                        + (f" for URL {redacted_fallback}." if redacted_fallback else ".")
                        + " Verify the n8n MCP trigger URL and ensure the workflow is active."
                    )
                    raise MCPConnectionError(message) from retry_exc
                except Exception as retry_exc:  # noqa: BLE001
                    logger.warning(
                        "Fallback MCP initialisation failed",
                        alias=alias,
                        error=str(retry_exc),
                    )
                    raise MCPConnectionError(
                        f"Failed to initialise MCP server '{alias}' via fallback '/sse' URL: {retry_exc}"
                    ) from retry_exc

        logger.warning(
            "MCP server responded with HTTP error",
            alias=alias,
            status_code=exc.response.status_code,
            url=redacted_url,
        )
        message = (
            f"MCP server '{alias}' returned HTTP {exc.response.status_code}"
            + (f" for URL {redacted_url}." if redacted_url else ".")
            + " Check the endpoint path, credentials, and networking configuration."
        )
        if exc.response.status_code == 404:
            message += " If this server is n8n, confirm the URL ends with the '/sse' trigger path."
        raise MCPConnectionError(message) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to initialise MCP server",
            alias=alias,
            error=str(exc),
        )
        raise MCPConnectionError(
            f"Failed to initialise MCP server '{alias}': {exc}"
        ) from exc


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
        prepared_cfg = _prepare_connections(servers_cfg)
        if not prepared_cfg:
            return []

        collected: List[BaseTool] = []
        for alias, config in prepared_cfg.items():
            collected.extend(await _load_tools_for_alias(alias, config))

        tools = collected
    except MCPConnectionError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load MCP tools", error=str(exc))
        return []

    if whitelist:
        filtered_tools = [
            tool
            for tool in tools
            if getattr(tool, "name", None) in whitelist
        ]

        missing_tools = whitelist - {
            getattr(tool, "name", "")
            for tool in tools
            if getattr(tool, "name", None)
        }
        if missing_tools:
            logger.warning(
                "Some MCP tools requested in allowed_tools were not found",
                missing=list(sorted(missing_tools)),
            )
        return filtered_tools

    return tools
