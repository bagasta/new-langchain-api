# How to Use the LangChain API

The examples below assume the FastAPI server is running locally on port 8000. Update the variables if your deployment differs.

```bash
export BASE_URL="https://lfzlwlbz-8000.asse.devtunnels.ms"
export API_PREFIX="/api/v1"  # Adjust if you change API_V1_STR or router prefixes
export TOKEN="paste-your-jwt-here"
```

Use `$BASE_URL$API_PREFIX` as the base for all versioned endpoints and include `-H "Authorization: Bearer $TOKEN"` on routes that require authentication.

## Public Endpoints

- **GET /**
  ```bash
  curl "$BASE_URL/"
  ```
  If the agent includes Google Workspace tools (e.g. `gmail`, `google_sheets`) and you haven't linked a Google account yet, the response will include `auth_required`, `auth_url`, and `auth_state`. Visit the URL to complete OAuth before executing the agent.

- **GET /health**
  ```bash
  curl "$BASE_URL/health"
  ```

## Authentication Routes (`$API_PREFIX/auth`)

- **POST /login** (query parameters)
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/login?email=user@example.com&password=changeme"
  ```

- **POST /register** (query parameters)
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/register?email=newuser@example.com&password=changeme"
  ```

- **POST /google/auth**
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/google/auth" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "tools": ["gmail", "google_sheets"]
        }'
  ```
  When new scopes are required the response includes `{"auth_required": true, "auth_url": "...", "state": "..."}`; otherwise `auth_required` is `false`, indicating your current Google connection already covers the requested tools.

- **GET /google/callback**
  ```bash
  curl "$BASE_URL$API_PREFIX/auth/google/callback?code=auth-code-from-google&state=state-token" \
    -H "Authorization: Bearer $TOKEN"
  ```
  On success the payload includes `auth_required`, `auth_url`, and `missing_scopes`. If `auth_required` is `true`, Google only granted a subset of the requested permissions—follow the returned `auth_url` to complete the consent flow again.

- **GET /google/auth** (optional `tools` query parameter)
  ```bash
  curl "$BASE_URL$API_PREFIX/auth/google/auth?tools=gmail,google_sheets" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **GET /me**
  ```bash
  curl "$BASE_URL$API_PREFIX/auth/me" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **GET /tokens**
  ```bash
  curl "$BASE_URL$API_PREFIX/auth/tokens" \
    -H "Authorization: Bearer $TOKEN"
  ```

## Tool Routes (`$API_PREFIX/tools`)

- **GET /** list available tools
  ```bash
  curl "$BASE_URL$API_PREFIX/tools/" \
    -H "Authorization: Bearer $TOKEN"
  ```

### Available Built-in Tools:
- `gmail` - Read and send emails using Gmail
- `google_sheets` - Read and write data from Google Sheets
- `google_calendar` - List and create Google Calendar events
- `csv` - Read and write CSV files
- `json` - Read and write JSON files
- `file_list` - List files in a directory

## Agent Routes (`$API_PREFIX/agents`)

- **POST /** create agent
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/agents/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "Research Assistant",
          "tools": ["gmail", "google_sheets"],
          "config": {
            "llm_model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 1000,
            "memory_type": "buffer",
            "reasoning_strategy": "react",
            "system_prompt": "You are a helpful research aide. Remember the users name and refer back to earlier answers when possible"
          }
        }'
  ```

- **GET /** list agents
  ```bash
  curl "$BASE_URL$API_PREFIX/agents/" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **GET /{agent_id}**
  ```bash
  curl "$BASE_URL$API_PREFIX/agents/AGENT_ID" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **PUT /{agent_id}**
  ```bash
  curl -X PUT "$BASE_URL$API_PREFIX/agents/AGENT_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "Updated Agent Name",
          "status": "ACTIVE"
        }'
  ```

- **DELETE /{agent_id}**
  ```bash
  curl -X DELETE "$BASE_URL$API_PREFIX/agents/AGENT_ID" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **POST /{agent_id}/execute**
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/agents/AGENT_ID/execute" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "input": "Summarize the latest news about AI.",
          "parameters": {
            "max_steps": 5
          },
          "session_id": "demo-session-1"
        }'
  ```
  The response includes a `response` field containing the assistant's reply. Conversation history is persisted in the `executions` table and is automatically replayed on subsequent executions.
  Use the optional `session_id` field to partition memory (only executions sharing the same session id are replayed).

- **GET /{agent_id}/executions**
  ```bash
  curl "$BASE_URL$API_PREFIX/agents/AGENT_ID/executions" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **GET /executions/stats**
  ```bash
  curl "$BASE_URL$API_PREFIX/agents/executions/stats" \
    -H "Authorization: Bearer $TOKEN"
  ```

## Tool Routes (`$API_PREFIX/tools`)

- **GET /** list tools (optional `tool_type`)
  ```bash
  curl "$BASE_URL$API_PREFIX/tools?tool_type=CUSTOM" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **POST /** create tool
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/tools" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "gmail",
          "description": "Reads recent Gmail messages",
          "schema": {
            "type": "object",
            "properties": {
              "query": {"type": "string"},
              "max_results": {"type": "integer"}
            },
            "required": ["query"]
          },
          "type": "CUSTOM"
        }'
  ```

- **GET /{tool_id}**
  ```bash
  curl "$BASE_URL$API_PREFIX/tools/TOOL_ID" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **PUT /{tool_id}**
  ```bash
  curl -X PUT "$BASE_URL$API_PREFIX/tools/TOOL_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "description": "Updated description",
          "schema": {
            "type": "object",
            "properties": {
              "query": {"type": "string"},
              "label": {"type": "string"}
            },
            "required": ["query"]
          }
        }'
  ```

- **DELETE /{tool_id}**
  ```bash
  curl -X DELETE "$BASE_URL$API_PREFIX/tools/TOOL_ID" \
    -H "Authorization: Bearer $TOKEN"
  ```

## Web Dashboard (React)

A user dashboard is available under the `dashboard/` directory. It wraps the API endpoints above and does not introduce any new backend logic.

### Prerequisites

```bash
cd dashboard
npm install
```

Create a `.env` file (or export an environment variable) with the API base URL if it differs from the default:

```bash
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
```

### Local development

```bash
npm run dev
```

The Vite development server defaults to http://localhost:5173 and proxies every request directly to the FastAPI service at `VITE_API_BASE_URL`.

### Production build

```bash
npm run build
npm run preview  # optional local preview of the production build
```

### Available screens

- **Login / Register** – uses `/api/v1/auth/login` and `/api/v1/auth/register` to obtain a JWT before loading the dashboard.
- **Dashboard** – lists your agents, shows available tools and Google tokens, and surfaces aggregate execution stats.
- **Agent Detail** – executes prompts via `/api/v1/agents/{agent_id}/execute` and displays the historical records from `/api/v1/agents/{agent_id}/executions`.

All API calls are made through the existing REST endpoints; no additional routes or side effects were introduced.

- **POST /execute**
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/tools/execute" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "tool_id": "TOOL_ID",
          "parameters": {
            "query": "latest unread",
            "max_results": 10
          }
        }'
  ```

## Document Ingestion (`$API_PREFIX/agents/{agent_id}/documents`)

Upload knowledge files so an agent can reference them later. Supported formats: `pdf`, `docx`, `pptx`, `txt`.

```bash
curl -X POST "$BASE_URL$API_PREFIX/agents/$AGENT_ID/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/report.pdf" \
  -F "chunk_size=400" \
  -F "chunk_overlap=80" \
  -F "batch_size=50"
```

The API converts the file to plain text, removes noisy characters, chunks the content, embeds each chunk with OpenAI, and stores the vectors in the `embeddings` table.

- **GET /schemas/{tool_name}**
  ```bash
  curl "$BASE_URL$API_PREFIX/tools/schemas/gmail" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **GET /scopes/required** (comma-separated `tools` list)
  ```bash
  curl "$BASE_URL$API_PREFIX/tools/scopes/required?tools=gmail,google_sheets" \
    -H "Authorization: Bearer $TOKEN"
  ```

Replace placeholders (`AGENT_ID`, `TOOL_ID`, `TOKEN`, etc.) with real values from your environment. All sample payloads are minimal; include any additional fields your workflow requires.
