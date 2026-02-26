# 🔑 Google OAuth & Tools

Dokumentasi lengkap setup, konfigurasi, dan testing Google OAuth serta Google Tools.

> 📁 Bagian dari [Documentation Index](../README.md)

---

## 📄 File dalam Folder Ini

| File | Deskripsi |
|---|---|
| [`GOOGLE_AUTH_SETUP.md`](./GOOGLE_AUTH_SETUP.md) | Setup Google OAuth credentials di Google Cloud |
| [`GOOGLE_AUTH_FRONTEND_INTEGRATION.md`](./GOOGLE_AUTH_FRONTEND_INTEGRATION.md) | Integrasi Google Auth di frontend React |
| [`GOOGLE_TOOLS_TESTING_GUIDE.md`](./GOOGLE_TOOLS_TESTING_GUIDE.md) | Panduan testing semua Google Tools |
| [`OAUTH_FLOW_DIAGRAM.md`](./OAUTH_FLOW_DIAGRAM.md) | Diagram alur OAuth dari A ke Z |
| [`google_scopes.md`](./google_scopes.md) | Referensi lengkap Google OAuth scopes |

---

## 🔧 Quick Setup Google OAuth

1. **Buat Google Cloud Project** di [console.cloud.google.com](https://console.cloud.google.com)
2. **Aktifkan APIs**: Gmail API, Calendar API, Sheets API, Drive API
3. **Buat OAuth 2.0 credentials** (Type: Web Application)
4. **Set Redirect URI**: `https://your-api.com/auth/google/callback`
5. **Copy credentials** ke `.env`:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-api.com/auth/google/callback
```

Untuk panduan lengkap, lihat [`GOOGLE_AUTH_SETUP.md`](./GOOGLE_AUTH_SETUP.md).

---

## 🛠️ Google Tools yang Tersedia

| Tool Name | Layanan | Deskripsi |
|---|---|---|
| `gmail_send_message` | Gmail | Kirim email |
| `gmail_read_messages` | Gmail | Baca email |
| `gmail_search_messages` | Gmail | Cari email |
| `google_calendar_create_event` | Calendar | Buat event |
| `google_calendar_list_events` | Calendar | Lihat event |
| `google_sheets_get_values` | Sheets | Baca spreadsheet |
| `google_sheets_update_values` | Sheets | Update spreadsheet |
| `google_drive_list_files` | Drive | List file di Drive |
| `google_drive_upload_file` | Drive | Upload file |

---

*← Kembali ke [Documentation Index](../README.md)*
