from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    AnyHttpUrl,
    ConfigDict,
    AliasChoices,
)
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
    model_config = ConfigDict(extra="forbid")


class AgentConfigUpdate(BaseModel):
    llm_model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    memory_type: Optional[str] = None
    reasoning_strategy: Optional[str] = None
    system_prompt: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


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
    tools: List[str] = Field(default_factory=list)
    google_tools: List[str] = Field(default_factory=list)
    config: Optional[AgentConfig] = None
    mcp_servers: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    allowed_tools: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("allowed_tools", "mcp_tools"),
    )
    token_limit: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum tokens allowed for this agent. Set to None for unlimited."
    )

    @model_validator(mode="before")
    @classmethod
    def _merge_tool_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            tools = data.get("tools", []) or []
            google_tools = data.get("google_tools", []) or []
            
            if not isinstance(tools, list):
                tools = []
            if not isinstance(google_tools, list):
                google_tools = []
                
            # Define mcp_tools
            mcp_tools = data.get("mcp_tools") or data.get("allowed_tools") or []
            if not isinstance(mcp_tools, list): mcp_tools = []
            
            # Merge DB tools (Local + Google)
            db_tools = list(set(tools + google_tools))
            data["tools"] = db_tools
            
            # Merge into allowed_tools (Local + Google + MCP)
            all_tools = list(set(db_tools + mcp_tools))
            data["allowed_tools"] = all_tools
        return data

    @field_validator("tools", mode="after")
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
    tools: Optional[List[str]] = Field(default=None)
    google_tools: Optional[List[str]] = Field(default=None)
    config: Optional[AgentConfigUpdate] = None
    status: Optional[AgentStatus] = None
    mcp_servers: Optional[Dict[str, MCPServerConfig]] = None
    allowed_tools: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("allowed_tools", "mcp_tools"),
    )
    token_limit: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum tokens allowed for this agent. Set to None for unlimited."
    )

    @model_validator(mode="before")
    @classmethod
    def _merge_tool_update_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Only merge if either is present
            if "tools" in data or "google_tools" in data:
                tools = data.get("tools") or []
                google_tools = data.get("google_tools") or []
                
                if not isinstance(tools, list): tools = []
                if not isinstance(google_tools, list): google_tools = []
                
                # Check for mcp_tools/allowed_tools in update data
                mcp_tools = data.get("mcp_tools") or data.get("allowed_tools") or []
                if not isinstance(mcp_tools, list): mcp_tools = []
                
                # Merge DB tools (Local + Google)
                db_tools = list(set(tools + google_tools))
                data["tools"] = db_tools
                
                # Merge into allowed_tools (Local + Google + MCP)
                all_tools = list(set(db_tools + mcp_tools))
                data["allowed_tools"] = all_tools
        return data

    @field_validator("tools", mode="after")
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
    # Keep the database column name internally but expose as mcp_tools in API responses
    allowed_tools: List[str] = Field(default_factory=list, exclude=True)
    mcp_tools: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("mcp_tools", "allowed_tools"),
    )
    google_tools: List[str] = Field(default_factory=list)
    
    # Token limit fields
    token_limit: Optional[int] = None
    tokens_used: int = 0
    tokens_remaining: Optional[int] = None
    token_reset_date: Optional[datetime] = None
    
    # Auth Status
    auth_required: bool = False
    auth_url: Optional[str] = None
    auth_state: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _populate_mcp_tools_and_tokens(self) -> "AgentResponse":
        # Split allowed_tools into mcp_tools and google_tools
        self.mcp_tools = []
        self.google_tools = []
        
        if self.allowed_tools:
            # We define google tools pattern. 
            # Ideally this should come from a central registry, but for schema display purposes:
            google_prefixes = (
                "gmail_", 
                "google_calendar_", 
                "google_sheets_", 
                "google_docs_", 
                "google_drive_", 
                "google_search"
            )
            # Some tools might be just "gmail" or "google_docs"
            google_exact = {"gmail", "google_docs", "google_sheets", "google_calendar"}
            
            for tool in self.allowed_tools:
                is_google = (
                    tool.startswith(google_prefixes) 
                    or tool in google_exact
                )
                
                if is_google:
                    self.google_tools.append(tool)
                else:
                    self.mcp_tools.append(tool)
        
        # Calculate tokens remaining
        if self.token_limit is not None:
            self.tokens_remaining = max(0, self.token_limit - (self.tokens_used or 0))
            
        return self


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
    
    # Token usage tracking
    tokens_used: Optional[int] = None
    tokens_remaining: Optional[int] = None


class AgentCreateResponse(AgentResponse):
    auth_required: bool = False
    auth_url: Optional[str] = None
    auth_state: Optional[str] = None


class AgentUploadRecord(BaseModel):
    id: UUID
    agent_id: UUID
    user_id: Optional[UUID] = None
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    chunk_count: int
    embedding_ids: List[UUID] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AgentUploadListResponse(BaseModel):
    uploads: List[AgentUploadRecord]
