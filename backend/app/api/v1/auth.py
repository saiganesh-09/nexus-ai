from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.database.session import get_db
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserOut,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(token: str) -> TokenResponse:
    settings = get_settings()
    return TokenResponse(
        access_token=token, expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate, db: AsyncSession = Depends(get_db)
) -> User:
    user, _ = await AuthService(db).register(data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    _, token = await AuthService(db).login(data)
    return _token_response(token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await AuthService(db).logout(current_user)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
