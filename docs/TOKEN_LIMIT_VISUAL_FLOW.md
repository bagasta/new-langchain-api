# Token Limit System - Visual Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     USER REQUEST: Execute Agent                          │
│                          POST /agents/{id}/execute                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │   Get Agent from Database    │
                  │   - id, token_limit          │
                  │   - tokens_used              │
                  └──────────┬───────────────────┘
                             │
                             ▼
                ┌────────────────────────────────┐
                │  Is token_limit set (not NULL)? │
                └────────┬──────────────┬─────────┘
                         │              │
                    YES  │              │  NO (Unlimited)
                         │              │
                         ▼              ▼
        ┌────────────────────────┐   ┌─────────────────────┐
        │ Calculate Remaining:    │   │  Skip token check   │
        │ remaining = limit - used│   │  Proceed directly   │
        └────────┬───────────────┘   └──────────┬──────────┘
                 │                               │
                 ▼                               │
        ┌─────────────────────┐                 │
        │ remaining <= 0 ?    │                 │
        └──┬──────────────┬───┘                 │
           │ YES          │ NO                  │
           │              │                     │
           ▼              ▼                     │
    ┌──────────────┐  ┌───────────────┐       │
    │ 🔴 ERROR 429 │  │ ✅ Proceed    │◄──────┘
    │ Token Limit  │  │   to Execute   │
    │ Exceeded     │  └───────┬────────┘
    └──────────────┘          │
                              ▼
                 ┌────────────────────────────────┐
                 │   Create Execution Record      │
                 │   - status: RUNNING            │
                 │   - input: user message        │
                 └────────────┬───────────────────┘
                              │
                              ▼
                 ┌────────────────────────────────┐
                 │   Execute LangChain Agent      │
                 │   - Run LLM                    │
                 │   - Call tools if needed       │
                 │   - Generate response          │
                 └────────────┬───────────────────┘
                              │
                              ▼
                 ┌────────────────────────────────┐
                 │   Calculate Token Usage        │
                 │   ┌──────────────────────────┐ │
                 │   │ input_tokens = estimate  │ │
                 │   │   (user message)         │ │
                 │   └──────────────────────────┘ │
                 │   ┌──────────────────────────┐ │
                 │   │ output_tokens = estimate │ │
                 │   │   (AI response)          │ │
                 │   └──────────────────────────┘ │
                 │   ┌──────────────────────────┐ │
                 │   │ total = input + output   │ │
                 │   └──────────────────────────┘ │
                 └────────────┬───────────────────┘
                              │
                              ▼
                 ┌────────────────────────────────┐
                 │   Update Database              │
                 │   ┌──────────────────────────┐ │
                 │   │ execution.input_tokens   │ │
                 │   │ execution.output_tokens  │ │
                 │   │ execution.total_tokens   │ │
                 │   └──────────────────────────┘ │
                 │   ┌──────────────────────────┐ │
                 │   │ agent.tokens_used +=     │ │
                 │   │   total_tokens           │ │
                 │   └──────────────────────────┘ │
                 │   ┌──────────────────────────┐ │
                 │   │ execution.status =       │ │
                 │   │   COMPLETED              │ │
                 │   └──────────────────────────┘ │
                 └────────────┬───────────────────┘
                              │
                              ▼
                 ┌────────────────────────────────┐
                 │   Return Response              │
                 │   {                            │
                 │     "response": "...",         │
                 │     "tokens_used": 245,        │
                 │     "tokens_remaining": 9755   │
                 │   }                            │
                 └────────────────────────────────┘
```

---

## Token Usage Tracking Detail

```
┌───────────────────────────────────────────────────────────────┐
│                    AGENT (Database)                            │
├───────────────────────────────────────────────────────────────┤
│  id: uuid-xxx                                                  │
│  name: "Customer Bot"                                          │
│  token_limit: 10000          ← Maximum allowed                │
│  tokens_used: 0              ← Starts at 0                     │
│  token_reset_date: null                                        │
└───────────────────────────────────────────────────────────────┘
                              │
                              │ First Execution
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                   EXECUTION #1                                 │
├───────────────────────────────────────────────────────────────┤
│  Input: "What is AI?"                                          │
│  ├─ input_tokens: 50                                           │
│  Output: "AI stands for..."                                   │
│  ├─ output_tokens: 200                                         │
│  └─ total_tokens: 250                                          │
└───────────────────────┬───────────────────────────────────────┘
                        │
                        │ Update Agent
                        ▼
┌───────────────────────────────────────────────────────────────┐
│                    AGENT (Updated)                             │
├───────────────────────────────────────────────────────────────┤
│  token_limit: 10000                                            │
│  tokens_used: 250            ← Updated: 0 + 250                │
│  remaining: 9750             ← Calculated: 10000 - 250         │
└───────────────────────────────────────────────────────────────┘
                              │
                              │ Second Execution
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                   EXECUTION #2                                 │
├───────────────────────────────────────────────────────────────┤
│  Input: "Explain deep learning"                               │
│  ├─ input_tokens: 75                                           │
│  Output: "Deep learning is..."                                │
│  ├─ output_tokens: 350                                         │
│  └─ total_tokens: 425                                          │
└───────────────────────┬───────────────────────────────────────┘
                        │
                        │ Update Agent
                        ▼
┌───────────────────────────────────────────────────────────────┐
│                    AGENT (Updated)                             │
├───────────────────────────────────────────────────────────────┤
│  token_limit: 10000                                            │
│  tokens_used: 675            ← Updated: 250 + 425              │
│  remaining: 9325             ← Calculated: 10000 - 675         │
└───────────────────────────────────────────────────────────────┘
                              │
                              │ ... many executions ...
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                    AGENT (Near Limit)                          │
├───────────────────────────────────────────────────────────────┤
│  token_limit: 10000                                            │
│  tokens_used: 9950           ← Close to limit!                 │
│  remaining: 50               ← Only 50 tokens left             │
└───────────────────────────────────────────────────────────────┘
                              │
                              │ Next Large Execution
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                   EXECUTION ATTEMPT                            │
├───────────────────────────────────────────────────────────────┤
│  Pre-check: remaining (50) <= 0 ?  NO                         │
│  Proceed with execution                                        │
│  Input tokens: 30                                              │
│  Output tokens: 100                                            │
│  Total: 130 tokens                                             │
└───────────────────────┬───────────────────────────────────────┘
                        │
                        │ Update Agent
                        ▼
┌───────────────────────────────────────────────────────────────┐
│                    AGENT (Exceeded)                            │
├───────────────────────────────────────────────────────────────┤
│  token_limit: 10000                                            │
│  tokens_used: 10080          ← Over limit: 9950 + 130          │
│  remaining: -80              ← Negative!                       │
└───────────────────────────────────────────────────────────────┘
                              │
                              │ Next Execution Attempt
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                   🔴 BLOCKED                                   │
├───────────────────────────────────────────────────────────────┤
│  Pre-check: remaining (-80) <= 0 ?  YES!                      │
│  ❌ Return HTTP 429 Error                                     │
│  "Agent token limit exceeded. Used: 10080/10000 tokens.       │
│   Please increase the token limit or reset the agent."        │
└───────────────────────────────────────────────────────────────┘
                              │
                              │ Admin Updates Limit
                              ▼
┌───────────────────────────────────────────────────────────────┐
│              PATCH /agents/{id}                                │
│              { "token_limit": 50000 }                          │
└───────────────────────┬───────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────────┐
│                    AGENT (Limit Increased)                     │
├───────────────────────────────────────────────────────────────┤
│  token_limit: 50000          ← Updated!                        │
│  tokens_used: 10080          ← Unchanged                       │
│  remaining: 39920            ← Now has space!                  │
└───────────────────────────────────────────────────────────────┘
                              │
                              │ Can Execute Again ✅
                              ▼
```

---

## Comparison: With vs Without Token Limit

```
┌─────────────────────────────────────────────────────────────────────┐
│               WITHOUT Token Limit (token_limit: null)                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Execute ──► Run Agent ──► Track Tokens ──► Return Response         │
│                             (for stats)                               │
│                                                                       │
│  ✅ Always executes                                                  │
│  ✅ No restrictions                                                  │
│  ✅ Good for development/testing                                     │
│  ⚠️  No cost control                                                 │
│  ⚠️  Can consume unlimited resources                                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                WITH Token Limit (token_limit: 10000)                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Execute ──► Check Limit ──┬─► ❌ Error 429 (if exceeded)           │
│                             │                                         │
│                             └─► ✅ Run Agent ──► Track & Update      │
│                                                                       │
│  ✅ Controlled usage                                                 │
│  ✅ Predictable costs                                                │
│  ✅ Prevents abuse                                                   │
│  ✅ Good for production/SaaS                                         │
│  ⚠️  Need to monitor & update limits                                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Multi-Tier Agent Strategy

```
┌───────────────────────────────────────────────────────────────┐
│                     DEVELOPMENT                                │
├───────────────────────────────────────────────────────────────┤
│  Environment: Local/Staging                                    │
│  token_limit: null                                             │
│  tokens_used: tracked (for analysis)                           │
│  Use case: Testing, debugging                                  │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                     FREE TIER                                  │
├───────────────────────────────────────────────────────────────┤
│  Environment: Production                                       │
│  token_limit: 10,000                                           │
│  Value: ~$0.015 (at GPT-3.5 pricing)                          │
│  Reset: Monthly                                                │
│  Use case: Personal projects, trials                           │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                     BASIC TIER                                 │
├───────────────────────────────────────────────────────────────┤
│  Environment: Production                                       │
│  token_limit: 100,000                                          │
│  Value: ~$0.15 (at GPT-3.5 pricing)                           │
│  Reset: Monthly                                                │
│  Use case: Small businesses, startups                          │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                     PRO TIER                                   │
├───────────────────────────────────────────────────────────────┤
│  Environment: Production                                       │
│  token_limit: 1,000,000                                        │
│  Value: ~$1.50 (at GPT-3.5 pricing)                           │
│  Reset: Monthly                                                │
│  Use case: Medium businesses, high usage                       │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                     ENTERPRISE                                 │
├───────────────────────────────────────────────────────────────┤
│  Environment: Production                                       │
│  token_limit: null or very high (10M+)                        │
│  Custom pricing                                                │
│  Reset: Custom schedule                                        │
│  Use case: Large enterprises, white-label                      │
└───────────────────────────────────────────────────────────────┘
```

---

## Monitoring Dashboard (Concept)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AGENT DASHBOARD                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Agent: Customer Support Bot                      Status: 🟢 Active │
│  Created: 2024-12-20                              Plan: Pro Tier    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  TOKEN USAGE                                                  │   │
│  │  ████████████████████░░░░░░░░░░ 65% (650,000 / 1,000,000)   │   │
│  │                                                               │   │
│  │  Used: 650,000 tokens                                        │   │
│  │  Remaining: 350,000 tokens                                   │   │
│  │  Resets: 2024-12-31 (7 days)                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  USAGE BREAKDOWN (Last 7 Days)                               │   │
│  │                                                               │   │
│  │  Mon  ██████████ 50K                                         │   │
│  │  Tue  ████████████████ 80K                                   │   │
│  │  Wed  ████████████████████ 100K                              │   │
│  │  Thu  ██████████ 50K                                         │   │
│  │  Fri  ████████████ 60K                                       │   │
│  │  Sat  ████████ 40K                                           │   │
│  │  Sun  ██████ 30K                                             │   │
│  │                                                               │   │
│  │  Average: 58,571 tokens/day                                  │   │
│  │  Peak: Wednesday (100K)                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  RECENT EXECUTIONS                                            │   │
│  │                                                               │   │
│  │  #12543  10 min ago  "Check order status"      245 tokens   │   │
│  │  #12542  15 min ago  "Cancel subscription"     380 tokens   │   │
│  │  #12541  22 min ago  "Update payment method"   520 tokens   │   │
│  │  #12540  35 min ago  "Track shipment"          190 tokens   │   │
│  │                                                               │   │
│  │  [View All Executions]                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ALERTS & RECOMMENDATIONS                                     │   │
│  │                                                               │   │
│  │  ⚠️  Approaching limit (65% used)                            │   │
│  │      Consider upgrading to Enterprise tier                   │   │
│  │                                                               │   │
│  │  💡 Optimization Tip                                         │   │
│  │      Average response is 300 tokens. Consider reducing       │   │
│  │      max_tokens in config if responses too long.             │   │
│  │                                                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  [Update Token Limit]  [View Analytics]  [Download Report]         │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```
