# API Guide

## Authentication

### JWT Authentication

All API endpoints (except registration and login) require JWT authentication.

```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### Using the Token

Include the token in the Authorization header:
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Agent Management

### Create Agent

```bash
curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Email Assistant",
    "tools": ["gmail", "google_sheets"],
    "config": {
      "llm_model": "gpt-3.5-turbo",
      "temperature": 0.7,
      "max_tokens": 1000,
      "memory_type": "buffer",
      "reasoning_strategy": "react"
    },
    "mcp_servers": {
      "market": {
        "transport": "streamable_http",
        "url": "https://n8n.example.com/mcp/market/sse",
        "headers": {"Authorization": "Bearer TENANT_ABC"}
      }
    },
    "allowed_tools": ["market.google_trends", "market.shopee_scrape"]
  }'
```

> Both `mcp_servers` and `allowed_tools` are optional; omit them to keep the legacy built-in tool behavior.

### List Agents

```bash
curl -X GET "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Agent Details

```bash
curl -X GET "http://localhost:8000/api/v1/agents/{agent_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Agent

```bash
curl -X PUT "http://localhost:8000/api/v1/agents/{agent_id}" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Email Assistant",
    "tools": ["gmail"]
  }'
```

### Delete Agent

```bash
curl -X DELETE "http://localhost:8000/api/v1/agents/{agent_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Agent Execution

### Execute Agent

```bash
curl -X POST "http://localhost:8000/api/v1/agents/{agent_id}/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Read my latest emails and summarize them",
    "parameters": {
      "max_results": 10
    }
  }'
```

### Get Execution History

```bash
curl -X GET "http://localhost:8000/api/v1/agents/{agent_id}/executions" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Tool Management

### List Available Tools

```bash
curl -X GET "http://localhost:8000/api/v1/tools" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Built-in Tools Only

```bash
curl -X GET "http://localhost:8000/api/v1/tools?tool_type=builtin" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create Custom Tool

```bash
curl -X POST "http://localhost:8000/api/v1/tools" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "weather_api",
    "description": "Get weather information",
    "schema": {
      "type": "object",
      "properties": {
        "city": {
          "type": "string",
          "description": "City name"
        },
        "units": {
          "type": "string",
          "enum": ["celsius", "fahrenheit"],
          "default": "celsius"
        }
      },
      "required": ["city"]
    },
    "type": "custom"
  }'
```

### Execute Tool Directly

```bash
curl -X POST "http://localhost:8000/api/v1/tools/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "gmail",
    "parameters": {
      "action": "list",
      "max_results": 5
    }
  }'
```

## Google OAuth Integration

### Initiate Google OAuth

```bash
curl -X POST "http://localhost:8000/api/v1/auth/google/auth" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@gmail.com"}'
```

Response:
```json
{
  "auth_url": "https://accounts.google.com/oauth?...",
  "state": "uuid-string"
}
```

### Get User Tokens

```bash
curl -X GET "http://localhost:8000/api/v1/auth/tokens" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Tool Schemas

### Gmail Tool

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "read",
        "search",
        "send",
        "create_draft",
        "get_thread",
        "send_message",
        "list",
        "get_message"
      ],
      "description": "Action to perform (optional; inferred from other fields when omitted)"
    },
    "email_id": {
      "type": "string",
      "description": "Email ID for reading"
    },
    "to": {
      "type": "string",
      "description": "Recipient email"
    },
    "subject": {
      "type": "string",
      "description": "Email subject"
    },
    "body": {
      "type": "string",
      "description": "Email body"
    },
    "message": {
      "type": "string",
      "description": "Alias for the email body used by LangChain's GmailSendMessage"
    },
    "is_html": {
      "type": "boolean",
      "description": "When true the message body is sent as HTML"
    },
    "cc": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Optional CC recipients for send/create_draft"
    },
    "bcc": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Optional BCC recipients for send/create_draft"
    },
    "max_results": {
      "type": "integer",
      "default": 10,
      "description": "Maximum number of emails to list"
    },
    "query": {
      "type": "string",
      "description": "Search query when listing emails"
    },
    "mark_as_read": {
      "type": "boolean",
      "default": false,
      "description": "When reading, remove the UNREAD label from returned messages"
    },
    "label_ids": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Optional label filters for searches"
    },
    "thread_id": {
      "type": "string",
      "description": "Thread identifier for get_thread"
    },
    "format": {
      "type": "string",
      "description": "Message format when retrieving a single email (minimal|full|raw|metadata)",
      "default": "full"
    }
  },
  "required": []
}
```

- `read` defaults to the most recent matching message when `email_id` is omitted (respecting any `query`, `label_ids`, or `max_results` filters).
- `search` mirrors LangChain's `GmailSearch` tool by returning message metadata (IDs, senders, subjects) without requiring an explicit action parameter.
- `get_message` fetches a single email by ID using the requested Gmail format (`full`, `metadata`, `minimal`, or `raw`).
- `send`/`create_draft` align with LangChain's `GmailSendMessage`/`GmailCreateDraft`, expecting `message`, `subject`, and `to` (with optional `cc`/`bcc`).
- `create_draft` and `get_thread` mirror the Gmail toolkit endpoints documented in LangChain, so the agent can draft emails or retrieve whole threads when needed.
- Sending mail requires Gmail send/compose scopes (`gmail.send`, `gmail.compose`, or `mail.google.com`). If they are missing, reconnect your Google account via the provided OAuth link.

### Google Calendar Tool

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["list_events", "create_event", "get_event"],
      "description": "Action to perform (optional; inferred from other fields when omitted)"
    },
    "calendar_id": {
      "type": "string",
      "description": "Calendar ID (default 'primary')"
    },
    "max_results": {
      "type": "integer",
      "default": 10,
      "description": "Maximum number of events to list"
    },
    "time_min": {
      "type": "string",
      "description": "RFC3339 lower bound when listing events"
    },
    "time_max": {
      "type": "string",
      "description": "RFC3339 upper bound when listing events"
    },
    "summary": {
      "type": "string",
      "description": "Event title (create_event)"
    },
    "description": {
      "type": "string",
      "description": "Event description"
    },
    "location": {
      "type": "string",
      "description": "Event location"
    },
    "start": {
      "type": "string",
      "description": "Event start in RFC3339 or YYYY-MM-DD format"
    },
    "end": {
      "type": "string",
      "description": "Event end in RFC3339 or YYYY-MM-DD format"
    },
    "time_zone": {
      "type": "string",
      "description": "Time zone used when start/end contain dateTime values"
    },
    "attendees": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Optional attendee email addresses"
    },
    "event_id": {
      "type": "string",
      "description": "Event ID for get_event"
    }
  },
  "required": []
}
```

- `list_events` returns upcoming events (optionally filtered by time range).
- `create_event` accepts summary/start/end (and optional metadata) to add a calendar entry.
- `get_event` fetches a single event by ID.

### Google Sheets Tool

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["read", "write", "create"],
      "description": "Action to perform (optional; inferred from other fields when omitted)"
    },
    "spreadsheet_id": {
      "type": "string",
      "description": "Spreadsheet ID"
    },
    "range": {
      "type": "string",
      "description": "Sheet range (e.g., 'Sheet1!A1:D10')"
    },
    "values": {
      "type": "array",
      "description": "Values to write"
    },
    "title": {
      "type": "string",
      "description": "Sheet title"
    }
  },
  "required": []
}
```

### CSV Tool

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["read", "write"],
      "description": "Action to perform"
    },
    "file_path": {
      "type": "string",
      "description": "Path to CSV file"
    },
    "data": {
      "type": "array",
      "description": "Data to write"
    },
    "delimiter": {
      "type": "string",
      "default": ",",
      "description": "CSV delimiter"
    },
    "encoding": {
      "type": "string",
      "default": "utf-8",
      "description": "File encoding"
    }
  },
  "required": ["action", "file_path"]
}
```

## Error Handling

The API returns standard HTTP status codes and error messages:

```json
{
  "detail": "Error message describing the issue"
}
```

Common status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

## Rate Limiting

The API implements rate limiting:
- Default: 10 requests per second
- Burst: 20 requests
- Per-IP basis

## Webhooks

Long-running operations support webhooks for async notifications:

```bash
curl -X POST "http://localhost:8000/api/v1/agents/{agent_id}/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Complex task",
    "webhook_url": "https://your-webhook.com/notify"
  }'
```

## SDK Examples

### Python SDK

```python
import requests
import json

class LangChainAPI:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def login(self, email, password):
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        return self.token

    def create_agent(self, name, tools=None, config=None):
        response = requests.post(
            f"{self.base_url}/api/v1/agents",
            headers=self.headers,
            json={
                "name": name,
                "tools": tools or [],
                "config": config or {}
            }
        )
        return response.json()

    def execute_agent(self, agent_id, input_text, parameters=None):
        response = requests.post(
            f"{self.base_url}/api/v1/agents/{agent_id}/execute",
            headers=self.headers,
            json={
                "input": input_text,
                "parameters": parameters or {}
            }
        )
        return response.json()

# Usage
api = LangChainAPI()
api.login("user@example.com", "password")

agent = api.create_agent(
    name="Email Assistant",
    tools=["gmail"],
    config={"llm_model": "gpt-3.5-turbo"}
)

result = api.execute_agent(agent["id"], "Read my latest emails")
print(result)
```

### JavaScript SDK

```javascript
class LangChainAPI {
    constructor(baseUrl = 'http://localhost:8000', token = null) {
        this.baseUrl = baseUrl;
        this.token = token;
    }

    async login(email, password) {
        const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
        });
        const data = await response.json();
        this.token = data.access_token;
        return this.token;
    }

    async createAgent(name, tools = [], config = {}) {
        const response = await fetch(`${this.baseUrl}/api/v1/agents`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`,
            },
            body: JSON.stringify({ name, tools, config }),
        });
        return response.json();
    }

    async executeAgent(agentId, input, parameters = {}) {
        const response = await fetch(`${this.baseUrl}/api/v1/agents/${agentId}/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`,
            },
            body: JSON.stringify({ input, parameters }),
        });
        return response.json();
    }
}

// Usage
const api = new LangChainAPI();
await api.login('user@example.com', 'password');

const agent = await api.createAgent('Email Assistant', ['gmail']);
const result = await api.executeAgent(agent.id, 'Read my latest emails');
console.log(result);
```
