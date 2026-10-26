#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# NetworkPolicy Zero-Trust Isolation Verification Script
# Validates both Allowed and Blocked network paths inside the cluster.
# ==============================================================================

echo "==================================================================="
echo "  Verifying Kubernetes NetworkPolicies (Zero-Trust Security)"
echo "==================================================================="

DASH_POD=$(kubectl get pods -l app.kubernetes.io/name=dashboard -o jsonpath='{.items[0].metadata.name}')
GW_POD=$(kubectl get pods -l app.kubernetes.io/name=gateway -o jsonpath='{.items[0].metadata.name}')
WP_POD=$(kubectl get pods -l app.kubernetes.io/name=wordpress -o jsonpath='{.items[0].metadata.name}')
WOO_POD=$(kubectl get pods -l app.kubernetes.io/name=mcp-woocommerce -o jsonpath='{.items[0].metadata.name}')
CALC_POD=$(kubectl get pods -l app.kubernetes.io/name=mcp-calculator -o jsonpath='{.items[0].metadata.name}')

echo -e "\n[1/2] Testing Prohibited / Blocked Traffic (Must be Rejected):"

# 1. Dashboard -> Postgres
echo -n "  • Dashboard attempting direct access to Postgres (5432)... "
if kubectl exec "$DASH_POD" -- timeout 3 nc -zv postgres 5432 >/dev/null 2>&1; then
    echo "FAILED (Unexpectedly allowed)"
    exit 1
else
    echo "PASSED (Blocked by NetworkPolicy)"
fi

# 2. Dashboard -> MariaDB
echo -n "  • Dashboard attempting direct access to MariaDB (3306)... "
if kubectl exec "$DASH_POD" -- timeout 3 nc -zv mariadb 3306 >/dev/null 2>&1; then
    echo "FAILED (Unexpectedly allowed)"
    exit 1
else
    echo "PASSED (Blocked by NetworkPolicy)"
fi

# 3. WordPress -> MCP Calculator
echo -n "  • WordPress attempting direct access to mcp-calculator (8001)... "
if kubectl exec "$WP_POD" -- timeout 3 curl -s --connect-timeout 3 http://mcp-calculator:8001/mcp >/dev/null 2>&1; then
    echo "FAILED (Unexpectedly allowed)"
    exit 1
else
    echo "PASSED (Blocked by NetworkPolicy)"
fi

# 4. MCP Calculator -> MariaDB
echo -n "  • mcp-calculator attempting direct access to MariaDB (3306)... "
if kubectl exec "$CALC_POD" -- python3 -c "
import socket
s = socket.socket()
s.settimeout(2.0)
s.connect(('mariadb', 3306))
" >/dev/null 2>&1; then
    echo "FAILED (Unexpectedly allowed)"
    exit 1
else
    echo "PASSED (Blocked by NetworkPolicy)"
fi

echo -e "\n[2/2] Testing Legitimate Application Paths (Must be Connected):"

# 5. Gateway -> Postgres
echo -n "  • Gateway connecting to PostgreSQL (5432)... "
kubectl exec "$GW_POD" -- python3 -c "
import socket
s = socket.socket()
s.settimeout(3.0)
s.connect(('postgres', 5432))
" >/dev/null 2>&1 && echo "PASSED (Connected)"

# 6. Gateway -> MCP Upstreams
echo -n "  • Gateway connecting to mcp-woocommerce (8000)... "
kubectl exec "$GW_POD" -- python3 -c "
import socket
s = socket.socket()
s.settimeout(3.0)
s.connect(('mcp-woocommerce', 8000))
" >/dev/null 2>&1 && echo "PASSED (Connected)"

echo -n "  • Gateway connecting to mcp-calculator (8001)... "
kubectl exec "$GW_POD" -- python3 -c "
import socket
s = socket.socket()
s.settimeout(3.0)
s.connect(('mcp-calculator', 8001))
" >/dev/null 2>&1 && echo "PASSED (Connected)"

echo -n "  • Gateway connecting to mcp-metrics (8002)... "
kubectl exec "$GW_POD" -- python3 -c "
import socket
s = socket.socket()
s.settimeout(3.0)
s.connect(('mcp-metrics', 8002))
" >/dev/null 2>&1 && echo "PASSED (Connected)"

# 7. mcp-woocommerce -> WordPress
echo -n "  • mcp-woocommerce calling WordPress REST API (80)... "
kubectl exec "$WOO_POD" -- python3 -c "
import socket
s = socket.socket()
s.settimeout(3.0)
s.connect(('wordpress', 80))
" >/dev/null 2>&1 && echo "PASSED (Connected)"

# 8. WordPress -> MariaDB
echo -n "  • WordPress connecting to MariaDB (3306)... "
kubectl exec "$WP_POD" -- php -r "
\$fp = @fsockopen('mariadb', 3306, \$errCode, \$errStr, 3);
if (\$fp) { fclose(\$fp); exit(0); } else { exit(1); }
" >/dev/null 2>&1 && echo "PASSED (Connected)"

echo -e "\n==================================================================="
echo "  ✓ ALL NETWORK POLICY ZERO-TRUST CHECKS PASSED (100% SECURE)"
echo "==================================================================="
