# 🤖 AIStaff MCP Server — Dokumentasi Lengkap

> **Model Context Protocol (MCP) Server** yang mengekspos seluruh endpoint Langchain API sebagai MCP Tools, memungkinkan AI agent seperti Claude Desktop terhubung langsung ke sistem AIStaff.

---

## 📋 Daftar Isi

- [Overview](#overview)
- [Cara Menjalankan](#cara-menjalankan)
- [Konfigurasi Port](#konfigurasi-port)
- [Kategori Tools](#kategori-tools)
- [Dokumentasi Per Kategori](#dokumentasi-per-kategori)

---

## Overview

MCP Server ini adalah **standalone entry-point** yang mengimpor service dan database dari direktori `app/` tanpa memodifikasi file apapun di dalamnya.

Server menggunakan `mcp.server.fastmcp.FastMCP` yang sudah dibundel dengan package `mcp>=1.6`.

### Teknologi
- **Framework MCP**: FastMCP (dari package `mcp>=1.6`)
- **Transport**: stdio (default) atau SSE (Server-Sent Events)
- **Database**: SQLAlchemy SessionLocal
- **Auth**: JWT tokens

---

## Cara Menjalankan

```bash
# Mode stdio (default — untuk Claude Desktop)
python mcp_server.py

# Mode SSE (port default 8190)
python mcp_server.py --sse

# Mode SSE dengan port eksplisit
python mcp_server.py --sse --port 8190

# Mode SSE bind ke semua interface
python mcp_server.py --sse --host 0.0.0.0
```

### Environment Variables

| Variable | Default | Deskripsi |
|---|---|---|
| `MCP_SSE_HOST` | `0.0.0.0` | Host untuk SSE server |
| `MCP_SSE_PORT` | `8190` | Port untuk SSE server |
| `MCP_SSE_URL` | `http://localhost:8190/sse` | URL SSE (di `.env`) |

---

## Konfigurasi Port

| Server | Port Default | Keterangan |
|---|---|---|
| Uvicorn (FastAPI) | `8000` | REST API utama |
| MCP SSE Server | `8190` | MCP tools endpoint |

> ⚠️ **Penting**: Port sengaja dibedakan agar tidak terjadi konflik antara Uvicorn dan MCP server.

---

## Kategori Tools

MCP Server ini menyediakan **26 tools** yang dikelompokkan dalam 7 kategori:

| Kategori | Jumlah Tools | Deskripsi |
|---|---|---|
| [🔐 Auth](./auth/README.md) | 6 tools | Registrasi, login, API key, dan OAuth |
| [🤖 Agents](./agents/README.md) | 6 tools | CRUD agent dan MCP server management |
| [⚡ Execution](./execution/README.md) | 4 tools | Eksekusi agent dan manajemen execution |
| [📄 Documents](./documents/README.md) | 3 tools | Manajemen dokumen yang di-upload ke agent |
| [🛠️ Tools](./tools/README.md) | 5 tools | Manajemen tools dan schema |
| [👤 User Management](./user-management/README.md) | 2 tools | Manajemen slot agent user |
| [🔑 Google Auth](./google-auth/README.md) | 3 tools | Google OAuth flow |

---

## Dokumentasi Per Kategori

| File | Deskripsi |
|---|---|
| [`auth/README.md`](./auth/README.md) | Autentikasi & API Key management |
| [`agents/README.md`](./agents/README.md) | Manajemen AI Agent |
| [`execution/README.md`](./execution/README.md) | Eksekusi & monitoring agent |
| [`documents/README.md`](./documents/README.md) | Upload & manajemen dokumen |
| [`tools/README.md`](./tools/README.md) | Registry & eksekusi tools |
| [`user-management/README.md`](./user-management/README.md) | Manajemen user & slot |
| [`google-auth/README.md`](./google-auth/README.md) | Google OAuth integration |

---

## Format Response

Semua tools mengembalikan **JSON string**. Response sukses selalu menyertakan `"status": "success"`, dan response error menyertakan `"status": "error"` beserta field `"error"` yang berisi pesan kesalahan.

```json
// Contoh sukses
{
  "status": "success",
  "data": { ... }
}

// Contoh error
{
  "status": "error",
  "error": "Invalid user_id: 'abc'"
}
```

---

## ⚙️ Catatan Implementasi Penting

Hasil validasi langsung dari `mcp_server.py`:

| Tool | Catatan Teknis |
|---|---|
| `register_user` | Response `access_token` hanya ada untuk plan `GUEST` dan `TRIAL` |
| `create_agent` | API key agent otomatis di-generate setelah pembuatan (auto-publish) |
| `update_agent` | `google_tools` **bukan** field DB terpisah — disimpan dalam `allowed_tools`, difilter dari prefix tool name |
| `update_agent_mcp_servers` | Melakukan **MERGE** (bukan replace) dengan MCP servers yang sudah ada |
| `execute_agent` | Response sukses adalah **plain string** (bukan JSON), kecuali terjadi error |
| `check_google_auth` | Melakukan **2-pass check**: (1) agent-scoped tokens, (2) user-level tokens sebagai fallback |
| `get_google_auth_url` | Response berupa spread `**result` dari `AuthService.create_google_auth_url()` — key utama: `auth_url` |
| `get_execution_stats` | Response berupa spread `**stats` dari `ExecutionService.get_execution_stats()` |
| `update_user_agent_slots` | Nilai `agent_slots=-1` → unlimited (disimpan sebagai `None` di DB) |

---

*Dibuat: 2026-02-26 | Divalidasi: 2026-02-26 | Versi MCP Server: FastMCP ≥1.6*
