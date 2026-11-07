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

## Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Service status, version, environment, timestamp |

## Token handling

- JWT (HS256), claims: `sub` (user id), `tv` (token version), `iat`, `exp`, `type=access`.
- Logout and password change increment `token_version`; tokens carrying a stale
  `tv` are rejected with `401 token_revoked`.
- TTL configured via `ACCESS_TOKEN_EXPIRE_MINUTES` (default 1440).
