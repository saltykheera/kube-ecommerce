from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class AuditLogBase(SQLModel):
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True, description="Caller user ID")
    user_email: Optional[str] = Field(default=None, index=True, description="Caller user email for quick querying")
    api_key_id: Optional[int] = Field(default=None, foreign_key="api_keys.id", index=True, description="API Key ID used")
    server_slug: str = Field(index=True, description="Upstream server slug (e.g. 'woo', 'calc', 'metrics')")
    tool_name: str = Field(index=True, description="Full namespaced tool name called (e.g. 'woo__list_products')")
    arguments: str = Field(default="{}", description="JSON string of sanitized tool arguments")
    status: str = Field(index=True, description="Execution outcome: 'success', 'error', 'timeout', or 'unauthorized'")
    duration_ms: float = Field(description="Execution latency in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Optional error message if failed")


class AuditLog(AuditLogBase, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class AuditLogRead(AuditLogBase):
    id: int
    created_at: datetime
