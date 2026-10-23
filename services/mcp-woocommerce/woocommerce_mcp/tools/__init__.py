"""Explicit tool registration; tool modules do not import the server."""

from mcp.server.mcpserver import MCPServer

from ..client import WooCommerceClient
from .create_product import build_tool as build_create_product
from .get_order import build_tool as build_get_order
from .list_orders import build_tool as build_list_orders
from .list_products import build_tool as build_list_products
from .update_order_status import build_tool as build_update_order_status


def register_tools(server: MCPServer, client: WooCommerceClient) -> None:
    """Register the public WooCommerce tool contract on a server instance."""
    server.tool(
        name="list_products",
        description="Retrieve a paginated list of products from the WooCommerce store.",
    )(build_list_products(client))
    server.tool(
        name="create_product",
        description="Create a new simple product in the WooCommerce store.",
    )(build_create_product(client))
    server.tool(
        name="list_orders",
        description="Retrieve a paginated list of store orders, optionally filtered by status.",
    )(build_list_orders(client))
    server.tool(
        name="get_order",
        description="Get full details of a specific WooCommerce order by ID.",
    )(build_get_order(client))
    server.tool(
        name="update_order_status",
        description=(
            "Update the status of an existing WooCommerce order "
            "(e.g. 'completed', 'processing', 'cancelled')."
        ),
    )(build_update_order_status(client))
