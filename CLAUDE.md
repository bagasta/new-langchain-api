# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start development environment with Docker
docker-compose up -d

# Start services manually (if not using Docker)
# 1. Start PostgreSQL and Redis
# 2. Create database
createdb langchain_api

# 3. Run database migrations
alembic upgrade head

# 4. Enable pgvector extension (if not using Docker)
DATABASE_URL="postgresql://postgres:password@localhost:5432/langchain_api" \
  scripts/install_pgvector.sh

# 5. Start the application
uvicorn app.main:app --reload
```

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current revision
alembic current
```

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v

# Run tests with coverage report (HTML + terminal)
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run specific test function
pytest tests/test_agents.py::test_create_agent -v
```

### Code Quality
```bash
# Format code with Black
black app/ tests/

# Sort imports with isort
isort app/ tests/

# Lint code with flake8
flake8 app/ tests/

# Type checking with mypy
mypy app/
```

## Architecture Overview

### Core Architecture
- **FastAPI Application**: Async web framework with automatic OpenAPI documentation
- **SQLAlchemy 2.0**: Async ORM with PostgreSQL and pgvector extension
- **Multi-layer Authentication**: JWT users + API keys with plan-based expiration
- **Agent Management**: LangChain-based AI agents with configurable tools
- **Tool Ecosystem**: Built-in tools plus custom tool registration
- **Asynchronous Execution**: Background agent execution with session-scoped memory

### Key Components

#### Application Structure (`app/`)
- `main.py`: FastAPI app with middleware, exception handlers, and OAuth callback routing
- `api/v1/`: API endpoints (agents, auth, tools)
- `core/`: Configuration, database connection, logging, dependencies
- `models/`: SQLAlchemy ORM models (User, Agent, Tool, AuthToken, etc.)
- `services/`: Business logic (auth, execution, tool management)
- `tools/`: Built-in tool implementations (Gmail, Google Sheets, etc.)
- `integrations/`: Reserved for external integrations
- `schemas/`: Pydantic models for request/response validation

#### Database Models
- **User**: Authentication and user management
- **Agent**: AI agent configuration with tool whitelist and settings
- **Tool**: Tool registry with JSON schema validation
- **AuthToken**: Encrypted OAuth token storage with scope management
- **ApiKey**: Plan-based API keys (PRO_M: 30 days, PRO_Y: 365 days)
- **Execution**: Agent execution history with session memory
- **Embedding**: Vector storage for RAG functionality (requires pgvector)

#### Authentication System
- **Two-step process**: User registration → API key generation
- **JWT tokens**: For user authentication
- **API keys**: Plan-based access with expiration
- **Google OAuth**: Dynamic scope generation based on selected tools
- **Token management**: Encrypted storage with automatic refresh

### Agent Execution
- **Session-scoped memory**: Conversation history persisted per session ID
- **Asynchronous processing**: Background execution with status tracking
- **RAG support**: Document upload and pgvector-based retrieval
- **Tool execution**: Built-in and custom tool integration

## Development Guidelines

### Database Development
- Use Alembic for all schema changes
- Test database changes with `alembic upgrade head` locally first
- The `executions` table stores conversation history and is replayed for context
- Always use UUID primary keys for security
- JSONB columns provide flexibility for agent/tool configurations

### API Development
- Follow FastAPI patterns with dependency injection
- Use Pydantic schemas for all request/response validation
- Implement proper error handling with logging
- All endpoints require authentication (JWT or API key)
- OAuth callbacks are handled dynamically based on configuration

### Testing
- Tests use a separate test database (`langchain_api_test`)
- Agent execution is stubbed in tests to avoid external API calls
- Use pytest fixtures for database setup and teardown
- Coverage reporting includes HTML output in `htmlcov/` directory

### Configuration Management
- All sensitive data must be in environment variables
- Use Pydantic Settings for type-safe configuration
- Database URL must include database name for testing
- OAuth scopes are generated dynamically based on tool selection

### Security Considerations
- Never commit API keys or secrets
- OAuth tokens are encrypted at rest
- Scopes are minimized based on selected tools
- API keys have plan-based expiration
- Input validation on all endpoints

## Production Deployment

### Environment Setup
- Use managed PostgreSQL and Redis services
- Enable pgvector extension in production database
- Configure SSL/TLS certificates
- Set proper CORS origins for production domains
- Use environment-specific configuration files

### Performance Considerations
- Database connection pooling is configured
- Redis caching for session management
- Async processing for agent execution
- Request logging and monitoring enabled
- Health check endpoints available at `/health`

### Docker Deployment
- Multi-stage build with Python 3.11
- Non-root user execution
- Volume mounts for persistent data
- Nginx reverse proxy configuration included
- Health checks configured in containers
