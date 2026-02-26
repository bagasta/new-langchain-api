# GUEST to TRIAL Upgrade Logic

## 📊 Visual Flow

```
┌─────────────────────────────────────────────────────┐
│         User Journey: GUEST → TRIAL                 │
└─────────────────────────────────────────────────────┘

GUEST User (Anonymous)
├── plan_code: "GUEST"
├── email: guest_xyz@guest.local (auto-generated)
├── duration: 14 days
└── access: Full features
         │
         │ User clicks "Sign in with Google"
         ▼
    Google OAuth
         │
         │ User authenticates
         ▼
  Migration Process
  ┌──────────────────────────────────────┐
  │ 1. Update email → user@gmail.com     │
  │ 2. Randomize password                │
  │ 3. Activate account                  │
  │ 4. Save OAuth tokens                 │
  │ 5. CHECK PLAN CODE:                  │
  │    IF plan_code == "GUEST":          │
  │       ⬆️ UPGRADE TO "TRIAL"          │
  │       ⏰ Reset expiration (14 days)  │
  └──────────────────────────────────────┘
         │
         ▼
TRIAL User (Registered)
├── plan_code: "TRIAL" ✨ (upgraded!)
├── email: user@gmail.com
├── duration: 14 days (reset from login date)
└── access: Full features


┌─────────────────────────────────────────────────────┐
│         User Journey: TRIAL → TRIAL                 │
└─────────────────────────────────────────────────────┘

TRIAL User (Already registered)
├── plan_code: "TRIAL"
├── email: user@example.com
├── duration: 14 days
└── access: Full features
         │
         │ User clicks "Sign in with Google"
         ▼
    Google OAuth
         │
         │ User authenticates
         ▼
  Migration Process
  ┌──────────────────────────────────────┐
  │ 1. Update email → user@gmail.com     │
  │ 2. Randomize password                │
  │ 3. Activate account                  │
  │ 4. Save OAuth tokens                 │
  │ 5. CHECK PLAN CODE:                  │
  │    plan_code == "TRIAL"              │
  │       ✅ STAYS "TRIAL"               │
  │       (no expiration reset)          │
  └──────────────────────────────────────┘
         │
         ▼
TRIAL User (Google linked)
├── plan_code: "TRIAL" (unchanged)
├── email: user@gmail.com
├── duration: Same as before
└── access: Full features
```

## 🎯 Why This Design?

### GUEST = Temporary Anonymous Access
- Created automatically (no signup)
- For demos, widgets, embedded agents
- Limited identity (guest_xyz@guest.local)

### TRIAL = Registered User Account
- User has authenticated with real identity
- Google account = permanent identity
- Deserves proper "trial" status

### Upgrade Logic
**When GUEST logs in with Google → becomes TRIAL**

This makes sense because:
1. ✅ User proved their identity (Google OAuth)
2. ✅ User is no longer anonymous
3. ✅ User deserves fresh 14-day trial from login date
4. ✅ Clearer distinction: GUEST (nobody) vs TRIAL (somebody)

## 💻 Code Implementation

### In `auth_service.py`

```python
# After migration completes...
api_key = self.ensure_api_key_for_user(trial_user.id)

# IMPORTANT: If user was GUEST, upgrade to TRIAL
if api_key.plan_code == PlanCode.GUEST.value:
    api_key.plan_code = PlanCode.TRIAL.value
    # Reset expiration to 14 days from now
    api_key.expires_at = self._calculate_plan_expiration(PlanCode.TRIAL)
    self.db.commit()
    logger.info("Upgraded GUEST to TRIAL after Google login")
```

## 📝 Database State Changes

### Before Migration (GUEST)
```sql
SELECT * FROM users WHERE id = 'user-id';
-- email: guest_abc123@guest.local
-- is_active: true

SELECT * FROM api_keys WHERE user_id = 'user-id';
-- plan_code: GUEST
-- expires_at: 2026-02-13 (14 days from creation)
```

### After Migration (TRIAL)
```sql
SELECT * FROM users WHERE id = 'user-id';
-- email: user@gmail.com ✅ (changed)
-- is_active: true

SELECT * FROM api_keys WHERE user_id = 'user-id';
-- plan_code: TRIAL ✅ (upgraded from GUEST!)
-- expires_at: 2026-02-13 (14 days from login) ✅ (reset!)
```

## 🧪 Testing Scenarios

### Scenario 1: GUEST upgrades to TRIAL
```bash
# 1. Create GUEST account
curl -X POST http://localhost:8000/api/v1/auth/api-key/trial \
  -d '{"ip_user": "192.168.1.1"}'
# Response: plan_code = "GUEST", user_id = "xyz"

# 2. Initiate migration
curl -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -d '{"trial_user_id": "xyz"}'
# Get auth_url

# 3. Complete Google OAuth
# (open auth_url in browser)

# 4. Check result
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer NEW_TOKEN"
# Response: plan_code = "TRIAL" ✅ (upgraded!)
```

### Scenario 2: TRIAL stays TRIAL
```bash
# 1. Create TRIAL account
curl -X POST http://localhost:8000/api/v1/auth/api-key \
  -d '{"username": "user@example.com", "password": "pass", "plan_code": "TRIAL"}'
# Response: plan_code = "TRIAL", user_id = "abc"

# 2. Migrate to Google
curl -X POST http://localhost:8000/api/v1/auth/google/migrate-trial \
  -d '{"trial_user_id": "abc"}'
# Complete OAuth...

# 3. Check result
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer NEW_TOKEN"
# Response: plan_code = "TRIAL" ✅ (unchanged)
```

## 🎭 User Experience

### For Anonymous User (GUEST)
```
"Try Demo" → Creates GUEST account
     ↓
Uses features for a while
     ↓
"Hmm, I like this. Let me save my work."
     ↓
"Sign in with Google" → Upgrades to TRIAL
     ↓
"Great! My work is saved and I have 14 more days!"
```

### For Returning User (TRIAL)
```
"I already have an account"
     ↓
"But I want Google login for convenience"
     ↓
"Sign in with Google" → Links Google
     ↓
"Perfect! Same account, just easier login."
```

## ✨ Benefits

1. **Clear User Progression**
   - GUEST → anonymous trial
   - TRIAL → authenticated trial
   - PRO → paid user

2. **Better Conversion Tracking**
   - Count GUEST→TRIAL as successful conversion
   - Track how many anonymous users become real users

3. **Fair Trial Period**
   - GUEST gets fresh 14 days after proving identity
   - Encourages anonymous users to authenticate

4. **Simpler Frontend Logic**
   - Check: `if (plan_code === 'GUEST') show "Sign in to save progress"`
   - Check: `if (plan_code === 'TRIAL') show "Upgrade to PRO"`

---

**Implementation Date:** 2026-01-30  
**Status:** ✅ Complete and Ready  
**Impact:** Improved user journey and conversion tracking
