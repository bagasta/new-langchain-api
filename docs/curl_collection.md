# LangChain API cURL Collection

This document provides a comprehensive collection of cURL commands for interacting with the LangChain Agent API.

## Prerequisites

Set the following environment variables for convenience:

```bash
export API_URL="http://localhost:8000/api/v1"
export TOKEN="your_jwt_token_here"
```

## Authentication

### Register a New User
```bash
curl -X POST "$API_URL/auth/register?email=user@example.com&password=securepassword123" \
  -H "accept: application/json"
```

### Login
```bash
curl -X POST "$API_URL/auth/login?email=user@example.com&password=securepassword123" \
  -H "accept: application/json"
```
*Response will contain the `jwt_token`. Export this as `TOKEN`.*

### Get Current User Profile (with Stats)
```bash
curl -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

### Google Auth Initiation
```bash
curl -X GET "$API_URL/auth/google/login?tools=gmail,google_calendar" \
  -H "accept: application/json"
```

## Agents Management

### Create an Agent
```bash
curl -X POST "$API_URL/agents/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Research Agent",
    "tools": ["web_search", "calculator"],
    "google_tools": ["gmail_read_messages"],
    "token_limit": 10000,
    "config": {
        "llm_model": "gpt-4",
        "temperature": 0.5,
        "system_prompt": "You are a helpful research assistant."
    }
  }'
```

### List User Agents
```bash
curl -X GET "$API_URL/agents/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

### Get Specific Agent
```bash
curl -X GET "$API_URL/agents/{agent_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

### Update Agent
```bash
curl -X PUT "$API_URL/agents/{agent_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Agent Name",
    "config": {
        "temperature": 0.8,
        "system_prompt": "You are now a creative writer."
    }
  }'
```

### Delete Agent
```bash
curl -X DELETE "$API_URL/agents/{agent_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

### Publish Agent (Get API Key)
```bash
curl -X POST "$API_URL/agents/{agent_id}/publish" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

### Get Agent System Message History
```bash
curl -X GET "$API_URL/agents/{agent_id}/history/system-messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

## Documents / RAG

### Upload Document
```bash
curl -X POST "$API_URL/agents/{agent_id}/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json" \
  -F "file=@/path/to/document.pdf" \
  -F "chunk_size=1000" \
  -F "chunk_overlap=200"
```

### List Documents
```bash
curl -X GET "$API_URL/agents/{agent_id}/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

### Delete Document
```bash
curl -X DELETE "$API_URL/agents/{agent_id}/documents/{upload_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

## Agent Execution

### Execute Agent
```bash
curl -X POST "$API_URL/agents/{agent_id}/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Summarize the last email I received.",
    "session_id": "optional-session-id"
  }'
```

### Get Agent Execution History
```bash
curl -X GET "$API_URL/agents/{agent_id}/executions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

### Get Overall Execution Stats
```bash
curl -X GET "$API_URL/agents/executions/stats" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

## Tools

### List Available Tools
```bash
curl -X GET "$API_URL/tools/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

### Get Tool Schema
```bash
curl -X GET "$API_URL/tools/schemas/gmail_send_message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

### Execute Tool Directly
```bash
curl -X POST "$API_URL/tools/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "tool_uuid_here",
    "parameters": {
        "param1": "value1"
    }
  }'
```

### Create Custom Tool
```bash
curl -X POST "$API_URL/tools/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "custom_search",
    "description": "Searches a specific internal database",
    "type": "custom",
    "schema_definition": {
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        }
    }
  }'
```

## User Management

### Get My Agent Slots Info
```bash
curl -X GET "$API_URL/users/me/agent-slots" \
  -H "Authorization: Bearer $TOKEN" \
  -H "accept: application/json"
```

### Update User Agent Slots
```bash
# Set to specific number (e.g., 5 slots)
curl -X PATCH "$API_URL/users/{user_id}/agent-slots" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_slots": 5
  }'

# Set to unlimited (null)
curl -X PATCH "$API_URL/users/{user_id}/agent-slots" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_slots": null
  }'
```
