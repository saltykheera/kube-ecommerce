"""
MCP Protocol Controller.
Exposes the central /mcp endpoint implementing the Model Context Protocol (Streamable HTTP / JSON-RPC 2.0).
Enforces API key authentication, immediate key revocation, role-based access control (RBAC), and PostgreSQL audit logging.
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
from core.rbac import is_tool_allowed_for_role
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
    Secured by Bearer API Key authentication with instant revocation and RBAC.
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

    # ========================================================================
    # 1. API Key Authentication & Immediate Revocation Enforcement
    # ========================================================================
    user, api_key, auth_error = await authenticate_mcp_caller(authorization, session)

    if auth_error:
        logger.warning(f"Unauthorized MCP request rejected: {auth_error} (method: {method})")
        
        # Log unauthorized attempt to audit table
        try:
            audit_record = AuditLog(
                user_id=None,
                user_email=None,
                api_key_id=None,
                server_slug="gateway",
                tool_name=method or "unknown",
                arguments=json.dumps(params),
                status="unauthorized",
                duration_ms=0.0,
                error_message=auth_error,
            )
            session.add(audit_record)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to record unauthorized audit log: {e}")

        return JSONResponse(
            status_code=401,
            content={"jsonrpc": "2.0", "id": req_id, "error": {"code": -32001, "message": auth_error}}
        )

    # ========================================================================
    # 2. MCP Handshake / Initialization
    # ========================================================================
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
                "instructions": f"Team MCP Gateway authenticated for {user.email} (Role: {user.role.value}).",
            }
        }
        sse_text = f"event: message\ndata: {json.dumps(response_data)}\n\n"
        return Response(content=sse_text, media_type="text/event-stream")

    # ========================================================================
    # 3. Tool Discovery (tools/list)
    # ========================================================================
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

    # ========================================================================
    # 4. Tool Execution (tools/call) with RBAC & Audit Trail
    # ========================================================================
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return JSONResponse(
                content={"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "Missing 'name' in params"}}
            )

        slug = tool_name.split("__")[0] if "__" in tool_name else "unknown"

        # Check Role-Based Access Control (RBAC)
        is_allowed, rbac_error = is_tool_allowed_for_role(tool_name, user.role)
        if not is_allowed:
            logger.warning(f"RBAC Rejection: User '{user.email}' (role: {user.role.value}) attempted '{tool_name}'")
            
            # Record forbidden attempt in PostgreSQL audit table
            try:
                audit_record = AuditLog(
                    user_id=user.id,
                    user_email=user.email,
                    api_key_id=api_key.id,
                    server_slug=slug,
                    tool_name=tool_name,
                    arguments=json.dumps(arguments),
                    status="forbidden",
                    duration_ms=0.0,
                    error_message=rbac_error,
                )
                session.add(audit_record)
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to record forbidden audit log: {e}")

            response_data = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": rbac_error}]
                }
            }
            sse_text = f"event: message\ndata: {json.dumps(response_data)}\n\n"
            return Response(content=sse_text, media_type="text/event-stream")

        # Execute Tool Call
        start_time = time.perf_counter()
        logger.info(f"Gateway executing tool: {tool_name} for caller: {user.email} (Role: {user.role.value})")

        result = await aggregator.call_tool(tool_name, arguments)
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Determine outcome status
        is_error = result.get("isError", False)
        status_str = "error" if is_error else "success"

        # Record audit log entry in PostgreSQL
        try:
            audit_record = AuditLog(
                user_id=user.id,
                user_email=user.email,
                api_key_id=api_key.id,
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

    # ========================================================================
    # 5. Unknown / Unsupported MCP Method
    # ========================================================================
    else:
        return JSONResponse(
            content={"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method '{method}' not found"}}
        )
