# 🔄 Trial Account Migration - Quick Start

## TL;DR

Endpoint baru untuk migrasi akun trial ke Google account tanpa kehilangan agents!

## API Endpoint

```
POST /api/v1/auth/google/migrate-trial
```

**Request:**
```json
{
  "trial_user_id": "uuid-of-trial-user"
}
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "auth_state": "encoded-state",
  "message": "Redirect user to auth_url to complete Google sign-in for migration"
}
```

## Frontend Code (Copy-Paste)

```javascript
// Check if trial account
const isTrial = user.email.startsWith('trial_') && user.email.endsWith('@trial.local');

if (isTrial) {
  // Call migration endpoint
  const response = await fetch('/api/v1/auth/google/migrate-trial', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ trial_user_id: user.id })
  });
  
  const data = await response.json();
  
  // Redirect to Google
  window.location.href = data.auth_url;
}

// Handle callback at /auth/callback
const params = new URLSearchParams(window.location.search);
if (params.get('migrated') === 'true') {
  localStorage.setItem('token', params.get('token'));
  window.location.href = '/dashboard';
}
```

## What Happens?

1. ✅ User ID stays the same
2. ✅ All agents preserved
3. ✅ Email changes to Google email
4. ✅ Password randomized (Google OAuth used)
5. ✅ Account activated

## Test

```bash
# Run test script
./tests/test_trial_migration.sh

# Or manually
curl -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d '{"trial_user_id": "your-uuid-here"}'
```

## Files Changed

- `app/schemas/auth.py` - Added schema
- `app/services/auth_service.py` - Added migration method
- `app/api/v1/auth.py` - Added endpoint & callback logic

## Documentation

📖 Full docs: `/docs/TRIAL_MIGRATION.md`
📊 Flow diagram: `/docs/MIGRATION_FLOW_DIAGRAM.md`
⚛️ React component: `/docs/frontend-examples/GoogleSignInButton.jsx`

## Error Handling

| Code | Meaning |
|------|---------|
| 404 | Trial user not found |
| 400 | Not a trial account |
| 409 | Google email already exists |

---

**Need help?** Check `/docs/TRIAL_MIGRATION.md` for complete documentation.
