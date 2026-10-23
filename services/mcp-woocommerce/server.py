"""
WooCommerce Model Context Protocol (MCP) Server.
Implements the 5 mandatory WooCommerce tools over Streamable HTTP.
"""

import os
import json
import logging
from typing import Any, Optional
import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from starlette.responses import JSONResponse

# Load environment variables if present
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("woocommerce-mcp")

# Environment configuration
WC_URL = os.getenv("WOOCOMMERCE_INTERNAL_URL") or os.getenv("WOOCOMMERCE_URL", "http://wordpress.default.svc.cluster.local:80")
WC_KEY = os.getenv("WOOCOMMERCE_CONSUMER_KEY", "")
WC_SECRET = os.getenv("WOOCOMMERCE_CONSUMER_SECRET", "")
WC_HOST_HEADER = os.getenv("WOOCOMMERCE_HOST_HEADER", "store.local")
PORT = int(os.getenv("PORT", "8000"))

# Initialize MCP Server
server = MCPServer(
    name="woocommerce-mcp",
    version="1.0.0",
    instructions="Provides tools to manage WooCommerce products, orders, and store operations."
)


def _get_client_kwargs() -> dict[str, Any]:
    """Prepares httpx client configuration for WooCommerce REST API."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "WooCommerce-MCP-Server/1.0",
    }
    if WC_HOST_HEADER:
        headers["Host"] = WC_HOST_HEADER

    return {
        "base_url": WC_URL.rstrip("/"),
        "headers": headers,
        "auth": (WC_KEY, WC_SECRET) if WC_KEY and WC_SECRET else None,
        "timeout": 15.0,
    }


# ============================================================================
# Mandatory Tool 1: list_products
# ============================================================================
@server.tool(
    name="list_products",
    description="Retrieve a paginated list of products from the WooCommerce store."
)
async def list_products(
    page: int = 1,
    per_page: int = 10,
    search: str = ""
) -> str:
    """List products from the WooCommerce catalog."""
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if search:
        params["search"] = search

    try:
        async with httpx.AsyncClient(**_get_client_kwargs()) as client:
            resp = await client.get("/wp-json/wc/v3/products", params=params)
            resp.raise_for_status()
            products = resp.json()

            clean_products = []
            for p in products:
                clean_products.append({
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "price": p.get("price"),
                    "regular_price": p.get("regular_price"),
                    "status": p.get("status"),
                    "stock_status": p.get("stock_status"),
                    "permalink": p.get("permalink"),
                    "categories": [c.get("name") for c in p.get("categories", [])],
                })
            return json.dumps(clean_products, indent=2)
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error listing products: {e.response.text}")
        return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        logger.error(f"Error listing products: {str(e)}")
        return json.dumps({"error": str(e)})


# ============================================================================
# Mandatory Tool 2: create_product
# ============================================================================
@server.tool(
    name="create_product",
    description="Create a new simple product in the WooCommerce store."
)
async def create_product(
    name: str,
    regular_price: str,
    description: str = "",
    short_description: str = ""
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

    try:
        async with httpx.AsyncClient(**_get_client_kwargs()) as client:
            resp = await client.post("/wp-json/wc/v3/products", json=payload)
            resp.raise_for_status()
            p = resp.json()

            return json.dumps({
                "success": True,
                "message": f"Product '{name}' created successfully.",
                "product": {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "price": p.get("price"),
                    "status": p.get("status"),
                    "permalink": p.get("permalink"),
                }
            }, indent=2)
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error creating product: {e.response.text}")
        return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        return json.dumps({"error": str(e)})


# ============================================================================
# Mandatory Tool 3: list_orders
# ============================================================================
@server.tool(
    name="list_orders",
    description="Retrieve a paginated list of store orders, optionally filtered by status."
)
async def list_orders(
    status: str = "",
    page: int = 1,
    per_page: int = 10
) -> str:
    """List orders from the WooCommerce store."""
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if status:
        params["status"] = status

    try:
        async with httpx.AsyncClient(**_get_client_kwargs()) as client:
            resp = await client.get("/wp-json/wc/v3/orders", params=params)
            resp.raise_for_status()
            orders = resp.json()

            clean_orders = []
            for o in orders:
                clean_orders.append({
                    "id": o.get("id"),
                    "status": o.get("status"),
                    "total": o.get("total"),
                    "currency": o.get("currency"),
                    "date_created": o.get("date_created"),
                    "customer_id": o.get("customer_id"),
                    "billing_name": f"{o.get('billing', {}).get('first_name', '')} {o.get('billing', {}).get('last_name', '')}".strip(),
                    "items": [
                        {
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "quantity": item.get("quantity"),
                            "total": item.get("total"),
                        }
                        for item in o.get("line_items", [])
                    ]
                })
            return json.dumps(clean_orders, indent=2)
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error listing orders: {e.response.text}")
        return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        logger.error(f"Error listing orders: {str(e)}")
        return json.dumps({"error": str(e)})


# ============================================================================
# Mandatory Tool 4: get_order
# ============================================================================
@server.tool(
    name="get_order",
    description="Get full details of a specific WooCommerce order by ID."
)
async def get_order(order_id: int) -> str:
    """Retrieve details for a single order by ID."""
    try:
        async with httpx.AsyncClient(**_get_client_kwargs()) as client:
            resp = await client.get(f"/wp-json/wc/v3/orders/{order_id}")
            resp.raise_for_status()
            o = resp.json()

            order_details = {
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
            }
            return json.dumps(order_details, indent=2)
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting order {order_id}: {e.response.text}")
        return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {str(e)}")
        return json.dumps({"error": str(e)})


# ============================================================================
# Mandatory Tool 5: update_order_status
# ============================================================================
@server.tool(
    name="update_order_status",
    description="Update the status of an existing WooCommerce order (e.g. 'completed', 'processing', 'cancelled')."
)
async def update_order_status(order_id: int, status: str) -> str:
    """Update order status."""
    valid_statuses = {"pending", "processing", "on-hold", "completed", "cancelled", "refunded", "failed", "trash"}
    clean_status = status.strip().lower()
    if clean_status not in valid_statuses:
        return json.dumps({
            "error": f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}"
        })

    try:
        async with httpx.AsyncClient(**_get_client_kwargs()) as client:
            resp = await client.put(f"/wp-json/wc/v3/orders/{order_id}", json={"status": clean_status})
            resp.raise_for_status()
            o = resp.json()

            return json.dumps({
                "success": True,
                "message": f"Order {order_id} status updated to '{clean_status}'.",
                "order": {
                    "id": o.get("id"),
                    "status": o.get("status"),
                    "date_modified": o.get("date_modified"),
                }
            }, indent=2)
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error updating order {order_id}: {e.response.text}")
        return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        logger.error(f"Error updating order {order_id}: {str(e)}")
        return json.dumps({"error": str(e)})


# ============================================================================
# Health Check Endpoint
# ============================================================================
@server.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Kubernetes liveness and readiness probe endpoint."""
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-woocommerce",
        "woocommerce_target": WC_URL
    })


from mcp.server.streamable_http import TransportSecuritySettings

# Build the ASGI app using Streamable HTTP with DNS rebinding protection disabled for internal Kubernetes networking
app = server.streamable_http_app(
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
)


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting WooCommerce MCP Server on port {PORT} (Streamable HTTP)")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

