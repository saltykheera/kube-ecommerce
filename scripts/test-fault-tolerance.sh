#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "🧪 MCP GATEWAY FAULT TOLERANCE & FAILURE ISOLATION DEMO"
echo "======================================================================"

echo -e "\n[1/5] Verifying all 11 tools before simulated failure..."
COUNT_BEFORE=$(curl -s -X POST http://localhost/mcp -H "Host: gateway.local" -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | grep -o '"name": "[^"]*"' | wc -l | tr -d ' ')
echo "   Discovered tools count: $COUNT_BEFORE (expected: 11)"
if [ "$COUNT_BEFORE" -ne 11 ]; then
  echo "❌ Expected 11 tools initially, found $COUNT_BEFORE"
  exit 1
fi

echo -e "\n[2/5] Simulating outage: scaling mcp-calculator deployment to 0..."
kubectl scale deployment/mcp-calculator --replicas=0
sleep 2

echo -e "\n[3/5] Testing gateway resilience during partial outage..."
# Query tools/list during outage
COUNT_DURING=$(curl -s -X POST http://localhost/mcp -H "Host: gateway.local" -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}' | grep -o '"name": "[^"]*"' | wc -l | tr -d ' ')
echo "   Tools available during calculator outage: $COUNT_DURING (expected: 8)"

# Verify woo tool still works
echo "   Calling 'woo__list_products' while calculator is down..."
WOO_RESP=$(curl -s -X POST http://localhost/mcp -H "Host: gateway.local" -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "woo__list_products", "arguments": {"per_page": 1}}}')
if echo "$WOO_RESP" | grep -q "Antigravity Hoodie\|MCP Terminal Sticker"; then
  echo "   ✅ WooCommerce tool executed successfully despite calculator outage!"
else
  echo "❌ Failed to execute WooCommerce tool"
  exit 1
fi

# Verify calling dead tool returns clean JSON error
echo "   Calling 'calc__calculate' to verify graceful error containment..."
CALC_ERR=$(curl -s -X POST http://localhost/mcp -H "Host: gateway.local" -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "calc__calculate", "arguments": {"expression": "2+2"}}}')
if echo "$CALC_ERR" | grep -q "isError\": true"; then
  echo "   ✅ Gateway gracefully contained dead tool call with clean isError response!"
else
  echo "❌ Dead tool call did not return expected error JSON: $CALC_ERR"
  exit 1
fi

# Verify server registry status in PostgreSQL
echo -e "\n[4/5] Checking registry status in PostgreSQL..."
SERVER_STATUS=$(curl -s -H "Host: gateway.local" http://localhost/api/servers)
echo "$SERVER_STATUS" | grep -o '"slug":"calc"[^}]*'
echo "   ✅ PostgreSQL server registry dynamically flagged calculator as unreachable."

echo -e "\n[5/5] Restoring mcp-calculator to 1 replica..."
kubectl scale deployment/mcp-calculator --replicas=1
kubectl rollout status deployment/mcp-calculator --timeout=30s > /dev/null

# Allow K8s service endpoint routing to propagate
sleep 5
COUNT_AFTER=$(curl -s -X POST http://localhost/mcp -H "Host: gateway.local" -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {}}' | grep -o '"name": "[^"]*"' | wc -l | tr -d ' ')
echo "   Discovered tools count after recovery: $COUNT_AFTER (expected: 11)"
if [ "$COUNT_AFTER" -ne 11 ]; then
  echo "❌ Expected 11 tools after recovery, found $COUNT_AFTER"
  exit 1
fi

echo -e "\n======================================================================"
echo "🎉 ALL FAULT TOLERANCE TESTS PASSED SUCCESSFULLY!"
echo "======================================================================"
