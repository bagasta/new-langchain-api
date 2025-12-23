# Panduan Optimasi Nginx untuk Skala Ribuan User

Dokumen ini berisi konfigurasi Nginx yang dioptimalkan untuk menangani beban trafik tinggi (High Concurrency) pada LangChain API.

## 1. Konfigurasi Inti (`nginx.conf`)

Ubah file `/etc/nginx/nginx.conf` dengan parameter berikut untuk memaksimalkan throughput dan mencegah bottleneck di level web server.

```nginx
user nginx;
# Auto detect jumlah CPU core.
# Jika server punya 8 core, ini akan spawn 8 worker process.
worker_processes auto;

# Meningkatkan limit file descriptor (perlu disesuaikan juga di OS level `ulimit -n`)
worker_rlimit_nofile 65535;

events {
    # Menggunakan epoll (Linux) untuk efisiensi tinggi
    use epoll;
    
    # Jumlah koneksi simultan per worker. 
    # Total koneksi max = worker_processes * worker_connections
    worker_connections 10240;
    
    # Menerima banyak koneksi baru sekaligus
    multi_accept on;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Optimasi I/O Disk
    sendfile        on;
    tcp_nopush      on; # Mengirim header HTTP dalam satu paket
    tcp_nodelay     on; # Jangan buffer data, kirim secepatnya (bagus untuk API)

    # Keepalive connections
    # Menjaga koneksi tetap terbuka untuk request beruntun dari client yang sama
    keepalive_timeout  65;
    keepalive_requests 1000;

    # Buffer Sizes (Penting untuk upload file/payload besar)
    client_body_buffer_size 128k;
    client_max_body_size 10M; # Sesuaikan dengan max ukuran dokumen upload
    client_header_buffer_size 1k;
    large_client_header_buffers 4 4k;
    output_buffers 1 32k;
    postpone_output 1460;

    # Timeouts (Mencegah koneksi menggantung)
    client_header_timeout 12;
    client_body_timeout 12;
    send_timeout 10;

    # Gzip Compression (Menghemat bandwidth)
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Caching File Descriptor (Untuk file statis/aset)
    open_file_cache max=200000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    # Load Balancing Upstream
    upstream backend_api {
        # Least Connection: Mengirim request ke server dengan koneksi aktif paling sedikit
        least_conn;
        
        # Daftar server aplikasi (Uvicorn Workers)
        server 127.0.0.1:8001;
        server 127.0.0.1:8002;
        server 127.0.0.1:8003;
        server 127.0.0.1:8004;
        
        # Keepalive ke upstream (aplikasi)
        keepalive 64;
    }

    server {
        listen 80;
        server_name api.langchain.local;

        location / {
            proxy_pass http://backend_api;
            
            # Header forwarding
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # HTTP 1.1 diperlukan untuk keepalive
            proxy_http_version 1.1;
            proxy_set_header Connection "";

            # Timeouts untuk Long-Running Requests (Agent Execution)
            # Penting: Sesuaikan dengan durasi maksimal eksekusi agen Anda
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 300s; # 5 Menit untuk menunggu respons LLM
        }
    }
}
```

## 2. Tuning OS (Linux Kernel)

Nginx tidak bisa bekerja maksimal jika dibatasi oleh OS. Tambahkan konfigurasi ini di `/etc/sysctl.conf`:

```bash
# Meningkatkan range port ephemeral (untuk koneksi keluar yang banyak)
net.ipv4.ip_local_port_range = 1024 65535

# Reuse sockets dalam status TIME_WAIT
net.ipv4.tcp_tw_reuse = 1

# Meningkatkan backlog queue (antrian koneksi masuk)
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535

# Meningkatkan limit file descriptor global
fs.file-max = 2097152
```

Jalankan `sysctl -p` untuk menerapkan perubahan.

## 3. Checklist Deployment
1.  [ ] Pastikan jumlah `worker_processes` sesuai dengan jumlah core CPU server.
2.  [ ] Pastikan `ulimit -n` user nginx minimal 65535.
3.  [ ] Gunakan Load Balancer di depan Nginx jika menggunakan multiple server (Horizontal Scaling).
