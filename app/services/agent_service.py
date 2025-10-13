import json
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, text, inspect
from fastapi import HTTPException, status
from datetime import datetime

from app.models import Agent, AgentTool, Tool, User, Execution
from app.schemas.agent import AgentCreate, AgentUpdate, AgentExecuteRequest
from app.core.logging import logger


class AgentService:
    def __init__(self, db: Session):
        self.db = db
        self._agent_tools_has_id_column: Optional[bool] = None

    def create_agent(self, user_id: UUID, agent_data: AgentCreate) -> Agent:
        try:
            # Check if user exists
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Validate tools exist
            valid_tools = []
            if agent_data.tools:
                tools = self.db.query(Tool).filter(Tool.name.in_(agent_data.tools)).all()
                valid_tools = [tool.id for tool in tools]

                if len(valid_tools) != len(agent_data.tools):
                    invalid_tools = set(agent_data.tools) - set(tool.name for tool in tools)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid tools: {invalid_tools}"
                    )

            # Create agent
            config_dict = agent_data.config.model_dump() if agent_data.config else {}

            mcp_servers = {
                alias: cfg.model_dump(mode="json", exclude_none=True)
                for alias, cfg in (agent_data.mcp_servers or {}).items()
            }

            agent = Agent(
                user_id=user_id,
                name=agent_data.name,
                config=config_dict,
                mcp_servers=mcp_servers,
                allowed_tools=list(agent_data.allowed_tools or []),
            )

            self.db.add(agent)
            self.db.commit()
            self.db.refresh(agent)

            # Add agent tools
            if valid_tools:
                self._add_agent_tools(agent.id, valid_tools)

            logger.info("Agent created successfully", agent_id=str(agent.id), user_id=str(user_id))
            return agent

        except HTTPException:
            # re-raise FastAPI HTTP exceptions without modification so callers get accurate status codes
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create agent", error=str(e), user_id=str(user_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create agent: {str(e)}"
            )

    def get_agent(self, agent_id: UUID, user_id: UUID) -> Agent:
        agent = self.db.query(Agent).filter(
            and_(Agent.id == agent_id, Agent.user_id == user_id)
        ).first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )

        return agent

    def get_user_agents(self, user_id: UUID) -> List[Agent]:
        return self.db.query(Agent).filter(Agent.user_id == user_id).all()

    def update_agent(self, agent_id: UUID, user_id: UUID, agent_data: AgentUpdate) -> Agent:
        agent = self.get_agent(agent_id, user_id)

        try:
            if agent_data.name is not None:
                agent.name = agent_data.name

            if agent_data.config is not None:
                existing_config = dict(agent.config or {})
                updates = agent_data.config.model_dump(exclude_unset=True, exclude_none=True)
                existing_config.update(updates)
                agent.config = existing_config

            if agent_data.status is not None:
                agent.status = agent_data.status

            if agent_data.mcp_servers is not None:
                agent.mcp_servers = {
                    alias: cfg.model_dump(mode="json", exclude_none=True)
                    for alias, cfg in agent_data.mcp_servers.items()
                }

            if agent_data.allowed_tools is not None:
                agent.allowed_tools = list(agent_data.allowed_tools or [])

            if agent_data.tools is not None:
                # Remove existing tools
                self.db.query(AgentTool).filter(AgentTool.agent_id == agent_id).delete()

                # Add new tools
                if agent_data.tools:
                    tools = self.db.query(Tool).filter(Tool.name.in_(agent_data.tools)).all()
                    tool_ids = [tool.id for tool in tools]
                    self._add_agent_tools(agent_id, tool_ids)

            self.db.commit()
            self.db.refresh(agent)

            logger.info("Agent updated successfully", agent_id=str(agent_id), user_id=str(user_id))
            return agent

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to update agent", error=str(e), agent_id=str(agent_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update agent: {str(e)}"
            )

    def delete_agent(self, agent_id: UUID, user_id: UUID) -> bool:
        agent = self.get_agent(agent_id, user_id)

        try:
            # Delete agent tools
            self.db.query(AgentTool).filter(AgentTool.agent_id == agent_id).delete()

            # Delete agent
            self.db.delete(agent)
            self.db.commit()

            logger.info("Agent deleted successfully", agent_id=str(agent_id), user_id=str(user_id))
            return True

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to delete agent", error=str(e), agent_id=str(agent_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete agent: {str(e)}"
            )

    def get_agent_tools(self, agent_id: UUID, user_id: UUID) -> List[Tool]:
        agent = self.get_agent(agent_id, user_id)
        return self.db.query(Tool).join(AgentTool).filter(AgentTool.agent_id == agent_id).all()

    def execute_agent(self, agent_id: UUID, user_id: UUID, execute_data: AgentExecuteRequest) -> Execution:
        agent = self.get_agent(agent_id, user_id)

        try:
            # Create execution record
            execution = Execution(
                agent_id=agent_id,
                input={"input": execute_data.input, "parameters": execute_data.parameters or {}},
                status="pending"
            )

            self.db.add(execution)
            self.db.commit()
            self.db.refresh(execution)

            # TODO: Implement actual agent execution with LangChain
            # This would involve:
            # 1. Getting agent tools and their configs
            # 2. Building the LangChain agent
            # 3. Executing the agent with the input
            # 4. Updating the execution record with results

            logger.info("Agent execution started", execution_id=str(execution.id), agent_id=str(agent_id))

            return execution

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to execute agent", error=str(e), agent_id=str(agent_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute agent: {str(e)}"
            )

    def get_agent_executions(self, agent_id: UUID, user_id: UUID) -> List[Execution]:
        agent = self.get_agent(agent_id, user_id)
        return self.db.query(Execution).filter(Execution.agent_id == agent_id).all()

    def get_execution(self, execution_id: UUID, user_id: UUID) -> Execution:
        execution = self.db.query(Execution).join(Agent).filter(
            and_(Execution.id == execution_id, Agent.user_id == user_id)
        ).first()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )

        return execution

    # Internal helpers

    def _agent_tools_table_has_id(self) -> bool:
        if self._agent_tools_has_id_column is None:
            try:
                inspector = inspect(self.db.bind)
                columns = inspector.get_columns("agent_tools")
                self._agent_tools_has_id_column = any(col["name"] == "id" for col in columns)
            except Exception:
                # If inspection fails, assume modern schema without an id column
                self._agent_tools_has_id_column = False
        return bool(self._agent_tools_has_id_column)

    def _add_agent_tools(self, agent_id: UUID, tool_ids: List[UUID], tool_configs: Optional[Dict[UUID, Dict[str, Any]]] = None) -> None:
        if not tool_ids:
            return

        tool_configs = tool_configs or {}

        if self._agent_tools_table_has_id():
            for tool_id in tool_ids:
                next_id = self.db.execute(
                    text("SELECT COALESCE(MAX(id), 0) + 1 FROM agent_tools")
                ).scalar() or 1
                config_payload = tool_configs.get(tool_id) or {}
                config_json = json.dumps(config_payload)
                self.db.execute(
                    text(
                        "INSERT INTO agent_tools (id, agent_id, tool_id, config) "
                        "VALUES (:id, :agent_id, :tool_id, CAST(:config AS jsonb))"
                    ),
                    {
                        "id": int(next_id),
                        "agent_id": str(agent_id),
                        "tool_id": str(tool_id),
                        "config": config_json,
                    }
                )
            self.db.commit()
        else:
            for tool_id in tool_ids:
                agent_tool = AgentTool(
                    agent_id=agent_id,
                    tool_id=tool_id,
                    config=tool_configs.get(tool_id) or {},
                )
                self.db.add(agent_tool)
            self.db.commit()
