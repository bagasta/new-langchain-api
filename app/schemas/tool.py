from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.models.tool import ToolType


class ToolSchema(BaseModel):
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class ToolCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    schema_definition: ToolSchema = Field(..., alias="schema")
    type: ToolType = ToolType.CUSTOM


class ToolUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    schema_definition: Optional[ToolSchema] = Field(default=None, alias="schema")


class ToolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    description: Optional[str]
    schema_definition: Dict[str, Any] = Field(alias="schema")
    type: ToolType
    created_at: datetime


class ToolExecuteRequest(BaseModel):
    tool_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    result: Any
    execution_time: Optional[float] = None
    error: Optional[str] = None
