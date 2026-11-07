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

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # or run without .env (defaults work for dev)
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
| `pytest` | backend | Test suite |

## Environment variables

See `.env.example`. Copy to `backend/.env`. Never commit real keys.

## Documentation

- [docs/architecture.md](docs/architecture.md) — system architecture
- [docs/development-roadmap.md](docs/development-roadmap.md) — phased plan
- [docs/security.md](docs/security.md) — security model (in progress)

## Roadmap

Phase 1 (current): foundation — scaffolding, health check, frontend↔backend
connectivity, design system shell. See `docs/development-roadmap.md`.

## License

Private / portfolio project.
