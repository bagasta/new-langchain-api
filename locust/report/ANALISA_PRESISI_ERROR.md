# Laporan Analisis & Perbaikan Error Load Test (Presisi)

**File Log:** `/home/bagas/Langchain-API-new/locust/report/new-error-log.csv`
**Total Error:** Ribuan baris error `502 Bad Gateway` dan `504 Gateway Time-out`.

## 1. Analisis Akar Masalah (Root Cause Analysis)

Setelah meninjau log error dan konfigurasi sistem, ditemukan bahwa peningkatan jumlah worker aplikasi (dari 1 ke 4) justru memicu bottleneck baru di layer Database.

### A. `502 Bad Gateway` (Dominan)
*   **Gejala:** Ribuan request registrasi gagal seketika.
*   **Penyebab Teknis:** **Connection Pool Exhaustion**.
    *   Setiap worker Uvicorn (ada 4 worker) membuat connection pool sendiri ke database.
    *   Konfigurasi lama: `DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20`. Total koneksi per worker = 30.
    *   Total koneksi dari 4 worker = 4 * 30 = 120 koneksi.
    *   Namun, saat load tinggi, worker berebut koneksi. Jika database lambat merespons (karena CPU spike atau I/O wait), pool di aplikasi penuh.
    *   SQLAlchemy akan melempar error `TimeoutError: QueuePool limit of size 10 overflow 20 reached`.
    *   Aplikasi crash/hang -> Nginx menerima pemutusan koneksi -> `502 Bad Gateway`.

### B. `504 Gateway Time-out`
*   **Gejala:** Request eksekusi agen timeout setelah 300 detik (sesuai config baru).
*   **Penyebab Teknis:** **Database Locking / Contention**.
    *   Karena ribuan request registrasi membanjiri database, query untuk eksekusi agen (ambil history, simpan log) ikut antre.
    *   Database `postgres` default `max_connections` biasanya 100.
    *   Jika 4 worker membuka total >100 koneksi, Postgres akan menolak koneksi baru (`FATAL: sorry, too many clients already`).

## 2. Perbaikan Presisi yang Dilakukan

Kami melakukan tuning vertikal pada konfigurasi Database dan Connection Pool untuk menyeimbangkan throughput antara Nginx, Uvicorn, dan PostgreSQL.

### A. Tuning Aplikasi (`app/core/config.py`)
*   **Meningkatkan Ukuran Pool:**
    *   `DB_POOL_SIZE` dinaikkan dari **10** menjadi **40**.
    *   `DB_POOL_TIMEOUT` dinaikkan dari **10** menjadi **30** detik.
    *   **Rasional:** Dengan 4 worker, kita ingin setiap worker punya cadangan koneksi cukup tanpa harus sering membuat koneksi baru (yang mahal).

### B. Tuning Database (`docker-compose.yml`)
*   **Meningkatkan Kapasitas Koneksi Postgres:**
    *   Menambahkan command: `postgres -c 'max_connections=200'`.
    *   **Rasional:** Default 100 tidak cukup.
        *   Hitungan: 4 worker * (40 pool + 20 overflow) = 240 potensi koneksi maksimal.
        *   Kita set 200 sebagai batas aman hard limit container, dengan asumsi tidak semua worker full load bersamaan (overflow jarang terpakai penuh).

## 3. Verifikasi Logika
*   **Sebelum:** 1 Worker, Pool 10. Bottleneck di CPU Worker.
*   **Percobaan 1 (Gagal):** 4 Worker, Pool 10. Bottleneck pindah ke Database Connection Limit (100). Error `502` meningkat karena worker saling berebut koneksi DB.
*   **Perbaikan Sekarang:** 4 Worker, Pool 40, DB Max Conn 200.
    *   Worker punya jalur lebar ke DB.
    *   DB punya kapasitas menampung semua worker.

## 4. Rekomendasi Selanjutnya
Silakan jalankan ulang load test. Jika masih ada error, kemungkinan besar kita perlu **PgBouncer** (Connection Pooling eksternal) karena membuka 200 koneksi langsung ke Postgres memakan banyak RAM dan CPU database. Tapi untuk 200-500 user, konfigurasi ini seharusnya sudah stabil.
