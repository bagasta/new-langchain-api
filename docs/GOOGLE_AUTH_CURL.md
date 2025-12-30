# Google Sign-In - Quick CURL Reference

## 🚀 Quick Start

### 1. Get Google Login URL
```bash
curl -X GET "http://localhost:8000/api/v1/auth/google/login"
```

**Response:**
```json
{
  "auth_required": true,
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "auth_state": "eyJuIjogIjU4OGRkMjYxLT...",
  "required_scopes": [...],
  "tokens": []
}
```

**Frontend Usage:**
```javascript
// Get the URL
const res = await fetch('/api/v1/auth/google/login');
const data = await res.json();

// Redirect user to Google
window.location.href = data.auth_url;
```

---

### 2. After Google Redirects Back

Google will automatically redirect to:
```
http://localhost:8000/api/v1/auth/google/callback?code=...&state=...
```

Backend will:
- ✅ Verify the code
- ✅ Get user info from Google
- ✅ Create user if doesn't exist
- ✅ **Return JWT Token** (Save this!)

**Response from Callback:**
```json
{
  "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "...",
  "plan_code": "TRIAL"
}
```

---

### 3. Traditional Login (for testing)
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

### 4. Get User Info (with token)
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00"
}
```

---

## 📝 Complete Flow Example

```bash
# 1. Get Google OAuth URL
RESPONSE=$(curl -s "http://localhost:8000/api/v1/auth/google/login")
AUTH_URL=$(echo $RESPONSE | jq -r '.auth_url')

# 2. Print URL (copy and open in browser)
echo "Open this URL in browser:"
echo $AUTH_URL

# After completing Google login, Google redirects to callback
# Backend processes it automatically and creates the user

# 3. Login with email (to get JWT token)
curl -X POST "http://localhost:8000/api/v1/auth/login?email=your-google-email@gmail.com&password=auto-generated"

# Note: If registered via Google, you need to set password first
# or use the callback strategy to get JWT directly
```

---

## 🎯 Testing Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### API Docs
Open in browser:
```
http://localhost:8000/docs
```

### Register New User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register?email=test@example.com&password=testpass123"
```

---

## 🔑 What Frontend Needs

1. **Button Click Handler:**
```javascript
async function handleGoogleLogin() {
  const response = await fetch('/api/v1/auth/google/login');
  const data = await response.json();
  window.location.href = data.auth_url;
}
```

2. **Callback Handler (if using custom redirect):**
```javascript
// Parse token from URL after callback
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');
if (token) {
  localStorage.setItem('jwt_token', token);
}
```

3. **Authenticated Requests:**
```javascript
const token = localStorage.getItem('jwt_token');
fetch('/api/v1/auth/me', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

---

## 📌 Important Notes

- ✅ No HTML/UI needed from backend - pure API
- ✅ Frontend handles all UI and redirects
- ✅ Backend only provides OAuth URLs and processes callbacks
- ✅ Auto-creates users on first Google login
- ✅ Existing login/register still works
