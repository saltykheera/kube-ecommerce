"""
MCP Tool Aggregator & Routing Engine.
Connects to internal upstream MCP servers, namespaces tools, and handles failure containment.
"""

import json
import logging
from typing import Any, Optional
import httpx
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import async_session_maker
from models import UpstreamServer

logger = logging.getLogger("gateway-aggregator")

# Timeout in seconds for upstream calls (enforcing assignment requirement:
# "A slow or dead upstream must not break tool listing or calls to other servers. Calls have timeouts and return a clear error.")
UPSTREAM_TIMEOUT = 3.5


class ToolAggregator:
    def __init__(self):
        # Maps prefixed_tool_name -> {"slug": ..., "server_url": ..., "auth_header": ..., "original_name": ..., "schema": ...}
        self.tool_registry: dict[str, dict[str, Any]] = {}

    async def refresh_tools(self) -> list[dict[str, Any]]:
        """Queries all enabled upstream servers, aggregates their tools with prefixing, and updates server health."""
        async with async_session_maker() as session:
            result = await session.exec(select(UpstreamServer))
            servers = result.all()

            aggregated_tools: list[dict[str, Any]] = []
            new_registry: dict[str, dict[str, Any]] = {}

            for server in servers:
                if not server.is_enabled:
                    if server.status != "disabled":
                        server.status = "disabled"
                        session.add(server)
                    continue

                # Query tools from upstream with timeout
                tools, is_healthy = await self._fetch_upstream_tools(server)

                # Update server status in DB
                new_status = "connected" if is_healthy else "unreachable"
                if server.status != new_status:
                    server.status = new_status
                    session.add(server)

                if is_healthy and tools:
                    for tool in tools:
                        original_name = tool.get("name", "")
                        prefixed_name = f"{server.slug}__{original_name}"

                        # Clone and namespace the tool schema
                        namespaced_tool = dict(tool)
                        namespaced_tool["name"] = prefixed_name
                        namespaced_tool["description"] = f"[{server.name}] {tool.get('description', '')}"

                        aggregated_tools.append(namespaced_tool)
                        new_registry[prefixed_name] = {
                            "slug": server.slug,
                            "server_url": server.url,
                            "auth_header": server.auth_header,
                            "original_name": original_name,
                            "schema": namespaced_tool,
                        }

            await session.commit()
            self.tool_registry = new_registry
            logger.info(f"Aggregated {len(aggregated_tools)} tools from {len(servers)} upstream servers.")
            return aggregated_tools

    async def _fetch_upstream_tools(self, server: UpstreamServer) -> tuple[list[dict[str, Any]], bool]:
        """Queries tools/list from a single upstream server with strict timeout."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "MCP-Gateway/1.0",
        }
        if server.auth_header:
            headers["Authorization"] = server.auth_header

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        try:
            async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
                resp = await client.post(server.url, json=payload, headers=headers)
                resp.raise_for_status()

                # Parse response (handling SSE 'data: ...' or standard JSON)
                text = resp.text.strip()
                data = None
                for line in text.splitlines():
                    if line.startswith("data:"):
                        data = json.loads(line[5:].strip())
                        break
                if data is None and text.startswith("{"):
                    data = json.loads(text)

                if data and "result" in data and "tools" in data["result"]:
                    return data["result"]["tools"], True
                elif data and "error" in data:
                    logger.warning(f"Upstream {server.name} returned error: {data['error']}")
                    return [], False
                return [], False

        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
            logger.warning(f"Upstream {server.name} ({server.url}) is unreachable or timed out: {e}")
            return [], False
        except Exception as e:
            logger.error(f"Unexpected error communicating with {server.name}: {e}")
            return [], False

    async def call_tool(self, prefixed_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Routes a tool call to the correct upstream server by stripping its namespace prefix."""
        tool_meta = self.tool_registry.get(prefixed_name)

        # If not found in memory, try refreshing tools once
        if not tool_meta:
            await self.refresh_tools()
            tool_meta = self.tool_registry.get(prefixed_name)

        if not tool_meta:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error: Tool '{prefixed_name}' is not found or its upstream server is currently disabled/unreachable."}]
            }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "MCP-Gateway/1.0",
        }
        if tool_meta["auth_header"]:
            headers["Authorization"] = tool_meta["auth_header"]

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_meta["original_name"],
                "arguments": arguments,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
                resp = await client.post(tool_meta["server_url"], json=payload, headers=headers)
                resp.raise_for_status()

                text = resp.text.strip()
                data = None
                for line in text.splitlines():
                    if line.startswith("data:"):
                        data = json.loads(line[5:].strip())
                        break
                if data is None and text.startswith("{"):
                    data = json.loads(text)

                if data and "result" in data:
                    return data["result"]
                elif data and "error" in data:
                    return {
                        "isError": True,
                        "content": [{"type": "text", "text": f"Upstream Error: {json.dumps(data['error'])}"}]
                    }
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Empty or unparseable response from upstream: {text}"}]
                }

        except httpx.TimeoutException:
            logger.error(f"Timeout calling upstream for tool '{prefixed_name}'")
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error: Upstream server timed out after {UPSTREAM_TIMEOUT}s while executing '{prefixed_name}'."}]
            }
        except Exception as e:
            logger.error(f"Error executing tool '{prefixed_name}': {e}")
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Upstream communication error: {str(e)}"}]
            }


# Singleton aggregator instance
aggregator = ToolAggregator()
