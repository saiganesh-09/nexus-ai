"""User provider credential management — keys are Fernet-encrypted at rest
and never returned to the client (masked preview only)."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.errors import NexusError
from app.database.session import get_db
from app.models import ApiCredential, User

router = APIRouter(prefix="/credentials", tags=["credentials"])

ALLOWED_PROVIDERS = {"openai-compatible", "anthropic", "openai", "groq", "mistral", "together"}


class CredentialIn(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    api_key: str = Field(min_length=8, max_length=500)
    label: str = Field(default="", max_length=100)


class CredentialOut(BaseModel):
    id: str
    provider: str
    label: str
    key_preview: str
    is_active: bool


def _preview(credential: ApiCredential) -> str:
    try:
        secret = decrypt_secret(credential.encrypted_key)
    except Exception:
        return "••••"
    return secret[:4] + "••••" + secret[-4:] if len(secret) > 8 else "••••"


@router.get("", response_model=list[CredentialOut])
async def list_credentials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(ApiCredential).where(ApiCredential.user_id == current_user.id)
        )
    ).scalars().all()
    return [
        CredentialOut(id=str(c.id), provider=c.provider, label=c.label,
                      key_preview=_preview(c), is_active=c.is_active)
        for c in rows
    ]


@router.post("", response_model=CredentialOut, status_code=201)
async def store_credential(
    data: CredentialIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = data.provider.strip().lower()
    if provider not in ALLOWED_PROVIDERS:
        raise NexusError(422, "invalid_provider",
                         f"Provider must be one of {sorted(ALLOWED_PROVIDERS)}")
    existing = (
        await db.execute(
            select(ApiCredential).where(
                ApiCredential.user_id == current_user.id,
                ApiCredential.provider == provider,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.encrypted_key = encrypt_secret(data.api_key)
        existing.label = data.label or existing.label
        existing.is_active = True
        cred = existing
    else:
        cred = ApiCredential(
            user_id=current_user.id, provider=provider, label=data.label,
            encrypted_key=encrypt_secret(data.api_key),
        )
        db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return CredentialOut(id=str(cred.id), provider=cred.provider, label=cred.label,
                         key_preview=_preview(cred), is_active=cred.is_active)


@router.delete("/{credential_id}", status_code=204)
async def delete_credential(
    credential_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cred = (
        await db.execute(
            select(ApiCredential).where(
                ApiCredential.id == credential_id,
                ApiCredential.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if cred is None:
        raise NexusError(404, "credential_not_found", "Credential not found")
    await db.delete(cred)
    await db.commit()
