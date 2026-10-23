# WooCommerce MCP service

Streamable HTTP MCP server exposing five WooCommerce tools. Run from this directory:

```sh
python -m pip install -r requirements.txt
python server.py
# Alternatively: uvicorn server:app --host 0.0.0.0 --port 8000
```

The MCP endpoint is `/mcp`; `/health` is a liveness check and does not check store connectivity.

## Structure

```text
server.py                         # Server assembly, health route, ASGI app, startup
woocommerce_mcp/
  config.py                       # Environment configuration
  client.py                       # HTTP access and shared JSON error handling
  tools/
    __init__.py                   # Explicit tool registration
    list_products.py
    create_product.py
    list_orders.py
    get_order.py
    update_order_status.py
tests/test_tools.py               # Mocked HTTP and MCP contract tests
```

Each tool module exposes `build_tool(client)`, returning a handler with its public MCP signature. Dependencies are injected through the factory instead of importing a global server. `register_tools` owns names and descriptions. To add a tool, add its module, register it explicitly, and test its API contract.

One file per tool works well while handlers have distinct payloads and responses. Shared HTTP behavior belongs in `client.py`; if substantial domain logic develops, move that into product/order services rather than duplicating it across handlers.

## Configuration

`.env` is loaded by the entry point. Environment variables retain their existing defaults:

| Variable | Purpose/default |
| --- | --- |
| `WOOCOMMERCE_INTERNAL_URL` | Preferred API base URL |
| `WOOCOMMERCE_URL` | Fallback URL; defaults to `http://wordpress.default.svc.cluster.local:80` |
| `WOOCOMMERCE_CONSUMER_KEY` | WooCommerce API key |
| `WOOCOMMERCE_CONSUMER_SECRET` | WooCommerce API secret |
| `WOOCOMMERCE_HOST_HEADER` | Host override; defaults to `store.local`; empty disables override |
| `PORT` | Direct startup port; defaults to `8000` |

The refactor preserves tool arguments, JSON string responses, the 15-second HTTP timeout, and per-request client cleanup. Errors retain the existing JSON contract. Automatic write retries are not added because creation requests may not be safe to repeat. The existing internal Kubernetes transport security configuration is retained; this refactor does not change deployment access controls.

## Tests

Using the service's installed dependencies:

```sh
python -m unittest discover -s tests -v
```

Tests use `httpx.MockTransport` and Starlette's test client. They cover discovery, schemas, MCP invocation, request construction, response projections, status validation, errors, configuration, and the health endpoint without contacting WooCommerce.
