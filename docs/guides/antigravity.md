# Antigravity Learning Report: LangChain Agent API

## 1. Project Overview
The **LangChain Agent API** is a robust and scalable backend system designed to facilitate the creation, management, and execution of AI agents. It leverages the power of **LangChain** and **LangGraph** to orchestrate complex agent behaviors and integrates seamlessly with various tools and services.

## 2. Technology Stack
The project is built using a modern and efficient technology stack:

- **Language:** Python 3.11+
- **Web Framework:** FastAPI (Async)
- **Database:** PostgreSQL 15+ (with `pgvector` extension for RAG)
- **Caching & Session Store:** Redis 7+
- **ORM:** SQLAlchemy 2.0 (Async)
- **AI Framework:** LangChain, LangGraph
- **Tool Protocol:** Model Context Protocol (MCP)
- **Containerization:** Docker, Docker Compose
- **Authentication:** JWT (JSON Web Tokens), OAuth2 (Google)

## 3. Key Features & Architecture

### 3.1. Agent Management
- **Dynamic Configuration:** Agents can be created and configured with specific LLM models, system prompts, and tools.
- **Lifecycle Management:** Full CRUD operations for agents.
- **Execution History:** Detailed tracking of agent executions, including inputs, outputs, and duration.

### 3.2. Tool Ecosystem
- **Built-in Tools:** Includes integrations for Google Workspace (Gmail, Calendar, Sheets, Drive), document processing (PDF, DOCX, etc.), and file utilities.
- **Custom Tools:** Support for registering custom tools with JSON schemas.
- **MCP Integration:** Implements the Model Context Protocol to federate tools from remote servers (HTTP/SSE).

### 3.3. Authentication & Security
- **Multi-layer Auth:** Supports JWT for user sessions and plan-based API keys for programmatic access.
- **OAuth Integration:** Seamless integration with Google OAuth for accessing user-specific data (e.g., Gmail, Calendar) with automatic scope reconciliation.
- **Security Best Practices:** Password hashing (bcrypt), encrypted tokens, and role-based access control.

### 3.4. RAG (Retrieval-Augmented Generation)
- **Vector Storage:** Uses `pgvector` within PostgreSQL to store and query embeddings.
- **Document Ingestion:** Pipeline for uploading and chunking documents for efficient retrieval.

## 4. Project Structure
The project follows a clean and modular structure:

- **`app/`**: Contains the core application logic.
    - **`main.py`**: Entry point.
    - **`api/`**: API route definitions (v1).
    - **`core/`**: Configuration, database setup, and logging.
    - **`models/`**: SQLAlchemy database models.
    - **`services/`**: Business logic for auth, execution, tools, etc.
    - **`tools/`**: Implementations of built-in tools.
- **`alembic/`**: Database migration scripts.
- **`tests/`**: Comprehensive test suite using `pytest`.
- **`docker-compose.yml`**: Orchestration for the app, database, and Redis.

## 5. Database Schema
The database is well-structured to support the application's needs:
- **`users`**: User profiles and authentication data.
- **`agents`**: Agent configurations.
- **`tools`** & **`agent_tools`**: Tool registry and assignments.
- **`executions`**: History of agent runs.
- **`embeddings`**: Vector data for RAG.
- **`auth_tokens`** & **`api_keys`**: Token management.

## 6. Conclusion
This project represents a sophisticated platform for building AI agents. Its use of async Python, vector databases, and the Model Context Protocol positions it as a forward-looking solution for scalable AI application development. The documentation is thorough, and the codebase appears to be well-organized and maintainable.

## 7. API Endpoints

The API is versioned (v1) and organized into logical resources.

### 7.1. Authentication (`/api/v1/auth`)
Handles user registration, login, and token management.

- **`POST /login`**: Authenticate user and return a JWT bearer token. Accepts `email`/`phone`/`identifier` and `password`.
- **`POST /register`**: Register a new user account.
- **`POST /activate`**: Activate a user account (admin/internal use).
- **`GET /me`**: Retrieve the currently authenticated user's profile and plan information.
- **`POST /user/update-password`**: Update the current user's password.

#### Google OAuth
- **`GET /google/auth`** & **`POST /google/auth`**: Initiate the Google OAuth flow. Can specify `tools` or `scopes` to request specific permissions.
- **`GET /google/callback`**: Handle the OAuth callback from Google.
- **`GET /google`** & **`POST /google`**: Check the status of Google authentication tokens and required scopes.
- **`POST /refresh-status-google`**: Refresh the Google authentication status for a specific agent.

#### API Keys
- **`POST /api-key`**: Generate a long-lived API key with a specific plan (`PRO_M`, `PRO_Y`, etc.).
- **`POST /api-key/trial`**: Issue a temporary trial API key based on IP address.
- **`POST /api-key/update`**: Extend or update an existing API key.

### 7.2. Agents (`/api/v1/agents`)
Core endpoints for managing and interacting with AI agents.

- **`GET /`**: List all agents belonging to the user.
- **`POST /`**: Create a new agent. Supports defining tools, LLM model, and system prompt. Returns auth requirements if Google tools are selected.
- **`GET /{agent_id}`**: Get details of a specific agent.
- **`PUT /{agent_id}`**: Update an agent's configuration.
- **`DELETE /{agent_id}`**: Delete an agent.

#### Execution
- **`POST /{agent_id}/execute`**: Run the agent with a specific input. Supports `session_id` for conversation memory.
- **`GET /{agent_id}/executions`**: Retrieve the execution history for an agent.
- **`GET /executions/stats`**: Get aggregate execution statistics for the user.

#### RAG & Documents
- **`POST /{agent_id}/documents`**: Upload a document (PDF, DOCX, TXT, etc.) for the agent's knowledge base. Handles chunking and vector embedding.
- **`GET /{agent_id}/documents`**: List all documents uploaded for an agent.
- **`DELETE /{agent_id}/documents/{upload_id}`**: Remove a document and its embeddings.

### 7.3. Tools (`/api/v1/tools`)
Endpoints for discovering and managing tools.

- **`GET /`**: List all available tools (builtin and custom).
- **`POST /`**: Register a new custom tool.
- **`GET /{tool_id}`**: Get details of a specific tool.
- **`PUT /{tool_id}`**: Update a tool definition.
- **`DELETE /{tool_id}`**: Delete a tool.
- **`POST /execute`**: Execute a specific tool directly (bypassing the agent).
- **`GET /schemas/{tool_name}`**: Get the JSON schema for a tool's parameters.
- **`GET /scopes/required`**: Check which OAuth scopes are needed for a list of tools.

### 7.4. System
- **`GET /health`**: Health check endpoint returning service status and version.
- **`GET /`**: Root endpoint providing API information.
