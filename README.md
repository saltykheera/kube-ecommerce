# WooCommerce Hosting Platform with Team MCP Gateway on Kubernetes

A production-grade, stateful Kubernetes deployment hosting WooCommerce with an integrated Model Context Protocol (MCP) Gateway layer for AI agents (Claude Code, Cursor, MCP Inspector, and Dashboard Chat).

---

## Quick Reference: Starting and Stopping

### To Start / Resume the Platform
```bash
./scripts/start.sh
```
*Checks Docker, resumes or initializes the k3d cluster, verifies all 8 pods are Ready, and displays active endpoints and credentials.*

### To Stop / Pause the Platform
```bash
./scripts/stop.sh
```
*Safely pauses the cluster containers. CPU & RAM are immediately freed up, while **all WooCommerce products, orders, database tables, and persistent storage (PVCs) remain 100% saved on disk**.*

---

## Live Endpoints & Default Credentials

| Service | Local URL | Role | Credentials |
| :--- | :--- | :--- | :--- |
| **WooCommerce Store** | `http://store.local` | Public storefront & WP Admin | `admin` / `AdminSecurePassword123!` |
| **PostHog Dashboard** | `http://dashboard.local` | Team & MCP Server Management | `admin@ecommerce.local` / `AdminSecurePassword123!`<br/>`member@ecommerce.local` / `MemberSecurePassword123!` |
| **Central MCP Gateway** | `http://gateway.local/mcp` | Unified Streamable HTTP MCP Endpoint | `Authorization: Bearer <mcp_live_...>` |
| **Gateway Health Check**| `http://gateway.local/health` | HTTP Liveness / Probe | *Public* |

> [!NOTE]
> Ensure local domain resolution is configured in `/etc/hosts`:
> ```bash
> sudo sh -c 'echo "127.0.0.1   store.local gateway.local dashboard.local" >> /etc/hosts'
> ```

---

## Complete Verification Suite

To run the unified **15-point Definition-of-Done demo verification script**:
```bash
./scripts/run-all-demo-checks.sh
```

To run the **Zero-Trust NetworkPolicy isolation tests**:
```bash
./scripts/test-network-policies.sh
```

To run the **Chaos & Fault-Tolerance test suite**:
```bash
./scripts/test-chaos-fault-tolerance.sh
```

---

## Architecture & Technical Decisions
For a deep dive into the 8 microservices, request flows, day-by-day engineering decisions, and Round 2 interview defense, read [**`ARCHITECTURE.md`**](file:///Users/vishalkumar/kube-ecommerce/ARCHITECTURE.md).

For the STRIDE security analysis and trust boundaries, read [**`THREAT_MODEL.md`**](file:///Users/vishalkumar/kube-ecommerce/THREAT_MODEL.md).
