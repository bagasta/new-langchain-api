# 🔌 API Reference

Koleksi referensi REST API, contoh curl, dan Postman collection untuk AIStaff Langchain API.

> 📁 Bagian dari [Documentation Index](../README.md)

---

## 📄 File dalam Folder Ini

| File | Deskripsi |
|---|---|
| [`API_GUIDE.md`](./API_GUIDE.md) | Panduan lengkap semua REST endpoint |
| [`API_RESPONSE_EXAMPLES.md`](./API_RESPONSE_EXAMPLES.md) | Contoh response JSON untuk setiap endpoint |
| [`CURL_EXAMPLES.md`](./CURL_EXAMPLES.md) | Contoh curl command yang siap dipakai |
| [`curl_collection.md`](./curl_collection.md) | Koleksi curl organized by category |
| [`GOOGLE_AUTH_CURL.md`](./GOOGLE_AUTH_CURL.md) | Contoh curl khusus Google Auth flow |
| [`GOOGLE_OAUTH_CURL_EXAMPLES.md`](./GOOGLE_OAUTH_CURL_EXAMPLES.md) | Contoh curl untuk semua Google OAuth endpoint |
| [`postman_collection.json`](./postman_collection.json) | Postman collection JSON (siap import) |

---

## 🚀 Quick Start

### Base URL
```
https://api.aistaff.com/api/v1
```

### Authentication

```bash
# Login untuk dapatkan access token
curl -X POST "https://api.aistaff.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"identifier": "user@example.com", "password": "yourpassword"}'

# Gunakan token di request selanjutnya
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.aistaff.com/api/v1/agents"
```

---

## 📋 Endpoint Categories

| Kategori | Prefix | Deskripsi |
|---|---|---|
| Auth | `/auth/` | Login, register, token management |
| Agents | `/agents/` | CRUD agent |
| Sessions | `/sessions/` | Chat sessions |
| Executions | `/executions/` | Execution history & management |
| Tools | `/tools/` | Tool registry |
| Upload | `/upload/` | Document upload |
| Google | `/auth/google/` | Google OAuth |

---

*← Kembali ke [Documentation Index](../README.md)*
