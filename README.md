# NEXUS AI — Intelligent LLM Gateway & AI Operations Platform

> Status: **Phases 1–7 complete** — auth, multi-provider LLM gateway, intelligent
> routing, agent tools, deterministic evaluations, analytics, caching, rate
> limiting, encrypted credentials, Docker + CI.

NEXUS AI sits between users and multiple LLM providers: it routes prompts to
the right model, tracks tokens/cost/latency, caches responses safely, runs
tool-using agents, and evaluates them on a deterministic benchmark suite —
all behind a dark enterprise dashboard.

## Features

- **Auth** — register/login/logout, JWT with token-version revocation, bcrypt (SHA-256 pre-hash), protected routes
- **AI Playground** — prompt editor, auto/manual model selection, routing explanation, token/cost/latency display, copy/regenerate
- **Intelligent router** — rule-based complexity classifier (length, code, reasoning, domain signals) → economy/standard/premium → ordered model policy with same-tier fallback; every decision persisted with score, signals, reason, policy version
- **Provider layer** — OpenAI-compatible adapter (Ollama/OpenAI/Groq/LM Studio) + Anthropic adapter; timeouts, exponential-backoff retry, structured errors
- **Model comparison** — fan one prompt out to 2–4 models, side-by-side results
- **Request history** — search, filters, pagination, detail drawer with routing decision
- **Analytics** — real aggregations: KPIs, daily cost/request timeseries, model usage, per-model performance
- **Agents** — calculator (AST-safe), knowledge lookup, code analysis; bounded tool-calling loop with full traces
- **Evaluations** — 25-task dataset, deterministic graders only (no LLM judge), per-category breakdowns, run history, pass rates
- **Reliability** — Redis response cache (user-scoped keys), per-user rate limiting, correlation IDs, structured logging
- **Security** — Fernet-encrypted provider credentials (masked API), ownership isolation, consistent error envelope, CORS allowlist, max body size

## Architecture

```mermaid
flowchart LR
    subgraph Client
        FE[Next.js 16 dashboard]
    end
    subgraph Backend[FastAPI]
        API[API layer /api/v1]
        RT[RoutingEngine + classifier]
        CS[ChatService]
        AG[Agent + ToolRegistry]
        EV[Eval runner + scorers]
        PR[Provider adapters]
        CA[(Redis cache)]
    end
    subgraph Data
        PG[(PostgreSQL 16)]
    end
    subgraph Providers
        OL[Ollama / OpenAI-compatible]
        AN[Anthropic]
    end
    FE -->|JWT| API
    API --> RT --> CS --> PR
    CS --> CA
    CS --> PG
    AG --> PR
    EV --> AG
    PR --> OL & AN
```

## Tech stack

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript strict, Tailwind v4, Recharts, Vitest + Testing Library
- **Backend:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.x async, Alembic, structlog, httpx, PyJWT, bcrypt, cryptography (Fernet), redis-py, pytest + pytest-asyncio
- **Infra:** PostgreSQL 16, Redis 7, Docker Compose, GitHub Actions

## Quick start (local dev)

```bash
# 1. Infrastructure
cd backend && docker compose -f ../docker-compose.yml up -d postgres redis
# (or reuse existing nexus-postgres :5434 / nexus-redis :6380)

# 2. Backend
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp ../.env.example .env                            # set DATABASE_URL, SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend && npm install && npm run dev           # http://localhost:3000
```

API docs: http://localhost:8000/docs · Health: http://localhost:8000/api/v1/health

### Local LLM (no API key needed)

```bash
ollama pull llama3.2:3b        # ~2GB
ollama serve                  # exposes http://localhost:11434/v1
```

`OPENAI_COMPAT_BASE_URL=http://localhost:11434/v1` is the default — the app
works end-to-end with zero cloud credentials.

## Docker deployment (verified)

```bash
cp .env.example .env           # set POSTGRES_PASSWORD, SECRET_KEY, FRONTEND_URL
# optional: OPENAI_COMPAT_API_KEY / ANTHROPIC_API_KEY for cloud providers
docker compose up -d --build
```

Services: `postgres` (healthy-gated), `redis`, `backend` (runs `alembic upgrade head` on start, 2 uvicorn workers), `frontend` (Next.js prod build). Healthchecks on postgres/redis/backend; frontend waits for backend health. Backend reaches host Ollama via `host.docker.internal`.

Verified live: `docker compose up` → `/api/v1/health` 200 → register → login → chat (real Ollama response) → request history → analytics → eval run.

## CI

`.github/workflows/ci.yml` runs on push/PR:
- **backend** — pip install + `pytest tests -q` (SQLite, no services needed)
- **frontend** — `npm ci`, lint, `vitest run`, `npm run build`
- **docker** — `docker compose config` validation + both image builds

## Testing

```bash
cd backend && pytest tests -q          # 86 tests: auth, isolation, routing (24-prompt matrix), chat, agents, evals, cache, rate limit, credentials
cd frontend && npm test                # Vitest component tests
cd frontend && npm run lint && npm run build
```

E2E coverage: registration→login→chat→history→analytics→eval exercised via API (see `docs/security-reliability-report.md`).

## Environment variables

See `.env.example` (root) and `backend/.env.example`. Key ones:

| Var | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing — **must be 32+ random bytes in production** |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | cache backend |
| `CORS_ORIGINS` | comma-separated allowed origins |
| `OPENAI_COMPAT_BASE_URL` / `_API_KEY` | OpenAI-compatible endpoint (Ollama default) |
| `ANTHROPIC_API_KEY` | Anthropic provider |
| `RATE_LIMIT_REQUESTS` / `REQUEST_TIMEOUT_SECONDS` / `PROVIDER_MAX_RETRIES` | reliability tuning |
| `CACHE_TTL_SECONDS` | response cache TTL |

Never commit `.env` or real keys — provider keys can also be stored per-user via `POST /api/v1/credentials` (Fernet-encrypted).

## Project structure

```
backend/app/{api,core,database,models,schemas,repositories,services,
             providers,routers,agents,evaluations,middleware,utils}
backend/tests/{unit}          frontend/app, components, lib
backend/scripts/              eval + policy-comparison tooling
docs/                         architecture, schema, api, security, roadmap
.github/workflows/ci.yml      docker-compose.yml   Dockerfiles ×2
```

## Security notes

- Passwords: SHA-256 pre-hash → bcrypt. JWTs carry `token_version`; logout/password change revokes all tokens.
- Provider keys: env-only or Fernet-encrypted per-user; never returned to clients (masked preview only).
- All queries are ownership-scoped; cross-user access returns 404.
- Rate limit per user/IP, max body size, CORS allowlist, structured error envelope (no stack traces).
- Full details: [docs/security-reliability-report.md](docs/security-reliability-report.md), [docs/security.md](docs/security.md)

## Known limitations

- **Rule-based routing** is heuristic, not a trained model — 24/24 on the curated test matrix but real-world misclassification is expected; decisions are persisted for tuning.
- **Local-model eval pass rate is 68%** (17/25) on `llama3.2:3b` — frontier models will score higher; the framework measures, it doesn't guarantee.
- **Streaming (SSE)** not yet implemented — responses are non-streaming.
- **JWT in localStorage** — migrate to httpOnly cookies for production hardening.
- **Rate limiter is per-process** — needs Redis backend for multi-instance deploys.
- **Sequential comparison/eval fan-out** — parallelization is a future optimization.
- Cloud deployment is *prepared* (Dockerfiles/compose/CI) but not executed — no cloud credentials or paid infra was used.

## Roadmap

- [x] Phase 1–2: foundation, auth, PostgreSQL schema
- [x] Phase 3–4: providers, router, playground, comparisons
- [x] Phase 5: dashboard, history, analytics, settings
- [x] Phase 6: agents, tools, eval framework + dashboard
- [x] Phase 7: retries, caching, rate limits, credentials, policy comparison
- [x] Phase 8: Docker, CI, deployment docs
- [ ] Streaming responses (SSE)
- [ ] httpOnly cookie auth, refresh tokens
n- [ ] Per-user provider key resolution in routing
- [ ] Redis-backed distributed rate limiter
- [ ] Parallel comparison/eval execution
- [ ] Cloud deployment (needs credentials + approval)

## License

Private / portfolio project.
