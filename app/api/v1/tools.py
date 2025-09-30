from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.deps import get_current_user, get_tool_service
from app.services.tool_service import ToolService
from app.models import User
from app.schemas.tool import ToolCreate, ToolUpdate, ToolResponse, ToolExecuteRequest
from app.core.logging import logger

router = APIRouter()


@router.get("/", response_model=List[ToolResponse])
async def get_tools(
    tool_type: Optional[str] = None,
    tool_service: ToolService = Depends(get_tool_service)
):
    """Get available tools"""
    tools = tool_service.get_tools(tool_type)
    return tools


@router.post("/", response_model=ToolResponse)
async def create_tool(
    tool_data: ToolCreate,
    current_user: User = Depends(get_current_user),
    tool_service: ToolService = Depends(get_tool_service)
):
    """Create a custom tool"""
    try:
        tool = tool_service.create_tool(current_user.id, tool_data)
        logger.info("Tool created", tool_id=str(tool.id), user_id=str(current_user.id))
        return tool
    except Exception as e:
        logger.error("Failed to create tool", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tool: {str(e)}"
        )


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    tool_service: ToolService = Depends(get_tool_service)
):
    """Get a specific tool"""
    try:
        from uuid import UUID
        tool = tool_service.get_tool(UUID(tool_id))
        return tool
    except Exception as e:
        logger.error("Failed to get tool", error=str(e), tool_id=tool_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str,
    tool_data: ToolUpdate,
    current_user: User = Depends(get_current_user),
    tool_service: ToolService = Depends(get_tool_service)
):
    """Update a tool"""
    try:
        from uuid import UUID
        tool = tool_service.update_tool(UUID(tool_id), tool_data)
        logger.info("Tool updated", tool_id=tool_id, user_id=str(current_user.id))
        return tool
    except Exception as e:
        logger.error("Failed to update tool", error=str(e), tool_id=tool_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tool: {str(e)}"
        )


@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: str,
    current_user: User = Depends(get_current_user),
    tool_service: ToolService = Depends(get_tool_service)
):
    """Delete a tool"""
    try:
        from uuid import UUID
        tool_service.delete_tool(UUID(tool_id))
        logger.info("Tool deleted", tool_id=tool_id, user_id=str(current_user.id))
        return {"message": "Tool deleted successfully"}
    except Exception as e:
        logger.error("Failed to delete tool", error=str(e), tool_id=tool_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tool: {str(e)}"
        )


@router.post("/execute")
async def execute_tool(
    request: ToolExecuteRequest,
    current_user: User = Depends(get_current_user),
    tool_service: ToolService = Depends(get_tool_service)
):
    """Execute a tool directly"""
    try:
        result = tool_service.execute_tool(
            request.tool_id, request.parameters, current_user.id
        )
        logger.info("Tool executed", tool_id=request.tool_id, user_id=str(current_user.id))
        return result
    except Exception as e:
        logger.error("Failed to execute tool", error=str(e), tool_id=request.tool_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute tool: {str(e)}"
        )


@router.get("/schemas/{tool_name}")
async def get_tool_schema(
    tool_name: str,
    tool_service: ToolService = Depends(get_tool_service)
):
    """Get tool schema"""
    try:
        schema = tool_service.get_tool_schema(tool_name)
        return schema
    except Exception as e:
        logger.error("Failed to get tool schema", error=str(e), tool_name=tool_name)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool schema not found: {tool_name}"
        )


@router.get("/scopes/required")
async def get_required_scopes(
    tools: str,  # Comma-separated list of tool names
    tool_service: ToolService = Depends(get_tool_service)
):
    """Get required OAuth scopes for tools"""
    try:
        tool_list = [tool.strip() for tool in tools.split(",")]
        scopes = tool_service.get_required_scopes(tool_list)
        return {"scopes": scopes}
    except Exception as e:
        logger.error("Failed to get required scopes", error=str(e), tools=tools)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get required scopes: {str(e)}"
        )
