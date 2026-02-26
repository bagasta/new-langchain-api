# 🤖 Agent Tools — Dokumentasi

Kategori ini mencakup semua tools untuk membuat, mengelola, dan mengkonfigurasi AI Agent.

> 📁 Bagian dari [MCP Server Documentation](../README.md)

---

## Daftar Tools

| Tool | Deskripsi Singkat |
|---|---|
| [`create_agent`](#create_agent) | Buat AI agent baru |
| [`list_agents`](#list_agents) | Daftar semua agent milik user |
| [`get_agent`](#get_agent) | Detail agent tertentu |
| [`update_agent`](#update_agent) | Update informasi dan tools agent |
| [`update_agent_mcp_servers`](#update_agent_mcp_servers) | Update koneksi MCP server agent |
| [`delete_agent`](#delete_agent) | Hapus agent permanen |

---

## `create_agent`

**Buat AI agent baru dengan konfigurasi lengkap.**

Setelah agent berhasil dibuat, **API key agent otomatis di-generate** (auto-publish) dan dikembalikan dalam response sebagai `jwt_token`.

### Parameter

| Parameter | Tipe | Wajib | Default | Deskripsi |
|---|---|---|---|---|
| `user_id` | `str` | ✅ Ya | — | UUID user pemilik agent |
| `name` | `str` | ✅ Ya | — | Nama agent (1-255 karakter) |
| `system_prompt` | `str` | ❌ Tidak | `""` | System prompt / instruksi untuk agent |
| `llm_model` | `str` | ❌ Tidak | `"gpt-4o-mini"` | Nama LLM model yang digunakan |
| `temperature` | `float` | ❌ Tidak | `0.7` | Temperature LLM (0.0 – 2.0) |
| `max_tokens` | `int` | ❌ Tidak | `1000` | Maksimum output tokens |
| `tools` | `list` | ❌ Tidak | `null` | Daftar nama tool yang terdaftar di DB |
| `google_tools` | `list` | ❌ Tidak | `null` | Daftar nama Google tools |
| `allowed_tools` | `list` | ❌ Tidak | `null` | Daftar nama MCP/external tools |
| `token_limit` | `int` | ❌ Tidak | `4000000` | Budget maksimum token untuk agent ini |

### LLM Model yang Tersedia

| Model | Keterangan |
|---|---|
| `gpt-4o-mini` | Default — cepat dan hemat |
| `gpt-4o` | Lebih powerful, lebih mahal |
| `gpt-4-turbo` | Versi turbo GPT-4 |
| `claude-3-5-sonnet` | Anthropic Sonnet |
| `gemini-1.5-pro` | Google Gemini Pro |

### Response Sukses

```json
{
  "status": "success",
  "agent_id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "Customer Support Bot",
  "config": {
    "llm_model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1000,
    "system_prompt": "Kamu adalah asisten customer support..."
  },
  "token_limit": 4000000,
  "created_at": "2026-02-26T11:57:24",
  "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Contoh Penggunaan

```python
result = await create_agent(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    name="WhatsApp Customer Support",
    system_prompt="Kamu adalah asisten customer support yang ramah dan membantu.",
    llm_model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1000,
    google_tools=["gmail_send_message"],
    allowed_tools=["web_search"]
)

agent = json.loads(result)
print(f"Agent ID: {agent['agent_id']}")
print(f"Test di: wa.me/6288809133839/?text=/connect%20{agent['agent_id']}")
```

---

## `list_agents`

**Tampilkan daftar semua agent milik user.**

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `user_id` | `str` | ✅ Ya | UUID user |

### Response Sukses

```json
{
  "status": "success",
  "agents": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Customer Support Bot",
      "status": "active",
      "config": {
        "llm_model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1000,
        "system_prompt": "Kamu adalah asisten..."
      },
      "token_limit": 4000000,
      "tokens_used": 12500,
      "allowed_tools": ["web_search", "gmail_send_message"],
      "created_at": "2026-02-26T11:57:24"
    }
  ]
}
```

### Status Agent

| Status | Arti |
|---|---|
| `active` | Agent aktif dan siap digunakan |
| `inactive` | Agent dinonaktifkan sementara |
| `suspended` | Agent diblokir karena melampaui limit |

### Contoh Penggunaan

```python
result = await list_agents(user_id="550e8400-e29b-41d4-a716-446655440000")
agents = json.loads(result)["agents"]
for agent in agents:
    print(f"- {agent['name']} ({agent['id']}): {agent['status']}")
```

---

## `get_agent`

**Dapatkan detail lengkap dari agent tertentu.**

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `agent_id` | `str` | ✅ Ya | UUID agent |
| `user_id` | `str` | ✅ Ya | UUID user pemilik (untuk otorisasi) |

### Response Sukses

```json
{
  "status": "success",
  "agent": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "Customer Support Bot",
    "status": "active",
    "config": {
      "llm_model": "gpt-4o-mini",
      "temperature": 0.7,
      "max_tokens": 1000,
      "system_prompt": "Kamu adalah asisten customer support..."
    },
    "mcp_servers": {
      "calculator_sse": {
        "url": "http://194.238.23.242:8190/sse",
        "transport": "sse"
      }
    },
    "allowed_tools": ["web_search", "gmail_send_message"],
    "token_limit": 4000000,
    "tokens_used": 12500,
    "created_at": "2026-02-26T11:57:24",
    "updated_at": "2026-02-26T12:30:00"
  }
}
```

### Contoh Penggunaan

```python
result = await get_agent(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000"
)
agent = json.loads(result)["agent"]
print(f"System Prompt: {agent['config']['system_prompt']}")
```

---

## `update_agent`

**Update informasi dasar dan tool assignment agent.**

> ⚠️ **Batasan**: Hanya field berikut yang bisa diubah via tool ini: `name`, `system_prompt`, `google_tools`, `allowed_tools`. Field sensitif seperti `llm_model`, `temperature`, `max_tokens`, `token_limit`, dan `status` **tidak** bisa diubah di sini.

### Parameter

| Parameter | Tipe | Wajib | Default | Deskripsi |
|---|---|---|---|---|
| `agent_id` | `str` | ✅ Ya | — | UUID agent yang akan diupdate |
| `user_id` | `str` | ✅ Ya | — | UUID user pemilik |
| `name` | `str` | ❌ Tidak | `""` | Nama baru (kosongkan untuk mempertahankan) |
| `system_prompt` | `str` | ❌ Tidak | `""` | Instruksi baru (kosongkan untuk mempertahankan) |
| `google_tools` | `list\|null` | ❌ Tidak | `null` | Daftar Google tools baru; `[]` untuk hapus semua; `null` untuk tidak ubah |
| `allowed_tools` | `list\|null` | ❌ Tidak | `null` | Daftar MCP tools baru; `[]` untuk hapus semua; `null` untuk tidak ubah |

### Perilaku Update Tools

| Input | Efek |
|---|---|
| `["tool_a", "tool_b"]` | Ganti semua tools dengan daftar baru |
| `[]` (empty list) | Hapus semua tools |
| `null` atau tidak di-pass | Pertahankan tools yang ada |

### Response Sukses

```json
{
  "status": "success",
  "agent": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "Updated Bot Name",
    "system_prompt": "System prompt yang baru...",
    "google_tools": ["gmail_send_message"],
    "allowed_tools": ["web_search", "gmail_send_message"],
    "updated_at": "2026-02-26T12:30:00"
  }
}
```

> ⚠️ **Catatan Implementasi**: Field `google_tools` dalam response **bukan field DB terpisah** — ia di-compute secara dinamis dari `allowed_tools` dengan cara memfilter tool yang **tidak** memiliki prefix `web_`, `fetch_`, `deep_`, atau `docx_`. Artinya `allowed_tools` menyimpan SEMUA tools (termasuk Google tools). Saat melakukan `update_agent` dengan `google_tools`, tools tersebut di-merge ke dalam `allowed_tools`.

### Contoh Penggunaan

```python
# Update hanya system prompt
result = await update_agent(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    system_prompt="Kamu adalah asisten yang ditingkatkan dengan kemampuan analisa..."
)

# Update nama dan tambahkan Google Calendar
result = await update_agent(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    name="Smart Calendar Assistant",
    google_tools=["gmail_send_message", "google_calendar_create_event"]
)
```

---

## `update_agent_mcp_servers`

**Tambahkan atau update koneksi MCP server eksternal untuk agent.**

Tool ini **merge** server baru dengan yang sudah ada — server yang tidak disebutkan tetap dipertahankan. Untuk menghapus server, panggil tool ini dengan dict lengkap yang tidak menyertakan server yang ingin dihapus.

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `agent_id` | `str` | ✅ Ya | UUID agent |
| `user_id` | `str` | ✅ Ya | UUID user pemilik |
| `mcp_servers` | `dict` | ✅ Ya | Dict berisi konfigurasi MCP server (lihat format di bawah) |

### Format MCP Server Config

```json
{
  "<alias>": {
    "url": "http://<host>:<port>/sse",
    "transport": "sse",
    "env": {},
    "args": [],
    "headers": {}
  }
}
```

| Field | Wajib | Tipe | Deskripsi |
|---|---|---|---|
| `url` | Untuk SSE | `str` | URL endpoint SSE/streamable HTTP |
| `transport` | ✅ Ya | `str` | `"sse"`, `"streamable_http"`, atau `"stdio"` |
| `env` | ❌ Tidak | `dict` | Environment variables opsional |
| `args` | ❌ Tidak | `list` | Argumen opsional (untuk stdio) |
| `headers` | ❌ Tidak | `dict` | HTTP headers opsional |

### Response Sukses

```json
{
  "status": "success",
  "agent_id": "660e8400-e29b-41d4-a716-446655440001",
  "mcp_servers": {
    "calculator_sse": {
      "url": "http://194.238.23.242:8190/sse",
      "transport": "sse",
      "env": {},
      "args": [],
      "headers": {}
    }
  }
}
```

### Contoh Penggunaan

```python
# Tambahkan MCP server kalkulator
result = await update_agent_mcp_servers(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    mcp_servers={
        "calculator_sse": {
            "url": "http://194.238.23.242:8190/sse",
            "transport": "sse",
            "env": {},
            "args": [],
            "headers": {}
        }
    }
)

# Tambahkan STDIO server
result = await update_agent_mcp_servers(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    mcp_servers={
        "python_runner": {
            "command": "python",
            "transport": "stdio",
            "args": ["/path/to/mcp_script.py"]
        }
    }
)
```

---

## `delete_agent`

**Hapus agent secara permanen beserta semua data terkait.**

> ⚠️ **Peringatan**: Tindakan ini tidak bisa dibatalkan! Semua history eksekusi, dokumen yang di-upload, dan konfigurasi agent akan dihapus permanen.

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `agent_id` | `str` | ✅ Ya | UUID agent yang akan dihapus |
| `user_id` | `str` | ✅ Ya | UUID user pemilik (untuk otorisasi) |

### Response Sukses

```json
{
  "status": "success",
  "message": "Agent deleted"
}
```

### Response Error

```json
{
  "status": "error",
  "error": "Agent not found or not authorized"
}
```

### Contoh Penggunaan

```python
result = await delete_agent(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000"
)
print(json.loads(result)["message"])  # "Agent deleted"
```

---

## Alur Kerja Lengkap: Membuat Agent Baru

```mermaid
flowchart TD
    A[login_user] --> B[Dapatkan user_id & access_token]
    B --> C[create_agent dengan konfigurasi]
    C --> D[Dapatkan agent_id & jwt_token]
    D --> E{Perlu Google Tools?}
    E -- Ya --> F[auth_me dengan access_token]
    F --> G{auth_required?}
    G -- Ya --> H[Kirim auth_url ke user]
    H --> I[User login Google]
    G -- Tidak --> J[Agent siap digunakan]
    I --> J
    E -- Tidak --> J
    J --> K[Link: wa.me/6288809133839/?text=/connect%20{agent_id}]
```

---

*← Kembali ke [MCP Server Documentation](../README.md)*
