from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NexusError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories import UserRepository
from app.schemas.auth import LoginRequest, UserCreate, UserUpdate


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = UserRepository(db)

    async def register(self, data: UserCreate) -> tuple[User, str]:
        existing = await self.users.get_by_email(str(data.email).lower())
        if existing:
            raise NexusError(409, "email_taken", "An account with this email already exists")
        user = await self.users.create(
            email=str(data.email).lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
        )
        await self.db.commit()
        token = create_access_token(user.id, user.token_version)
        return user, token

    async def login(self, data: LoginRequest) -> tuple[User, str]:
        user = await self.users.get_by_email(str(data.email).lower())
        if not user or not verify_password(data.password, user.password_hash):
            raise NexusError(401, "invalid_credentials", "Invalid email or password")
        if not user.is_active:
            raise NexusError(403, "account_disabled", "This account is disabled")
        token = create_access_token(user.id, user.token_version)
        return user, token

    async def logout(self, user: User) -> None:
        await self.users.increment_token_version(user)
        await self.db.commit()

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        fields = data.model_dump(exclude_unset=True)
        if "password" in fields and fields["password"]:
            fields["password_hash"] = hash_password(fields.pop("password"))
        else:
            fields.pop("password", None)
        if "password_hash" in fields:
            await self.users.increment_token_version(user)
        updated = await self.users.update(user, **fields)
        await self.db.commit()
        return updated
