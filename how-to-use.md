# How to Use the LangChain API

The examples below assume the FastAPI server is running locally on port 8000. Update the variables if your deployment differs.

```bash
export BASE_URL="http://localhost:8000"
export API_PREFIX="/api/v1"  # Adjust if you change API_V1_STR or router prefixes
export TOKEN="paste-your-access-token-here"
```

`$TOKEN` should be the `access_token` value returned by the login or API key generation endpoints. Use `$BASE_URL$API_PREFIX` as the base for all versioned endpoints and include `-H "Authorization: Bearer $TOKEN"` on routes that require authentication.

## Frontend Quick Reference

- **Headers:** `Authorization: Bearer <token>` for protected routes, `Content-Type: application/json` for JSON bodies.
- **Auth responses:** `/auth/login` and `/auth/api-key` return `{ "access_token": "...", "token_type": "bearer", "expires_at": "<iso8601>"? }`.
- **Agent execute request:** `POST /agents/{agent_id}/execute` with `{ "input": "<user text>", "parameters": { ... }, "session_id": "<optional>" }`.
- **Agent execute response:** 
  ```json
  {
    "id": "execution-id",
    "status": "COMPLETED|FAILED|RUNNING",
    "output": {
      "output": "final text",
      "tools_used": ["google_calendar", "web_search"],
      "intermediate_steps": [
        {"tool": "google_calendar_list_events", "observation": "...", "tool_call_id": "..."}
      ],
      "execution_time": 1.23
    },
    "error_message": null
  }
  ```
- **Google OAuth hint:** Call `GET /auth/google` to get `auth_url` and `auth_state` if the user hasn’t linked Google yet. Frontend should open `auth_url` in a new tab, then retry the tool call after redirect completes.
- **CORS:** Origins are taken from server settings—when running locally the defaults include `http://localhost:3000` and `http://localhost:8000`.

## Updated Authentication Flow

The API now uses a two-step authentication process:

1. **Register User Account**: Create a user account
2. **Generate API Key**: Request an API key with specific plan and expiration

### Example Flow

```bash
# Step 1: Register user
# Register with email (replace with phone using identifier= or phone= query params)
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL$API_PREFIX/auth/register?email=newuser@example.com&password=changeme")
USER_ID=$(echo $REGISTER_RESPONSE | jq -r '.user_id')
echo "Registered user: $USER_ID"

# Step 2: Generate API key with PRO_M plan (30 days)
API_KEY_RESPONSE=$(curl -s -X POST "$BASE_URL$API_PREFIX/auth/api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser@example.com",
    "password": "changeme",
    "plan_code": "PRO_M"
  }')

# Check if API key generation was successful
if echo "$API_KEY_RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
    TOKEN=$(echo $API_KEY_RESPONSE | jq -r '.access_token')
    EXPIRES_AT=$(echo $API_KEY_RESPONSE | jq -r '.expires_at')
    echo "Generated API key expires at: $EXPIRES_AT"

    # Use the token for authenticated requests
    curl -H "Authorization: Bearer $JWT_TOKEN" "$BASE_URL$API_PREFIX/auth/me"
    # Response includes user profile fields, echoes the same token, and reports the plan code when an API key is used.
    # Example:
    # {
    #   "id": "0a1b2c3d-....",
    #   "email": "newuser@example.com",
    #   "is_active": true,
    #   "created_at": "2024-06-03T11:22:33.123456",
    #   "access_token": "...",  # Matches $TOKEN
    #   "plan_code": "PRO_M"
    # }
else
    echo "API key generation failed: $API_KEY_RESPONSE"
    echo "User account might not be activated yet. Contact administrator."
fi
```

### Troubleshooting Authentication

**If you get "User account is inactive" error:**

1. The user registration creates accounts with "inactive" status by default
2. Or check if there's an activation endpoint available

**Alternative: Use existing active user:**
If you have access to an already activated user account, use that email/password for API key generation.

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

  ```bash
  # Login with phone number (digits with optional +). identifier= takes precedence over email/phone.
  curl -X POST "$BASE_URL$API_PREFIX/auth/login?phone=%2B628123456789&password=changeme"
  ```

  The `password` query parameter accepts either a plaintext password or the stored bcrypt hash (prefix `$2b$12$` or legacy `$bcrypt-sha256$`). Passing the hash lets you authenticate without exposing the raw password when scripting.
  A successful login response returns a JSON payload containing `access_token` (the bearer credential) and `token_type`.

- **POST /register** (query parameters)

  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/register?email=newuser@example.com&password=changeme"
  ```

  ```bash
  # Register with a phone number by using phone= or identifier=
  curl -X POST "$BASE_URL$API_PREFIX/auth/register?phone=%2B628123456789&password=changeme"
  ```

  Returns user information without API key. Supply either `email`, `phone`, or `identifier` (email/phone string) along with the password. Phone numbers can include `+` and separators; the API normalizes them to digits only for storage. Use the API key generation endpoint to get access tokens.

- **POST /api-key** (JSON body)

  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/api-key" \
    -H "Content-Type: application/json" \
    -d '{
          "username": "user@example.com",
          "password": "password123",
          "plan_code": "PRO_M"
        }'
  ```

  Generates API key with plan-based expiration:

  - `PRO_M`: 30 days expiration
  - `PRO_Y`: 365 days expiration
  - `TRIAL`: 14 days (two weeks) expiration

    The `username` field accepts the email address or phone number used during registration.
    The `password` field accepts either the plaintext value or an existing bcrypt hash using prefix `$2b$12$`. Supplying the stored hash allows you to avoid sending the raw password.
    Older accounts might still have hashes starting with `$bcrypt-sha256$`; those are also accepted.

  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/api-key" \
    -H "Content-Type: application/json" \
    -d '{
          "username": "user@example.com",
          "password": "$2b$12$3btCYb.2P1M08/CxYFKE8uQXOv.QKtOn4POSTp2aG4ZXexthBkwA6",
          "plan_code": "PRO_M"
        }'
  ```

- **POST /api-key/update** (JSON body)

  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/api-key/update" \
    -H "Content-Type: application/json" \
    -d '{
          "username": "user@example.com",
          "password": "password123",
          "access_token": "existing-api-key-token",
          "plan_code": "PRO_M"
        }'
  ```

  Extends the selected plan’s expiration for an existing key and reactivates it if it was expired. Supported `plan_code` values match the generation endpoint (`PRO_M`, `PRO_Y`, `TRIAL`) with the same 30/365/14 day durations. Returns `true` on success. A bcrypt hash with prefix `$2b$12$` can be supplied in the `password` field as an alternative to the plaintext value.
  Hashes created before this change may use the `$bcrypt-sha256$` prefix and remain valid inputs.

- **POST /api-key/trial** (JSON body)

  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/api-key/trial" \
    -H "Content-Type: application/json" \
    -d '{
          "ip_user": "203.0.113.5"
        }'
  ```

  Issues a 14-day trial API key without requiring an account or prior authentication. The service stores the provided IP address and either returns an existing, still-active trial key for that IP or creates a new one tied to the `TRIAL` plan. When the trial expires, the key is removed automatically. Use the returned `access_token` in the `Authorization` header to explore the API and create agents during the trial window:

  ```bash
  curl "$BASE_URL$API_PREFIX/agents" \
    -H "Authorization: Bearer $(jq -r '.access_token' <<<"$TRIAL_KEY_RESPONSE")"
  ```

- **POST /user/update-password** (JSON body)

  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/user/update-password" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "user_id": "00000000-0000-0000-0000-000000000000",
          "new_password": "newSecurePassword"
        }'
  ```

  Updates the authenticated user’s password. The `new_password` accepts plaintext or a bcrypt hash (preferred `$2b$12$…`, legacy `$bcrypt-sha256$…` still supported).

- **GET /google**

  ```bash
  curl -X GET "$BASE_URL$API_PREFIX/auth/google" \
    -H "Authorization: Bearer $TOKEN"
  ```

  Add context so only the needed scopes are requested:

  ```bash
  # Request scopes for specific tools (recommended to avoid broad consent screens)
  curl -X GET "$BASE_URL$API_PREFIX/auth/google?tools=gmail_read_messages" \
    -H "Authorization: Bearer $TOKEN"

  # Or pass scopes directly (space- or comma-separated)
  curl -X GET "$BASE_URL$API_PREFIX/auth/google?scopes=https://www.googleapis.com/auth/gmail.readonly" \
    -H "Authorization: Bearer $TOKEN"

  # Bind to a specific agent so each agent can use different Google accounts/scopes
  curl -X GET "$BASE_URL$API_PREFIX/auth/google?tools=gmail_read_messages&agent_id=$AGENT_ID" \
    -H "Authorization: Bearer $TOKEN"
  ```

  Prefer sending scopes in the body to avoid URL length and quickly swap scope sets:

  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/google" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
          "agent_id": "00000000-0000-0000-0000-000000000000"
        }'
  ```

  Initiates Google OAuth authentication or returns the latest token payload when already linked. Supply `tools`/`scopes` via query or POST body; body values take precedence. Include `agent_id` when each agent should have its own Google account/scopes.

  **Note:** The system automatically handles scope changes from Google. When requesting `drive.file` scope, Google may add broader Drive scopes (`drive`, `drive.photos.readonly`, `drive.appdata`) which are accepted as long as all requested scopes are granted.

- **GET /refresh-status-google** (API key + `agent_id`)

  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/refresh-status-google" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "agent_id": "'"$AGENT_ID"'"
        }'
  ```

  Checks the Google OAuth status for a specific agent using API key auth and refreshes the token when a refresh token is available. The response includes the agent ID, whether a refresh occurred (`refreshed`), and a simple `status` string. If any Google token exists (agent-scoped first, then global), status is `Authenticated` and the payload includes `required_scopes`, `granted_scopes`, and `missing_scopes` so you can see exactly which scopes are available. If no Google token is stored, status is `Unauthenticated`.

- **GET /google/callback**

  ```bash
  curl "$BASE_URL$API_PREFIX/auth/google/callback?code=auth-code-from-google&state=state-token"
  ```

  Handles the OAuth callback from Google. The authorization token is not required for this endpoint.

- **GET /me**

  ```bash
  curl "$BASE_URL$API_PREFIX/auth/me" \
    -H "Authorization: Bearer $JWT_TOKEN"
  ```

Returns user metadata along with the JWT or API key that was supplied in the request. If the token matches an API key, the response also includes the associated `plan_code`, making it easy to confirm which credential and plan are active.

- **GET /google**
  ```bash
  curl "$BASE_URL$API_PREFIX/auth/google" \
    -H "Authorization: Bearer $TOKEN"
  ```
  Lists every stored auth token for the signed-in user. Look for entries where `service` is `google` to confirm a Google account has been linked and to inspect granted scopes and expirations.

## End-to-End Regression Script

Run the bundled regression script to exercise the full API surface—registration, activation, login, API keys, tools, agents, and optional Google OAuth—in one pass:

```bash
python3 scripts/endpoint_test_runner.py --help

# Example run against a local instance
python3 scripts/endpoint_test_runner.py \
  --base-url "$BASE_URL" \
  --api-prefix "$API_PREFIX" \
  --email "regression@example.com" \
  --password "S3curePass!" \
  --plan-code PRO_M
```

Each step reports whether it passed, failed, or was skipped, giving you a quick regression check on a running deployment.

## Agent Routes (`$API_PREFIX/agents`)

- **POST /** create agent

  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/agents/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "Research Assistant (MCP)",
          "google_tools": ["gmail"],
          "config": {
            "llm_model": "gpt-4o-mini",
            "temperature": 0.5,
            "system_prompt": "You can call remote tools to calculate, fetch, or search information."
          },
          "mcp_servers": {
            "langchain_mcp": {
              "transport": "streamable_http",
              "url": "http://localhost:8080/mcp/stream",
              "headers": {"Authorization": "Bearer jango"}
            }
          },
          "mcp_tools": ["web_search", "web_fetch", "pdf_generate", "docx_generate", "deep_research", "google_calendar", "send_reminder", "send_messages"]
        }'
  ```

  The response payload includes the stored MCP configuration. You can confirm the tools are available by running an execution that prompts the model to call one of the MCP tools (e.g., a calculator request) and checking the execution logs for tool usage.

- **PUT /{agent_id}** update agent details

  ```bash
  curl -X PUT "$BASE_URL$API_PREFIX/agents/$AGENT_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "Research Assistant v2",
          "config": {
            "system_prompt": "Keep conversations concise and always cite sources."
          },
          "mcp_tools": ["web_search", "web_fetch", "pdf_generate", "docx_generate", "deep_research", "google_calendar", "send_reminder", "send_messages"],
          "google_tools": [
            "gmail_get_message", "gmail_read_messages", "gmail_list_messages", "gmail_send_message", "gmail_create_draft",
            "google_calendar_list_events", "google_calendar_create_event", "google_calendar_get_event",
            "google_sheets_create_spreadsheet", "google_sheets_update_values", "google_sheets_get_values",
            "google_docs_list_documents", "google_docs_get_document", "google_docs_create_document", "google_docs_append_text", "google_docs_update_text", "google_docs_delete_document",
            "google_docs", "google_sheets_list_spreadsheets"
          ]
        }'
  ```

  All fields are optional—omit anything you do not want to change. Providing only `config.system_prompt` updates the system message without resetting other LLM settings. `mcp_tools` controls which MCP/remote tools an agent may call at runtime, while `google_tools` selects the Google/LangChain tools that require OAuth scopes.

  **Tip:** Untuk Google Docs actions (get/append/update/delete), sertakan `document_id` atau `document_url` (mis. `https://docs.google.com/document/d/<id>/edit`). Sistem akan otomatis mengekstrak `document_id` dari URL jika disediakan.

  If you want every agent to access tools hosted on your FastMCP server, declare the following environment variables before starting the API (see `mcp-server.md`). Streamable HTTP is preferred, with SSE as an optional fallback:

  ```
  MCP_HTTP_URL=http://localhost:8080/mcp/stream
  MCP_HTTP_TOKEN=your-secret-token
  MCP_HTTP_ALLOWED_TOOLS=calculator,web_search

  # Optional SSE fallback
  MCP_SSE_URL=http://localhost:8080
  MCP_SSE_TOKEN=your-secret-token
  MCP_SSE_ALLOWED_TOOLS=calculator,web_search
  MCP_SSE_ALLOWED_TOOL_CATEGORIES=math
  ```

  With these values in place the execution service retrieves remote tool definitions over HTTP and merges them with the agent's configured tools, falling back to SSE if available. Use `MCP_SSE_ALLOWED_TOOL_CATEGORIES` to keep the tool list scoped to specific categories such as `math`.

  Sanity check the connection:

  ```bash
  curl -X POST "$MCP_HTTP_URL/mcp/" \\
    -H "Authorization: Bearer $MCP_HTTP_TOKEN" \\
    -H "Content-Type: application/json" \\
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
  ```

  ### Creating Agents with MCP Tools

  Once the environment variables are in place, creating an agent that can use MCP tools is the same as creating any other agent—the MCP tools are added automatically at runtime. A minimal example:

  ```bash
   curl -X POST "$BASE_URL$API_PREFIX/agents/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "Agent Google 4",
          "google_tools": [
            "gmail_get_message", "gmail_read_messages", "gmail_list_messages", "gmail_send_message", "gmail_create_draft",
            "google_calendar_list_events", "google_calendar_create_event", "google_calendar_get_event",
            "google_sheets_create_spreadsheet", "google_sheets_update_values", "google_sheets_get_values",
            "google_docs_list_documents", "google_docs_get_document", "google_docs_create_document", "google_docs_append_text", "google_docs_update_text", "google_docs_delete_document",
            "google_docs", "google_sheets_list_spreadsheets"
          ],
          "config": {
            "llm_model": "gpt-4o-mini",
            "temperature": 0.5,
            "system_prompt": "Kamu adalah assistant pribadi saya yang dapat menggunakan semua tools ini: gmail_get_message, gmail_read_messages, gmail_list_messages, gmail_send_message, gmail_create_draft, google_calendar_list_events, google_calendar_create_event, google_calendar_get_event, google_sheets_create_spreadsheet , google_sheets_update_values, google_sheets_get_values, google_docs_list_documents, google_docs_get_document, google_docs_create_document, google_docs_append_text, google_docs_update_text, google_docs_delete_document, google_sheets_list_spreadsheets, google_docs"
          },
          "mcp_servers": {
            "calculator_sse": {
              "transport": "sse",
              "url": "http://0.0.0.0:8190/sse"
            }
          },
          "mcp_tools": ["web_search"]
        }'
  ```

  The response payload includes the stored MCP configuration. You can confirm the tools are available by running an execution that prompts the model to call one of the MCP tools (e.g., a calculator request) and checking the execution logs for tool usage.

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

  The response now includes `google_tools`, which contains the Google tool names inferred from the linked OAuth scopes for this `agent_id`. Example payload:

  ```json
  {
    "id": "66aa4e6c-f7c3-4356-a7a8-09ffb4aab067",
    "user_id": "f6939327-881d-4e85-91b0-29ec3ddcbd60",
    "name": "CS Mukenaku",
    "config": {
      "llm_model": "gpt-4o-mini",
      "max_tokens": 1500,
      "memory_type": "buffer",
      "temperature": 0.1,
      "system_prompt": "Kamu Hebat",
      "reasoning_strategy": "react"
    },
    "status": "active",
    "created_at": "2025-11-24T02:24:47.581490Z",
    "updated_at": "2025-11-24T02:35:54.610572Z",
    "mcp_servers": {
      "calculator_sse": {
        "env": {},
        "url": "http://0.0.0.0:8190/sse",
        "args": [],
        "headers": {},
        "transport": "sse"
      }
    },
    "mcp_tools": [
      "web_search",
      "fetch_web"
    ],
    "google_tools": [
      "gmail_get_message",
      "gmail_read_messages",
      "gmail_list_messages",
      "gmail_send_message"
    ]
  }
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
  curl "$BASE_URL$API_PREFIX/tools?tool_type=custom" \
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
          "type": "custom"
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

- **POST /execute**
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/tools/execute" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "tool_id": "TOOL_ID",
          "parameters": {
            "directory": "/data/reports",
            "pattern": "*.csv",
            "recursive": true
          }
        }'
  ```
  The execution payload is routed to the registered tool. Built-in tools include file utilities (`csv`, `json`, `file_list`, `docx`, `spreadsheet`) in addition to Google Workspace integrations.

### DOCX & Spreadsheet helpers

- **Read a DOCX file**
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/tools/execute" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "tool_id": "docx",
          "parameters": {
            "action": "read",
            "file_path": "/data/notes/summary.docx"
          }
        }'
  ```

- **Write spreadsheet rows to `Sheet1`**
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/tools/execute" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "tool_id": "spreadsheet",
          "parameters": {
            "action": "write",
            "file_path": "/data/reports/metrics.xlsx",
            "sheet_name": "Sheet1",
            "data": [
              {"metric": "signups", "value": 120},
              {"metric": "churn", "value": 4}
            ]
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

Successful uploads return chunk statistics, embedding ids, and a unique `upload_id`:

```json
{
  "message": "Document processed and embeddings stored.",
  "chunks": 18,
  "embedding_ids": ["d5e9d4f6-4f2d-4a3b-861a-6b5430a96a16", "..."],
  "upload_id": "80b6ed2c-2d5d-4235-9e9f-9f9c1545b203"
}
```

### List Uploaded Files

Every ingestion is logged for easier management. Use the new history endpoint to review uploads (active and deleted):

```bash
curl "$BASE_URL$API_PREFIX/agents/$AGENT_ID/documents" \
  -H "Authorization: Bearer $TOKEN" \
  | jq
```

Response shape:

```json
{
  "uploads": [
    {
      "id": "80b6ed2c-2d5d-4235-9e9f-9f9c1545b203",
      "agent_id": "d3e9c51d-5a29-4d6f-94b9-88dbe3fbbbfc",
      "filename": "report.pdf",
      "content_type": "application/pdf",
      "size_bytes": 482131,
      "chunk_count": 18,
      "embedding_ids": ["d5e9d4f6-4f2d-4a3b-861a-6b5430a96a16", "..."],
      "details": {
        "chunk_size": 400,
        "chunk_overlap": 80,
        "batch_size": 50,
        "characters": 41523,
        "adjusted": false
      },
      "is_deleted": false,
      "deleted_at": null,
      "created_at": "2025-10-20T06:12:01.145321+00:00",
      "updated_at": "2025-10-20T06:12:01.145321+00:00"
    }
  ]
}
```

### Delete an Uploaded File

To remove the original upload and its associated embeddings, call:

```bash
curl -X DELETE "$BASE_URL$API_PREFIX/agents/$AGENT_ID/documents/$UPLOAD_ID" \
  -H "Authorization: Bearer $TOKEN" \
  | jq
```

The response echoes the upload record with `is_deleted` set to `true`. Embeddings created from the upload are removed inside the same transaction.

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

## Troubleshooting

### Google OAuth Issues

#### "Scope has changed" Error

If you encounter this error during Google authentication:

```json
{ "detail": "Google authentication failed: Scope has changed from ..." }
```

**This is normal behavior.** Google automatically adds broader scopes when certain scopes (like `drive.file`) are requested. The system now handles these changes gracefully.

**Solution:** The authentication should work automatically now. If it still fails:

1. Try re-authenticating by calling `/api/v1/auth/google` again
2. Follow the OAuth flow completely
3. The system will automatically handle scope differences

#### Missing Google Scopes

If you're missing required Google scopes, ensure you've enabled these APIs in Google Cloud Console:

- Gmail API
- Google Calendar API
- Google Sheets API
- Google Drive API
- Google Docs API

#### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the required APIs listed above
4. Create OAuth 2.0 credentials (Web Application)
5. Add redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
6. Copy Client ID and Client Secret to your `.env` file

### Agent Creation Issues

#### Agent Creation Fails with Google Tools

When creating an agent with Google Workspace tools:

```bash
curl -X POST "$BASE_URL$API_PREFIX/agents/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Email Assistant",
    "google_tools": ["gmail_get_message", "gmail_read_messages", "gmail_list_messages", "gmail_send_message", "gmail_create_draft"],
    "mcp_tools": ["web_search"],
    "config": {...}
  }'
```

If the response includes `"auth_required": true`, you need to complete Google OAuth:

1. Visit the `auth_url` provided in the response
2. Complete the OAuth flow
3. The agent will then be able to use Google tools

### API Key Issues

#### API Key Expiration

API keys have plan-based expiration:

- `PRO_M`: 30 days
- `PRO_Y`: 365 days

To check when your key expires:

```bash
curl "$BASE_URL$API_PREFIX/auth/me" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

Review the `access_token` field in the response to double-check that you are inspecting the expected key.

To generate a new key:

```bash
curl -X POST "$BASE_URL$API_PREFIX/auth/api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-email@example.com",
    "password": "your-password",
    "plan_code": "PRO_M"
  }'
```

### Document Ingestion Issues

#### Unsupported File Types

Only these file types are supported for document ingestion:

- `application/pdf` (.pdf)
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (.docx)
- `application/vnd.openxmlformats-officedocument.presentationml.presentation` (.pptx)
- `text/plain` (.txt)

#### Large Files

For large files, consider adjusting these parameters:

- `chunk_size`: Smaller chunks for better relevance (default: 400)
- `chunk_overlap`: Overlap between chunks (default: 80)
- `batch_size`: Number of chunks to process at once (default: 50)

### Performance Issues

#### Slow Agent Execution

- Use appropriate `max_tokens` limits
- Adjust `temperature` for faster responses (lower = faster)
- Use session IDs to maintain context and reduce repetition
- Limit the number of tools per agent

#### Database Performance

- Ensure PostgreSQL is properly tuned
- Use connection pooling
- Consider read replicas for high-traffic deployments

### Common Error Messages

#### "Required scopes not granted"

This means Google didn't grant all the scopes your agent needs. Check:

1. All required APIs are enabled in Google Cloud Console
2. User has granted necessary permissions during OAuth
3. OAuth consent screen is properly configured

#### "Agent execution failed"

Common causes:

- Missing API keys (OpenAI, Google)
- Insufficient permissions for Google services
- Invalid agent configuration
- Tool execution errors

Check the execution logs for detailed error information.
