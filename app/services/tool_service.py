from typing import Dict, Any, List, Optional, Type
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID

from app.models import Tool, ToolType
from app.schemas.tool import ToolCreate, ToolUpdate, ToolExecuteRequest
from app.tools.base import BaseTool
from app.tools.google_tools import GmailTool, GoogleSheetsTool, GoogleCalendarTool
from app.tools.file_tools import CSVTool, JSONTool, FileListTool
from app.core.logging import logger


class ToolService:
    def __init__(self, db: Session):
        self.db = db
        self._initialize_builtin_tools()

    def _initialize_builtin_tools(self):
        """Initialize built-in tools in the database"""
        builtin_tools = [
            GmailTool(),
            GoogleSheetsTool(),
            GoogleCalendarTool(),
            CSVTool(),
            JSONTool(),
            FileListTool(),
        ]

        created = False
        updated = False
        for tool in builtin_tools:
            existing_tool = self.db.query(Tool).filter(Tool.name == tool.name).first()
            if not existing_tool:
                db_tool = Tool(
                    name=tool.name,
                    description=tool.description,
                    schema=tool.schema,
                    type=ToolType.BUILTIN,
                )
                self.db.add(db_tool)
                created = True
            else:
                needs_update = False
                if existing_tool.description != tool.description:
                    existing_tool.description = tool.description
                    needs_update = True
                if existing_tool.schema != tool.schema:
                    existing_tool.schema = tool.schema
                    needs_update = True
                if existing_tool.type != ToolType.BUILTIN:
                    existing_tool.type = ToolType.BUILTIN
                    needs_update = True

                if needs_update:
                    updated = True

        if created or updated:
            self.db.commit()
            if created and not updated:
                logger.info("Built-in tools initialized")
            elif updated and not created:
                logger.info("Built-in tools metadata refreshed")
            else:
                logger.info("Built-in tools synchronized")

    def create_tool(self, user_id: UUID, tool_data: ToolCreate) -> Tool:
        try:
            # Check if tool name already exists
            existing_tool = self.db.query(Tool).filter(Tool.name == tool_data.name).first()
            if existing_tool:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tool name already exists"
                )

            # Create tool
            tool = Tool(
                name=tool_data.name,
                description=tool_data.description,
                schema=tool_data.schema.model_dump(),
                type=tool_data.type,
            )

            self.db.add(tool)
            self.db.commit()
            self.db.refresh(tool)

            logger.info("Tool created successfully", tool_id=str(tool.id), user_id=str(user_id))
            return tool

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create tool", error=str(e), user_id=str(user_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create tool: {str(e)}"
            )

    def get_tool(self, tool_id: UUID) -> Tool:
        tool = self.db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tool not found"
            )
        return tool

    def get_tools(self, tool_type: Optional[str] = None) -> List[Tool]:
        query = self.db.query(Tool)
        if tool_type:
            try:
                enum_value = ToolType(tool_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tool type: {tool_type}"
                )
            query = query.filter(Tool.type == enum_value)
        return query.all()

    def update_tool(self, tool_id: UUID, tool_data: ToolUpdate) -> Tool:
        tool = self.get_tool(tool_id)

        try:
            if tool_data.name is not None:
                # Check if new name conflicts with existing tools
                existing_tool = self.db.query(Tool).filter(
                    Tool.name == tool_data.name,
                    Tool.id != tool_id
                ).first()
                if existing_tool:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Tool name already exists"
                    )
                tool.name = tool_data.name

            if tool_data.description is not None:
                tool.description = tool_data.description

            if tool_data.schema is not None:
                tool.schema = tool_data.schema.model_dump()

            self.db.commit()
            self.db.refresh(tool)

            logger.info("Tool updated successfully", tool_id=str(tool_id))
            return tool

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to update tool", error=str(e), tool_id=str(tool_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update tool: {str(e)}"
            )

    def delete_tool(self, tool_id: UUID) -> bool:
        tool = self.get_tool(tool_id)

        try:
            self.db.delete(tool)
            self.db.commit()

            logger.info("Tool deleted successfully", tool_id=str(tool_id))
            return True

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to delete tool", error=str(e), tool_id=str(tool_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete tool: {str(e)}"
            )

    def get_tool_instance(self, tool_name: str) -> Optional[BaseTool]:
        """Get tool instance by name"""
        tool_map = {
            "gmail": GmailTool,
            "google_sheets": GoogleSheetsTool,
            "google_calendar": GoogleCalendarTool,
            "csv": CSVTool,
            "json": JSONTool,
            "file_list": FileListTool
        }

        tool_class = tool_map.get(tool_name)
        if tool_class:
            return tool_class()

        return None

    def execute_tool(self, tool_identifier: str, parameters: Dict[str, Any], user_id: UUID) -> Dict[str, Any]:
        """Execute a tool with given parameters"""
        tool_record = None

        try:
            tool_record = self.get_tool(UUID(tool_identifier))
        except (ValueError, HTTPException):
            tool_record = self.db.query(Tool).filter(Tool.name == tool_identifier).first()
            if not tool_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tool not found: {tool_identifier}"
                )

        tool_instance = self.get_tool_instance(tool_record.name)

        logger.debug(
            "Executing tool",
            tool_name=tool_record.name,
            tool_id=str(tool_record.id),
            user_id=str(user_id),
            parameters=parameters,
        )

        try:
            if tool_instance:
                # For Google tools, we need to pass auth service
                if tool_record.name in ["gmail", "google_sheets", "google_calendar"]:
                    from app.services.auth_service import AuthService

                    auth_service = AuthService(self.db)
                    return tool_instance.execute(parameters, str(user_id), auth_service)

                return tool_instance.run(parameters)

            # Custom tool fallback: echo parameters to acknowledge execution
            return {
                "success": True,
                "result": {
                    "tool_id": str(tool_record.id),
                    "parameters": parameters,
                    "message": "Custom tool execution placeholder"
                },
                "execution_time": 0.0,
                "error": None,
            }

        except ValueError as e:
            logger.warning(
                "Tool validation error",
                error=str(e),
                tool_id=str(tool_record.id),
                user_id=str(user_id)
            )
            raise
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Tool execution failed",
                error=str(e),
                tool_id=str(tool_record.id),
                user_id=str(user_id)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Tool execution failed: {str(e)}"
            )

    def validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Validate tool parameters against schema"""
        tool = self.get_tool_instance(tool_name)
        if not tool:
            return False

        try:
            tool.validate_parameters(parameters)
            return True
        except ValueError:
            return False

    def get_tool_schema(self, tool_identifier: str) -> Dict[str, Any]:
        """Get tool schema"""
        try:
            tool_record = self.get_tool(UUID(tool_identifier))
        except (ValueError, HTTPException):
            tool_record = self.db.query(Tool).filter(Tool.name == tool_identifier).first()
            if not tool_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tool not found: {tool_identifier}"
                )

        tool = self.get_tool_instance(tool_record.name)
        if not tool:
            return tool_record.schema

        return tool.schema

    def get_required_scopes(self, tool_names: List[str]) -> List[str]:
        """Get required OAuth scopes for given tools"""
        scope_mapping = {
            "gmail": [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.compose"
            ],
            "google_sheets": [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/spreadsheets"
            ],
            "google_calendar": [
                "https://www.googleapis.com/auth/calendar"
            ]
        }

        scopes = set()
        for tool_name in tool_names:
            if tool_name in scope_mapping:
                scopes.update(scope_mapping[tool_name])

        return list(scopes)
