# Security Threat Model: Team MCP Gateway & Kubernetes Storefront

This document formalizes the threat model, security boundaries, STRIDE classification, and defense-in-depth mitigations for the WooCommerce hosting platform and centralized MCP Gateway on Kubernetes.

---

## 1. System Architecture & Trust Boundaries

```
[ UNTRUSTED INTERNET / EXTERNAL ACTORS ]
                   │
                   ▼
  ┌─────────────────────────────────────────────────────────┐
  │  TRUST BOUNDARY 0: Ingress Edge (Traefik Ingress)      │
  │  - Routes http://store.local, gateway.local, dashboard   │
  │  - Strips/validates host headers                        │
  └────────────────────────┬────────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
  ┌───────────────────────┐   ┌─────────────────────────────┐
  │  TRUST BOUNDARY 1     │   │  TRUST BOUNDARY 2           │
  │  Dashboard SPA        │   │  Central MCP Gateway        │
  │  (Nginx Static Pod)   │   │  - Auth: JWT & API Keys     │
  │                       │   │  - RBAC: Admin vs Member    │
  │  No direct DB access  │   │  - Auditing: PostgreSQL     │
  │  NetworkPolicy: In/Out│   │  - Timeout: 3.5s per server │
  └──────────┬────────────┘   └──────────────┬──────────────┘
             │ (internal proxy)              │
             └───────────────────────────────┘
                                     │
           ┌─────────────────────────┴────────────────────────┐
           ▼                                                  ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│  TRUST BOUNDARY 3            │              │  TRUST BOUNDARY 4            │
│  Internal MCP Upstreams      │              │  Stateful Databases          │
│  - mcp-woocommerce (port 8000│              │  - postgres (port 5432)      │
│  - mcp-calculator  (port 8001│              │  - mariadb  (port 3306)      │
│  - mcp-metrics     (port 8002│              │                              │
│                              │              │  NetworkPolicy:              │
│  NetworkPolicy: Only Gateway │              │  Postgres: Only Gateway      │
│  can initiate TCP ingress    │              │  MariaDB: Only WordPress     │
└──────────────┬───────────────┘              └──────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│  WordPress / WooCommerce     │
│  - wp-content / PVC          │
│  - Only reached by Gateway   │
│    or Ingress / mcp-woo      │
└──────────────────────────────┘
```

---

## 2. STRIDE Threat Analysis & Mitigations

### S — Spoofing Identity
| Threat | Risk | Mitigation Implemented | Verification Evidence |
| :--- | :--- | :--- | :--- |
| Attacker impersonates an authorized team member to invoke MCP tools | High | • Bearer API Keys generated with cryptographically secure random entropy (`mcp_live_<hex>`).<br/>• SHA-256 key hashing stored in PostgreSQL; raw keys never logged.<br/>• JWT bearer tokens signed with HMAC-SHA256 for dashboard operations. | Rejection test in `scripts/test-multi-user-e2e.py`: invalid or missing key returns 401 Unauthorized immediately. |
| Forged WooCommerce REST API requests | High | • Upstream `mcp-woocommerce` uses dedicated Consumer Key & Secret securely mounted via Kubernetes Secrets.<br/>• `mcp-woocommerce` is accessible *only* from the Gateway pod. | Prohibited ingress from Dashboard or external IPs dropped by NetworkPolicy. |

### T — Tampering with Data
| Threat | Risk | Mitigation Implemented | Verification Evidence |
| :--- | :--- | :--- | :--- |
| Rogue microservice modifies WooCommerce order or product data directly in MariaDB | Critical | • MariaDB port 3306 accepts ingress *exclusively* from the WordPress pod selector (`app.kubernetes.io/name=wordpress`).<br/>• All other pods (Gateway, Dashboard, Calculator, Metrics) are blocked at the Linux kernel packet level. | `scripts/test-network-policies.sh` Test 2: Dashboard $\rightarrow$ MariaDB TCP connection refused/timed out. |
| Unauthorized user modifies upstream server configs or disables servers | High | • `PATCH /api/servers/{id}` protected by `require_admin` dependency.<br/>• Members receive HTTP 403 Forbidden on management endpoints. | Admin RBAC verified in `scripts/test-multi-user-e2e.py`. |

### R — Repudiation
| Threat | Risk | Mitigation Implemented | Verification Evidence |
| :--- | :--- | :--- | :--- |
| Team member executes unauthorized order cancellations or price discounts and denies action | High | • Gateway maintains an append-only audit trail in PostgreSQL (`audit_logs` table).<br/>• Every `/mcp` call and `/api/chat` tool invocation records: `user_id`, `user_email`, `api_key_id`, `tool_name`, `arguments`, `status`, `duration_ms`, and timestamp. | `scripts/test-multi-user-e2e.py` Step 7 confirms exact audit attribution for both Admin and Member. |

### I — Information Disclosure
| Threat | Risk | Mitigation Implemented | Verification Evidence |
| :--- | :--- | :--- | :--- |
| Member user inspects sensitive WooCommerce API credentials or upstream tokens | Critical | • Upstream credentials remain isolated inside `mcp-woocommerce` and Gateway containers.<br/>• Clients only see namespaced tools (`woo__*`) and schemas.<br/>• API keys in database are one-way hashed with SHA-256; UI only shows prefix (`mcp_live_...`). | `GET /api/keys` returns `masked_key` (e.g. `mcp_live_f2d0a8...`), never the plaintext secret. |
| External attacker probes internal MCP microservices directly | High | • All 3 MCP servers (`mcp-woocommerce`, `mcp-calculator`, `mcp-metrics`) are exposed as ClusterIP services without Ingress rules.<br/>• Kubernetes NetworkPolicies drop all traffic not originating from the Gateway pod. | `scripts/test-network-policies.sh` Step 1 confirms zero-trust boundary. |

### D — Denial of Service (DoS)
| Threat | Risk | Mitigation Implemented | Verification Evidence |
| :--- | :--- | :--- | :--- |
| Slow or hung upstream MCP server hangs the entire Gateway and exhausts connection pools | High | • Gateway executes upstream calls with strict `httpx.AsyncClient(timeout=3.5)`.<br/>• Upstream failures fail fast without taking down the event loop or blocking concurrent user requests. | `scripts/test-chaos-fault-tolerance.sh` Step 2: scaling `mcp-calculator` to 0 returns remaining tools in 0.12s. |
| Memory leak or runaway process takes down Kubernetes worker node | Medium | • All deployments define strict `resources.requests` and `resources.limits` for both CPU and memory.<br/>• WordPress: 512Mi limit; Gateway: 256Mi limit; Databases: 512Mi limits. | Verified in `helm/ecommerce-stack/values.yaml` and `helm template` checks. |

### E — Elevation of Privilege
| Threat | Risk | Mitigation Implemented | Verification Evidence |
| :--- | :--- | :--- | :--- |
| Member uses a cached tool name (e.g. `woo__create_product`) to bypass UI restrictions | High | • RBAC is enforced on the server at execution time (`is_tool_allowed_for_role`).<br/>• Even if a Member sends a raw JSON-RPC request to `woo__create_product`, the Gateway rejects it with `isError: True` and logs a `forbidden` audit event. | Verified in `scripts/test-multi-user-e2e.py` Step 4: Member mutation blocked. |
| Compromised API key continues to be used after security incident | Critical | • Instant revocation: When an API key is deleted or deactivated via `DELETE /api/keys/{id}`, all subsequent requests with that key are rejected immediately (HTTP 401). | `scripts/test-multi-user-e2e.py` Step 5: revoked key immediately rejected. |

---

## 3. Defense-in-Depth Summary

1. **Network Layer**: Kubernetes CNI NetworkPolicies create micro-segmentation boundaries between frontend, gateway, upstreams, and databases.
2. **Transport Layer**: Traefik Ingress routes external traffic; internal services communicate over dedicated ClusterIP networks.
3. **Application Layer**: Central Gateway terminates external MCP sessions, enforces authentication, inspects authorization roles, and handles timeouts.
4. **Data Layer**: Sensitive credentials stored in Kubernetes Secrets; persistent volumes protected by container user isolation; passwords hashed with PBKDF2; keys hashed with SHA-256.
