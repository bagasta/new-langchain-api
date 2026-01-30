# GUEST Plan Code Implementation

## 📋 Summary

Added **GUEST** plan code to support guest users, with same features as TRIAL plan.

## ✅ Changes Made

### 1. Schema (`app/schemas/auth.py`)
- ✅ Added `GUEST = "GUEST"` to `PlanCode` enum

### 2. Service (`app/services/auth_service.py`)
- ✅ Added `PlanCode.GUEST: 14` to `_PLAN_EXPIRATION_DAYS`
- ✅ Updated `migrate_trial_to_google()` to accept GUEST accounts

### 3. Model (`app/models/auth.py`)
- ✅ Updated enum definition to include GUEST

### 4. API Endpoints (`app/api/v1/auth.py`)
- ✅ Updated migration endpoint to accept GUEST accounts
- ✅ Updated callback to detect GUEST accounts for migration

### 5. Database Migration
- ✅ Created migration file: `alembic/versions/20260130_add_guest_plan_code.py`

## 🔧 Database Migration (Manual)

If alembic doesn't work, run this SQL manually:

```sql
-- Add GUEST to plan_code_enum
ALTER TYPE plan_code_enum ADD VALUE IF NOT EXISTS 'GUEST';

-- Verify
SELECT enum_range(NULL::plan_code_enum);
-- Should return: {PRO_M,PRO_Y,TRIAL,GUEST}
```

## 📝 Plan Code Comparison

| Feature | TRIAL | GUEST |
|---------|-------|-------|
| Duration | 14 days | 14 days |
| Can be migrated | ✅ Yes | ✅ Yes → **Becomes TRIAL** |
| Auto-generated email | ✅ Yes | ✅ Yes |
| Access level | Same as PRO | Same as PRO |
| After Google Login | Stays TRIAL | **Upgrades to TRIAL** ⬆️ |

## 🔄 Migration Flow

### GUEST → Google Login → TRIAL

When a GUEST user signs in with Google:

1. User has `plan_code = "GUEST"`
2. User clicks "Sign in with Google"
3. OAuth completes successfully
4. **Migration happens:**
   - Email changes to Google email ✅
   - Password randomized ✅
   - Account activated ✅
   - **Plan code: GUEST → TRIAL** ⬆️ **NEW!**
   - Expiration reset to 14 days from login
5. User is now a proper TRIAL user with Google account

### TRIAL → Google Login → TRIAL

When a TRIAL user signs in with Google:

1. User has `plan_code = "TRIAL"`
2. User clicks "Sign in with Google"
3. OAuth completes successfully
4. **Migration happens:**
   - Email changes to Google email ✅
   - Password randomized ✅
   - Account activated ✅
   - **Plan code stays TRIAL** ✅
5. User remains TRIAL with Google account

## 🎯 Use Cases

### TRIAL
- Traditional trial users
- User explicitly selected "Start Trial"
- Testing before purchase

### GUEST
- Anonymous/guest users
- Quick access without signup
- Demo/preview mode
- Widget users
- Embedded agent users

## 🔄 Migration Support

Both TRIAL and GUEST accounts can be migrated to Google accounts:

```bash
# Works for both TRIAL and GUEST
curl -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -H "Content-Type: application/json" \
  -d '{
    "trial_user_id": "user-id-here"
  }'
```

The endpoint name is still `/migrate-trial` but it accepts both TRIAL and GUEST.

## 💻 Code Examples

### Create GUEST API Key

```python
# Similar to create_trial_api_key but with GUEST plan
api_key = ApiKey(
    user_id=user.id,
    access_token=access_token,
    plan_code=PlanCode.GUEST.value,  # Use GUEST instead of TRIAL
    expires_at=expires_at,
    created_at=datetime.utcnow(),
    is_active=True,
    trial_ip=ip_str,
)
```

### Check if User is GUEST or TRIAL

```python
# Both are considered "temporary" accounts
is_temporary = user_api_key.plan_code in ["TRIAL", "GUEST"]

# Can migrate both
can_migrate = is_temporary
```

### Generate GUEST Key

You can use the same trial endpoint with GUEST plan:

```bash
curl -X POST http://localhost:8000/api/v1/auth/api-key \
  -H "Content-Type: application/json" \
  -d '{
    "username": "guest@example.com",
    "password": "secure-password",
    "plan_code": "GUEST"
  }'
```

## 🔍 Validation

The migration endpoint now accepts accounts with:

1. ✅ Email format: `trial_*@trial.local`
2. ✅ Plan code: `TRIAL`
3. ✅ Plan code: `GUEST` ⬅️ **NEW**

All three types can be migrated to Google accounts.

## 🚀 Deployment Checklist

- [x] Update schemas
- [x] Update service layer
- [x] Update API endpoints
- [x] Update models
- [x] Create migration file
- [ ] Run migration: `ALTER TYPE plan_code_enum ADD VALUE 'GUEST'`
- [ ] Test GUEST account creation
- [ ] Test GUEST account migration
- [ ] Update frontend to use GUEST for anonymous users

## 📚 Related Files

- `app/schemas/auth.py` - GUEST enum definition
- `app/services/auth_service.py` - GUEST expiration & validation
- `app/api/v1/auth.py` - GUEST migration support
- `app/models/auth.py` - GUEST in database enum
- `alembic/versions/20260130_add_guest_plan_code.py` - Migration

---

**Created:** 2026-01-30  
**Status:** ✅ Ready (pending DB migration)
