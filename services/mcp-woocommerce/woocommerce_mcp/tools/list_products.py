"""Retrieve a paginated list of products from the WooCommerce store."""

import json
from typing import Any, Callable, Coroutine

from ..client import WooCommerceClient, handle_tool_errors


def build_tool(client: WooCommerceClient) -> Callable[..., Coroutine[Any, Any, str]]:
    @handle_tool_errors("list_products")
    async def list_products(page: int = 1, per_page: int = 10, search: str = "") -> str:
        """List products from the WooCommerce catalog."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if search:
            params["search"] = search
        products = await client.request("GET", "/wp-json/wc/v3/products", params=params)
        return json.dumps([
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "price": p.get("price"),
                "regular_price": p.get("regular_price"),
                "status": p.get("status"),
                "stock_status": p.get("stock_status"),
                "permalink": p.get("permalink"),
                "categories": [c.get("name") for c in p.get("categories", [])],
            }
            for p in products
        ], indent=2)

    return list_products
