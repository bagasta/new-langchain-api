# API Response Examples

## 1. Initiate Migration (Success)

**Request:**
```http
POST /api/v1/auth/google/migrate-trial HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "trial_user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (200 OK):**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback&scope=openid+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.profile&state=eyJuIjoiYWJjZGVmIiwicyI6WyJvcGVuaWQiXSwidSI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCJ9&access_type=offline&prompt=consent",
  "auth_state": "eyJuIjoiYWJjZGVmIiwicyI6WyJvcGVuaWQiXSwidSI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCJ9",
  "message": "Redirect user to auth_url to complete Google sign-in for migration"
}
```

## 2. Initiate Migration (Trial Not Found)

**Request:**
```http
POST /api/v1/auth/google/migrate-trial HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "trial_user_id": "00000000-0000-0000-0000-000000000000"
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Trial user not found"
}
```

## 3. Initiate Migration (Not a Trial Account)

**Request:**
```http
POST /api/v1/auth/google/migrate-trial HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "trial_user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "This account is not a trial account"
}
```

## 4. Google OAuth Callback (Success - Migration)

**Request:**
```http
GET /api/v1/auth/google/callback?code=4/0AX4XfWh...&state=eyJuIjoiYWJj... HTTP/1.1
Host: localhost:8000
```

**Response (302 Redirect):**
```http
HTTP/1.1 302 Found
Location: https://your-frontend.com/auth/callback?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...&user_id=550e8400-e29b-41d4-a716-446655440000&migrated=true
```

## 5. Migration Service Method Response

When `migrate_trial_to_google()` is called internally:

```python
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@gmail.com",
  "access_token": "sk_live_abcd1234efgh5678",
  "token_type": "bearer",
  "expires_at": "2026-02-13T10:47:37.123456",
  "plan_code": "TRIAL",
  "message": "Trial account successfully migrated to Google account. All agents have been preserved."
}
```

## 6. Migration Error: Email Already Exists

During callback, if Google email already used:

**Internal Error Response:**
```json
{
  "detail": "An account with this Google email already exists"
}
```

**Browser Redirect:**
```http
HTTP/1.1 302 Found
Location: https://your-frontend.com/auth/error?message=An+account+with+this+Google+email+already+exists
```

## 7. Get User Info After Migration

**Request:**
```http
GET /api/v1/auth/me HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (Before Migration):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "trial_abc123def456@trial.local",
  "is_active": true,
  "created_at": "2026-01-30T03:47:37.123456",
  "api_expires_at": "2026-02-13T03:47:37.123456",
  "access_token": "sk_trial_xyz789",
  "plan_code": "TRIAL",
  "agent_slots": {
    "total_slots": null,
    "used_slots": 3,
    "available_slots": null,
    "is_unlimited": true
  }
}
```

**Response (After Migration):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@gmail.com",  // ← Changed
  "is_active": true,
  "created_at": "2026-01-30T03:47:37.123456",
  "api_expires_at": "2026-02-13T03:47:37.123456",
  "access_token": "sk_live_new123",
  "plan_code": "TRIAL",
  "agent_slots": {
    "total_slots": null,
    "used_slots": 3,  // ← Same! Agents preserved
    "available_slots": null,
    "is_unlimited": true
  }
}
```

## 8. Frontend Auth Callback Handler

JavaScript example to handle the redirect:

```javascript
// In /auth/callback page
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');
const userId = urlParams.get('user_id');
const migrated = urlParams.get('migrated');

if (token && migrated === 'true') {
  // Migration successful!
  localStorage.setItem('access_token', token);
  localStorage.setItem('user_id', userId);
  
  // Show success notification
  showNotification('success', '✅ Account migrated successfully! Welcome!');
  
  // Fetch updated user info
  const response = await fetch('/api/v1/auth/me', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const userData = await response.json();
  console.log('Migrated user:', userData);
  
  // Redirect to dashboard
  setTimeout(() => {
    window.location.href = '/dashboard';
  }, 2000);
}
```

## State Parameter Structure

The `state` parameter in OAuth URL contains base64-encoded JSON:

**Decoded:**
```json
{
  "n": "abc123def456",  // Nonce for security
  "s": [                 // Requested scopes
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
  ],
  "u": "550e8400-e29b-41d4-a716-446655440000"  // Trial user ID
}
```

**Encoded (in URL):**
```
eyJuIjoiYWJjMTIzZGVmNDU2IiwicyI6WyJvcGVuaWQiLCJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9hdXRoL3VzZXJpbmZvLmVtYWlsIiwiaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vYXV0aC91c2VyaW5mby5wcm9maWxlIl0sInUiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAifQ
```

This state is validated in the callback to ensure it's the same request.
