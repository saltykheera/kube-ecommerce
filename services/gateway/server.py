"""
FastAPI MCP Gateway Application.
Provides the central /mcp endpoint and REST APIs for server registry management.
"""

import os
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from aggregator import aggregator
from database import init_db, get_session
from models import UpstreamServer, UpstreamServerCreate, UpstreamServerRead

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp-gateway")

PORT = int(os.getenv("PORT", "8000"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MCP Gateway database and seeding upstreams...")
    await init_db()
    logger.info("Refreshing initial tools from all upstreams...")
    await aggregator.refresh_tools()
    yield
    logger.info("MCP Gateway shutting down.")


app = FastAPI(
    title="Team MCP Gateway",
    version="1.0.0",
    description="Centralized Model Context Protocol Gateway on Kubernetes",
    lifespan=lifespan
)

# Enable CORS for the future React Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check Endpoint
# ============================================================================
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mcp-gateway"}


# ============================================================================
# Central MCP Endpoint (/mcp - Streamable HTTP & JSON-RPC 2.0)
# ============================================================================
@app.post("/mcp")
async def handle_mcp_request(request: Request):
    """Exposes the unified outward-facing MCP protocol endpoint for external clients."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error: Invalid JSON"}}
        )

    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    # 1. MCP Initialization
    if method == "initialize":
        response_data = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "team-mcp-gateway",
                    "version": "1.0.0",
                },
                "instructions": "Unified Team MCP Gateway aggregating WooCommerce, Calculator, and Business Metrics tools.",
            }
        }
        sse_text = f"event: message\ndata: {json.dumps(response_data)}\n\n"
        return Response(content=sse_text, media_type="text/event-stream")

    # 2. Tools Discovery (tools/list)
    elif method == "tools/list":
        # Refresh tools dynamically from enabled upstreams
        tools = await aggregator.refresh_tools()
        response_data = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": tools
            }
        }
        sse_text = f"event: message\ndata: {json.dumps(response_data)}\n\n"
        return Response(content=sse_text, media_type="text/event-stream")

    # 3. Tool Execution (tools/call)
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return JSONResponse(
                content={"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "Missing 'name' in params"}}
            )

        logger.info(f"Gateway executing tool: {tool_name} with arguments: {arguments}")
        result = await aggregator.call_tool(tool_name, arguments)

        response_data = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result
        }
        sse_text = f"event: message\ndata: {json.dumps(response_data)}\n\n"
        return Response(content=sse_text, media_type="text/event-stream")

    # 4. Unknown / Unsupported MCP Method
    else:
        return JSONResponse(
            content={"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method '{method}' not found"}}
        )


# ============================================================================
# REST Management APIs (Server Registry for Admins & Dashboard)
# ============================================================================
@app.get("/api/servers", response_model=list[UpstreamServerRead])
async def list_servers(session: AsyncSession = Depends(get_session)):
    """List all registered upstream MCP servers and their current status."""
    result = await session.exec(select(UpstreamServer))
    return result.all()


@app.post("/api/servers", response_model=UpstreamServerRead, status_code=status.HTTP_201_CREATED)
async def create_server(server_data: UpstreamServerCreate, session: AsyncSession = Depends(get_session)):
    """Register a new upstream MCP server in the gateway."""
    # Check if slug is unique
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


@app.patch("/api/servers/{server_id}/toggle", response_model=UpstreamServerRead)
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


@app.delete("/api/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(server_id: int, session: AsyncSession = Depends(get_session)):
    """Remove an upstream MCP server from the registry."""
    server = await session.get(UpstreamServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    await session.delete(server)
    await session.commit()
    await aggregator.refresh_tools()
    return None


@app.get("/api/tools")
async def list_aggregated_tools():
    """Retrieve the current aggregated namespaced tool schemas."""
    tools = await aggregator.refresh_tools()
    return {"count": len(tools), "tools": tools}


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting MCP Gateway on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
