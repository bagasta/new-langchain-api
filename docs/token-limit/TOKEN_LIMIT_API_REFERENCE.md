# Token Limit API - Quick Reference

## Create Agent dengan Token Limit

```bash
POST /api/v1/agents
Content-Type: application/json
Authorization: Bearer {API_KEY}

{
  "name": "Customer Support Bot",
  "token_limit": 100000,        // Max tokens (null = unlimited)
  "config": {
    "llm_model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 1000,
    "system_prompt": "You are a helpful assistant"
  },
  "tools": [],
  "mcp_servers": {}
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Customer Support Bot",
  "token_limit": 100000,
  "tokens_used": 0,
  "token_reset_date": null,
  "config": {...},
  "status": "active",
  "created_at": "2024-12-24T15:00:00Z"
}
```

---

## Update Token Limit

```bash
PATCH /api/v1/agents/{agent_id}
Content-Type: application/json
Authorization: Bearer {API_KEY}

{
  "token_limit": 200000    // Update to higher limit
}
```

---

## Execute Agent (dengan Token Tracking)

```bash
POST /api/v1/agents/{agent_id}/execute
Content-Type: application/json
Authorization: Bearer {API_KEY}

{
  "input": "What is the weather today?",
  "parameters": {},
  "session_id": "optional-session-id"
}
```

**Success Response (200):**
```json
{
  "execution_id": "uuid",
  "status": "completed",
  "message": "Agent execution started",
  "response": "Based on current data...",
  "session_id": "optional-session-id",
  "tokens_used": 245,          // Tokens untuk eksekusi ini
  "tokens_remaining": 99755    // Sisa token available
}
```

**Token Limit Exceeded (429):**
```json
{
  "detail": "Agent token limit exceeded. Used: 100000/100000 tokens. Please increase the token limit or reset the agent."
}
```

---

## Get Agent Info (including Token Usage)

```bash
GET /api/v1/agents/{agent_id}
Authorization: Bearer {API_KEY}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Customer Support Bot",
  "token_limit": 100000,
  "tokens_used": 5420,
  "token_reset_date": null,
  "config": {...},
  "status": "active",
  "mcp_servers": {},
  "google_tools": [],
  "created_at": "2024-12-24T15:00:00Z",
  "updated_at": "2024-12-24T15:30:00Z"
}
```

---

## Common Use Cases

### 1. Unlimited Agent (Development)
```json
{
  "name": "Dev Agent",
  "token_limit": null    // No limit
}
```

### 2. Free Tier Agent
```json
{
  "name": "Free User Agent",
  "token_limit": 10000
}
```

### 3. Premium Agent
```json
{
  "name": "Premium Agent",
  "token_limit": 1000000
}
```

### 4. Increase Limit when Near Maximum
```bash
# Check current usage
GET /agents/{id}
# Response: tokens_used: 95000, token_limit: 100000

# Update before hitting limit
PATCH /agents/{id}
{
  "token_limit": 200000
}
```

---

## Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 429  | Token limit exceeded | Update `token_limit` or wait for reset |
| 404  | Agent not found | Check agent_id |
| 401  | Unauthorized | Check API key |
| 500  | Server error | Check logs |

---

## Python Example

```python
import requests

API_URL = "http://localhost:8000/api/v1"
API_KEY = "your-api-key"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 1. Create agent with limit
response = requests.post(
    f"{API_URL}/agents",
    headers=headers,
    json={
        "name": "My Bot",
        "token_limit": 50000,
        "config": {
            "llm_model": "gpt-3.5-turbo"
        }
    }
)
agent = response.json()
agent_id = agent["id"]
print(f"Created agent: {agent_id}")

# 2. Execute and track tokens
response = requests.post(
    f"{API_URL}/agents/{agent_id}/execute",
    headers=headers,
    json={
        "input": "Hello!"
    }
)
result = response.json()
print(f"Tokens used: {result['tokens_used']}")
print(f"Tokens remaining: {result['tokens_remaining']}")

# 3. Check usage
response = requests.get(
    f"{API_URL}/agents/{agent_id}",
    headers=headers
)
agent = response.json()
print(f"Total usage: {agent['tokens_used']}/{agent['token_limit']}")

# 4. Update limit if needed
if agent['tokens_used'] > agent['token_limit'] * 0.8:  # 80% used
    response = requests.patch(
        f"{API_URL}/agents/{agent_id}",
        headers=headers,
        json={"token_limit": agent['token_limit'] * 2}
    )
    print("Limit increased!")
```

---

## JavaScript Example

```javascript
const API_URL = "http://localhost:8000/api/v1";
const API_KEY = "your-api-key";

const headers = {
  "Authorization": `Bearer ${API_KEY}`,
  "Content-Type": "application/json"
};

// Create agent with limit
const createAgent = async () => {
  const response = await fetch(`${API_URL}/agents`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      name: "My Bot",
      token_limit: 50000,
      config: {
        llm_model: "gpt-3.5-turbo"
      }
    })
  });
  return await response.json();
};

// Execute with tracking
const executeAgent = async (agentId, input) => {
  const response = await fetch(`${API_URL}/agents/${agentId}/execute`, {
    method: "POST",
    headers,
    body: JSON.stringify({ input })
  });
  
  if (response.status === 429) {
    throw new Error("Token limit exceeded!");
  }
  
  const result = await response.json();
  console.log(`Tokens used: ${result.tokens_used}`);
  console.log(`Tokens remaining: ${result.tokens_remaining}`);
  
  return result;
};

// Usage
(async () => {
  const agent = await createAgent();
  const result = await executeAgent(agent.id, "Hello!");
  console.log(result.response);
})();
```

---

## Monitoring Tips

### 1. Set Up Alerts
```python
def check_token_usage(agent_id):
    agent = get_agent(agent_id)
    usage_percent = (agent['tokens_used'] / agent['token_limit']) * 100
    
    if usage_percent >= 80:
        send_alert(f"Agent {agent_id} at {usage_percent}% token usage")
    
    return usage_percent
```

### 2. Daily Usage Reports
```python
def generate_usage_report(agents):
    report = []
    for agent in agents:
        if agent['token_limit']:
            usage = {
                'name': agent['name'],
                'used': agent['tokens_used'],
                'limit': agent['token_limit'],
                'percent': (agent['tokens_used'] / agent['token_limit']) * 100
            }
            report.append(usage)
    return report
```

### 3. Auto-Scale Limits
```python
def auto_scale_limit(agent_id):
    agent = get_agent(agent_id)
    
    if not agent['token_limit']:
        return  # Unlimited
    
    usage_percent = (agent['tokens_used'] / agent['token_limit']) * 100
    
    if usage_percent >= 90:
        new_limit = agent['token_limit'] * 1.5  # Increase by 50%
        update_agent(agent_id, {'token_limit': new_limit})
        print(f"Auto-scaled limit to {new_limit}")
```
