import asyncio
import json
import re
import time
from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from fastapi import HTTPException, status
from datetime import datetime, timezone
import os

from app.models import Execution, Agent, AgentTool, Tool, User
from app.models.execution import ExecutionStatus
from app.services.tool_service import ToolService
from app.services.auth_service import AuthService
from app.services.embedding_service import EmbeddingService
from app.core.logging import logger
from app.core.config import settings
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import Tool as LangChainTool
from app.integrations.mcp import load_mcp_tools, MCPConnectionError


class ExecutionService:
    _session_column_checked = False

    def __init__(self, db: Session):
        self.db = db
        self.tool_service = ToolService(db)
        self.auth_service = AuthService(db)
        self.embedding_service = EmbeddingService(db)

        if not ExecutionService._session_column_checked:
            self._ensure_session_column()
            ExecutionService._session_column_checked = True

    async def execute_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
        input_text: str,
        parameters: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Execution:
        """Execute an agent with the given input"""
        try:
            # Get agent and validate ownership
            agent = self.db.query(Agent).filter(
                Agent.id == agent_id,
                Agent.user_id == user_id
            ).first()

            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )

            # Create execution record
            execution = Execution(
                agent_id=agent_id,
                input={"input": input_text, "parameters": parameters or {}},
                status=ExecutionStatus.RUNNING,
                session_id=session_id
            )

            self.db.add(execution)
            self.db.commit()
            self.db.refresh(execution)

            logger.info("Agent execution started", execution_id=str(execution.id), agent_id=str(agent_id))

            try:
                # Execute the agent
                result = await self._run_agent(agent, input_text, parameters or {}, session_id)

                # Update execution record
                execution.output = result
                execution.status = ExecutionStatus.COMPLETED
                now_utc = datetime.now(timezone.utc)
                execution.duration_ms = int((now_utc - execution.created_at).total_seconds() * 1000)

                self.db.commit()
                self.db.refresh(execution)

                logger.info("Agent execution completed", execution_id=str(execution.id))

                return execution

            except Exception as e:
                # Update execution with error
                execution.output = {"error": str(e)}
                execution.status = ExecutionStatus.FAILED
                execution.error_message = str(e)
                now_utc = datetime.now(timezone.utc)
                execution.duration_ms = int((now_utc - execution.created_at).total_seconds() * 1000)

                self.db.commit()
                self.db.refresh(execution)

                logger.error("Agent execution failed", error=str(e), execution_id=str(execution.id))
                if isinstance(e, HTTPException):
                    raise e
                return execution

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to execute agent", error=str(e), agent_id=str(agent_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute agent: {str(e)}"
            )

    async def _run_agent(
        self,
        agent: Agent,
        input_text: str,
        parameters: Dict[str, Any],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """Run the LangChain agent"""
        # Get agent configuration
        config = agent.config or {}
        llm_config = config.get("llm_config") or config

        # Initialize LLM
        api_key = (
            llm_config.get("openai_api_key")
            or llm_config.get("api_key")
            or settings.OPENAI_API_KEY
            or os.getenv("OPENAI_API_KEY")
        )
        if not api_key:
            logger.error(
                "OpenAI API key missing while executing agent",
                agent_id=str(agent.id)
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API key is not configured. Set OPENAI_API_KEY in your environment or agent config."
            )

        llm = ChatOpenAI(
            model=(
                llm_config.get("model")
                or llm_config.get("llm_model")
                or config.get("llm_model")
                or "gpt-4o-mini"
            ),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 1000),
            openai_api_key=api_key,
            api_key=api_key
        )

        # Get agent tools
        agent_tools = self.db.query(AgentTool).filter(AgentTool.agent_id == agent.id).all()
        tool_records: List[Tool] = []
        for agent_tool in agent_tools:
            tool_record = self.db.query(Tool).filter(Tool.id == agent_tool.tool_id).first()
            if tool_record:
                tool_records.append(tool_record)

        tool_names = [tool.name for tool in tool_records]

        # Build conversation history context
        conversation_history = self._build_conversation_history(agent.id, session_id)

        # Create LangChain tools
        langchain_tools = []
        for tool_record in tool_records:
            tool_instance = self._create_langchain_tool(tool_record, agent.user_id)
            if tool_instance:
                langchain_tools.append(tool_instance)

        try:
            mcp_tools = await load_mcp_tools(
                servers_cfg=getattr(agent, "mcp_servers", None) or {},
                allowed_tools=getattr(agent, "allowed_tools", None) or [],
            )
        except MCPConnectionError as exc:
            logger.error(
                "Failed to attach MCP tools",
                agent_id=str(agent.id),
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            )
        if mcp_tools:
            langchain_tools.extend(mcp_tools)
            tool_names.extend(
                [
                    tool_name
                    for tool_name in (getattr(tool, "name", None) for tool in mcp_tools)
                    if tool_name
                ]
            )

        # Create prompt template
        base_system_prompt = (
            llm_config.get("system_prompt")
            or config.get("system_prompt")
            or f"You are a helpful AI assistant named {agent.name}."
        )

        tool_description = ""
        unique_tool_names = sorted({name for name in tool_names if name})

        if unique_tool_names:
            tool_description = (
                "You have access to the following tools to help users: "
                f"{', '.join(unique_tool_names)}."
            )

        combined_system_prompt = base_system_prompt.strip()
        guidance_blocks = []
        if tool_description:
            guidance_blocks.append(tool_description)
        if langchain_tools:
            guidance_blocks.append(
                "When a user request requires information or actions from an available tool, "
                "you must call that tool before responding. Never claim an email was sent, "
                "data was read, or content was written unless the relevant tool execution "
                "actually reports success. If a tool call fails, explain the failure instead "
                "of fabricating a result."
            )
            guidance_blocks.append(
                "Each tool expects a single JSON object passed as its argument. Provide well-formed JSON containing "
                "all required fields whenever you invoke a tool."
            )
        tool_names_lower = {name.lower() for name in unique_tool_names}
        if "gmail" in tool_names_lower:
            guidance_blocks.append(
                "For any email task you must call the Gmail tool. Supported actions include 'send', 'read', 'search', 'create_draft', 'get_message', and 'get_thread'. "
                "For 'send' and 'create_draft', include 'to', 'subject', and 'message' (or 'body'), plus optional 'is_html', 'cc', or 'bcc'. "
                "For reading, provide an 'email_id'/'message_id' or a search query with 'max_results'; set 'mark_as_read' to true only when the user explicitly asks. "
                "If the user asks to send an email but omits required information, ask follow-up questions before calling the tool."
            )
        if "google_sheets" in tool_names_lower:
            guidance_blocks.append(
                "For spreadsheet actions, call the Google Sheets tool with the requested operation and range." 
                "Do not fabricate spreadsheet contents."
            )
        if "google_calendar" in tool_names_lower:
            guidance_blocks.append(
                "Use the Google Calendar tool to list events, fetch event details, or create calendar entries. "
                "Provide start/end timestamps in RFC3339 or YYYY-MM-DD format, and specify attendees as emails when needed."
            )
        if guidance_blocks:
            combined_system_prompt = f"{combined_system_prompt}\n\n" + "\n\n".join(guidance_blocks)

        rag_context = self._build_rag_context(agent.id, input_text, parameters)
        if rag_context:
            combined_system_prompt = f"{combined_system_prompt}\n\nContext:\n{rag_context}".strip()

        graph = create_react_agent(
            model=llm,
            tools=langchain_tools,
            prompt=combined_system_prompt,
        )

        messages_input: List[BaseMessage] = list(conversation_history or [])
        messages_input.append(HumanMessage(content=input_text))

        start_time = time.time()
        result_state = await graph.ainvoke({"messages": messages_input})
        execution_time = time.time() - start_time

        result_messages = []
        if isinstance(result_state, dict):
            result_messages = result_state.get("messages", []) or []

        output_text = ""
        tools_used: List[str] = []
        intermediate_steps: List[Dict[str, Any]] = []

        def _stringify(content: Any) -> str:
            if content is None:
                return ""
            if isinstance(content, str):
                return content
            try:
                return json.dumps(content, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(content)

        for message in result_messages:
            if isinstance(message, AIMessage):
                output_text = _stringify(message.content)
            elif isinstance(message, ToolMessage):
                tool_name = getattr(message, "tool", None) or getattr(message, "name", None)
                if tool_name and tool_name not in tools_used:
                    tools_used.append(tool_name)
                intermediate_steps.append(
                    {
                        "tool": tool_name,
                        "observation": _stringify(message.content),
                    }
                )

        return {
            "output": output_text,
            "intermediate_steps": intermediate_steps,
            "tools_used": tools_used,
            "execution_time": execution_time,
            "final_messages": [message.to_json() if hasattr(message, "to_json") else _stringify(message.content) for message in result_messages],
        }

    def _build_rag_context(
        self,
        agent_id: UUID,
        user_query: str,
        parameters: Dict[str, Any],
        top_k: int = 3,
    ) -> str:
        try:
            self._log_rag_event(
                event="retrieval-start",
                agent_id=str(agent_id),
                query_preview=user_query[:200],
                top_k=top_k,
            )
            chunks = self.embedding_service.get_relevant_chunks(agent_id, user_query, top_k)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RAG retrieval failed", agent_id=str(agent_id), error=str(exc))
            return ""

        if not chunks:
            self._log_rag_event(event="retrieval-empty", agent_id=str(agent_id))
            return ""

        lines: List[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            metadata = chunk.get("metadata") or {}
            metadata_json = json.dumps(metadata, ensure_ascii=False)
            distance = chunk.get("distance")
            distance_str = f" (distance: {distance:.4f})" if isinstance(distance, (float, int)) else ""
            self._log_rag_event(
                event="match",
                agent_id=str(agent_id),
                index=idx,
                distance=f"{distance:.4f}" if isinstance(distance, (float, int)) else None,
                metadata=json.dumps(metadata, ensure_ascii=False),
                preview=chunk.get("content", "")[:200],
            )
            lines.append(
                f"[{idx}]{distance_str} metadata={metadata_json}\n{chunk['content']}"
            )

        self._log_rag_event(
            event="context-ready",
            agent_id=str(agent_id),
            chunks=len(lines),
        )
        return "\n\n".join(lines)

    def _log_rag_event(self, event: str, **fields: Any) -> None:
        header = f"[RAG] {event.replace('_', ' ').title()}"
        body_lines = [f"    {key}: {value}" for key, value in fields.items() if value is not None]
        message = "\n".join([header, *body_lines])
        logger.info(message, **fields)

    def _create_langchain_tool(self, tool_record: Tool, user_id: UUID):
        """Create a LangChain tool from our tool system"""
        tool_id = str(tool_record.id)

        description = tool_record.description or "Execute the tool"

        def tool_func(input: Optional[str] = None, **kwargs) -> str:
            payload: Dict[str, Any]

            if kwargs:
                payload = kwargs
            else:
                raw_input = input
                if raw_input is None:
                    return "Invalid JSON input for {tool}: expected a JSON string or keyword arguments.".format(
                        tool=tool_record.name
                    )
                if not raw_input or not raw_input.strip():
                    raw_input = "{}"
                try:
                    payload = json.loads(raw_input)
                except json.JSONDecodeError as exc:
                    parsed = self._parse_freeform_input(raw_input)
                    if parsed is None:
                        return (
                            f"Invalid JSON input for {tool_record.name}: {exc}. "
                            "Provide JSON like {\"action\": \"list_events\", \"max_results\": 5}."
                        )
                    payload = parsed

            try:
                result = self.tool_service.execute_tool(tool_id, payload, user_id)
            except ValueError as exc:
                return f"Tool validation error: {exc}"
            except Exception as exc:  # noqa: BLE001
                return f"Tool execution failed: {exc}"

            if isinstance(result, dict):
                try:
                    return json.dumps(result, ensure_ascii=False)
                except (TypeError, ValueError):
                    return str(result)
            return str(result)

        tool_func.__doc__ = (
            description
            + "\n\nAccepts either a single 'input' JSON string or direct keyword arguments "
              "matching the tool schema."
        )

        return LangChainTool.from_function(
            func=tool_func,
            name=tool_record.name,
            description=description,
        )

    def _parse_freeform_input(self, raw: str) -> Optional[Dict[str, Any]]:
        parts = re.split(r'[;\n,]+', raw)
        parsed: Dict[str, Any] = {}
        for part in parts:
            if not part.strip():
                continue
            if '=' in part:
                key, value = part.split('=', 1)
            elif ':' in part:
                key, value = part.split(':', 1)
            else:
                continue
            parsed[key.strip()] = value.strip()
        if parsed:
            return parsed

        simple = raw.strip().lower()
        simple = re.sub(r'\s+', ' ', simple)
        if not simple:
            return {}

        if simple in {"list events", "list_events", "list upcoming events", "show events"}:
            return {"action": "list_events"}

        if simple.startswith("create event"):
            return {"action": "create_event"}

        if simple.startswith("get event") or simple.startswith("find event"):
            return {"action": "get_event"}

        return None

    def _build_conversation_history(self, agent_id: UUID, session_id: Optional[str]) -> List[BaseMessage]:
        query = (
            self.db.query(Execution)
            .filter(
                Execution.agent_id == agent_id,
                Execution.status == ExecutionStatus.COMPLETED,
                Execution.output.isnot(None),
            )
        )

        if session_id:
            query = query.filter(Execution.session_id == session_id)

        executions = (
            query
            .order_by(Execution.created_at.asc())
            .limit(20)
            .all()
        )

        history_messages: List[BaseMessage] = []
        for exec_record in executions:
            user_input = ""
            if isinstance(exec_record.input, dict):
                user_input = exec_record.input.get("input") or ""
            elif isinstance(exec_record.input, str):
                user_input = exec_record.input

            agent_reply = ""
            if isinstance(exec_record.output, dict):
                agent_reply = exec_record.output.get("output") or ""
            elif isinstance(exec_record.output, str):
                agent_reply = exec_record.output

            if user_input:
                history_messages.append(HumanMessage(content=user_input))
            if agent_reply:
                history_messages.append(AIMessage(content=agent_reply))

        return history_messages

    def _ensure_session_column(self) -> None:
        try:
            inspector = inspect(self.db.bind)
            columns = {col["name"] for col in inspector.get_columns("executions")}
            if "session_id" not in columns:
                self.db.execute(
                    text("ALTER TABLE executions ADD COLUMN IF NOT EXISTS session_id VARCHAR(255)")
                )
                self.db.commit()
        except Exception:
            self.db.rollback()

    def get_execution(self, execution_id: UUID, user_id: UUID) -> Execution:
        """Get execution details"""
        execution = self.db.query(Execution).join(Agent).filter(
            Execution.id == execution_id,
            Agent.user_id == user_id
        ).first()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )

        return execution

    def get_agent_executions(self, agent_id: UUID, user_id: UUID) -> List[Execution]:
        """Get all executions for an agent"""
        agent = self.db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.user_id == user_id
        ).first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )

        return self.db.query(Execution).filter(Execution.agent_id == agent_id).all()

    def cancel_execution(self, execution_id: UUID, user_id: UUID) -> Execution:
        """Cancel an execution"""
        execution = self.get_execution(execution_id, user_id)

        if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Execution cannot be cancelled"
            )

        execution.status = ExecutionStatus.CANCELLED
        now_utc = datetime.now(timezone.utc)
        execution.duration_ms = int((now_utc - execution.created_at).total_seconds() * 1000)

        self.db.commit()
        self.db.refresh(execution)

        logger.info("Execution cancelled", execution_id=str(execution_id))

        return execution

    def get_execution_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get execution statistics for a user"""
        user_agents = self.db.query(Agent).filter(Agent.user_id == user_id).all()
        agent_ids = [agent.id for agent in user_agents]

        executions = self.db.query(Execution).filter(Execution.agent_id.in_(agent_ids)).all()

        total_executions = len(executions)
        completed_executions = len([e for e in executions if e.status == ExecutionStatus.COMPLETED])
        failed_executions = len([e for e in executions if e.status == ExecutionStatus.FAILED])
        avg_duration = sum(e.duration_ms or 0 for e in executions) / total_executions if total_executions > 0 else 0

        return {
            "total_executions": total_executions,
            "completed_executions": completed_executions,
            "failed_executions": failed_executions,
            "success_rate": completed_executions / total_executions if total_executions > 0 else 0,
            "average_duration_ms": avg_duration
        }
