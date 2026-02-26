# 📄 Document Tools — Dokumentasi

Kategori ini mencakup tools untuk mengelola dokumen yang di-upload ke agent. Dokumen ini digunakan sebagai knowledge base untuk agent (RAG - Retrieval Augmented Generation).

> 📁 Bagian dari [MCP Server Documentation](../README.md)

---

## Daftar Tools

| Tool | Deskripsi Singkat |
|---|---|
| [`list_agent_documents`](#list_agent_documents) | Daftar dokumen yang di-upload ke agent |
| [`delete_agent_document`](#delete_agent_document) | Hapus dokumen dan embedding-nya |
| [`get_agent_system_message_history`](#get_agent_system_message_history) | Riwayat perubahan system message agent |

---

## `list_agent_documents`

**Tampilkan semua dokumen yang sudah di-upload ke agent.**

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `agent_id` | `str` | ✅ Ya | UUID agent |
| `user_id` | `str` | ✅ Ya | UUID user pemilik (untuk otorisasi) |

### Response Sukses

```json
{
  "status": "success",
  "uploads": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440003",
      "filename": "product_catalog.pdf",
      "content_type": "application/pdf",
      "size_bytes": 245760,
      "chunk_count": 48,
      "is_deleted": false,
      "created_at": "2026-02-26T10:00:00"
    },
    {
      "id": "880e8400-e29b-41d4-a716-446655440004",
      "filename": "faq.docx",
      "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "size_bytes": 52480,
      "chunk_count": 12,
      "is_deleted": false,
      "created_at": "2026-02-26T10:15:00"
    }
  ]
}
```

### Field Response Detail

| Field | Tipe | Deskripsi |
|---|---|---|
| `id` | `str` | UUID upload |
| `filename` | `str` | Nama file asli |
| `content_type` | `str` | MIME type file |
| `size_bytes` | `int` | Ukuran file dalam bytes |
| `chunk_count` | `int` | Jumlah chunk yang dihasilkan untuk RAG |
| `is_deleted` | `bool` | Apakah sudah dihapus (soft-delete) |
| `created_at` | `str` | Waktu upload |

### Tipe File yang Didukung

| Ekstensi | MIME Type | Keterangan |
|---|---|---|
| `.pdf` | `application/pdf` | PDF dokumen |
| `.docx` | `application/vnd.openxmlformats-...` | Microsoft Word |
| `.txt` | `text/plain` | File teks biasa |
| `.md` | `text/markdown` | Markdown |
| `.csv` | `text/csv` | Spreadsheet CSV |

### Contoh Penggunaan

```python
result = await list_agent_documents(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000"
)
docs = json.loads(result)["uploads"]

total_size = sum(d["size_bytes"] for d in docs)
print(f"Total dokumen: {len(docs)}")
print(f"Total ukuran: {total_size / 1024:.1f} KB")
```

---

## `delete_agent_document`

**Hapus dokumen yang di-upload dan semua embedding-nya.**

> ⚠️ **Perhatian**: Ini menghapus dokumen **dan** semua vector embeddings yang terkait. Agent tidak akan lagi memiliki akses ke konten dokumen tersebut.

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `agent_id` | `str` | ✅ Ya | UUID agent pemilik dokumen |
| `upload_id` | `str` | ✅ Ya | UUID upload yang akan dihapus |
| `user_id` | `str` | ✅ Ya | UUID user (untuk otorisasi) |

### Response Sukses

```json
{
  "status": "success",
  "message": "Document and embeddings deleted",
  "upload_id": "880e8400-e29b-41d4-a716-446655440003"
}
```

### Response Error — Tidak Ditemukan

```json
{
  "status": "error",
  "error": "Upload not found"
}
```

### Contoh Penggunaan

```python
# Hapus dokumen tertentu
result = await delete_agent_document(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    upload_id="880e8400-e29b-41d4-a716-446655440003",
    user_id="550e8400-e29b-41d4-a716-446655440000"
)

data = json.loads(result)
if data["status"] == "success":
    print(f"Dokumen {data['upload_id']} berhasil dihapus")
```

---

## `get_agent_system_message_history`

**Ambil riwayat perubahan system message untuk agent.**

Tool ini berguna untuk melihat evolusi instruksi agent dari waktu ke waktu, memungkinkan rollback manual ke versi sebelumnya jika diperlukan.

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `agent_id` | `str` | ✅ Ya | UUID agent |
| `user_id` | `str` | ✅ Ya | UUID user pemilik (untuk otorisasi) |

### Response Sukses

```json
{
  "status": "success",
  "history": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440005",
      "system_message": "Kamu adalah asisten customer support versi 2.0 yang telah diperbarui...",
      "created_at": "2026-02-26T12:30:00"
    },
    {
      "id": "990e8400-e29b-41d4-a716-446655440006",
      "system_message": "Kamu adalah asisten customer support yang ramah dan membantu.",
      "created_at": "2026-02-26T11:57:24"
    }
  ]
}
```

> 📝 History diurutkan dari **terbaru ke terlama** (descending by `created_at`).

### Contoh Penggunaan

```python
result = await get_agent_system_message_history(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000"
)
history = json.loads(result)["history"]

print(f"Total versi system message: {len(history)}")
print(f"\nVersi terbaru ({history[0]['created_at']}):")
print(history[0]["system_message"][:200] + "...")

if len(history) > 1:
    print(f"\nVersi sebelumnya ({history[1]['created_at']}):")
    print(history[1]["system_message"][:200] + "...")
```

### Use Case: Rollback System Message

```python
# Dapatkan riwayat
history_result = await get_agent_system_message_history(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000"
)
history = json.loads(history_result)["history"]

# Rollback ke versi sebelumnya
old_prompt = history[1]["system_message"]  # versi kedua terakhir
rollback_result = await update_agent(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    system_prompt=old_prompt
)
print("System message berhasil di-rollback!")
```

---

## Cara Upload Dokumen

> 📌 **Catatan**: Upload dokumen ke agent dilakukan melalui **REST API endpoint**, bukan melalui MCP tool. Gunakan endpoint berikut:

```bash
# Upload dokumen ke agent via REST API
curl -X POST "https://api.aistaff.com/api/v1/agents/{agent_id}/upload" \
  -H "Authorization: Bearer {jwt_token}" \
  -F "file=@/path/to/document.pdf"
```

Setelah upload sukses, gunakan `list_agent_documents` untuk memverifikasi dokumen berhasil diproses.

---

*← Kembali ke [MCP Server Documentation](../README.md)*
