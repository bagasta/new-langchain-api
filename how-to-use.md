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

1. **Register User Account**: Create a user account without generating an API key
2. **Generate API Key**: Request an API key with specific plan and expiration

### Example Flow

```bash
# Step 1: Register user
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
TOKEN=$(echo $API_KEY_RESPONSE | jq -r '.access_token')
EXPIRES_AT=$(echo $API_KEY_RESPONSE | jq -r '.expires_at')
echo "Generated API key expires at: $EXPIRES_AT"

# Use the token for authenticated requests
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL$API_PREFIX/auth/me"
```

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
  Returns user information without API key. Use the API key generation endpoint to get access tokens.

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

- **POST /google/auth**
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/auth/google/auth" \
    -H "Authorization: Bearer $TOKEN"
  ```
  This endpoint initiates Google OAuth authentication. It no longer requires a request body.

  **Note:** The system automatically handles scope changes from Google. When requesting `drive.file` scope, Google may add broader Drive scopes (`drive`, `drive.photos.readonly`, `drive.appdata`) which are accepted as long as all requested scopes are granted.

- **GET /google/auth**
  ```bash
  curl -X GET "$BASE_URL$API_PREFIX/auth/google/auth" \
    -H "Authorization: Bearer $TOKEN"
  ```
  GET method also available for clickable links.

- **GET /google/callback**
  ```bash
  curl "$BASE_URL$API_PREFIX/auth/google/callback?code=auth-code-from-google&state=state-token"
  ```
  Handles the OAuth callback from Google. The authorization token is not required for this endpoint.

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

## Agent Routes (`$API_PREFIX/agents`)

- **POST /** create agent
  ```bash
  curl -X POST "$BASE_URL$API_PREFIX/agents/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "Research Assistant",
          "tools": ["tool-id-1"],
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
