# 👤 User Management Tools — Dokumentasi

Kategori ini mencakup tools untuk mengelola slot agent dan resource management untuk user.

> 📁 Bagian dari [MCP Server Documentation](../README.md)

---

## Daftar Tools

| Tool | Deskripsi Singkat |
|---|---|
| [`get_user_agent_slots`](#get_user_agent_slots) | Cek info slot agent milik user |
| [`update_user_agent_slots`](#update_user_agent_slots) | Update jumlah slot agent user (admin) |

---

## `get_user_agent_slots`

**Dapatkan informasi slot agent untuk user tertentu.**

Tool ini menunjukkan berapa banyak agent yang sudah dibuat user, berapa sisa slot yang tersedia, dan plan apa yang aktif.

### Parameter

| Parameter | Tipe | Wajib | Deskripsi |
|---|---|---|---|
| `user_id` | `str` | ✅ Ya | UUID user |

### Response Sukses

```json
{
  "status": "success",
  "total_slots": 5,
  "used_slots": 3,
  "available_slots": 2,
  "plan_code": "PRO_M",
  "is_unlimited": false
}
```

### Response — Unlimited Slots

```json
{
  "status": "success",
  "total_slots": null,
  "used_slots": 10,
  "available_slots": null,
  "plan_code": "PRO_Y",
  "is_unlimited": true
}
```

### Field Response

| Field | Tipe | Deskripsi |
|---|---|---|
| `total_slots` | `int\|null` | Total slot yang diizinkan (`null` = unlimited) |
| `used_slots` | `int` | Jumlah agent yang sudah dibuat |
| `available_slots` | `int\|null` | Sisa slot yang tersedia (`null` = unlimited) |
| `plan_code` | `str` | Kode plan aktif user |
| `is_unlimited` | `bool` | Apakah user memiliki slot unlimited |

### Slot per Plan

| Plan | Jumlah Slot |
|---|---|
| `GUEST` | 1 agent |
| `TRIAL` | 3 agent |
| `PRO_M` | 10 agent |
| `PRO_Y` | Unlimited |

### Contoh Penggunaan

```python
result = await get_user_agent_slots(user_id="550e8400-e29b-41d4-a716-446655440000")
slots = json.loads(result)

if slots["is_unlimited"]:
    print(f"Plan {slots['plan_code']}: Unlimited agents (sudah pakai: {slots['used_slots']})")
elif slots["available_slots"] > 0:
    print(f"Sisa slot: {slots['available_slots']} dari {slots['total_slots']} total")
else:
    print("⚠️ Slot agent habis! Upgrade plan untuk menambah agent.")
```

---

## `update_user_agent_slots`

**Update jumlah slot agent untuk user (aksi admin).**

> ⚠️ **Aksi Admin**: Tool ini dimaksudkan untuk admin sistem. Gunakan dengan hati-hati karena mengubah resource limit user.

### Parameter

| Parameter | Tipe | Wajib | Default | Deskripsi |
|---|---|---|---|---|
| `user_id` | `str` | ✅ Ya | — | UUID user yang slot-nya akan diubah |
| `agent_slots` | `int` | ❌ Tidak | `-1` | Jumlah slot baru (`-1` untuk unlimited) |

### Nilai `agent_slots`

| Nilai | Efek |
|---|---|
| `-1` (default) | Set ke **unlimited** |
| `0` | Blokir pembuatan agent baru |
| `> 0` | Set ke jumlah slot spesifik |

### Response Sukses

```json
{
  "status": "success",
  "total_slots": 10,
  "used_slots": 3,
  "available_slots": 7,
  "is_unlimited": false,
  "message": "Agent slots updated"
}
```

### Response — Set ke Unlimited

```json
{
  "status": "success",
  "total_slots": null,
  "used_slots": 3,
  "available_slots": null,
  "is_unlimited": true,
  "message": "Agent slots updated"
}
```

### Response Error — User Tidak Ditemukan

```json
{
  "status": "error",
  "error": "User not found"
}
```

### Contoh Penggunaan

```python
# Berikan 10 slot ke user
result = await update_user_agent_slots(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    agent_slots=10
)

# Set ke unlimited (upgrade ke enterprise)
result = await update_user_agent_slots(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    agent_slots=-1  # -1 = unlimited
)

# Blokir pembuatan agent baru
result = await update_user_agent_slots(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    agent_slots=0
)

data = json.loads(result)
print(f"Status: {data['message']}")
print(f"Slot tersedia: {data['available_slots'] if not data['is_unlimited'] else 'Unlimited'}")
```

---

## Manajemen Slot: Alur Upgrade

```
User mendekati batas slot
         │
         ↓
  get_user_agent_slots()
  → available_slots = 0
         │
         ↓
   Notifikasi user
"Upgrade plan untuk lebih banyak agent"
         │
         ↓
   Admin konfirmasi
   pembayaran plan baru
         │
         ↓
  update_user_agent_slots()
  agent_slots = (jumlah sesuai plan baru)
         │
         ↓
    User bisa buat
    agent baru lagi ✅
```

---

*← Kembali ke [MCP Server Documentation](../README.md)*
