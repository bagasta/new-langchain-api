```mermaid
sequenceDiagram
    participant F as Frontend
    participant API as Backend API
    participant DB as Database
    participant G as Google OAuth

    Note over F: User dengan akun trial<br/>clicks "Sign in with Google"
    
    F->>API: POST /auth/google/migrate-trial<br/>{trial_user_id: "uuid"}
    
    API->>DB: Query user by ID
    DB-->>API: Return user data
    
    API->>API: Validate trial account<br/>(email: trial_*@trial.local)
    
    API->>API: Generate Google OAuth URL<br/>with trial_user_id in state
    
    API-->>F: {auth_url, auth_state}
    
    F->>G: Redirect to Google OAuth URL
    
    Note over G: User authenticates<br/>with Google account
    
    G->>API: Redirect to /auth/google/callback<br/>with code & state
    
    API->>G: Exchange code for tokens
    G-->>API: {access_token, refresh_token, email}
    
    API->>API: Decode state → extract trial_user_id
    
    API->>DB: Query user by ID
    DB-->>API: Return trial user
    
    API->>API: Detect trial migration<br/>(email starts with "trial_")
    
    API->>DB: Check if Google email exists
    DB-->>API: No duplicate found
    
    API->>DB: UPDATE users SET<br/>email = Google email,<br/>password_hash = random,<br/>is_active = true<br/>WHERE id = trial_user_id
    
    API->>DB: INSERT auth_tokens<br/>(Google OAuth tokens)
    
    API->>DB: SELECT/UPDATE api_keys
    
    DB-->>API: Migration complete
    
    API->>API: Generate new access token
    
    API-->>F: Redirect to /auth/callback?<br/>token=xxx&user_id=xxx&migrated=true
    
    Note over F: Save token,<br/>show success message,<br/>redirect to dashboard
    
    F->>API: GET /auth/me<br/>Authorization: Bearer {token}
    
    API->>DB: Query user & agents
    DB-->>API: User data + all agents
    
    API-->>F: {user, agents}
    
    Note over F: Display dashboard<br/>with all preserved agents!
```

## Key Points

### 🔑 State Flow
The `state` parameter in OAuth contains:
```json
{
  "n": "nonce-uuid",
  "s": ["scopes"],
  "u": "trial_user_id"  // ← This identifies the trial user
}
```

### 🔄 Migration Logic
```python
# In callback, after getting Google token:
if user.email.startswith("trial_") and user.email.endswith("@trial.local"):
    # This is a trial migration!
    migrate_trial_to_google(
        trial_user_id=user.id,
        google_email=token_data["email"],
        google_token_data=token_data
    )
```

### 📊 Database Changes
```sql
-- Before Migration
SELECT * FROM users WHERE id = 'trial-user-id';
-- email: trial_abc123@trial.local
-- is_active: false
-- password_hash: <trial_password_hash>

-- After Migration  
SELECT * FROM users WHERE id = 'trial-user-id';
-- email: user@gmail.com
-- is_active: true
-- password_hash: <random_secure_hash>

-- Agents remain unchanged!
SELECT * FROM agents WHERE user_id = 'trial-user-id';
-- All agents still there with same configurations
```

### ✨ Zero Data Loss Guarantee
```
user_id: UNCHANGED ✅
  ↓
agents.user_id: UNCHANGED ✅
  ↓
All agents preserved ✅
```
