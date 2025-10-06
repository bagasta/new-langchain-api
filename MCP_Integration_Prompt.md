# MCP Integration — Prompt for Codex (Schema A, n8n MCP Server) — **Keep Original Agent Payload**

**Goal:** Add **Model Context Protocol (MCP)** support to the existing FastAPI + LangChain project with **minimal database changes (Schema A)** while **preserving the current `Create Agent` payload structure**. The only changes to the API are two **optional** top‑level fields: `mcp_servers` and `allowed_tools`. If these are not provided, the system behaves exactly as before.

---

## 0) Backward‑Compatibility Requirement (VERY IMPORTANT)
- The current `Create Agent` payload **must continue to work** unchanged:
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/agents/" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
            "name": "Research Assistant",
            "tools": ["tool-id-1"],
            "config": {
              "llm_model": "gpt-4o-mini",
              "temperature": 0.7,
              "max_tokens": 1000,
              "memory_type": "buffer",
              "reasoning_strategy": "react",
              "system_prompt": "You are a helpful research aide. Remember the user'\''s name and refer back to earlier answers when possible."
            }
          }'
  ```
- We **extend** this payload with two **optional** top‑level fields for MCP support:
  - `mcp_servers`: MCP server registry for this agent (one or more servers).  
  - `allowed_tools`: whitelist of MCP tools (fully‑qualified names, e.g., `market.google_trends`).

**If `mcp_servers`/`allowed_tools` are omitted, load no MCP tools and keep legacy behavior.**

---

## 1) Dependencies
Add MCP adapter dependency and lock it in project config:
```bash
pip install langchain-mcp-adapters
```
Also update `requirements.txt` / `pyproject.toml` as appropriate.

---

## 2) Database Migration (Schema A, Alembic)
Create `alembic/versions/<timestamp>_add_mcp_fields_to_agents.py`:

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "<SET_ME>"
down_revision = "<FILL_PREVIOUS_REVISION_ID>"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column(
        "agents",
        sa.Column(
            "mcp_servers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "allowed_tools",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )

def downgrade():
    op.drop_column("agents", "allowed_tools")
    op.drop_column("agents", "mcp_servers")
```

Run:
```bash
alembic upgrade head
```

---

## 3) SQLAlchemy Model Update
In your `Agent` model (e.g., `app/models/agent.py`), add:
```python
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

mcp_servers = sa.Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
allowed_tools = sa.Column(ARRAY(sa.String()), nullable=False, server_default="{}")
```

---

## 4) Pydantic Schemas
In `app/schemas/agent.py` (or equivalent), extend DTOs:

```python
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AgentBase(BaseModel):
    name: str
    tools: List[str] = Field(default_factory=list)  # existing internal tool IDs
    config: Dict[str, Any]
    # NEW (optional)
    mcp_servers: Dict[str, Any] = Field(default_factory=dict, description="MultiServerMCPClient config per server alias")
    allowed_tools: List[str] = Field(default_factory=list, description="Whitelist MCP tool names, e.g. 'market.google_trends'")

class AgentCreate(AgentBase):
    pass

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    tools: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    # NEW (optional)
    mcp_servers: Optional[Dict[str, Any]] = None
    allowed_tools: Optional[List[str]] = None

class AgentOut(AgentBase):
    id: str
    class Config:
        orm_mode = True
```

> Keep any other existing fields you already had on `AgentBase/AgentOut`.

---

## 5) CRUD / Repository
Ensure create/update persist the new fields with safe defaults:

```python
# app/crud/agent.py
def create_agent(db, data: AgentCreate):
    obj = Agent(
        name=data.name,
        # existing fields...
        tools=data.tools or [],
        config=data.config or {},
        # NEW
        mcp_servers=data.mcp_servers or {},
        allowed_tools=data.allowed_tools or [],
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def update_agent(db, agent: Agent, data: AgentUpdate):
    for f, v in data.dict(exclude_unset=True).items():
        setattr(agent, f, v)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent
```

---

## 6) MCP Integration Module
Create `app/integrations/mcp.py`:

```python
# app/integrations/mcp.py
from typing import Dict, List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools.base import BaseTool

async def load_mcp_tools(servers_cfg: Dict, allowed_tools: Optional[List[str]] = None) -> List[BaseTool]:
    """
    servers_cfg example:
    {
      "market": {
        "transport": "streamable_http",
        "url": "https://n8n.example.com/mcp/market/sse",
        "headers": {"Authorization": "Bearer TENANT_123"}
      },
      "viz": {
        "transport": "stdio",
        "command": "node",
        "args": ["dist/mcp-viz.js"]
      }
    }
    """
    if not servers_cfg:
        return []
    client = MultiServerMCPClient(servers_cfg)
    tools = await client.get_tools()  # LangChain BaseTool instances
    if allowed_tools:
        allow = set(allowed_tools)
        tools = [t for t in tools if getattr(t, "name", "") in allow]
    return tools
```

---

## 7) Agent Runtime Builder
Where you construct an agent (e.g., `app/services/agent_runtime.py`), merge built‑in tools with MCP tools. **Do not change how internal tools are loaded.** Only add MCP tools when present:

```python
from langgraph.prebuilt import create_react_agent
from app.integrations.mcp import load_mcp_tools

async def build_agent_from_row(db_agent, builtin_tools, llm):
    # builtin_tools: your existing resolved internal tools (from db_agent.tools)
    mcp_tools = await load_mcp_tools(
        servers_cfg=db_agent.mcp_servers or {},
        allowed_tools=db_agent.allowed_tools or [],
    )
    tools = list(builtin_tools) + list(mcp_tools)
    agent = create_react_agent(llm, tools=tools)
    return agent
```

> If `db_agent.mcp_servers` is `{}` or missing, `mcp_tools` will be `[]`, so behavior is unchanged.

---

## 8) API Endpoints (Create/Update)
- `POST /agents` and `PATCH /agents/{id}` must accept/return the **new optional** fields `mcp_servers`, `allowed_tools`.
- Validate minimal config per server:
  - For `streamable_http`: require `url` (SSE endpoint). `headers` is optional.
  - For `stdio`: require `command`; optional `args` list.

**Do not break existing clients** that only send `name`, `tools`, and `config`.

---

## 9) Example Payloads

### 9.1 Original (unchanged — must still work)
```bash
curl -X POST "$BASE_URL$API_PREFIX/agents/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Research Assistant",
        "tools": ["tool-id-1"],
        "config": {
          "llm_model": "gpt-4o-mini",
          "temperature": 0.7,
          "max_tokens": 1000,
          "memory_type": "buffer",
          "reasoning_strategy": "react",
          "system_prompt": "You are a helpful research aide. Remember the user'\''s name and refer back to earlier answers when possible."
        }
      }'
```

### 9.2 Extended with **one** MCP server (n8n via SSE)
```bash
curl -X POST "$BASE_URL$API_PREFIX/agents/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Research Assistant",
        "tools": ["tool-id-1"],
        "config": {
          "llm_model": "gpt-4o-mini",
          "temperature": 0.7,
          "max_tokens": 1000,
          "memory_type": "buffer",
          "reasoning_strategy": "react",
          "system_prompt": "You are a helpful research aide. Remember the user'\''s name and refer back to earlier answers when possible."
        },
        "mcp_servers": {
          "market": {
            "transport": "streamable_http",
            "url": "https://n8n.example.com/mcp/market/sse",
            "headers": { "Authorization": "Bearer TENANT_ABC" }
          }
        },
        "allowed_tools": [
          "market.google_trends",
          "market.shopee_scrape"
        ]
      }'
```

### 9.3 Extended with **two** MCP servers
```bash
curl -X POST "$BASE_URL$API_PREFIX/agents/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Market Insights Agent",
        "tools": ["tool-id-1", "tool-id-2"],
        "config": {
          "llm_model": "gpt-4o-mini",
          "temperature": 0.5,
          "max_tokens": 1200,
          "memory_type": "buffer",
          "reasoning_strategy": "react",
          "system_prompt": "You synthesize market signals and visualize quickly."
        },
        "mcp_servers": {
          "market": {
            "transport": "streamable_http",
            "url": "https://n8n.example.com/mcp/market/sse",
            "headers": { "Authorization": "Bearer TENANT_ABC" }
          },
          "viz": {
            "transport": "streamable_http",
            "url": "https://n8n.example.com/mcp/viz/sse"
          }
        },
        "allowed_tools": [
          "market.google_trends",
          "market.shopee_scrape",
          "viz.quickchart"
        ]
      }'
```

---

## 10) Optional: Dry‑Run Tool Endpoint (for quick connectivity test)
```python
# app/api/routes/agents.py (example)
from fastapi import APIRouter, Depends, HTTPException
from app.db import get_db
from app.crud.agent import get_agent_by_id
from app.services.agent_runtime import build_agent_from_row
from app.services.llm import get_llm

router = APIRouter()

@router.post("/agents/{agent_id}/dry-run-tool")
async def dry_run_tool(agent_id: str, tool_name: str, args: dict, db=Depends(get_db)):
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(404, "agent not found")
    lc_agent = await build_agent_from_row(agent, builtin_tools=[], llm=get_llm())
    tool = next((t for t in lc_agent.tools if getattr(t, "name", "") == tool_name), None)
    if not tool:
        raise HTTPException(404, f"tool {tool_name} not found")
    result = await tool.ainvoke(args)
    return {"ok": True, "result": result}
```

---

## 11) Security & Guardrails (minimum)
- Always enforce **least privilege**: filter MCP tools by `allowed_tools` per agent.
- Validate minimal fields per server (`url` for `streamable_http`; `command` for `stdio`).
- Consider per‑tool execution timeout/retry policies to protect your service.
- Namespaces: recommend prefixing tool names by server alias (e.g., `market.*`, `viz.*`) to avoid collisions.

---

## 12) Deliverables Codex Must Produce
1) Alembic migration for Schema A and upgraded successfully  
2) Updated SQLAlchemy `Agent` model (two new columns)  
3) Updated Pydantic schemas (create/update/out) including the two optional fields  
4) Updated CRUD to persist the two fields with safe defaults  
5) New `app/integrations/mcp.py` that loads & filters MCP tools  
6) Agent builder updated to merge built‑in tools with MCP tools when present  
7) API docs/examples updated with payloads in section **9**  
8) No breaking changes to existing clients that only send `name`, `tools`, and `config`

---

## 13) n8n MCP Notes (for `streamable_http`)
- `url` should point to the **SSE endpoint** exposed by n8n’s MCP Server Trigger.
- If protected, include `headers` (e.g., `Authorization: Bearer <token>`).
- Ensure reverse proxy settings support SSE (no proxy buffering; keep-alive).

---

## 14) Test Checklist
- [ ] Create agent with original payload (no MCP fields) → success, runs with built‑in tools only.  
- [ ] Create agent with one MCP server and a couple of `allowed_tools` → MCP tools are available and callable.  
- [ ] Create agent with two MCP servers → union of selected tools is available.  
- [ ] Invalid MCP config → 422 with helpful error.  
- [ ] Missing/unknown tool in `allowed_tools` → excluded gracefully.  
- [ ] Dry‑run endpoint can call a selected MCP tool and returns output.  