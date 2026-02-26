# Update TODO

Security and stability fixes to tackle next:

- Move `/auth/login` and `/auth/register` to accept credentials in JSON bodies (no query params); update the docs/examples accordingly.
- Stop allowing raw password hashes to be used for login: remove the direct string equality check and rely on bcrypt verification only.
- Redact or drop query strings from request logging so credentials never land in logs.
- Derive trial API key IPs from the request (not client input), and add server-side rate limiting for trials.
- Add timeouts + friendly error handling to outbound Google token exchanges (and other external HTTP calls, if any).
- Update `how-to-use.md` to show body-based auth requests and remove guidance about passing hashes as passwords.
- Add regression tests: login/register payload shape, hash-as-password is rejected, trial issuance rate limits/IP source, and Google token exchange timeout handling.
- Consider enabling a DB connection pool (or validating `NullPool` is intentional) to avoid connection churn under load.
- Hardening idea: avoid MAX(id)+1 inserts in `AgentService._add_agent_tools` to prevent race conditions; use serial/identity when possible.
