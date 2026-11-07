# NEXUS AI Architecture

## Overview

NEXUS AI is an intelligent LLM gateway: a single API that authenticates users,
routes prompts to the most suitable LLM provider/model, tracks token usage and
cost, caches responses safely, runs tool-using agents, and evaluates agent
performance — all backed by PostgreSQL and Redis.

```
┌──────────────────────────────┐        ┌────────────────────────────────┐
│   Next.js frontend (App      │  HTTPS │   FastAPI backend              │
│   Router, TypeScript strict) │ ─────► │                                │
│   - Auth (JWT in httpOnly    │        │   API layer (api/v1/*)         │
│     cookie / memory)         │        │   ├─ Services (business logic) │
│   - Playground / Compare /   │        │   ├─ Repositories (DB access)  │
│     Requests / Evals /       │        │   ├─ Providers (OpenAI,        │
│     Analytics / Settings     │        │   │   Anthropic, compatible)   │
│   - Design system: dark navy │        │   ├─ Router (complexity        │
│     + indigo/electric-blue   │        │   │   classifier → model pick) │
└──────────────────────────────┘        │   ├─ Agents (tools: calc,      │
                                        │   │   knowledge, code analysis)│
                                        │   ├─ Evaluations (datasets,    │
                                        │   │   scorers, reports)        │
                                        │   └─ Core (config, security,   │
                                        │       logging, middleware)     │
                                        └───────┬───────────┬────────────┘
                                                │           │
                                        ┌───────▼───┐ ┌─────▼──────┐
                                        │PostgreSQL │ │   Redis    │
                                        │(users,    │ │(cache,     │
                                        │ requests, │ │ rate limit,│
                                        │ routing,  │ │ sessions)  │
                                        │ evals…)   │ │            │
                                        └───────────┘ └────────────┘
                                                │
                                        ┌───────▼────────────────┐
                                        │ External LLM providers │
                                        │ OpenAI · Anthropic ·   │
                                        │ OpenAI-compatible      │
                                        └────────────────────────┘
```

## Layered backend design

| Layer | Responsibility |
|---|---|
| `api/` | HTTP endpoints, request/response wiring only |
| `schemas/` | Pydantic validation models |
| `services/` | Business logic (chat orchestration, pricing, analytics) |
| `repositories/` | All database access; no business rules |
| `providers/` | External LLM API clients: retry, timeout, fallback, streaming |
| `routers/` | Model routing: rule-based complexity classifier (pluggable) |
| `agents/` | Agent loop + tool registry |
| `evaluations/` | Datasets, execution, scoring, reports |
| `core/` | Settings, JWT/password security, structured logging |
| `middleware/` | Correlation IDs, rate limiting, request-size limits |

## Key design decisions

- **Provider abstraction:** a common `LLMProvider` interface; each provider
  adapter normalizes responses (content, token usage, latency). A generic
  OpenAI-compatible adapter covers Groq, Ollama, LM Studio, etc.
- **Routing:** rule-based scorer (prompt length, task type, code presence,
  keywords → complexity tier) maps to a configurable model policy. The
  classifier is an interface so ML-based routers can be added later. Routing
  decisions are persisted with score, reason and policy version.
- **Caching:** Redis keys include model + parameters + prompt hash + user ID;
  cached responses are never shared across users.
- **Cost tracking:** provider-reported token usage only; pricing table is
  versioned by effective date; missing usage is recorded as unavailable rather
  than estimated silently (explicit estimates are flagged as such).
- **Security:** bcrypt password hashing, short-lived JWTs, per-user data
  isolation enforced at the repository/service layer, secrets only via env.

## Frontend design system

- Dark navy (`#0B0F1A` family) / charcoal surfaces, indigo + electric-blue
  accents, subtle borders, restrained shadows.
- Tokens defined in Tailwind config / CSS variables; shadcn/ui primitives themed
  to match.
- Layout: persistent sidebar navigation + top bar with user menu; fully
  responsive (collapses to drawer on mobile).
