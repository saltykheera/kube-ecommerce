"""Contract checks with mocked HTTP; no running store or credentials required."""

import json
import unittest
from unittest.mock import patch

import httpx
from mcp.server.mcpserver import MCPServer
from starlette.testclient import TestClient

from server import app
from woocommerce_mcp.client import WooCommerceClient
from woocommerce_mcp.config import Settings
from woocommerce_mcp.tools import register_tools
from woocommerce_mcp.tools.create_product import build_tool as create_product
from woocommerce_mcp.tools.get_order import build_tool as get_order
from woocommerce_mcp.tools.list_orders import build_tool as list_orders
from woocommerce_mcp.tools.list_products import build_tool as list_products
from woocommerce_mcp.tools.update_order_status import build_tool as update_order_status


class ToolTests(unittest.IsolatedAsyncioTestCase):
    def client(self, handler):
        return WooCommerceClient(
            Settings(url="http://store.test/", consumer_key="key", consumer_secret="secret"),
            transport=httpx.MockTransport(handler),
        )

    async def test_public_schemas_and_mcp_invocation(self):
        server = MCPServer("test")
        register_tools(server, self.client(lambda req: httpx.Response(200, json={"id": 7})))
        schemas = {tool.name: tool.input_schema for tool in await server.list_tools()}
        expected = {
            "list_products": ({"page", "per_page", "search"}, set()),
            "create_product": (
                {"name", "regular_price", "description", "short_description"},
                {"name", "regular_price"},
            ),
            "list_orders": ({"status", "page", "per_page"}, set()),
            "get_order": ({"order_id"}, {"order_id"}),
            "update_order_status": ({"order_id", "status"}, {"order_id", "status"}),
        }
        self.assertEqual(set(schemas), set(expected))
        for name, (properties, required) in expected.items():
            self.assertEqual(set(schemas[name]["properties"]), properties)
            self.assertEqual(set(schemas[name].get("required", [])), required)
        self.assertEqual(schemas["list_products"]["properties"]["per_page"]["default"], 10)
        result = await server.call_tool("get_order", {"order_id": 7})
        self.assertFalse(result.is_error)
        self.assertEqual(json.loads(result.content[0].text)["id"], 7)

    async def test_list_products_filters_headers_auth_and_projection(self):
        def handle(request):
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.path, "/wp-json/wc/v3/products")
            self.assertEqual(dict(request.url.params), {"page": "2", "per_page": "5", "search": "shirt"})
            self.assertEqual(request.headers["host"], "store.local")
            self.assertEqual(request.headers["authorization"], "Basic a2V5OnNlY3JldA==")
            return httpx.Response(200, json=[{
                "id": 1, "name": "Shirt", "categories": [{"name": "Clothes"}], "private": 1,
            }])
        result = json.loads(await list_products(self.client(handle))(2, 5, "shirt"))
        self.assertEqual(result[0]["categories"], ["Clothes"])
        self.assertNotIn("private", result[0])

    async def test_create_product_payload_and_response(self):
        def handle(request):
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.url.path, "/wp-json/wc/v3/products")
            self.assertEqual(json.loads(request.content), {
                "name": "Shirt", "regular_price": "12.00", "type": "simple",
                "status": "publish", "description": "Cotton", "short_description": "Soft",
            })
            return httpx.Response(201, json={"id": 3, "name": "Shirt", "price": "12.00"})
        result = json.loads(await create_product(self.client(handle))("Shirt", "12.00", "Cotton", "Soft"))
        self.assertTrue(result["success"])
        self.assertEqual(result["product"]["id"], 3)

    async def test_list_orders_filter_and_projection(self):
        def handle(request):
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.path, "/wp-json/wc/v3/orders")
            self.assertEqual(dict(request.url.params), {"page": "1", "per_page": "10", "status": "processing"})
            return httpx.Response(200, json=[{
                "id": 4, "billing": {"first_name": "Ada", "last_name": "Lovelace"},
                "line_items": [{"id": 9, "name": "Shirt", "quantity": 2, "total": "24.00"}],
            }])
        result = json.loads(await list_orders(self.client(handle))(status="processing"))
        self.assertEqual(result[0]["billing_name"], "Ada Lovelace")
        self.assertEqual(result[0]["items"][0]["quantity"], 2)

    async def test_get_order_details(self):
        def handle(request):
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.path, "/wp-json/wc/v3/orders/4")
            return httpx.Response(200, json={
                "id": 4, "billing": {"first_name": "Ada"}, "shipping": {"city": "London"},
                "line_items": [{"product_id": 3, "subtotal": "12.00"}],
            })
        result = json.loads(await get_order(self.client(handle))(4))
        self.assertEqual(result["shipping"], {"city": "London"})
        self.assertEqual(result["items"][0]["product_id"], 3)

    async def test_update_status_normalization_and_validation(self):
        requests = []
        def handle(request):
            requests.append(request)
            self.assertEqual(request.method, "PUT")
            self.assertEqual(request.url.path, "/wp-json/wc/v3/orders/4")
            self.assertEqual(json.loads(request.content), {"status": "completed"})
            return httpx.Response(200, json={"id": 4, "status": "completed"})
        tool = update_order_status(self.client(handle))
        result = json.loads(await tool(4, " Completed "))
        self.assertEqual(result["order"]["status"], "completed")
        self.assertIn("Invalid status", json.loads(await tool(4, "invalid"))["error"])
        self.assertEqual(len(requests), 1)

    async def test_shared_error_contract(self):
        for factory, args in [
            (list_products, ()), (create_product, ("Shirt", "12.00")),
            (list_orders, ()), (get_order, (4,)), (update_order_status, (4, "completed")),
        ]:
            with self.subTest(tool=factory.__module__):
                client = self.client(lambda req: httpx.Response(401, text="Unauthorized"))
                self.assertEqual(json.loads(await factory(client)(*args)), {"error": "HTTP 401: Unauthorized"})

        def timeout(request):
            raise httpx.ReadTimeout("Store timed out", request=request)
        self.assertEqual(
            json.loads(await get_order(self.client(timeout))(4)), {"error": "Store timed out"}
        )
        invalid_json = self.client(lambda req: httpx.Response(200, text="not JSON"))
        self.assertIn("error", json.loads(await get_order(invalid_json)(4)))


class ConfigurationTests(unittest.TestCase):
    def test_environment_precedence_and_secret_repr(self):
        with patch.dict("os.environ", {
            "WOOCOMMERCE_INTERNAL_URL": "http://internal", "WOOCOMMERCE_URL": "http://external",
            "WOOCOMMERCE_CONSUMER_KEY": "private-key", "WOOCOMMERCE_CONSUMER_SECRET": "private-secret",
            "PORT": "9000",
        }, clear=True):
            settings = Settings.from_env()
        self.assertEqual(settings.url, "http://internal")
        self.assertEqual(settings.port, 9000)
        self.assertNotIn("private-key", repr(settings))
        self.assertNotIn("private-secret", repr(settings))

    def test_health_endpoint(self):
        with TestClient(app) as client:
            response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["service"], "mcp-woocommerce")


if __name__ == "__main__":
    unittest.main()
