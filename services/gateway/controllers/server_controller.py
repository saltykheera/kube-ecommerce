"""
Upstream Server Registry Controller.
Provides REST APIs for managing connected upstream MCP servers.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from aggregator import aggregator
from database import get_session
from models.upstream_server import UpstreamServer, UpstreamServerCreate, UpstreamServerRead

router = APIRouter(prefix="/api/servers", tags=["Server Registry"])


@router.get("", response_model=list[UpstreamServerRead])
async def list_servers(session: AsyncSession = Depends(get_session)):
    """List all registered upstream MCP servers and their current status."""
    result = await session.exec(select(UpstreamServer))
    return result.all()


@router.post("", response_model=UpstreamServerRead, status_code=status.HTTP_201_CREATED)
async def create_server(server_data: UpstreamServerCreate, session: AsyncSession = Depends(get_session)):
    """Register a new upstream MCP server in the gateway."""
    existing = await session.exec(select(UpstreamServer).where(UpstreamServer.slug == server_data.slug))
    if existing.first():
        raise HTTPException(
            status_code=400,
            detail=f"Server with prefix slug '{server_data.slug}' already exists."
        )

    new_server = UpstreamServer.model_validate(server_data)
    session.add(new_server)
    await session.commit()
    await session.refresh(new_server)

    # Immediately refresh tools to register the new upstream
    await aggregator.refresh_tools()
    return new_server


@router.patch("/{server_id}/toggle", response_model=UpstreamServerRead)
async def toggle_server(server_id: int, session: AsyncSession = Depends(get_session)):
    """Enable or disable an upstream server dynamically."""
    server = await session.get(UpstreamServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    server.is_enabled = not server.is_enabled
    session.add(server)
    await session.commit()
    await session.refresh(server)

    # Refresh tool registry immediately
    await aggregator.refresh_tools()
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(server_id: int, session: AsyncSession = Depends(get_session)):
    """Remove an upstream MCP server from the registry."""
    server = await session.get(UpstreamServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    await session.delete(server)
    await session.commit()
    await aggregator.refresh_tools()
    return None
