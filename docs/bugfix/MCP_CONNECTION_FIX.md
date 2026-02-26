# MCP Connection Fix: 0.0.0.0 vs localhost

## Issue

**Error in logs:**
```json
{
  "url": "http://0.0.0.0:8190/sse",
  "event": "MCP SSE connection failed 1/1: All connection attempts failed"
}
```

## Root Cause

**`0.0.0.0` is NOT a valid connection address!**

- ✅ **Server Bind:** `0.0.0.0` means "listen on all interfaces"
- ❌ **Client Connect:** Cannot connect TO `0.0.0.0` - it's not a real address

## Correct Configuration

### Your MCP Server Binding
```bash
# Your MCP server is running on:
http://0.0.0.0:8190/sse  # ← This is the BIND address
```

### Backend Connection URL
```bash
# Backend must connect using:
http://localhost:8190/sse  # ← Use localhost instead
# OR
http://127.0.0.1:8190/sse  # ← Or specific IP
```

## Solution

### Step 1: Verify `.env` File

**File:** `/home/bagas/Langchain-API-new/.env`

```bash
# CORRECT ✅
MCP_SSE_URL=http://localhost:8190/sse

# WRONG ❌
MCP_SSE_URL=http://0.0.0.0:8190/sse
```

**Current `.env` is CORRECT!** (Line 36 shows `localhost`)

### Step 2: Check Agent Configuration

Agent might have MCP config that overrides environment:

```sql
-- Check if agent has mcp_servers config
SELECT 
    id, 
    name, 
    config->>'mcp_sse_url' as config_mcp_url,
    mcp_servers
FROM agents 
WHERE id = '7e81f7c3-d3bc-4906-b8df-986f94c9ae9f';
```

If `mcp_servers` contains `0.0.0.0`, update it:

```sql
-- Fix agent's MCP config
UPDATE agents 
SET mcp_servers = jsonb_set(
    COALESCE(mcp_servers, '{}'::jsonb),
    '{default,url}',
    '"http://localhost:8190/sse"'
)
WHERE id = '7e81f7c3-d3bc-4906-b8df-986f94c9ae9f';
```

### Step 3: Restart Backend Server

**.env changes require server restart:**

```bash
# Stop existing server (Ctrl+C or kill process)
pkill -f "uvicorn app.main:app"

# Start fresh
uvicorn app.main:app --reload
```

## Resolution Priority

The backend checks MCP URL in this order:

1. **Request parameters** (`mcp_sse_url` in execute call)
2. **Agent's `mcp_servers` field** (database)
3. **Agent's `config.mcp_sse_url`** (database)
4. **Environment variable** (`MCP_SSE_URL` from `.env`) ← Should use this!

If agent has `mcp_servers` or `config.mcp_sse_url` with `0.0.0.0`, it will override correct `.env` value!

## Quick Fix Commands

```bash
# 1. Verify .env has localhost (already correct)
grep MCP_SSE_URL .env
# Should show: MCP_SSE_URL=http://localhost:8190/sse

# 2. Test MCP server is reachable on localhost
curl http://localhost:8190/sse
# Should return: event: endpoint

# 3. Restart backend
pkill -f uvicorn
uvicorn app.main:app --reload

# 4. Test agent execution
curl -X POST http://localhost:8000/api/v1/agents/7e81f7c3-d3bc-4906-b8df-986f94c9ae9f/execute \
  -H "Authorization: Bearer your-token" \
  -d '{"input": "search web for AI news"}'
```

## Expected Result After Fix

**Before:**
```json
{
  "url": "http://0.0.0.0:8190/sse",
  "event": "MCP SSE connection failed"
}
{
  "event": "Launching LangChain agent without MCP tools",
  "total_tools": 5,
  "tool_names": ["gmail_read_messages", "gmail_send_message", ...]
}
```

**After:**
```json
{
  "url": "http://localhost:8190/sse",
  "event": "Connecting to MCP SSE server"
}
{
  "event": "Launching LangChain agent with MCP tools",
  "total_tools": 8,
  "mcp_tool_count": 3,
  "tool_names": [
    "gmail_read_messages",
    "gmail_send_message",
    "web_search",  ← From MCP
    "brave_search",
    "..."
  ]
}
```

## Why 0.0.0.0 Doesn't Work

### Network Explanation

```
┌─────────────────────────────────────────────────┐
│  MCP Server                                     │
│  Binding: 0.0.0.0:8190                         │
│  (Listens on ALL interfaces)                   │
│                                                 │
│  Available on:                                 │
│  • localhost:8190      ✅                      │
│  • 127.0.0.1:8190      ✅                      │
│  • 192.168.1.x:8190    ✅ (LAN IP)            │
│  • 194.238.23.242:8190 ✅ (Public IP)         │
│                                                 │
│  NOT available on:                             │
│  • 0.0.0.0:8190        ❌ (Not an address!)   │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Backend (Client)                               │
│  Needs to connect TO a real address:           │
│                                                 │
│  ✅ http://localhost:8190/sse    (Same host)  │
│  ✅ http://127.0.0.1:8190/sse    (Loopback)   │
│  ❌ http://0.0.0.0:8190/sse      (Invalid!)   │
└─────────────────────────────────────────────────┘
```

`0.0.0.0` is a **meta-address** meaning "all available interfaces" - it's used ONLY for server binding, never for client connections.

## Code Reference

**Where the connection happens:**

`app/services/execution_service.py:406-442`
```python
if mcp_connection:
    async with mcp_agent_executor_context(
        connection=mcp_connection,  # ← Uses MCPConnectionSettings
        ...
    ) as resources:
```

**Where MCP URL is resolved:**

`app/services/execution_service.py:656-704`
```python
def _resolve_mcp_connection_settings(agent, parameters):
    # Priority 1: Parameters override
    override_url = parameters.get("mcp_sse_url")
    if override_url:
        return MCPConnectionSettings(sse_url=override_url, ...)
    
    # Priority 2: Agent mcp_servers config
    if agent.mcp_servers:
        ...
    
    # Priority 3: Agent config
    config_url = agent.config.get("mcp_sse_url")
    if config_url:
        return MCPConnectionSettings(sse_url=config_url, ...)
    
    # Priority 4: Environment default
    return get_default_connection_settings()  # ← Uses .env
```

**Where default is loaded:**

`app/core/mcp_config.py:77-85`
```python
def get_default_connection_settings():
    if not settings.MCP_SSE_URL:
        return None
    return MCPConnectionSettings(
        sse_url=settings.MCP_SSE_URL,  # ← From .env
        token=settings.MCP_SSE_TOKEN,
    )
```

---

**Status:** 🔄 Needs Server Restart  
**Issue:** Connection using `0.0.0.0` instead of `localhost`  
**Fix:** Restart backend after verifying `.env` has `localhost`  
**Date:** 2026-02-02
