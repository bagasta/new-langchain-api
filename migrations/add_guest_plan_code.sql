-- Add GUEST Plan Code to Database
-- Run this SQL script manually if alembic migration fails

-- Step 1: Add GUEST value to plan_code_enum
ALTER TYPE plan_code_enum ADD VALUE IF NOT EXISTS 'GUEST';

-- Step 2: Verify the enum values
SELECT enum_range(NULL::plan_code_enum);
-- Expected output: {PRO_M,PRO_Y,TRIAL,GUEST}

-- Step 3: Check existing plan codes in use
SELECT plan_code, COUNT(*) as count
FROM api_keys
GROUP BY plan_code
ORDER BY count DESC;

-- Optional: Create a sample GUEST account for testing
-- (Uncomment to use)
/*
DO $$
DECLARE
    guest_user_id UUID;
    guest_email VARCHAR(255);
    guest_password_hash VARCHAR(255);
    guest_token VARCHAR(255);
    guest_expires_at TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Generate random guest email
    guest_email := 'guest_' || substr(md5(random()::text), 1, 12) || '@guest.local';
    
    -- Use a dummy password hash
    guest_password_hash := '$2b$12$dummyhashfordemopurposesonly1234567890';
    
    -- Create guest user
    INSERT INTO users (id, email, password_hash, is_active, created_at)
    VALUES (gen_random_uuid(), guest_email, guest_password_hash, true, NOW())
    RETURNING id INTO guest_user_id;
    
    -- Generate guest API key
    guest_token := 'sk_guest_' || substr(md5(random()::text), 1, 24);
    guest_expires_at := NOW() + INTERVAL '14 days';
    
    INSERT INTO api_keys (id, user_id, access_token, plan_code, expires_at, is_active, created_at)
    VALUES (
        gen_random_uuid(),
        guest_user_id,
        guest_token,
        'GUEST',
        guest_expires_at,
        true,
        NOW()
    );
    
    -- Print result
    RAISE NOTICE 'Created GUEST account:';
    RAISE NOTICE '  User ID: %', guest_user_id;
    RAISE NOTICE '  Email: %', guest_email;
    RAISE NOTICE '  Token: %', guest_token;
    RAISE NOTICE '  Expires: %', guest_expires_at;
END $$;
*/
