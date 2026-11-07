from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AiRequest, User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, **fields) -> User:
        user = User(**fields)
        self.db.add(user)
        await self.db.flush()
        return user

    async def update(self, user: User, **fields) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        await self.db.flush()
        return user

    async def increment_token_version(self, user: User) -> None:
        user.token_version += 1
        await self.db.flush()


class RequestRepository:
    """All queries are scoped by user_id — callers must always pass it."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _filtered(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        request_type: str | None = None,
        q: str | None = None,
        date_from=None,
        date_to=None,
    ) -> Select:
        stmt = select(AiRequest).where(AiRequest.user_id == user_id)
        if status:
            stmt = stmt.where(AiRequest.status == status)
        if provider:
            stmt = stmt.where(AiRequest.provider == provider)
        if model:
            stmt = stmt.where(AiRequest.model == model)
        if request_type:
            stmt = stmt.where(AiRequest.request_type == request_type)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                AiRequest.prompt.ilike(like) | AiRequest.response_text.ilike(like)
            )
        if date_from:
            stmt = stmt.where(AiRequest.created_at >= date_from)
        if date_to:
            stmt = stmt.where(AiRequest.created_at <= date_to)
        return stmt

    async def list_paginated(
        self, user_id: UUID, *, page: int, page_size: int, **filters
    ) -> tuple[list[AiRequest], int]:
        base = self._filtered(user_id, **filters)
        total = (
            await self.db.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        stmt = (
            base.order_by(AiRequest.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db.execute(stmt)).scalars().all()
        return list(items), total

    async def get_for_user(self, user_id: UUID, request_id) -> AiRequest | None:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(AiRequest)
            .where(AiRequest.id == request_id, AiRequest.user_id == user_id)
            .options(selectinload(AiRequest.routing_decision))
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()
