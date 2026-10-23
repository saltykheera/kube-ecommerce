"""
MCP Protocol Controller.
Exposes the central /mcp endpoint implementing the Model Context Protocol (Streamable HTTP / JSON-RPC 2.0).
"""

import time
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, Header
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from aggregator import aggregator
from database import get_session
from core.dependencies import authenticate_mcp_caller
from models.audit_log import AuditLog
from models.user import User
from models.api_key import APIKey

logger = logging.getLogger("mcp-controller")
router = APIRouter(tags=["MCP Protocol"])


@router.post("/mcp")
async def handle_mcp_request(
    request: Request,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """
    Exposes the unified outward-facing MCP protocol endpoint for external clients.
    Supports JSON-RPC 2.0 over Streamable HTTP (SSE).
    """
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

    # Authenticate caller if Bearer key is provided
    user, api_key = await authenticate_mcp_caller(authorization, session)

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

        start_time = time.perf_counter()
        logger.info(f"Gateway executing tool: {tool_name} with caller: {user.email if user else 'anonymous'}")
        
        result = await aggregator.call_tool(tool_name, arguments)
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Determine outcome status
        is_error = result.get("isError", False)
        status_str = "error" if is_error else "success"

        # Record audit log entry in PostgreSQL
        try:
            slug = tool_name.split("__")[0] if "__" in tool_name else "unknown"
            audit_record = AuditLog(
                user_id=user.id if user else None,
                user_email=user.email if user else None,
                api_key_id=api_key.id if api_key else None,
                server_slug=slug,
                tool_name=tool_name,
                arguments=json.dumps(arguments),
                status=status_str,
                duration_ms=duration_ms,
                error_message=str(result) if is_error else None,
            )
            session.add(audit_record)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to record audit log: {e}")

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
