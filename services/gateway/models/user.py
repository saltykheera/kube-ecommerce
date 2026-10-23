from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True, description="Unique user email address")
    role: UserRole = Field(default=UserRole.MEMBER, description="User role: admin or member")
    is_active: bool = Field(default=True, description="Whether this user account is active")


class User(UserBase, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(description="Securely hashed password (PBKDF2-SHA256)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserCreate(SQLModel):
    email: str
    password: str
    role: UserRole = UserRole.MEMBER


class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime


class UserLogin(SQLModel):
    email: str
    password: str


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
