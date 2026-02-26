# ⚡ Execution Tools — Dokumentasi

Kategori ini mencakup tools untuk menjalankan AI agent, mengambil riwayat eksekusi, mendapatkan statistik, dan membatalkan eksekusi.

> 📁 Bagian dari [MCP Server Documentation](../README.md)

---

## Daftar Tools

| Tool | Deskripsi Singkat |
|---|---|
| [`execute_agent`](#execute_agent) | Jalankan agent dengan query |
| [`get_execution_history`](#get_execution_history) | Riwayat eksekusi agent |
| [`get_execution_stats`](#get_execution_stats) | Statistik eksekusi user |
| [`cancel_execution`](#cancel_execution) | Batalkan eksekusi yang berjalan |

---

## `execute_agent`

**Jalankan AI Agent dengan query/pertanyaan tertentu.**

Ini adalah tool utama untuk berinteraksi dengan agent. Agent akan memproses query, menggunakan tools yang dikonfigurasi, dan mengembalikan respons teks.

### Parameter

| Parameter | Tipe | Wajib | Default | Deskripsi |
|---|---|---|---|---|
| `query` | `str` | ✅ Ya | — | Pertanyaan atau instruksi untuk agent |
| `agent_id` | `str` | ✅ Ya | — | UUID agent yang akan dijalankan |
| `user_id` | `str` | ✅ Ya | — | UUID user pemilik (untuk otorisasi & kuota) |
| `session_id` | `str` | ❌ Tidak | `""` | Session ID untuk kontinuitas percakapan |
| `parameters` | `dict\|str` | ❌ Tidak | `null` | Parameter tambahan opsional (dict atau JSON string) |

### Session ID

Gunakan `session_id` yang sama untuk mempertahankan konteks percakapan antar eksekusi. Tanpa `session_id`, setiap eksekusi dianggap percakapan baru.

### Response — Berhasil dengan Output

```
// Respons berhasil langsung dikembalikan sebagai string teks:
"Halo! Saya dengan senang hati akan membantu Anda dengan pertanyaan tersebut..."
```

> 💡 Response eksekusi yang berhasil adalah **string teks langsung** (bukan JSON), kecuali terjadi error.

### Response — Error dalam Eksekusi

```json
{
  "status": "error",
  "error": "Agent quota exceeded",
  "execution_id": "770e8400-e29b-41d4-a716-446655440002"
}
```

### Response — Selesai Tanpa Output

```json
{
  "status": "completed",
  "execution_id": "770e8400-e29b-41d4-a716-446655440002",
  "message": "Execution completed but produced no output."
}
```

### Contoh Penggunaan

```python
# Eksekusi sederhana
result = await execute_agent(
    query="Apa ibukota Indonesia?",
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000"
)
print(result)  # "Ibukota Indonesia adalah Jakarta..."

# Eksekusi dengan session ID (percakapan berlanjut)
session = "session-abc-12345"

msg1 = await execute_agent(
    query="Halo, nama saya Budi",
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    session_id=session
)

msg2 = await execute_agent(
    query="Siapa nama saya?",
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    session_id=session
)
print(msg2)  # "Nama Anda adalah Budi"
```

### Notes Penting

- **Token Budget**: Eksekusi akan gagal jika `tokens_used` melampaui `token_limit` agent
- **Tool Invocation**: Agent secara otomatis memanggil tools yang dikonfigurasi sesuai kebutuhan
- **Async**: Tool ini adalah async — pastikan dipanggil dengan `await`

---

## `get_execution_history`

**Ambil riwayat semua eksekusi untuk agent tertentu.**

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `agent_id` | `str` | ✅ Ya | UUID agent |
| `user_id` | `str` | ✅ Ya | UUID user pemilik |

### Response Sukses

```json
{
  "status": "success",
  "executions": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "input": {
        "text": "Apa ibukota Indonesia?"
      },
      "output": {
        "output": "Ibukota Indonesia adalah Jakarta...",
        "error": null
      },
      "status": "completed",
      "duration_ms": 1250,
      "error_message": null,
      "created_at": "2026-02-26T11:57:24"
    }
  ]
}
```

### Status Eksekusi

| Status | Arti |
|---|---|
| `pending` | Eksekusi dalam antrian |
| `running` | Sedang berjalan |
| `completed` | Selesai dengan sukses |
| `failed` | Gagal dengan error |
| `cancelled` | Dibatalkan oleh user |

### Contoh Penggunaan

```python
result = await get_execution_history(
    agent_id="660e8400-e29b-41d4-a716-446655440001",
    user_id="550e8400-e29b-41d4-a716-446655440000"
)
history = json.loads(result)["executions"]

for exec in history[-5:]:  # 5 eksekusi terakhir
    print(f"[{exec['created_at']}] Status: {exec['status']}, Durasi: {exec['duration_ms']}ms")
```

---

## `get_execution_stats`

**Dapatkan statistik eksekusi untuk semua agent milik user.**

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `user_id` | `str` | ✅ Ya | UUID user |

### Response Sukses

```json
{
  "status": "success",
  "total_executions": 150,
  "completed": 142,
  "failed": 8,
  "success_rate": 94.67,
  "avg_duration": 1340.5
}
```

### Field Response

| Field | Tipe | Deskripsi |
|---|---|---|
| `total_executions` | `int` | Total semua eksekusi |
| `completed` | `int` | Eksekusi yang berhasil |
| `failed` | `int` | Eksekusi yang gagal |
| `success_rate` | `float` | Persentase keberhasilan (0–100) |
| `avg_duration` | `float` | Rata-rata durasi dalam milidetik |

> 📌 **Catatan Implementasi**: Response menggunakan `**stats` spread dari `ExecutionService.get_execution_stats()`. Field-field di atas adalah yang diharapkan — namun nama field aktual bergantung pada implementasi service.

### Contoh Penggunaan

```python
result = await get_execution_stats(user_id="550e8400-e29b-41d4-a716-446655440000")
stats = json.loads(result)

print(f"Total eksekusi: {stats['total_executions']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Rata-rata durasi: {stats['avg_duration']:.0f}ms")
```

---

## `cancel_execution`

**Batalkan eksekusi yang sedang berjalan atau dalam antrian.**

> 💡 Hanya eksekusi dengan status `pending` atau `running` yang bisa dibatalkan.

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `execution_id` | `str` | ✅ Ya | UUID eksekusi yang akan dibatalkan |
| `user_id` | `str` | ✅ Ya | UUID user pemilik |

### Response Sukses

```json
{
  "status": "success",
  "execution_id": "770e8400-e29b-41d4-a716-446655440002",
  "execution_status": "cancelled",
  "message": "Execution cancelled"
}
```

### Response Error — Tidak Bisa Dibatalkan

```json
{
  "status": "error",
  "error": "Execution already completed and cannot be cancelled"
}
```

### Contoh Penggunaan

```python
result = await cancel_execution(
    execution_id="770e8400-e29b-41d4-a716-446655440002",
    user_id="550e8400-e29b-41d4-a716-446655440000"
)
data = json.loads(result)
print(f"Status sekarang: {data['execution_status']}")
```

---

## Diagram Siklus Hidup Eksekusi

```
                ┌─────────┐
                │ pending │  ← execute_agent() dipanggil
                └────┬────┘
                     │
                     ↓
                ┌─────────┐
         ┌──────│ running │──────────────────────┐
         │      └────┬────┘                      │
         │           │                           │
     cancel      selesai                      error
         │           │                           │
         ↓           ↓                           ↓
    ┌───────────┐  ┌───────────┐         ┌──────────┐
    │ cancelled │  │ completed │         │  failed  │
    └───────────┘  └───────────┘         └──────────┘
```

---

*← Kembali ke [MCP Server Documentation](../README.md)*
