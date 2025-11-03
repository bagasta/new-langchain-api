-- Retrieve a consolidated view of a user's data by user_id.
-- Usage with psql:
--   \set target_user_id '00000000-0000-0000-0000-000000000000'
--   \i scripts/sql/get_user_full_profile.sql

WITH selected_user AS (
    SELECT *
    FROM users
    WHERE id = :target_user_id::uuid
),
api_key_data AS (
    SELECT
        ak.user_id,
        jsonb_agg(
            jsonb_build_object(
                'id', ak.id,
                'access_token', ak.access_token,
                'plan_code', ak.plan_code,
                'expires_at', ak.expires_at,
                'is_active', ak.is_active,
                'created_at', ak.created_at,
                'trial_ip', ak.trial_ip
            )
            ORDER BY ak.created_at DESC
        ) AS api_keys
    FROM api_keys ak
    WHERE ak.user_id = :target_user_id::uuid
    GROUP BY ak.user_id
),
agent_data AS (
    SELECT
        a.user_id,
        jsonb_agg(
            jsonb_build_object(
                'id', a.id,
                'name', a.name,
                'status', a.status,
                'created_at', a.created_at,
                'updated_at', a.updated_at,
                'tool_count', (
                    SELECT COUNT(*)
                    FROM agent_tools at
                    WHERE at.agent_id = a.id
                )
            )
            ORDER BY a.created_at DESC
        ) AS agents
    FROM agents a
    WHERE a.user_id = :target_user_id::uuid
    GROUP BY a.user_id
),
execution_stats AS (
    SELECT
        a.user_id,
        jsonb_build_object(
            'total', COUNT(e.*),
            'completed', COUNT(*) FILTER (WHERE e.status = 'completed'),
            'failed', COUNT(*) FILTER (WHERE e.status = 'failed'),
            'cancelled', COUNT(*) FILTER (WHERE e.status = 'cancelled'),
            'last_execution_at', MAX(e.created_at)
        ) AS executions
    FROM executions e
    JOIN agents a ON e.agent_id = a.id
    WHERE a.user_id = :target_user_id::uuid
    GROUP BY a.user_id
),
auth_token_data AS (
    SELECT
        at.user_id,
        jsonb_agg(
            jsonb_build_object(
                'id', at.id,
                'service', at.service,
                'scope', COALESCE(to_jsonb(at.scope), '[]'::jsonb),
                'expires_at', at.expires_at,
                'created_at', at.created_at
            )
            ORDER BY at.created_at DESC
        ) AS tokens
    FROM auth_tokens at
    WHERE at.user_id = :target_user_id::uuid
    GROUP BY at.user_id
),
upload_data AS (
    SELECT
        au.user_id,
        jsonb_agg(
            jsonb_build_object(
                'id', au.id,
                'agent_id', au.agent_id,
                'filename', au.filename,
                'content_type', au.content_type,
                'size_bytes', au.size_bytes,
                'created_at', au.created_at,
                'is_deleted', au.is_deleted
            )
            ORDER BY au.created_at DESC
        ) AS uploads
    FROM agent_uploads au
    WHERE au.user_id = :target_user_id::uuid
    GROUP BY au.user_id
)
SELECT
    u.id,
    u.email,
    u.is_active,
    u.created_at,
    u.updated_at,
    COALESCE(ak.api_keys, '[]'::jsonb) AS api_keys,
    COALESCE(at.tokens, '[]'::jsonb) AS auth_tokens,
    COALESCE(ag.agents, '[]'::jsonb) AS agents,
    COALESCE(es.executions, jsonb_build_object(
        'total', 0,
        'completed', 0,
        'failed', 0,
        'cancelled', 0,
        'last_execution_at', NULL
    )) AS execution_summary,
    COALESCE(up.uploads, '[]'::jsonb) AS uploads
FROM selected_user u
LEFT JOIN api_key_data ak ON ak.user_id = u.id
LEFT JOIN auth_token_data at ON at.user_id = u.id
LEFT JOIN agent_data ag ON ag.user_id = u.id
LEFT JOIN execution_stats es ON es.user_id = u.id
LEFT JOIN upload_data up ON up.user_id = u.id;
