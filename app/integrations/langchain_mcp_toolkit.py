from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set
from uuid import uuid4

import httpx
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_mcp import MCPToolkit
from mcp import ClientSession
from mcp.client.sse import sse_client

from app.core.mcp_config import MCPConnectionSettings, MCPToolFilter
from app.core.logging import logger


class MCPIntegrationError(RuntimeError):
    """Base exception for MCP integration failures."""


class MCPConnectionError(MCPIntegrationError):
    """Raised when an MCP transport cannot be established."""


class MCPToolSelectionError(MCPIntegrationError):
    """Raised when no tools satisfy the selection criteria."""


@asynccontextmanager
async def mcp_toolkit_context(
    *,
    connection: MCPConnectionSettings,
    extra_headers: Optional[Mapping[str, str]] = None,
) -> AsyncIterator[MCPToolkit]:
    """Context manager that yields an initialised MCPToolkit over SSE."""
    headers: MutableMapping[str, str] = dict(connection.headers)
    if extra_headers:
        headers.update(extra_headers)

    logger.info(
        "Connecting to MCP SSE server",
        url=connection.sse_url,
        headers=bool(headers),
        request_timeout=connection.request_timeout,
        connection_timeout=connection.connection_timeout,
    )

    try:
        async with sse_client(
            connection.sse_url,
            headers=headers or None,
            timeout=connection.request_timeout,
            sse_read_timeout=connection.connection_timeout,
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                toolkit = MCPToolkit(session=session)
                try:
                    await toolkit.initialize()
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Failed to initialise MCP SSE toolkit",
                        url=connection.sse_url,
                        error=str(exc),
                    )
                    raise MCPIntegrationError(
                        f"MCP SSE session initialisation failed: {exc}"
                    ) from exc

                logger.info("Connected to MCP SSE server", url=connection.sse_url)

                try:
                    yield toolkit
                finally:
                    close_callable = getattr(toolkit, "close", None)
                    if callable(close_callable):
                        close_result = close_callable()
                        if inspect.isawaitable(close_result):
                            await close_result
    except MCPIntegrationError:
        raise
    except BaseExceptionGroup as exc:
        inners = list(_iter_exception_group(exc)) or [exc]
        total = len(inners)
        for idx, inner in enumerate(inners, 1):
            logger.exception(
                "MCP SSE inner exception %d/%d",
                idx,
                total,
                exc_info=(type(inner), inner, inner.__traceback__),
            )

        primary = inners[0]
        if isinstance(primary, MCPIntegrationError) and not isinstance(
            primary, MCPConnectionError
        ):
            raise primary

        raise MCPConnectionError(
            f"Failed to open MCP SSE connection to {connection.sse_url}: {primary}"
        ) from primary
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response else "unknown"
        logger.error(
            "MCP SSE connection returned HTTP error",
            url=connection.sse_url,
            status_code=status,
        )
        raise MCPConnectionError(
            f"MCP SSE server at {connection.sse_url} returned HTTP {status}. "
            "Ensure the calculator server is running and reachable."
        ) from exc
    except httpx.RequestError as exc:
        logger.error(
            "MCP SSE connection failed",
            url=connection.sse_url,
            error=str(exc),
        )
        raise MCPConnectionError(
            "Unable to reach the MCP SSE server. "
            "Verify that `python -m src.transports.sse` is running and "
            f"accessible at {connection.sse_url}."
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unexpected error while establishing MCP SSE connection",
            url=connection.sse_url,
        )
        raise MCPConnectionError(
            f"Failed to open MCP SSE connection to {connection.sse_url}: {exc}"
        ) from exc


def _iter_exception_group(exc: BaseException) -> Iterable[BaseException]:
    if isinstance(exc, BaseExceptionGroup):
        for sub in exc.exceptions:
            yield from _iter_exception_group(sub)
    else:
        yield exc


def filter_mcp_tools(
    tools: Iterable[BaseTool],
    tool_filter: Optional[MCPToolFilter] = None,
) -> List[BaseTool]:
    """Filter MCP tools by name and category."""
    tool_list = list(tools)
    if not tool_filter or (not tool_filter.names and not tool_filter.categories):
        return tool_list

    name_filters = set(tool_filter.names)
    category_filters = set(tool_filter.categories)
    alias_map = _build_name_aliases(tool_list)
    expanded_name_filters: Set[str] = set(name_filters)
    for alias in list(name_filters):
        expanded_name_filters.update(alias_map.get(alias, set()))

    filtered: List[BaseTool] = []
    for tool in tool_list:
        name_raw = getattr(tool, "name", "")
        name_lower = name_raw.strip().lower()
        categories = [
            category.strip().lower()
            for category in _extract_categories(tool)
            if isinstance(category, str)
        ]

        name_match = True
        if name_filters:
            name_match = False
            if name_lower and name_lower in expanded_name_filters:
                name_match = True
            else:
                for requested in name_filters:
                    if requested and requested in name_lower:
                        name_match = True
                        break

        category_match = True
        if category_filters:
            category_match = any(category in category_filters for category in categories)

        if name_match and category_match:
            filtered.append(tool)

    return filtered


def _extract_categories(tool: BaseTool) -> Sequence[str]:
    metadata = getattr(tool, "metadata", None)
    if not metadata:
        return []

    if isinstance(metadata, Mapping):
        categories = metadata.get("categories")
    else:
        categories = getattr(metadata, "get", lambda _key, _default=None: None)(
            "categories", None
        )

    if not categories:
        return []

    if isinstance(categories, str):
        return [categories]

    if isinstance(categories, Sequence):
        return [str(category) for category in categories if str(category).strip()]

    return []


def _build_name_aliases(tools: Iterable[BaseTool]) -> Dict[str, Set[str]]:
    names: Set[str] = set()
    for tool in tools:
        raw = getattr(tool, "name", "")
        if raw:
            names.add(raw.strip().lower())

    alias_map: Dict[str, Set[str]] = {}

    calculator_aliases = {
        "calculator",
        "calculators",
        "math",
        "arithmetic",
    }
    calculator_tools = {
        "add",
        "subtract",
        "multiply",
        "divide",
        "power",
        "sqrt",
        "factorial",
        "percentage",
    }
    available_calculator_tools = {name for name in names if name in calculator_tools}
    if available_calculator_tools:
        for alias in calculator_aliases:
            alias_map[alias] = available_calculator_tools

    if "fetch_web_content" in names:
        for alias in {"web_fetch", "webfetch", "web", "fetch", "fetch_web"}:
            alias_map.setdefault(alias, set()).add("fetch_web_content")

    return alias_map


@dataclass
class MCPAgentResources:
    executor: AgentExecutor
    tools: Sequence[BaseTool]
    mcp_tools: Sequence[BaseTool]


@asynccontextmanager
async def mcp_agent_executor_context(
    *,
    connection: MCPConnectionSettings,
    llm: BaseChatModel,
    prompt_builder: Callable[[Sequence[BaseTool], Sequence[BaseTool]], ChatPromptTemplate],
    tool_filter: Optional[MCPToolFilter] = None,
    base_tools: Optional[Sequence[BaseTool]] = None,
    agent_executor_kwargs: Optional[Mapping[str, Any]] = None,
    extra_headers: Optional[Mapping[str, str]] = None,
) -> AsyncIterator[MCPAgentResources]:
    """Yield an AgentExecutor configured with MCP tools."""
    agent_executor_kwargs = dict(agent_executor_kwargs or {})
    base_tool_list = list(base_tools or [])

    async with mcp_toolkit_context(
        connection=connection,
        extra_headers=extra_headers,
    ) as toolkit:
        try:
            tools = toolkit.get_tools()
        except Exception as exc:  # noqa: BLE001
            raise MCPIntegrationError(f"Failed to retrieve MCP tools: {exc}") from exc

        selected_tools = filter_mcp_tools(tools, tool_filter=tool_filter)

        if not selected_tools and not base_tool_list:
            logger.warning(
                "No MCP tools matched filters",
                available=[getattr(tool, "name", "") for tool in tools],
                filter_names=sorted(tool_filter.names) if tool_filter else [],
                filter_categories=sorted(tool_filter.categories)
                if tool_filter
                else [],
            )
            raise MCPToolSelectionError("No MCP tools matched the provided filters")

        combined_tools = [*base_tool_list, *selected_tools]

        try:
            prompt = prompt_builder(combined_tools, selected_tools)
        except Exception as exc:  # noqa: BLE001
            raise MCPIntegrationError(f"Failed to build MCP prompt: {exc}") from exc

        agent = create_tool_calling_agent(llm, combined_tools, prompt)
        _ensure_runnable_identity(agent, prefix="mcp_tool_agent")
        executor = AgentExecutor(
            agent=agent,
            tools=combined_tools,
            **agent_executor_kwargs,
        )

        yield MCPAgentResources(
            executor=executor,
            tools=combined_tools,
            mcp_tools=selected_tools,
        )


def _ensure_runnable_identity(runnable: Any, prefix: str) -> None:
    try:
        existing_id = getattr(runnable, "id", None)
    except Exception:  # noqa: BLE001
        existing_id = None

    if not existing_id:
        try:
            runnable.__dict__["id"] = f"{prefix}-{uuid4().hex}"
        except Exception:  # noqa: BLE001
            pass

    try:
        existing_name = getattr(runnable, "name", None)
    except Exception:  # noqa: BLE001
        existing_name = None

    if not existing_name:
        try:
            runnable.__dict__["name"] = prefix
        except Exception:  # noqa: BLE001
            pass
