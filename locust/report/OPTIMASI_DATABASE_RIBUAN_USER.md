# Panduan Optimasi Database PostgreSQL untuk Skala Ribuan User

Dokumen ini berisi konfigurasi PostgreSQL dan PgBouncer yang dioptimalkan untuk menangani beban transaksi tinggi (High Throughput) pada LangChain API.

## 1. Spesifikasi Hardware (Rekomendasi)
Untuk menangani ribuan user aktif, database membutuhkan resource yang memadai:
*   **RAM:** Minimal 16GB (Disarankan 32GB+ agar index muat di memori).
*   **Disk:** NVMe SSD (Wajib untuk IOPS tinggi).
*   **CPU:** 4 Core ke atas.

## 2. Tuning `postgresql.conf`

Gunakan [PGTune](https://pgtune.leopard.in.ua/) untuk hasil presisi. Berikut adalah contoh konfigurasi untuk server dengan **RAM 16GB, 4 CPU, SSD**:

```properties
# --- KONEKSI ---
# Jangan set terlalu tinggi tanpa PgBouncer. 
# Setiap koneksi memakan RAM (~10MB).
max_connections = 200 

# --- MEMORI ---
# 25% dari Total RAM. Buffer utama untuk caching data tabel.
shared_buffers = 4GB

# 75% dari Total RAM. Estimasi cache OS yang tersedia.
effective_cache_size = 12GB

# Memori untuk operasi maintenance (VACUUM, CREATE INDEX).
maintenance_work_mem = 1GB

# Memori per operasi sort/hash. Hati-hati, ini dikali jumlah koneksi aktif.
# 16MB * 200 koneksi = 3.2GB potensi penggunaan RAM.
work_mem = 16MB

# --- WRITE AHEAD LOG (WAL) ---
# Mengurangi frekuensi checkpoint (I/O spike).
min_wal_size = 1GB
max_wal_size = 4GB
wal_buffers = 16MB

# --- CHECKPOINT ---
# Menyebar beban penulisan ke disk agar tidak macet sesaat.
checkpoint_completion_target = 0.9

# --- WORKER PROCESSES ---
# Sesuaikan dengan jumlah CPU core.
max_worker_processes = 4
max_parallel_workers_per_gather = 2
max_parallel_workers = 4

# --- DISK I/O ---
# Untuk SSD
random_page_cost = 1.1
effective_io_concurrency = 200
```

## 3. Connection Pooling (PgBouncer)

**Sangat Wajib** untuk ribuan user. Aplikasi tidak boleh connect langsung ke Postgres, tapi lewat PgBouncer.

### Kenapa?
*   Postgres berat saat membuka koneksi baru (fork process).
*   PgBouncer ringan dan menjaga koneksi ke Postgres tetap terbuka (persistent).
*   Ribuan client bisa "berbagi" 50-100 koneksi fisik ke database.

### Konfigurasi `pgbouncer.ini`

```ini
[databases]
# Alias = host=IP port=5432 dbname=DB
langchain_db = host=127.0.0.1 port=5432 dbname=langchain_prod

[pgbouncer]
listen_addr = *
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# --- POOLING ---
# Transaction mode: Koneksi dikembalikan ke pool segera setelah transaksi selesai.
# Ini paling efisien untuk aplikasi web stateless.
pool_mode = transaction

# Total koneksi maksimal yang diterima PgBouncer dari Client (Aplikasi)
max_client_conn = 10000

# Total koneksi maksimal yang dibuka PgBouncer ke Postgres
default_pool_size = 100

# Cadangan koneksi jika pool penuh
reserve_pool_size = 20
reserve_pool_timeout = 5.0
```

## 4. Strategi Indexing

Query lambat adalah pembunuh performa nomor satu.

1.  **Index Foreign Keys:** Pastikan semua kolom `user_id`, `agent_id` di tabel anak (Executions, Documents) memiliki index.
    ```sql
    CREATE INDEX idx_executions_agent_id ON executions(agent_id);
    CREATE INDEX idx_executions_user_id ON executions(user_id); -- Jika ada kolom user_id
    ```
2.  **Index Pencarian:** Untuk kolom yang sering dicari (misal `email`, `session_id`).
    ```sql
    CREATE INDEX idx_users_email ON users(email);
    CREATE INDEX idx_executions_session_id ON executions(session_id);
    ```
3.  **Composite Index:** Jika sering query dengan 2 kolom (misal `agent_id` DAN `status`).
    ```sql
    CREATE INDEX idx_executions_agent_status ON executions(agent_id, status);
    ```
4.  **Vector Index (pgvector):** Untuk tabel embedding, gunakan index `hnsw` atau `ivfflat` agar pencarian RAG cepat.
    ```sql
    CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops);
    ```

## 5. Maintenance Rutin
*   **VACUUM ANALYZE:** Jalankan rutin (atau pastikan autovacuum aktif) agar statistik query planner selalu update.
*   **Monitoring:** Gunakan `pg_stat_statements` untuk melihat query mana yang paling lambat dan memakan resource CPU tinggi.
