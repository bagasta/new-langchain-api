# Analisis & Solusi Final: 502 Bad Gateway (10,369 Error)

**Test Scenario:** 200 user per 3 detik selama 3 menit  
**Error Rate:** 98.5% (10,369 dari 10,524 total error)

## Akar Masalah Sebenarnya (Root Cause)

### 1. **Bcrypt Blocking Thread Pool**
Meskipun kita sudah menggunakan `run_in_executor`, ada masalah:
- Default `ThreadPoolExecutor` Python hanya punya **min(32, os.cpu_count() + 4)** threads (biasanya 8-12 threads)
- Dengan 200 user dalam 3 detik = **66 registrasi/detik**
- Bcrypt hashing memakan waktu **~250-500ms per request**
- Thread pool **PENUH** → request baru **hung** → Nginx timeout → 502
  
**Bukti:**
```
66 req/sec × 0.3 sec/hash = 19.8 threads needed
Tapi hanya ada 8-12 threads tersedia
```

### 2. **Database Connection Starvation**
Walaupun sudah dinaikkan:
- Pool size 40 per worker × 4 workers = 160 koneksi potensial
- Tapi kalau aplikasi **hang** di thread pool, koneksi tidak pernah di-release
- Database pool **terblokir** karena semua koneksi **menunggu** thread

### 3. **Worker Crash/Restart Loop**
Saat worker kehabisan thread:
- Worker **hang** atau **crash**
- Nginx mendapat koneksi terputus → **502 Bad Gateway**
- Worker restart → koneksi baru masuk → crash lagi → loop

## Solusi Presisi (Bertahap)

### **Solusi 1: Optimalkan Bcrypt (WAJIB)**

Bcrypt default cost=12 terlalu tinggi untuk load test. Turunkan jadi cost=4 untuk dev/test:

```python
# app/core/security.py
from passlib.context import CryptContext

# BEFORE (default cost=12, ~300-500ms)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# AFTER (cost=4, ~10-20ms) - 15x LEBIH CEPAT
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__default_rounds=4  # Untuk DEV/TEST saja!
)
```

**Impact:** 250ms → 15ms per hash = **16x lebih cepat**

### **Solusi 2: Perbesar Thread Pool**

```python
# app/core/config.py
import os
from concurrent.futures import ThreadPoolExecutor

# Custom thread pool untuk blocking operations
THREAD_POOL_SIZE = int(os.getenv("THREAD_POOL_SIZE", "100"))
executor = ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE)
```

Modifikasi `auth_service.py` untuk gunakan shared executor:
```python
# app/services/auth_service.py
from app.core.config import executor

async def create_user(self, identifier: str, password: str) -> User:
    # ... validation code ...
    
    loop = asyncio.get_running_loop()
    # Gunakan shared executor, bukan default
    hashed_password = await loop.run_in_executor(executor, get_password_hash, password)
```

### **Solusi 3: Request Rate Limiting di Nginx**

Tambahkan di nginx config untuk membatasi burst:

```nginx
# deploy/nginx/docker.dev.conf
http {
    limit_req_zone $binary_remote_addr zone=registration:10m rate=10r/s;
    
    location /api/v1/auth/register {
        limit_req zone=registration burst=20 nodelay;
        # ... proxy pass ...
    }
}
```

### **Solusi 4: Monitoring & Gunicorn Timeout**

Update docker-compose dengan timeout lebih panjang:
```yaml
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --timeout-keep-alive 300 --timeout-graceful-shutdown 10
```

## Implementasi Bertahap

1. **Prioritas 1 (SEGERA):** Turunkan bcrypt cost ke 4
2. **Prioritas 2:** Perbesar thread pool ke 100
3. **Prioritas 3:** Restart container dengan `docker-compose down && docker-compose up -d --build`
4. **Prioritas 4:** Re-run load test

## Ekspektasi Hasil

Setelah implementasi:
- **502 Error:** 10,369 → <100 (99% reduction)
- **Response Time:** 500-5000ms → 50-200ms
- **Throughput:** 20 req/s → 150+ req/s

## Catatan Penting

⚠️ **bcrypt cost=4 HANYA untuk DEV/TEST**  
Untuk production, gunakan cost=10-12 dan skalakan horizontal (lebih banyak worker/server).
