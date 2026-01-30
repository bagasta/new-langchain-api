# Trial Account Migration to Google

## Overview

Endpoint ini memungkinkan user dengan akun trial untuk migrasi ke akun Google tanpa kehilangan agent yang sudah dibuat.

## Flow Diagram

```
1. Frontend detects user has trial account (email: trial_*@trial.local)
2. User clicks "Sign in with Google" button
3. Frontend calls POST /api/v1/auth/google/migrate-trial
   - Body: { "trial_user_id": "uuid-here" }
4. Backend validates trial account and returns Google OAuth URL
5. Frontend redirects user to Google OAuth URL
6. User completes Google authentication
7. Google redirects to callback: /api/v1/auth/google/callback
8. Backend detects trial migration flow and calls migrate_trial_to_google()
9. Backend updates:
   - User email → Google email
   - User password → random (Google OAuth used instead)
   - User is_active → true
   - Saves Google OAuth tokens
   - All agents remain intact (no deletion)
10. Backend redirects to frontend with new access token
11. Frontend receives token and user is logged in with Google account
```

## Endpoint Details

### 1. Initiate Trial Migration

**Endpoint:** `POST /api/v1/auth/google/migrate-trial`

**Request Body:**
```json
{
  "trial_user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "auth_state": "base64-encoded-state",
  "message": "Redirect user to auth_url to complete Google sign-in for migration"
}
```

**Error Responses:**
- `404 Not Found` - Trial user tidak ditemukan
- `400 Bad Request` - Akun bukan trial account

### 2. Google OAuth Callback (Automatic)

**Endpoint:** `GET /api/v1/auth/google/callback`

Ini adalah endpoint callback yang otomatis dipanggil oleh Google setelah user menyelesaikan OAuth.

**Query Parameters:**
- `code` - OAuth authorization code dari Google
- `state` - State yang berisi trial_user_id
- `scope` (optional) - Scopes yang diberikan

**Redirect:**
- Success: `{FRONTEND_URL}/auth/callback?token={access_token}&user_id={user_id}&migrated=true`
- Error: `{FRONTEND_URL}/auth/error?message={error_message}`

## Frontend Integration Example

### React/JavaScript Example

```javascript
// Detect if user is on trial account
async function checkIfTrialAccount(user) {
  return user.email.startsWith('trial_') && user.email.endsWith('@trial.local');
}

// Initiate migration
async function migrateToGoogle(trialUserId) {
  try {
    const response = await fetch('/api/v1/auth/google/migrate-trial', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        trial_user_id: trialUserId
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // Redirect to Google OAuth
      window.location.href = data.auth_url;
    } else {
      console.error('Migration failed:', data.detail);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

// Handle callback after Google OAuth
// In your /auth/callback page component:
function AuthCallbackPage() {
  const searchParams = new URLSearchParams(window.location.search);
  const token = searchParams.get('token');
  const userId = searchParams.get('user_id');
  const migrated = searchParams.get('migrated');
  
  if (token && migrated === 'true') {
    // Save token
    localStorage.setItem('access_token', token);
    
    // Show success message
    console.log('Trial account successfully migrated to Google!');
    
    // Redirect to dashboard
    window.location.href = '/dashboard';
  }
}
```

### Vue Example

```vue
<template>
  <div>
    <button 
      v-if="isTrialAccount" 
      @click="signInWithGoogle"
      class="google-signin-btn"
    >
      <img src="/google-icon.svg" alt="Google" />
      Sign in with Google
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useUserStore } from '@/stores/user';

const userStore = useUserStore();

const isTrialAccount = computed(() => {
  return userStore.email?.startsWith('trial_') && 
         userStore.email?.endsWith('@trial.local');
});

async function signInWithGoogle() {
  try {
    const response = await fetch('/api/v1/auth/google/migrate-trial', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        trial_user_id: userStore.id
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      window.location.href = data.auth_url;
    } else {
      alert('Migration failed: ' + data.detail);
    }
  } catch (error) {
    console.error('Error:', error);
    alert('An error occurred during migration');
  }
}
</script>
```

## Important Notes

### Data Preservation
- ✅ **All agents are preserved** - Tidak ada agent yang dihapus
- ✅ **Agent configurations retained** - Semua konfigurasi agent tetap sama
- ✅ **User ID remains the same** - ID user tidak berubah, jadi relasi tetap utuh
- ✅ **API keys updated** - API key tetap valid dengan plan yang sama

### Changed Data
- ❌ Email - Berubah dari `trial_*@trial.local` ke Google email
- ❌ Password - Berubah menjadi random (tidak digunakan, OAuth saja)
- ✅ is_active - Berubah menjadi `true`

### Security
1. Validasi bahwa user yang dimigrasikan memang trial account
2. Validasi bahwa Google email belum digunakan user lain
3. Simpan Google OAuth tokens untuk akses berkelanjutan
4. Generate password random yang kuat (tidak akan digunakan)

### Error Handling
- **404**: Trial user tidak ditemukan
- **400**: Bukan trial account
- **409**: Google email sudah digunakan user lain
- **500**: Server error during migration

## Database Changes

Tidak ada perubahan schema database yang diperlukan. Endpoint ini menggunakan table yang sudah ada:
- `users` - Update email, password_hash, is_active
- `auth_tokens` - Insert/Update Google OAuth tokens
- `agents` - Tidak berubah (tetap terhubung dengan user_id yang sama)
- `api_keys` - Tetap valid

## Testing

### Manual Testing Steps
1. Create trial account via frontend
2. Create some test agents
3. Click "Sign in with Google"
4. Complete Google OAuth
5. Verify:
   - User logged in with Google email
   - All agents still visible
   - Can create new agents
   - Email changed in profile
   - Google OAuth works for future logins

### cURL Examples

```bash
# 1. Initiate migration
curl -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d '{
    "trial_user_id": "550e8400-e29b-41d4-a716-446655440000"
  }'

# Response will contain auth_url - open in browser
```

## Troubleshooting

### User gets "Account already exists" error
- Google email sudah digunakan oleh user lain
- Solution: User harus login dengan akun Google yang berbeda

### Migration fails silently
- Check backend logs untuk detail error
- Pastikan Google OAuth credentials valid
- Verify FRONTEND_URL di .env benar

### Agents disappeared after migration
- Ini seharusnya TIDAK terjadi karena user_id tetap sama
- Check database untuk memastikan agents masih ada
- Verify foreign key constraints tidak cascade delete
