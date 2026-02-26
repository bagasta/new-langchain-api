# OAuth Flow Diagram - Before vs After Fix

## BEFORE FIX (❌ BUG)

```
┌─────────────────────────────────────────────────────────────┐
│ Flow 1: Agent OAuth (Google Tools) - GUEST User           │
└─────────────────────────────────────────────────────────────┘

Frontend                 Backend                    Google
   │                        │                          │
   ├─POST /google/auth─────►│                          │
   │  agent_id=xxx          │                          │
   │  scopes=gmail          │                          │
   │                        │                          │
   │◄──auth_url─────────────┤                          │
   │   state={u,a,s}        │                          │
   │                        │                          │
   ├────────────────────────┼───AUTH URL──────────────►│
   │                        │                          │
   │◄───────────────────────┼────CALLBACK─────────────┤
   │                        │   code, state            │
   │                        │                          │
   │                     ❌ CALLBACK LOGIC:            │
   │                        │                          │
   │                        if user:                   │
   │                          is_trial = check()       │
   │                          if is_trial:  ❌ ALWAYS  │
   │                            migrate()  ❌          │
   │                                                   │
   │◄────ERROR──────────────┤                          │
   │  "not trial account"   │                          │
   │                        │                          │
   ✗ FAILS FOR GUEST USERS                             │
```

```
┌─────────────────────────────────────────────────────────────┐
│ Flow 2: Migrate Trial to Google - WORKS                    │
└─────────────────────────────────────────────────────────────┘

Frontend                 Backend                    Google
   │                        │                          │
   ├─POST /migrate-trial───►│                          │
   │  trial_user_id         │                          │
   │                        │                          │
   │◄──auth_url─────────────┤                          │
   │   state={u,s}          │                          │
   │                        │                          │
   ├────────────────────────┼───AUTH URL──────────────►│
   │                        │                          │
   │◄───────────────────────┼────CALLBACK─────────────┤
   │                        │   code, state            │
   │                        │                          │
   │                     ✅ CALLBACK LOGIC:            │
   │                        │                          │
   │                        if user:                   │
   │                          is_trial = check()       │
   │                          if is_trial:             │
   │                            migrate() ✅           │
   │                                                   │
   │◄────SUCCESS────────────┤                          │
   │  token, migrated=true  │                          │
   │                        │                          │
   ✓ WORKS CORRECTLY                                   │
```

---

## AFTER FIX (✅ WORKS)

```
┌─────────────────────────────────────────────────────────────┐
│ Flow 1: Agent OAuth (Google Tools) - GUEST User           │
└─────────────────────────────────────────────────────────────┘

Frontend                 Backend                    Google
   │                        │                          │
   ├─POST /google/auth─────►│                          │
   │  agent_id=xxx          │                          │
   │  scopes=gmail          │                          │
   │                        │                          │
   │                     create_google_auth_url(       │
   │                       agent_id=xxx,               │
   │                       is_migration=False ⭐       │
   │                     )                             │
   │                        │                          │
   │◄──auth_url─────────────┤                          │
   │   state={u,a,s,m:false}│ ⭐ NO MIGRATION MARKER   │
   │                        │                          │
   ├────────────────────────┼───AUTH URL──────────────►│
   │                        │                          │
   │◄───────────────────────┼────CALLBACK─────────────┤
   │                        │   code, state            │
   │                        │                          │
   │                     ✅ CALLBACK LOGIC:            │
   │                        │                          │
   │                        is_migration = state.get("m") │
   │                        # is_migration = False     │
   │                        │                          │
   │                        if is_migration and user:  │
   │                          # SKIPPED ✅             │
   │                        │                          │
   │                        # Continue normal OAuth    │
   │                        save_auth_token() ✅       │
   │                                                   │
   │◄────SUCCESS────────────┤                          │
   │  token saved           │                          │
   │                        │                          │
   ✓ WORKS FOR GUEST USERS NOW ✅                      │
```

```
┌─────────────────────────────────────────────────────────────┐
│ Flow 2: Migrate Trial to Google - STILL WORKS              │
└─────────────────────────────────────────────────────────────┘

Frontend                 Backend                    Google
   │                        │                          │
   ├─POST /migrate-trial───►│                          │
   │  trial_user_id         │                          │
   │                        │                          │
   │                     create_google_auth_url(       │
   │                       user_id=trial_id,           │
   │                       is_migration=True ⭐        │
   │                     )                             │
   │                        │                          │
   │◄──auth_url─────────────┤                          │
   │   state={u,s,m:true}   │ ⭐ MIGRATION MARKER      │
   │                        │                          │
   ├────────────────────────┼───AUTH URL──────────────►│
   │                        │                          │
   │◄───────────────────────┼────CALLBACK─────────────┤
   │                        │   code, state            │
   │                        │                          │
   │                     ✅ CALLBACK LOGIC:            │
   │                        │                          │
   │                        is_migration = state.get("m") │
   │                        # is_migration = True ⭐   │
   │                        │                          │
   │                        if is_migration and user:  │
   │                          is_trial = check() ✅    │
   │                          if is_trial:             │
   │                            migrate() ✅           │
   │                                                   │
   │◄────SUCCESS────────────┤                          │
   │  token, migrated=true  │                          │
   │                        │                          │
   ✓ STILL WORKS CORRECTLY ✅                          │
```

---

## Key Differences

### State Payload

**Agent OAuth:**
```json
{
  "n": "nonce-123",
  "u": "user-uuid",
  "a": "agent-uuid",
  "s": ["gmail.readonly"],
  "m": false  // ⭐ or omitted
}
```

**Migration Flow:**
```json
{
  "n": "nonce-456",
  "u": "trial-user-uuid",
  "s": ["userinfo.email"],
  "m": true  // ⭐ MIGRATION MARKER
}
```

### Callback Decision Tree

```
process_google_callback(code, state)
│
├─ Decode state
│  └─ Extract: u (user_id), a (agent_id), m (is_migration)
│
├─ is_migration_flow = state["m"] ?? false
│
├─ IF is_migration_flow AND user exists:
│  │
│  ├─ Check if user is TRIAL/GUEST
│  │  │
│  │  ├─ YES → migrate_trial_to_google() ✅
│  │  │         redirect to /auth/callback
│  │  │
│  │  └─ NO → Error: "not a trial account" ❌
│  │            redirect to /auth/error
│  │
│  └─ RETURN (exit early)
│
└─ ELSE (NOT migration flow OR no user):
   │
   ├─ Get or create user
   ├─ save_auth_token(user_id, token_data, agent_id) ✅
   └─ redirect to frontend
```

---

## Summary

### Problem
- Backend couldn't differentiate between **Agent OAuth** and **Migrate Trial**
- EVERY trial/guest user OAuth was treated as migration attempt
- Agent OAuth for GUEST users FAILED

### Solution
- Added `"m": true` marker in state for migration flows
- Callback now checks `is_migration_flow` before running migration logic
- Agent OAuth flows skip migration check entirely

### Result
- ✅ Agent OAuth works for GUEST/TRIAL users
- ✅ Migration flow still works correctly
- ✅ Clear separation of concerns
