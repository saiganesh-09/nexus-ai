# Security Model (Phase 1 — baseline)

## Implemented now

- Secrets only via environment variables; `.env` git-ignored; `.env.example` ships placeholders.
- CORS restricted to configured origins (default `http://localhost:3000`).
- Structured logging via structlog with JSON output; no secrets logged.
- Request correlation IDs (`X-Request-ID`) for tracing.
- Pydantic v2 settings validation; no hardcoded credentials.

## Planned (later phases)

- bcrypt/argon2 password hashing, JWT access tokens with expiry.
- Per-user data isolation enforced in repositories.
- Rate limiting (slowapi/Redis) and max request body size.
- Provider API keys stored encrypted at rest; never returned to clients.
- Safe error responses (no stack traces to clients).
