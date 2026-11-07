# Database Schema

PostgreSQL via SQLAlchemy 2.x (async, asyncpg). Migrations: Alembic
(`backend/alembic/`). All entities use UUID primary keys and UTC timestamps.

## Entity relationship summary

```
users ──< api_credentials
users ──< ai_requests ──< routing_decisions (1:1)
                  └──< request_logs
users ──< conversations ──< messages
users ──< eval_runs ──< eval_results
model_configs (global catalog, referenced by provider+model_id)
eval_datasets ──< eval_runs (via dataset_id)
```

## Tables

### users
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email | varchar(320) | unique, indexed; stored lowercase |
| password_hash | varchar(255) | bcrypt over SHA-256 pre-hash; never plaintext |
| full_name | varchar(200) | |
| is_active | bool | disabled accounts cannot authenticate |
| token_version | int | incremented on logout/password change to revoke JWTs |
| created_at / updated_at | timestamptz | |

### api_credentials
Per-user provider keys. `encrypted_key` holds Fernet ciphertext derived from
`SECRET_KEY` — plaintext keys are never persisted.

### model_configs
Global model catalog: `provider`, `model_id` (unique together), display name,
USD-per-1M-token input/output pricing, `context_window`, `capabilities` JSONB,
`pricing_effective_date`.

### conversations / messages
Chat threads and turns; messages carry optional token counts and model used.

### ai_requests
One row per AI request: `user_id` (ownership), `request_type`
(chat/comparison/agent/eval), `provider`, `model`, `prompt`, `response_text`,
`status`, `input_tokens`/`output_tokens` (nullable = provider didn't report),
`latency_ms`, `estimated_cost_usd` + `cost_is_estimate` flag, `cache_hit`,
`error_message`, `metadata` JSONB. Indexes: `(user_id, created_at)`, plus
single-column indexes on `user_id`, `provider`, `model`, `status`,
`request_type`, `conversation_id`.

### routing_decisions
1:1 with `ai_requests`: `complexity_score`, `complexity_tier`,
`selected_provider`, `selected_model`, `reason`, `policy_version`, timestamp.

### request_logs
Append-only per-request event log (provider attempts, retries, errors) with
`level`, `event`, `detail` JSONB — feeds provider-error analytics.

### eval_datasets / eval_runs / eval_results
Datasets hold versioned JSON task lists. Runs capture `agent_config`,
`status`, aggregate `summary` JSONB. Results store per-task `passed`, `score`,
`details`, `latency_ms`, `cost_usd`.

## Conventions

- JSON columns use `JSONB` on Postgres, `JSON` on SQLite (test fallback).
- Deletes cascade from `users`; `ai_requests.conversation_id` uses
  `ON DELETE SET NULL`.
- User data isolation is enforced in `RequestRepository` — every query takes
  `user_id` explicitly.
