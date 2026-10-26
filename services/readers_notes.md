# Reader's Notes & Architectural Defense Manual
### WooCommerce Hosting Platform with Team MCP Gateway on Kubernetes

> **Project Target:** Urumi AI FDE Internship — Round 1 Technical Submission & Round 2 Defense  
> **Author:** Vishal Kumar  
> **Repository:** `kube-ecommerce`  
> **Purpose:** This document provides comprehensive, production-grade answers to all core architecture, Kubernetes, MCP protocol, security, AI agent, and deployment questions required for the submission walkthrough and technical interview.

---

## 1. System Design and Implementation

### 1.1. Components and Responsibilities

The system is composed of **8 decoupled containerized workloads** coordinated within Kubernetes, fulfilling four functional layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             TRAEFIK INGRESS                                 │
│       store.local             gateway.local              dashboard.local    │
└────────────┬─────────────────────────┬───────────────────────────┬──────────┘
             │                         │                           │
             ▼                         ▼                           ▼
    ┌─────────────────┐       ┌─────────────────┐         ┌─────────────────┐
    │ WordPress Store │       │ Central Gateway │◄────────┤  React UI (SPA) │
    │   (Apache+PHP)  │       │  (FastAPI+MCP)  │ (proxy) │  (Nginx Static) │
    └────────┬────────┘       └────────┬────────┘         └─────────────────┘
             │                         │
             ▼                         ▼
    ┌─────────────────┐       ┌─────────────────┐
    │  MariaDB 11.4   │       │  PostgreSQL 16  │
    │  (Store Data)   │       │(Registry/Audit) │
    └─────────────────┘       └────────┬────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
   ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
   │ mcp-woocommerce │        │ mcp-calculator  │        │   mcp-metrics   │
   │  (:8000 - 5 T)  │        │  (:8001 - 3 T)  │        │  (:8002 - 3 T)  │
   └────────┬────────┘        └─────────────────┘        └─────────────────┘
            │ (REST API)
            ▼
   ┌─────────────────┐
   │ WordPress Store │
   └─────────────────┘
```

1. **WordPress + WooCommerce Storefront (`wordpress:6.7-apache`, port 80)**:
   - Hosts the PHP/Apache store accessible at `http://store.local`.
   - Manages the product catalog, shopping cart, customer checkout, and WooCommerce REST API v3.
   - Backed by persistent storage (`wordpress-pvc`, 5Gi) for uploads, themes, and plugins.

2. **Store Database (`mariadb:11.4`, port 3306)**:
   - Dedicated relational database storing WordPress tables, post entities, order rows, and customer details.
   - Backed by persistent volume claim (`mariadb-pvc`, 2Gi). Completely isolated from non-WordPress traffic.

3. **Central MCP Gateway (`mcp-gateway:v1`, port 8000)**:
   - **The central nervous system of the architecture.** Operates in a **dual role**:
     - *MCP Server* toward external AI clients (Cursor, Claude Code, MCP Inspector, Dashboard).
     - *MCP Client* toward internal upstream MCP microservices.
   - Enforces Bearer API key authentication, execution-time Role-Based Access Control (RBAC), tool aggregation, dynamic namespace isolation, 3.5s per-server timeout containment, and PostgreSQL audit logging.
   - Houses the Gemini conversational Chat Agent engine (`POST /api/chat`).

4. **Gateway Registry & Audit Database (`postgres:16-alpine`, port 5432)**:
   - Stores dynamic upstream server registration state, server health statuses (`connected`, `unreachable`, `disabled`), team user accounts, SHA-256 hashed API keys, and immutable audit logs.
   - Backed by persistent volume claim (`postgres-pvc`, 2Gi).

5. **Management Dashboard UI (`ecommerce-dashboard:local`, port 80)**:
   - React 19 Single Page Application served by Nginx at `http://dashboard.local`.
   - Designed using PostHog’s warm cream canvas (`#eeefe9`), flat 1px borders, `#f7a501` yellow CTA buttons, and SVG Hedgehog mascot.
   - Features real-time 3-state server monitoring badges, schema inspector, API key generation/revocation, live audit viewer, and conversational chat bubble.
   - Proxies `/api/*` requests internally to `gateway:8000`.

6. **Upstream 1: WooCommerce MCP Server (`mcp-woocommerce:local`, port 8000)**:
   - Custom Python FastMCP microservice exposing 5 store tools (`list_products`, `create_product`, `list_orders`, `get_order`, `update_order_status`).
   - Translates incoming JSON-RPC tool invocations into authenticated WooCommerce REST API v3 calls using internal Consumer Key/Secret credentials.

7. **Upstream 2: Calculator MCP Server (`mcp-calculator:local`, port 8001)**:
   - Standalone Python FastMCP microservice exposing 3 deterministic math tools (`calculate`, `tax_calculation`, `discount_rate`).

8. **Upstream 3: Business Metrics MCP Server (`mcp-metrics:local`, port 8002)**:
   - Standalone Python FastMCP microservice exposing 3 business intelligence tools (`get_sales_target`, `calculate_revenue_summary`, `get_inventory_thresholds`).

---

### 1.2. The Definition-of-Done (DoD) Flow, Live, with Two Users

The end-to-end flow is fully automated and verified via [`scripts/run-all-demo-checks.sh`](file:///Users/vishalkumar/kube-ecommerce/scripts/run-all-demo-checks.sh), simulating two distinct team members across all 15 submission requirements:

#### User A (Store Administrator — `admin@ecommerce.local`):
1. **Storefront Verification & Checkout**:
   - Storefront responds with HTTP 200 at `http://store.local`.
   - An order (e.g., Order #20) is placed via checkout and recorded with `processing` status in WooCommerce.
2. **Dashboard Management & Server Registry**:
   - Admin logs in via `POST /api/auth/login` to obtain an administrative JWT.
   - Views registered MCP servers with live dynamic health badges (`Connected`, `Unreachable`, `Disabled`).
3. **Conversational Chat Agent Execution**:
   - Admin sends a message to the dashboard chat agent (`POST /api/chat`): *"List our products and retrieve today's orders."*
   - Chat agent converts MCP schemas into Gemini function declarations, invokes `woo__list_products` and `woo__list_orders` under User A's identity, and outputs a synthesized conversational summary.
   - The executions are immediately attributed to `admin@ecommerce.local` in PostgreSQL.

#### User B (Team Member — `member@ecommerce.local`):
1. **Zero-Credential Connection via Gateway**:
   - User B logs into the dashboard and generates a self-service API key (`mcp_live_<hex>`).
   - User B connects an external MCP client (Claude Code, Cursor, or MCP Inspector) using **only** the Gateway URL (`http://gateway.local/mcp`) and their API key.
   - Client sends JSON-RPC `initialize` and receives protocol handshake confirmation (`serverInfo: {"name": "team-mcp-gateway"}`).
2. **Upstream Discovery**:
   - User B queries `tools/list` and automatically discovers all 11 tools across all 3 enabled upstreams (`woo__*`, `calc__*`, `metrics__*`) without ever seeing or needing upstream credentials.
3. **Cross-Server Chained Workflow**:
   - In a single workflow, User B invokes:
     - `calc__calculate` (e.g., calculating an 80% discounted price on a $150 item $\rightarrow$ returns `120.0`).
     - `metrics__get_sales_target` (fetches daily revenue targets).
   - Both tools execute successfully through the single gateway connection.

#### Control, Chaos & Security Validation:
1. **Instant Key Revocation**:
   - Admin revokes User B's API key via `DELETE /api/keys/{id}`.
   - User B's very next JSON-RPC call to `/mcp` is **instantly rejected with HTTP 401 Unauthorized**.
2. **Dynamic Server Disabling**:
   - Admin toggles `mcp-metrics` off via `PATCH /api/servers/{id}/toggle`.
   - Tool count immediately drops from 11 to 8 in both the dashboard and external MCP client; direct invocations to disabled tools are rejected. Re-enabling restores all 11 tools.
3. **Fault Containment (Pod Kill / Outage)**:
   - `mcp-calculator` is scaled to 0 replicas.
   - Calling live server `metrics__get_sales_target` succeeds with HTTP 200.
   - Calling dead server `calc__calculate` fails fast with a structured JSON-RPC error; **the Gateway process and all other 7 pods survive completely unharmed**.
4. **Audit Log Verification**:
   - Admin inspects the audit table (`GET /api/audit`): every single invocation (User A chat calls, User B external tool calls, and blocked attempts) is recorded with timestamp, duration, status, and user email.

---

## 2. Kubernetes

### 2.1. What Runs Where: Namespaces, Secrets, Volumes, Ingress

```
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
```

- **Ingress Layer**: Traefik Ingress routes inbound traffic matching HTTP `Host` headers:
  - `store.local` $\rightarrow$ `wordpress:80`
  - `gateway.local` $\rightarrow$ `gateway:8000` (routes `/mcp`, `/api/*`, `/health`)
  - `dashboard.local` $\rightarrow$ `dashboard:80`

---

### 2.2. Requests and Limits, Probes

Every pod in the cluster defines explicit resource constraints and health probes in its Helm template:

| Workload | CPU Request | CPU Limit | Memory Request | Memory Limit | Liveness Probe | Readiness Probe |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **wordpress** | `100m` | `500m` | `256Mi` | `512Mi` | HTTP GET `:80/wp-login.php` (delay: 30s) | HTTP GET `:80/wp-login.php` (delay: 10s) |
| **mariadb** | `100m` | `300m` | `128Mi` | `256Mi` | TCP Socket `:3306` (delay: 15s) | TCP Socket `:3306` (delay: 5s) |
| **gateway** | `50m` | `250m` | `128Mi` | `256Mi` | HTTP GET `:8000/health` (delay: 10s) | HTTP GET `:8000/health` (delay: 5s) |
| **postgres** | `50m` | `250m` | `128Mi` | `256Mi` | TCP Socket `:5432` (delay: 10s) | TCP Socket `:5432` (delay: 5s) |
| **dashboard** | `25m` | `100m` | `32Mi` | `64Mi` | HTTP GET `:80/` (delay: 5s) | HTTP GET `:80/` (delay: 5s) |
| **mcp-woocommerce** | `50m` | `200m` | `64Mi` | `128Mi` | HTTP GET `:8000/health` (delay: 10s) | HTTP GET `:8000/health` (delay: 5s) |
| **mcp-calculator** | `25m` | `100m` | `32Mi` | `64Mi` | HTTP GET `:8001/health` (delay: 5s) | HTTP GET `:8001/health` (delay: 5s) |
| **mcp-metrics** | `25m` | `100m` | `32Mi` | `64Mi` | HTTP GET `:8002/health` (delay: 5s) | HTTP GET `:8002/health` (delay: 5s) |

#### Architectural Rationale:
- **Requests vs Limits**: Guarantees the Kubernetes scheduler assigns pods to nodes with guaranteed memory allocation, while limits protect the host from rogue memory leaks or CPU starvation.
- **Readiness vs Liveness**: If a container fails its readiness probe (e.g., WordPress during initial plugin database migrations), Kubernetes immediately removes it from Service endpoints so clients receive no dropped requests. If a container deadlocks and fails its liveness probe, Kubernetes automatically restarts the container.

---

### 2.3. What is Public vs What is Internal-Only & How Enforced

#### The Exposure Matrix:
- **Publicly Accessible (via Traefik Ingress)**:
  - `store.local` (Storefront customer browsing and checkout).
  - `gateway.local` (External MCP endpoint `/mcp`, dashboard REST API `/api/*`, and `/health`).
  - `dashboard.local` (Frontend React SPA).
- **Strictly Internal-Only (Zero External Ingress)**:
  - `mariadb:3306` (Storefront database).
  - `postgres:5432` (Gateway database).
  - `mcp-woocommerce:8000`, `mcp-calculator:8001`, `mcp-metrics:8002` (Upstream microservices).

#### Enforcement Mechanism: Dual-Layer Security
1. **Service Abstraction**: Internal workloads are exposed **exclusively as `ClusterIP` services**, which allocate virtual IPs routable *only* from within the Kubernetes pod SDN. No Ingress rules or NodePort mappings exist for them.
2. **Kubernetes NetworkPolicies (Linux Kernel Packet Filtering)**:
   In `helm/ecommerce-stack/templates/networkpolicy.yaml`, 6 strict zero-trust NetworkPolicies enforce micro-segmentation:
   - `allow-gateway-to-mcp-upstreams`: MCP upstream pods accept ingress **only from pods matching `app.kubernetes.io/name: gateway`**. Direct traffic from the dashboard, WordPress, or external attackers is dropped at the kernel network stack.
   - `allow-gateway-to-postgres`: PostgreSQL accepts ingress **only from `gateway`**.
   - `allow-wordpress-to-mariadb`: MariaDB accepts ingress **only from `wordpress`**.
   - `gateway-boundary-policy`: Restricts Gateway egress exclusively to Postgres (5432), upstream MCPs (8000–8002), CoreDNS (53), and outbound HTTPS (443) for Gemini AI API calls.

---

## 3. MCP Internals

### 3.1. How the Gateway Connects to Upstreams & Request Journey

```
[Claude Code / Cursor]
        │
        │ 1. POST /mcp (JSON-RPC: tools/call, Bearer mcp_live_...)
        ▼
[Traefik Ingress]
        │
        ▼
[Central Gateway: mcp_controller.py]
        │
        ├─► 2. Hash raw token with SHA-256 & verify in PostgreSQL (api_keys table)
        ├─► 3. Evaluate RBAC rules (is_tool_allowed_for_role)
        │
        ▼
[Aggregator Dispatcher: aggregator.py]
        │
        ├─► 4. Parse tool prefix: "woo__list_products" -> server slug: "woo"
        ├─► 5. Strip prefix -> original tool: "list_products"
        ├─► 6. Resolve internal URL: http://mcp-woocommerce:8000/mcp
        │
        ▼ (Internal HTTP POST /mcp)
[mcp-woocommerce: server.py]
        │
        ├─► 7. Extract Consumer Key & Secret from environment
        ├─► 8. Execute HTTP Basic Auth GET http://wordpress:80/wp-json/wc/v3/products
        │
        ▼
[WordPress Core Engine]
        │
        ├─► 9. Query MariaDB on port 3306
        ▼
[MariaDB Database] ──► Returns rows ──► WordPress formats JSON ──► mcp-woocommerce
        │
        ▼
[Central Gateway]
        │
        ├─► 10. Record execution in PostgreSQL audit_logs table
        │
        ▼ 11. Streamable HTTP (SSE) JSON-RPC Response
[Claude Code / Cursor]
```

---

### 3.2. Tool Name Collisions, Timeouts, and Dead Upstream Handling

#### 1. Tool Name Collisions:
- **The Problem**: Two independent upstream servers might both define a tool named `get_order`, `list_items`, or `search`.
- **The Solution (Slug Prefix Namespacing)**:
  During tool discovery (`tools/list`), the Gateway’s aggregator dynamically prepends each server's registered slug followed by a double underscore: `<slug>__<tool_name>`:
  - `mcp-woocommerce` $\rightarrow$ `woo__list_products`, `woo__create_product`, `woo__list_orders`
  - `mcp-calculator` $\rightarrow$ `calc__calculate`, `calc__tax_calculation`
  - `mcp-metrics` $\rightarrow$ `metrics__get_sales_target`
  When a call is received, the Gateway splits on `__` in $O(1)$ time to determine the destination server and strips the prefix before forwarding.

#### 2. Timeout Containment:
- Every upstream HTTP call is wrapped in an `httpx.AsyncClient` with a strict **3.5-second timeout ceiling**:
  ```python
  async with httpx.AsyncClient(timeout=3.5) as client:
      resp = await client.post(upstream_url, json=payload)
  ```
- If an upstream experiences network degradation or hangs, the Gateway cancels the request after 3.5s, preventing worker thread starvation and connection pool exhaustion.

#### 3. Dead Upstream Handling (Non-Blocking Partial Discovery):
- When `tools/list` is queried, the Gateway queries enabled upstreams concurrently using `asyncio.gather(return_exceptions=True)`.
- If an upstream is unreachable or times out:
  1. The Gateway catches the connection error without raising an unhandled exception.
  2. Automatically updates the database record: `UPDATE upstream_servers SET status = 'unreachable'`.
  3. Omits the dead server's tools from the returned toolset while **immediately returning the tools of all healthy servers**.
  4. In our chaos test, discovery across living servers completed in **0.12 seconds** while `mcp-calculator` was completely dead.
- If a client attempts to invoke a tool on a dead server, the Gateway returns a structured JSON-RPC error response:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
      "isError": true,
      "content": [{"type": "text", "text": "Upstream server 'calc' is currently unreachable."}]
    }
  }
  ```

---

## 4. Security Posture

### 4.1. How API Keys and Upstream Credentials are Stored and Used

#### Client API Keys:
- Generated using cryptographically secure pseudorandom entropy: `mcp_live_` + 24 random hex bytes (192 bits of entropy).
- **Stored Hashed at Rest**: Plaintext API keys are **never stored in the database**. The Gateway hashes the raw key with `SHA-256` and stores only the digest:
  ```python
  key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
  ```
- **Masked Display**: Plaintext keys are shown to the user exactly once upon generation. In all subsequent API and dashboard views, keys are masked (`mcp_live_f2d0...`).

#### Upstream Credentials:
- Sensitive WooCommerce REST API keys (`ck_...` and `cs_...`) and database passwords are stored exclusively in **Kubernetes Secrets** (`woocommerce-keys-secret`, `mariadb-secret`, `postgres-secret`).
- Upstream credentials are never returned over any API, never sent to client IDEs, and never rendered in frontend HTML/JS.

#### User Passwords:
- User passwords are protected using **PBKDF2-HMAC-SHA256** with 100,000 hashing iterations and unique cryptographic salts.

---

### 4.2. What a Member Can and Cannot Do (RBAC Matrix)

The platform enforces strict Role-Based Access Control verified at execution time:

| Action / Tool | Store Admin (`admin`) | Team Member (`member`) | Enforcement Point |
| :--- | :---: | :---: | :--- |
| **Log into Dashboard** | ✅ Yes | ✅ Yes | JWT Auth Controller |
| **Generate Personal API Key** | ✅ Yes | ✅ Yes | Key Controller |
| **Connect Cursor / Claude Code** | ✅ Yes | ✅ Yes | Gateway MCP Endpoint (`/mcp`) |
| **Discover Tools (`tools/list`)** | ✅ Yes (All 11 tools) | ✅ Yes (All 11 tools) | Aggregator |
| **Execute Read Tools (`woo__list_*`)** | ✅ Yes | ✅ Yes | Gateway RBAC Gate |
| **Execute Calculator & Metrics** | ✅ Yes | ✅ Yes | Gateway RBAC Gate |
| **Create Product (`woo__create_product`)** | ✅ Allowed | ❌ **FORBIDDEN (HTTP 403)** | `is_tool_allowed_for_role()` |
| **Update Order (`woo__update_order_status`)**| ✅ Allowed | ❌ **FORBIDDEN (HTTP 403)** | `is_tool_allowed_for_role()` |
| **Add / Toggle / Remove Upstreams** | ✅ Allowed | ❌ **FORBIDDEN (HTTP 403)** | Server Controller (`require_admin`) |
| **Revoke Other Users' Keys** | ✅ Allowed | ❌ **FORBIDDEN (HTTP 403)** | Key Controller (`require_admin`) |
| **Inspect System Audit Logs** | ✅ Allowed | ❌ **FORBIDDEN (HTTP 403)** | Audit Controller (`require_admin`) |

> **Critical Security Detail**: RBAC is enforced **on the server at execution time**. Even if a malicious Member bypasses the UI and sends a raw JSON-RPC payload directly calling `woo__create_product`, the Gateway rejects the request with `isError: True`, blocks execution, and writes a `forbidden` security violation to the audit log.

---

### 4.3. What Happens if an Admin Adds a Malicious or Compromised MCP Server

If an administrator unknowingly registers a malicious or compromised upstream MCP server URL, the system provides **multiple layers of containment**:

1. **Network Containment (Zero Lateral Movement)**:
   - Upstream servers run inside isolated pods governed by Kubernetes `NetworkPolicies`.
   - A compromised upstream MCP container **cannot initiate TCP connections to MariaDB, PostgreSQL, or other upstreams**. Any attempt to scan the cluster network or reach port 3306 / 5432 is dropped by Linux kernel iptables rules.
2. **Credential Isolation (Zero Secrets Leakage)**:
   - The Gateway does not pass client tokens, user database credentials, or other upstream keys to the compromised server. The compromised server only receives the arguments explicitly passed for its own tool calls.
3. **Tool Shadowing Prevention**:
   - The Gateway enforces prefix namespacing (`slug__*`). A rogue server registered as `calc` cannot shadow or hijack `woo__list_products` or system management tools.
4. **Audit Trail & Attribution**:
   - Every single call forwarded to the rogue server, along with its input arguments, response latency, and outcome, is logged in PostgreSQL. If anomalous behavior occurs, administrators have an immutable forensic record.

---

## 5. Chat Agent

### 5.1. The Tool Loop & How the Agent Acts as the Logged-In User

```
User Prompt: "Create a discount code for order 18"
                 │
                 ▼
     [POST /api/chat + Bearer JWT]
                 │
                 ▼
┌──────────────────────────────────────────────────┐
│ Central Gateway (chat_controller.py)             │
│ • Authenticates JWT -> Resolves User: user_id=1  │
│ • Passes authenticated User object to Agent      │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│ GeminiChatAgent (gemini_agent.py)                │
│ 1. Aggregates active tools via aggregator        │
│ 2. Translates MCP schemas -> Gemini Declarations │
│ 3. Injects system instructions + user role       │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼ (HTTPS POST :443)
┌──────────────────────────────────────────────────┐
│ Google Gemini API (gemini-flash-lite / latest)   │
│ • Evaluates prompt against tools                 │
│ • Emits: FunctionCall(name, args)                │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│ Authenticated Execution Gate (Under User Session)│
│ • Evaluates RBAC: is_tool_allowed_for_role()     │
│ • Executes tool through Aggregator               │
│ • Writes AuditLog:                               │
│     user_id = current_user.id                    │
│     user_email = current_user.email              │
│     tool_name = "calc__discount_rate"            │
│     status = "success"                           │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│ Gemini Synthesizes Natural Language Reply        │
│ • Returns: {"reply": "...", "tool_calls": [...]} │
└──────────────────────────────────────────────────┘
```

#### Key Technical Highlights:
- **Dynamic Tool Schema Converter (`agent/tool_converter.py`)**: Automatically translates the Gateway’s 11 MCP JSON Schema definitions into Google Gemini’s OpenAPI-compliant `FunctionDeclaration` structures.
- **Identity Retention**: The Chat Agent does **not** run as an anonymous background service. It receives the caller’s validated `User` object directly from the FastAPI dependency chain (`get_current_user`). When tools are invoked, the audit trail captures the human user who triggered the AI action.
- **Multi-Turn Looping**: Supports up to 5 sequential tool invocations per turn, enabling complex multi-step reasoning (e.g. `woo__list_products` $\rightarrow$ `calc__discount_rate` $\rightarrow$ `metrics__get_sales_target` $\rightarrow$ final synthesized answer).
- **Multi-Model Fallback with 503 Auto-Retry**: Automatically falls back across model families (`gemini-flash-latest`, `gemini-flash-lite-latest`, `gemini-2.5-flash`) with exponential backoff if Google's API returns transient 503 rate limits.

---

## 6. Local-to-VPS Production Story

### 6.1. What Changes Between Local and VPS Through Helm Values

Per the assignment specification:
> *"The code and Kubernetes manifests are 100% identical. The only thing that changes between local testing and production is the Helm values file."*

We created [`helm/ecommerce-stack/values-prod.yaml`](file:///Users/vishalkumar/kube-ecommerce/helm/ecommerce-stack/values-prod.yaml) to handle all environmental adaptations:

| Configuration Area | Local Testing (`values.yaml`) | Production Cloud VPS (`values-prod.yaml`) |
| :--- | :--- | :--- |
| **Domain Routing** | Local synthetic domains (`store.local`, `gateway.local`, `dashboard.local`) mapped via `/etc/hosts`. | Real public domains or wildcard DNS (`*.<vps-ip>.nip.io`). |
| **Ingress TLS** | Disabled (`tls: false`, plain HTTP port 80). | Enabled (`tls: true`) with automated Let's Encrypt certificates via `cert-manager`. |
| **Workload Replicas**| Single replica per service (`replicas: 1`). | High availability (`replicas: 2` for Gateway and Dashboard). |
| **Storage Classes** | k3d local path provisioner (`storageClass: local-path`). | Production cloud block storage (`storageClass: gp3` / cloud SSD). |
| **Container Images** | Local image daemon (`pullPolicy: Never`). | Public or private registry (`ghcr.io/company/...`, `pullPolicy: IfNotPresent`). |
| **Resource Limits** | Developer laptop baseline (WordPress: 512Mi, MariaDB: 256Mi). | Production workloads (WordPress: 1.5Gi, MariaDB: 1Gi). |

---

### 6.2. Ingress, Domains, Storage, and Secrets Strategy

1. **Ingress & Domains Strategy**:
   - On the VPS, **k3s comes pre-bundled with the Traefik Ingress Controller** listening directly on public ports 80 and 443.
   - We utilize **wildcard DNS (`.nip.io`)**, which dynamically maps any IP to a hostname without purchasing a domain:
     - `http://store.<vps-ip>.nip.io`
     - `http://gateway.<vps-ip>.nip.io`
     - `http://dashboard.<vps-ip>.nip.io`
   - For custom production domains, an Ingress annotation (`cert-manager.io/cluster-issuer: letsencrypt-prod`) automatically conducts ACME HTTP-01 challenges and provisions TLS certificates into Kubernetes secrets.
2. **Storage Strategy**:
   - In production, Stateful workloads (`mariadb`, `postgres`, `wordpress`) define PersistentVolumeClaims with storage classes backed by network block storage (e.g. AWS EBS `gp3`, DigitalOcean Block Storage, or Hetzner Volume Storage).
   - If a cloud worker node experiences hardware failure, Kubernetes automatically reschedules the pod to a healthy node and remounts the cloud volume with zero data loss.
3. **Secrets Strategy**:
   - In production, secrets are injected via external secret stores (HashiCorp Vault, AWS Secrets Manager, or SealedSecrets) or passed at deployment time using secure Helm flags:
     ```bash
     helm upgrade --install ecommerce-stack ./helm/ecommerce-stack \
       -f ./helm/ecommerce-stack/values-prod.yaml \
       --set mariadb.password="${PROD_DB_PASS}" \
       --set secrets.geminiApiKey="${PROD_GEMINI_KEY}"
     ```

---

### 6.3. Upgrade and Rollback with Helm

#### 1. Zero-Downtime Rolling Upgrades:
- When a new version of the gateway or storefront is released, we update the image tag in `values-prod.yaml` and run:
  ```bash
  helm upgrade ecommerce-stack ./helm/ecommerce-stack -f ./helm/ecommerce-stack/values-prod.yaml
  ```
- Kubernetes executes a `RollingUpdate`:
  - Spins up the new pod revision and runs readiness probes.
  - Keeps the old pod receiving live customer traffic until the new pod reports healthy.
  - Gracefully terminates the old pod (`SIGTERM` with 30s grace period).

#### 2. Safe and Instant Rollbacks:
- If a regression or issue is detected in a new release:
  ```bash
  # 1. View deployment revision history
  helm history ecommerce-stack

  # 2. Instantly roll back to the previous healthy revision (e.g. revision 2)
  helm rollback ecommerce-stack 2
  ```
- **Storage Safety Guarantee**: Rolling back a Helm release updates only deployment specs and container images. **PersistentVolumeClaims (`wordpress-pvc`, `mariadb-pvc`, `postgres-pvc`) are never deleted or truncated during rollbacks**, ensuring customer orders and database records remain 100% safe.
