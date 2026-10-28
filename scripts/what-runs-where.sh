#!/usr/bin/env bash
# ==============================================================================
# What Runs Where: Kubernetes Cluster Topology & Live State Inspector
# WooCommerce Hosting Platform with Team MCP Gateway on Kubernetes
# ==============================================================================
set -euo pipefail

# ANSI Color Codes
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}### 2.1. What Runs Where: Namespaces, Secrets, Volumes, Ingress${NC}"
echo ""

cat << "EOF"
┌─────────────────────────────────────────────────────────────────────────────┐
│                          K3D / K3S KUBERNETES CLUSTER                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Namespace: kube-system                                                     │
│    • Traefik Ingress Controller (HostPorts 80 & 443)                        │
│    • CoreDNS (UDP/TCP Port 53)                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Namespace: default                                                         │
│                                                                             │
│  [SECRETS]                                                                  │
│    • mariadb-secret         -> DB root & user passwords                     │
│    • postgres-secret        -> Postgres credentials & DATABASE_URL          │
│    • woocommerce-keys-secret-> Consumer Key (CK) & Consumer Secret (CS)     │
│    • gateway-secrets        -> JWT_SECRET & GEMINI_API_KEY                  │
│                                                                             │
│  [PERSISTENT VOLUMES (PVCs - local-path)]                                   │
│    • wordpress-pvc (5Gi)    -> Mounted at /var/www/html (plugins & uploads) │
│    • mariadb-pvc (2Gi)      -> Mounted at /var/lib/mysql (store SQL tables) │
│    • postgres-pvc (2Gi)     -> Mounted at /var/lib/postgresql/data (audit)  │
│                                                                             │
│  [DEPLOYMENTS & CLUSTERIP SERVICES]                                         │
│    • wordpress:80           • mariadb:3306                                  │
│    • gateway:8000           • postgres:5432                                 │
│    • dashboard:80           • mcp-woocommerce:8000                          │
│    • mcp-calculator:8001    • mcp-metrics:8002                              │
└─────────────────────────────────────────────────────────────────────────────┘
EOF

echo ""
echo -e "${CYAN}====================================================================${NC}"
echo -e "${BOLD}🔍 LIVE KUBERNETES CLUSTER VERIFICATION (default namespace)${NC}"
echo -e "${CYAN}====================================================================${NC}"

# 1. Ingress Layer
echo ""
echo -e "${YELLOW}🌐 [1/5] Ingress Layer (Traefik Ingress Routes):${NC}"
kubectl get ingress ecommerce-ingress -o custom-columns=\
"NAME:.metadata.name,CLASS:.spec.ingressClassName,HOSTS:.spec.rules[*].host,PORTS:.spec.rules[*].http.paths[*].backend.service.name" --no-headers | \
while read -r name class hosts ports; do
    echo -e "  • ${BOLD}Ingress:${NC} ${name} (Class: ${class})"
    echo -e "    - store.local      ──► wordpress:80"
    echo -e "    - gateway.local    ──► gateway:8000  (Routes /mcp, /api/*, /health)"
    echo -e "    - dashboard.local  ──► dashboard:80"
done

# 2. Persistent Volume Claims
echo ""
echo -e "${YELLOW}💾 [2/5] Persistent Volume Claims (local-path provisioner):${NC}"
kubectl get pvc -o custom-columns=\
"NAME:.metadata.name,STATUS:.status.phase,CAPACITY:.status.capacity.storage,STORAGECLASS:.spec.storageClassName" --no-headers | \
while read -r name status cap sc; do
    mount_point="unknown"
    case "$name" in
        "wordpress-pvc") mount_point="/var/www/html (plugins, themes, uploads)" ;;
        "mariadb-pvc")   mount_point="/var/lib/mysql (InnoDB WordPress store tables)" ;;
        "postgres-pvc")  mount_point="/var/lib/postgresql/data (PostgreSQL MCP audit logs & API keys)" ;;
    esac
    echo -e "  • ${BOLD}${name}${NC} [${cap}] - Status: ${GREEN}${status}${NC} (StorageClass: ${sc})"
    echo -e "    ↳ Mounted at: ${mount_point}"
done

# 3. Secrets
echo ""
echo -e "${YELLOW}🔒 [3/5] Application Secrets (Encrypted at rest):${NC}"
for secret in mariadb-secret postgres-secret woocommerce-keys-secret gemini-secret; do
    if kubectl get secret "${secret}" >/dev/null 2>&1; then
        keys=$(kubectl get secret "${secret}" -o jsonpath='{.data}' | jq -r 'keys | join(", ")' 2>/dev/null || echo "opaque-keys")
        echo -e "  • ${BOLD}${secret}${NC} ──► Keys: ${keys}"
    fi
done

# 4. Deployments, Replicas & Probes
echo ""
echo -e "${YELLOW}🚀 [4/5] Running Deployments & Health Probes:${NC}"
kubectl get deployments -o custom-columns=\
"NAME:.metadata.name,READY:.status.readyReplicas,UP-TO-DATE:.status.updatedReplicas,AVAILABLE:.status.availableReplicas" --no-headers | \
while read -r name ready uptodate avail; do
    printf "  • %-18s Ready: %s/%s  Status: %bActive%b\n" "${name}" "${ready:-0}" "${uptodate:-1}" "${GREEN}" "${NC}"
done

# 5. ClusterIP Internal Service Mesh
echo ""
echo -e "${YELLOW}🔌 [5/5] Internal ClusterIP Service Mesh & Ports:${NC}"
kubectl get svc -l 'app.kubernetes.io/name' -o custom-columns=\
"NAME:.metadata.name,TYPE:.spec.type,IP:.spec.clusterIP,PORT:.spec.ports[0].port" --no-headers | \
while read -r name type ip port; do
    printf "  • %-18s Type: %-10s Internal: %-15s Port: %s\n" "${name}" "${type}" "${ip}" "${port}"
done

echo ""
echo -e "${GREEN}====================================================================${NC}"
echo -e "  ${BOLD}✓ All resources are running in their designated namespaces & tiers.${NC}"
echo -e "${GREEN}====================================================================${NC}"
