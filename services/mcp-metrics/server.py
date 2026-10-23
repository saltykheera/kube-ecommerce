"""
Business Metrics and Store Analytics MCP Server.
Provides business sales targets, revenue comparison, and inventory analytics over Streamable HTTP.
"""

import os
import json
import logging
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from mcp.server.streamable_http import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp-metrics")

PORT = int(os.getenv("PORT", "8002"))

# Initialize MCP Server
server = MCPServer(
    name="metrics-mcp",
    version="1.0.0",
    instructions="Provides business intelligence tools: sales targets, revenue performance analysis, and inventory thresholds."
)

DEFAULT_TARGETS = {
    "daily": 500.0,
    "weekly": 3500.0,
    "monthly": 15000.0,
    "quarterly": 45000.0,
}


# ============================================================================
# Tool 1: get_sales_target
# ============================================================================
@server.tool(
    name="get_sales_target",
    description="Retrieve the configured business sales target for a specified period (daily, weekly, monthly, quarterly)."
)
async def get_sales_target(period: str = "daily") -> str:
    """Retrieve sales target benchmark."""
    clean_period = period.strip().lower()
    target = DEFAULT_TARGETS.get(clean_period)

    if target is None:
        return json.dumps({
            "error": f"Invalid period '{period}'. Supported periods: {', '.join(DEFAULT_TARGETS.keys())}",
            "status": "error"
        })

    return json.dumps({
        "period": clean_period,
        "target_amount": target,
        "currency": "USD",
        "description": f"Standard {clean_period} revenue quota for the ecommerce storefront.",
        "status": "success"
    }, indent=2)


# ============================================================================
# Tool 2: calculate_revenue_summary
# ============================================================================
@server.tool(
    name="calculate_revenue_summary",
    description="Analyze actual gross sales against target revenue to compute attainment percentage and variance."
)
async def calculate_revenue_summary(gross_sales: float, target_sales: float = 500.0) -> str:
    """Compare gross store sales against a revenue target."""
    if gross_sales < 0:
        return json.dumps({"error": "Gross sales cannot be negative.", "status": "error"})
    if target_sales <= 0:
        return json.dumps({"error": "Target sales must be greater than zero.", "status": "error"})

    variance = round(gross_sales - target_sales, 2)
    attainment_pct = round((gross_sales / target_sales) * 100.0, 1)

    if attainment_pct >= 100.0:
        performance_status = "target_exceeded"
    elif attainment_pct >= 80.0:
        performance_status = "on_track"
    else:
        performance_status = "underperforming"

    return json.dumps({
        "gross_sales": round(gross_sales, 2),
        "target_sales": round(target_sales, 2),
        "variance": variance,
        "attainment_percentage": attainment_pct,
        "performance_status": performance_status,
        "currency": "USD",
        "summary": f"Store achieved {attainment_pct}% of the ${target_sales:.2f} target (${variance:+.2f}).",
        "status": "success"
    }, indent=2)


# ============================================================================
# Tool 3: get_inventory_thresholds
# ============================================================================
@server.tool(
    name="get_inventory_thresholds",
    description="Retrieve stock management warning thresholds (low stock warning, critical stock, and reorder batch quantity)."
)
async def get_inventory_thresholds() -> str:
    """Return inventory risk thresholds."""
    return json.dumps({
        "low_stock_warning": 5,
        "critical_out_of_stock": 1,
        "recommended_reorder_batch": 25,
        "safety_stock_buffer": 3,
        "status": "success"
    }, indent=2)


# ============================================================================
# Health Check Endpoint
# ============================================================================
@server.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Kubernetes liveness and readiness probe endpoint."""
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-metrics"
    })


# Build Streamable HTTP app
app = server.streamable_http_app(
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
)

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Metrics MCP Server on port {PORT} (Streamable HTTP)")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
