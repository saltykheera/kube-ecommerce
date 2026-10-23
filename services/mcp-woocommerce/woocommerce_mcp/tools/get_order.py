"""Get full details of a specific WooCommerce order by ID."""

import json
from typing import Any, Callable, Coroutine

from ..client import WooCommerceClient, handle_tool_errors


def build_tool(client: WooCommerceClient) -> Callable[..., Coroutine[Any, Any, str]]:
    @handle_tool_errors("get_order")
    async def get_order(order_id: int) -> str:
        """Retrieve details for a single order by ID."""
        o = await client.request("GET", f"/wp-json/wc/v3/orders/{order_id}")
        return json.dumps({
            "id": o.get("id"),
            "status": o.get("status"),
            "total": o.get("total"),
            "currency": o.get("currency"),
            "date_created": o.get("date_created"),
            "customer_id": o.get("customer_id"),
            "billing": o.get("billing"),
            "shipping": o.get("shipping"),
            "payment_method_title": o.get("payment_method_title"),
            "items": [
                {
                    "product_id": item.get("product_id"),
                    "name": item.get("name"),
                    "quantity": item.get("quantity"),
                    "subtotal": item.get("subtotal"),
                    "total": item.get("total"),
                }
                for item in o.get("line_items", [])
            ],
        }, indent=2)

    return get_order
