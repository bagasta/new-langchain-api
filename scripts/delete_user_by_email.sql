-- ===========================================================
-- Script: Hapus User berdasarkan Email
-- ===========================================================
-- PERINGATAN: Script ini menghapus user DAN semua data terkait
-- secara permanen (CASCADE). Tidak bisa dibatalkan!
--
-- Data yang ikut terhapus (CASCADE):
--   - agents           (agents milik user)
--   - api_keys         (API key user)
--   - auth_tokens      (Google OAuth token user)
--   - agent_uploads    (upload file user, SET NULL on agent uploads)
--   - executions       (riwayat eksekusi agent)
--   - embeddings       (vector embedding dokumen)
--   - agent_histories  (riwayat perubahan agent)
--
-- Cara pakai:
--   Ganti 'user@example.com' di bawah dengan email yang ingin dihapus
--   lalu jalankan script ini di database PostgreSQL.
-- ===========================================================

-- Cek dulu sebelum hapus (opsional, untuk konfirmasi)
SELECT
    u.id          AS user_id,
    u.email,
    u.is_active,
    u.created_at,
    COUNT(DISTINCT a.id)   AS total_agents,
    COUNT(DISTINCT ak.id)  AS total_api_keys,
    COUNT(DISTINCT at2.id) AS total_auth_tokens
FROM users u
LEFT JOIN agents      a   ON a.user_id  = u.id
LEFT JOIN api_keys    ak  ON ak.user_id = u.id
LEFT JOIN auth_tokens at2 ON at2.user_id = u.id
WHERE u.email = 'user@example.com'  -- << GANTI EMAIL DI SINI
GROUP BY u.id, u.email, u.is_active, u.created_at;

-- ===========================================================
-- HAPUS USER (uncomment baris di bawah setelah yakin)
-- ===========================================================
-- DELETE FROM users
-- WHERE email = 'user@example.com';  -- << GANTI EMAIL DI SINI

-- Konfirmasi hasil
-- SELECT 'User berhasil dihapus' AS status
-- WHERE NOT EXISTS (
--     SELECT 1 FROM users WHERE email = 'user@example.com'
-- );
