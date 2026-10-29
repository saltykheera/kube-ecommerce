#!/usr/bin/env bash
# ==============================================================================
# Deploy eCommerce Stack & MCP Gateway onto AWS Cloud VPS (k3s)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PUBLIC_IP="${1:-}"
KEY_FILE="${ROOT_DIR}/${AWS_KEY_NAME:-ecommerce-vps-key}.pem"

if [ -z "${PUBLIC_IP}" ]; then
    echo "Usage: $0 <AWS_PUBLIC_IP>"
    exit 1
fi

if [ ! -f "${KEY_FILE}" ]; then
    echo "Error: Private key ${KEY_FILE} not found."
    exit 1
fi

echo "===================================================================="
echo "🚀 DEPLOYING STACK TO AWS VPS: ${PUBLIC_IP}"
echo "===================================================================="

# 1. Sync repository to remote instance (excluding heavy local virtualenvs/node_modules)
echo "📦 [1/5] Syncing project files to AWS VPS..."
rsync -avz -e "ssh -o StrictHostKeyChecking=no -i ${KEY_FILE}" \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '.venv' \
    --exclude '*.log' \
    --exclude 'kubeconfig-aws.yaml' \
    --exclude '*.pem' \
    --exclude '*_accessKeys.csv' \
    --exclude '.aws' \
    --exclude '.env*' \
    --exclude '*.env' \
    "${ROOT_DIR}/" ubuntu@"${PUBLIC_IP}":/home/ubuntu/kube-ecommerce/

# 2. Build or import local microservice images inside the remote VPS Docker daemon and k3s
echo "🐳 [2/5] Building images directly on AWS VPS..."
ssh -o StrictHostKeyChecking=no -i "${KEY_FILE}" ubuntu@"${PUBLIC_IP}" '
set -e
cd /home/ubuntu/kube-ecommerce

echo "Building ecommerce-gateway:local..."
docker build -t ecommerce-gateway:local services/gateway/
echo "Building ecommerce-dashboard:local..."
docker build -t ecommerce-dashboard:local services/dashboard/
echo "Building mcp-woocommerce:local..."
docker build -t mcp-woocommerce:local services/mcp-woocommerce/
echo "Building mcp-calculator:local..."
docker build -t mcp-calculator:local services/mcp-calculator/
echo "Building mcp-metrics:local..."
docker build -t mcp-metrics:local services/mcp-metrics/

echo "Importing images into k3s containerd..."
docker save ecommerce-gateway:local | sudo k3s ctr images import -
docker save ecommerce-dashboard:local | sudo k3s ctr images import -
docker save mcp-woocommerce:local | sudo k3s ctr images import -
docker save mcp-calculator:local | sudo k3s ctr images import -
docker save mcp-metrics:local | sudo k3s ctr images import -
'

# 3. Create nip.io / DNS values file for AWS Cloud VPS
echo "📝 [3/5] Configuring Helm values for cloud VPS ingress (${PUBLIC_IP}.nip.io)..."
ssh -o StrictHostKeyChecking=no -i "${KEY_FILE}" ubuntu@"${PUBLIC_IP}" "
cat << EOF > /home/ubuntu/kube-ecommerce/helm/ecommerce-stack/values-aws.yaml
global:
  domains:
    store: store.${PUBLIC_IP}.nip.io
    gateway: gateway.${PUBLIC_IP}.nip.io
    dashboard: dashboard.${PUBLIC_IP}.nip.io

# Ingress configuration with automatic nip.io wildcard DNS
ingress:
  annotations:
    kubernetes.io/ingress.class: traefik
  tls:
    enabled: false

mariadb:
  enabled: true
  persistence:
    size: 10Gi
    storageClass: local-path

wordpress:
  enabled: true
  persistence:
    size: 15Gi
    storageClass: local-path

postgres:
  enabled: true
  persistence:
    size: 10Gi
    storageClass: local-path

gateway:
  enabled: true
  image:
    repository: ecommerce-gateway
    tag: local
    pullPolicy: Never

dashboard:
  enabled: true
  image:
    repository: ecommerce-dashboard
    tag: local
    pullPolicy: Never

mcpUpstreams:
  woocommerce:
    enabled: true
    image:
      repository: mcp-woocommerce
      tag: local
      pullPolicy: Never
  calculator:
    enabled: true
    image:
      repository: mcp-calculator
      tag: local
      pullPolicy: Never
  metrics:
    enabled: true
    image:
      repository: mcp-metrics
      tag: local
      pullPolicy: Never
EOF
"

# 4. Deploy Helm Chart on remote VPS
echo "☸️  [4/5] Deploying Helm release 'ecommerce-stack'..."
ssh -o StrictHostKeyChecking=no -i "${KEY_FILE}" ubuntu@"${PUBLIC_IP}" '
export KUBECONFIG=/home/ubuntu/.kube/config
cd /home/ubuntu/kube-ecommerce
helm upgrade --install ecommerce-stack ./helm/ecommerce-stack -f ./helm/ecommerce-stack/values-aws.yaml
echo "Waiting for all pods to become ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=mariadb --timeout=180s || true
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgres --timeout=180s || true
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=wordpress --timeout=180s || true
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=gateway --timeout=180s || true
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=dashboard --timeout=180s || true
'

# 5. Initialize WooCommerce on the Cloud VPS
echo "🛍️  [5/5] Initializing WooCommerce & seed catalog on Cloud VPS..."
ssh -o StrictHostKeyChecking=no -i "${KEY_FILE}" ubuntu@"${PUBLIC_IP}" '
export KUBECONFIG=/home/ubuntu/.kube/config
cd /home/ubuntu/kube-ecommerce
./scripts/setup-woocommerce.sh
'

echo "===================================================================="
echo "🎉 CLOUD DEPLOYMENT COMPLETED ON AWS!"
echo "===================================================================="
echo "🌐 Cloud Endpoints (No /etc/hosts edits required via nip.io):"
echo "  • Storefront:  http://store.${PUBLIC_IP}.nip.io"
echo "  • Dashboard:   http://dashboard.${PUBLIC_IP}.nip.io"
echo "  • MCP Gateway: http://gateway.${PUBLIC_IP}.nip.io/mcp"
echo ""
echo "🔑 Credentials:"
echo "  • Dashboard Admin:  admin@ecommerce.local / AdminSecurePassword123!"
echo "  • Dashboard Member: member@ecommerce.local / MemberSecurePassword123!"
echo "  • WordPress Admin:  admin / AdminSecurePassword123!"
echo ""
echo "💻 Manage Remotely with Kubectl:"
echo "  KUBECONFIG=${ROOT_DIR}/kubeconfig-aws.yaml kubectl get pods"
echo "===================================================================="
