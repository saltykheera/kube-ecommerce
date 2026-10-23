"""Update the status of an existing WooCommerce order."""

import json
from typing import Any, Callable, Coroutine

from ..client import WooCommerceClient, handle_tool_errors

VALID_STATUSES = frozenset({
    "pending", "processing", "on-hold", "completed", "cancelled", "refunded", "failed", "trash",
})


def build_tool(client: WooCommerceClient) -> Callable[..., Coroutine[Any, Any, str]]:
    @handle_tool_errors("update_order_status")
    async def update_order_status(order_id: int, status: str) -> str:
        """Update order status."""
        clean_status = status.strip().lower()
        if clean_status not in VALID_STATUSES:
            return json.dumps({
                "error": (
                    f"Invalid status '{status}'. Must be one of: "
                    f"{', '.join(sorted(VALID_STATUSES))}"
                ),
            })
        o = await client.request(
            "PUT", f"/wp-json/wc/v3/orders/{order_id}", json={"status": clean_status}
        )
        return json.dumps({
            "success": True,
            "message": f"Order {order_id} status updated to '{clean_status}'.",
            "order": {
                "id": o.get("id"),
                "status": o.get("status"),
                "date_modified": o.get("date_modified"),
            },
        }, indent=2)

    return update_order_status
