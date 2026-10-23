"""Retrieve a paginated list of store orders, optionally filtered by status."""

import json
from typing import Any, Callable, Coroutine

from ..client import WooCommerceClient, handle_tool_errors


def build_tool(client: WooCommerceClient) -> Callable[..., Coroutine[Any, Any, str]]:
    @handle_tool_errors("list_orders")
    async def list_orders(status: str = "", page: int = 1, per_page: int = 10) -> str:
        """List orders from the WooCommerce store."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if status:
            params["status"] = status
        orders = await client.request("GET", "/wp-json/wc/v3/orders", params=params)
        return json.dumps([
            {
                "id": o.get("id"),
                "status": o.get("status"),
                "total": o.get("total"),
                "currency": o.get("currency"),
                "date_created": o.get("date_created"),
                "customer_id": o.get("customer_id"),
                "billing_name": (
                    f"{o.get('billing', {}).get('first_name', '')} "
                    f"{o.get('billing', {}).get('last_name', '')}"
                ).strip(),
                "items": [
                    {
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "quantity": item.get("quantity"),
                        "total": item.get("total"),
                    }
                    for item in o.get("line_items", [])
                ],
            }
            for o in orders
        ], indent=2)

    return list_orders
