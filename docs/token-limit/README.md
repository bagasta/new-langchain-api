# 📊 Token Limit Feature

Dokumentasi fitur token limit management untuk mengontrol penggunaan token per agent.

> 📁 Bagian dari [Documentation Index](../README.md)

---

## 📄 File dalam Folder Ini

| File | Deskripsi |
|---|---|
| [`TOKEN_LIMIT_FEATURE.md`](./TOKEN_LIMIT_FEATURE.md) | Overview dan cara kerja fitur token limit |
| [`TOKEN_LIMIT_API_REFERENCE.md`](./TOKEN_LIMIT_API_REFERENCE.md) | API reference untuk token limit endpoints |
| [`TOKEN_LIMIT_IMPLEMENTATION.md`](./TOKEN_LIMIT_IMPLEMENTATION.md) | Detail implementasi teknis |
| [`TOKEN_LIMIT_VISUAL_FLOW.md`](./TOKEN_LIMIT_VISUAL_FLOW.md) | Visual flow diagram token management |

---

## 💡 Tentang Token Limit

Setiap agent memiliki `token_limit` yang membatasi total token yang bisa digunakan. Saat `tokens_used` mencapai `token_limit`, agent akan menolak eksekusi baru.

```
token_limit = 4,000,000  (default)
tokens_used = 0          (awal)
```

Default limit saat `create_agent`: **4.000.000 tokens**.

---

*← Kembali ke [Documentation Index](../README.md)*
