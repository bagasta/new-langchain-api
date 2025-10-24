# How to Use the LangChain API

All commands assume the FastAPI server is running locally on port 8000. Replace the values with your own deployment information.

```bash
export BASE_URL="http://localhost:8000"
export API_PREFIX="/api/v1"
```

## Tokens and Headers

- `/auth/login` returns a short-lived JWT in the `jwt_token` field. Use it for user-scoped endpoints such as Google OAuth and password updates.
- `/auth/api-key` returns a long-lived API key in the `access_token` field. Agent and tool routes require this token because they validate against the `api_keys` table.

```bash
# After successful authentication
export JWT_TOKEN="copy-from-/auth/login"
export JWT_AUTH_HEADER="Authorization: Bearer $JWT_TOKEN"

export API_KEY="copy-from-/auth/api-key"
export AUTH_HEADER="Authorization: Bearer $API_KEY"
```

Use `$JWT_AUTH_HEADER` when an endpoint only needs a valid user session. Use `$AUTH_HEADER` for any route that depends on `get_api_key_user` (all agent and tool mutations as well as executions).

## Public Routes

### GET /
- Auth: none
- Returns a welcome payload with links to `/docs` and `/health`.

```bash
curl "$BASE_URL/"
```

### GET /health
- Auth: none
- Returns service status, project name, and version.

```bash
curl "$BASE_URL/health"
```

## Authentication API (`$API_PREFIX/auth`)

### POST /register
- Auth: none
- Query parameters: provide `email` or `phone` (or `identifier`), plus `password`.
- Creates an inactive user record and returns the newly created user ID.

```bash
curl -X POST \
  "$BASE_URL$API_PREFIX/auth/register?email=newuser@example.com&password=changeme"
```

### POST /activate
- Auth: none
- Query parameter: `email`.
- Marks the user as active. Use this endpoint or update the database manually before generating an API key.

```bash
curl -X POST \
  "$BASE_URL$API_PREFIX/auth/activate?email=newuser@example.com"
```

### POST /login
- Auth: none
- Query parameters mirror `/register`.
- Returns `{"jwt_token": "...", "token_type": "bearer"}`.

```bash
curl -X POST \
  "$BASE_URL$API_PREFIX/auth/login?email=newuser@example.com&password=changeme"
```

### POST /api-key
- Auth: none
- JSON body: `username`, `password`, `plan_code` (`PRO_M` for 30 days, `PRO_Y` for 365 days).
- Validates the credentials and issues a bearer token stored in the `api_keys` table.

```bash
curl -X POST "$BASE_URL$API_PREFIX/auth/api-key" \
  -H "Content-Type: application/json" \
  -d '{
        "username": "newuser@example.com",
        "password": "changeme",
        "plan_code": "PRO_M"
      }'
```

A successful response includes `access_token`, `token_type`, `expires_at`, and `plan_code`. Save `access_token` as `$API_KEY`.

### POST /api-key/update
- Auth: none
- JSON body: `username`, `password`, `access_token`, `plan_code`.
- Extends the expiration for an existing API key and reactivates it if necessary.

```bash
curl -X POST "$BASE_URL$API_PREFIX/auth/api-key/update" \
  -H "Content-Type: application/json" \
  -d '{
        "username": "newuser@example.com",
        "password": "changeme",
        "access_token": "'"$API_KEY"'",
        "plan_code": "PRO_Y"
      }'
```

### GET /me
- Auth: bearer (`$JWT_AUTH_HEADER` or `$AUTH_HEADER`).
- Returns the current user profile and, when using an API key, the associated `plan_code`.

```bash
curl -H "$AUTH_HEADER" "$BASE_URL$API_PREFIX/auth/me"
```

### POST /user/update-password
- Auth: bearer (JWT or API key).
- JSON body: `user_id`, `new_password` (plaintext or supported bcrypt hash).
- Only the authenticated user can update their own password.

```bash
curl -X POST "$BASE_URL$API_PREFIX/auth/user/update-password" \
  -H "$JWT_AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
        "user_id": "'"$USER_ID"'",
        "new_password": "StrongNewPassword123!"
      }'
```

### GET or POST /google/auth
- Auth: bearer (`$JWT_AUTH_HEADER` recommended).
- Initiates Google OAuth and returns `{ "auth_url": "...", "state": "..." }`.
- `POST` keeps backward compatibility with clients that send `{ "email": "..." }`, but the payload is ignored.

```bash
curl -H "$JWT_AUTH_HEADER" "$BASE_URL$API_PREFIX/auth/google/auth"
```

### GET /google/callback
- Auth: none (Google redirects the browser here).
- Query parameters: `code`, `state`, optional `scope`.
- Exchanges the authorization code, persists tokens, and links them to the requesting user.

### GET /google
- Auth: bearer (`$JWT_AUTH_HEADER`).
- Lists stored OAuth tokens, including granted scopes and expiration times.

```bash
curl -H "$JWT_AUTH_HEADER" "$BASE_URL$API_PREFIX/auth/google"
```

## Agents API (`$API_PREFIX/agents`)

> Every endpoint in this section requires an API key (`-H "$AUTH_HEADER"`). The dependency layer verifies that the token exists in the `api_keys` table and is not expired.

### POST /
- Creates a new agent.
- JSON body fields:
  - `name` (string, required).
  - `tools` (list of tool names; duplicates are removed).
  - `config` (LLM configuration; defaults to `{"llm_model": "gpt-3.5-turbo", "temperature": 0.7, "max_tokens": 1000, "memory_type": "buffer", "reasoning_strategy": "react"}`).
  - `mcp_servers` (optional mapping of MCP server aliases to transport config).
  - `allowed_tools` (optional allow-list for MCP/remote tools; built-in tools listed in `tools` remain available, while remote tools are filtered to these names).
- Response mirrors the stored agent and adds Google OAuth hints when required tools demand scopes the user has not granted yet (`auth_required`, `auth_url`, `auth_state`).
- When `allowed_tools` contains entries, MCP tool discovery uses them as a whitelist (categories are ignored). Declare each remote tool you want reachable; any other remote tools the server exposes are dropped.

```bash
curl -X POST "$BASE_URL$API_PREFIX/agents/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Research Assistant",
        "tools": ["web_search", "gmail"],
        "config": {
          "llm_model": "gpt-4o-mini",
          "temperature": 0.4,
          "max_tokens": 1200,
          "system_prompt": "Provide concise, sourced answers."
        },
        "allowed_tools": ["web_search", "calculator"],
        "mcp_servers": {
          "langchain_mcp": {
            "transport": "streamable_http",
            "url": "http://localhost:8080/mcp/stream",
            "headers": {"Authorization": "Bearer token"}
          }
        }
      }'
```

Ensure `OPENAI_API_KEY` is set globally or embedded inside `config.llm_model` options; otherwise executions will fail.

### GET /
- Lists the authenticated user's agents.

```bash
curl -H "$AUTH_HEADER" "$BASE_URL$API_PREFIX/agents/"
```

### GET /{agent_id}
- Fetches a single agent by UUID.

### PUT /{agent_id}
- Updates agent metadata. Include only the fields you want to change (`name`, `tools`, `config`, `status`, `allowed_tools`, `mcp_servers`).

### DELETE /{agent_id}
- Deletes the agent and cascades to associated agent-tool mappings.

### POST /{agent_id}/execute
- Runs an agent conversation.
- JSON body: `input` (prompt), optional `parameters` dict, optional `session_id`.
- Response returns `execution_id`, `status`, `message`, `response`, and the `session_id` that was used.

The execution history is persisted; reuse the same `session_id` to preserve conversational context.

### GET /{agent_id}/executions
- Returns historical executions for the agent, including inputs, outputs, status, duration (ms), and timestamps.

### GET /executions/stats
- Aggregates executions across all agents owned by the user.
- Response includes `total_executions`, `completed_executions`, `failed_executions`, `success_rate`, and `average_duration_ms`.

### Document Ingestion (`/agents/{agent_id}/documents`)
These endpoints manage knowledge files linked to an agent.

#### POST /{agent_id}/documents
- Uploads a document, extracts clean text, and stores embeddings.
- Multipart fields:
  - `file` (required; content types: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/vnd.openxmlformats-officedocument.presentationml.presentation`, `text/plain`).
  - `chunk_size`, `chunk_overlap`, `batch_size` (all optional overrides).
- Response includes the ingestion summary (`chunks`, `embedding_ids`, `upload_id`).

```bash
curl -X POST "$BASE_URL$API_PREFIX/agents/$AGENT_ID/documents" \
  -H "$AUTH_HEADER" \
  -F "file=@/path/to/report.pdf" \
  -F "chunk_size=400" \
  -F "chunk_overlap=80"
```

#### GET /{agent_id}/documents
- Lists uploads tied to the agent, including metadata, chunk statistics, and soft-deletion flags.

#### DELETE /{agent_id}/documents/{upload_id}
- Removes the upload record and associated embeddings in a single transaction. The response echoes the upload record with `is_deleted: true` and timestamps.

## Tools API (`$API_PREFIX/tools`)

- `GET` endpoints are publicly accessible.
- `POST`, `PUT`, `DELETE`, and `/execute` require an API key (`-H "$AUTH_HEADER"`).

### GET /
- Optional query parameter: `tool_type=builtin|custom`.
- Returns available tools.

```bash
curl "$BASE_URL$API_PREFIX/tools?tool_type=custom"
```

### POST /
- Creates a new custom tool owned by the requesting user.
- JSON body:
  - `name` (unique per workspace).
  - `description`.
  - `schema` (JSON Schema describing parameters).
  - `type` (`custom` by default; `builtin` is reserved).

### GET /{tool_id}
- Returns a single tool definition by UUID.

### PUT /{tool_id}
- Updates mutable fields (`name`, `description`, `schema`).

### DELETE /{tool_id}
- Deletes the tool and drops any agent-tool links.

### POST /execute
- Runs a tool directly.
- Body: `tool_id`, `parameters`.
- Response structure depends on the tool implementation and includes optional `execution_time` and `error`.

```bash
curl -X POST "$BASE_URL$API_PREFIX/tools/execute" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
        "tool_id": "uuid-of-tool",
        "parameters": {
          "directory": "/shared/reports",
          "pattern": "*.csv",
          "recursive": true
        }
      }'
```

### GET /schemas/{tool_name}
- Returns the schema for a built-in tool.

### GET /scopes/required
- Query parameter: `tools` (comma-separated names).
- Returns `{ "scopes": [...] }` describing the Google OAuth scopes required by each tool. Use this before agent creation to avoid missing-scope errors.

## Troubleshooting

### Google OAuth
- If a response from `/agents/` includes `auth_required: true`, open the returned `auth_url` to grant the required scopes. The API stores tokens under `/auth/google`.
- Google occasionally broadens requested scopes (for example, requesting `drive.file` may add the full Drive scope). The API normalizes scope differences automatically.

### API Keys
- `PRO_M` keys expire after 30 days; `PRO_Y` keys last 365 days. Use `/auth/api-key/update` to extend a key.
- When calling `/auth/me` with an API key, verify that the returned `access_token` matches the key you expect and that `plan_code` aligns with your plan.

### Document Uploads
- Only PDF, DOCX, PPTX, and plain-text files are accepted.
- Adjust `chunk_size`, `chunk_overlap`, and `batch_size` if ingestion is slow or the embeddings feel too coarse.

### Agent Execution
- Ensure `OPENAI_API_KEY` is configured globally or included in the agent config when using OpenAI-hosted models.
- Set `session_id` to segment conversations; executions without a session ID share no memory.
- Inspect `/agents/{agent_id}/executions` for detailed error messages when a run fails.
