from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional, Sequence, Set

from app.core.config import settings


@dataclass(frozen=True)
class MCPConnectionSettings:
    """Settings required to establish an MCP SSE connection."""

    sse_url: str
    token: Optional[str] = None
    request_timeout: float = 30.0
    connection_timeout: float = 300.0

    @property
    def headers(self) -> Mapping[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}


@dataclass(frozen=True)
class MCPToolFilter:
    """Filter definition for narrowing down MCP tools."""

    names: Set[str] = field(default_factory=set)
    categories: Set[str] = field(default_factory=set)

    @classmethod
    def from_iterables(
        cls,
        *,
        names: Optional[Iterable[str]] = None,
        categories: Optional[Iterable[str]] = None,
    ) -> MCPToolFilter:
        return cls(
            names=_normalise_collection(names),
            categories=_normalise_collection(categories),
        )

    def includes(self, *, name: Optional[str], categories: Sequence[str] | None) -> bool:
        if not self.names and not self.categories:
            return True

        name_match = True
        category_match = True

        if self.names:
            name_match = bool(name and name.strip().lower() in self.names)

        if self.categories:
            category_match = any(
                isinstance(category, str)
                and category.strip().lower() in self.categories
                for category in (categories or [])
            )

        return name_match and category_match


def _normalise_collection(values: Optional[Iterable[str]]) -> Set[str]:
    if not values:
        return set()
    normalised: Set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            normalised.add(text.lower())
    return normalised


def get_default_connection_settings() -> Optional[MCPConnectionSettings]:
    """Build connection settings from environment defaults."""
    if not settings.MCP_SSE_URL:
        return None

    return MCPConnectionSettings(
        sse_url=settings.MCP_SSE_URL,
        token=settings.MCP_SSE_TOKEN,
    )


def get_default_tool_filter() -> MCPToolFilter:
    """Return the default tool filter derived from settings."""
    return MCPToolFilter.from_iterables(
        names=settings.MCP_SSE_ALLOWED_TOOLS,
        categories=settings.MCP_SSE_ALLOWED_TOOL_CATEGORIES,
    )
