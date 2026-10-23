"""
Controllers / Routers Package.
Organizes API endpoints into modular, industry-standard controllers.
"""

from controllers.auth_controller import router as auth_router
from controllers.key_controller import router as key_router
from controllers.server_controller import router as server_router
from controllers.tool_controller import router as tool_router
from controllers.audit_controller import router as audit_router
from controllers.mcp_controller import router as mcp_router
from controllers.chat_controller import router as chat_router

__all__ = [
    "auth_router",
    "key_router",
    "server_router",
    "tool_router",
    "audit_router",
    "mcp_router",
    "chat_router",
]
