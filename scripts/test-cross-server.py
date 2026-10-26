#!/usr/bin/env python3
"""
Cross-Server MCP Workflow Verification Script.
Connects to http://gateway.local/mcp (via localhost ingress) and executes a deterministic
multi-tool workflow chaining WooCommerce, Calculator, and Business Metrics upstreams.
"""

import sys
import json
import urllib.request
import urllib.error

GATEWAY_URL = "http://localhost/mcp"
HEADERS = {
    "Host": "gateway.local",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "User-Agent": "MCP-CrossServerTest/1.0"
}


def send_mcp_request(method: str, params: dict, req_id: int = 1) -> dict:
    """Sends a JSON-RPC request to the MCP Gateway and parses the SSE / JSON response."""
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(GATEWAY_URL, data=data, headers=HEADERS, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8").strip()
            # Parse possible SSE data lines
            for line in body.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:].strip())
            return json.loads(body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"❌ HTTP Error {e.code}: {error_body}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Request failed: {e}")
        sys.exit(1)


def main():
    print("=" * 70)
    print("🚀 TEAM MCP GATEWAY: CROSS-SERVER WORKFLOW VERIFICATION (PHASE 3)")
    print("=" * 70)

    # 1. Initialize Protocol
    print("\n[Step 1/5] Initializing MCP Protocol with Gateway...")
    init_res = send_mcp_request("initialize", {}, req_id=1)
    server_info = init_res.get("result", {}).get("serverInfo", {})
    print(f"   Connected to: {server_info.get('name')} v{server_info.get('version')}")
    assert server_info.get("name") == "team-mcp-gateway", "Unexpected server info"

    # 2. Discover Tools (tools/list)
    print("\n[Step 2/5] Querying Aggregated Tools (tools/list)...")
    tools_res = send_mcp_request("tools/list", {}, req_id=2)
    tools = tools_res.get("result", {}).get("tools", [])
    tool_names = [t["name"] for t in tools]
    print(f"   Aggregated {len(tools)} tools across 3 upstream servers:")
    for name in tool_names:
        print(f"     • {name}")

    expected_prefixes = ["woo__", "calc__", "metrics__"]
    for prefix in expected_prefixes:
        matching = [n for n in tool_names if n.startswith(prefix)]
        assert len(matching) > 0, f"No tools found with prefix '{prefix}'!"
    print("   ✅ Tool namespacing and aggregation verified.")

    # 3. Call Upstream 1: WooCommerce
    print("\n[Step 3/5] Upstream 1: Fetching store products via 'woo__list_products'...")
    woo_res = send_mcp_request("tools/call", {
        "name": "woo__list_products",
        "arguments": {"per_page": 2}
    }, req_id=3)
    woo_content = woo_res["result"]["content"][0]["text"]
    products = json.loads(woo_content)
    assert len(products) > 0, "No products returned from store!"
    first_product = products[0]
    product_name = first_product["name"]
    product_price = float(first_product["price"])
    print(f"   Retrieved Product: '{product_name}' at ${product_price:.2f}")

    # 4. Call Upstream 2: Calculator
    tax_rate = 8.5
    print(f"\n[Step 4/5] Upstream 2: Calculating sales tax for ${product_price:.2f} at {tax_rate}% via 'calc__tax_calculation'...")
    calc_res = send_mcp_request("tools/call", {
        "name": "calc__tax_calculation",
        "arguments": {
            "subtotal": product_price,
            "tax_rate_percent": tax_rate
        }
    }, req_id=4)
    calc_data = json.loads(calc_res["result"]["content"][0]["text"])
    tax_amount = calc_data["tax_amount"]
    final_total = calc_data["final_total"]
    print(f"   Tax Amount: ${tax_amount:.2f} | Final Order Total: ${final_total:.2f}")

    # 5. Call Upstream 3: Business Metrics
    target_sales = 250.0
    print(f"\n[Step 5/5] Upstream 3: Comparing gross sales (${final_total:.2f}) against target (${target_sales:.2f}) via 'metrics__calculate_revenue_summary'...")
    metrics_res = send_mcp_request("tools/call", {
        "name": "metrics__calculate_revenue_summary",
        "arguments": {
            "gross_sales": final_total,
            "target_sales": target_sales
        }
    }, req_id=5)
    metrics_data = json.loads(metrics_res["result"]["content"][0]["text"])
    attainment = metrics_data["attainment_percentage"]
    status_str = metrics_data["performance_status"]
    summary_str = metrics_data["summary"]
    print(f"   Attainment: {attainment:.1f}% ({status_str})")
    print(f"   Summary: {summary_str}")

    print("\n" + "=" * 70)
    print("🎉 CROSS-SERVER WORKFLOW COMPLETED SUCCESSFULLY!")
    print("   All 3 upstream servers (WooCommerce, Calculator, Metrics) seamlessly")
    print("   cooperated through a single unified endpoint: http://gateway.local/mcp")
    print("=" * 70)


if __name__ == "__main__":
    main()
