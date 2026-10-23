Here is the plan for **Days 4–5: The Gateway Core (Three Upstreams Through One Endpoint)**:

---

### The Big Picture of Days 4–5

The **MCP Gateway** is the central brain of this entire project. It has a **dual role**:
1. **MCP Client** (inward-facing): Connects to the 3 internal upstream MCP servers.
2. **MCP Server** (outward-facing): Exposes a **single unified endpoint** (`http://gateway.local/mcp`) to Claude Code, Cursor, MCP Inspector, and the future chat agent.

```
[ External Client: Claude / Cursor / Inspector ]
                      │
                      ▼
       [ The MCP Gateway (gateway.local) ]
         ┌────────────┼────────────┐
         │ (Internal) │ (Internal) │ (Internal)
         ▼            ▼            ▼
   [ WooCommerce ] [ Calculator ] [ Business Metrics ]
     (Upstream 1)   (Upstream 2)     (Upstream 3)
```

---

### Phase 1: Build the 2 Additional Upstream Servers (Required by Prompt)
The assignment requires at least **three** upstream MCP servers. We will build two lightweight, deterministic servers:

1. **`mcp-calculator`** (`services/mcp-calculator` on port `8001`):
   - Exposes mathematical & pricing calculation tools (e.g. `calculate`, `tax_calculation`, `discount_rate`).
   - Easy to test deterministic results.
2. **`mcp-metrics`** (`services/mcp-metrics` on port `8002`):
   - Exposes business analytics tools (e.g. `get_sales_target`, `calculate_revenue_summary`).
   - Allows multi-server prompts (e.g., *"Calculate today's WooCommerce revenue and compare it against the sales target"*).

---

### Phase 2: Build the FastAPI MCP Gateway (`services/gateway`)

The gateway implements these essential capabilities:

1. **Server Registry (PostgreSQL-backed)**:
   - Stores registered upstreams (`id`, `name`, `url`, `auth_header`, `is_enabled`, `status`).
   - Admin can enable/disable servers dynamically without redeploying code.
2. **Tool Aggregation & Namespacing (Solves Name Collisions)**:
   - If two upstreams have a tool with the same name, the gateway prefixes them:
     - `woo__list_products`
     - `calc__calculate`
     - `metrics__get_sales_target`
   - External clients see clean namespaced tools; the gateway knows how to map calls back to the right upstream.
3. **Timeout & Partial Failure Containment**:
   - If one upstream takes > 5 seconds or crashes, the gateway doesn't hang or crash. It returns the tools from the remaining live servers and marks the dead one as `unreachable`.
4. **Credential Masking**:
   - Upstream secrets are stored encrypted and **never sent** to the browser or external clients.

---

### Phase 3: Deliverables & Verification (Definition of Done for Days 4–5)

1. Deploy the 3 upstreams + Gateway + PostgreSQL via Helm.
2. Connect MCP Inspector to `http://gateway.local/mcp`:
   - Inspect all tools from **all 3 servers** aggregated under one roof.
3. Run a **cross-server prompt** that executes tools across two different servers.
4. **Fault Tolerance Demo**: Kill the `mcp-calculator` pod:
   - Show that `woo__...` and `metrics__...` tools still work smoothly without crashing the gateway.

---

Would you like to start implementing **Phase 1** (the two additional MCP servers) now?