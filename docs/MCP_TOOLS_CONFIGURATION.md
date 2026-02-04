# MCP Tools Configuration Guide

## Overview

This document explains how MCP (Model Context Protocol) tools work alongside local Google Workspace tools in the LangChain API.

---

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                   LANGCHAIN AGENT                             │
│                                                               │
│  ┌──────────────────────┐         ┌──────────────────────┐  │
│  │   LOCAL TOOLS        │         │    MCP TOOLS         │  │
│  │   (Built-in)         │         │    (External)        │  │
│  │                      │         │                      │  │
│  │  • gmail_read        │         │  • web_search       │  │
│  │  • gmail_send        │         │  • database_query   │  │
│  │  • calendar_events   │         │  • custom_tools     │  │
│  │  • sheets_read       │         │  • file_operations  │  │
│  │  • drive_upload      │         │  • api_calls        │  │
│  │                      │         │                      │  │
│  │  Uses: OAuth tokens  │         │  Uses: MCP Protocol │  │
│  │  Direct Google APIs  │         │  SSE/HTTP           │  │
│  └──────────────────────┘         └──────────────────────┘  │
│           ↓                                  ↓                │
│    Google Workspace APIs          MCP Server (Port 8190)     │
└───────────────────────────────────────────────────────────────┘
```

---

## Configuration

### `.env` File

```bash
# MCP Server Configuration
MCP_SSE_URL=http://localhost:8190/sse
MCP_SSE_TOKEN=                          # Optional authentication token
MCP_SSE_ALLOWED_TOOLS=[]                # Empty = all MCP tools allowed

# Alternative: HTTP-based MCP (less common)
MCP_HTTP_URL=
MCP_HTTP_TOKEN=
MCP_HTTP_ALLOWED_TOOLS=[]
```

### Current Setup

**Status:** ✅ MCP Server Connected

- **URL:** `http://localhost:8190/sse`
- **Protocol:** Server-Sent Events (SSE)
- **Token:** None (local server, no auth needed)
- **Filter:** All MCP tools allowed (empty array)

---

## How It Works

### 1. Tool Resolution Flow

```python
# From execution_service.py line 656-704

def _resolve_mcp_connection_settings(agent, parameters):
    # 1. Check if agent only uses Google tools
    if agent.allowed_tools:
        non_google_tools = filter_google_workspace_tools(agent.allowed_tools)
        if not non_google_tools:
            return None  # ← Skip MCP, use local tools only
    
    # 2. Check for override in request parameters
    if parameters.get("mcp_sse_url"):
        return MCPConnectionSettings(...)
    
    # 3. Check agent's MCP server config
    if agent.mcp_servers:
        return connection_from_mapping(...)
    
    # 4. Fall back to environment defaults
    if settings.MCP_SSE_URL:
        return MCPConnectionSettings(
            sse_url=settings.MCP_SSE_URL,
            token=settings.MCP_SSE_TOKEN
        )  # ← This is now active!
    
    return None  # No MCP connection
```

### 2. Execution Logic

```python
# From execution_service.py line 406-462

# Phase 1: Try with MCP tools
if mcp_connection:
    async with mcp_agent_executor_context(...) as resources:
        combined_tools = local_tools + mcp_tools
        logger.info(
            "Launching LangChain agent with MCP tools",
            total_tools=len(combined_tools),
            mcp_tool_count=len(mcp_tools),
        )
        result = await resources.executor.ainvoke(...)

# Phase 2: Fallback to local tools only
else:
    combined_tools = local_tools  # Gmail, Calendar, etc.
    logger.info(
        "Launching LangChain agent without MCP tools",
        total_tools=len(combined_tools),
    )
    result = await executor.ainvoke(...)
```

---

## Testing MCP Connection

### 1. Test MCP Server Availability

```bash
# Check if MCP server is running
curl http://localhost:8190/sse

# Expected output:
# event: endpoint
# data: /messages/?session_id=<uuid>
```

### 2. Check Agent Execution Logs

**Before (MCP disabled):**
```json
{
  "event": "Launching LangChain agent without MCP tools",
  "total_tools": 2,
  "tool_names": ["gmail_read_messages", "gmail_send_message"]
}
```

**After (MCP enabled):**
```json
{
  "event": "Launching LangChain agent with MCP tools",
  "total_tools": 5,
  "mcp_tool_count": 3,
  "tool_names": [
    "gmail_read_messages",
    "gmail_send_message", 
    "web_search",
    "database_query",
    "file_operations"
  ]
}
```

### 3. Test Agent Execution

```bash
# Execute agent and check which tools are available
curl -X POST http://localhost:8000/api/v1/agents/{agent_id}/execute \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Search the web for latest AI news",
    "parameters": {}
  }'

# If MCP is working, agent will use web_search from MCP
# If MCP fails, it will only use local tools (Gmail, etc.)
```

---

## Tool Filtering

### Environment Level (Global)

```bash
# Only allow specific MCP tools
MCP_SSE_ALLOWED_TOOLS=["web_search", "database_query"]

# This applies to ALL agents unless overridden
```

### Agent Level (Per Agent)

**In Agent Config:**
```json
{
  "allowed_mcp_tools": ["web_search"],
  "mcp_tool_categories": ["search", "data"]
}
```

**In Request Parameters:**
```json
{
  "input": "Search for something",
  "parameters": {
    "mcp_tools": ["web_search"],
    "mcp_categories": ["search"]
  }
}
```

### Google Workspace Tools Exclusion

Google Workspace tools are **ALWAYS** filtered out from MCP:

```python
# From execution_service.py line 52-55, 72-84
GOOGLE_WORKSPACE_TOOL_NAMES = {
    "gmail", "gmail_read_messages", "gmail_send_message",
    "calendar_list_events", "calendar_create_event",
    "sheets_read_data", "sheets_write_data",
    "drive_list_files", "drive_upload_file",
    # etc...
}

# These tools ALWAYS use local OAuth-based implementation
# Never fetched from MCP server
```

**Why?** Google tools require OAuth authentication which is handled by the backend. MCP server doesn't have access to user's OAuth tokens.

---

## Troubleshooting

### Issue 1: "Launching without MCP tools" even after setting URL

**Cause:** MCP server not responding or connection failed

**Solutions:**
```bash
# 1. Check if MCP server is running
netstat -tulpn | grep 8190

# 2. Check MCP server logs
# (depends on your MCP server implementation)

# 3. Test connection manually
curl -v http://localhost:8190/sse

# 4. Check backend logs for MCP errors
tail -f logs/app.log | grep -i mcp
```

### Issue 2: MCP tools not appearing in tool list

**Cause:** Tool filter blocking MCP tools

**Solutions:**
```bash
# 1. Set MCP_SSE_ALLOWED_TOOLS to empty array (allow all)
MCP_SSE_ALLOWED_TOOLS=[]

# 2. Or explicitly allow tools
MCP_SSE_ALLOWED_TOOLS=["web_search", "database_query"]

# 3. Check agent's allowed_tools list
# If agent.allowed_tools only contains Google tools, MCP is skipped
```

### Issue 3: MCP connection timeout

**Cause:** MCP server slow or network issues

**Solutions:**
```bash
# Increase timeout in request parameters
{
  "parameters": {
    "mcp_request_timeout": 60.0,        # Default: 30s
    "mcp_connection_timeout": 600.0     # Default: 300s
  }
}
```

---

## Architecture Optimization

### Why Separate Local and MCP Tools?

1. **Performance**: 
   - Google tools use direct API calls (faster)
   - MCP adds network overhead (SSE connection)

2. **Security**:
   - Google tools use per-user OAuth tokens (secure)
   - MCP might use shared authentication

3. **Reliability**:
   - Google tools work offline (if MCP server is down)
   - Built-in tools have better error handling

4. **Flexibility**:
   - MCP allows custom tools without code changes
   - Can swap MCP server without backend changes

### Code References

| Function | Location | Purpose |
|----------|----------|---------|
| `_resolve_mcp_connection_settings()` | `execution_service.py:656` | Determine MCP server URL |
| `_resolve_mcp_tool_filter()` | `execution_service.py:739` | Filter which MCP tools to use |
| `_filter_google_workspace_tools()` | `execution_service.py:72` | Exclude Google tools from MCP |
| `mcp_agent_executor_context()` | `app/core/mcp_tools.py` | Connect to MCP and load tools |
| `get_default_connection_settings()` | `app/core/mcp_config.py:77` | Load MCP config from env |

---

## Configuration Examples

### Example 1: MCP Disabled (Google Tools Only)

```bash
# .env
MCP_SSE_URL=
MCP_SSE_TOKEN=
MCP_SSE_ALLOWED_TOOLS=[]
```

**Result:**
- ✅ Gmail, Calendar, Sheets, Drive tools available
- ❌ No web search, database, or custom MCP tools

### Example 2: MCP Enabled (All Tools)

```bash
# .env
MCP_SSE_URL=http://localhost:8190/sse
MCP_SSE_TOKEN=
MCP_SSE_ALLOWED_TOOLS=[]  # Empty = allow all
```

**Result:**
- ✅ Gmail, Calendar, Sheets, Drive tools available (local)
- ✅ Web search, database, custom tools available (MCP)
- Agent can use both local and MCP tools together

### Example 3: MCP with Tool Filtering

```bash
# .env
MCP_SSE_URL=http://localhost:8190/sse
MCP_SSE_TOKEN=my-secret-token
MCP_SSE_ALLOWED_TOOLS=["web_search", "brave_search"]
```

**Result:**
- ✅ Gmail, Calendar, etc. (local)
- ✅ Only web_search and brave_search from MCP
- ❌ Other MCP tools blocked

---

## Current Status

**MCP Configuration:**
- ✅ MCP Server URL: `http://localhost:8190/sse`
- ✅ MCP Server Status: **CONNECTED**
- ✅ Tool Filter: **ALL TOOLS ALLOWED**
- ✅ Authentication: **NONE** (local server)

**Next Execution:**
Agents will now launch with **BOTH** local Google tools AND MCP tools combined!

Expected log:
```json
{
  "event": "Launching LangChain agent with MCP tools",
  "agent_id": "...",
  "total_tools": 5,
  "mcp_tool_count": 3,
  "tool_names": [
    "gmail_read_messages",
    "gmail_send_message",
    "web_search",
    "database_query",
    "custom_tool"
  ]
}
```

---

**Last Updated:** 2026-02-02  
**MCP Server:** http://localhost:8190/sse  
**Status:** ✅ ACTIVE
