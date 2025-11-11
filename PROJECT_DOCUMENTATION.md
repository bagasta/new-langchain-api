# LangChain API Project Documentation

## Project Overview

This project is a scalable **LangChain Agent API** built with FastAPI that enables creating and managing AI agents with dynamic tool integration. The API provides a comprehensive platform for building AI-powered agents with support for various tools including Google services, document processing, and custom integrations.

### Key Features
- **Multi-layer Authentication**: JWT sessions plus plan-based API keys with hashed password support and inactive-user safeguards
- **Agent Management**: Create, configure, and manage LangChain-based AI agents with session-aware execution tracking
- **Dynamic Tool Integration**: Built-in tools, custom registrations, and Model Context Protocol (MCP) remote tool federation
- **File & Workspace Tools**: CSV/JSON/file-list helpers alongside Google Workspace integrations
- **RAG Support**: Document upload pipeline with pgvector-backed retrieval
- **OAuth Integration**: Google OAuth with automatic scope reconciliation
- **Asynchronous Execution**: Background agent execution with session-scoped memory and telemetry
- **Vector Database**: PostgreSQL with pgvector for embeddings

## Architecture

### Technology Stack
- **Backend**: FastAPI (async web framework)
- **Database**: PostgreSQL 15 with pgvector extension
- **Cache**: Redis 7
- **ORM**: SQLAlchemy 2.0 (async)
- **Authentication**: JWT + OAuth2 (Google)
- **AI Framework**: LangChain + LangGraph
- **Tool Federation**: Model Context Protocol (MCP) HTTP/SSE transports
- **Containerization**: Docker & Docker Compose
- **Proxy**: Nginx (reverse proxy)

### Project Structure
```
/home/bagas/Langchain-API-new/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   └── v1/
│   │       ├── agents.py       # Agent management endpoints
│   │       ├── auth.py         # Authentication endpoints
│   │       └── tools.py        # Tool management endpoints
│   ├── core/
│   │   ├── config.py           # Application configuration
│   │   ├── database.py         # Database connection and setup
│   │   ├── deps.py             # Dependency injection
│   │   ├── logging.py          # Logging configuration
│   │   └── mcp_config.py       # MCP transport and tool filtering helpers
│   ├── models/
│   │   ├── user.py             # User model
│   │   ├── agent.py            # Agent model
│   │   ├── auth.py             # Authentication models
│   │   ├── tool.py             # Tool models
│   │   ├── execution.py        # Execution model
│   │   └── embedding.py        # Embedding model for RAG
│   ├── services/
│   │   ├── auth_service.py     # Authentication business logic
│   │   ├── execution_service.py # Agent execution logic
│   │   ├── embedding_service.py # Document ingestion and embeddings
│   │   └── tool_service.py     # Tool management logic
│   └── tools/                  # Built-in tool implementations
├── alembic/                    # Database migrations
├── tests/                      # Test suite
├── docker-compose.yml          # Docker configuration
├── requirements.txt            # Python dependencies
└── CLAUDE.md                   # Development guidelines
```

## Database Schema

### Core Tables

#### 1. Users (`users`)
**Purpose**: Stores user authentication and profile information
```sql
Columns:
- id: UUID (Primary Key)
- email: VARCHAR(255) (Unique, Indexed) - stores normalized email or phone
- password_hash: VARCHAR(255) - bcrypt hashed password
- is_active: BOOLEAN - account activation status
- created_at: TIMESTAMPTZ - registration timestamp
```

#### 2. Agents (`agents`)
**Purpose**: Stores AI agent configurations and settings
```sql
Columns:
- id: UUID (Primary Key)
- user_id: UUID (Foreign Key → users.id)
- name: VARCHAR(255) - agent display name
- config: JSONB - agent configuration (LLM settings, prompts, etc.)
- status: ENUM (active, inactive, deleted)
- mcp_servers: JSONB - MCP server configurations
- allowed_tools: TEXT[] - list of permitted tool names
```

#### 3. Authentication (`auth_tokens`, `api_keys`)

**Auth Tokens** - OAuth token storage:
```sql
Columns:
- id: UUID (Primary Key)
- user_id: UUID (Foreign Key → users.id)
- service: VARCHAR(50) - 'google', 'microsoft', etc.
- access_token: TEXT - encrypted OAuth access token
- refresh_token: TEXT - encrypted OAuth refresh token
- scope: TEXT[] - OAuth scopes array
- expires_at: TIMESTAMPTZ - token expiration
```

**API Keys** - Plan-based API access:
```sql
Columns:
- id: UUID (Primary Key)
- user_id: UUID (Foreign Key → users.id)
- access_token: VARCHAR (Unique) - API key string
- plan_code: ENUM ('PRO_M', 'PRO_Y') - subscription plan
- expires_at: TIMESTAMPTZ - key expiration
- is_active: BOOLEAN - key status
- created_at: TIMESTAMPTZ - creation timestamp
```

#### 4. Tools (`tools`, `agent_tools`)

**Tools Registry**:
```sql
Columns:
- id: UUID (Primary Key)
- name: VARCHAR(255) (Unique, Indexed) - tool identifier
- description: TEXT - tool description
- schema: JSONB - JSON schema for tool parameters
- type: ENUM ('builtin', 'custom') - tool category
```

**Agent-Tool Mapping**:
```sql
Columns:
- agent_id: UUID (Composite Primary Key → agents.id)
- tool_id: UUID (Composite Primary Key → tools.id)
- config: JSONB - tool-specific configuration
```

#### 5. Executions (`executions`)
**Purpose**: Tracks agent execution history and conversation memory
```sql
Columns:
- id: UUID (Primary Key)
- agent_id: UUID (Foreign Key → agents.id)
- input: JSONB - user input/request
- output: JSONB - agent response/output
- session_id: VARCHAR(255) (Indexed) - conversation session
- status: ENUM (pending, running, completed, failed, cancelled)
- duration_ms: INTEGER - execution time in milliseconds
- error_message: TEXT - error details if failed
```

#### 6. Embeddings (`embeddings`)
**Purpose**: RAG functionality with vector storage
```sql
Columns:
- id: UUID (Primary Key)
- agent_id: UUID (Foreign Key → agents.id)
- content: TEXT - original text content
- embedding: VECTOR(1536) - OpenAI embedding vector
- metadata: JSONB - additional metadata
```

### Database Relationships
```
Users (1) ←→ (N) Agents
Users (1) ←→ (N) AuthTokens
Users (1) ←→ (N) ApiKeys
Agents (1) ←→ (N) Executions
Agents (1) ←→ (N) Embeddings
Agents (N) ←→ (N) Tools (through AgentTools)
```

## API Endpoints

### Authentication Endpoints (`/api/v1/auth`)

#### User Registration & Login
- `POST /register` - Supply `email`, `phone`, or `identifier` via query parameters along with `password` to create a user. Accounts are created in an inactive state so they can be reviewed before API access is granted.
- `POST /login` - Authenticate with query parameters (`email`, `phone`, or `identifier`) and `password`. The password parameter accepts either plaintext or the stored bcrypt hash (prefix `$2b$12$` or legacy `$bcrypt-sha256$`) so automation can authenticate without exposing raw passwords.
- `GET /me` - Return the current user profile; the response echoes the bearer token supplied in the request and, when it's an API key, includes the associated `plan_code` so clients can confirm which credential and subscription are active.

Example response:
```json
{
  "id": "0a1b2c3d-....",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2024-06-03T11:22:33.123456",
  "access_token": "eyJ..."
}
```

#### Google OAuth Integration
- `POST /google/auth` - Initiate Google OAuth flow and return `auth_url` + `state` (no request body required)
- `GET /google/auth` - Alternate method for initiating the OAuth flow (handy for browser redirects)
- `GET /google/callback` - Handle the OAuth callback; reconciles Google scope changes automatically

#### API Key Management
- `POST /api-key` - Generate a new plan-based API key; request body includes `username`, `password`, and `plan_code` (`PRO_M` 30 days, `PRO_Y` 365 days, `TRIAL` 14 days)
- `POST /api-key/update` - Extend or reactivate an existing key by providing `username`, `password`, `plan_code`, and the current `access_token`
- `POST /user/update-password` - Rotate a user's password using plaintext or a supported bcrypt hash

### Agent Management (`/api/v1/agents`)

#### CRUD Operations
- `GET /` - List user's agents
- `POST /` - Create new agent
- `GET /{agent_id}` - Get agent details
- `PUT /{agent_id}` - Update agent configuration
- `DELETE /{agent_id}` - Delete agent

#### Agent Execution
- `POST /{agent_id}/execute` - Execute agent with input; optional `parameters` dictionary and `session_id` allow fine-grained control over runs
- `GET /{agent_id}/executions` - List execution history for the agent
- `GET /{agent_id}/executions/{execution_id}` - Get execution details
- `GET /executions/stats` - Aggregate execution statistics for the authenticated user
- `POST /{agent_id}/documents` - Upload documents for retrieval-augmented generation (RAG) with chunking controls (`chunk_size`, `chunk_overlap`, `batch_size`)

### Tool Management (`/api/v1/tools`)

#### Tool Registry
- `GET /` - List available tools (optional `tool_type` filter accepts `builtin` or `custom`)
- `GET /{tool_id}` - Get tool details and schema
- `POST /` - Register custom tool
- `PUT /{tool_id}` - Update tool configuration
- `DELETE /{tool_id}` - Remove tool
- `POST /execute` - Execute a tool directly by ID with JSON parameters
- `GET /schemas/{tool_name}` - Retrieve the JSON schema for a known tool by name
- `GET /scopes/required?tools=...` - Determine the OAuth scopes required for Google Workspace tools

## Setup Requirements

### Prerequisites
- **Python 3.11+** - Application runtime
- **PostgreSQL 15+** - Database with pgvector extension
- **Redis 7+** - Caching and session storage
- **Docker & Docker Compose** - Containerization (recommended)

### Environment Variables

#### Core Configuration
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/langchain_api
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200  # 30 days

# Application
PROJECT_NAME=LangChain Agent API
API_V1_STR=/api/v1
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
```

#### OAuth Configuration
```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Allowed OAuth Scopes (comma-separated)
GOOGLE_SCOPES=https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/spreadsheets
```

#### AI Services
```bash
# OpenAI
OPENAI_API_KEY=your-openai-api-key
# Agent-level configs default to gpt-4o-mini; override per agent via config.llm_model

# Optional: Other AI providers
ANTHROPIC_API_KEY=your-anthropic-key
```

#### CORS Configuration
```bash
# Comma-separated list of allowed origins
BACKEND_CORS_ORIGINS=["http://localhost:3000","https://yourdomain.com"]

# MCP (Model Context Protocol) remote tool federation
MCP_HTTP_URL=http://localhost:8080/mcp/stream
MCP_HTTP_TOKEN=your-mcp-token
MCP_HTTP_ALLOWED_TOOLS=calculator,web_search,pdf_generate

MCP_SSE_URL=http://localhost:8080
MCP_SSE_TOKEN=your-mcp-token
MCP_SSE_ALLOWED_TOOLS=calculator,web_search
MCP_SSE_ALLOWED_TOOL_CATEGORIES=math,files
```

Values for `BACKEND_CORS_ORIGINS`, `MCP_HTTP_ALLOWED_TOOLS`, and related lists can be provided as comma-separated strings or JSON arrays. The configuration layer normalizes either format into Python lists.

### Installation Steps

#### 1. Clone and Setup
```bash
git clone <repository-url>
cd Langchain-API-new
```

#### 2. Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

#### 3. Database Setup
```bash
# Create database
createdb langchain_api

# Enable pgvector extension
DATABASE_URL="postgresql://user:password@localhost:5432/langchain_api" \
  scripts/install_pgvector.sh

# Run migrations
alembic upgrade head
```

#### 4. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

#### 5. Start Application
```bash
# Development mode
uvicorn app.main:app --reload

# Or with Docker Compose (recommended)
docker-compose up -d
```

### API Usage Workflow

#### 1. User Registration
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register?email=user@example.com&password=securepassword"
```

#### 2. Login and Get JWT Token
```bash
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login?email=user@example.com&password=securepassword")
TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.jwt_token')
echo "Session JWT: $TOKEN"
```
`jq` is used here to extract JSON fields; substitute your preferred JSON parser if needed.

#### 3. Generate API Key
```bash
curl -X POST "http://localhost:8000/api/v1/auth/api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "securepassword",
    "plan_code": "PRO_M"
  }'
```
The request body accepts the user's plaintext password or the stored bcrypt hash. Successful responses return an `access_token` you can use as the bearer credential for agent and tool routes.

#### 4. Create Agent
```bash
curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer <api-key-access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Email Assistant",
    "config": {
      "llm_model": "gpt-4o-mini",
      "system_prompt": "You are a helpful email assistant.",
      "temperature": 0.7
    },
    "allowed_tools": ["gmail", "calendar"],
    "mcp_servers": {}
  }'
```

#### 5. Execute Agent
```bash
curl -X POST "http://localhost:8000/api/v1/agents/{agent_id}/execute" \
  -H "Authorization: Bearer <api-key-access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Check my recent emails",
    "session_id": "user_session_123"
  }'
```

## Built-in Tools

### Google Services
- **Gmail**: Read, send, and manage emails
- **Google Sheets**: Read and write spreadsheet data
- **Google Calendar**: Manage calendar events
- **Google Drive**: Access and manage files

### Document Processing
- **PDF Reader**: Extract text from PDF files
- **Word Processor**: Handle .docx files
- **Excel Reader**: Process .xlsx files
- **PowerPoint Reader**: Extract from .pptx files

### File Utilities
- **CSV Tool**: Read and write CSV data with configurable delimiter and encoding
- **JSON Tool**: Read and write JSON files with customizable indentation
- **File List Tool**: List files within a directory (supports glob patterns and recursive walks)

### Custom Tools
- **Web Search**: Internet search capabilities
- **Calculator**: Mathematical computations
- **Text Processing**: String manipulation and analysis
- **MCP Remote Tools**: Any tools exposed by an MCP server configured through `MCP_HTTP_*` or `MCP_SSE_*` environment variables are merged into the agent's runtime toolset.

## Development Guidelines

### Code Quality
```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_agents.py::test_create_agent -v
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Production Deployment

### Docker Configuration
The project includes Docker Compose setup with:
- **Application Container**: FastAPI app with Python 3.11
- **PostgreSQL**: Database with pgvector extension
- **Redis**: Caching and session storage
- **Nginx**: Reverse proxy with SSL support

### Security Considerations
- Use HTTPS in production
- Rotate SECRET_KEY regularly
- Implement rate limiting
- Monitor API usage and logs
- Keep dependencies updated
- Use environment-specific configurations

### Monitoring
- Health check endpoint: `/health`
- Request logging enabled
- Error tracking with structured logging
- Performance metrics available

## API Rate Limits

### Plan-based Limits
- **PRO_M (Monthly)**: 30-day expiration
- **PRO_Y (Yearly)**: 365-day expiration

### Usage Tracking
- Execution history stored in database
- Session-based memory management
- Resource usage monitoring

## Troubleshooting

### Common Issues
1. **Database Connection**: Ensure PostgreSQL is running and pgvector is enabled
2. **OAuth Callbacks**: Verify redirect URIs match configuration
3. **CORS Errors**: Check allowed origins in environment variables
4. **Tool Permissions**: Ensure tools are whitelisted for agents

### Debug Commands
```bash
# Check database connection
docker-compose exec db psql -U postgres -d langchain_api

# View logs
docker-compose logs app

# Test API
curl http://localhost:8000/health
```

## SQL Query Reference

### API Key Management Queries

#### 1. Get All API Keys (Admin View)
```sql
SELECT
    ak.id,
    ak.access_token,
    ak.plan_code,
    ak.expires_at,
    ak.is_active,
    ak.created_at,
    u.email as user_email,
    u.created_at as user_created_at,
    CASE
        WHEN ak.expires_at < NOW() THEN 'EXPIRED'
        WHEN ak.expires_at < NOW() + INTERVAL '7 days' THEN 'EXPIRING_SOON'
        ELSE 'ACTIVE'
    END as status,
    EXTRACT(DAYS FROM ak.expires_at - NOW()) as days_until_expiry
FROM api_keys ak
JOIN users u ON ak.user_id = u.id
ORDER BY ak.created_at DESC;
```

#### 2. Get API Keys by User Email
```sql
SELECT
    ak.id,
    ak.access_token,
    ak.plan_code,
    ak.expires_at,
    ak.is_active,
    ak.created_at,
    CASE
        WHEN ak.expires_at < NOW() THEN 'EXPIRED'
        WHEN ak.expires_at < NOW() + INTERVAL '7 days' THEN 'EXPIRING_SOON'
        ELSE 'ACTIVE'
    END as status,
    EXTRACT(DAYS FROM ak.expires_at - NOW()) as days_until_expiry
FROM api_keys ak
JOIN users u ON ak.user_id = u.id
WHERE u.email = 'user@example.com'
ORDER BY ak.created_at DESC;
```

#### 3. Get Active API Keys Only
```sql
SELECT
    ak.id,
    ak.access_token,
    ak.plan_code,
    ak.expires_at,
    ak.created_at,
    u.email as user_email,
    EXTRACT(DAYS FROM ak.expires_at - NOW()) as days_until_expiry
FROM api_keys ak
JOIN users u ON ak.user_id = u.id
WHERE ak.is_active = true
    AND ak.expires_at > NOW()
ORDER BY ak.expires_at ASC;
```

#### 4. Get API Keys by Plan Type
```sql
-- Get PRO_M (Monthly) API Keys
SELECT
    ak.id,
    ak.access_token,
    ak.plan_code,
    ak.expires_at,
    ak.is_active,
    ak.created_at,
    u.email as user_email,
    EXTRACT(DAYS FROM ak.expires_at - NOW()) as days_until_expiry
FROM api_keys ak
JOIN users u ON ak.user_id = u.id
WHERE ak.plan_code = 'PRO_M'
ORDER BY ak.created_at DESC;

-- Get PRO_Y (Yearly) API Keys
SELECT
    ak.id,
    ak.access_token,
    ak.plan_code,
    ak.expires_at,
    ak.is_active,
    ak.created_at,
    u.email as user_email,
    EXTRACT(DAYS FROM ak.expires_at - NOW()) as days_until_expiry
FROM api_keys ak
JOIN users u ON ak.user_id = u.id
WHERE ak.plan_code = 'PRO_Y'
ORDER BY ak.created_at DESC;
```

#### 5. Get Expiring API Keys (Next 30 Days)
```sql
SELECT
    ak.id,
    ak.access_token,
    ak.plan_code,
    ak.expires_at,
    ak.created_at,
    u.email as user_email,
    EXTRACT(DAYS FROM ak.expires_at - NOW()) as days_until_expiry
FROM api_keys ak
JOIN users u ON ak.user_id = u.id
WHERE ak.expires_at BETWEEN NOW() AND NOW() + INTERVAL '30 days'
    AND ak.is_active = true
ORDER BY ak.expires_at ASC;
```

#### 6. Get API Key Usage Statistics
```sql
SELECT
    COUNT(*) as total_keys,
    COUNT(CASE WHEN ak.is_active = true AND ak.expires_at > NOW() THEN 1 END) as active_keys,
    COUNT(CASE WHEN ak.expires_at < NOW() THEN 1 END) as expired_keys,
    COUNT(CASE WHEN ak.plan_code = 'PRO_M' THEN 1 END) as pro_monthly_keys,
    COUNT(CASE WHEN ak.plan_code = 'PRO_Y' THEN 1 END) as pro_yearly_keys,
    COUNT(CASE WHEN ak.expires_at BETWEEN NOW() AND NOW() + INTERVAL '7 days' THEN 1 END) as expiring_next_week,
    COUNT(CASE WHEN ak.expires_at BETWEEN NOW() AND NOW() + INTERVAL '30 days' THEN 1 END) as expiring_next_month
FROM api_keys ak;
```

#### 7. Search API Keys by Partial Token
```sql
SELECT
    ak.id,
    ak.access_token,
    ak.plan_code,
    ak.expires_at,
    ak.is_active,
    ak.created_at,
    u.email as user_email
FROM api_keys ak
JOIN users u ON ak.user_id = u.id
WHERE ak.access_token ILIKE '%partial-token-here%'
ORDER BY ak.created_at DESC;
```

#### 8. Clean Up Expired API Keys (Update to Inactive)
```sql
UPDATE api_keys
SET is_active = false
WHERE expires_at < NOW() AND is_active = true;
```

#### 9. Count API Keys by Status
```sql
SELECT
    CASE
        WHEN expires_at < NOW() THEN 'EXPIRED'
        WHEN is_active = false THEN 'INACTIVE'
        WHEN expires_at < NOW() + INTERVAL '7 days' THEN 'EXPIRING_SOON'
        ELSE 'ACTIVE'
    END as status,
    COUNT(*) as count
FROM api_keys
GROUP BY
    CASE
        WHEN expires_at < NOW() THEN 'EXPIRED'
        WHEN is_active = false THEN 'INACTIVE'
        WHEN expires_at < NOW() + INTERVAL '7 days' THEN 'EXPIRING_SOON'
        ELSE 'ACTIVE'
    END
ORDER BY count DESC;
```

### Agent Management Queries

#### 1. Get All Agents with User Info
```sql
SELECT
    a.id,
    a.name,
    a.status,
    a.created_at,
    u.email as user_email,
    COUNT(e.id) as execution_count
FROM agents a
JOIN users u ON a.user_id = u.id
LEFT JOIN executions e ON a.id = e.agent_id
WHERE a.status != 'deleted'
GROUP BY a.id, a.name, a.status, a.created_at, u.email
ORDER BY a.created_at DESC;
```

#### 2. Get Agent Execution History
```sql
SELECT
    e.id,
    e.session_id,
    e.status,
    e.duration_ms,
    e.created_at,
    a.name as agent_name,
    u.email as user_email
FROM executions e
JOIN agents a ON e.agent_id = a.id
JOIN users u ON a.user_id = u.id
WHERE e.agent_id = 'agent-uuid-here'
ORDER BY e.created_at DESC;
```

### User Management Queries

#### 1. Get All Users Information
```sql
SELECT
    u.id,
    u.email,
    u.is_active,
    u.created_at,
    COUNT(DISTINCT a.id) as total_agents,
    COUNT(DISTINCT CASE WHEN a.status = 'active' THEN a.id END) as active_agents,
    COUNT(DISTINCT ak.id) as total_api_keys,
    COUNT(DISTINCT CASE WHEN ak.is_active = true AND ak.expires_at > NOW() THEN ak.id END) as active_api_keys,
    COUNT(DISTINCT e.id) as total_executions,
    MAX(e.created_at) as last_execution_date,
    CASE
        WHEN u.is_active = false THEN 'INACTIVE'
        WHEN COUNT(DISTINCT CASE WHEN ak.is_active = true AND ak.expires_at > NOW() THEN ak.id END) = 0 THEN 'NO_ACTIVE_KEYS'
        ELSE 'ACTIVE'
    END as account_status
FROM users u
LEFT JOIN agents a ON u.id = a.user_id
LEFT JOIN api_keys ak ON u.id = ak.user_id
LEFT JOIN executions e ON a.id = e.agent_id
GROUP BY u.id, u.email, u.is_active, u.created_at
ORDER BY u.created_at DESC;
```

#### 2. Get User by Email
```sql
SELECT
    u.id,
    u.email,
    u.is_active,
    u.created_at,
    COUNT(DISTINCT a.id) as total_agents,
    COUNT(DISTINCT CASE WHEN a.status = 'active' THEN a.id END) as active_agents,
    COUNT(DISTINCT ak.id) as total_api_keys,
    COUNT(DISTINCT CASE WHEN ak.is_active = true AND ak.expires_at > NOW() THEN ak.id END) as active_api_keys,
    COUNT(DISTINCT e.id) as total_executions,
    MAX(e.created_at) as last_execution_date,
    EXTRACT(DAYS FROM NOW() - u.created_at) as days_since_registration
FROM users u
LEFT JOIN agents a ON u.id = a.user_id
LEFT JOIN api_keys ak ON u.id = ak.user_id
LEFT JOIN executions e ON a.id = e.agent_id
WHERE u.email = 'user@example.com'
GROUP BY u.id, u.email, u.is_active, u.created_at;
```

#### 3. Get Active Users Only
```sql
SELECT
    u.id,
    u.email,
    u.created_at,
    EXTRACT(DAYS FROM NOW() - u.created_at) as days_since_registration,
    COUNT(DISTINCT a.id) as agent_count,
    COUNT(DISTINCT ak.id) as api_key_count,
    COUNT(DISTINCT CASE WHEN ak.is_active = true AND ak.expires_at > NOW() THEN ak.id END) as active_api_keys,
    MAX(e.created_at) as last_activity
FROM users u
LEFT JOIN agents a ON u.id = a.user_id AND a.status != 'deleted'
LEFT JOIN api_keys ak ON u.id = ak.user_id
LEFT JOIN executions e ON a.id = e.agent_id
WHERE u.is_active = true
GROUP BY u.id, u.email, u.created_at
ORDER BY u.created_at DESC;
```

#### 4. Get User Statistics
```sql
SELECT
    COUNT(*) as total_users,
    COUNT(CASE WHEN u.is_active = true THEN 1 END) as active_users,
    COUNT(CASE WHEN u.is_active = false THEN 1 END) as inactive_users,
    COUNT(CASE WHEN u.created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as new_users_this_week,
    COUNT(CASE WHEN u.created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as new_users_this_month,
    COUNT(CASE WHEN u.created_at >= NOW() - INTERVAL '90 days' THEN 1 END) as new_users_this_quarter,
    AVG(EXTRACT(DAYS FROM NOW() - u.created_at)) as avg_user_age_days
FROM users u;
```

#### 5. Get Users with Agent and API Key Count
```sql
SELECT
    u.id,
    u.email,
    u.is_active,
    u.created_at,
    COUNT(DISTINCT a.id) as agent_count,
    COUNT(DISTINCT CASE WHEN a.status = 'active' THEN a.id END) as active_agent_count,
    COUNT(DISTINCT ak.id) as api_key_count,
    COUNT(DISTINCT CASE WHEN ak.is_active = true AND ak.expires_at > NOW() THEN ak.id END) as active_api_key_count,
    COUNT(DISTINCT CASE WHEN ak.plan_code = 'PRO_M' THEN ak.id END) as pro_monthly_keys,
    COUNT(DISTINCT CASE WHEN ak.plan_code = 'PRO_Y' THEN ak.id END) as pro_yearly_keys
FROM users u
LEFT JOIN agents a ON u.id = a.user_id AND a.status != 'deleted'
LEFT JOIN api_keys ak ON u.id = ak.user_id
GROUP BY u.id, u.email, u.is_active, u.created_at
ORDER BY u.created_at DESC;
```

#### 6. Get User by UUID
```sql
SELECT
    u.id,
    u.email,
    u.is_active,
    u.created_at,
    EXTRACT(DAYS FROM NOW() - u.created_at) as days_since_registration,
    -- Agent Information
    (SELECT COUNT(*) FROM agents WHERE user_id = u.id AND status != 'deleted') as total_agents,
    (SELECT COUNT(*) FROM agents WHERE user_id = u.id AND status = 'active') as active_agents,
    -- API Key Information
    (SELECT COUNT(*) FROM api_keys WHERE user_id = u.id) as total_api_keys,
    (SELECT COUNT(*) FROM api_keys WHERE user_id = u.id AND is_active = true AND expires_at > NOW()) as active_api_keys,
    -- Execution Information
    (SELECT COUNT(*) FROM executions e JOIN agents a ON e.agent_id = a.id WHERE a.user_id = u.id) as total_executions,
    (SELECT MAX(e.created_at) FROM executions e JOIN agents a ON e.agent_id = a.id WHERE a.user_id = u.id) as last_execution
FROM users u
WHERE u.id = 'user-uuid-here';
```

#### 7. Get Recently Active Users (Last 30 Days)
```sql
SELECT DISTINCT
    u.id,
    u.email,
    u.created_at,
    MAX(e.created_at) as last_execution_date,
    COUNT(e.id) as executions_last_30_days
FROM users u
JOIN agents a ON u.id = a.user_id
JOIN executions e ON a.id = e.agent_id
WHERE e.created_at >= NOW() - INTERVAL '30 days'
    AND u.is_active = true
GROUP BY u.id, u.email, u.created_at
ORDER BY last_execution_date DESC;
```

#### 8. Get Users Without Active API Keys
```sql
SELECT
    u.id,
    u.email,
    u.is_active,
    u.created_at,
    EXTRACT(DAYS FROM NOW() - u.created_at) as days_since_registration,
    COUNT(DISTINCT a.id) as agent_count
FROM users u
LEFT JOIN agents a ON u.id = a.user_id AND a.status != 'deleted'
LEFT JOIN api_keys ak ON u.id = ak.user_id AND ak.is_active = true AND ak.expires_at > NOW()
WHERE ak.id IS NULL
GROUP BY u.id, u.email, u.is_active, u.created_at
ORDER BY u.created_at DESC;
```

#### 9. Get User Registration Trends
```sql
SELECT
    DATE_TRUNC('day', u.created_at) as registration_date,
    COUNT(*) as users_registered,
    COUNT(CASE WHEN u.is_active = true THEN 1 END) as active_users,
    COUNT(CASE WHEN u.is_active = false THEN 1 END) as inactive_users
FROM users u
WHERE u.created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', u.created_at)
ORDER BY registration_date DESC;
```

#### 10. Get Users with Execution Analytics
```sql
SELECT
    u.id,
    u.email,
    u.is_active,
    u.created_at,
    COUNT(DISTINCT a.id) as agent_count,
    COUNT(DISTINCT e.id) as total_executions,
    COUNT(DISTINCT CASE WHEN e.status = 'completed' THEN e.id END) as completed_executions,
    COUNT(DISTINCT CASE WHEN e.status = 'failed' THEN e.id END) as failed_executions,
    AVG(e.duration_ms) as avg_execution_duration_ms,
    MAX(e.created_at) as last_execution_date,
    CASE
        WHEN COUNT(DISTINCT e.id) = 0 THEN 'NO_EXECUTIONS'
        WHEN COUNT(DISTINCT CASE WHEN e.status = 'completed' THEN e.id END) = 0 THEN 'ALL_FAILED'
        WHEN COUNT(DISTINCT CASE WHEN e.status = 'failed' THEN e.id END) = 0 THEN 'ALL_SUCCESS'
        ELSE 'MIXED_RESULTS'
    END as execution_profile
FROM users u
LEFT JOIN agents a ON u.id = a.user_id AND a.status != 'deleted'
LEFT JOIN executions e ON a.id = e.agent_id
GROUP BY u.id, u.email, u.is_active, u.created_at
HAVING COUNT(DISTINCT e.id) > 0
ORDER BY total_executions DESC;
```

#### 11. Search Users by Email Partial
```sql
SELECT
    u.id,
    u.email,
    u.is_active,
    u.created_at,
    COUNT(DISTINCT a.id) as agent_count,
    COUNT(DISTINCT ak.id) as api_key_count
FROM users u
LEFT JOIN agents a ON u.id = a.user_id AND a.status != 'deleted'
LEFT JOIN api_keys ak ON u.id = ak.user_id
WHERE u.email ILIKE '%partial-email-here%'
GROUP BY u.id, u.email, u.is_active, u.created_at
ORDER BY u.created_at DESC;
```

#### 12. Get Inactive Users (No Activity in 30 Days)
```sql
SELECT
    u.id,
    u.email,
    u.is_active,
    u.created_at,
    MAX(e.created_at) as last_execution_date,
    EXTRACT(DAYS FROM NOW() - MAX(e.created_at)) as days_since_last_execution,
    COUNT(DISTINCT a.id) as agent_count
FROM users u
LEFT JOIN agents a ON u.id = a.user_id AND a.status != 'deleted'
LEFT JOIN executions e ON a.id = e.agent_id
WHERE u.is_active = true
GROUP BY u.id, u.email, u.is_active, u.created_at
HAVING MAX(e.created_at) < NOW() - INTERVAL '30 days' OR MAX(e.created_at) IS NULL
ORDER BY days_since_last_execution DESC NULLS FIRST;
```

### Execution Analytics Queries

#### 1. Get Execution Statistics
```sql
SELECT
    COUNT(*) as total_executions,
    COUNT(CASE WHEN e.status = 'completed' THEN 1 END) as completed_executions,
    COUNT(CASE WHEN e.status = 'failed' THEN 1 END) as failed_executions,
    COUNT(CASE WHEN e.status = 'running' THEN 1 END) as running_executions,
    AVG(e.duration_ms) as avg_duration_ms,
    MAX(e.created_at) as last_execution
FROM executions e
WHERE e.created_at >= NOW() - INTERVAL '24 hours';
```

#### 2. Get Popular Agents by Execution Count
```sql
SELECT
    a.id,
    a.name,
    u.email as user_email,
    COUNT(e.id) as execution_count,
    AVG(e.duration_ms) as avg_duration_ms,
    MAX(e.created_at) as last_execution
FROM agents a
JOIN users u ON a.user_id = u.id
JOIN executions e ON a.id = e.agent_id
WHERE a.status = 'active'
GROUP BY a.id, a.name, u.email
ORDER BY execution_count DESC
LIMIT 10;
```

This documentation provides a comprehensive overview of the LangChain API project, making it suitable for integration with WhatsApp API development and understanding the complete system architecture.
