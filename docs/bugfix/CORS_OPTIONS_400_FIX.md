# CORS OPTIONS 400 Error - Troubleshooting Guide

## Issue Description

**Error in logs:**
```
INFO: 222.124.56.193:0 - "OPTIONS /api/v1/auth/me HTTP/1.1" 400 Bad Request
INFO: 222.124.56.193:0 - "OPTIONS /api/v1/agents/ HTTP/1.1" 400 Bad Request
```

**What is OPTIONS request?**
OPTIONS is a "preflight" HTTP request sent by browsers **before** the actual request to check CORS permissions. This is part of CORS security.

---

## Root Cause

### Problem 1: Typo in `.env` File ❌
**Line 41 had missing newline:**
```bash
FRONTEND_URL=https://unlevelled-ariah-zoochemical.ngrok-free.devDB_HOST=194.238.23.242
```

This caused:
- `FRONTEND_URL` value to include `DB_HOST`
- Malformed environment variable parsing
- Potential CORS config issues

### Problem 2: Mismatched CORS Origins ❌
**Configured origins:**
```bash
BACKEND_CORS_ORIGINS=["https://uninterjected-rife-wilburn.ngrok-free.dev"]
FRONTEND_URL=https://unlevelled-ariah-zoochemical.ngrok-free.dev
```

**Actual requests from:**
```
https://b75650b1396e.ngrok-free.app
```

**Result:** Browser's preflight OPTIONS requests were **rejected** because origin not in allowed list.

---

## Solution

### Fix 1: Corrected `.env` Typo ✅

**Before:**
```bash
FRONTEND_URL=https://unlevelled-ariah-zoochemical.ngrok-free.devDB_HOST=194.238.23.242
```

**After:**
```bash
FRONTEND_URL=https://b75650b1396e.ngrok-free.app
DB_HOST=194.238.23.242
```

### Fix 2: Updated CORS Origins ✅

**Before:**
```bash
BACKEND_CORS_ORIGINS=["https://uninterjected-rife-wilburn.ngrok-free.dev"]
```

**After:**
```bash
BACKEND_CORS_ORIGINS=["https://b75650b1396e.ngrok-free.app"]
```

---

## How CORS Works

### Normal Flow (✅ Success)

```
Browser (https://allowed-origin.com)
  │
  ├─ 1. Send OPTIONS preflight
  │    Origin: https://allowed-origin.com
  │
  ▼
Backend CORS Middleware
  │
  ├─ Check: Is origin allowed? ✅ YES
  ├─ Return: 204 No Content
  │    Access-Control-Allow-Origin: https://allowed-origin.com
  │    Access-Control-Allow-Methods: GET, POST, OPTIONS, ...
  │
  ▼
Browser receives 204 → Proceeds with actual request
  │
  ├─ 2. Send actual POST/GET request
  │
  ▼
Backend processes request ✅
```

### Error Flow (❌ 400/403)

```
Browser (https://unknown-origin.com)
  │
  ├─ 1. Send OPTIONS preflight
  │    Origin: https://unknown-origin.com
  │
  ▼
Backend CORS Middleware
  │
  ├─ Check: Is origin allowed? ❌ NO
  ├─ Return: 400 Bad Request or 403 Forbidden
  │
  ▼
Browser receives error → BLOCKS actual request ❌
  │
  └─ Console Error: "CORS policy: No 'Access-Control-Allow-Origin' header"
```

---

## How to Identify CORS Issues

### 1. Check Browser Console
```javascript
Access to fetch at 'https://api.example.com/api/v1/auth/me' 
from origin 'https://frontend.com' has been blocked by CORS policy: 
Response to preflight request doesn't pass access control check: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

### 2. Check Network Tab
- Look for **OPTIONS** requests with status **400** or **403**
- Actual GET/POST requests will be **cancelled** or **blocked**

### 3. Check Backend Logs
```
INFO: "OPTIONS /api/v1/auth/me HTTP/1.1" 400 Bad Request
```

---

## Testing CORS Configuration

### Test 1: Verify OPTIONS Request (Local)
```bash
curl -X OPTIONS http://localhost:8000/api/v1/auth/me \
  -H "Origin: https://b75650b1396e.ngrok-free.app" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization" \
  -v
```

**Expected:**
```
< HTTP/1.1 204 No Content
< access-control-allow-origin: https://b75650b1396e.ngrok-free.app
< access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS
< access-control-allow-headers: authorization
< access-control-allow-credentials: true
```

### Test 2: Verify OPTIONS Request (ngrok)
```bash
curl -X OPTIONS https://your-ngrok-url.ngrok-free.app/api/v1/auth/me \
  -H "Origin: https://b75650b1396e.ngrok-free.app" \
  -H "Access-Control-Request-Method: GET" \
  -v
```

### Test 3: Check Actual Endpoint
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer your-token" \
  -H "Origin: https://b75650b1396e.ngrok-free.app" \
  -v
```

---

## Common CORS Misconfigurations

### Issue 1: Using `allow_origins=["*"]` with `allow_credentials=True` ❌
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ Can't use with credentials
    allow_credentials=True,  # ❌ Conflict!
)
```

**Error:** "Credential is not supported if the CORS header 'Access-Control-Allow-Origin' is '*'"

**Fix:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://frontend.com"],  # ✅ Specific origins
    allow_credentials=True,  # ✅ OK now
)
```

### Issue 2: Trailing Slashes Mismatch ❌
```python
# .env
FRONTEND_URL=https://frontend.com/

# CORS config
allow_origins=["https://frontend.com"]  # No trailing slash
```

**Result:** `https://frontend.com/` ≠ `https://frontend.com` → CORS blocked

**Fix:** Normalize URLs (remove trailing slashes):
```python
frontend_url = settings.FRONTEND_URL.rstrip("/")
```

### Issue 3: Protocol Mismatch ❌
```python
# Frontend
https://frontend.com

# CORS allowed
http://frontend.com  # ❌ Wrong protocol
```

**Fix:** Use exact protocol:
```python
allow_origins=["https://frontend.com"]  # ✅ Match protocol
```

---

## Updated `.env` Configuration

```bash
# API Settings
SECRET_KEY=your-secret-key-here
API_V1_STR=/api/v1
PROJECT_NAME=LangChain Agent API

# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# Redis
REDIS_URL=redis://localhost:6379/0

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-backend-url.com/api/v1/auth/google/callback

# OpenAI
OPENAI_API_KEY='sk-proj-your-openai-api-key'

# CORS - IMPORTANT: Match your frontend URL exactly!
BACKEND_CORS_ORIGINS=["https://your-frontend-url.com"]

# Logging
LOG_LEVEL=INFO

# Performance
MAX_CONCURRENT_AGENTS=10000
AGENT_EXECUTION_TIMEOUT=300

# MCP defaults
MCP_HTTP_URL=
MCP_HTTP_TOKEN=
MCP_HTTP_ALLOWED_TOOLS=[]
MCP_SSE_URL=
MCP_SSE_TOKEN=
MCP_SSE_ALLOWED_TOOLS=["web_search"]

# Frontend URL - Must match BACKEND_CORS_ORIGINS
FRONTEND_URL=https://your-frontend-url.com

# Database credentials (used by Docker/scripts)
DB_HOST=your-db-host
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_NAME=your-db-name
DB_PORT=5432

# Deployment
TRAEFIK_NETWORK=proxy
DOMAIN=your-domain.com
```

---

## CORS Middleware Configuration (`app/main.py`)

```python
# Build allowed origins list
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:5173",
]

# Add configured FRONTEND_URL
if settings.FRONTEND_URL:
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    if frontend_url not in origins:
        origins.append(frontend_url)

# Add other configured origins
for origin in settings.BACKEND_CORS_ORIGINS:
    origin_stripped = origin.rstrip("/")
    if origin_stripped not in origins:
        origins.append(origin_stripped)

# Apply CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # ✅ Specific origins
    allow_credentials=True,  # ✅ Allow cookies/auth
    allow_methods=["*"],     # ✅ All methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],     # ✅ All headers (Authorization, Content-Type, etc.)
)
```

---

## Verification Steps

### 1. Check Server Logs on Startup
```
INFO: CORS Settings, frontend_url=https://b75650b1396e.ngrok-free.app, 
      allowed_origins=['http://localhost:3000', 'http://localhost:8000', 
                       'http://localhost:5173', 'https://b75650b1396e.ngrok-free.app']
```

### 2. Test OPTIONS Request
```bash
curl -X OPTIONS http://localhost:8000/api/v1/auth/me -v
```

**Expected:** `HTTP/1.1 204 No Content` ✅

### 3. Test from Browser
Open browser console and check:
```javascript
fetch('http://localhost:8000/api/v1/auth/me', {
  headers: { 'Authorization': 'Bearer token' }
})
```

**Expected:** No CORS errors ✅

---

## Quick Troubleshooting Checklist

- [ ] **Check `.env` for typos** (missing newlines, quotes, etc.)
- [ ] **Verify FRONTEND_URL matches actual frontend origin**
- [ ] **Verify BACKEND_CORS_ORIGINS includes frontend**
- [ ] **Check protocol (http vs https)**
- [ ] **Remove trailing slashes from URLs**
- [ ] **Restart server after `.env` changes**
- [ ] **Clear browser cache if needed**
- [ ] **Test OPTIONS request with curl**

---

## Related Issues

This CORS issue is **SEPARATE** from the OAuth bug fix. The OAuth fix was for:
- ❌ Migration flow incorrectly triggered for agent OAuth
- ✅ Fixed with migration marker in state

This CORS issue is for:
- ❌ Frontend origin not allowed in CORS
- ✅ Fixed by updating .env URLs

---

**Status:** ✅ FIXED  
**Date:** 2026-02-02  
**Impact:** High (blocked all frontend API calls)  
**Solution:** Updated `.env` CORS and FRONTEND_URL  
**Related:** BUGFIX_OAUTH_FLOW.md
