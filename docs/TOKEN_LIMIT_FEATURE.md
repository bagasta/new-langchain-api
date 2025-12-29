# Token Limit Feature - Implementation Guide

## 📖 Overview

Fitur **Token Limit** memungkinkan setiap agent memiliki batasan penggunaan token. Ketika limit tercapai, agent tidak akan merespons eksekusi baru sampai token limit ditambah atau direset.

## 🔧 Fitur Utama

### 1. **Database Schema**
Menambahkan kolom baru di tabel `agents`:
- `token_limit` - Batasan maksimum token (nullable, `NULL` = unlimited)
- `tokens_used` - Total token yang sudah terpakai
- `token_reset_date` - Tanggal untuk reset token (opsional, untuk future feature)

Menambahkan kolom baru di tabel `executions`:
- `input_tokens` - Token dari input
- `output_tokens` - Token dari output
- `total_tokens` - Total token per eksekusi

### 2. **API Changes**

#### Create Agent
```json
POST /api/v1/agents
{
  "name": "My Agent",
  "token_limit": 100000,  // Optional, null = unlimited
  "config": {...},
  "tools": [...]
}
```

#### Update Agent
```json
PATCH /api/v1/agents/{agent_id}
{
  "token_limit": 200000  // Update token limit
}
```

#### Execute Agent Response
```json
{
  "execution_id": "...",
  "status": "completed",
  "response": "...",
  "tokens_used": 150,
  "tokens_remaining": 99850
}
```

#### Get Agent Response
```json
{
  "id": "...",
  "name": "My Agent",
  "token_limit": 100000,
  "tokens_used": 5420,
  "token_reset_date": null,
  ...
}
```

### 3. **Error Handling**

Ketika token limit tercapai:
```json
HTTP 429 Too Many Requests
{
  "detail": "Agent token limit exceeded. Used: 100000/100000 tokens. Please increase the token limit or reset the agent."
}
```

## 📊 Usage Flow

### Scenario 1: Agent dengan Token Limit
1. User membuat agent dengan `token_limit: 10000`
2. Setiap eksekusi akan:
   - Check apakah `tokens_used < token_limit`
   - Jika tidak, return `HTTP 429`
   - Jika ya, eksekusi dilanjutkan
3. Setelah eksekusi:
   - Hitung token input & output
   - Update `tokens_used` di agent
   - Tracking di execution record

### Scenario 2: Agent Unlimited
1. User membuat agent dengan `token_limit: null`
2. Agent bisa digunakan tanpa batasan
3. Token usage tetap di-track untuk analytics

## 🔄 Migration

Run migration untuk update database schema:

```bash
# Run migration
alembic upgrade head
```

Migration akan:
- Menambahkan kolom `token_limit`, `tokens_used`, `token_reset_date` ke tabel `agents`
- Menambahkan kolom `input_tokens`, `output_tokens`, `total_tokens` ke tabel `executions`
- Membuat index untuk performa optimal

## 📈 Token Estimation

Token dihitung menggunakan `tiktoken` library:
- Estimasi input tokens dari user message
- Estimasi output tokens dari AI response
- Support berbagai model (GPT-3.5, GPT-4, dll)

## 🛠️ Advanced Features (Future)

### Reset Token Usage
```python
# Future endpoint
POST /api/v1/agents/{agent_id}/reset-tokens
```

### Token Usage Analytics
```python
# Get token usage per agent
GET /api/v1/agents/{agent_id}/token-stats
```

### Scheduled Token Reset
Menggunakan `token_reset_date` untuk auto-reset token usage setiap periode:
- Daily
- Weekly  
- Monthly

## 💡 Best Practices

1. **Set Reasonable Limits**: 
   - Small agents: 10,000 - 50,000 tokens
   - Medium agents: 100,000 - 500,000 tokens
   - Large agents: 1,000,000+ tokens

2. **Monitor Usage**: 
   - Check `tokens_used` dan `tokens_remaining` regularly
   - Set up alerts ketika mendekati limit

3. **Update Limits Proactively**:
   - Adjust `token_limit` sebelum mencapai batas
   - Consider usage patterns

## 🔍 Monitoring & Logging

Semua operasi token di-log:
```
Token usage check passed
  agent_id: xxx
  tokens_remaining: 95000
  tokens_used: 5000
  token_limit: 100000

Token usage tracked
  execution_id: xxx
  input_tokens: 124
  output_tokens: 178
  total_tokens: 302
  agent_tokens_used: 5302
```

## 🚨 Troubleshooting

### Agent Tidak Bisa Digunakan (429 Error)
**Solusi**: Update token_limit agent
```bash
PATCH /api/v1/agents/{agent_id}
{
  "token_limit": 200000
}
```

### Token Count Tidak Akurat
**Note**: Token estimation adalah approximate. Actual usage dari OpenAI API mungkin sedikit berbeda.

## 📝 Example Usage

### Python SDK
```python
import requests

# Create agent with token limit
response = requests.post(
    "http://localhost:8000/api/v1/agents",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "name": "Customer Support Bot",
        "token_limit": 50000,
        "config": {
            "llm_model": "gpt-3.5-turbo",
            "temperature": 0.7
        }
    }
)

agent_id = response.json()["id"]

# Execute agent
exec_response = requests.post(
    f"http://localhost:8000/api/v1/agents/{agent_id}/execute",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "input": "Help me with my order"
    }
)

print(f"Tokens used: {exec_response.json()['tokens_used']}")
print(f"Tokens remaining: {exec_response.json()['tokens_remaining']}")
```

## 🎯 Summary

Fitur Token Limit memberikan kontrol penuh atas penggunaan token setiap agent:
✅ Set limit saat create agent
✅ Update limit kapan saja
✅ Auto-reject eksekusi jika limit tercapai
✅ Real-time tracking token usage
✅ Detailed logging dan monitoring
