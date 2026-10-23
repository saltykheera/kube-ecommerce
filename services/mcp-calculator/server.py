"""
Calculator & Financial Math MCP Server.
Provides deterministic arithmetic, tax calculation, and discount computations over Streamable HTTP.
"""

import os
import ast
import json
import logging
import operator as op
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from mcp.server.streamable_http import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp-calculator")

PORT = int(os.getenv("PORT", "8001"))

# Initialize MCP Server
server = MCPServer(
    name="calculator-mcp",
    version="1.0.0",
    instructions="Provides deterministic arithmetic, percentage, tax, and discount calculation tools."
)

# Safe AST-based Math Evaluator
ALLOWED_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def _eval_expr(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
        left = _eval_expr(node.left)
        right = _eval_expr(node.right)
        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Division by zero is not allowed.")
        return ALLOWED_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _eval_expr(node.operand)
        return ALLOWED_OPERATORS[op_type](operand)
    else:
        raise ValueError(f"Unsupported AST node expression: {type(node).__name__}")


def evaluate_math(expression: str) -> float:
    """Safely evaluates a basic mathematical expression string."""
    clean_expr = expression.strip().replace("^", "**")
    parsed = ast.parse(clean_expr, mode="eval")
    return _eval_expr(parsed.body)


# ============================================================================
# Tool 1: calculate
# ============================================================================
@server.tool(
    name="calculate",
    description="Safely evaluate a mathematical expression (supports +, -, *, /, %, ** and parentheses)."
)
async def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    try:
        result = evaluate_math(expression)
        return json.dumps({
            "expression": expression,
            "result": round(result, 4) if isinstance(result, float) else result,
            "status": "success"
        }, indent=2)
    except ZeroDivisionError:
        return json.dumps({"error": "Division by zero is undefined.", "status": "error"})
    except Exception as e:
        return json.dumps({"error": f"Invalid expression: {str(e)}", "status": "error"})


# ============================================================================
# Tool 2: tax_calculation
# ============================================================================
@server.tool(
    name="tax_calculation",
    description="Calculate sales tax and the final order total given a subtotal and tax rate percentage."
)
async def tax_calculation(subtotal: float, tax_rate_percent: float) -> str:
    """Calculate sales tax and gross total."""
    if subtotal < 0:
        return json.dumps({"error": "Subtotal must be non-negative.", "status": "error"})
    if tax_rate_percent < 0:
        return json.dumps({"error": "Tax rate must be non-negative.", "status": "error"})

    tax_amount = round(subtotal * (tax_rate_percent / 100.0), 2)
    final_total = round(subtotal + tax_amount, 2)

    return json.dumps({
        "subtotal": round(subtotal, 2),
        "tax_rate_percent": tax_rate_percent,
        "tax_amount": tax_amount,
        "final_total": final_total,
        "status": "success"
    }, indent=2)


# ============================================================================
# Tool 3: discount_rate
# ============================================================================
@server.tool(
    name="discount_rate",
    description="Calculate the discount savings and discounted net price given an original price and discount percentage."
)
async def discount_rate(original_price: float, discount_percent: float) -> str:
    """Calculate discount amount and final discounted price."""
    if original_price < 0:
        return json.dumps({"error": "Original price must be non-negative.", "status": "error"})
    if not (0 <= discount_percent <= 100):
        return json.dumps({"error": "Discount percentage must be between 0 and 100.", "status": "error"})

    savings = round(original_price * (discount_percent / 100.0), 2)
    net_price = round(original_price - savings, 2)

    return json.dumps({
        "original_price": round(original_price, 2),
        "discount_percent": discount_percent,
        "savings": savings,
        "net_price": net_price,
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
        "service": "mcp-calculator"
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
    logger.info(f"Starting Calculator MCP Server on port {PORT} (Streamable HTTP)")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
