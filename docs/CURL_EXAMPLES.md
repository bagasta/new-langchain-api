# cURL Examples - Trial Account Migration

## Quick Testing Commands

### 1️⃣ Create Trial Account (First)

```bash
curl -X POST http://localhost:8000/api/v1/auth/api-key/trial \
  -H "Content-Type: application/json" \
  -d '{
    "ip_user": "192.168.1.100"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_at": "2026-02-13T04:16:50.000000",
  "plan_code": "TRIAL",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

📝 **Save the `user_id` for next step!**

---

### 2️⃣ Initiate Trial Migration

```bash
# Replace USER_ID_HERE with the user_id from step 1
curl -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d '{
    "trial_user_id": "USER_ID_HERE"
  }'
```

**Example with actual UUID:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d '{
    "trial_user_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=...",
  "auth_state": "eyJuIjoiYWJjZGVmIiwicyI6...",
  "message": "Redirect user to auth_url to complete Google sign-in for migration"
}
```

🌐 **Copy the `auth_url` and open it in browser to complete OAuth!**

---

### 3️⃣ Check User Info (Before Migration)

```bash
# Replace TOKEN_HERE with access_token from step 1
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer TOKEN_HERE"
```

**Example:**
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (Before Migration):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "trial_abc123@trial.local",
  "is_active": true,
  "plan_code": "TRIAL"
}
```

---

### 4️⃣ Check User Info (After Migration)

After completing Google OAuth in browser, you'll get redirected with a new token.
Use that new token:

```bash
# Replace NEW_TOKEN with token from redirect URL
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer NEW_TOKEN"
```

**Response (After Migration):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@gmail.com",
  "is_active": true,
  "plan_code": "TRIAL"
}
```

✅ **Email changed, but user_id stays the same!**

---

## Complete Test Flow (Copy & Paste)

```bash
#!/bin/bash

echo "🚀 Starting Trial Migration Test..."

# Step 1: Create trial account
echo -e "\n📝 Step 1: Creating trial account..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/api-key/trial \
  -H "Content-Type: application/json" \
  -d '{"ip_user": "192.168.1.100"}')

echo "$RESPONSE" | jq '.'

USER_ID=$(echo "$RESPONSE" | jq -r '.user_id')
TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')

echo -e "\n✅ Trial account created!"
echo "User ID: $USER_ID"
echo "Token: ${TOKEN:0:20}..."

# Step 2: Check user info before migration
echo -e "\n📝 Step 2: Checking user info..."
curl -s -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Step 3: Initiate migration
echo -e "\n📝 Step 3: Initiating migration..."
MIGRATE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d "{\"trial_user_id\": \"$USER_ID\"}")

echo "$MIGRATE_RESPONSE" | jq '.'

AUTH_URL=$(echo "$MIGRATE_RESPONSE" | jq -r '.auth_url')

echo -e "\n✅ Migration initiated!"
echo -e "\n🌐 Open this URL in browser to complete Google OAuth:"
echo "$AUTH_URL"

echo -e "\n⏸️  Waiting for you to complete Google OAuth..."
echo "After OAuth, you'll be redirected with a new token."
echo "Use that token with: curl -X GET http://localhost:8000/api/v1/auth/me -H \"Authorization: Bearer NEW_TOKEN\""
```

**Save as `test_migration.sh` and run:**
```bash
chmod +x test_migration.sh
./test_migration.sh
```

---

## Testing Error Cases

### ❌ Non-existent User

```bash
curl -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d '{
    "trial_user_id": "00000000-0000-0000-0000-000000000000"
  }'
```

**Expected Response (404):**
```json
{
  "detail": "Trial user not found"
}
```

---

### ❌ Non-Trial Account

First create a regular user:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register?email=regular@example.com&password=test123"
```

Then try to migrate (will fail):
```bash
# Use the regular user's ID
curl -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d '{
    "trial_user_id": "REGULAR_USER_ID"
  }'
```

**Expected Response (400):**
```json
{
  "detail": "This account is not a trial account"
}
```

---

## Production URLs

For production, replace `localhost:8000` with your domain:

```bash
# Production example
curl -X POST https://api.yourdomain.com/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d '{
    "trial_user_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

---

## Using Environment Variables

For easier testing:

```bash
# Set variables
export API_URL="http://localhost:8000"
export TRIAL_USER_ID="550e8400-e29b-41d4-a716-446655440000"

# Use in curl
curl -X POST $API_URL/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d "{\"trial_user_id\": \"$TRIAL_USER_ID\"}"
```

---

## Pretty Print with jq

Install jq: `sudo apt install jq`

```bash
curl -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d '{"trial_user_id": "550e8400-e29b-41d4-a716-446655440000"}' \
  | jq '.'
```

---

## Save Response to File

```bash
curl -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d '{"trial_user_id": "550e8400-e29b-41d4-a716-446655440000"}' \
  -o migration_response.json

cat migration_response.json | jq '.'
```

---

## Debug Mode (-v)

To see full request/response headers:

```bash
curl -v -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d '{
    "trial_user_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```
