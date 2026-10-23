"""
Authentication Controller.
Handles user login, JWT session generation, and profile retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from core.security import verify_password, create_access_token
from core.dependencies import get_current_user
from models.user import User, UserLogin, UserRead, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, session: AsyncSession = Depends(get_session)):
    """Authenticates team users (admin or member) and issues a JWT access token."""
    statement = select(User).where(User.email == credentials.email.lower().strip())
    result = await session.exec(statement)
    user = result.first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact an administrator."
        )

    # Issue JWT token
    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role.value})

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(user)
    )


@router.get("/me", response_model=UserRead)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Retrieves profile information for the authenticated user."""
    return current_user
