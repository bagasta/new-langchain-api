# Bug Fix: OAuth Flow Differentiation

## Date: 2026-02-02

## Problem Summary
Backend Google OAuth callback (`/api/v1/auth/google/callback`) was incorrectly attempting to migrate EVERY trial/guest user's OAuth flow, including **Agent OAuth flows** (for Google Tools authentication).

### Root Cause
The callback function `process_google_callback()` could not differentiate between:

1. **Agent OAuth Flow** - User authenticating Google tools for an agent
   - Should: Save OAuth token, redirect to success
   - Was doing: Checking if trial account → trying to migrate → FAILING with "not a trial/guest account"

2. **Migrate Trial Flow** - User upgrading from GUEST/TRIAL to real Google account
   - Should: Check trial status, migrate account, redirect to dashboard
   - Was doing: Correctly migrating

### Error Message Seen
```
"This account is not a trial/guest account (no trial email format or TRIAL/GUEST plan_code found)"
```

This error appeared when GUEST/TRIAL users tried to authenticate Google tools for agents, because backend was treating it as migration flow.

---

## Solution

### Changes Made

#### 1. Added Migration Marker in OAuth State
**File**: `app/services/auth_service.py`

Added `is_migration` parameter to `create_google_auth_url()`:

```python
def create_google_auth_url(
    self,
    user_id: Optional[str] = None,
    scopes: Optional[Sequence[str]] = None,
    include_granted_scopes: bool = False,
    agent_id: Optional[str] = None,
    is_migration: bool = False,  # NEW PARAMETER
) -> Dict[str, str]:
    # ...
    state_payload = {
        "n": str(uuid4()),
        "s": scopes,
    }
    if user_id:
        state_payload["u"] = user_id
    if agent_id:
        state_payload["a"] = agent_id
    if is_migration:
        state_payload["m"] = True  # MIGRATION MARKER
```

#### 2. Marked Migration Flow Explicitly
**File**: `app/api/v1/auth.py` - `/google/migrate-trial` endpoint

```python
@router.post("/google/migrate-trial")
async def migrate_trial_to_google(
    request: MigrateTrialToGoogleRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    # ...
    auth_data = auth_service.create_google_auth_url(
        user_id=str(request.trial_user_id),
        scopes=DEFAULT_GOOGLE_SCOPES,
        is_migration=True,  # EXPLICITLY MARK AS MIGRATION
    )
```

#### 3. Fixed Callback Logic
**File**: `app/api/v1/auth.py` - `process_google_callback()`

**Before** (Buggy code):
```python
# Check if this is a trial account migration flow
is_trial_migration = False
if user:
    # ALWAYS checks if user is trial/guest
    is_trial_account = is_trial_email or trial_or_guest_api_key is not None
    
    if is_trial_account:
        # ALWAYS tries to migrate - BUG!
        migrate_trial_to_google(...)
```

**After** (Fixed code):
```python
# Extract migration marker from state
is_migration_flow = state_data.get("m", False) if state_data else False

# ONLY perform migration logic if explicitly marked
if is_migration_flow and user:
    # Check if trial account
    is_trial_account = is_trial_email or trial_or_guest_api_key is not None
    
    if not is_trial_account:
        # Migration flow but NOT trial - ERROR
        return RedirectResponse(to error page)
    
    # IS trial account in migration flow - MIGRATE
    migrate_trial_to_google(...)
    return RedirectResponse(to dashboard)

# If NOT migration flow, continue with normal OAuth token storage
# (This is for Agent OAuth flows)
```

---

## Flow Comparison

### Flow 1: Agent OAuth (Google Tools Authentication)
**Frontend** → `POST /auth/google?agent_id=xxx&scopes=gmail,sheets`  
**Backend** → `create_google_auth_url(agent_id=xxx, is_migration=False)`  
**State** → `{"u": "user-id", "a": "agent-id", "s": ["scopes"], "m": False}` ❌ NO MIGRATION MARKER  
**Google** → User authorizes → Callback  
**Backend Callback** → `is_migration_flow = False` → **SKIP migration check** → Save token → Success  

### Flow 2: Migrate Trial to Google Account
**Frontend** → `POST /google/migrate-trial` with `trial_user_id`  
**Backend** → `create_google_auth_url(user_id=trial_id, is_migration=True)` ✅  
**State** → `{"u": "trial-user-id", "s": ["scopes"], "m": True}` ✅ MIGRATION MARKER  
**Google** → User authorizes → Callback  
**Backend Callback** → `is_migration_flow = True` → **CHECK trial status** → Migrate account → Success  

---

## Testing

### Test Case 1: Agent OAuth for GUEST User ✅
1. Create GUEST user (plan_code=GUEST)
2. Create agent with Google tools (gmail)
3. Call `POST /google/auth?agent_id={agent_id}&scopes=gmail`
4. Complete OAuth flow
5. **Expected**: Token saved, redirect to success
6. **Result**: ✅ PASS (no longer errors with "not trial account")

### Test Case 2: Migrate GUEST to Google Account ✅
1. Create GUEST user
2. Call `POST /google/migrate-trial` with `trial_user_id`
3. Complete OAuth flow
4. **Expected**: Account migrated, email updated, plan upgraded to TRIAL
5. **Result**: ✅ PASS

### Test Case 3: Agent OAuth for PRO User ✅
1. Create PRO_M user
2. Create agent with Google tools
3. Complete OAuth flow
4. **Expected**: Token saved, no migration attempted
5. **Result**: ✅ PASS

### Test Case 4: Migrate Non-Trial Account (Should Fail) ✅
1. Create PRO_M user
2. Call `POST /google/migrate-trial` with that user_id
3. **Expected**: Error "not a trial account" BEFORE OAuth
4. **Result**: ✅ PASS (validation at /migrate-trial endpoint)

---

## State Payload Schema

### OAuth State Structure
```typescript
interface OAuthState {
  n: string;           // Nonce (random UUID)
  s: string[];         // Requested scopes
  u?: string;          // User ID (optional)
  a?: string;          // Agent ID (optional, for agent-scoped OAuth)
  m?: boolean;         // Migration marker (true = migrate trial flow)
}
```

### State Examples

**Agent OAuth:**
```json
{
  "n": "abc-123-def",
  "s": ["https://www.googleapis.com/auth/gmail.readonly"],
  "u": "user-uuid-here",
  "a": "agent-uuid-here"
  // NO "m" field or m=false
}
```

**Migration Flow:**
```json
{
  "n": "xyz-789-abc",
  "s": ["https://www.googleapis.com/auth/userinfo.email"],
  "u": "trial-user-uuid",
  "m": true  // MIGRATION MARKER
}
```

---

## Impact Assessment

### Before Fix
- ❌ GUEST users CANNOT use Google tools on agents
- ❌ Error: "not a trial/guest account" on agent OAuth
- ✅ Trial migration works correctly

### After Fix
- ✅ GUEST users CAN use Google tools on agents
- ✅ Agent OAuth completes successfully
- ✅ Trial migration still works correctly
- ✅ Clear separation between flows

---

## Files Modified

1. **`app/services/auth_service.py`**
   - Added `is_migration` parameter to `create_google_auth_url()`
   - Added migration marker `"m": True` to state payload

2. **`app/api/v1/auth.py`**
   - Updated `/google/migrate-trial` to pass `is_migration=True`
   - Fixed `process_google_callback()` to check `is_migration_flow` before migration logic
   - Added comment explaining agent OAuth vs migration flow

---

## Rollback Plan

If issues arise, revert commits:
```bash
git log --oneline | grep "OAuth"
git revert <commit-hash>
```

Or manually:
1. Remove `is_migration` parameter from `create_google_auth_url()`
2. Remove `state_payload["m"]` line
3. Restore original `if user:` logic in callback (without `is_migration_flow` check)

---

## Related Documentation

- BRD: Subscription Management (FR-2)
- PRD: Authentication System (US-1.3)
- API Docs: `/auth/google/auth` and `/auth/google/callback`

---

## Notes

- Migration marker uses single character `"m"` to minimize state payload size
- Default value is `False` (no migration) for backward compatibility
- Agent OAuth flows will never have `"m": True` marker
- Only `/google/migrate-trial` endpoint sets `is_migration=True`

---

**Status**: ✅ Fixed and Tested  
**Severity**: High (blocked GUEST users from using Google tools)  
**Priority**: P0 (Critical)  
**Assignee**: Backend Team  
**Reviewer**: Product Team
