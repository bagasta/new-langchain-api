from pydantic import BaseModel, Field, field_validator, model_validator, AnyHttpUrl, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from datetime import datetime
from app.models.agent import AgentStatus


class AgentConfig(BaseModel):
    llm_model: str = Field(default="gpt-3.5-turbo")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, gt=0)
    memory_type: str = Field(default="buffer")
    reasoning_strategy: str = Field(default="react")
    system_prompt: Optional[str] = Field(default=None)


class MCPServerConfig(BaseModel):
    transport: Literal["streamable_http", "sse", "stdio"] = "streamable_http"
    url: Optional[AnyHttpUrl] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    cwd: Optional[str] = None

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def _validate_transport_requirements(self) -> "MCPServerConfig":
        transport = self.transport.lower()
        if transport in {"streamable_http", "sse"}:
            if not self.url:
                raise ValueError("HTTP/SSE transports require a URL")
        if transport == "stdio" and not self.command:
            raise ValueError("stdio transport requires a command")
        return self


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tools: List[str] = Field(default=[])
    config: Optional[AgentConfig] = None
    mcp_servers: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    allowed_tools: List[str] = Field(default_factory=list)

    @field_validator("tools", mode="before")
    @classmethod
    def _dedupe_tools(cls, value):
        if not value:
            return []
        unique = []
        seen = set()
        for tool in value:
            if tool is None:
                continue
            cleaned = tool.strip()
            if not cleaned:
                raise ValueError("Tool names must not be empty")
            if cleaned not in seen:
                seen.add(cleaned)
                unique.append(cleaned)
        return unique

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def _dedupe_allowed_tools(cls, value):
        if value is None:
            return []
        unique = []
        seen = set()
        for name in value:
            if name is None:
                continue
            cleaned = name.strip()
            if not cleaned:
                raise ValueError("Allowed tool names must not be empty")
            if cleaned not in seen:
                seen.add(cleaned)
                unique.append(cleaned)
        return unique

class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    tools: Optional[List[str]] = None
    config: Optional[AgentConfig] = None
    status: Optional[AgentStatus] = None
    mcp_servers: Optional[Dict[str, MCPServerConfig]] = None
    allowed_tools: Optional[List[str]] = None

    @field_validator("tools", mode="before")
    @classmethod
    def _validate_tools(cls, value):
        if value is None:
            return value
        unique = []
        seen = set()
        for tool in value:
            if tool is None:
                continue
            cleaned = tool.strip()
            if not cleaned:
                raise ValueError("Tool names must not be empty")
            if cleaned not in seen:
                seen.add(cleaned)
                unique.append(cleaned)
        return unique

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def _validate_allowed_tools(cls, value):
        if value is None:
            return value
        unique = []
        seen = set()
        for name in value:
            if name is None:
                continue
            cleaned = name.strip()
            if not cleaned:
                raise ValueError("Allowed tool names must not be empty")
            if cleaned not in seen:
                seen.add(cleaned)
                unique.append(cleaned)
        return unique


class AgentToolConfig(BaseModel):
    tool_id: str
    config: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    config: Dict[str, Any]
    status: AgentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    mcp_servers: Dict[str, Any] = Field(default_factory=dict)
    allowed_tools: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AgentExecuteRequest(BaseModel):
    input: str
    parameters: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class AgentExecuteResponse(BaseModel):
    execution_id: str
    status: str
    message: str
    response: Optional[str] = None
    session_id: Optional[str] = None


class AgentCreateResponse(AgentResponse):
    auth_required: bool = False
    auth_url: Optional[str] = None
    auth_state: Optional[str] = None
