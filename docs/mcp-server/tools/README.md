# 🛠️ Tool Management — Dokumentasi

Kategori ini mencakup tools untuk mengelola dan mengeksekusi tools yang tersedia dalam sistem AIStaff.

> 📁 Bagian dari [MCP Server Documentation](../README.md)

---

## Daftar Tools

| Tool | Deskripsi Singkat |
|---|---|
| [`list_tools`](#list_tools) | Daftar semua tools yang tersedia |
| [`get_tool`](#get_tool) | Detail tool berdasarkan ID |
| [`get_tool_schema`](#get_tool_schema) | JSON schema tool (by ID atau nama) |
| [`get_required_scopes`](#get_required_scopes) | OAuth scope yang dibutuhkan tools |
| [`execute_tool`](#execute_tool) | Eksekusi tool langsung |

---

## `list_tools`

**Tampilkan semua tools yang tersedia di sistem, opsional difilter berdasarkan tipe.**

### Parameter

| Parameter | Tipe | Wajib | Default | Deskripsi |
|---|---|---|---|---|
| `tool_type` | `str` | ❌ Tidak | `""` | Filter berdasarkan tipe: `builtin`, `custom`, atau kosong untuk semua |

### Tipe Tool

| Tipe | Deskripsi |
|---|---|
| `builtin` | Tools bawaan sistem yang sudah tersedia by default |
| `custom` | Tools yang dibuat oleh user/admin |

### Response Sukses

```json
{
  "status": "success",
  "tools": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440010",
      "name": "web_search",
      "description": "Search the web for current information",
      "type": "builtin",
      "created_at": "2026-01-01T00:00:00"
    },
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440011",
      "name": "gmail_send_message",
      "description": "Send an email via Gmail",
      "type": "builtin",
      "created_at": "2026-01-01T00:00:00"
    },
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440012",
      "name": "google_sheets_get_values",
      "description": "Read values from Google Sheets",
      "type": "builtin",
      "created_at": "2026-01-01T00:00:00"
    }
  ]
}
```

### Tools yang Tersedia (Reference)

#### Web Tools
| Nama Tool | Deskripsi |
|---|---|
| `web_search` | Pencarian di internet |
| `fetch_webpage` | Ambil konten halaman web |
| `deep_research` | Riset mendalam dengan multiple search |

#### Document Tools
| Nama Tool | Deskripsi |
|---|---|
| `docx_generate` | Generate dokumen Word DOCX |

#### Google Tools
| Nama Tool | Layanan | Scope Diperlukan |
|---|---|---|
| `gmail_send_message` | Gmail | `gmail.send` |
| `gmail_read_messages` | Gmail | `gmail.readonly` |
| `gmail_search_messages` | Gmail | `gmail.readonly` |
| `google_calendar_create_event` | Calendar | `calendar.events` |
| `google_calendar_list_events` | Calendar | `calendar.readonly` |
| `google_sheets_get_values` | Sheets | `spreadsheets.readonly` |
| `google_sheets_update_values` | Sheets | `spreadsheets` |
| `google_drive_list_files` | Drive | `drive.readonly` |
| `google_drive_upload_file` | Drive | `drive.file` |

### Contoh Penggunaan

```python
# Tampilkan semua tools
result = await list_tools()
tools = json.loads(result)["tools"]
print(f"Total tools: {len(tools)}")

# Hanya tools builtin
result = await list_tools(tool_type="builtin")
builtin_tools = json.loads(result)["tools"]

# Hanya tools custom
result = await list_tools(tool_type="custom")
custom_tools = json.loads(result)["tools"]
```

---

## `get_tool`

**Dapatkan detail lengkap dari tool berdasarkan ID-nya.**

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `tool_id` | `str` | ✅ Ya | UUID tool |

### Response Sukses

```json
{
  "status": "success",
  "tool": {
    "id": "aa0e8400-e29b-41d4-a716-446655440010",
    "name": "web_search",
    "description": "Search the web for current information and return relevant results",
    "schema": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query"
        },
        "num_results": {
          "type": "integer",
          "description": "Number of results to return",
          "default": 5
        }
      },
      "required": ["query"]
    },
    "type": "builtin",
    "created_at": "2026-01-01T00:00:00"
  }
}
```

### Contoh Penggunaan

```python
result = await get_tool(tool_id="aa0e8400-e29b-41d4-a716-446655440010")
tool = json.loads(result)["tool"]

print(f"Nama: {tool['name']}")
print(f"Deskripsi: {tool['description']}")
print(f"Schema: {json.dumps(tool['schema'], indent=2)}")
```

---

## `get_tool_schema`

**Dapatkan JSON schema untuk tool berdasarkan ID atau nama.**

Lebih fleksibel dari `get_tool` karena menerima nama tool (string) selain UUID.

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `tool_identifier` | `str` | ✅ Ya | UUID atau nama tool (e.g., `"web_search"`) |

### Response Sukses

```json
{
  "status": "success",
  "schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      }
    },
    "required": ["query"]
  }
}
```

### Contoh Penggunaan

```python
# Via nama tool
result = await get_tool_schema(tool_identifier="web_search")
schema = json.loads(result)["schema"]

# Via UUID
result = await get_tool_schema(tool_identifier="aa0e8400-e29b-41d4-a716-446655440010")
schema = json.loads(result)["schema"]

# Gunakan schema untuk validasi parameter
required_params = schema.get("required", [])
print(f"Parameter wajib: {required_params}")
```

---

## `get_required_scopes`

**Dapatkan OAuth scopes yang dibutuhkan untuk daftar tools tertentu.**

Berguna sebelum memanggil `auth_me` atau `get_google_auth_url` untuk mengetahui scopes apa yang perlu diminta dari Google.

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `tool_names` | `list\|str` | ✅ Ya | Daftar nama tools (e.g., `["gmail_send_message", "google_sheets_get_values"]`) |

### Response Sukses

```json
{
  "status": "success",
  "scopes": [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets.readonly"
  ]
}
```

### Mapping Tool → Scope

| Tool Name | OAuth Scope |
|---|---|
| `gmail_send_message` | `https://www.googleapis.com/auth/gmail.send` |
| `gmail_read_messages` | `https://www.googleapis.com/auth/gmail.readonly` |
| `gmail_search_messages` | `https://www.googleapis.com/auth/gmail.readonly` |
| `google_calendar_create_event` | `https://www.googleapis.com/auth/calendar.events` |
| `google_calendar_list_events` | `https://www.googleapis.com/auth/calendar.readonly` |
| `google_sheets_get_values` | `https://www.googleapis.com/auth/spreadsheets.readonly` |
| `google_sheets_update_values` | `https://www.googleapis.com/auth/spreadsheets` |
| `google_drive_list_files` | `https://www.googleapis.com/auth/drive.readonly` |
| `google_drive_upload_file` | `https://www.googleapis.com/auth/drive.file` |

### Contoh Penggunaan

```python
# Cari tahu scopes yang dibutuhkan sebelum Google Auth
required_tools = ["gmail_send_message", "google_calendar_create_event"]
result = await get_required_scopes(tool_names=required_tools)
scopes = json.loads(result)["scopes"]

print("Scopes yang diperlukan:")
for scope in scopes:
    print(f"  - {scope}")
```

---

## `execute_tool`

**Eksekusi tool secara langsung dengan parameter tertentu.**

Tool ini memungkinkan eksekusi langsung tanpa melalui agent. Berguna untuk testing, debugging, atau automasi sederhana.

### Parameter

| Parameter | Tipe | Wajib | Default | Deskripsi |
|---|---|---|---|---|
| `tool_identifier` | `str` | ✅ Ya | — | UUID atau nama tool |
| `user_id` | `str` | ✅ Ya | — | UUID user (untuk otorisasi) |
| `parameters` | `dict\|str` | ❌ Tidak | `null` | Parameter tool (dict atau JSON string) |
| `agent_id` | `str` | ❌ Tidak | `""` | UUID agent untuk konteks opsional |

### Response Sukses

```json
{
  "status": "success",
  "result": {
    "results": [
      {
        "title": "Contoh Hasil Pencarian",
        "url": "https://example.com",
        "snippet": "Deskripsi singkat hasil pencarian..."
      }
    ]
  }
}
```

### Contoh Penggunaan

```python
# Eksekusi web search
result = await execute_tool(
    tool_identifier="web_search",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    parameters={
        "query": "cuaca Jakarta hari ini",
        "num_results": 3
    }
)
data = json.loads(result)
print(f"Hasil: {json.dumps(data['result'], indent=2, ensure_ascii=False)}")

# Eksekusi dengan konteks agent
result = await execute_tool(
    tool_identifier="gmail_send_message",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    parameters={
        "to": "recipient@example.com",
        "subject": "Test dari AIStaff",
        "body": "Ini adalah email test dari AIStaff agent."
    }
)
```

---

*← Kembali ke [MCP Server Documentation](../README.md)*
