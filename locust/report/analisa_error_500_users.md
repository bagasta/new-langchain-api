# Laporan Analisis Kegagalan Load Test (500 User)

**Tanggal:** 23 Desember 2025
**Skenario:** 500 Pengguna Konkuren selama 5 Menit
**Status:** ❌ **CRITICAL FAILURE**

## 1. Ringkasan Masalah
Pengujian beban dengan 500 pengguna secara bersamaan menyebabkan kegagalan sistem yang meluas. Sistem tidak mampu menangani lonjakan trafik ini, mengakibatkan ribuan permintaan gagal.

## 2. Analisis Error
Berdasarkan file log `failures(500 users 5m).csv`, ditemukan pola kesalahan sebagai berikut:

### **Jenis Error Utama**
1.  **`502 Bad Gateway` (Dominan)**
    *   **Penyebab:** Server aplikasi (FastAPI/Uvicorn) kewalahan dan tidak dapat merespons permintaan dalam batas waktu yang ditentukan. Reverse proxy (seperti Nginx) atau Load Balancer menutup koneksi karena timeout.
    *   **Dampak:** Pengguna tidak dapat mendaftar, login, atau menggunakan fitur agen.

2.  **`500 Internal Server Error`**
    *   **Penyebab:** Terjadi pengecualian (exception) yang tidak tertangani di sisi server. Ini sering kali disebabkan oleh kegagalan koneksi database (connection pool habis) atau kehabisan memori (OOM).

### **Endpoint Terdampak**
Hampir seluruh alur kerja pengguna mengalami kegagalan:
*   `POST /api/v1/auth/register` (Paling banyak gagal)
*   `POST /api/v1/auth/login`
*   `POST /api/v1/auth/activate`
*   `POST /api/v1/agents/{id}/execute`

## 3. Akar Masalah (Root Cause)
1.  **Bottleneck Database:** Latensi tinggi pada tes 100 user (hingga 8 detik) mengindikasikan bahwa database adalah hambatan utama. Pada 500 user, antrian penulisan ke database kemungkinan besar penuh, menyebabkan timeout.
2.  **CPU Bound:** Proses hashing password (bcrypt) saat registrasi sangat memakan CPU. Dengan 500 registrasi bersamaan, CPU server kemungkinan mencapai 100%, membuat proses lain terhenti (starvation).
3.  **Connection Exhaustion:** Jumlah koneksi ke database mungkin telah melebihi batas `max_connections` yang diizinkan.

## 4. Saran Perbaikan (Rekomendasi)

Untuk mencegah error ini terulang dan meningkatkan kapasitas sistem, disarankan melakukan langkah-langkah berikut:

### **A. Optimasi Infrastruktur & Database**
*   **Connection Pooling:** Gunakan **PgBouncer** untuk mengelola koneksi database secara efisien. Ini mencegah aplikasi membuka terlalu banyak koneksi langsung ke PostgreSQL.
*   **Database Tuning:** Tingkatkan `max_connections` dan optimalkan konfigurasi PostgreSQL (`shared_buffers`, `work_mem`) sesuai kapasitas RAM server.
*   **Read Replicas:** Jika beban pembacaan tinggi, gunakan Read Replica untuk memisahkan trafik baca dan tulis.

### **B. Scaling Aplikasi**
*   **Horizontal Scaling:** Jangan hanya menjalankan satu instance aplikasi. Jalankan beberapa worker Uvicorn/Gunicorn atau replika container (jika menggunakan Docker/Kubernetes) di belakang Load Balancer.
*   **Vertical Scaling:** Tambahkan CPU core pada server jika monitoring menunjukkan penggunaan CPU konsisten di 100%.

### **C. Optimasi Kode**
*   **Asynchronous Processing:** Pastikan semua operasi I/O (database, network call) bersifat `async`. Untuk tugas berat yang tidak perlu respons instan (seperti mengirim email aktivasi), pindahkan ke **Background Worker** (menggunakan Celery atau Arq).
*   **Rate Limiting:** Terapkan pembatasan jumlah request (Rate Limiting) per IP untuk mencegah satu pengguna membebani sistem.

### **D. Konfigurasi Server**
*   **Timeout:** Perbesar nilai timeout pada Nginx (`proxy_read_timeout`) dan Gunicorn/Uvicorn (`timeout`) untuk memberikan waktu lebih bagi proses yang lambat, meskipun ini hanya solusi sementara.

## 5. Kesimpulan
Sistem saat ini stabil untuk ~100 pengguna (meskipun lambat), namun **gagal total pada 500 pengguna**. Prioritas utama perbaikan adalah **Optimasi Database** dan **Scaling Aplikasi** untuk menangani beban komputasi hashing password.
