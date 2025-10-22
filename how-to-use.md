# How to Use the LangChain API

The examples below assume the FastAPI server is running locally on port 8000. Update the variables if your deployment differs.

```bash
export BASE_URL="http://localhost:8000"
export API_PREFIX="/api/v1"  # Adjust if you change API_V1_STR or router prefixes
export TOKEN="paste-your-jwt-here"
```

Use `$BASE_URL$API_PREFIX` as the base for all versioned endpoints and include `-H "Authorization: Bearer $TOKEN"` on routes that require authentication.

## Updated Authentication Flow

The API now uses a two-step authentication process:

1. **Register User Account**: Create a user account
2. **Activate User**: User account needs to be activated (contact admin or check database)
3. **Generate API Key**: Request an API key with specific plan and expiration

### Example Flow

```bash
# Step 1: Register user
# Register with email (replace with phone using identifier= or phone= query params)
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL$API_PREFIX/auth/register?email=newuser@example.com&password=changeme")
USER_ID=$(echo $REGISTER_RESPONSE | jq -r '.user_id')
echo "Registered user: $USER_ID"

# Step 2: User needs to be activated (contact admin or check database status)
# Note: Users are created as "inactive" by default and need activation

# Step 3: Generate API key with PRO_M plan (30 days)
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
    curl -H "Authorization: Bearer $TOKEN" "$BASE_URL$API_PREFIX/auth/me"
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
2. Contact your system administrator to activate the user account
3. Or check if there's an activation endpoint available

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

- **POST /auth/login** (query parameters)
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/login?email=user@example.com&password=changeme"
  ```
  ```bash
  # Login with phone number (digits with optional +). identifier= takes precedence over email/phone.
  curl -X POST "$BASE_URL$API_PREFIX/auth/login?phone=%2B628123456789&password=changeme"
  ```
  The `password` query parameter accepts either a plaintext password or the stored bcrypt hash (prefix `$2b$12$` or legacy `$bcrypt-sha256$`). Passing the hash lets you authenticate without exposing the raw password when scripting.
  A successful login response returns a JSON payload containing `jwt_token` (the bearer credential) and `token_type`.

- **POST /auth/register** (query parameters)
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/register?email=newuser@example.com&password=changeme"
  ```
  ```bash
  # Register with a phone number by using phone= or identifier=
  curl -X POST "$BASE_URL$API_PREFIX/auth/register?phone=%2B628123456789&password=changeme"
  ```
  Returns user information without API key. Supply either `email`, `phone`, or `identifier` (email/phone string) along with the password. Phone numbers can include `+` and separators; the API normalizes them to digits only for storage. Use the API key generation endpoint to get access tokens.

- **POST /auth/api-key** (JSON body)
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

- **POST /auth/api-key/update** (JSON body)
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
  Extends the selected plan’s expiration for an existing key and reactivates it if it was expired. Returns `true` on success. A bcrypt hash with prefix `$2b$12$` can be supplied in the `password` field as an alternative to the plaintext value.
  Hashes created before this change may use the `$bcrypt-sha256$` prefix and remain valid inputs.

- **POST /auth/user/update-password** (JSON body)
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

- **POST /auth/google/auth**
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/google" \
    -H "Authorization: Bearer $TOKEN"
  ```
  This endpoint initiates Google OAuth authentication. It no longer requires a request body.

  **Note:** The system automatically handles scope changes from Google. When requesting `drive.file` scope, Google may add broader Drive scopes (`drive`, `drive.photos.readonly`, `drive.appdata`) which are accepted as long as all requested scopes are granted.

- **GET /auth/google/auth**
  ```bash
  curl -X GET "$BASE_URL$API_PREFIX/auth/google/auth" \
    -H "Authorization: Bearer $TOKEN"
  ```
  GET method also available for clickable links.

- **GET /auth/google/callback**
  ```bash
  curl "$BASE_URL$API_PREFIX/auth/google/callback?code=auth-code-from-google&state=state-token"
  ```
  Handles the OAuth callback from Google. The authorization token is not required for this endpoint. Successful responses now return a simple confirmation payload:
  ```json
  {"message": "Google authentication successful"}
  ```

- **GET /auth/me**
  ```bash
  curl "$BASE_URL$API_PREFIX/auth/me" \
    -H "Authorization: Bearer $TOKEN"
  ```
  Returns user metadata along with the JWT or API key that was supplied in the request. If the token matches an API key, the response also includes the associated `plan_code`, making it easy to confirm which credential and plan are active.

- **GET /auth/google**
  ```bash
  curl "$BASE_URL$API_PREFIX/auth/google" \
    -H "Authorization: Bearer $TOKEN"
  ```
  Lists every stored auth token for the signed-in user. Look for entries where `service` is `google` to confirm a Google account has been linked and to inspect granted scopes and expirations.

## Agent Routes (`$API_PREFIX/agents`)

- **POST /agents** create agent
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/agents/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "Research Assistant",
          "tools": ["gmail"],
          "config": {
            "llm_model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 1000,
            "memory_type": "buffer",
            "reasoning_strategy": "react",
            "system_prompt": "You are a helpful research aide. Remember the user's name and refer back to earlier answers when possible."
          }
        }'
  ```
  Include Google tools only if you have already linked the relevant account, otherwise the response will return `auth_required: true` and an OAuth URL.

- **PUT /agents/{agent_id}** update agent details
  ```bash
  curl -X PUT "$BASE_URL$API_PREFIX/agents/$AGENT_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "Research Assistant v2",
          "config": {
            "system_prompt": "Keep conversations concise and always cite sources."
          },
          "allowed_tools": ["web_search", "calculator"],
          "tools": ["web_search", "calculator"]
        }'
  ```
  All fields are optional—omit anything you do not want to change. Providing only `config.system_prompt` updates the system message without resetting other LLM settings. `allowed_tools` controls which MCP/remote tools an agent may call at runtime, while `tools` updates the core LangChain tool list.

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
          "name": "Research Assistant (MCP)",
          "tools": [],
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
          "allowed_tools": ["calculator", "web_fetch", "web_search", "pdf_generate"]
        }'
  ```

  The response payload includes the stored MCP configuration. You can confirm the tools are available by running an execution that prompts the model to call one of the MCP tools (e.g., a calculator request) and checking the execution logs for tool usage.

- **GET /agents** list agents
  ```bash
  curl "$BASE_URL$API_PREFIX/agents/" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **GET /agents/{agent_id}**
  ```bash
  curl "$BASE_URL$API_PREFIX/agents/AGENT_ID" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **DELETE /agents/{agent_id}**
  ```bash
  curl -X DELETE "$BASE_URL$API_PREFIX/agents/AGENT_ID" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **POST /agents/{agent_id}/execute**
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

- **GET /agents/{agent_id}/executions**
  ```bash
  curl "$BASE_URL$API_PREFIX/agents/AGENT_ID/executions" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **GET /agents/executions/stats**
  ```bash
  curl "$BASE_URL$API_PREFIX/agents/executions/stats" \
    -H "Authorization: Bearer $TOKEN"
  ```

## Tool Routes (`$API_PREFIX/tools`)

- **GET /tools** list tools (optional `tool_type`)
  ```bash
  curl "$BASE_URL$API_PREFIX/tools?tool_type=custom" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **POST /tools** create tool
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

- **GET /tools/{tool_id}**
  ```bash
  curl "$BASE_URL$API_PREFIX/tools/TOOL_ID" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **PUT /tools/{tool_id}**
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

- **DELETE /tools/{tool_id}**
  ```bash
  curl -X DELETE "$BASE_URL$API_PREFIX/tools/TOOL_ID" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **POST /tools/execute**
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
  The execution payload is routed to the registered tool. Built-in tools include file utilities (`csv`, `json`, `file_list`) in addition to Google Workspace integrations.

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
  "embedding_ids": [
    "d5e9d4f6-4f2d-4a3b-861a-6b5430a96a16",
    "..."
  ],
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
      "embedding_ids": [
        "d5e9d4f6-4f2d-4a3b-861a-6b5430a96a16",
        "..."
      ],
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

- **GET /tools/schemas/{tool_name}**
  ```bash
  curl "$BASE_URL$API_PREFIX/tools/schemas/gmail" \
    -H "Authorization: Bearer $TOKEN"
  ```

- **GET /tools/scopes/required** (comma-separated `tools` list)
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
{"detail":"Google authentication failed: Scope has changed from ..."}
```

**This is normal behavior.** Google automatically adds broader scopes when certain scopes (like `drive.file`) are requested. The system now handles these changes gracefully.

**Solution:** The authentication should work automatically now. If it still fails:
1. Try re-authenticating by calling `/api/v1/auth/google/auth` again
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
    "tools": ["gmail", "google_sheets"],
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
  -H "Authorization: Bearer $TOKEN"
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
