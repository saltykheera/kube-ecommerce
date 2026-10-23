#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="ecommerce-cluster"

echo "=== [1/3] Checking Docker daemon ==="
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker daemon is not running. Please start Docker Desktop first."
    exit 1
fi
echo "Docker is running."

echo "=== [2/3] Checking / creating k3d cluster: ${CLUSTER_NAME} ==="
if k3d cluster list | grep -q "^${CLUSTER_NAME} "; then
    echo "Cluster '${CLUSTER_NAME}' already exists."
else
    echo "Creating k3d cluster with Traefik ingress mapped to ports 80 and 443..."
    k3d cluster create "${CLUSTER_NAME}" \
        --agents 1 \
        --port "80:80@loadbalancer" \
        --port "443:443@loadbalancer" \
        --wait
fi

echo "=== [3/3] Checking cluster nodes and context ==="
kubectl cluster-info
kubectl get nodes

echo ""
echo " Cluster '${CLUSTER_NAME}' is ready!"
echo "Next step: Helm deployment or local /etc/hosts mapping (store.local, gateway.local, dashboard.local)."
