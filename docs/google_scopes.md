# Google Tool Scopes

Daftar scope OAuth yang digunakan oleh setiap Google tool di API (berdasarkan `GOOGLE_TOOL_SCOPE_MAP`). Gunakan daftar ini saat meminta izin OAuth (misal lewat `google_tools` pada agen) agar hanya meminta scope yang dibutuhkan.

## Gmail
- `gmail`:  
  - `https://www.googleapis.com/auth/gmail.readonly`  
  - `https://www.googleapis.com/auth/gmail.compose`  
  - `https://www.googleapis.com/auth/gmail.send`  
  - `https://www.googleapis.com/auth/gmail.modify`  
  - `https://www.googleapis.com/auth/gmail.labels`  
  - `https://mail.google.com/`
- `gmail_get_message`: `https://www.googleapis.com/auth/gmail.readonly`
- `gmail_read_messages`: `https://www.googleapis.com/auth/gmail.readonly`
- `gmail_list_messages`: `https://www.googleapis.com/auth/gmail.readonly`
- `gmail_send_message`: `https://www.googleapis.com/auth/gmail.send`
- `gmail_create_draft`: `https://www.googleapis.com/auth/gmail.compose`
- `gmail_get_thread`: `https://www.googleapis.com/auth/gmail.readonly`

## Google Sheets
- `google_sheets`:  
  - `https://www.googleapis.com/auth/spreadsheets.readonly`  
  - `https://www.googleapis.com/auth/spreadsheets`  
  - `https://www.googleapis.com/auth/drive.file`
- `google_sheets_get_values`: `https://www.googleapis.com/auth/spreadsheets.readonly`
- `google_sheets_update_values`:  
  - `https://www.googleapis.com/auth/spreadsheets`  
  - `https://www.googleapis.com/auth/drive.file`
- `google_sheets_create_spreadsheet`:  
  - `https://www.googleapis.com/auth/spreadsheets`  
  - `https://www.googleapis.com/auth/drive.file`
- `google_sheets_list_spreadsheets`: `https://www.googleapis.com/auth/drive.metadata.readonly`

## Google Calendar
- `google_calendar`:  
  - `https://www.googleapis.com/auth/calendar`  
  - `https://www.googleapis.com/auth/calendar.events`  
  - `https://www.googleapis.com/auth/calendar.readonly`
- `google_calendar_list_events`: `https://www.googleapis.com/auth/calendar.readonly`
- `google_calendar_create_event`: `https://www.googleapis.com/auth/calendar.events`
- `google_calendar_get_event`: `https://www.googleapis.com/auth/calendar.readonly`

## Google Docs
- `google_docs`:  
  - `https://www.googleapis.com/auth/documents`  
  - `https://www.googleapis.com/auth/documents.readonly`  
  - `https://www.googleapis.com/auth/drive.file`  
  - `https://www.googleapis.com/auth/drive.metadata.readonly`
- `google_docs_list_documents`: `https://www.googleapis.com/auth/drive.metadata.readonly`
- `google_docs_get_document`:  
  - `https://www.googleapis.com/auth/documents.readonly`  
  - `https://www.googleapis.com/auth/drive.metadata.readonly`
- `google_docs_create_document`:  
  - `https://www.googleapis.com/auth/documents`  
  - `https://www.googleapis.com/auth/drive.file`
- `google_docs_append_text`:  
  - `https://www.googleapis.com/auth/documents`  
  - `https://www.googleapis.com/auth/drive.file`
- `google_docs_update_text`:  
  - `https://www.googleapis.com/auth/documents`  
  - `https://www.googleapis.com/auth/drive.file`
- `google_docs_delete_document`: `https://www.googleapis.com/auth/drive.file`
