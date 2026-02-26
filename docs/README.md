# 📚 Documentation Index — AIStaff Langchain API

Selamat datang di dokumentasi lengkap **AIStaff Langchain API**. Semua dokumentasi telah diorganisir ke dalam folder-folder berdasarkan tema.

---

## 🗂️ Struktur Dokumentasi

```
docs/
├── mcp-server/          # MCP Server — tools untuk AI agent (Claude, dsb.)
│   ├── auth/            # Auth & API Key tools
│   ├── agents/          # Agent management tools
│   ├── execution/       # Execution & monitoring tools
│   ├── documents/       # Document & knowledge base tools
│   ├── tools/           # Tool registry & execution
│   ├── user-management/ # User slot management
│   └── google-auth/     # Google OAuth tools
├── api/                 # REST API reference & examples
├── deployment/          # Panduan deployment
├── google/              # Google OAuth & tools setup
├── token-limit/         # Token limit feature
├── migration/           # Database migration & plan upgrade
├── guides/              # How-to guides & tutorials
├── bugfix/              # Catatan bugfix & perbaikan
└── examples/            # Contoh integrasi
```

---

## 🚀 Mulai Dari Sini

| Jika Anda... | Baca ini |
|---|---|
| Baru pertama kali | [guides/how-to-use.md](./guides/how-to-use.md) |
| Ingin deploy ke server | [deployment/DEPLOYMENT.md](./deployment/DEPLOYMENT.md) |
| Ingin pakai MCP tools | [mcp-server/README.md](./mcp-server/README.md) |
| Ingin setup Google | [google/GOOGLE_AUTH_SETUP.md](./google/GOOGLE_AUTH_SETUP.md) |
| Butuh REST API reference | [api/API_GUIDE.md](./api/API_GUIDE.md) |
| Mau integrasi universal | [guides/integration-universal.md](./guides/integration-universal.md) |

---

## 📂 Folder Overview

### 🤖 [mcp-server/](./mcp-server/README.md)
Dokumentasi lengkap MCP Server yang mengekspos seluruh Langchain API sebagai MCP Tools. Cocok untuk integrasi dengan Claude Desktop, n8n, dan AI agent lainnya.

**26 Tools** dalam 7 kategori:
- Auth, Agents, Execution, Documents, Tools, User Management, Google Auth

---

### 🔌 [api/](./api/)
Referensi REST API, contoh curl, dan Postman collection.

| File | Deskripsi |
|---|---|
| `API_GUIDE.md` | Panduan lengkap REST API |
| `API_RESPONSE_EXAMPLES.md` | Contoh response untuk setiap endpoint |
| `CURL_EXAMPLES.md` | Contoh curl command |
| `GOOGLE_OAUTH_CURL_EXAMPLES.md` | Contoh curl untuk Google OAuth |
| `postman_collection.json` | Postman collection siap import |

---

### 🚀 [deployment/](./deployment/)
Panduan deployment ke berbagai environment.

| File | Deskripsi |
|---|---|
| `DEPLOYMENT.md` | Panduan deployment lengkap |
| `how-to-deploy.md` | Quick deploy guide |

---

### 🔑 [google/](./google/)
Setup dan konfigurasi Google OAuth & Tools.

| File | Deskripsi |
|---|---|
| `GOOGLE_AUTH_SETUP.md` | Setup Google OAuth credentials |
| `GOOGLE_AUTH_FRONTEND_INTEGRATION.md` | Integrasi auth di frontend |
| `GOOGLE_TOOLS_TESTING_GUIDE.md` | Panduan testing Google Tools |
| `OAUTH_FLOW_DIAGRAM.md` | Diagram alur OAuth |
| `google_scopes.md` | Referensi Google OAuth scopes |

---

### 📊 [token-limit/](./token-limit/)
Dokumentasi fitur token limit management.

| File | Deskripsi |
|---|---|
| `TOKEN_LIMIT_FEATURE.md` | Overview fitur token limit |
| `TOKEN_LIMIT_API_REFERENCE.md` | API reference token limit |
| `TOKEN_LIMIT_IMPLEMENTATION.md` | Detail implementasi |
| `TOKEN_LIMIT_VISUAL_FLOW.md` | Visual flow diagram |

---

### 🔄 [migration/](./migration/)
Panduan migrasi database dan upgrade plan.

| File | Deskripsi |
|---|---|
| `MIGRATION_FLOW_DIAGRAM.md` | Diagram alur migrasi |
| `TRIAL_MIGRATION.md` | Migrasi ke plan TRIAL |
| `GUEST_TO_TRIAL_UPGRADE.md` | Upgrade dari GUEST ke TRIAL |
| `GUEST_PLAN_CODE.md` | Dokumentasi GUEST plan |

---

### 📖 [guides/](./guides/)
How-to guides dan tutorial lengkap.

| File | Deskripsi |
|---|---|
| `how-to-use.md` | Panduan penggunaan lengkap |
| `integration-universal.md` | Panduan integrasi universal |
| `PROJECT_DOCUMENTATION.md` | Dokumentasi project lengkap |
| `PRD LANGCHAIN API.md` | Product Requirements Document |
| `AGENTS.md` | Panduan khusus agents |
| `CODE_REVIEW_SYSTEM_PROMPT.md` | System prompt untuk code review |

---

### 🐛 [bugfix/](./bugfix/)
Catatan perbaikan bug dan analisis teknis.

| File | Deskripsi |
|---|---|
| `BUGFIX_OAUTH_FLOW.md` | Perbaikan OAuth flow |
| `BEFORE_AFTER_COMPARISON.md` | Perbandingan sebelum/sesudah perbaikan |
| `ANALISIS_PERBAIKAN_GOOGLE_TOOLS.md` | Analisis perbaikan Google Tools |
| `CORS_OPTIONS_400_FIX.md` | Fix CORS OPTIONS 400 error |
| `MCP_CONNECTION_FIX.md` | Fix koneksi MCP server |

---

## 🔗 Quick Links

- **API Base URL**: `https://api.aistaff.com` (atau sesuai deployment)
- **MCP SSE URL**: `http://localhost:8190/sse` (default)
- **WhatsApp Test**: `wa.me/6288809133839/?text=/connect%20{agent_id}`
- **n8n Instance**: `https://n8n.srv651498.hstgr.cloud`

---

*Dokumentasi terakhir diperbarui: 2026-02-26*
