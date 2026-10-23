# WooCommerce Hosting Platform with Team MCP Gateway on Kubernetes

A production-grade, stateful Kubernetes deployment hosting WooCommerce with an integrated Model Context Protocol (MCP) Gateway layer for AI agents.

## Architecture Overview

1. **Storefront Layer**: WordPress + WooCommerce powered by a dedicated MariaDB database with PersistentVolumeClaims (PVCs), exposed via Traefik Ingress on `store.local`.
2. **WooCommerce MCP Server**: Internal microservice translating MCP tool invocations into WooCommerce REST API operations.
3. **Team MCP Gateway & Dashboard**: Centralized MCP server/client aggregator enforcing authentication, upstream discovery, tool namespacing, and database audit logs.
4. **Chat Agent**: Dashboard-integrated tool-calling AI agent executing store tasks with user identity attribution.

---

## Local Development Prerequisites

- **macOS** or **Linux**
- [Docker Desktop](https://www.docker.com/) (running)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [k3d](https://k3d.io/) (`brew install k3d`)
- [Helm](https://helm.sh/) (`brew install helm`)

---

## Quick Start (Day 1–2 Stack)

### 1. Initialize the k3d Cluster
Creates a local 2-node cluster with ports `80` and `443` routed into Traefik Ingress:
```bash
./scripts/init-cluster.sh
```

### 2. Configure Local DNS
Add the local test domains to `/etc/hosts`:
```bash
sudo sh -c 'echo "127.0.0.1   store.local gateway.local dashboard.local" >> /etc/hosts'
```

### 3. Deploy the Helm Stack
```bash
helm upgrade --install ecommerce-stack ./helm/ecommerce-stack
```

### 4. Configure WooCommerce & Seed Initial Store Data
```bash
./scripts/setup-woocommerce.sh
```

Open `http://store.local` in your browser to access the live storefront.
Admin credentials: `admin` / `AdminSecurePassword123!`.
