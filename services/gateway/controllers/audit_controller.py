"""
Audit Log Controller.
Provides REST APIs for inspecting tool execution audit records.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from core.dependencies import get_current_user
from models.user import User, UserRole
from models.audit_log import AuditLog, AuditLogRead

router = APIRouter(prefix="/api/audit", tags=["Audit Logs"])


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    tool_name: Optional[str] = Query(None, description="Filter by tool name"),
    status: Optional[str] = Query(None, description="Filter by status ('success', 'error', 'timeout')"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Retrieves audit logs.
    Admins can view all audit logs or filter by user. Members see only their own tool calls.
    """
    statement = select(AuditLog)

    # Enforce role boundaries
    if current_user.role != UserRole.ADMIN:
        statement = statement.where(AuditLog.user_id == current_user.id)
    elif user_id is not None:
        statement = statement.where(AuditLog.user_id == user_id)

    if tool_name:
        statement = statement.where(AuditLog.tool_name == tool_name)
    if status:
        statement = statement.where(AuditLog.status == status)

    statement = statement.order_by(col(AuditLog.created_at).desc()).offset(offset).limit(limit)
    result = await session.exec(statement)
    return result.all()
