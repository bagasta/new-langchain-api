# Repository Guidelines

## Project Structure & Modules
- `app/main.py` boots the FastAPI app; v1 routes live under `app/api/v1/` (`auth`, `agents`, `tools`).
- Core settings/logging/DB + shared deps: `app/core/`; shared helpers: `app/utils/`.
- Business logic: `app/services/`; SQLAlchemy models: `app/models/`; Pydantic I/O: `app/schemas/`.
- Tool implementations: `app/tools/`; MCP + LangChain bridges: `app/integrations/`.
- Tests: `tests/` (unit + API); migrations: `alembic/`.

## Build, Test, and Development Commands
- Create env & deps: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Database prep: copy `.env.example` → `.env`, set secrets, run `alembic upgrade head` (PostgreSQL 15+).
- Run API: `uvicorn app.main:app --reload` (dev) or `docker-compose up -d`; prod: `docker-compose -f docker-compose.prod.yml up -d`.
- Tests: `pytest` (HTML + terminal coverage). Lint/format/type-check: `black .`, `isort .`, `mypy app`.

## Coding Style & Naming Conventions
- Python 3.11, Black line length 88, isort profile `black`. Keep imports sorted.
- Type hints required (mypy strict). Avoid implicit optionals and untyped defs.
- Names: snake_case funcs/vars, PascalCase classes, UPPER_SNAKE_CASE constants/env keys.
- APIs should return schema models from `app/schemas` (e.g., `AgentCreate`, `ToolExecuteRequest`).

## Runtime & API Behavior
- `app/main.py` adds CORS (origins from settings), request logging middleware, a global 500 handler, and `/health` + `/` info endpoints. Preflight `OPTIONS` returns 204. An extra Google callback route is registered if `GOOGLE_REDIRECT_URI` differs from `/api/v1/auth/google/callback`.
- Logging uses structlog (`LOG_FORMAT` json|console, `LOG_LEVEL`), initialised on startup.

## Auth & Users
- Identifiers are normalised email/phone; duplicates rejected. Passwords accept bcrypt/bcrypt_sha256 (or plaintext hashed on save). JWTs: HS256, `SECRET_KEY`, 30‑day default expiry.
- API keys (table `api_keys`): plans `PRO_M`=30 days, `PRO_Y`=365 days, `TRIAL`=14 days. Trial keys are issued per IP with auto‑purge of expired trials and auto‑activated trial users. `/auth/me` uses the presented token or most recent active key for the user.
- Google OAuth: default scopes in `DEFAULT_GOOGLE_SCOPES`; state encodes user id + scopes. Callback exchanges code manually to enforce scopes, stores tokens in `auth_tokens` (access + optional refresh + scopes), and merges scopes on refresh. `/auth/google/auth` issues auth URL, `/auth/google/callback` saves tokens, `/auth/google` lists them.
- Other endpoints: `/auth/login`, `/auth/register`, `/auth/api-key`, `/auth/api-key/update`, `/auth/api-key/trial`, `/auth/user/update-password` (owner only), `/auth/activate` (by email).

## Agents
- Create/update validates tool names against `tools`; stores config, MCP server map, and `allowed_tools` whitelist. When selected tools need Google scopes and the user lacks them, the response includes `auth_required`, `auth_url`, `auth_state`.
- CRUD and execution require API-key auth. `allowed_tools` also gates MCP tool name filtering (Google Workspace tools are excluded from the whitelist logic).
- Document endpoints: upload pdf/docx/pptx/txt (reject empty/unsupported), list, and delete; deletions mark uploads and remove embeddings.

## Execution Pipeline
- `ExecutionService` builds a LangChain tool-calling agent (`ChatOpenAI`, default model `gpt-4o-mini`, temp 0.7, max_tokens 1000; API key from agent config → settings → env `OPENAI_API_KEY`). Executions are recorded with status, errors, duration, and optional `session_id`.
- RAG: top‑3 embedding chunks per agent (pgvector cosine) are escaped and inlined into the system prompt; retrieval/match events are logged.
- Conversation history: last 20 completed executions (optionally filtered by `session_id`) feed a `MessagesPlaceholder`.
- Tools: agent tool records become LangChain tools. MCP SSE tools are added when available from agent.mcp_servers, agent config, per-request overrides, or defaults (`MCP_SSE_URL`/token). Tool filters merge settings + agent config + request parameters + `allowed_tools` whitelist; Google Workspace tool names are filtered out when enforcing whitelists. Execution gracefully falls back to local tools if MCP selection or connection fails.
- Output payload contains `output`, `intermediate_steps` (tool/observation/tool_call_id), `tools_used`, `execution_time`, and final messages; failures keep the error in `execution.output` with status `FAILED`. `/agents/executions/stats` aggregates totals, success rate, avg duration.

## Tools
- Built-ins auto-synchronised at startup: Gmail (send/read/search/get_thread/get_message/create_draft), Google Sheets (get/update values, create spreadsheet), Google Calendar (list/create/get event), plus file utilities `csv`, `json`, `file_list`.
- Google tools enforce required fields, normalise aliases, and provide detailed validation errors; scope mappings live in `GOOGLE_TOOL_SCOPE_MAP`. Gmail only marks messages read when requested; draft creation synthesises subject/body fallbacks if omitted.
- Custom tools are stored with JSON schema but execute via a placeholder echo response until implemented. `/tools/scopes/required` returns the union of scopes for provided tool names.

## Documents & Embeddings
- `EmbeddingService` uses `text-embedding-3-small`; cleans text, chunks (default 500 words / 100 overlap) and auto-downscales chunk/overlap/batch for large docs. MIME/extension whitelist: pdf, docx, pptx, txt. Batch embedding respects token estimates and records chunk parameters.
- Uploads stored in `agent_uploads` with size, chunking details, embedding_ids, and deletion markers; embeddings (1536-d pgvector) link back to uploads.

## Database & Migrations
- `init_db` ensures pgvector (PostgreSQL), creates metadata, and backfills `agents.mcp_servers` and `agents.allowed_tools` when missing. `ExecutionService` auto-adds `executions.session_id` if absent. Agent-tool insertion handles schemas with or without an `id` column.

## Configuration & Environment
- Key env vars: `DATABASE_URL`, `SECRET_KEY`, `OPENAI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `REDIS_URL`; optional MCP: `MCP_SSE_URL`, `MCP_SSE_TOKEN`, `MCP_SSE_ALLOWED_TOOLS`, `MCP_SSE_ALLOWED_TOOL_CATEGORIES`. CORS defaults include localhost:3000/8000 and the provided ngrok URL. Logging controlled via `LOG_LEVEL`/`LOG_FORMAT`.

## Testing Guidelines
- Use pytest defaults (`test_*.py`/`*_test.py`, `Test*`, `test_*`). Prefer async tests for async endpoints; fixtures in `tests/conftest.py` handle DB/session/auth.
- Add regression tests alongside fixes; API tests live in `tests/test_endpoints.py`. Keep coverage green (HTML + terminal reports via pytest addopts).

## Commit & Pull Request Guidelines
- Commit messages: imperative, present tense (e.g., "Add agent execution audit"). Keep scope small, note migrations/breaking changes.
- Before PR: run `pytest`, `black`, `isort`, `mypy`; include command output on failure. PRs should summarise changes, testing, and any auth/env setup; attach screenshots or example payloads when helpful.

## Security & Configuration Tips
- Never commit secrets; keep `.env` locally and update `.env.example` when adding settings.
- Required services: PostgreSQL, Redis; Google OAuth + MCP endpoints optional. Confirm service URLs/tokens before running.
- After pulling migrations, rerun `alembic upgrade head`; restart containers when env vars change.
