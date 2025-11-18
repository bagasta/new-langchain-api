# Codex Activity Log

## 2025-11-14
- Added token usage columns to `executions` model and ensured schema backfills for legacy databases.
- Instrumented `ExecutionService` with a LangChain callback handler to collect prompt/completion tokens, persisted them, and exposed metrics via `/agents/{id}/executions`.
- Updated tests to align with the new tracking behavior and attempted to run `pytest tests/test_endpoints.py::test_agent_endpoints -q` (fails because pytest is not installed in this environment).
- Documented the three steps required for future quota enforcement: capture usage data returned by the OpenAI API/LLM response (`usage.prompt_tokens`, `usage.completion_tokens`) directly after `executor.ainvoke(...)`; persist the counts via new columns (`prompt_tokens`, `completion_tokens`, `total_tokens`) and, if needed, future per-agent/per-user quota tables; then debit the appropriate quota bucket after each execution and reject requests that would exceed the remaining allowance.
