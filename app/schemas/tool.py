from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.models.tool import ToolType


class ToolSchema(BaseModel):
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class ToolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    schema: ToolSchema
    type: ToolType = ToolType.CUSTOM


class ToolUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    schema: Optional[ToolSchema] = None


class ToolResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    schema: Dict[str, Any]
    type: ToolType
    created_at: datetime

    class Config:
        from_attributes = True


class ToolExecuteRequest(BaseModel):
    tool_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    result: Any
    execution_time: Optional[float] = None
    error: Optional[str] = None
