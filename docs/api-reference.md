# API Reference (Phase 2)

Base URL: `http://localhost:8000/api/v1` · Interactive docs: `/docs` (Swagger) · `/redoc`

All protected endpoints require `Authorization: Bearer <access_token>`.
Errors use a consistent envelope: `{"error": {"code", "message", "details"}}`.

## Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Create account. Body: `email`, `password` (min 8), `full_name?`. → `201 UserOut` · `409 email_taken` · `422` validation |
| POST | `/auth/login` | — | Body: `email`, `password` → `TokenResponse {access_token, token_type, expires_in}` · `401 invalid_credentials` |
| POST | `/auth/logout` | ✓ | Invalidates all tokens for the user (bumps `token_version`) → `204` |
| GET | `/auth/me` | ✓ | Current user profile → `UserOut` |

## Users

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | ✓ | Profile → `UserOut` |
| PATCH | `/users/me` | ✓ | Update `full_name` and/or `password`. Password change revokes existing tokens. → `UserOut` |

## Requests (history)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/requests` | ✓ | Paginated, user-scoped list. Query: `page` (≥1), `page_size` (1–100, default 20), `status`, `provider`, `model`, `request_type`, `q` (prompt/response search), `date_from`, `date_to` → `PaginatedRequests` |
| GET | `/requests/{id}` | ✓ | Request detail incl. `routing_decision` → `AiRequestDetail` · `404` if not owned/found |

## Chat (Phase 3)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/chat` | ✓ | Submit a prompt. Body: `prompt` (1–8000 chars), `model` (`"auto"` or `"provider/model_id"` or bare catalog id; default auto), `max_tokens?`, `temperature?` → `ChatResponseOut` with content, token usage, latency, cost, routing explanation · `502 provider_error` on failure (request still recorded) |
| GET | `/models` | ✓ | Active model catalog with pricing and `provider_configured` flag |
| POST | `/routing/explain` | ✓ | Routing preview WITHOUT calling a provider. Body: `prompt` → `RoutingExplanationOut`: score, tier, signals, selected provider/model, reason, policy version, ordered fallback candidates, decision timestamp |
| GET | `/analytics/overview?days=N` | ✓ | Aggregates: requests, tokens, est. cost, avg latency, success/cache rates, daily timeseries, model usage — all from `ai_requests` |
| GET | `/analytics/models?days=N` | ✓ | Per-model requests/tokens/cost/latency/success rate |
| POST | `/compare` | ✓ | Body: `prompt`, `models` (2–4 explicit `provider/model_id`) → side-by-side `CompareResponseOut`; each attempt persisted as `request_type='comparison'`; per-model failures return as error items, not request failure |

### Routing

`model: "auto"` delegates to `RoutingEngine` (`app/routers/engine.py`), which
is provider-independent — it receives an `is_configured(provider)` predicate
and returns a `RoutingOutcome`. The classifier (`app/routers/classifier.py`)
scores prompts 0–1 from length bands, code indicators, reasoning keywords,
task verbs, technical/writing domain signals, sentence structure and
simple-lookup penalties → `economy | standard | premium` → ordered
`TIER_POLICY` candidates (`rule-v1`). Manual `provider/model_id` selection
bypasses the engine entirely (`routing: null` in the response). Every
decision is persisted in `routing_decisions` and viewable per-request via
`GET /requests/{id}` or previewed via `POST /routing/explain`.

Classifier accuracy is heuristic, not measured at production scale — see
`tests/unit/test_routing_engine.py` for the 24-prompt evaluation matrix.

### Providers

- `openai-compatible` — any `/chat/completions` endpoint (Ollama default
  `http://localhost:11434/v1`, or OpenAI via `OPENAI_COMPAT_BASE_URL` +
  `OPENAI_COMPAT_API_KEY`; keyless endpoints supported).
- `anthropic` — native Messages API via `ANTHROPIC_API_KEY`.

### Cost & tokens

Token counts come from provider `usage` when reported; otherwise estimated
(len/4) and flagged via `cost_is_estimate`. Cost = tokens × catalog price
(USD per 1M, `model_configs.pricing_effective_date`). Local models price at $0.

## Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Service status, version, environment, timestamp |

## Token handling

- JWT (HS256), claims: `sub` (user id), `tv` (token version), `iat`, `exp`, `type=access`.
- Logout and password change increment `token_version`; tokens carrying a stale
  `tv` are rejected with `401 token_revoked`.
- TTL configured via `ACCESS_TOKEN_EXPIRE_MINUTES` (default 1440).
