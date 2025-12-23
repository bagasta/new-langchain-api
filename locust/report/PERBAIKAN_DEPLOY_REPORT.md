# Laporan Perbaikan Error Load Test (200 User)

**Target:** Memperbaiki error `502 Bad Gateway` dan `504 Gateway Time-out` pada file `failures(200 users 3m) DEPLOY.csv`.

## Analisis Masalah
1.  **`502 Bad Gateway` pada Registrasi:**
    *   **Penyebab:** Aplikasi berjalan dengan **1 worker** (default Uvicorn). Saat 200 user mendaftar bersamaan, antrian request penuh dan worker tidak bisa merespons tepat waktu, atau menolak koneksi.
    *   **Konteks:** Meskipun kode sudah `async`, satu worker tetap memiliki limitasi throughput, terutama jika ada sedikit saja operasi blocking atau overhead framework.

2.  **`504 Gateway Time-out` pada Eksekusi Agen:**
    *   **Penyebab:** Eksekusi agen melibatkan pemanggilan LLM yang memakan waktu lama (> 60 detik). Konfigurasi default Nginx memutus koneksi jika tidak ada respons dalam 60 detik.
    *   **Konteks:** Log menunjukkan Nginx memutus koneksi, padahal agen mungkin masih bekerja.

3.  **Konfigurasi Nginx Tidak Tepat:**
    *   File `nginx.conf` di root proyek dikonfigurasi untuk `proxy_pass http://127.0.0.1:8123`, yang **salah** jika dijalankan di dalam container Docker (karena `localhost` di container Nginx bukan host machine). Ini bisa menyebabkan error koneksi.

## Perbaikan yang Dilakukan

### 1. Optimasi Konfigurasi Nginx (`deploy/nginx/docker.dev.conf`)
*   **Meningkatkan Timeout:**
    *   `proxy_read_timeout` dinaikkan dari 180s menjadi **300s** (5 menit). Ini memberi waktu cukup bagi LLM untuk merespons tanpa diputus oleh Nginx.
    *   `proxy_send_timeout` dinaikkan menjadi **300s**.
    *   `proxy_connect_timeout` dinaikkan menjadi **60s**.

### 2. Optimasi Aplikasi (`docker-compose.yml`)
*   **Multi-Worker Strategy:**
    *   Menambahkan command: `uvicorn app.main:app ... --workers 4`.
    *   Dengan 4 worker, aplikasi bisa menangani 4x lipat request secara paralel. Ini sangat krusial untuk mengatasi bottleneck saat registrasi massal.
*   **Keep-Alive Timeout:**
    *   Menambahkan `--timeout-keep-alive 300` agar Uvicorn tidak memutus koneksi idle yang sedang menunggu proses panjang dari Nginx.

### 3. Perbaikan Deployment (`docker-compose.yml`)
*   **Mengganti Config Nginx:**
    *   Mengubah volume mount Nginx untuk menggunakan `deploy/nginx/docker.dev.conf` yang sudah dioptimasi dan memiliki konfigurasi upstream yang benar (`http://app_upstream` -> `app:8000`).
    *   Menyesuaikan mapping port `80:8080` (karena config baru listen di 8080).

## Rekomendasi Selanjutnya
*   **SSL/HTTPS:** Konfigurasi `docker.dev.conf` saat ini hanya melayani HTTP di port 8080. Jika deployment ini membutuhkan HTTPS (port 443), Anda perlu menyalin blok `server { listen 443 ... }` dari `nginx.conf` lama ke `deploy/nginx/docker.dev.conf` dan menyesuaikan `proxy_pass`-nya.
*   **Database:** Pastikan PostgreSQL juga di-tuning (seperti panduan sebelumnya) jika beban terus meningkat.

Silakan jalankan `docker-compose up -d --build` untuk menerapkan perubahan ini dan ulangi load test.
