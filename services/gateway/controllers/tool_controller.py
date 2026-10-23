"""
Tool Discovery Controller.
Provides REST APIs for inspecting aggregated, namespaced MCP tools.
"""

from fastapi import APIRouter
from aggregator import aggregator

router = APIRouter(prefix="/api/tools", tags=["Tools"])


@router.get("")
async def list_aggregated_tools():
    """Retrieve the current aggregated namespaced tool schemas across all enabled upstreams."""
    tools = await aggregator.refresh_tools()
    return {"count": len(tools), "tools": tools}
