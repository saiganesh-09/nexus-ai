from collections.abc import AsyncGenerator
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NexusError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models import User
from app.repositories import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise NexusError(401, "not_authenticated", "Authentication required")
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") != "access":
            raise ValueError("wrong token type")
        user_id = UUID(payload["sub"])
        token_version = int(payload.get("tv", 0))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise NexusError(401, "invalid_token", "Invalid or expired token") from exc

    user = await UserRepository(db).get_by_id(user_id)
    if not user or not user.is_active:
        raise NexusError(401, "invalid_token", "Invalid or expired token")
    if user.token_version != token_version:
        raise NexusError(401, "token_revoked", "Token has been revoked")
    request.state.user_id = user.id
    return user
