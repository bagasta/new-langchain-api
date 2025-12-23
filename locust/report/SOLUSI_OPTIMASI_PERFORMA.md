# Panduan Lengkap Solusi Optimasi Performa & Skalabilitas

Dokumen ini berisi panduan teknis langkah demi langkah untuk mengatasi masalah "Bad Gateway" dan "Internal Server Error" saat beban tinggi (500+ user), serta strategi untuk meningkatkan kapasitas sistem LangChain API.

---

## 1. Optimasi Level Aplikasi (Code & Runtime)

Masalah utama saat registrasi massal adalah **CPU Bottleneck** (karena hashing password) dan **Blocking I/O**.

### A. Gunakan Multiple Workers (Wajib)
Python memiliki Global Interpreter Lock (GIL), yang berarti satu proses hanya bisa menggunakan satu core CPU. Hashing password adalah operasi CPU-bound. Jika Anda hanya menjalankan satu worker, 500 request akan antri di satu core.

**Solusi:** Jalankan aplikasi dengan beberapa worker proses.
**Rekomendasi:** Jumlah worker = `(2 x Jumlah Core CPU) + 1`.

**Cara Menjalankan (Tanpa Docker):**
```bash
# Contoh jika server punya 4 Core
gunicorn -w 9 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
# Atau langsung dengan Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 9
```

### B. Background Tasks
Jangan biarkan pengguna menunggu proses yang tidak perlu hasil instan (seperti kirim email aktivasi, logging analitik, upload dokumen berat).

**Contoh Implementasi (FastAPI BackgroundTasks):**
```python
from fastapi import BackgroundTasks

def send_welcome_email(email: str):
    # Logika kirim email yang lambat (2-3 detik)
    pass

@app.post("/register")
async def register(user: UserCreate, background_tasks: BackgroundTasks):
    # 1. Simpan user ke DB (Cepat)
    new_user = await auth_service.create_user(user)
    
    # 2. Lempar tugas email ke background (Tidak memblokir response)
    background_tasks.add_task(send_welcome_email, user.email)
    
    return {"status": "User created"}
```
*Untuk skala lebih besar, gunakan **Celery** dengan Redis.*

---

## 2. Optimasi Database (PostgreSQL)

Error "Internal Server Error" seringkali karena kehabisan koneksi database.

### A. Gunakan Connection Pooler (PgBouncer)
Aplikasi modern membuka tutup koneksi dengan sangat cepat. PostgreSQL memakan resource besar untuk setiap koneksi baru. **PgBouncer** menjaga koneksi ke DB tetap terbuka dan meminjamkannya ke aplikasi secara efisien.

### B. Tuning Konfigurasi PostgreSQL (`postgresql.conf`)
Edit file konfigurasi PostgreSQL untuk performa lebih baik (sesuaikan dengan RAM server, contoh untuk RAM 8GB):

```properties
# Izinkan lebih banyak koneksi (default biasanya 100)
max_connections = 500

# Memori untuk caching data (25% dari Total RAM)
shared_buffers = 2GB

# Estimasi memori tersedia untuk OS caching (75% dari Total RAM)
effective_cache_size = 6GB

# Memori untuk operasi sort/hash per koneksi
work_mem = 16MB

# Checkpoint (mengurangi I/O spike)
min_wal_size = 1GB
max_wal_size = 4GB
```

---

## 3. Arsitektur Deployment (Docker & Scaling)

Gunakan Docker Compose untuk mensimulasikan arsitektur production yang *scalable*. Kita akan menggunakan Nginx sebagai Load Balancer di depan beberapa container aplikasi.

**Struktur Folder:**
```
project/
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
└── ...
```

### A. File `nginx/nginx.conf`
Konfigurasi Nginx untuk membagi beban (Load Balancing).

```nginx
events { worker_connections 1024; }

http {
    upstream backend_api {
        # Nginx akan membagi request ke container-container ini
        server api_1:8000;
        server api_2:8000;
        server api_3:8000;
    }

    server {
        listen 80;
        
        location / {
            proxy_pass http://backend_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            
            # Timeout settings (Penting untuk load tinggi)
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
}
```

### B. File `docker-compose.yml`
Setup lengkap dengan Replikasi Aplikasi, PgBouncer, dan Redis.

```yaml
version: '3.8'

services:
  # 1. Load Balancer
  nginx:
    image: nginx:latest
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on:
      - api_1
      - api_2
      - api_3

  # 2. Aplikasi (Replikasi Manual untuk contoh sederhana)
  # Dalam production swarm/k8s, ini bisa di-scale otomatis
  api_1: &api_service
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      - DATABASE_URL=postgresql://user:pass@pgbouncer:6432/dbname
      - REDIS_URL=redis://redis:6379
    depends_on:
      - pgbouncer
      - redis

  api_2:
    <<: *api_service

  api_3:
    <<: *api_service

  # 3. Database
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: dbname
    command: postgres -c 'max_connections=500'
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # 4. Connection Pooler
  pgbouncer:
    image: edoburu/pgbouncer
    environment:
      DB_USER: user
      DB_PASSWORD: pass
      DB_HOST: db
      DB_NAME: dbname
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 1000
      DEFAULT_POOL_SIZE: 20
    ports:
      - "6432:6432"
    depends_on:
      - db

  # 5. Caching & Broker
  redis:
    image: redis:alpine

volumes:
  postgres_data:
```

---

## 4. Konfigurasi Server (OS Level)

Jika server Linux Anda memiliki limitasi default, koneksi akan ditolak meski aplikasi sudah dioptimasi.

**Cek Limit:**
```bash
ulimit -n
```
Jika hasilnya `1024`, ini terlalu kecil untuk 500 user konkuren (karena setiap user membuka file/socket).

**Naikkan Limit (Temporary):**
```bash
ulimit -n 65535
```

**Naikkan Limit (Permanen):**
Edit `/etc/security/limits.conf`:
```
* soft nofile 65535
* hard nofile 65535
```

---

## 5. Checklist Sebelum Load Test Berikutnya

1.  [ ] **Worker:** Pastikan aplikasi berjalan dengan minimal 4 worker (atau lebih).
2.  [ ] **Database:** Pastikan `max_connections` DB cukup atau gunakan PgBouncer.
3.  [ ] **Logging:** Matikan log level `DEBUG` saat load test, gunakan `INFO` atau `WARNING` saja untuk mengurangi I/O disk.
4.  [ ] **Client:** Pastikan mesin yang menjalankan Locust punya resource cukup (CPU/Bandwidth) agar tidak jadi bottleneck pengujian.
