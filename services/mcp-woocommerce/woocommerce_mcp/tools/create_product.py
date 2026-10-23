"""Create a new simple product in the WooCommerce store."""

import json
from typing import Any, Callable, Coroutine

from ..client import WooCommerceClient, handle_tool_errors


def build_tool(client: WooCommerceClient) -> Callable[..., Coroutine[Any, Any, str]]:
    @handle_tool_errors("create_product")
    async def create_product(
        name: str,
        regular_price: str,
        description: str = "",
        short_description: str = "",
    ) -> str:
        """Create a new product with title, regular price, and description."""
        payload: dict[str, Any] = {
            "name": name,
            "type": "simple",
            "regular_price": str(regular_price),
            "status": "publish",
        }
        if description:
            payload["description"] = description
        if short_description:
            payload["short_description"] = short_description
        p = await client.request("POST", "/wp-json/wc/v3/products", json=payload)
        return json.dumps({
            "success": True,
            "message": f"Product '{name}' created successfully.",
            "product": {
                "id": p.get("id"),
                "name": p.get("name"),
                "price": p.get("price"),
                "status": p.get("status"),
                "permalink": p.get("permalink"),
            },
        }, indent=2)

    return create_product
