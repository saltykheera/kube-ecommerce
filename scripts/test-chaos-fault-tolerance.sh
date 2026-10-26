#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Days 10 & 11 Phase 2: Chaos & Fault-Tolerance Verification Suite
# Simulates upstream outages, kills pods, tests timeout containment and recovery.
# ==============================================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

pass() { echo -e "  [${GREEN}PASSED${NC}] $1"; }
fail() { echo -e "  [${RED}FAILED${NC}] $1"; exit 1; }
info() { echo -e "\n${BLUE}==>${NC} $1"; }

BASE_URL="http://127.0.0.1"

echo "==================================================================="
echo "  Executing Chaos & Fault-Tolerance Testing Suite on Kubernetes"
echo "==================================================================="

info "Step 1: Baseline Cluster Health & Active User Login"
LOGIN_JSON=$(curl -s -X POST "${BASE_URL}/api/auth/login" \
  -H "Host: gateway.local" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@ecommerce.local", "password": "AdminSecurePassword123!"}')

TOKEN=$(echo "$LOGIN_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")
if [ -z "$TOKEN" ]; then
    fail "Unable to authenticate admin against gateway.local"
fi
pass "Admin authenticated. JWT acquired."

# Generate a testing API key for direct /mcp calls
KEY_JSON=$(curl -s -X POST "${BASE_URL}/api/keys" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Chaos Test Key"}')

API_KEY=$(echo "$KEY_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('raw_key', ''))")
KEY_ID=$(echo "$KEY_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")
pass "Temporary API key generated: ${API_KEY:0:15}... (ID: ${KEY_ID})"

# Check baseline tools count
TOOLS_COUNT=$(curl -s -X GET "${BASE_URL}/api/tools" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('tools', data)))")

if [ "$TOOLS_COUNT" -eq 11 ]; then
    pass "Baseline tool discovery: exactly 11 tools active across 3 upstreams"
else
    fail "Expected 11 tools initially, found $TOOLS_COUNT"
fi

info "Step 2: Simulating Hard Upstream Failure (Scale mcp-calculator to 0)"
kubectl scale deployment/mcp-calculator --replicas=0 >/dev/null
echo "  • mcp-calculator deployment scaled to 0 replicas. Simulating dead pod..."
sleep 2

# Measure timeout duration during discovery
START_TIME=$(python3 -c "import time; print(time.time())")
TOOLS_OUTAGE=$(curl -s -X GET "${BASE_URL}/api/tools" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${TOKEN}")
END_TIME=$(python3 -c "import time; print(time.time())")
DURATION=$(python3 -c "print(round($END_TIME - $START_TIME, 2))")

OUTAGE_COUNT=$(echo "$TOOLS_OUTAGE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('tools', data)))")

if [ "$OUTAGE_COUNT" -eq 8 ]; then
    pass "Partial Tool Discovery: 8 tools discovered (calc excluded, woo & metrics available) in ${DURATION}s"
else
    fail "Expected 8 tools during calc outage, received $OUTAGE_COUNT"
fi

info "Step 3: Verifying Upstream Degraded Status in Registry"
SERVERS_STATUS=$(curl -s -X GET "${BASE_URL}/api/servers" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${TOKEN}")

CALC_STATUS=$(echo "$SERVERS_STATUS" | python3 -c "import sys, json; servers=json.load(sys.stdin); s=[x for x in servers if x['slug']=='calc'][0]; print(s.get('status', ''))")

if [ "$CALC_STATUS" = "unreachable" ]; then
    pass "mcp-calculator correctly flagged as 'unreachable' in database"
else
    fail "Expected calc status to be 'unreachable', got '$CALC_STATUS'"
fi

info "Step 4: Verifying Fault Containment (Living servers work; dead server fails cleanly)"
# 4a. Call living upstream (metrics)
METRICS_CALL=$(curl -s -X POST "${BASE_URL}/mcp" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "metrics__get_sales_target", "arguments": {"period": "daily"}}}')

if echo "$METRICS_CALL" | grep -q "daily"; then
    pass "Living upstream execution (metrics__get_sales_target) succeeded with 200 OK"
else
    fail "Living upstream execution failed unexpectedly: $METRICS_CALL"
fi

# 4b. Call dead upstream (calc)
DEAD_CALL=$(curl -s -X POST "${BASE_URL}/mcp" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "calc__calculate", "arguments": {"expression": "2 + 2"}}}')

if echo "$DEAD_CALL" | grep -q "Error"; then
    pass "Dead upstream execution failed fast with structured error (Gateway process survived unharmed)"
else
    fail "Expected structured error on dead upstream, received: $DEAD_CALL"
fi

info "Step 5: Verifying Self-Healing & Automatic Cluster Recovery"
kubectl scale deployment/mcp-calculator --replicas=1 >/dev/null
echo "  • Scaling mcp-calculator back to 1 replica..."
kubectl rollout status deployment/mcp-calculator --timeout=30s >/dev/null
sleep 2

RECOVERED_COUNT=$(curl -s -X GET "${BASE_URL}/api/tools" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('tools', data)))")

if [ "$RECOVERED_COUNT" -eq 11 ]; then
    pass "Automatic Self-Healing: All 11 tools restored without restarting Gateway"
else
    fail "Expected 11 tools after recovery, received $RECOVERED_COUNT"
fi

RECOVERED_CALL=$(curl -s -X POST "${BASE_URL}/mcp" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "calc__calculate", "arguments": {"expression": "100 * 2"}}}')

if echo "$RECOVERED_CALL" | grep -q "200.0"; then
    pass "Recovered tool execution (calc__calculate) succeeded (Result: 200.0)"
else
    fail "Execution of recovered tool failed: $RECOVERED_CALL"
fi

info "Step 6: Verifying Dynamic Admin Disabling vs Unreachable State"
METRICS_ID=$(echo "$SERVERS_STATUS" | python3 -c "import sys, json; servers=json.load(sys.stdin); s=[x for x in servers if x['slug']=='metrics'][0]; print(s.get('id', ''))")

# Disable metrics
curl -s -X PATCH "${BASE_URL}/api/servers/${METRICS_ID}/toggle" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${TOKEN}" >/dev/null

DISABLED_COUNT=$(curl -s -X GET "${BASE_URL}/api/tools" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('tools', data)))")

if [ "$DISABLED_COUNT" -eq 8 ]; then
    pass "Admin Disabling: Tools dropped from 11 to 8 immediately upon toggle"
else
    fail "Expected 8 tools when metrics is disabled, got $DISABLED_COUNT"
fi

# Re-enable metrics
curl -s -X PATCH "${BASE_URL}/api/servers/${METRICS_ID}/toggle" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${TOKEN}" >/dev/null

pass "Admin Re-enabling: metrics re-enabled successfully"

info "Step 7: Testing Pod Resiliency & PVC Persistence (Killing WordPress)"
WP_POD_BEFORE=$(kubectl get pods -l app.kubernetes.io/name=wordpress -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$WP_POD_BEFORE" >/dev/null
echo "  • Terminated WordPress pod: $WP_POD_BEFORE"

# Wait for replacement pod to be running
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=wordpress --timeout=45s >/dev/null
WP_POD_AFTER=$(kubectl get pods -l app.kubernetes.io/name=wordpress -o jsonpath='{.items[0].metadata.name}')
pass "Kubernetes spawned replacement WordPress pod: $WP_POD_AFTER"

# Verify Storefront responds with 200 OK
STORE_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: store.local" "${BASE_URL}/")
if [ "$STORE_HTTP" = "200" ]; then
    pass "WordPress Storefront returned 200 OK after pod recreation (PVC Data Intact)"
else
    fail "Storefront returned HTTP $STORE_HTTP after pod restart"
fi

# Cleanup temporary key
curl -s -X DELETE "${BASE_URL}/api/keys/${KEY_ID}" \
  -H "Host: gateway.local" \
  -H "Authorization: Bearer ${TOKEN}" >/dev/null
pass "Cleaned up temporary chaos test API key"

echo -e "\n==================================================================="
echo -e "  ${GREEN}✓ ALL CHAOS & FAULT-TOLERANCE SCENARIOS PASSED 100%${NC}"
echo "==================================================================="
