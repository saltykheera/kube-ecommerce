from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class UpstreamServerBase(SQLModel):
    name: str = Field(index=True, description="Human readable name of the upstream MCP server")
    slug: str = Field(unique=True, index=True, description="Unique namespace prefix for tools (e.g. 'woo', 'calc')")
    url: str = Field(description="Streamable HTTP endpoint URL (e.g. http://mcp-woocommerce:8000/mcp)")
    auth_header: Optional[str] = Field(default=None, description="Optional bearer token or auth header")
    is_enabled: bool = Field(default=True, description="Whether this server's tools are aggregated and usable")
    status: str = Field(default="connected", description="Current status: connected, unreachable, or disabled")


class UpstreamServer(UpstreamServerBase, table=True):
    __tablename__ = "upstream_servers"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UpstreamServerCreate(UpstreamServerBase):
    pass


class UpstreamServerRead(UpstreamServerBase):
    id: int
    created_at: datetime
    updated_at: datetime
