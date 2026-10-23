"""
API Key Management Controller.
Handles key generation (returning plaintext once), listing masked keys, and instant revocation.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from core.security import generate_api_key
from core.dependencies import get_current_user
from models.user import User, UserRole
from models.api_key import APIKey, APIKeyCreate, APIKeyRead, APIKeyGeneratedResponse

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


@router.post("", response_model=APIKeyGeneratedResponse, status_code=status.HTTP_201_CREATED)
async def generate_key(
    key_in: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Generates a new API key for the current user.
    The raw plaintext key is returned ONLY in this response and must be stored securely.
    """
    raw_key, key_hash, display_prefix = generate_api_key(prefix="mcp_live_")

    api_key = APIKey(
        user_id=current_user.id,
        name=key_in.name,
        key_hash=key_hash,
        prefix=display_prefix,
        is_active=True,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    return APIKeyGeneratedResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        raw_key=raw_key,
        created_at=api_key.created_at,
    )


@router.get("", response_model=list[APIKeyRead])
async def list_keys(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Lists API keys.
    Admins see all keys across all users; members see only their own keys.
    Raw keys are never exposed.
    """
    if current_user.role == UserRole.ADMIN:
        statement = select(APIKey).order_by(APIKey.created_at.desc())
    else:
        statement = select(APIKey).where(APIKey.user_id == current_user.id).order_by(APIKey.created_at.desc())

    result = await session.exec(statement)
    return result.all()


@router.delete("/{key_id}", status_code=status.HTTP_200_OK)
async def revoke_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Immediately revokes an API key.
    Once revoked, the very next tool call using this key is rejected with HTTP 401.
    """
    api_key = await session.get(APIKey, key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key not found")

    # Only key owner or admin can revoke
    if api_key.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only revoke your own API keys."
        )

    api_key.is_active = False
    api_key.revoked_at = datetime.now(timezone.utc)
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    return {"message": "API key revoked successfully", "id": api_key.id, "is_active": False}
