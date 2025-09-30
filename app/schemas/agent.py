from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
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


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tools: List[str] = Field(default=[])
    config: Optional[AgentConfig] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    tools: Optional[List[str]] = None
    config: Optional[AgentConfig] = None
    status: Optional[AgentStatus] = None


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
