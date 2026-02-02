# Product Requirement Document (PRD)
## LangChain Agent API Platform

---

## Document Information

| Item | Details |
|------|---------|
| **Document Type** | Product Requirement Document |
| **Project Name** | LangChain Agent API |
| **Version** | 1.0 |
| **Date** | February 2, 2026 |
| **Status** | Active |
| **Owner** | Product & Engineering Team |

---

## 1. Product Overview

### 1.1 Product Vision
Menciptakan platform API yang paling developer-friendly untuk mengintegrasikan AI agents ke dalam aplikasi apapun, dengan fokus pada:
- **Simplicity**: Setup dalam hitungan menit
- **Power**: Enterprise-grade features dan customization
- **Reliability**: Production-ready infrastructure

### 1.2 Product Mission
Memberdayakan setiap developer untuk membangun intelligent applications tanpa perlu menjadi AI expert atau mengelola complex infrastructure.

### 1.3 Product Positioning
**"The fastest way to add AI agents to your application"**

**Target Users**: 
- SaaS developers yang ingin add AI capabilities
- Automation agencies yang build client solutions
- Enterprise teams yang butuh scalable AI infrastructure

**What we are**:
- ✅ Developer-first AI agent platform
- ✅ Production-ready API infrastructure
- ✅ Flexible tool integration system

**What we are NOT**:
- ❌ No-code chatbot builder
- ❌ LLM training platform
- ❌ Data analytics service

---

## 2. Product Goals & Success Metrics

### 2.1 Product Goals

#### Goal 1: Developer Onboarding Experience
**Objective**: Enable developers to create their first agent dalam <10 menit

**Success Metrics**:
- Time-to-first-agent: <10 minutes (p90)
- First execution success rate: >95%
- Documentation satisfaction: >4.5/5

**How to Measure**:
- Event tracking pada sign-up → first agent → first execution
- User feedback surveys
- Support ticket analysis

#### Goal 2: API Reliability
**Objective**: Maintain production-grade reliability untuk paying customers

**Success Metrics**:
- Uptime: 99.9%
- Error rate: <0.1%
- P95 response time: <500ms

**How to Measure**:
- APM monitoring (DataDog/New Relic)
- Automated health checks
- Incident tracking

#### Goal 3: Feature Adoption
**Objective**: Drive adoption of premium features (RAG, custom tools, MCP)

**Success Metrics**:
- 40% users create custom tools
- 30% users upload RAG documents
- 20% users configure MCP servers

**How to Measure**:
- Feature usage analytics
- Cohort analysis
- User behavior tracking

### 2.2 Key Performance Indicators

#### Product Health Metrics
| Metric | Current | Target (3mo) | Target (6mo) |
|--------|---------|--------------|--------------|
| **Active Agents** | 0 | 500 | 2,000 |
| **Daily Executions** | 0 | 1,000 | 5,000 |
| **Avg Tools per Agent** | 0 | 3 | 4 |
| **Session Length** | 0 | 5 turns | 8 turns |

#### User Engagement
| Metric | Target |
|--------|--------|
| **WAU (Weekly Active Users)** | 60% of registered |
| **Stickiness (DAU/MAU)** | >30% |
| **Feature Discovery** | >50% try 2+ tools |
| **API Error Recovery** | <2% user-facing errors |

---

## 3. User Stories & Use Cases

### 3.1 Primary User Stories

#### Epic 1: Authentication & Onboarding

**US-1.1: User Registration**
```
As a developer
I want to register dengan email dan password
So that saya bisa access the platform securely

Acceptance Criteria:
✅ Email format validation
✅ Password strength requirements (min 8 chars, 1 uppercase, 1 number)
✅ Duplicate email prevention
✅ Email confirmation (optional for MVP)
✅ Return user_id dan user info (not API key)

Story Points: 3
Priority: P0 (Must Have)
```

**US-1.2: API Key Generation**
```
As a registered user
I want to generate API key dengan plan selection
So that saya bisa authenticate API requests

Acceptance Criteria:
✅ Support plan types: GUEST, PRO_M, PRO_Y
✅ PRO_M expires dalam 30 hari
✅ PRO_Y expires dalam 365 hari
✅ Return API key, expiration date, dan JWT token
✅ Allow multiple API keys per user
✅ Show expiration warnings

Story Points: 5
Priority: P0 (Must Have)
```

**US-1.3: Google OAuth Integration**
```
As a user who wants Google Workspace features
I want to authorize Google account via OAuth
So that agents can access my Gmail, Sheets, Calendar

Acceptance Criteria:
✅ Initiate OAuth flow dengan /auth/google/auth
✅ Dynamic scope generation based on selected tools
✅ Handle OAuth callback dengan state validation
✅ Store encrypted tokens dalam database
✅ Automatic token refresh when expired
✅ Handle scope changes gracefully

Story Points: 8
Priority: P0 (Must Have)
```

#### Epic 2: Agent Management

**US-2.1: Create Agent**
```
As a developer
I want to create an AI agent dengan custom configuration
So that saya bisa deploy intelligent automation

Acceptance Criteria:
✅ Specify agent name (required)
✅ Select tools from available list
✅ Configure LLM settings (model, temperature, max_tokens)
✅ Set custom system prompt
✅ Return agent_id dan configuration
✅ If Google tools selected, return OAuth URL
✅ Validate tool availability

Story Points: 8
Priority: P0 (Must Have)

Example Request:
{
  "name": "Email Assistant",
  "tools": ["gmail", "web_search"],
  "config": {
    "llm_model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1000,
    "system_prompt": "You are a helpful email assistant"
  }
}
```

**US-2.2: List User Agents**
```
As a developer
I want to view all my created agents
So that saya bisa manage dan monitor them

Acceptance Criteria:
✅ List all agents for authenticated user
✅ Show agent name, tools, creation date
✅ Show token usage statistics
✅ Paginate results (default 20 per page)
✅ Support filtering by status (active/inactive)

Story Points: 3
Priority: P0 (Must Have)
```

**US-2.3: Update Agent**
```
As a developer
I want to update agent configuration
So that saya bisa improve agent behavior

Acceptance Criteria:
✅ Update system prompt
✅ Add/remove tools
✅ Change LLM settings
✅ Preserve execution history
✅ Validate new configuration
✅ Re-trigger OAuth if new Google tools added

Story Points: 5
Priority: P0 (Must Have)
```

**US-2.4: Delete Agent**
```
As a developer
I want to delete an agent
So that saya bisa clean up unused resources

Acceptance Criteria:
✅ Soft delete (preserve data)
✅ Prevent execution after deletion
✅ Preserve execution history untuk analytics
✅ Confirm deletion action
✅ Return success message

Story Points: 3
Priority: P1 (Should Have)
```

#### Epic 3: Agent Execution

**US-3.1: Execute Agent**
```
As a developer
I want to execute an agent dengan user input
So that saya bisa get AI-powered responses

Acceptance Criteria:
✅ Accept text input dan optional parameters
✅ Support session_id untuk conversation memory
✅ Return execution_id, response, dan metadata
✅ Track token usage
✅ Handle errors gracefully
✅ Timeout after 300 seconds (configurable)
✅ Log all executions untuk replay

Story Points: 13
Priority: P0 (Must Have)

Example Request:
{
  "input": "Send email to john@example.com: Meeting at 3pm",
  "session_id": "session-123",
  "parameters": {}
}

Example Response:
{
  "execution_id": "exec-abc-123",
  "response": "Email sent successfully to john@example.com",
  "session_id": "session-123",
  "tokens_used": 245,
  "tools_used": ["gmail"],
  "status": "completed"
}
```

**US-3.2: Session Memory**
```
As a developer
I want agent to remember previous conversation
So that users can have contextual multi-turn interactions

Acceptance Criteria:
✅ Store all executions dalam executions table
✅ Replay executions dengan same session_id
✅ Maintain conversation context across turns
✅ Support new session creation
✅ Allow session reset
✅ Session isolation (no cross-contamination)

Story Points: 8
Priority: P0 (Must Have)
```

**US-3.3: Execution History**
```
As a developer
I want to view execution history
So that saya bisa debug dan analyze agent behavior

Acceptance Criteria:
✅ List all executions for an agent
✅ Filter by session_id, status, date range
✅ Show input, output, tokens_used, tools_used
✅ Support pagination
✅ Export to JSON/CSV

Story Points: 5
Priority: P1 (Should Have)
```

#### Epic 4: Tool Management

**US-4.1: List Available Tools**
```
As a developer
I want to see all available tools
So that saya bisa decide which tools to use

Acceptance Criteria:
✅ List built-in tools (gmail, sheets, calendar, etc.)
✅ List user's custom tools
✅ Show tool description, parameters, dan examples
✅ Indicate OAuth requirements
✅ Show tool categories

Story Points: 3
Priority: P0 (Must Have)
```

**US-4.2: Create Custom Tool**
```
As a developer
I want to create custom tools
So that saya bisa extend agent capabilities

Acceptance Criteria:
✅ Define tool name, description
✅ Specify JSON Schema untuk parameters
✅ Provide implementation code/endpoint
✅ Validate schema correctness
✅ Test tool execution
✅ Make tool available to user's agents

Story Points: 13
Priority: P1 (Should Have)

Example:
{
  "name": "send_sms",
  "description": "Send SMS via Twilio",
  "parameters": {
    "type": "object",
    "properties": {
      "to": {"type": "string"},
      "message": {"type": "string"}
    },
    "required": ["to", "message"]
  },
  "endpoint": "https://api.example.com/sms"
}
```

**US-4.3: Built-in Tool: Gmail**
```
As a user with Gmail OAuth
I want agent to read, send, and search emails
So that saya bisa automate email workflows

Acceptance Criteria:
✅ gmail.read_latest: Get latest N emails
✅ gmail.search: Search emails by query
✅ gmail.send: Send email dengan to, subject, body
✅ gmail.reply: Reply to email thread
✅ Handle OAuth token refresh
✅ Return formatted email data

Story Points: 8
Priority: P0 (Must Have)
```

**US-4.4: Built-in Tool: Google Sheets**
```
As a user with Sheets OAuth
I want agent to read dan write spreadsheet data
So that saya bisa automate data entry/analysis

Acceptance Criteria:
✅ sheets.read: Read range dari spreadsheet
✅ sheets.write: Write data ke range
✅ sheets.append: Append row to sheet
✅ sheets.create: Create new spreadsheet
✅ Support multiple sheets dalam workbook

Story Points: 8
Priority: P0 (Must Have)
```

**US-4.5: Built-in Tool: Google Calendar**
```
As a user with Calendar OAuth
I want agent to create events dan check availability
So that saya bisa automate scheduling

Acceptance Criteria:
✅ calendar.create_event: Create event dengan title, time, attendees
✅ calendar.list_events: List upcoming events
✅ calendar.find_availability: Check free slots
✅ calendar.update_event: Update existing event
✅ calendar.delete_event: Cancel event

Story Points: 8
Priority: P1 (Should Have)
```

**US-4.6: Built-in Tool: File Operations**
```
As a developer
I want agent to read/write files (CSV, JSON)
So that saya bisa process structured data

Acceptance Criteria:
✅ file.read_csv: Parse CSV file
✅ file.write_csv: Generate CSV file
✅ file.read_json: Parse JSON file
✅ file.write_json: Generate JSON file
✅ Handle file encoding issues

Story Points: 5
Priority: P1 (Should Have)
```

#### Epic 5: RAG (Retrieval Augmented Generation)

**US-5.1: Upload Domain Documents**
```
As a developer
I want to upload documents untuk RAG
So that agent can reference domain-specific knowledge

Acceptance Criteria:
✅ Support PDF, TXT, DOCX, MD formats
✅ Maximum file size: 10MB
✅ Automatic text extraction
✅ Chunk documents into 500-token segments
✅ Store chunks dalam embeddings table
✅ Associate dengan specific agent

Story Points: 13
Priority: P1 (Should Have)
```

**US-5.2: Vector Search**
```
As a system
I want to automatically retrieve relevant document chunks
So that agent has context untuk answering questions

Acceptance Criteria:
✅ Embed user query dengan OpenAI embeddings
✅ Similarity search dengan pgvector
✅ Return top 3 most relevant chunks
✅ Include chunks dalam agent context
✅ Cache embeddings untuk performance

Story Points: 8
Priority: P1 (Should Have)
```

**US-5.3: Document Management**
```
As a developer
I want to manage uploaded documents
So that saya bisa keep knowledge base current

Acceptance Criteria:
✅ List all documents for agent
✅ Delete outdated documents
✅ Re-index documents after updates
✅ Show document metadata (size, chunks, upload date)

Story Points: 5
Priority: P2 (Could Have)
```

#### Epic 6: MCP Integration

**US-6.1: Configure MCP Server**
```
As a developer
I want to connect agent to external MCP server
So that saya bisa use custom tools dari MCP ecosystem

Acceptance Criteria:
✅ Support HTTP and SSE transports
✅ Specify MCP server URL dan auth token
✅ List available tools dari MCP server
✅ Filter allowed tools
✅ Merge MCP tools dengan built-in tools
✅ Handle MCP connection errors

Story Points: 13
Priority: P2 (Could Have)

Example:
{
  "mcp_servers": {
    "custom_mcp": {
      "transport": "streamable_http",
      "url": "http://mcp.example.com/mcp/stream",
      "headers": {"Authorization": "Bearer token123"}
    }
  },
  "allowed_tools": ["calculator", "web_fetch"]
}
```

**US-6.2: Execute MCP Tools**
```
As an agent
I want to call MCP tools during execution
So that saya bisa extend capabilities beyond built-in tools

Acceptance Criteria:
✅ Discover tools dari MCP server
✅ Validate tool parameters
✅ Execute tool calls dengan proper auth
✅ Handle streaming responses
✅ Timeout after 60 seconds
✅ Log MCP tool usage

Story Points: 8
Priority: P2 (Could Have)
```

### 3.2 Secondary User Stories

#### Epic 7: API Key Management

**US-7.1: View API Keys**
```
As a user
I want to see all my API keys
So that saya bisa track usage dan expiration

Acceptance Criteria:
✅ List all API keys with plan, status, expiration
✅ Show last used timestamp
✅ Indicate active/expired status
✅ Sort by creation date

Story Points: 3
Priority: P1 (Should Have)
```

**US-7.2: Revoke API Key**
```
As a user
I want to revoke compromised API key
So that saya bisa maintain security

Acceptance Criteria:
✅ Immediately invalidate API key
✅ Prevent further API calls
✅ Log revocation event
✅ Notify via email (optional)

Story Points: 3
Priority: P1 (Should Have)
```

**US-7.3: Usage Analytics**
```
As a user
I want to see usage statistics per API key
So that saya bisa optimize costs

Acceptance Criteria:
✅ Show total API calls
✅ Show total tokens consumed
✅ Show per-agent breakdown
✅ Export to CSV
✅ Date range filtering

Story Points: 8
Priority: P2 (Could Have)
```

#### Epic 8: System Administration

**US-8.1: Health Check Endpoint**
```
As a DevOps engineer
I want health check endpoint
So that saya bisa monitor system status

Acceptance Criteria:
✅ /health endpoint returns 200 if healthy
✅ Check database connectivity
✅ Check Redis connectivity
✅ Return component status
✅ Include version info

Story Points: 3
Priority: P0 (Must Have)
```

**US-8.2: Logging & Monitoring**
```
As an engineer
I want comprehensive logging
So that saya bisa debug issues

Acceptance Criteria:
✅ Structured JSON logs
✅ Log all API requests/responses
✅ Log agent executions
✅ Log errors dengan stack traces
✅ Log level configuration (INFO, DEBUG, ERROR)

Story Points: 5
Priority: P0 (Must Have)
```

---

## 4. Functional Requirements

### 4.1 Authentication System

#### Feature: User Registration
**Description**: Allow users to create account dengan email dan password

**Endpoint**: `POST /api/v1/auth/register`

**Request**:
```json
{
  "email": "developer@example.com",
  "password": "SecurePass123!"
}
```

**Response**:
```json
{
  "user_id": "uuid-here",
  "email": "developer@example.com",
  "created_at": "2026-02-02T11:24:48Z"
}
```

**Validation Rules**:
- Email must be valid format
- Email must be unique
- Password minimum 8 characters
- Password must contain 1 uppercase, 1 number

**Error Handling**:
- 400: Invalid email format
- 409: Email already exists
- 422: Password too weak

---

#### Feature: API Key Generation
**Description**: Generate plan-based API key untuk authentication

**Endpoint**: `POST /api/v1/auth/api-key`

**Request**:
```json
{
  "username": "developer@example.com",
  "password": "SecurePass123!",
  "plan_code": "PRO_M"
}
```

**Response**:
```json
{
  "access_token": "sk_live_abc123...",
  "token_type": "bearer",
  "plan_code": "PRO_M",
  "expires_at": "2026-03-04T11:24:48Z",
  "created_at": "2026-02-02T11:24:48Z"
}
```

**Business Logic**:
- GUEST: No expiration
- PRO_M: Expires in 30 days
- PRO_Y: Expires in 365 days
- JWT token untuk session management
- Allow multiple API keys per user

---

#### Feature: Google OAuth Flow
**Description**: OAuth 2.0 untuk Google Workspace integration

**Endpoint**: `POST /api/v1/auth/google/auth`

**Request**:
```json
{
  "required_scopes": [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets"
  ]
}
```

**Response**:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random-state-token"
}
```

**Google OAuth Callback**: `GET /api/v1/auth/google/callback`
- Validate state parameter
- Exchange code for tokens
- Encrypt dan store tokens
- Redirect to frontend dengan success

**Token Storage**:
- Access token (encrypted)
- Refresh token (encrypted)
- Scope list
- Expiration timestamp

**Token Refresh**:
- Automatic refresh when expired
- Handle scope changes gracefully
- Log refresh events

---

### 4.2 Agent Management

#### Feature: Create Agent
**Description**: Create new AI agent dengan configuration

**Endpoint**: `POST /api/v1/agents`

**Request**:
```json
{
  "name": "Customer Support Agent",
  "tools": ["gmail", "web_search"],
  "config": {
    "llm_model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1500,
    "system_prompt": "You are a helpful customer support agent. Be empathetic and clear."
  },
  "mcp_servers": {},
  "allowed_tools": []
}
```

**Response**:
```json
{
  "id": "agent-uuid",
  "name": "Customer Support Agent",
  "user_id": "user-uuid",
  "tools": ["gmail", "web_search"],
  "config": {...},
  "tokens_used": 0,
  "created_at": "2026-02-02T11:24:48Z",
  "auth_required": true,
  "auth_url": "https://accounts.google.com/...",
  "auth_state": "state-token"
}
```

**Validation**:
- Name: Required, 3-100 characters
- Tools: Must be valid tool names
- LLM Model: Must be supported model
- Temperature: 0.0 - 2.0
- Max Tokens: 1 - 4000

**Special Logic**:
- If Google tools selected → return OAuth URL
- Store agent configuration dalam JSONB
- Initialize tokens_used = 0

---

#### Feature: Execute Agent
**Description**: Execute agent dengan user input

**Endpoint**: `POST /api/v1/agents/{agent_id}/execute`

**Request**:
```json
{
  "input": "Find emails from last week about project Alpha and summarize",
  "session_id": "conv-123",
  "parameters": {
    "max_results": 10
  }
}
```

**Response**:
```json
{
  "execution_id": "exec-uuid",
  "agent_id": "agent-uuid",
  "session_id": "conv-123",
  "input": "Find emails from...",
  "response": "I found 5 emails about project Alpha from last week. Here's a summary:\n1. ...",
  "tokens_used": 342,
  "tools_used": ["gmail", "web_search"],
  "status": "completed",
  "created_at": "2026-02-02T11:24:48Z",
  "completed_at": "2026-02-02T11:25:12Z"
}
```

**Execution Flow**:
1. Validate agent exists dan user has access
2. Load agent configuration
3. Retrieve session history (all executions dengan same session_id)
4. Build LangChain agent dengan tools
5. Execute agent dengan input
6. Store execution dalam database
7. Update agent.tokens_used
8. Return response

**Error Handling**:
- 404: Agent not found
- 401: Unauthorized (not owner)
- 403: OAuth required but not completed
- 408: Execution timeout (>300s)
- 500: LLM API error

**Session Memory**:
- Load all executions dengan matching session_id
- Replay dalam chronological order
- Include dalam LangChain memory
- Max 20 previous turns (configurable)

---

### 4.3 Tool System

#### Built-in Tool: Gmail

**Methods**:

1. **gmail.read_latest**
```python
{
  "name": "gmail.read_latest",
  "description": "Read latest emails from inbox",
  "parameters": {
    "max_results": 10  # optional, default 10
  },
  "returns": [
    {
      "id": "msg-id",
      "from": "sender@example.com",
      "subject": "Meeting tomorrow",
      "body": "Let's meet at...",
      "date": "2026-02-01T10:00:00Z"
    }
  ]
}
```

2. **gmail.search**
```python
{
  "name": "gmail.search",
  "description": "Search emails by query",
  "parameters": {
    "query": "from:boss@example.com subject:urgent",
    "max_results": 20
  }
}
```

3. **gmail.send**
```python
{
  "name": "gmail.send",
  "description": "Send email",
  "parameters": {
    "to": "recipient@example.com",
    "subject": "Hello",
    "body": "Email content here",
    "cc": [],  # optional
    "bcc": []  # optional
  }
}
```

**OAuth Scopes Required**:
- `https://www.googleapis.com/auth/gmail.readonly` (for read)
- `https://www.googleapis.com/auth/gmail.send` (for send)

---

#### Built-in Tool: Google Sheets

**Methods**:

1. **sheets.read**
```python
{
  "name": "sheets.read",
  "description": "Read data from spreadsheet",
  "parameters": {
    "spreadsheet_id": "1abc...xyz",
    "range": "Sheet1!A1:D10"
  },
  "returns": [
    ["Header1", "Header2", "Header3"],
    ["Row1Col1", "Row1Col2", "Row1Col3"]
  ]
}
```

2. **sheets.write**
```python
{
  "name": "sheets.write",
  "description": "Write data to spreadsheet",
  "parameters": {
    "spreadsheet_id": "1abc...xyz",
    "range": "Sheet1!A1:B2",
    "values": [
      ["Name", "Score"],
      ["Alice", "95"]
    ]
  }
}
```

3. **sheets.append**
```python
{
  "name": "sheets.append",
  "description": "Append row to sheet",
  "parameters": {
    "spreadsheet_id": "1abc...xyz",
    "range": "Sheet1!A:D",
    "values": [["NewRow1", "NewRow2", "NewRow3", "NewRow4"]]
  }
}
```

**OAuth Scopes Required**:
- `https://www.googleapis.com/auth/spreadsheets`

---

#### Built-in Tool: Google Calendar

**Methods**:

1. **calendar.create_event**
```python
{
  "name": "calendar.create_event",
  "description": "Create calendar event",
  "parameters": {
    "summary": "Team Meeting",
    "start": "2026-02-03T14:00:00Z",
    "end": "2026-02-03T15:00:00Z",
    "attendees": ["team@example.com"],
    "description": "Discuss Q1 goals"
  }
}
```

2. **calendar.list_events**
```python
{
  "name": "calendar.list_events",
  "description": "List upcoming events",
  "parameters": {
    "time_min": "2026-02-02T00:00:00Z",
    "time_max": "2026-02-09T23:59:59Z",
    "max_results": 10
  }
}
```

**OAuth Scopes Required**:
- `https://www.googleapis.com/auth/calendar`

---

#### Custom Tool Registration

**Endpoint**: `POST /api/v1/tools`

**Request**:
```json
{
  "name": "weather_forecast",
  "description": "Get weather forecast for a location",
  "category": "external_api",
  "parameters_schema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "City name"
      },
      "days": {
        "type": "integer",
        "description": "Number of days",
        "default": 3
      }
    },
    "required": ["location"]
  },
  "endpoint": "https://api.weather.com/forecast",
  "method": "GET",
  "auth_header": "X-API-Key: ${WEATHER_API_KEY}"
}
```

**Validation**:
- JSON Schema must be valid
- Endpoint must be reachable (optional validation)
- Parameters must match schema

---

### 4.4 RAG System

#### Feature: Document Upload
**Endpoint**: `POST /api/v1/agents/{agent_id}/upload`

**Request**: Multipart form data
```
file: document.pdf
```

**Process**:
1. Validate file type (PDF, TXT, DOCX, MD)
2. Validate file size (<10MB)
3. Extract text content
4. Chunk text (500 tokens per chunk)
5. Generate embeddings dengan OpenAI
6. Store dalam embeddings table dengan pgvector
7. Associate dengan agent_id

**Response**:
```json
{
  "upload_id": "upload-uuid",
  "filename": "product_guide.pdf",
  "total_chunks": 42,
  "status": "completed",
  "created_at": "2026-02-02T11:24:48Z"
}
```

---

#### Feature: Vector Search
**Process** (automatic during execution):
1. User submits query
2. Generate query embedding
3. pgvector similarity search:
```sql
SELECT content, metadata
FROM embeddings
WHERE agent_id = ?
ORDER BY embedding <=> query_embedding
LIMIT 3
```
4. Include chunks dalam agent context
5. Agent references chunks dalam response

**Configuration**:
- Top K chunks: 3 (configurable)
- Similarity threshold: 0.7
- Embedding model: text-embedding-3-small

---

### 4.5 MCP Integration

#### Feature: Configure MCP Server
**Included dalam agent creation**:
```json
{
  "mcp_servers": {
    "langchain_mcp": {
      "transport": "streamable_http",
      "url": "http://mcp.example.com/mcp/stream",
      "headers": {
        "Authorization": "Bearer secret-token"
      }
    }
  },
  "allowed_tools": ["calculator", "web_fetch"]
}
```

**Process**:
1. Validate MCP server connectivity
2. Fetch tools list dari MCP server
3. Filter tools berdasarkan allowed_tools
4. Merge dengan built-in tools
5. Store configuration dalam agent.config

---

## 5. Non-Functional Requirements

### 5.1 Performance Requirements

#### API Response Times
| Endpoint | Target (p95) | Maximum |
|----------|--------------|---------|
| **GET /agents** | 200ms | 500ms |
| **POST /agents** | 300ms | 1s |
| **POST execute** | 5s | 300s (timeout) |
| **GET /tools** | 100ms | 300ms |

#### Database Performance
- Query response time: <100ms (p95)
- Connection pool: 20-100 connections
- Index all foreign keys
- Optimize with EXPLAIN ANALYZE

#### LLM API Performance
- OpenAI API: <3s for completion
- Retry logic: 3 attempts dengan exponential backoff
- Timeout: 60s per request

---

### 5.2 Scalability Requirements

#### Horizontal Scalability
- Support 10,000 concurrent users
- Stateless API servers (scale horizontally)
- Load balancer distribution
- Auto-scaling based on CPU/memory

#### Database Scalability
- PostgreSQL with read replicas
- Connection pooling (PgBouncer)
- Query optimization
- Partitioning untuk large tables (executions)

#### Caching Strategy
- Redis untuk session management
- Cache OAuth tokens (encrypted)
- Cache tool metadata
- TTL: 1 hour default

---

### 5.3 Security Requirements

#### Authentication Security
- JWT tokens with HS256 algorithm
- Token expiration: 24 hours
- Refresh token rotation
- API key hashing dengan bcrypt

#### Data Encryption
- OAuth tokens: AES-256 encryption at rest
- HTTPS/TLS 1.2+ untuk all communications
- Secrets management dengan environment variables
- Database connection encrypted

#### Access Control
- User isolation (row-level security)
- API key scoped to user
- Agent ownership validation
- Rate limiting per API key

#### Input Validation
- Pydantic schema validation
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention
- File upload validation

---

### 5.4 Reliability Requirements

#### Availability
- **Uptime SLA**: 99.9% (43.2 min downtime/month)
- **Failover**: Multi-AZ deployment
- **Backup**: Daily database backups dengan 30-day retention
- **Disaster Recovery**: RPO 1 hour, RTO 4 hours

#### Error Handling
- Graceful degradation
- Retry logic untuk transient errors
- Detailed error messages
- Error tracking (Sentry/DataDog)

#### Monitoring
- Health checks every 30 seconds
- APM monitoring (response times, error rates)
- Log aggregation (ELK stack)
- Alerting untuk critical issues

---

### 5.5 Maintainability Requirements

#### Code Quality
- Test coverage: >80%
- Linting: flake8, mypy
- Code formatting: black, isort
- Documentation: docstrings untuk all functions

#### Database Migrations
- Alembic untuk schema changes
- Migration testing dalam staging
- Rollback capability
- Version control untuk migrations

#### API Versioning
- URL versioning: /api/v1/
- Backward compatibility untuk minor versions
- Deprecation warnings (6 months notice)
- Changelog maintenance

---

### 5.6 Usability Requirements

#### API Documentation
- OpenAPI 3.0 specification
- Interactive Swagger UI
- Code examples dalam Python, JavaScript, cURL
- Error code reference
- Rate limit documentation

#### Developer Experience
- Clear error messages dengan actionable suggestions
- Consistent response format
- Idempotent operations where possible
- Webhook support untuk async operations (future)

---

## 6. Technical Architecture

### 6.1 System Architecture

```
┌─────────────────┐
│   Client Apps   │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│  Load Balancer  │
│    (Nginx)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────┐
│   FastAPI       │◄─────►│    Redis     │
│   Application   │       │   (Cache)    │
└────────┬────────┘       └──────────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   + pgvector    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  External APIs  │
│  - OpenAI       │
│  - Google OAuth │
│  - MCP Servers  │
└─────────────────┘
```

### 6.2 Technology Stack

#### Backend
- **Framework**: FastAPI 0.104+
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0 (async)
- **Migration**: Alembic
- **Validation**: Pydantic V2

#### Database
- **Primary DB**: PostgreSQL 15+
- **Vector Extension**: pgvector 0.5+
- **Cache**: Redis 7+
- **Connection Pool**: PgBouncer

#### AI/ML
- **LLM**: OpenAI GPT-4o-mini, GPT-4
- **Framework**: LangChain 0.1+
- **Embeddings**: text-embedding-3-small

#### Infrastructure
- **Web Server**: Nginx
- **Container**: Docker + Docker Compose
- **Orchestration**: Kubernetes (future)
- **Monitoring**: DataDog/Prometheus

---

### 6.3 Database Schema

#### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### API Keys Table
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    plan_code VARCHAR(50) NOT NULL,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);
```

#### Agents Table
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    tools TEXT[] DEFAULT '{}',
    config JSONB NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Executions Table
```sql
CREATE TABLE executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    input TEXT NOT NULL,
    response TEXT,
    tokens_used INTEGER DEFAULT 0,
    tools_used TEXT[] DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    INDEX idx_session (agent_id, session_id, created_at)
);
```

#### Embeddings Table
```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    upload_id UUID,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- pgvector
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_embedding_similarity 
ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

#### Auth Tokens Table
```sql
CREATE TABLE auth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,  -- 'google'
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT,
    scope TEXT NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

### 6.4 API Endpoints Summary

#### Authentication Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/api-key` | Generate API key |
| POST | `/api/v1/auth/google/auth` | Initiate Google OAuth |
| GET | `/api/v1/auth/google/callback` | OAuth callback |

#### Agent Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/agents` | Create agent |
| GET | `/api/v1/agents` | List user agents |
| GET | `/api/v1/agents/{id}` | Get agent details |
| PUT | `/api/v1/agents/{id}` | Update agent |
| DELETE | `/api/v1/agents/{id}` | Delete agent |
| POST | `/api/v1/agents/{id}/execute` | Execute agent |
| POST | `/api/v1/agents/{id}/upload` | Upload RAG document |

#### Tool Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tools` | List available tools |
| POST | `/api/v1/tools` | Create custom tool |
| GET | `/api/v1/tools/{id}` | Get tool details |
| PUT | `/api/v1/tools/{id}` | Update tool |
| DELETE | `/api/v1/tools/{id}` | Delete tool |

#### System Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc documentation |

---

## 7. Edge Cases & Error Handling

### 7.1 Edge Cases

#### EC-1: OAuth Scope Changes
**Scenario**: Google adds broader scopes automatically

**Handling**:
- Accept superset of requested scopes
- Log scope differences
- Allow token refresh dengan new scopes
- Don't fail authentication

#### EC-2: Session Memory Overflow
**Scenario**: Session has >50 turns, context too large

**Handling**:
- Limit to last 20 turns
- Summarize older turns (future feature)
- Clear session option untuk users

#### EC-3: Multiple Concurrent Executions
**Scenario**: Same agent executed simultaneously

**Handling**:
- Allow concurrent executions (stateless agents)
- Separate session_id untuk each conversation
- Lock-free execution

#### EC-4: LLM API Rate Limit
**Scenario**: OpenAI rate limit exceeded

**Handling**:
- Exponential backoff: 1s, 2s, 4s
- Return 429 status to client
- Queue execution (future feature)

#### EC-5: Malformed Custom Tool Response
**Scenario**: Custom tool endpoint returns invalid data

**Handling**:
- Validate response against schema
- Return error to agent
- Log validation failure
- Agent can retry or skip

---

### 7.2 Error Response Format

**Standard Error Response**:
```json
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "The provided API key is invalid or expired",
    "details": {
      "api_key": "sk_***abc",
      "expires_at": "2026-01-15T10:00:00Z"
    },
    "timestamp": "2026-02-02T11:24:48Z",
    "request_id": "req-uuid-123"
  }
}
```

**Error Codes**:
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_API_KEY` | 401 | API key invalid atau expired |
| `OAUTH_REQUIRED` | 403 | Google OAuth not completed |
| `AGENT_NOT_FOUND` | 404 | Agent ID tidak ditemukan |
| `TOOL_NOT_AVAILABLE` | 400 | Tool tidak tersedia |
| `EXECUTION_TIMEOUT` | 408 | Execution exceeded 300s |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## 8. Testing Strategy

### 8.1 Unit Tests
**Coverage Target**: >80%

**Scope**:
- Services (auth, agent, tool, execution)
- Utils (token generation, encryption)
- Schemas (validation)

**Example**:
```python
def test_create_agent_success():
    # Arrange
    user = create_test_user()
    agent_data = {
        "name": "Test Agent",
        "tools": ["gmail"],
        "config": {...}
    }
    
    # Act
    agent = agent_service.create(user.id, agent_data)
    
    # Assert
    assert agent.name == "Test Agent"
    assert "gmail" in agent.tools
```

---

### 8.2 Integration Tests
**Scope**:
- API endpoints
- Database operations
- External API mocks

**Example**:
```python
def test_execute_agent_with_oauth():
    # Arrange
    user = create_user_with_google_oauth()
    agent = create_agent(user.id, tools=["gmail"])
    
    # Act
    response = client.post(
        f"/api/v1/agents/{agent.id}/execute",
        json={"input": "Read my emails"},
        headers={"Authorization": f"Bearer {user.api_key}"}
    )
    
    # Assert
    assert response.status_code == 200
    assert "execution_id" in response.json()
```

---

### 8.3 Load Testing
**Tool**: Locust

**Scenarios**:
1. **Agent Creation**: 100 users, 1000 agents
2. **Executions**: 500 concurrent executions
3. **API Read**: 1000 req/s on /agents endpoint

**Performance Targets**:
- 95th percentile: <500ms
- 99th percentile: <1s
- Error rate: <0.1%

---

### 8.4 Security Testing
**Scope**:
- SQL injection attempts
- XSS в payloads
- JWT token manipulation
- OAuth flow hijacking

**Tools**:
- OWASP ZAP
- Manual penetration testing
- Dependency scanning (Snyk)

---

## 9. Deployment & Release

### 9.1 Deployment Architecture

**Environments**:
1. **Development**: Local Docker Compose
2. **Staging**: Cloud VM dengan production-like setup
3. **Production**: Multi-region cloud deployment

**CI/CD Pipeline**:
```
Git Push → GitHub Actions → Tests → Build Docker → Deploy to Staging → Manual Approval → Deploy to Production
```

---

### 9.2 Release Checklist

#### Pre-Release
- [ ] All tests passing
- [ ] Code review completed
- [ ] Database migrations tested
- [ ] Staging deployment successful
- [ ] Load testing completed
- [ ] Security scan passed
- [ ] Documentation updated

#### Release
- [ ] Tag release version (v1.x.x)
- [ ] Deploy to production
- [ ] Run smoke tests
- [ ] Monitor error rates
- [ ] Check performance metrics

#### Post-Release
- [ ] Update changelog
- [ ] Notify users (if breaking changes)
- [ ] Monitor for 24 hours
- [ ] Gather user feedback

---

### 9.3 Rollback Plan

#### Triggers
- Error rate >1%
- P95 latency >2s
- Database connection failures
- Critical bug discovered

#### Rollback Steps
1. Stop new traffic to v1.x
2. Route to previous version v1.x-1
3. Verify metrics return to normal
4. Database rollback migration (if needed)
5. Investigate root cause

---

## 10. Future Roadmap

### Phase 2 (Month 7-9)
- [ ] Webhook support untuk async notifications
- [ ] Streaming responses (SSE)
- [ ] Multi-language support (Node.js, Go SDKs)
- [ ] Agent analytics dashboard

### Phase 3 (Month 10-12)
- [ ] Enterprise features (SSO, white-label)
- [ ] Advanced RAG (multi-document, re-ranking)
- [ ] Fine-tuned models integration
- [ ] Team collaboration features

### Phase 4 (Year 2)
- [ ] Agent marketplace
- [ ] Visual agent builder (no-code)
- [ ] Voice agent support
- [ ] Multi-modal agents (vision, audio)

---

## 11. Appendix

### 11.1 Glossary
- **Agent**: AI assistant dengan configured tools
- **Tool**: Function yang dapat dipanggil agent
- **Execution**: Single run dari agent dengan user input
- **Session**: Conversation context dengan unique session_id
- **RAG**: Retrieval Augmented Generation
- **MCP**: Model Context Protocol
- **Pgvector**: PostgreSQL extension untuk vector similarity
- **OAuth**: Open Authentication protocol

### 11.2 References
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [LangChain Documentation](https://python.langchain.com)
- [OpenAI API Reference](https://platform.openai.com/docs)
- [Google OAuth Guide](https://developers.google.com/identity/protocols/oauth2)
- [Pgvector GitHub](https://github.com/pgvector/pgvector)

---

**Document Status**: ✅ Active  
**Last Updated**: 2026-02-02  
**Next Review**: 2026-03-02  
**Owner**: Product & Engineering Team
