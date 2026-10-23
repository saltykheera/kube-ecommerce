"""
Chat Agent Controller.
Exposes the conversational AI assistant API for the React Dashboard.
Authenticates callers, invokes the Gemini tool loop, and returns synthesized answers with tool call metadata.
"""

from typing import Optional, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from core.dependencies import get_current_user
from models.user import User, UserRead
from agent.gemini_agent import chat_agent

router = APIRouter(prefix="/api/chat", tags=["Chat Agent"])


class ChatRequest(BaseModel):
    message: str = Field(description="User prompt or task for the chat agent", min_length=1)
    history: Optional[list[dict[str, Any]]] = Field(
        default=[],
        description="Optional conversation history list of previous messages"
    )


class ToolCallRecord(BaseModel):
    tool: str
    arguments: dict[str, Any]
    result: Any
    status: str
    duration_ms: float


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolCallRecord]
    user: UserRead


@router.post("", response_model=ChatResponse)
async def chat_with_agent(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Submits a conversational message to the AI Chat Agent.
    The agent executes under the authenticated user's identity, enforcing RBAC and audit trail.
    """
    result = await chat_agent.chat(
        message=payload.message,
        user=current_user,
        session=session,
        history=payload.history
    )

    return ChatResponse(
        reply=result["reply"],
        tool_calls=result["tool_calls"],
        user=UserRead.model_validate(current_user)
    )
