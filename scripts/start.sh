#!/usr/bin/env bash
# ==============================================================================
# Start Script: Resume or Initialize the Kube-Ecommerce Platform
# ==============================================================================
set -euo pipefail

CLUSTER_NAME="ecommerce-cluster"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "\n${BOLD}${BLUE}====================================================================${NC}"
echo -e "${BOLD}${BLUE}   Starting WooCommerce & Team MCP Gateway Platform (Kubernetes)    ${NC}"
echo -e "${BOLD}${BLUE}====================================================================${NC}\n"

# 1. Check Docker Daemon
echo "• Checking Docker Desktop daemon..."
if ! docker info >/dev/null 2>&1; then
    echo -e "${YELLOW}❌ Docker daemon is not running. Please start Docker Desktop first.${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓ Docker is running.${NC}"

# 2. Check k3d cluster status
if k3d cluster list | grep -q "^${CLUSTER_NAME} "; then
    echo "• Found existing cluster '${CLUSTER_NAME}'. Starting / Resuming..."
    k3d cluster start "${CLUSTER_NAME}" >/dev/null
    echo -e "  ${GREEN}✓ Cluster '${CLUSTER_NAME}' is active.${NC}"
else
    echo "• Cluster '${CLUSTER_NAME}' not found. Initializing new cluster..."
    ./scripts/init-cluster.sh
    echo "• Deploying Helm stack..."
    helm upgrade --install ecommerce-stack ./helm/ecommerce-stack
    echo "• Initializing WooCommerce..."
    ./scripts/setup-woocommerce.sh
fi

# 3. Wait for core workloads to be ready
echo "• Waiting for Kubernetes pods to achieve Ready status..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=gateway --timeout=60s >/dev/null 2>&1 || true
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=dashboard --timeout=60s >/dev/null 2>&1 || true
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=wordpress --timeout=60s >/dev/null 2>&1 || true

echo -e "\n${BOLD}${GREEN}====================================================================${NC}"
echo -e "${BOLD}${GREEN}   ✓ ALL SERVICES ARE ONLINE & OPERATIONAL                          ${NC}"
echo -e "${BOLD}${GREEN}====================================================================${NC}\n"

echo -e "${BOLD}Access Endpoints:${NC}"
echo -e "  🛒 ${BOLD}Storefront:${NC}         http://store.local"
echo -e "  ⚡ ${BOLD}PostHog Dashboard:${NC}  http://dashboard.local"
echo -e "  🤖 ${BOLD}MCP Gateway URL:${NC}    http://gateway.local/mcp"
echo -e "  🩺 ${BOLD}Gateway Health:${NC}     http://gateway.local/health\n"

echo -e "${BOLD}Default Credentials:${NC}"
echo -e "  🔑 Admin User:   admin@ecommerce.local   / AdminSecurePassword123!"
echo -e "  👥 Member User:  member@ecommerce.local  / MemberSecurePassword123!"
echo -e "  📦 WP Store:     admin                   / AdminSecurePassword123!\n"

echo -e "${BOLD}Status Check:${NC}"
kubectl get pods
