"""Shared WooCommerce HTTP access and the existing JSON error contract."""

import json
import logging
from functools import wraps
from typing import Any, Callable, Coroutine, ParamSpec

import httpx

from .config import Settings

logger = logging.getLogger("woocommerce-mcp")
P = ParamSpec("P")


class WooCommerceClient:
    def __init__(
        self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.settings = settings
        self.transport = transport

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {
            "Accept": "application/json",
            "User-Agent": "WooCommerce-MCP-Server/1.0",
        }
        if self.settings.host_header:
            headers["Host"] = self.settings.host_header
        auth = (
            (self.settings.consumer_key, self.settings.consumer_secret)
            if self.settings.consumer_key and self.settings.consumer_secret
            else None
        )
        async with httpx.AsyncClient(
            base_url=self.settings.url.rstrip("/"),
            headers=headers,
            auth=auth,
            timeout=15.0,
            transport=self.transport,
        ) as client:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()


def handle_tool_errors(
    tool_name: str,
) -> Callable[[Callable[P, Coroutine[Any, Any, str]]], Callable[P, Coroutine[Any, Any, str]]]:
    """Keep tool signatures discoverable and preserve JSON error responses."""
    def decorate(
        func: Callable[P, Coroutine[Any, Any, str]],
    ) -> Callable[P, Coroutine[Any, Any, str]]:
        @wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> str:
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as exc:
                logger.error("HTTP error in %s: %s", tool_name, exc.response.status_code)
                return json.dumps({
                    "error": f"HTTP {exc.response.status_code}: {exc.response.text}"
                })
            except Exception as exc:
                logger.error("Error in %s: %s", tool_name, type(exc).__name__)
                return json.dumps({"error": str(exc)})

        return wrapped

    return decorate
