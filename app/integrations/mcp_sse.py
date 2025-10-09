from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from httpx import HTTPStatusError
from langchain_core.tools import BaseTool

try:  # pragma: no cover - optional dependency
    from langchain_mcp_adapters import MultiServerMCPClient  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - fallback import layout
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore[attr-defined]
    except ImportError as exc:  # pragma: no cover
        MultiServerMCPClient = None  # type: ignore[assignment]

from app.core.logging import logger


class MCPClientError(RuntimeError):
    """Raised when MCP clients cannot be initialised or contacted."""


class MCPHTTPClientError(MCPClientError):
    """Raised when MCP streamable HTTP clients cannot be initialised or contacted."""


class MCPSSEClientError(MCPClientError):
    """Raised when MCP SSE clients cannot be initialised or contacted."""


def build_sse_connection_config(
    base_url: str,
    token: Optional[str],
) -> Mapping[str, object]:
    """Construct the configuration expected by MultiServerMCPClient."""
    if base_url.endswith("/mcp/sse"):
        sse_url = base_url
    else:
        sse_url = f"{base_url.rstrip('/')}/mcp/sse"

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    config: dict[str, object] = {
        "transport": "sse",
        "url": sse_url,
    }

    if headers:
        config["headers"] = headers

    return config


def build_http_connection_config(
    base_url: str,
    token: Optional[str],
) -> Mapping[str, object]:
    url = base_url.rstrip("/") + "/"

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    config: dict[str, object] = {
        "transport": "streamable_http",
        "url": url,
    }

    if headers:
        config["headers"] = headers

    return config


def _sanitize_connection_config(
    alias: str, raw_config: Mapping[str, Any]
) -> Dict[str, Any]:
    """Remove unsupported keys and defaults before creating MCP sessions."""
    if not isinstance(raw_config, Mapping):
        raise MCPClientError(
            f"Invalid MCP connection configuration for '{alias}': expected a mapping"
        )

    sanitized: Dict[str, Any] = {}
    for key, value in raw_config.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, tuple, set)) and not value:
            continue
        if isinstance(value, Mapping) and not value:
            continue
        sanitized[key] = value

    transport: Optional[str]
    transport_raw = sanitized.get("transport")
    if isinstance(transport_raw, str) and transport_raw.strip():
        transport = transport_raw.lower()
    else:
        url_value = sanitized.get("url")
        if isinstance(url_value, str):
            normalized_url = url_value.rstrip("/").lower()
            if normalized_url.endswith("/mcp/sse"):
                transport = "sse"
            else:
                transport = "streamable_http"
        elif "command" in sanitized or "args" in sanitized:
            transport = "stdio"
        else:
            transport = "streamable_http"

    sanitized["transport"] = transport

    url_value = sanitized.get("url")
    if transport in {"streamable_http", "sse"}:
        for key in ("env", "cwd", "command", "args", "encoding", "encoding_error_handler"):
            sanitized.pop(key, None)
        if isinstance(url_value, str):
            normalized = url_value.rstrip("/")
            if transport == "sse":
                if normalized.endswith("/mcp/stream"):
                    normalized = normalized[: -len("/mcp/stream")]
                if not normalized.endswith("/mcp/sse"):
                    normalized = f"{normalized}/mcp/sse"
                sanitized["url"] = normalized
            else:  # streamable_http
                if normalized.endswith("/mcp/sse"):
                    normalized = normalized[: -len("/mcp/sse")]
                if not normalized.endswith("/"):
                    normalized = normalized + "/"
                if not normalized.endswith("/mcp/stream/"):
                    normalized = normalized.rstrip("/") + "/mcp/stream"
                sanitized["url"] = normalized.rstrip("/")
        if "url" not in sanitized or not isinstance(sanitized["url"], str):
            raise MCPClientError(
                f"MCP server '{alias}' configuration requires a valid URL for {transport} transport"
            )
    elif transport == "stdio":
        sanitized.pop("url", None)
        sanitized.pop("headers", None)
        if not sanitized.get("command"):
            raise MCPClientError(
                f"MCP server '{alias}' configuration requires a command for stdio transport"
            )
    else:
        raise MCPClientError(
            f"Unsupported transport '{transport}' in MCP server '{alias}' configuration"
        )

    return sanitized


async def load_mcp_sse_tools(
    base_url: Optional[str],
    token: Optional[str] = None,
    allowed_tools: Optional[Iterable[str]] = None,
    alias: str = "mcp_sse",
) -> List[BaseTool]:
    """Load tools from an MCP server reachable over SSE transport."""
    if not base_url:
        return []

    if MultiServerMCPClient is None:
        logger.warning(
            "langchain-mcp-adapters is not installed; skipping MCP SSE integration"
        )
        return []

    server_cfg = _sanitize_connection_config(
        alias,
        build_sse_connection_config(base_url, token),
    )
    whitelist = {tool for tool in (allowed_tools or []) if tool}

    logger.debug("Connecting to MCP SSE server", alias=alias, url=server_cfg.get("url"))

    client = MultiServerMCPClient({alias: server_cfg})
    try:
        tools = await client.get_tools(server_name=alias)
        logger.debug(
            "Received tool metadata from MCP SSE server",
            alias=alias,
            tool_names=[getattr(tool, "name", "") for tool in tools],
        )
    except HTTPStatusError as exc:
        logger.warning(
            "MCP SSE server responded with HTTP error",
            alias=alias,
            status_code=exc.response.status_code,
            url=server_cfg.get("url"),
        )
        raise MCPSSEClientError(
            f"MCP SSE server '{alias}' returned HTTP {exc.response.status_code}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to initialise MCP SSE server",
            alias=alias,
            error=str(exc),
        )
        raise MCPSSEClientError(
            f"Failed to initialise MCP SSE server '{alias}': {exc}"
        ) from exc

    if whitelist:
        filtered = [tool for tool in tools if getattr(tool, "name", None) in whitelist]
        missing = whitelist - {getattr(tool, "name", "") for tool in tools}
        if missing:
            logger.info(
                "Some MCP SSE tools requested in configuration were not found",
                missing=list(sorted(missing)),
            )
        return filtered

    return tools


async def load_mcp_streamable_http_tools(
    base_url: Optional[str],
    token: Optional[str] = None,
    allowed_tools: Optional[Iterable[str]] = None,
    alias: str = "mcp_http",
) -> List[BaseTool]:
    """Load tools from an MCP server reachable over streamable HTTP transport."""
    if not base_url:
        return []

    if MultiServerMCPClient is None:
        logger.warning(
            "langchain-mcp-adapters is not installed; skipping MCP HTTP integration"
        )
        return []

    server_cfg = _sanitize_connection_config(
        alias,
        build_http_connection_config(base_url, token),
    )
    whitelist = {tool for tool in (allowed_tools or []) if tool}

    logger.debug(
        "Connecting to MCP HTTP server",
        alias=alias,
        url=server_cfg.get("url"),
    )

    client = MultiServerMCPClient({alias: server_cfg})
    try:
        tools = await client.get_tools(server_name=alias)
        logger.debug(
            "Received tool metadata from MCP HTTP server",
            alias=alias,
            tool_names=[getattr(tool, "name", "") for tool in tools],
        )
    except HTTPStatusError as exc:
        logger.warning(
            "MCP HTTP server responded with HTTP error",
            alias=alias,
            status_code=exc.response.status_code,
            url=server_cfg.get("url"),
        )
        raise MCPHTTPClientError(
            f"MCP HTTP server '{alias}' returned HTTP {exc.response.status_code}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to initialise MCP HTTP server",
            alias=alias,
            error=str(exc),
        )
        raise MCPHTTPClientError(
            f"Failed to initialise MCP HTTP server '{alias}': {exc}"
        ) from exc

    if whitelist:
        filtered = [tool for tool in tools if getattr(tool, "name", None) in whitelist]
        missing = whitelist - {getattr(tool, "name", "") for tool in tools}
        if missing:
            logger.info(
                "Some MCP HTTP tools requested in configuration were not found",
                missing=list(sorted(missing)),
            )
        return filtered

    return tools


async def load_mcp_tools_from_connections(
    connections: Dict[str, Mapping[str, object]],
    allowed_tools: Optional[Iterable[str]] = None,
) -> List[BaseTool]:
    if not connections:
        return []

    if MultiServerMCPClient is None:
        logger.warning("langchain-mcp-adapters is not installed; skipping MCP integration")
        return []

    whitelist = {tool for tool in (allowed_tools or []) if tool}

    prepared_connections: Dict[str, Dict[str, Any]] = {}
    for alias, cfg in connections.items():
        try:
            prepared_connections[alias] = _sanitize_connection_config(alias, cfg)
        except MCPClientError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MCPClientError(
                f"Invalid configuration for MCP server '{alias}': {exc}"
            ) from exc

    client = MultiServerMCPClient(prepared_connections)
    aggregated: List[BaseTool] = []
    try:
        for alias in prepared_connections.keys():
            try:
                alias_tools = await client.get_tools(server_name=alias)
                logger.debug(
                    "Received tool metadata from MCP server",
                    alias=alias,
                    tool_names=[getattr(tool, "name", "") for tool in alias_tools],
                )
            except HTTPStatusError as exc:
                logger.warning(
                    "MCP server responded with HTTP error",
                    alias=alias,
                    status_code=exc.response.status_code,
                )
                raise MCPClientError(
                    f"MCP server '{alias}' returned HTTP {exc.response.status_code}"
                ) from exc
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to initialise MCP server",
                    alias=alias,
                    error=str(exc),
                )
                raise MCPClientError(f"Failed to initialise MCP server '{alias}': {exc}") from exc

            if whitelist:
                filtered_alias_tools = [
                    tool for tool in alias_tools if getattr(tool, "name", None) in whitelist
                ]
                aggregated.extend(filtered_alias_tools)
            else:
                aggregated.extend(alias_tools)

        if whitelist:
            missing = whitelist - {
                getattr(tool, "name", "")
                for tool in aggregated
                if getattr(tool, "name", None)
            }
            if missing:
                logger.info(
                    "Some MCP tools requested in configuration were not found",
                    missing=list(sorted(missing)),
                )

        return aggregated

    except Exception:
        raise
