# 💰 Analisis Biaya Token & Rekomendasi Plan

> Dokumen ini berisi perhitungan biaya token GPT-4o-mini dan rekomendasi token limit
> untuk setiap pricing plan di project Langchain API.
>
> **Dibuat**: 4 Maret 2026  
> **Terakhir diupdate**: 4 Maret 2026

---

## ⚙️ Konfigurasi Default Saat Ini

| Parameter | Nilai | Lokasi Kode |
|-----------|-------|-------------|
| Default token limit | `4.000.000` | `app/services/agent_service.py:52` |
| Model default | `gpt-4o-mini` | `app/services/execution_service.py:286` |
| Estimasi token/pesan | `2.000 token` | `app/schemas/agent.py:254` |

---

## 📐 Dasar Perhitungan Biaya

### Harga GPT-4o-mini (OpenAI, 2025)

| Tipe | Harga |
|------|-------|
| Input token | $0.15 / 1 juta token |
| Output token | $0.60 / 1 juta token |

### Asumsi Percakapan Normal (70% input / 30% output)

```
Per 1 juta token:
  Input  : 700.000 × $0.15/1M = $0.105
  Output : 300.000 × $0.60/1M = $0.180
  ─────────────────────────────────────
  Total  :                       $0.285 / 1 juta token
```

### Konversi ke Rupiah

```
Kurs           : Rp 16.300 / USD
Biaya per 1M   : $0.285 × Rp 16.300 = Rp 4.646 / 1 juta token
```

> ⚠️ **Catatan**: Kurs perlu diupdate berkala. Margin sudah cukup besar sehingga
> fluktuasi kurs kecil tidak terlalu berpengaruh.

---

## 🎯 Rekomendasi Token Limit per Plan

### Ringkasan

| Plan | Harga Jual | Token Limit | Setara Pesan | Modal Token | Profit | Margin |
|------|-----------|------------|--------------|-------------|--------|--------|
| **Gratis** | Rp 0 / 2 minggu | 500.000 | ~250 pesan | Rp 2.323 | -Rp 2.323 | — |
| **Economy** | Rp 200.000 / bulan | 4.000.000 | ~2.000 pesan | Rp 18.584 | **Rp 181.416** | **90,7%** |
| **Profesional** | Rp 880.000 / bulan | 15.000.000 | ~7.500 pesan | Rp 69.690 | **Rp 810.310** | **92,1%** |

---

### 🆓 Gratis — 500.000 Token

```
Token limit     : 500.000
Setara pesan    : 500.000 ÷ 2.000 = 250 percakapan
Durasi          : 14 hari
Pesan per hari  : ~18 pesan/hari

Modal token     : 500.000 ÷ 1.000.000 × Rp 4.646 = Rp 2.323 / user
```

**Tujuan Strategis:**
- Cukup untuk eksplorasi dan demo produk
- Tidak cukup untuk production use → mendorong upgrade ke Economy
- Jika 100 user trial aktif sekaligus → modal Rp 232.300/bulan

---

### 💼 Economy — 4.000.000 Token (Rp 200.000/bulan)

```
Token limit     : 4.000.000
Setara pesan    : 4.000.000 ÷ 2.000 = 2.000 percakapan/bulan
Pesan per hari  : ~67 pesan/hari

Modal token     : 4.000.000 ÷ 1.000.000 × Rp 4.646 = Rp 18.584 / user / bulan
Harga jual      : Rp 200.000
────────────────────────────────────────────────────────────────
Profit bersih   : Rp 200.000 - Rp 18.584 = Rp 181.416
Margin          : 90,7%
```

**Cocok untuk**: Individu atau UKM yang butuh 1 agent AI untuk kebutuhan sehari-hari.

---

### 🚀 Profesional — 15.000.000 Token (Rp 880.000/bulan)

```
Token limit     : 15.000.000
Setara pesan    : 15.000.000 ÷ 2.000 = 7.500 percakapan/bulan
Pesan per hari  : ~250 pesan/hari

Modal token     : 15.000.000 ÷ 1.000.000 × Rp 4.646 = Rp 69.690 / user / bulan
Harga jual      : Rp 880.000
────────────────────────────────────────────────────────────────
Profit bersih   : Rp 880.000 - Rp 69.690 = Rp 810.310
Margin          : 92,1%
```

**Cocok untuk**: Bisnis aktif dengan traffic tinggi, integrasi WhatsApp, dan full MCP tools.

---

## 📈 Proyeksi Revenue

| Skenario | User Economy | User Profesional | Revenue | Modal Token | **Profit Bersih** |
|----------|-------------|-----------------|---------|-------------|-------------------|
| Kecil    | 20          | 5               | Rp 8.400.000 | Rp 719.400 | **Rp 7.680.600** |
| Menengah | 50          | 15              | Rp 23.200.000 | Rp 1.974.000 | **Rp 21.226.000** |
| Besar    | 150         | 50              | Rp 74.000.000 | Rp 6.312.000 | **Rp 67.688.000** |

> Proyeksi di atas belum memperhitungkan biaya server, infrastruktur, support, dll.

---

## 🛠️ Implementasi di Kode

### Konstanta Token Limit (Rekomendasi)

Tambahkan/ubah di `app/services/agent_service.py`:

```python
# Token limit per plan (dalam token)
TOKEN_LIMITS_BY_PLAN = {
    "TRIAL":        500_000,     # Gratis - ~250 pesan / 2 minggu
    "GUEST":        500_000,     # Same as trial
    "ECONOMY":    4_000_000,     # ~2.000 pesan / bulan
    "PROFESSIONAL": 15_000_000,  # ~7.500 pesan / bulan
    "ENTERPRISE":   None,        # Unlimited
}
```

### Warning Threshold (Rekomendasi)

Kirim notifikasi ke user saat token tersisa **20%**:

| Plan | Total Token | Notifikasi di |
|------|------------|--------------|
| Gratis | 500.000 | 100.000 tersisa |
| Economy | 4.000.000 | 800.000 tersisa |
| Profesional | 15.000.000 | 3.000.000 tersisa |

### Reset Token Bulanan

Token Economy & Profesional perlu di-reset setiap bulan saat renewal.
Tambahkan job scheduler (cron/celery) untuk reset `tokens_used = 0` pada tanggal billing.

---

## 💡 Fitur Tambahan yang Disarankan

| Fitur | Deskripsi | Harga Saran |
|-------|-----------|-------------|
| **Top-up Token** | Beli token ekstra di luar paket | Rp 7.000 / 1 juta token (margin ~33%) |
| **Token Rollover** | Sisa token bulan lalu tidak hangus (maks 1 bulan) | Bonus loyalty untuk user lama |
| **Usage Alert** | Notifikasi email/WA saat 80% terpakai | — |
| **Token Analytics** | Dashboard grafik pemakaian token per hari | — |

---

## 📅 Log Perubahan

| Tanggal | Perubahan | Oleh |
|---------|-----------|------|
| 2026-03-04 | Dokumen dibuat | Strategy review |

---

*Dokumen ini harus diupdate jika ada perubahan harga model OpenAI atau perubahan pricing plan.*
