#!/usr/bin/env bash
# ==============================================================================
# Stop Script: Safely Pause the Kube-Ecommerce Platform
# Preserves all database data, PVCs, and configurations on disk.
# ==============================================================================
set -euo pipefail

CLUSTER_NAME="ecommerce-cluster"
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "\n${BOLD}${YELLOW}====================================================================${NC}"
echo -e "${BOLD}${YELLOW}   Stopping WooCommerce & Team MCP Gateway Platform                 ${NC}"
echo -e "${BOLD}${YELLOW}====================================================================${NC}\n"

if k3d cluster list | grep -q "^${CLUSTER_NAME} "; then
    echo "• Stopping k3d cluster '${CLUSTER_NAME}'..."
    k3d cluster stop "${CLUSTER_NAME}" >/dev/null
    echo -e "  ${GREEN}✓ Cluster paused.${NC}"
    echo -e "  • All container processes are halted (CPU & Memory returned to your Mac)."
    echo -e "  • ${BOLD}All database records, orders, and persistent volumes (PVCs) remain 100% saved on disk.${NC}\n"
    echo -e "To resume anytime, run:  ${BOLD}./scripts/start.sh${NC}\n"
else
    echo "Cluster '${CLUSTER_NAME}' is not running."
fi
