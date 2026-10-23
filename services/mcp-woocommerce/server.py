"""WooCommerce MCP entry point (Streamable HTTP)."""

import logging

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from mcp.server.streamable_http import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from woocommerce_mcp.client import WooCommerceClient
from woocommerce_mcp.config import Settings
from woocommerce_mcp.tools import register_tools

logger = logging.getLogger("woocommerce-mcp")


def create_server(settings: Settings) -> MCPServer:
    """Compose an isolated MCP server with all five WooCommerce tools."""
    server = MCPServer(
        name="woocommerce-mcp",
        version="1.0.0",
        instructions="Provides tools to manage WooCommerce products, orders, and store operations.",
    )
    register_tools(server, WooCommerceClient(settings))

    @server.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        """Kubernetes liveness endpoint; does not contact WooCommerce."""
        return JSONResponse({
            "status": "healthy",
            "service": "mcp-woocommerce",
            "woocommerce_target": settings.url,
        })

    return server


load_dotenv()
settings = Settings.from_env()
server = create_server(settings)
# Preserve the existing internal Kubernetes transport configuration.
app = server.streamable_http_app(
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger.info("Starting WooCommerce MCP Server on port %s (Streamable HTTP)", settings.port)
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
