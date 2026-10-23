"""
FastAPI Request Dependencies.
Handles database session injection, JWT user authentication, role checks, and API Key validation.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from core.security import decode_access_token, hash_api_key
from models.user import User, UserRole
from models.api_key import APIKey

security_bearer = HTTPBearer(auto_error=False)


# ============================================================================
# JWT User Authentication for Dashboard REST APIs
# ============================================================================
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    session: AsyncSession = Depends(get_session)
) -> User:
    """Extracts and verifies the JWT token from the Authorization header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(payload["sub"])
    user = await session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account does not exist or is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Enforces admin-only permissions."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this action."
        )
    return current_user


# ============================================================================
# API Key Verification for MCP Endpoint (/mcp)
# Supports: Authorization: Bearer mcp_live_...
# ============================================================================
async def authenticate_mcp_caller(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> tuple[Optional[User], Optional[APIKey]]:
    """
    Validates the caller's API key.
    If no authorization header is supplied or invalid/revoked, handles accordingly.
    Returns:
        (user, api_key)
    """
    if not authorization:
        return None, None

    # Parse Bearer token
    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None, None

    raw_key = parts[1].strip()
    key_hash = hash_api_key(raw_key)

    # Look up key in PostgreSQL
    statement = select(APIKey).where(APIKey.key_hash == key_hash)
    result = await session.exec(statement)
    api_key = result.first()

    if not api_key:
        return None, None

    # Immediate rejection if key has been revoked
    if not api_key.is_active:
        return None, None

    # Fetch corresponding user
    user = await session.get(User, api_key.user_id)
    if not user or not user.is_active:
        return None, None

    return user, api_key
