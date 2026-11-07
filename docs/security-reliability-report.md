# Security & Reliability Report — Phase 7

Date: 2026-11-07 · Scope: full backend + frontend verification pass.

## Reliability

| Control | Implementation | Verified by |
|---|---|---|
| Provider timeout | `request_timeout_seconds` (default 30s) on every httpx call | config + adapter code |
| Retry w/ exponential backoff | `provider_max_retries` (2) × base 0.5s → 0.5s/1s/2s; only `retryable` errors (408/409/425/429/5xx, timeouts, conn errors) retried; non-idempotent-safe since retries only hit read-style completions | `test_provider_retry_on_429` |
| Provider fallback | Auto-routed chat tries every configured same-tier candidate on any provider error; premium degrades to local model | live Phase 3/4 verification + `test_chat_provider_failure_recorded` |
| Redis caching | `app/core/cache.py` — user-scoped SHA-256 keys (`user_id` inside digest → no cross-user leakage), TTL `cache_ttl_seconds`, graceful in-memory fallback when Redis is down | `test_cache_roundtrip_and_user_isolation`, `test_chat_second_identical_prompt_is_cache_hit` (provider called once for 2 identical prompts) |
| Cache isolation | Key includes user_id, provider, model, prompt, max_tokens, temperature; `cache_hit` flag persisted on `ai_requests` | test above |
| Rate limiting | `RateLimitMiddleware` — sliding window per user (JWT sub) or IP; 429 with consistent error envelope; disabled in test env | `test_rate_limit_returns_429` |
| Correlation IDs | `X-Request-ID` on every request/response + structured log field | Phase 1–2 tests |
| Structured logging | structlog JSON, request duration + status | all requests |
| Max body size | `MaxBodySizeMiddleware` | existing |

## Security

| Control | Implementation | Verified by |
|---|---|---|
| Password hashing | SHA-256 pre-hash → bcrypt (72-byte safe) | `test_auth` suite |
| JWT auth | `sub`/`tv`/`exp` claims; `token_version` revocation on logout/password change | auth tests |
| Authorization | `get_current_user` on every protected route; ownership filters on all queries; eval run detail 404s cross-user | `test_other_user_cannot_read_run` |
| API key protection | `api_credentials` stores Fernet ciphertext only; API returns `key_preview` (`sk-a••••12345`), never plaintext; write-only via `POST /credentials`, masked list, owner-only delete | `test_credentials_encrypted_and_masked` (asserts plaintext absent from DB rows) |
| Provider allowlist | Credential provider restricted to known set → 422 otherwise | `test_credential_rejects_bad_provider` |
| Input validation | Pydantic on all inputs (prompt 1–8000 chars, page_size ≤100, models 2–4, password ≥8) | validation tests |
| SQL injection | Parameterized SQLAlchemy ORM only — no raw string interpolation of user input | code review |
| Secret redaction | No secrets in logs; provider errors truncate response bodies to 300 chars; JWT/API keys never logged | code review |
| CORS | Explicit origin allowlist from env | config |

## Known gaps (honest)

- **JWT in localStorage** (frontend) — XSS-exposed; httpOnly cookie migration recommended before public deployment.
- **Rate limiter is per-process** — multi-instance deployments need the Redis-backed variant (documented in `app/middleware/ratelimit.py`).
- **Dev JWT secret** in `.env` is short → PyJWT `InsecureKeyLengthWarning`; rotate to 32+ bytes for any shared environment.
- **User-supplied provider keys are stored but not yet wired into provider resolution** — `registry.get_provider` uses env credentials; per-user key resolution is the next milestone.
- **No refresh tokens** — access tokens expire; re-login required.
- Anthropic adapter is implemented but unverified live (no `ANTHROPIC_API_KEY` in this environment).

## Bugs found & fixed during this phase

1. `NameError: model` in both providers after the retry refactor — `_request_once` didn't receive the `model` param. Caught by the new retry test; fixed in both adapters.
2. `func.case(else_=)` invalid SQLAlchemy in analytics — replaced with `func.count().filter(...)` (Phase 5, recorded here for completeness).

## Test totals

- Backend: **86 passed** (was 79; +7 reliability/security tests).
- Frontend: lint 0 errors, production build clean.
