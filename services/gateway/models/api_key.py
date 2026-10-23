from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class APIKeyBase(SQLModel):
    name: str = Field(description="Descriptive name for the API key (e.g. 'Claude Code', 'Cursor')")
    prefix: str = Field(index=True, description="Public key prefix for display/identification (e.g. 'mcp_live_a1b2')")
    is_active: bool = Field(default=True, description="Whether this key is currently active or revoked")


class APIKey(APIKeyBase, table=True):
    __tablename__ = "api_keys"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, description="ID of the user who owns this key")
    key_hash: str = Field(unique=True, index=True, description="SHA-256 hash of the full plaintext key")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revoked_at: Optional[datetime] = Field(default=None, description="Timestamp when key was revoked")


class APIKeyCreate(SQLModel):
    name: str = Field(description="Name or purpose of this key", min_length=1, max_length=100)


class APIKeyRead(APIKeyBase):
    id: int
    user_id: int
    created_at: datetime
    revoked_at: Optional[datetime] = None


class APIKeyGeneratedResponse(SQLModel):
    id: int
    name: str
    prefix: str
    raw_key: str = Field(description="Plaintext API key. This will only be shown ONCE.")
    created_at: datetime
    message: str = "Store this API key safely. You will not be able to see it again."
