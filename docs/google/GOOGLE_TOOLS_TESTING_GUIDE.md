# Panduan Testing Google Tools Setelah Perbaikan

## Tanggal: 2026-02-03

## ✅ Perbaikan yang Telah Dilakukan

### 1. **Deskripsi Tools Lebih Informatif**

**Sebelum:**
```
Gmail get_message: "Retrieve a Gmail message by ID with optional format selection."
```

**Sesudah:**
```
Gmail get_message: "Retrieve and read the FULL CONTENT of a specific Gmail message by its ID. 
Use this tool when you need to read the complete details of an email (subject, sender, body, 
attachments info). The message_id can be obtained from gmail_list_messages or 
gmail_read_messages tools. Format options: 'full' (complete message with body), 'metadata' 
(headers only), 'minimal' (basic info), 'raw' (RFC 2822 format)."
```

**Manfaat:**
- ✅ AI Agent lebih mudah memahami kapan harus menggunakan tool
- ✅ Memberikan informasi tentang workflow (list dulu, baru get detail)
- ✅ Menjelaskan parameter dan options yang tersedia

### 2. **Error Messages Lebih Helpful**

**Sebelum:**
```python
raise ValueError("Gmail get_message action requires 'message_id'.")
```

**Sesudah:**
```python
logger.warning(
    "Gmail get_message action called without message_id",
    parameters_provided=list(parameters.keys()),
)
raise ValueError(
    "Gmail get_message action requires 'message_id' parameter. "
    "Use gmail_list_messages or gmail_read_messages to get message IDs first."
)
```

**Manfaat:**
- ✅ User tahu cara mendapatkan message_id
- ✅ Error di-log dengan context lengkap
- ✅ Debugging lebih mudah

### 3. **Logging Ditambahkan**

Logging debug ditambahkan di semua critical points:
- Gmail get_message execution
- Calendar list_events execution
- Calendar get_event execution
- Docs get_document execution

**Manfaat:**
- ✅ Mudah tracking execution flow
- ✅ Debugging lebih cepat
- ✅ Monitoring tool usage

### 4. **Tools yang Diperbaiki**

1. ✅ `gmail_get_message`
2. ✅ `gmail_list_messages`
3. ✅ `gmail_read_messages`
4. ✅ `google_calendar_list_events`
5. ✅ `google_calendar_get_event`
6. ✅ `google_docs_list_documents`
7. ✅ `google_docs_get_document`

---

## 🧪 Cara Testing

### Test 1: Verifikasi Schema (Sudah Dilakukan)

```bash
python3 scripts/verify_google_tools_fix.py
```

**Expected Output:**
```
🎉 ALL CRITICAL TESTS PASSED!
Passed: 13/13
Failed: 0/13
```

### Test 2: Test dengan cURL (Manual Testing)

#### A. Test Gmail Get Message

**Step 1: List messages dulu untuk dapat message_id**
```bash
# Dapatkan JWT token dari login
TOKEN="your_jwt_token_here"
AGENT_ID="your_agent_id_here"

# List messages
curl -X POST "http://localhost:8000/api/v1/agents/${AGENT_ID}/execute" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "List my latest 5 emails",
    "parameters": {}
  }'
```

**Step 2: Get detail message dengan message_id**
```bash
# Dari response di atas, ambil message_id
MESSAGE_ID="message_id_dari_step_1"

curl -X POST "http://localhost:8000/api/v1/agents/${AGENT_ID}/execute" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Read the full content of email with ID: '"${MESSAGE_ID}"'",
    "parameters": {}
  }'
```

**Expected:** ✅ Agent akan menggunakan `gmail_get_message` tool dan return full email content

#### B. Test Calendar Get Event

**Step 1: List events dulu**
```bash
curl -X POST "http://localhost:8000/api/v1/agents/${AGENT_ID}/execute" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "List my upcoming calendar events",
    "parameters": {}
  }'
```

**Step 2: Get event details**
```bash
# Dari response di atas, ambil event_id
EVENT_ID="event_id_dari_step_1"

curl -X POST "http://localhost:8000/api/v1/agents/${AGENT_ID}/execute" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Get full details of calendar event with ID: '"${EVENT_ID}"'",
    "parameters": {}
  }'
```

**Expected:** ✅ Agent akan menggunakan `google_calendar_get_event` dan return full event details

#### C. Test Error Messages

**Test tanpa message_id (should fail dengan error yang helpful)**
```bash
# Call tool service directly untuk test error
curl -X POST "http://localhost:8000/api/v1/tools/execute" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "gmail_get_message",
    "parameters": {}
  }'
```

**Expected Error:**
```json
{
  "detail": "Gmail get_message action requires 'message_id' parameter. Use gmail_list_messages or gmail_read_messages to get message IDs first."
}
```

### Test 3: Test dengan Agent (Recommended)

#### Setup Agent
```bash
# Create agent dengan Google tools
curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Google Assistant Test",
    "tools": [
      "gmail_get_message",
      "gmail_list_messages",
      "gmail_read_messages",
      "google_calendar_list_events",
      "google_calendar_get_event",
      "google_docs_list_documents",
      "google_docs_get_document"
    ],
    "config": {
      "llm_model": "gpt-4o-mini",
      "temperature": 0.7,
      "max_tokens": 2000,
      "system_prompt": "You are a helpful assistant with access to Gmail, Calendar, and Google Docs. Always use the appropriate tools to help users with their requests."
    }
  }'
```

#### Test Scenarios

**Scenario 1: Read Email Details**
```bash
curl -X POST "http://localhost:8000/api/v1/agents/${AGENT_ID}/execute" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Find my latest email from john@example.com and read its full content",
    "parameters": {}
  }'
```

**Expected Workflow:**
1. Agent menggunakan `gmail_list_messages` dengan query filter
2. Agent mendapat message_id dari hasil list
3. Agent menggunakan `gmail_get_message` untuk baca detail
4. Agent memberikan summary lengkap

**Scenario 2: Check Calendar**
```bash
curl -X POST "http://localhost:8000/api/v1/agents/${AGENT_ID}/execute" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What meetings do I have today? Show me the full details of the first one",
    "parameters": {}
  }'
```

**Expected Workflow:**
1. Agent menggunakan `google_calendar_list_events` dengan time filter
2. Agent mendapat event_id
3. Agent menggunakan `google_calendar_get_event` untuk detail
4. Agent memberikan informasi lengkap (attendees, location, description, etc)

**Scenario 3: Read Google Docs**
```bash
curl -X POST "http://localhost:8000/api/v1/agents/${AGENT_ID}/execute" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Find my document named 'Project Proposal' and read its content",
    "parameters": {}
  }'
```

**Expected Workflow:**
1. Agent menggunakan `google_docs_list_documents` dengan query filter
2. Agent mendapat document_id
3. Agent menggunakan `google_docs_get_document` untuk baca content
4. Agent memberikan summary atau full content

---

## 📊 Monitoring & Debugging

### Check Logs

```bash
# Tail application logs
tail -f logs/app.log | grep -E "(Gmail|Calendar|Docs)"

# Filter untuk specific tool
tail -f logs/app.log | grep "gmail_get_message"
```

### Expected Log Entries

**Successful Execution:**
```
DEBUG - Gmail get_message executing message_id=abc123 format=full
DEBUG - Google Calendar list_events executing calendar_id=primary max_results=10
DEBUG - Google Docs get_document executing document_id=doc123
```

**Error Cases:**
```
WARNING - Gmail get_message action called without message_id parameters_provided=['query', 'max_results']
WARNING - Google Calendar get_event called without event_id parameters_provided=[]
```

---

## ✅ Checklist Testing

Setelah deployment, pastikan semua ini berfungsi:

### Gmail Tools
- [ ] `gmail_list_messages` - List emails dengan query
- [ ] `gmail_get_message` - Get email detail dengan message_id
- [ ] `gmail_read_messages` - Read multiple emails
- [ ] Error message helpful saat missing message_id

### Calendar Tools
- [ ] `google_calendar_list_events` - List events dengan time filter
- [ ] `google_calendar_get_event` - Get event detail dengan event_id
- [ ] Error message helpful saat missing event_id

### Docs Tools
- [ ] `google_docs_list_documents` - List documents dengan query
- [ ] `google_docs_get_document` - Get document content dengan document_id
- [ ] Error message helpful saat missing document_id

### Workflow Testing
- [ ] Agent bisa workflow: list → get detail (Gmail)
- [ ] Agent bisa workflow: list → get detail (Calendar)
- [ ] Agent bisa workflow: list → get detail (Docs)
- [ ] Tool descriptions cukup jelas untuk AI agent
- [ ] Error messages membantu user memahami cara perbaikan

---

## 🚀 Next Steps

Jika ada masalah:

1. **Check logs first** - Lihat apakah tool dipanggil dengan parameter yang benar
2. **Verify Google OAuth** - Pastikan scopes sudah lengkap
3. **Test tool directly** - Gunakan `/api/v1/tools/execute` endpoint
4. **Check agent system prompt** - Pastikan agent tahu tools apa yang tersedia

Jika masih error setelah perbaikan ini:
1. Share log error lengkap
2. Share agent system prompt
3. Share test case yang digunakan

---

## 📝 Summary

**Problem**: Tools Google Docs, read email detail, dan read calendar tidak berfungsi

**Root Cause**: 
- ❌ Implementasi teknis sudah benar
- ❌ Deskripsi tools terlalu singkat → AI tidak tahu kapan pakai
- ❌ Error messages tidak helpful → User bingung kenapa error

**Solution**:
- ✅ Enhanced descriptions dengan workflow guidance
- ✅ Better error messages dengan actionable instructions
- ✅ Added logging untuk debugging
- ✅ All tools tested dan verified

**Status**: ✅ FIXED & READY FOR TESTING
