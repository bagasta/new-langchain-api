# Google Sign-In API Integration Guide

Dokumentasi untuk integrasi Google Sign-In dengan frontend application.

## Base URL
```
Development: http://localhost:8000
Production: https://new-langchain.chiefaiofficer.id
```

---

## Authentication Flow

### Overview
1. Frontend request URL Google OAuth dari backend
2. Frontend redirect user ke URL Google OAuth (atau popup)
3. User login di Google dan approve permissions
4. Google redirect ke backend callback URL
5. Backend create/login user dan return JWT token
6. Frontend simpan JWT token untuk authenticated requests

---

## API Endpoints

### 1. Initiate Google Sign-In

**Endpoint:** `GET /api/v1/auth/google/login`

**Description:** Get Google OAuth URL untuk memulai proses login

**Authentication:** None (Public endpoint)

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/auth/google/login"
```

**Response:**
```json
{
  "auth_required": true,
  "auth_url": "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=...",
  "auth_state": "eyJuIjogIjU4OGRkMjYxLTgzODQtNDc4Ny...",
  "required_scopes": [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
  ],
  "tokens": []
}
```

**Usage di Frontend:**
```javascript
// React/Vue/Angular example
async function initiateGoogleLogin() {
  const response = await fetch('/api/v1/auth/google/login');
  const data = await response.json();
  
  // Option 1: Redirect (full page)
  window.location.href = data.auth_url;
  
  // Option 2: Popup (recommended)
  const width = 500;
  const height = 600;
  const left = window.screen.width / 2 - width / 2;
  const top = window.screen.height / 2 - height / 2;
  
  window.open(
    data.auth_url,
    'googleSignIn',
    `width=${width},height=${height},left=${left},top=${top}`
  );
}
```

---

### 2. Google OAuth Callback
**Endpoint:** `GET /api/v1/auth/google/callback`

**Description:** Endpoint yang dipanggil Google setelah user authorize. Backend akan:
1.  Membuat user baru (jika belum ada) atau login user lama.
2.  **Set User Inactive** (jika user baru).
3.  **Redirect ke Frontend Payment Page** dengan temporary token.

**Authentication:** None (Called by Google)

**Query Parameters:**
- `code` (required): Authorization code dari Google
- `state` (required): State parameter untuk security
- `scope` (optional): Granted scopes

**Response (Redirect):**
Backend akan melakukan redirect ke frontend URL:
`{FRONTEND_URL}/payment?token={temp_token}&email={user_email}&user_id={user_id}`

**Flow Selanjutnya (Frontend):**
1.  Frontend menerima redirect di halaman `/payment`.
2.  Frontend mengambil `token` dari URL query params.
3.  User memilih plan (e.g., TRIAL, PRO_M, PRO_Y).
4.  Frontend memanggil endpoint aktivasi:

**Endpoint:** `POST /api/v1/auth/google/activate-plan`

**Request:**
```json
{
  "plan_code": "TRIAL"
}
```
**Header:** `Authorization: Bearer {temp_token}`

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_at": "2024-02-15T10:30:00",
  "plan_code": "TRIAL",
  "user_id": "..."
}
```
Token yang dikembalikan ini adalah **API Key** final yang bisa digunakan untuk request selanjutnya.

---

### 3. Traditional Login (Existing)

**Endpoint:** `POST /api/v1/auth/login`

**Description:** Login dengan email/phone dan password

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login?email=user@example.com&password=mypassword"
```

**Response:**
```json
{
  "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### 4. Register (Existing)

**Endpoint:** `POST /api/v1/auth/register`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register?email=newuser@example.com&password=securepass123"
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "newuser@example.com"
}
```

---

### 5. Get Current User Info

**Endpoint:** `GET /api/v1/auth/me`

**Authentication:** Required (Bearer token)

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "plan_code": "PRO_M"
}
```

---

## Implementation Strategies

### Strategy 1: Frontend Callback Handler (Recommended)

1. Backend redirect ke frontend URL dengan token di query params:

**Update backend callback untuk redirect:**
```python
# In app/api/v1/auth.py process_google_callback
# After successful auth, redirect to frontend:
return RedirectResponse(
    url=f"{frontend_url}/auth/callback?token={jwt_token}"
)
```

**Frontend handler:**
```javascript
// Route: /auth/callback
function handleGoogleCallback() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  
  if (token) {
    // Save token
    localStorage.setItem('jwt_token', token);
    
    // Redirect to dashboard
    window.location.href = '/dashboard';
  }
}
```

### Strategy 2: PostMessage (Untuk Popup)

**Frontend popup listener:**
```javascript
// Listen for message from popup
window.addEventListener('message', (event) => {
  if (event.origin !== 'http://localhost:8000') return;
  
  if (event.data.type === 'oauth_success' && event.data.token) {
    localStorage.setItem('jwt_token', event.data.token);
    window.location.href = '/dashboard';
  }
});
```

---

## Complete Frontend Example

### React Component
```jsx
import React, { useState } from 'react';

function GoogleSignIn() {
  const [loading, setLoading] = useState(false);

  const handleGoogleLogin = async () => {
    setLoading(true);
    
    try {
      // Get Google OAuth URL
      const response = await fetch('/api/v1/auth/google/login');
      const data = await response.json();
      
      // Redirect to Google (full page redirect)
      window.location.href = data.auth_url;
      
      // Or use popup (if you have callback handler)
      // openPopup(data.auth_url);
      
    } catch (error) {
      console.error('Google login failed:', error);
      setLoading(false);
    }
  };

  return (
    <button 
      onClick={handleGoogleLogin}
      disabled={loading}
    >
      {loading ? 'Loading...' : 'Sign in with Google'}
    </button>
  );
}
```

### Vanilla JavaScript
```javascript
async function googleLogin() {
  try {
    const response = await fetch('http://localhost:8000/api/v1/auth/google/login');
    const data = await response.json();
    
    // Redirect to Google
    window.location.href = data.auth_url;
    
  } catch (error) {
    console.error('Error:', error);
  }
}

// Add to your login button
document.getElementById('google-login-btn')
  .addEventListener('click', googleLogin);
```

---

## Environment Variables

Backend memerlukan environment variables ini di `.env`:

```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# For production:
# GOOGLE_REDIRECT_URI=https://new-langchain.chiefaiofficer.id/api/v1/auth/google/callback
```

---

## Testing dengan CURL

### Complete Flow Test

```bash
# Step 1: Get Google OAuth URL
curl -X GET "http://localhost:8000/api/v1/auth/google/login" \
  -H "Content-Type: application/json"

# Copy auth_url dari response dan buka di browser
# Setelah authorize, Google akan redirect ke callback URL

# Step 2: Test dengan existing user (traditional login)
curl -X POST "http://localhost:8000/api/v1/auth/login?email=test@example.com&password=testpass"

# Step 3: Use JWT token
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Error Handling

### Common Errors

**401 Unauthorized**
```json
{
  "detail": "Could not validate credentials"
}
```
**Solution:** Token expired atau invalid. Request new token via login.

**403 Forbidden**
```json
{
  "detail": "Inactive user"
}
```
**Solution:** User account tidak active.

**500 Internal Server Error**
```json
{
  "detail": "Google authentication failed: ..."
}
```
**Solution:** Check Google credentials di backend .env file.

---

## Security Best Practices

1. **HTTPS in Production:** Always use HTTPS untuk production
2. **Token Storage:** 
   - Use `httpOnly` cookies (paling aman)
   - Atau localStorage dengan XSS protection
3. **CORS Configuration:** Pastikan backend CORS configured untuk frontend domain
4. **Token Expiration:** JWT token expire dalam 30 hari (configurable)
5. **State Parameter:** Backend automatically generate state untuk prevent CSRF

---

## CORS Configuration

Jika frontend berjalan di domain berbeda, tambahkan domain ke `app/core/config.py`:

```python
BACKEND_CORS_ORIGINS: List[str] = [
    "http://localhost:3000",      # React dev server
    "http://localhost:5173",      # Vite dev server
    "https://yourfrontend.com",   # Production
]
```

---

## Support

Untuk pertanyaan atau issues, contact backend team atau check:
- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`
