# NEXUS AI — Intelligent LLM Gateway & AI Operations Platform

> Status: **Phase 1 — Project foundation** (backend scaffold + frontend shell).
> AI features (providers, routing, agents, evaluations) are not yet implemented.

NEXUS AI is a multi-model LLM gateway: a FastAPI backend that routes prompts to
multiple LLM providers with intelligent model selection, usage/cost tracking,
agent tooling, and evaluation — fronted by a Next.js enterprise dashboard.

## Tech stack

- **Backend:** Python 3.13, FastAPI, Pydantic v2, pydantic-settings, structlog, httpx, pytest
- **Frontend:** Next.js (App Router), React, TypeScript (strict), Tailwind CSS, shadcn/ui
- **Data/infra (planned):** PostgreSQL, Redis, Alembic, Docker, GitHub Actions

## Project structure

```
backend/    FastAPI application (app/, tests/, requirements.txt)
frontend/   Next.js application (app/, components/, lib/)
docs/       Architecture, database schema, API reference, roadmap, security
```

## Prerequisites

- Node.js 20+ and npm
- Python 3.11+

## Quick start

### Database (Docker)

```bash
docker run -d --name nexus-postgres -e POSTGRES_USER=nexus -e POSTGRES_PASSWORD=nexus \
  -e POSTGRES_DB=nexus -p 5432:5432 postgres:16-alpine
docker run -d --name nexus-redis -p 6379:6379 redis:7-alpine
```

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # adjust DATABASE_URL / ports if needed
alembic upgrade head     # run migrations
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs · Health: http://localhost:8000/api/v1/health

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

## Development scripts

| Command | Location | Purpose |
|---|---|---|
| `npm run dev` | frontend | Next.js dev server |
| `npm run lint` / `npm run build` | frontend | Lint / production build |
| `uvicorn app.main:app --reload` | backend | API dev server |
| `pytest` | backend | Test suite (SQLite, no external services needed) |
| `alembic upgrade head` | backend | Apply DB migrations |

## Environment variables

See `.env.example`. Copy to `backend/.env`. Never commit real keys.

## API

Interactive docs: http://localhost:8000/docs · See [docs/api-reference.md](docs/api-reference.md)

Implemented endpoints (Phase 2): health, register, login, logout, profile
(get/update), paginated request history with filters. AI endpoints arrive in
Phase 3+.

## Documentation

- [docs/architecture.md](docs/architecture.md) — system architecture
- [docs/database-schema.md](docs/database-schema.md) — relational schema
- [docs/api-reference.md](docs/api-reference.md) — endpoint reference
- [docs/development-roadmap.md](docs/development-roadmap.md) — phased plan
- [docs/security.md](docs/security.md) — security model

## Roadmap

- Phase 1 ✅ foundation — scaffolding, health check, frontend↔backend, design system
- Phase 2 ✅ data layer — PostgreSQL + Alembic, JWT auth, users, request history API
- Phase 3 ✅ AI core — provider abstraction (OpenAI-compatible + Anthropic), rule-based router with fallback, cost/token tracking, AI Playground + login/register UI
- Verified locally against Ollama (`llama3.2:3b`) — real responses, usage and routing explanations persisted. Set `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`-equivalent env vars for cloud providers.
- Phase 4 → Redis caching, retries, comparisons, analytics

## License

Private / portfolio project.
