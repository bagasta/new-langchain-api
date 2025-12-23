# Laporan Analisis Kegagalan Load Test (200 User)

**Tanggal:** 23 Desember 2025
**Skenario:** 200 Pengguna Konkuren selama 3 Menit
**Status:** ⚠️ **PARTIAL FAILURE (Timeouts)**

## 1. Ringkasan Masalah
Pada pengujian dengan 200 pengguna, sistem berhasil menangani proses registrasi dan login (tidak seperti pada tes 500 user). Namun, kegagalan terjadi secara spesifik pada fitur **Eksekusi Agen**, yang mengalami timeout.

## 2. Analisis Error
Berdasarkan file log `failures(200 users 3m).csv`:

### **Jenis Error**
*   **`504 Gateway Time-out`**
    *   Error ini berasal dari **Nginx**.
    *   **Arti:** Nginx telah meneruskan permintaan ke aplikasi (FastAPI), tetapi aplikasi tidak memberikan respons dalam batas waktu yang ditentukan (default biasanya 60 detik).

### **Endpoint Terdampak**
*   `POST /api/v1/agents/{id}/execute`
    *   Semua error yang tercatat terjadi pada endpoint ini.
    *   Endpoint ini kemungkinan besar melakukan tugas berat: memanggil LLM (OpenAI/Gemini), mencari di vector database, atau memproses dokumen.

## 3. Akar Masalah (Root Cause)
1.  **Proses Eksekusi Lambat:** Logika eksekusi agen memakan waktu lebih lama daripada setting `proxy_read_timeout` di Nginx. Saat beban meningkat, waktu respons dari LLM atau database mungkin melambat, menyebabkan total waktu eksekusi melebihi batas timeout.
2.  **Blocking Operations:** Jika kode eksekusi agen bersifat sinkronus (synchronous) dan worker terbatas, request baru akan mengantri. Antrian yang panjang menyebabkan request di belakang menunggu terlalu lama hingga timeout.

## 4. Saran Perbaikan

### **A. Solusi Cepat (Konfigurasi)**
*   **Naikkan Timeout Nginx:**
    Ubah konfigurasi Nginx untuk memperbolehkan koneksi yang lebih lama.
    ```nginx
    location / {
        proxy_read_timeout 300s; # Naikkan ke 5 menit
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        ...
    }
    ```
*   **Naikkan Timeout Gunicorn/Uvicorn:**
    Jika menggunakan Gunicorn, tambahkan flag `--timeout 300`.

### **B. Solusi Jangka Panjang (Arsitektur)**
*   **Asynchronous Execution (Fire-and-Forget):**
    Jangan biarkan pengguna menunggu hasil eksekusi agen secara real-time via HTTP request jika prosesnya memakan waktu menit-an.
    1.  Ubah endpoint `/execute` agar langsung mengembalikan `202 Accepted` dan `task_id`.
    2.  Jalankan proses agen di **Background Worker** (Celery/Arq).
    3.  Frontend melakukan *polling* ke endpoint status (misal: `GET /tasks/{task_id}`) atau gunakan WebSocket untuk notifikasi saat selesai.

## 5. Kesimpulan
Sistem mampu menangani beban registrasi 200 user, namun **gagal menangani durasi eksekusi agen yang panjang**. Solusi terbaik adalah mengubah mekanisme eksekusi menjadi asinkronus (background job) untuk menghindari limitasi timeout HTTP.
