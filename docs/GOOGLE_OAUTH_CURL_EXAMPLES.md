# Google OAuth API - Curl Examples

## Environment Variables Setup

```bash
export BASE_URL="http://localhost:8000"
export API_PREFIX="/api/v1"
export TOKEN="your-api-key-here"
export AGENT_ID="your-agent-uuid-here"
```

---

## Flow 1: Agent OAuth (Google Tools Authentication)

### Use Case
Authenticate Google Workspace tools (Gmail, Calendar, Sheets) for a specific agent.

### Step 1: Initiate Google OAuth for Agent

**Endpoint**: `POST /api/v1/auth/google`

**Method 1: JSON Body (Recommended)**

```bash
curl -X POST "$BASE_URL$API_PREFIX/auth/google" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "scopes": [
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/calendar"
        ],
        "agent_id": "'"$AGENT_ID"'"
      }'
```

**Method 2: Query Parameters**

```bash
curl -X POST "$BASE_URL$API_PREFIX/auth/google?agent_id=$AGENT_ID&scopes=gmail,calendar" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response:**
```json
{
  "auth_required": true,
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&state=...",
  "auth_state": "eyJ1IjoidXNlci11dWlkIiwiYSI6ImFnZW50LXV1aWQiLCJzIjpbLi4uXX0",
  "required_scopes": [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
  ],
  "tokens": []
}
```

### Step 2: User Authorization

Redirect user to `auth_url` from the response above. User will:
1. Sign in to Google (if not already)
2. Grant permissions for requested scopes
3. Get redirected back to your callback URL

### Step 3: Backend Callback (Automatic)

Google redirects to: `GET /api/v1/auth/google/callback?code=...&state=...`

Backend will:
1. Decode state → extract `user_id`, `agent_id`, check `is_migration`
2. Since `is_migration=false` → **SKIP migration check** ✅
3. Save OAuth tokens for the agent
4. Redirect to frontend with success

### Step 4: Verify Token Saved

```bash
# Check if token exists for agent
curl -X GET "$BASE_URL$API_PREFIX/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Flow 2: Migrate Trial/Guest to Google Account

### Use Case
Upgrade a TRIAL or GUEST account to a permanent Google account.

### Step 1: Initiate Migration

**Endpoint**: `POST /api/v1/auth/google/migrate-trial`

```bash
export TRIAL_USER_ID="trial-user-uuid-here"

curl -X POST "$BASE_URL$API_PREFIX/auth/google/migrate-trial" \
  -H "Content-Type: application/json" \
  -d '{
        "trial_user_id": "'"$TRIAL_USER_ID"'"
      }'
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&state=...",
  "auth_state": "eyJ1IjoidHJpYWwtdXVpZCIsIm0iOnRydWV9",
  "message": "Redirect user to auth_url to complete Google sign-in for migration"
}
```

**Note:** State contains `"m": true` marker to indicate migration flow! ⭐

### Step 2: User Authorization

User completes Google OAuth flow.

### Step 3: Backend Callback (Automatic)

Backend will:
1. Decode state → extract `user_id`, check `is_migration=true` ⭐
2. **Check if user is TRIAL/GUEST** (validation happens) ✅
3. Migrate account:
   - Update email to Google email
   - Save OAuth tokens
   - Upgrade GUEST → TRIAL plan
   - Activate account
4. Redirect to frontend with `migrated=true`

### Step 4: User Redirected

Frontend receives:
```
/auth/callback?token=new-access-token&user_id=user-uuid&migrated=true
```

---

## Flow 3: Public Google Login (No Pre-existing Account)

### Use Case
Allow users to sign up/login via Google OAuth (no pre-created account needed).

### Initiate Public Google Login

**Endpoint**: `GET /api/v1/auth/google/login`

```bash
curl -X GET "$BASE_URL$API_PREFIX/auth/google/login?scopes=gmail,calendar"
```

**Response:**
```json
{
  "auth_required": true,
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "auth_state": "eyJzIjpbLi4uXX0",
  "required_scopes": [...],
  "tokens": []
}
```

Backend will:
1. Create new user if email doesn't exist
2. Set `is_active=false` (require plan selection)
3. Redirect to payment page

---

## OAuth State Payload Comparison

### Agent OAuth State
```json
{
  "n": "nonce-uuid",
  "u": "user-uuid",
  "a": "agent-uuid",
  "s": ["gmail.readonly", "calendar"],
  "m": false  // ⭐ NOT a migration (or omitted)
}
```
**Base64 Encoded:** `eyJuIjoibm9uY2UtdXVpZCIsInUiOiJ1c2VyLXV1aWQiLCJhIjoiYWdlbnQtdXVpZCIsInMiOlsiZ21haWwucmVhZG9ubHkiLCJjYWxlbmRhciJdLCJtIjpmYWxzZX0`

### Migration State
```json
{
  "n": "nonce-uuid",
  "u": "trial-user-uuid",
  "s": ["userinfo.email", "userinfo.profile"],
  "m": true  // ⭐ MIGRATION MARKER
}
```
**Base64 Encoded:** `eyJuIjoibm9uY2UtdXVpZCIsInUiOiJ0cmlhbC11c2VyLXV1aWQiLCJzIjpbInVzZXJpbmZvLmVtYWlsIiwidXNlcmluZm8ucHJvZmlsZSJdLCJtIjp0cnVlfQ`

---

## Common Scopes

### Gmail
```json
{
  "scopes": [
    "https://www.googleapis.com/auth/gmail.readonly",     // Read emails
    "https://www.googleapis.com/auth/gmail.send",         // Send emails
    "https://www.googleapis.com/auth/gmail.modify"        // Full access
  ]
}
```

### Google Calendar
```json
{
  "scopes": [
    "https://www.googleapis.com/auth/calendar.readonly",  // Read events
    "https://www.googleapis.com/auth/calendar",           // Full access
    "https://www.googleapis.com/auth/calendar.events"     // Manage events
  ]
}
```

### Google Sheets
```json
{
  "scopes": [
    "https://www.googleapis.com/auth/spreadsheets.readonly",  // Read only
    "https://www.googleapis.com/auth/spreadsheets"            // Full access
  ]
}
```

### Combined Example
```bash
curl -X POST "$BASE_URL$API_PREFIX/auth/google" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "scopes": [
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.send",
          "https://www.googleapis.com/auth/calendar",
          "https://www.googleapis.com/auth/spreadsheets"
        ],
        "agent_id": "'"$AGENT_ID"'"
      }'
```

---

## Error Handling

### Error: Invalid API Key
```json
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "The provided API key is invalid or expired",
    "timestamp": "2026-02-02T13:47:55Z"
  }
}
```

### Error: Agent Not Found
```json
{
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent with ID 'xxx' not found",
    "timestamp": "2026-02-02T13:47:55Z"
  }
}
```

### Error: Not a Trial Account (Migration Flow Only)
```json
{
  "error": {
    "code": "INVALID_TRIAL_ACCOUNT",
    "message": "This account is not a trial/guest account",
    "timestamp": "2026-02-02T13:47:55Z"
  }
}
```
**When:** Only happens if you call `/migrate-trial` with a PRO user

---

## Complete Example: Agent with Gmail

```bash
#!/bin/bash

# 1. Set environment variables
export BASE_URL="http://localhost:8000"
export API_PREFIX="/api/v1"
export TOKEN="sk_live_your_api_key_here"

# 2. Create agent
AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL$API_PREFIX/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Email Assistant",
        "tools": ["gmail"],
        "config": {
          "llm_model": "gpt-4o-mini",
          "temperature": 0.7,
          "system_prompt": "You are a helpful email assistant"
        }
      }')

AGENT_ID=$(echo $AGENT_RESPONSE | jq -r '.id')
echo "Created agent: $AGENT_ID"

# 3. Initiate Google OAuth for agent
AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL$API_PREFIX/auth/google" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "scopes": [
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.send"
        ],
        "agent_id": "'"$AGENT_ID"'"
      }')

AUTH_URL=$(echo $AUTH_RESPONSE | jq -r '.auth_url')
echo "Auth URL: $AUTH_URL"
echo ""
echo "👉 Open this URL in browser to authorize Google access"
echo "   After authorization, backend will save tokens automatically"
echo ""

# 4. After user completes OAuth, execute agent
# (Wait for user to complete OAuth flow first)
read -p "Press Enter after completing OAuth authorization..."

# 5. Execute agent
curl -X POST "$BASE_URL$API_PREFIX/agents/$AGENT_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "input": "Read my latest 5 emails and summarize them",
        "session_id": "email-session-1"
      }' | jq
```

---

## Summary

### ✅ What Works Now (After Bug Fix)

| User Type | Agent OAuth | Migration |
|-----------|-------------|-----------|
| GUEST | ✅ Works | ✅ Works |
| TRIAL | ✅ Works | ✅ Works |
| PRO_M | ✅ Works | ❌ Not allowed |

### 🔑 Key Differences

| Aspect | Agent OAuth | Migration |
|--------|-------------|-----------|
| **Endpoint** | `POST /auth/google` | `POST /auth/google/migrate-trial` |
| **State Marker** | `"m": false` or omitted | `"m": true` |
| **Callback Behavior** | Save tokens only | Check trial → Migrate account |
| **Result** | OAuth tokens saved | Account upgraded |

---

**Documentation Version:** 2.0  
**Last Updated:** 2026-02-02  
**Related:** BUGFIX_OAUTH_FLOW.md, OAuth_FLOW_DIAGRAM.md
