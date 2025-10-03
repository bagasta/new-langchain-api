# LangChain Agent API

A scalable API for creating and managing AI agents with dynamic tool integration, built with FastAPI, LangChain, and PostgreSQL.

## Features

- **Dynamic Agent Creation**: Create custom AI agents with configurable tools
- **Google OAuth Integration**: Secure authentication with scope-based access (agent creation can return an OAuth link when Google Workspace tools are selected)
- **Two-Step Authentication**: Separate user registration from API key generation
- **Plan-Based API Keys**: Generate API keys with expiration periods (PRO_M: 30 days, PRO_Y: 365 days)
- **Built-in Tools**: Gmail, Google Sheets, Google Calendar, CSV/JSON file operations
- **Retrieval-Augmented Generation (RAG)**: Upload domain documents, embed them with pgvector, and have agents reference the most relevant chunks automatically.
- **Custom Tools**: Register and execute custom tools with JSON Schema validation
- **Scalable Architecture**: Microservices-ready with PostgreSQL and Redis
- **LangChain Integration**: Leverage LangChain for advanced AI workflows
- **Real-time Execution**: Asynchronous agent execution with status tracking
- **Persistent Memory**: Conversation history is stored in the `executions` table and reused on future turns

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Google OAuth credentials (for Google Workspace integration)
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Langchain-API-new
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**
   ```bash
   # Create database
   createdb langchain_api

   # Run migrations
   alembic upgrade head
   ```

5. **Start Redis**
   ```bash
   redis-server
   ```

6. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker Setup

For development with Docker:

```bash
docker-compose up -d
```

For production:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Core Concepts

### Agents

Agents are AI assistants that can use tools to accomplish tasks. Each agent has:
- Configuration (LLM model, temperature, system prompt, etc.)
- Associated tools
- Execution history (stored in the `executions` table) that is replayed to maintain conversation memory

### Tools

Tools are functions that agents can use:
- **Built-in**: Gmail, Google Sheets, Google Calendar, CSV/JSON operations
- **Custom**: User-defined tools with JSON Schema validation

### Authentication

The API uses a two-step authentication process:
1. **User Registration**: Create account without API key
2. **API Key Generation**: Request API key with plan-based expiration

**Supported Methods:**
- JWT-based authentication for API access
- Google OAuth for external service integration
- Scope-based access control
- Plan-based API key expiration (PRO_M: 30 days, PRO_Y: 365 days)

#### API Key Plans

- **PRO_M**: 30-day expiration for monthly subscriptions
- **PRO_Y**: 365-day expiration for annual subscriptions

#### API Key Management

- Generate multiple API keys per user account
- Each key has independent expiration dates
- Keys can be deactivated individually
- Plan codes determine expiration periods

## API Endpoints

### Authentication

- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration (returns user info only)
- `POST /api/v1/auth/api-key` - Generate API key with plan-based expiration
- `POST /api/v1/auth/google/auth` - Initiate Google OAuth
- `GET /api/v1/auth/google/callback` - Google OAuth callback

### Agents

- `POST /api/v1/agents` - Create agent
- `GET /api/v1/agents` - List user agents
- `GET /api/v1/agents/{id}` - Get agent details
- `PUT /api/v1/agents/{id}` - Update agent
- `DELETE /api/v1/agents/{id}` - Delete agent
- `POST /api/v1/agents/{id}/execute` - Execute agent

### Tools

- `GET /api/v1/tools` - List available tools
- `POST /api/v1/tools` - Create custom tool
- `GET /api/v1/tools/{id}` - Get tool details
- `PUT /api/v1/tools/{id}` - Update tool
- `DELETE /api/v1/tools/{id}` - Delete tool
- `POST /api/v1/tools/execute` - Execute tool directly

## Example Usage

### Authentication Flow

```python
import requests
import json

# Step 1: Register user
register_response = requests.post(
    "http://localhost:8000/api/v1/auth/register",
    params={"email": "user@example.com", "password": "securepassword"}
)
user_data = register_response.json()
print(f"Registered user: {user_data['user_id']}")

# Step 2: Generate API key with PRO_M plan (30 days)
api_key_response = requests.post(
    "http://localhost:8000/api/v1/auth/api-key",
    json={
        "username": "user@example.com",
        "password": "securepassword",
        "plan_code": "PRO_M"
    }
)
api_data = api_key_response.json()
token = api_data["access_token"]
expires_at = api_data["expires_at"]
print(f"API key expires at: {expires_at}")

# Use token for authenticated requests
headers = {"Authorization": f"Bearer {token}"}
```

### Creating an Agent

```python
import requests

# Create agent
response = requests.post(
    "http://localhost:8000/api/v1/agents",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={
        "name": "Email Assistant",
        "tools": ["gmail"],
        "config": {
            "llm_model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 1000,
            "system_prompt": "You are a friendly research assistant. Remember the user's name and keep context across turns."
        }
    }
)

agent = response.json()
print(f"Created agent: {agent['id']}")
if agent["auth_required"]:
    print(f"Complete Google OAuth: {agent['auth_url']} (state={agent['auth_state']})")
```

### Executing an Agent

```python
# Execute agent
response = requests.post(
    f"http://localhost:8000/api/v1/agents/{agent['id']}/execute",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={
        "input": "Read my latest emails and summarize them",
        "parameters": {},
        "session_id": "demo-session-1"
    }
)

execution = response.json()
print(f"Execution started: {execution['execution_id']}")
print(f"Model response: {execution.get('response')}")
print(f"Session id: {execution.get('session_id')}")

# Session scoping
# Passing a `session_id` partitions conversation memory. Each session replays only
# the executions that share that identifier (records live in the `executions` table).
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | JWT secret key | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Yes |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Yes |
| `GOOGLE_REDIRECT_URI` | Google OAuth redirect URI | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail, Google Calendar, Google Sheets, Google Drive, and Docs APIs
4. Create OAuth 2.0 credentials (Web Application)
5. Add redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
6. Copy Client ID and Client Secret to `.env`

**Note:** The system automatically handles scope changes from Google OAuth. When requesting `drive.file` scope, Google may add broader Drive scopes (`drive`, `drive.photos.readonly`, `drive.appdata`) which are accepted as long as all requested scopes are granted.

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=app
```

### Code Quality

```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Architecture

### System Components

1. **API Gateway**: FastAPI application with routing
2. **Authentication Service**: JWT + OAuth management
3. **Agent Service**: Agent lifecycle management
4. **Tool Service**: Tool registration and execution
5. **Execution Service**: Asynchronous agent execution
6. **Database**: PostgreSQL with pgvector for embeddings
7. **Cache**: Redis for session management

### Security

- JWT-based authentication
- OAuth 2.0 for external services
- Scope-based access control
- Encrypted token storage
- Rate limiting
- Input validation and sanitization

### Performance

- Connection pooling
- Read replicas (configurable)
- Caching with Redis
- Asynchronous processing
- Load balancing support

## Monitoring

The application includes comprehensive logging and monitoring:

- Structured logging with JSON format
- Request/response logging
- Error tracking
- Performance metrics
- Health checks

## Deployment

### Production Considerations

1. **Database**: Use managed PostgreSQL service
2. **Redis**: Use managed Redis service
3. **SSL/TLS**: Enable HTTPS with valid certificates
4. **Environment**: Use production environment variables
5. **Scaling**: Configure horizontal scaling
6. **Monitoring**: Set up monitoring and alerting
7. **Backups**: Implement database backup strategy

### Environment Setup

```bash
# Production environment variables
export SECRET_KEY="your-secure-secret-key"
export DATABASE_URL="postgresql://user:password@prod-db:5432/langchain_api"
export REDIS_URL="redis://prod-redis:6379/0"
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export GOOGLE_REDIRECT_URI="https://your-domain.com/api/v1/auth/google/callback"
export OPENAI_API_KEY="your-openai-api-key"
export LOG_LEVEL="INFO"
```

### PGVector Setup

The embeddings table depends on the [`pgvector`](https://github.com/pgvector/pgvector) extension. If you
are running PostgreSQL outside Docker, enable it with the helper script:

```bash
# requires psql client tools and sudo access for package installation
DATABASE_URL="postgresql://postgres:password@localhost:5432/langchain_api" \
  ./scripts/install_pgvector.sh
```

The script attempts to install the OS package (APT, Yum/DNF, Pacman, or Homebrew) and then runs
`CREATE EXTENSION IF NOT EXISTS vector;` against the target database. If your role lacks privileges,
run the command manually as a PostgreSQL superuser.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Ensure code quality standards
6. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the API examples

## Changelog

### v1.1.0
- **Fixed Google OAuth scope validation issues** - Now handles automatic scope expansion from Google
- **Enhanced token refresh mechanism** - Gracefully handles scope changes during token refresh
- **Improved error handling** - Better error messages for authentication failures

### v1.0.0
- Initial release
- Basic agent management
- Google OAuth integration
- Built-in tools (Gmail, Google Sheets, Google Calendar, file operations)
- Custom tool registration
- LangChain integration
- Docker deployment setup

## Troubleshooting

### Google OAuth Issues

**Q: I'm getting "Scope has changed" errors during Google authentication**
A: This is normal behavior. Google automatically adds broader scopes when certain scopes (like `drive.file`) are requested. The system now handles these changes gracefully.

**Q: My Google OAuth was working but now fails**
A: Google may have updated their scope requirements. Try re-authenticating by:
1. Calling `/api/v1/auth/google/auth` again
2. Following the OAuth flow
3. The system will automatically handle scope differences

**Q: I'm missing required Google scopes**
A: Ensure you've enabled the required APIs in Google Cloud Console:
- Gmail API
- Google Calendar API
- Google Sheets API
- Google Drive API
- Google Docs API
