"""
MCP Server — Exposes ALL LangChain API endpoints as MCP Tools.

This is a **standalone** entry-point.  It imports the existing
services and database machinery from ``app/`` but does NOT
modify any file inside that package.

Run:
    python mcp_server.py                        # stdio transport (default, for Claude Desktop)
    python mcp_server.py --sse                  # SSE transport on default port 8190
    python mcp_server.py --sse --port 8190      # SSE transport with explicit port
    python mcp_server.py --sse --host 0.0.0.0   # bind to all interfaces

Ports:
    - Uvicorn (FastAPI)  → port 8000  (default)
    - MCP SSE Server     → port 8190  (default, via MCP_SSE_PORT env or --port flag)
      Configured in .env as: MCP_SSE_URL=http://localhost:8190/sse

No extra dependencies required — uses ``mcp.server.fastmcp.FastMCP``
which is already bundled with the ``mcp>=1.6`` package.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional, List, Dict, Any
from uuid import UUID

# ── Parse CLI args early — BEFORE FastMCP is created ───────────────────
# FastMCP accepts host/port via its constructor (**settings kwargs).
# We parse first so we can pass them in when instantiating FastMCP below.
_early_parser = argparse.ArgumentParser(add_help=False)
_early_parser.add_argument("--sse", action="store_true")
_early_parser.add_argument("--host", default=os.environ.get("MCP_SSE_HOST", "0.0.0.0"))
_early_parser.add_argument(
    "--port",
    type=int,
    # Default 8190 so MCP server doesn't clash with uvicorn on 8000.
    default=int(os.environ.get("MCP_SSE_PORT", 8190)),
)
_early_args, _ = _early_parser.parse_known_args()

from mcp.server.fastmcp import FastMCP

# ── App imports (read-only, no modifications) ────────────────────────
from app.core.database import SessionLocal, init_db
from app.core.logging import logger
from app.services.auth_service import AuthService
from app.services.agent_service import AgentService
from app.services.execution_service import ExecutionService
from app.services.tool_service import ToolService
from app.services.upload_service import UploadService
from app.schemas.agent import AgentCreate, AgentUpdate, AgentConfig, AgentConfigUpdate
from app.schemas.auth import PlanCode
from app.models import Agent, User

# ── Initialise FastMCP (host/port from CLI args or env vars) ─────────
mcp = FastMCP(
    "AIStaff MCP Server",
    host=_early_args.host,
    port=_early_args.port,
)

# ── Ensure DB tables exist (safe to call multiple times) ─────────────
try:
    init_db()
    logger.info("MCP Server: database initialised successfully")
except Exception as exc:
    logger.warning(
        "MCP Server: database init encountered an issue — "
        "the tool will still try to create sessions on demand.",
        error=str(exc),
    )


# =====================================================================
# Helper: Validate UUID strings
# =====================================================================
def _parse_uuid(value: str, label: str = "ID") -> UUID:
    """Parse a string to UUID, raising ValueError on failure."""
    try:
        return UUID(value)
    except ValueError:
        raise ValueError(f"Invalid {label}: {value!r}")


def _serialize(obj: Any) -> str:
    """Convert any object to JSON string, handling common types."""
    if obj is None:
        return json.dumps(None)
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return json.dumps(obj, default=str)
    if isinstance(obj, list):
        return json.dumps(obj, default=str)
    # For SQLAlchemy models, try extracting common fields
    return json.dumps(str(obj))


def _to_list(value: Any) -> list:
    """Coerce value to a list. Accepts list, JSON string, or None."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, ValueError):
            return [value]  # single item
    return []


def _to_dict(value: Any) -> dict:
    """Coerce value to a dict. Accepts dict, JSON string, or None."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return {}
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


# =====================================================================
#  AUTH TOOLS
# =====================================================================

@mcp.tool()
async def register_user(identifier: str, password: str, plan_code: str = "GUEST") -> str:
    """Register a new user account and auto-activate for TRIAL/GUEST plans.

    TRIAL and GUEST accounts are immediately activated with an API key — no
    payment or email verification required.  PRO_M and PRO_Y accounts are
    created but stay inactive until payment is confirmed.

    Args:
        identifier: Email address or phone number.
        password:   Plaintext password.
        plan_code:  Plan to assign on registration.
                    Accepted values: GUEST (default), TRIAL, PRO_M, PRO_Y.

    Returns:
        JSON with user_id, email, is_active, and (for TRIAL/GUEST) access_token.
    """
    db = SessionLocal()
    try:
        plan_map = {
            "GUEST": PlanCode.GUEST,
            "TRIAL": PlanCode.TRIAL,
            "PRO_M": PlanCode.PRO_M,
            "PRO_Y": PlanCode.PRO_Y,
        }
        resolved_plan = plan_map.get(plan_code.upper(), PlanCode.GUEST)

        service = AuthService(db)
        result = await service.register_and_activate(identifier, password, resolved_plan)
        return json.dumps(result, default=str)
    except Exception as exc:
        logger.error("MCP register_user error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def login_user(identifier: str, password: str) -> str:
    """Authenticate a user and return an access token.

    Args:
        identifier: Email address or phone number.
        password:   Plaintext password.

    Returns:
        JSON with access_token and user_id on success, or error.
    """
    db = SessionLocal()
    try:
        service = AuthService(db)
        user = await service.authenticate_user(identifier, password)
        if not user:
            return json.dumps({"status": "error", "error": "Invalid credentials"})

        access_token = service.create_access_token(str(user.id))
        return json.dumps({
            "status": "success",
            "user_id": str(user.id),
            "email": user.email,
            "access_token": access_token,
            "token_type": "bearer",
        })
    except Exception as exc:
        logger.error("MCP login_user error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def generate_api_key(
    identifier: str,
    password: str,
    plan_code: str = "TRIAL",
) -> str:
    """Generate an API key for a user with a specific plan.

    Args:
        identifier: Email address or phone number.
        password:   Plaintext password.
        plan_code:  Plan code — one of: TRIAL, PRO_M, PRO_Y, GUEST.

    Returns:
        JSON with access_token, expires_at, and plan_code.
    """
    db = SessionLocal()
    try:
        service = AuthService(db)
        plan = PlanCode(plan_code)
        result = await service.generate_api_key(identifier, password, plan)
        return json.dumps({
            "status": "success",
            **result,
        }, default=str)
    except Exception as exc:
        logger.error("MCP generate_api_key error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def create_trial_api_key(ip_address: str) -> str:
    """Create a trial API key for a given IP address (guest access).

    Args:
        ip_address: The IP address of the trial user.

    Returns:
        JSON with access_token, user_id, and expiration.
    """
    db = SessionLocal()
    try:
        service = AuthService(db)
        result = service.create_trial_api_key(ip_address)
        return json.dumps({
            "status": "success",
            **result,
        }, default=str)
    except Exception as exc:
        logger.error("MCP create_trial_api_key error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def update_user_password(user_id: str, new_password: str) -> str:
    """Update a user's password.

    Args:
        user_id:      UUID of the user.
        new_password: The new password (plaintext or pre-hashed).

    Returns:
        JSON success or error.
    """
    db = SessionLocal()
    try:
        _user_uuid = _parse_uuid(user_id, "user_id")
        service = AuthService(db)
        service.update_user_password(_user_uuid, new_password)
        return json.dumps({"status": "success", "message": "Password updated"})
    except Exception as exc:
        logger.error("MCP update_user_password error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()



# =====================================================================
#  AUTH ME — Google Auth URL generator (works like /auth/me + /google/auth)
# =====================================================================

@mcp.tool()
async def auth_me(
    access_token: str,
    tool_names: Any = None,
    agent_id: str = "",
) -> str:
    """Generate a Google OAuth authentication URL for a user identified by their
    access_token (JWT).  Works exactly like the /auth/me + /google/auth endpoints
    in the Langchain API — no need to know the raw user UUID.

    Call this tool when:
    - A user needs to connect their Google account after agent creation.
    - You have the access_token from login_user/register_user but NOT the user UUID.

    Args:
        access_token: The JWT access token returned by login_user or register_user.
        tool_names:   List of Google tool names the agent will use
                      (e.g. ["gmail_send_message", "google_sheets_get_values"]).
                      Used to derive the required OAuth scopes.
        agent_id:     Optional UUID of the agent to scope the OAuth grant to.

    Returns:
        JSON with auth_required (bool), auth_url (str), and user_id (str).
    """
    db = SessionLocal()
    try:
        # 1. Resolve the user from the JWT
        auth_service = AuthService(db)
        token_data = auth_service.verify_token(access_token)
        if token_data is None:
            return json.dumps({"status": "error", "error": "Invalid or expired access_token"})

        user_id_str = str(token_data.sub)

        # 2. Derive required scopes from tool_names
        names = _to_list(tool_names)
        tool_service = ToolService(db)
        required_scopes = tool_service.get_required_scopes(names) if names else []

        # 3. Check if the user already has valid tokens (agent-level then user-level)
        _agent_id_str = agent_id if agent_id else None

        def _has_valid(tokens_list, scopes_set) -> bool:
            for t in tokens_list:
                if t.service != "google":
                    continue
                if scopes_set.issubset(set(t.scope or [])):
                    return True
            return False

        if required_scopes:
            scope_set = set(required_scopes)
            agent_tokens = auth_service.get_user_auth_tokens(user_id_str, _agent_id_str)
            user_tokens = auth_service.get_user_auth_tokens(user_id_str, None)
            if _has_valid(agent_tokens, scope_set) or _has_valid(user_tokens, scope_set):
                return json.dumps({
                    "status": "success",
                    "auth_required": False,
                    "auth_url": None,
                    "user_id": user_id_str,
                })

        # 4. Generate Google auth URL
        auth_data = auth_service.create_google_auth_url(
            user_id=user_id_str,
            scopes=required_scopes if required_scopes else None,
            agent_id=_agent_id_str,
        )

        return json.dumps({
            "status": "success",
            "auth_required": True,
            "auth_url": auth_data.get("auth_url"),
            "user_id": user_id_str,
        })

    except Exception as exc:
        logger.error("MCP auth_me error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


# =====================================================================

#  AGENT TOOLS
# =====================================================================

@mcp.tool()
async def create_agent(
    user_id: str,
    name: str,
    system_prompt: str = "",
    llm_model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    tools: Any = None,
    google_tools: Any = None,
    allowed_tools: Any = None,
    token_limit: int = 4000000,
) -> str:
    """Create a new AI agent.

    Args:
        user_id:       UUID of the owning user.
        name:          Agent name (1-255 chars).
        system_prompt: System prompt / instructions for the agent.
        llm_model:     LLM model name (default: gpt-4o-mini).
        temperature:   Temperature 0.0–2.0.
        max_tokens:    Max output tokens.
        tools:         List of tool names (DB-registered tools).
        google_tools:  List of Google tool names.
        allowed_tools: List of MCP/external tool names.
        token_limit:   Max tokens budget for this agent.

    Returns:
        JSON with agent_id and details.
    """
    db = SessionLocal()
    try:
        _user_uuid = _parse_uuid(user_id, "user_id")
        _tools = _to_list(tools)
        _google_tools = _to_list(google_tools)
        _allowed_tools = _to_list(allowed_tools)

        agent_data = AgentCreate(
            name=name,
            tools=_tools,
            google_tools=_google_tools,
            allowed_tools=_allowed_tools,
            config=AgentConfig(
                llm_model=llm_model,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt or None,
            ),
            token_limit=token_limit if token_limit > 0 else None,
        )

        service = AgentService(db)
        agent = service.create_agent(_user_uuid, agent_data)

        # Auto-publish: generate API key right after creation
        auth_service = AuthService(db)
        api_key_data = auth_service.create_agent_api_key(_user_uuid, agent.id)

        return json.dumps({
            "status": "success",
            "agent_id": str(agent.id),
            "name": agent.name,
            "config": agent.config,
            "token_limit": agent.token_limit,
            "created_at": str(agent.created_at),
            "jwt_token": api_key_data.get("access_token", ""),
        })
    except Exception as exc:
        logger.error("MCP create_agent error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def list_agents(user_id: str) -> str:
    """List all agents owned by a user.

    Args:
        user_id: UUID of the user.

    Returns:
        JSON array of agents with id, name, status, and config.
    """
    db = SessionLocal()
    try:
        _user_uuid = _parse_uuid(user_id, "user_id")
        service = AgentService(db)
        agents = service.get_user_agents(_user_uuid)

        return json.dumps({
            "status": "success",
            "agents": [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "status": a.status.value if hasattr(a.status, 'value') else str(a.status),
                    "config": a.config,
                    "token_limit": a.token_limit,
                    "tokens_used": a.tokens_used,
                    "allowed_tools": a.allowed_tools,
                    "created_at": str(a.created_at),
                }
                for a in agents
            ],
        })
    except Exception as exc:
        logger.error("MCP list_agents error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def get_agent(agent_id: str, user_id: str) -> str:
    """Get details of a specific agent.

    Args:
        agent_id: UUID of the agent.
        user_id:  UUID of the owning user.

    Returns:
        JSON with full agent details.
    """
    db = SessionLocal()
    try:
        _agent_uuid = _parse_uuid(agent_id, "agent_id")
        _user_uuid = _parse_uuid(user_id, "user_id")
        service = AgentService(db)
        agent = service.get_agent(_agent_uuid, _user_uuid)

        return json.dumps({
            "status": "success",
            "agent": {
                "id": str(agent.id),
                "name": agent.name,
                "status": agent.status.value if hasattr(agent.status, 'value') else str(agent.status),
                "config": agent.config,
                "mcp_servers": agent.mcp_servers,
                "allowed_tools": agent.allowed_tools,
                "token_limit": agent.token_limit,
                "tokens_used": agent.tokens_used,
                "created_at": str(agent.created_at),
                "updated_at": str(agent.updated_at) if agent.updated_at else None,
            },
        })
    except Exception as exc:
        logger.error("MCP get_agent error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def update_agent(
    agent_id: str,
    user_id: str,
    name: str = "",
    system_prompt: str = "",
    google_tools: Any = None,
    allowed_tools: Any = None,
) -> str:
    """Update an agent's basic info and tool assignments.

    ONLY the following fields can be changed via this tool:
    - name: Display name of the agent.
    - system_prompt: Instructions / personality for the agent.
    - google_tools: List of Google service tool names the agent can use.
    - allowed_tools: List of MCP/external tool names the agent can use.

    Sensitive fields (llm_model, temperature, max_tokens, token_limit,
    status) are intentionally NOT editable here.
    To add/remove MCP server connections use the `update_agent_mcp_servers` tool.

    Args:
        agent_id:      UUID of the agent to update.
        user_id:       UUID of the owning user.
        name:          New display name (leave empty to keep current).
        system_prompt: New instructions for the agent (leave empty to keep current).
        google_tools:  List of Google tool names, e.g. ["gmail_send_message", "google_sheets_read"].
                       Pass an empty list [] to clear all Google tools.
                       Pass null/omit to keep the current list unchanged.
        allowed_tools: List of MCP external tool names, e.g. ["web_search", "docx_generate"].
                       Pass an empty list [] to clear all MCP tools.
                       Pass null/omit to keep the current list unchanged.

    Returns:
        JSON with updated agent name, system_prompt, google_tools, and allowed_tools.
    """
    db = SessionLocal()
    try:
        _agent_uuid = _parse_uuid(agent_id, "agent_id")
        _user_uuid = _parse_uuid(user_id, "user_id")

        update_data: Dict[str, Any] = {}

        if name:
            update_data["name"] = name

        # Only system_prompt is editable inside config
        if system_prompt:
            update_data["config"] = AgentConfigUpdate(system_prompt=system_prompt)

        # google_tools — only update when explicitly provided (not None)
        if google_tools is not None:
            update_data["google_tools"] = _to_list(google_tools)

        # allowed_tools (MCP tools) — only update when explicitly provided
        if allowed_tools is not None:
            update_data["allowed_tools"] = _to_list(allowed_tools)

        agent_update = AgentUpdate(**update_data)
        service = AgentService(db)
        agent = service.update_agent(_agent_uuid, _user_uuid, agent_update)

        # Read back the saved config for display
        cfg = agent.config or {}
        return json.dumps({
            "status": "success",
            "agent": {
                "id": str(agent.id),
                "name": agent.name,
                "system_prompt": cfg.get("system_prompt"),
                "google_tools": [t for t in (agent.allowed_tools or []) if not t.startswith("web_") and not t.startswith("fetch_") and not t.startswith("deep_") and not t.startswith("docx_")],
                "allowed_tools": agent.allowed_tools,
                "updated_at": str(agent.updated_at) if agent.updated_at else None,
            },
        })
    except Exception as exc:
        logger.error("MCP update_agent error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def update_agent_mcp_servers(
    agent_id: str,
    user_id: str,
    mcp_servers: Any,
) -> str:
    """Add or update MCP server connections for an agent.

    Each MCP server must be provided as a named entry inside the mcp_servers dict.
    The key is the alias you choose for the server (e.g. "calculator_sse").

    Required format for each server:
    {
      "<alias>": {
        "url": "http://<host>:<port>/sse",   -- required for sse/streamable_http
        "transport": "sse",                   -- "sse" | "streamable_http" | "stdio"
        "env": {},                             -- optional env vars dict
        "args": [],                            -- optional args list (for stdio)
        "headers": {}                          -- optional HTTP headers dict
      }
    }

    Example:
    {
      "calculator_sse": {
        "url": "http://194.238.23.242:8190/sse",
        "transport": "sse",
        "env": {},
        "args": [],
        "headers": {}
      }
    }

    This call MERGES the new servers with existing ones (existing servers
    not mentioned are kept). To remove a server, call this tool again
    with the full desired mcp_servers dict (omitting the server to remove).

    Args:
        agent_id:    UUID of the agent to update.
        user_id:     UUID of the owning user.
        mcp_servers: Dict mapping alias → server config (see format above).

    Returns:
        JSON with the updated mcp_servers configuration.
    """
    db = SessionLocal()
    try:
        _agent_uuid = _parse_uuid(agent_id, "agent_id")
        _user_uuid = _parse_uuid(user_id, "user_id")

        # Accept dict or JSON string
        servers_dict = _to_dict(mcp_servers)
        if not servers_dict:
            return json.dumps({"status": "error", "error": "mcp_servers must be a non-empty dict"})

        # Validate structure — every entry must have at least url+transport or command
        from app.schemas.agent import MCPServerConfig
        validated = {}
        for alias, cfg in servers_dict.items():
            if not isinstance(cfg, dict):
                return json.dumps({"status": "error", "error": f"Server '{alias}' config must be a dict"})
            try:
                server_cfg = MCPServerConfig(**cfg)
                validated[alias] = server_cfg.model_dump(mode="json", exclude_none=True)
            except Exception as ve:
                return json.dumps({"status": "error", "error": f"Invalid config for '{alias}': {ve}"})

        # Merge with existing mcp_servers
        service = AgentService(db)
        agent = service.get_agent(_agent_uuid, _user_uuid)
        existing = dict(agent.mcp_servers or {})
        existing.update(validated)
        agent.mcp_servers = existing

        db.commit()
        db.refresh(agent)

        return json.dumps({
            "status": "success",
            "agent_id": str(agent.id),
            "mcp_servers": agent.mcp_servers,
        })
    except Exception as exc:
        logger.error("MCP update_agent_mcp_servers error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def delete_agent(agent_id: str, user_id: str) -> str:
    """Delete an agent permanently.

    Args:
        agent_id: UUID of the agent to delete.
        user_id:  UUID of the owning user.

    Returns:
        JSON success or error.
    """
    db = SessionLocal()
    try:
        _agent_uuid = _parse_uuid(agent_id, "agent_id")
        _user_uuid = _parse_uuid(user_id, "user_id")
        service = AgentService(db)
        service.delete_agent(_agent_uuid, _user_uuid)
        return json.dumps({"status": "success", "message": "Agent deleted"})
    except Exception as exc:
        logger.error("MCP delete_agent error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


# =====================================================================
#  AGENT EXECUTION TOOLS
# =====================================================================

@mcp.tool()
async def execute_agent(
    query: str,
    agent_id: str,
    user_id: str,
    session_id: str = "",
    parameters: Any = None,
) -> str:
    """Execute an AI Staff agent with a query.

    Args:
        query:      The user's question or instruction for the agent.
        agent_id:   UUID of the agent to execute.
        user_id:    UUID of the owning user (for authorisation & quota).
        session_id: Optional session ID for conversation continuity.
        parameters: Optional dict or JSON string of additional parameters.

    Returns:
        The agent's textual response, or a JSON error object.
    """
    db = SessionLocal()
    try:
        _agent_uuid = _parse_uuid(agent_id, "agent_id")
        _user_uuid = _parse_uuid(user_id, "user_id")
        _params = _to_dict(parameters)

        service = ExecutionService(db)
        execution = await service.execute_agent(
            agent_id=_agent_uuid,
            user_id=_user_uuid,
            input_text=query,
            parameters=_params if _params else None,
            session_id=session_id if session_id else None,
        )

        # Build the response
        if execution.output:
            output_text = execution.output.get("output", "")
            error_text = execution.output.get("error", "")

            if error_text:
                return json.dumps({
                    "status": "error",
                    "error": error_text,
                    "execution_id": str(execution.id),
                })

            return output_text if isinstance(output_text, str) else json.dumps(output_text)

        return json.dumps({
            "status": str(execution.status.value),
            "execution_id": str(execution.id),
            "message": "Execution completed but produced no output.",
        })

    except Exception as exc:
        logger.error("MCP execute_agent error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def get_execution_history(agent_id: str, user_id: str) -> str:
    """Get execution history for an agent.

    Args:
        agent_id: UUID of the agent.
        user_id:  UUID of the owning user.

    Returns:
        JSON array of execution records with id, input, output, status, etc.
    """
    db = SessionLocal()
    try:
        _agent_uuid = _parse_uuid(agent_id, "agent_id")
        _user_uuid = _parse_uuid(user_id, "user_id")

        service = ExecutionService(db)
        executions = service.get_agent_executions(_agent_uuid, _user_uuid)

        return json.dumps({
            "status": "success",
            "executions": [
                {
                    "id": str(e.id),
                    "input": e.input,
                    "output": e.output,
                    "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
                    "duration_ms": e.duration_ms,
                    "error_message": e.error_message,
                    "created_at": str(e.created_at),
                }
                for e in executions
            ],
        }, default=str)
    except Exception as exc:
        logger.error("MCP get_execution_history error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def get_execution_stats(user_id: str) -> str:
    """Get execution statistics for a user across all agents.

    Args:
        user_id: UUID of the user.

    Returns:
        JSON with total_executions, completed, failed, success_rate, avg_duration.
    """
    db = SessionLocal()
    try:
        _user_uuid = _parse_uuid(user_id, "user_id")
        service = ExecutionService(db)
        stats = service.get_execution_stats(_user_uuid)

        return json.dumps({
            "status": "success",
            **stats,
        }, default=str)
    except Exception as exc:
        logger.error("MCP get_execution_stats error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def cancel_execution(execution_id: str, user_id: str) -> str:
    """Cancel a running or pending execution.

    Args:
        execution_id: UUID of the execution to cancel.
        user_id:      UUID of the owning user.

    Returns:
        JSON with updated execution status.
    """
    db = SessionLocal()
    try:
        _exec_uuid = _parse_uuid(execution_id, "execution_id")
        _user_uuid = _parse_uuid(user_id, "user_id")

        service = ExecutionService(db)
        execution = service.cancel_execution(_exec_uuid, _user_uuid)

        return json.dumps({
            "status": "success",
            "execution_id": str(execution.id),
            "execution_status": execution.status.value if hasattr(execution.status, 'value') else str(execution.status),
            "message": "Execution cancelled",
        })
    except Exception as exc:
        logger.error("MCP cancel_execution error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


# =====================================================================
#  AGENT DOCUMENTS TOOLS
# =====================================================================

@mcp.tool()
async def list_agent_documents(agent_id: str, user_id: str) -> str:
    """List uploaded documents for an agent.

    Args:
        agent_id: UUID of the agent.
        user_id:  UUID of the owning user.

    Returns:
        JSON array of upload records.
    """
    db = SessionLocal()
    try:
        _agent_uuid = _parse_uuid(agent_id, "agent_id")
        _user_uuid = _parse_uuid(user_id, "user_id")

        # Verify ownership
        agent_service = AgentService(db)
        agent_service.get_agent(_agent_uuid, _user_uuid)

        upload_service = UploadService(db)
        uploads = upload_service.list_uploads(_agent_uuid, _user_uuid)

        return json.dumps({
            "status": "success",
            "uploads": [
                {
                    "id": str(u.id),
                    "filename": u.filename,
                    "content_type": u.content_type,
                    "size_bytes": u.size_bytes,
                    "chunk_count": u.chunk_count,
                    "is_deleted": u.is_deleted,
                    "created_at": str(u.created_at),
                }
                for u in uploads
            ],
        })
    except Exception as exc:
        logger.error("MCP list_agent_documents error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def delete_agent_document(
    agent_id: str,
    upload_id: str,
    user_id: str,
) -> str:
    """Delete an uploaded document and its embeddings.

    Args:
        agent_id:  UUID of the agent.
        upload_id: UUID of the upload to delete.
        user_id:   UUID of the owning user.

    Returns:
        JSON confirmation of deletion.
    """
    db = SessionLocal()
    try:
        _agent_uuid = _parse_uuid(agent_id, "agent_id")
        _upload_uuid = _parse_uuid(upload_id, "upload_id")
        _user_uuid = _parse_uuid(user_id, "user_id")

        # Verify ownership
        agent_service = AgentService(db)
        agent_service.get_agent(_agent_uuid, _user_uuid)

        upload_service = UploadService(db)
        upload = upload_service.get_upload(_upload_uuid, _agent_uuid, _user_uuid)

        if not upload:
            return json.dumps({"status": "error", "error": "Upload not found"})

        upload_service.delete_upload(upload)

        return json.dumps({
            "status": "success",
            "message": "Document and embeddings deleted",
            "upload_id": str(_upload_uuid),
        })
    except Exception as exc:
        logger.error("MCP delete_agent_document error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


# =====================================================================
#  AGENT SYSTEM MESSAGE HISTORY
# =====================================================================

@mcp.tool()
async def get_agent_system_message_history(agent_id: str, user_id: str) -> str:
    """Get the history of system message changes for an agent.

    Args:
        agent_id: UUID of the agent.
        user_id:  UUID of the owning user.

    Returns:
        JSON array of historical system messages.
    """
    db = SessionLocal()
    try:
        _agent_uuid = _parse_uuid(agent_id, "agent_id")
        _user_uuid = _parse_uuid(user_id, "user_id")

        agent_service = AgentService(db)
        agent_service.get_agent(_agent_uuid, _user_uuid)  # verify access

        from app.models.agent_history import AgentSystemMessageHistory
        history = (
            db.query(AgentSystemMessageHistory)
            .filter(AgentSystemMessageHistory.agent_id == _agent_uuid)
            .order_by(AgentSystemMessageHistory.created_at.desc())
            .all()
        )

        return json.dumps({
            "status": "success",
            "history": [
                {
                    "id": str(entry.id),
                    "system_message": entry.system_message,
                    "created_at": str(entry.created_at),
                }
                for entry in history
            ],
        })
    except Exception as exc:
        logger.error("MCP get_agent_system_message_history error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


# =====================================================================
#  TOOL MANAGEMENT TOOLS
# =====================================================================

@mcp.tool()
async def list_tools(tool_type: str = "") -> str:
    """List all available tools, optionally filtered by type.

    Args:
        tool_type: Filter by type: builtin, custom, or empty for all.

    Returns:
        JSON array of tools with id, name, description, type.
    """
    db = SessionLocal()
    try:
        service = ToolService(db)
        tools = service.get_tools(tool_type if tool_type else None)

        return json.dumps({
            "status": "success",
            "tools": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "description": t.description,
                    "type": t.type.value if hasattr(t.type, 'value') else str(t.type),
                    "created_at": str(t.created_at),
                }
                for t in tools
            ],
        })
    except Exception as exc:
        logger.error("MCP list_tools error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def get_tool(tool_id: str) -> str:
    """Get details of a specific tool by its ID.

    Args:
        tool_id: UUID of the tool.

    Returns:
        JSON with tool details including schema.
    """
    db = SessionLocal()
    try:
        _tool_uuid = _parse_uuid(tool_id, "tool_id")
        service = ToolService(db)
        tool = service.get_tool(_tool_uuid)

        return json.dumps({
            "status": "success",
            "tool": {
                "id": str(tool.id),
                "name": tool.name,
                "description": tool.description,
                "schema": tool.schema,
                "type": tool.type.value if hasattr(tool.type, 'value') else str(tool.type),
                "created_at": str(tool.created_at),
            },
        })
    except Exception as exc:
        logger.error("MCP get_tool error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def get_tool_schema(tool_identifier: str) -> str:
    """Get the JSON schema for a tool (by ID or name).

    Args:
        tool_identifier: UUID or name of the tool.

    Returns:
        JSON schema of the tool.
    """
    db = SessionLocal()
    try:
        service = ToolService(db)
        schema = service.get_tool_schema(tool_identifier)
        return json.dumps({
            "status": "success",
            "schema": schema,
        })
    except Exception as exc:
        logger.error("MCP get_tool_schema error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def get_required_scopes(tool_names: Any) -> str:
    """Get required OAuth scopes for a list of tools.

    Args:
        tool_names: List of tool names, e.g. ["gmail", "google_sheets"].

    Returns:
        JSON array of required OAuth scope URLs.
    """
    db = SessionLocal()
    try:
        names = _to_list(tool_names)
        service = ToolService(db)
        scopes = service.get_required_scopes(names)
        return json.dumps({
            "status": "success",
            "scopes": scopes,
        })
    except Exception as exc:
        logger.error("MCP get_required_scopes error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def execute_tool(
    tool_identifier: str,
    user_id: str,
    parameters: Any = None,
    agent_id: str = "",
) -> str:
    """Execute a tool directly with given parameters.

    Args:
        tool_identifier: UUID or name of the tool to execute.
        user_id:         UUID of the user.
        parameters:      Dict or JSON string of tool parameters.
        agent_id:        Optional UUID of the agent context.

    Returns:
        JSON with tool execution result.
    """
    db = SessionLocal()
    try:
        _user_uuid = _parse_uuid(user_id, "user_id")
        _params = _to_dict(parameters)
        _agent_uuid = _parse_uuid(agent_id, "agent_id") if agent_id else None

        service = ToolService(db)
        result = service.execute_tool(
            tool_identifier=tool_identifier,
            parameters=_params,
            user_id=_user_uuid,
            agent_id=_agent_uuid,
        )

        return json.dumps({
            "status": "success",
            "result": result,
        }, default=str)
    except Exception as exc:
        logger.error("MCP execute_tool error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


# =====================================================================
#  USER MANAGEMENT TOOLS
# =====================================================================

@mcp.tool()
async def get_user_agent_slots(user_id: str) -> str:
    """Get agent slot information for a user.

    Args:
        user_id: UUID of the user.

    Returns:
        JSON with total_slots, used_slots, available_slots, plan_code.
    """
    db = SessionLocal()
    try:
        _user_uuid = _parse_uuid(user_id, "user_id")

        user = db.query(User).filter(User.id == _user_uuid).first()
        if not user:
            return json.dumps({"status": "error", "error": "User not found"})

        used_slots = db.query(Agent).filter(Agent.user_id == _user_uuid).count()

        from app.models.auth import ApiKey
        api_key = (
            db.query(ApiKey)
            .filter(
                ApiKey.user_id == _user_uuid,
                ApiKey.is_active == True,
                ApiKey.agent_id.is_(None),
            )
            .order_by(ApiKey.created_at.desc())
            .first()
        )

        plan_code = api_key.plan_code if api_key else "UNKNOWN"
        is_unlimited = user.agent_slots is None
        available_slots = None if is_unlimited else max(0, user.agent_slots - used_slots)

        return json.dumps({
            "status": "success",
            "total_slots": user.agent_slots,
            "used_slots": used_slots,
            "available_slots": available_slots,
            "plan_code": plan_code,
            "is_unlimited": is_unlimited,
        })
    except Exception as exc:
        logger.error("MCP get_user_agent_slots error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def update_user_agent_slots(
    user_id: str,
    agent_slots: int = -1,
) -> str:
    """Update agent slots for a user (admin action).

    Args:
        user_id:     UUID of the target user.
        agent_slots: Number of allowed agent slots (-1 for unlimited).

    Returns:
        JSON with updated slot information.
    """
    db = SessionLocal()
    try:
        _user_uuid = _parse_uuid(user_id, "user_id")

        user = db.query(User).filter(User.id == _user_uuid).first()
        if not user:
            return json.dumps({"status": "error", "error": "User not found"})

        user.agent_slots = None if agent_slots < 0 else agent_slots
        db.commit()
        db.refresh(user)

        used_slots = db.query(Agent).filter(Agent.user_id == _user_uuid).count()
        is_unlimited = user.agent_slots is None
        available_slots = None if is_unlimited else max(0, user.agent_slots - used_slots)

        return json.dumps({
            "status": "success",
            "total_slots": user.agent_slots,
            "used_slots": used_slots,
            "available_slots": available_slots,
            "is_unlimited": is_unlimited,
            "message": "Agent slots updated",
        })
    except Exception as exc:
        logger.error("MCP update_user_agent_slots error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


# =====================================================================
#  GOOGLE AUTH TOOLS
# =====================================================================

@mcp.tool()
async def check_google_auth(
    user_id: str,
    agent_id: str,
    tool_names: Any = None,
) -> str:
    """Check if a user has valid Google OAuth tokens for required tools.

    Args:
        user_id:    UUID of the user.
        agent_id:   UUID of the agent (optional - falls back to user-level if invalid/empty).
        tool_names: List of tool names that require Google auth.

    Returns:
        JSON with auth_required, auth_url if needed.
    """
    db = SessionLocal()
    try:
        names = _to_list(tool_names)
        tool_service = ToolService(db)
        required_scopes = tool_service.get_required_scopes(names)

        auth_service = AuthService(db)

        # Sanitize agent_id — LLMs sometimes hallucinate or provide stale/invalid UUIDs.
        # If agent_id is not a valid UUID, fall back to user-level token lookup.
        sanitized_agent_id: Optional[str] = None
        if agent_id:
            try:
                UUID(str(agent_id))
                sanitized_agent_id = agent_id
            except ValueError:
                logger.warning(
                    "check_google_auth MCP: invalid agent_id UUID, using user-level fallback",
                    agent_id=agent_id,
                )
                sanitized_agent_id = None

        # --- Pass 1: check agent-scoped tokens (or user-level if agent_id is invalid) ---
        result = auth_service.check_google_auth_requirement(
            user_id, sanitized_agent_id, required_scopes
        )

        if not result.get("auth_required", True):
            # Agent already has valid tokens — done.
            return json.dumps({"status": "success", **result})

        # --- Pass 2: fallback to user-level tokens (agent_id = None) ---
        # This covers the case where the user authenticated via the Langchain
        # /auth/me or /auth/google flow, where tokens are stored WITHOUT a
        # specific agent_id.  The original check_google_auth_requirement only
        # queries tokens that belong to the given agent_id, so it misses these.
        result_user_level = auth_service.check_google_auth_requirement(
            user_id, None, required_scopes  # type: ignore[arg-type]
        )

        if not result_user_level.get("auth_required", True):
            # User-level token is valid — report auth as not required so
            # Arthur does NOT send another auth link.
            logger.info(
                "check_google_auth: valid user-level token found (agent-scoped lookup missed)",
                user_id=user_id,
                agent_id=agent_id,
            )
            return json.dumps({
                "status": "success",
                "auth_required": False,
                "auth_url": None,
                "auth_state": None,
            })

        # Neither agent-level nor user-level token found — return auth URL
        # from the first result (already includes agent_id in OAuth state).
        return json.dumps({"status": "success", **result})
    except Exception as exc:
        logger.error("MCP check_google_auth error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def get_google_auth_url(
    user_id: str = "",
    agent_id: str = "",
    scopes: Any = None,
) -> str:
    """Generate a Google OAuth authorization URL.

    Args:
        user_id:  Optional UUID of the user.
        agent_id: Optional UUID of the agent.
        scopes:   List of OAuth scope URLs.

    Returns:
        JSON with auth_url and state.
    """
    db = SessionLocal()
    try:
        _scopes = _to_list(scopes)

        auth_service = AuthService(db)
        result = auth_service.create_google_auth_url(
            user_id=user_id if user_id else None,
            scopes=_scopes if _scopes else None,
            agent_id=agent_id if agent_id else None,
        )

        return json.dumps({
            "status": "success",
            **result,
        })
    except Exception as exc:
        logger.error("MCP get_google_auth_url error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


@mcp.tool()
async def get_user_auth_tokens(user_id: str, agent_id: str = "") -> str:
    """Get stored OAuth tokens for a user.

    Args:
        user_id:  UUID of the user.
        agent_id: Optional UUID of the agent to filter by.

    Returns:
        JSON array of auth tokens with service, scope, and expiration.
    """
    db = SessionLocal()
    try:
        auth_service = AuthService(db)
        tokens = auth_service.get_user_auth_tokens(
            user_id,
            agent_id=agent_id if agent_id else None,
        )

        return json.dumps({
            "status": "success",
            "tokens": [
                {
                    "id": str(t.id),
                    "service": t.service,
                    "scope": t.scope,
                    "expires_at": str(t.expires_at) if t.expires_at else None,
                    "created_at": str(t.created_at),
                }
                for t in tokens
            ],
        })
    except Exception as exc:
        logger.error("MCP get_user_auth_tokens error", error=str(exc))
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()


# ── Entry-point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    transport = "sse" if _early_args.sse else "stdio"

    logger.info(
        "Starting AIStaff MCP Server",
        transport=transport,
        host=_early_args.host if _early_args.sse else "n/a (stdio)",
        port=_early_args.port if _early_args.sse else "n/a (stdio)",
    )

    # host & port are already baked into the FastMCP instance (set at init time above)
    mcp.run(transport=transport)
