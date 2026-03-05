# Microsoft Azure — Deployment Appendix

This appendix maps the Cashflow App's [generic architecture](../architecture-overview.md) to Azure services.

---

## 1. Service Mapping

| Generic Term | Azure Service |
|-------------|--------------|
| Managed container service | **Azure Container Apps** |
| Managed PostgreSQL | **Azure Database for PostgreSQL — Flexible Server** |
| Container registry | **Azure Container Registry (ACR)** |
| Private networking | **VNet** + **Private Endpoints** |
| HTTPS ingress | **Container Apps managed ingress** or **Azure Front Door** |
| IAM | **Microsoft Entra ID** (formerly Azure AD) + **Azure RBAC** |
| Secrets management | **Azure Key Vault** |
| Audit logs | **Azure Activity Log** + **Microsoft Defender for Cloud** |
| Network flow logs | **NSG Flow Logs** |
| Logging | **Azure Monitor** + **Log Analytics** |

---

## 2. Hosting Setup

### Azure Container Apps

- **Plan**: Consumption (pay-per-use, scales to zero)
- **CPU/Memory**: 0.25 vCPU, 0.5 GB for low traffic
- **VNet integration**: Required for private database access
- **Min replicas**: 0 (scales to zero) or 1 (avoids cold starts)
- **Max replicas**: 5–10 for a single-tenant deployment
- **Ingress**: External (public) or internal (VNet-only)
- **Health probes**: Liveness and readiness probes pointing to `/health` and `/health/ready`

### Azure Database for PostgreSQL — Flexible Server

- **Tier**: Burstable B1ms (1 vCPU, 2 GB RAM) — lowest cost option
- **Storage**: 32 GB (minimum)
- **Network**: Private access via VNet integration or Private Endpoint (no public access)
- **Backups**: Automated daily backups, 7-day retention (configurable up to 35 days)
- **High availability**: Optional zone-redundant HA

> **Note on database choice**: PostgreSQL is recommended (zero application code changes). If the customer requires Azure SQL Database for Power BI alignment, be aware that JSONB columns, UUID primary keys, and Alembic migrations would need adaptation. See the [project review document](../plans/2026-02-17-project-review-design.md) for details.

### Azure Container Registry (ACR)

- **Tier**: Basic ($5/month, 10 GB storage)
- Images are pulled privately by Container Apps — no public access needed.

### Region Selection

Choose based on data residency requirements:
- **Australia**: `australiaeast` (Sydney) or `australiasoutheast` (Melbourne)
- **US**: `eastus` (Virginia) or `westus2` (Washington)
- **Europe**: `westeurope` (Netherlands) or `uksouth` (London)

---

## 3. Cost Estimate

Approximate monthly costs for a single-tenant deployment (~1,000 requests/day):

| Service | Configuration | Est. Monthly Cost (USD) |
|---------|--------------|------------------------|
| Container Apps | Consumption plan, pay-per-use | $0–10 |
| Azure DB for PostgreSQL | Burstable B1ms | $12–15 |
| ACR | Basic tier | $5 |
| VNet / Private Endpoints | Included (minimal cost) | $0–1 |
| **Total** | | **$17–30** |

> Container Apps consumption plan has a generous free grant: 180,000 vCPU-seconds and 360,000 GB-seconds per subscription per month.

Verify current pricing: [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)

---

## 4. SSO / Authentication Options

### Option A: Easy Auth (Built-in Authentication) — Recommended

Azure Container Apps has a **built-in authentication layer** ("Easy Auth") that handles Entra ID authentication transparently at the platform level.

- **How it works**: Enable the authentication feature on the Container App and configure it with the customer's Entra ID tenant. Unauthenticated users are redirected to the Microsoft sign-in page. After authentication, verified identity claims are forwarded to the app in HTTP headers (`X-MS-CLIENT-PRINCIPAL`, `X-MS-CLIENT-PRINCIPAL-NAME`).
- **Customer identity**: Users sign in with their existing Microsoft 365 / Entra ID corporate credentials.
- **No app code changes**: The app receives pre-authenticated requests with identity headers.
- **MFA**: Enforced via the customer's Entra ID Conditional Access policies.
- **Best for**: Fastest path to production; customers already using Microsoft 365.

### Option B: Entra ID Direct JWT Validation

For more control over the authentication flow:

- **How it works**: Register the application in the customer's Entra ID tenant. The FastAPI backend validates Entra-issued JWTs using the `fastapi-azure-auth` library or standard OIDC JWT validation.
- **Customer identity**: Users authenticate with their Entra ID credentials. Supports both single-tenant and multi-tenant app registrations.
- **Features**: App-level role-based access control via Entra ID app roles, group claims, Conditional Access integration.
- **Best for**: When the app needs fine-grained user identity for audit logging, role-based access, or custom authorization logic.

### Option C: Entra External ID

For customers who need to authenticate external users (partners, contractors, clients) alongside internal staff:

- **How it works**: Entra External ID (formerly Azure AD B2C) provides a separate identity directory for external users, with federation to social providers, SAML/OIDC IdPs, or local accounts.
- **Best for**: Multi-stakeholder deployments where not all users have corporate Entra ID accounts.

---

## 5. Private Access (No Public Exposure)

### Option A: Easy Auth (Entra ID Required) — Recommended

- **How it works**: The Container App's public endpoint is accessible, but Easy Auth requires Entra ID authentication before any request reaches the app. Only users in the customer's Entra ID tenant (or configured guest accounts) can access it.
- **VPN required**: No — works over the public internet with identity verification.
- **Public exposure**: The URL is reachable, but unauthenticated requests are redirected to Microsoft sign-in. The app is never exposed to unauthenticated traffic.
- **Additional hardening**: Combine with Entra ID **Conditional Access** to restrict access by IP range, device compliance, or location.
- **Best for**: Simple setup with strong identity-based access control.

### Option B: VNet-Internal Container Apps + VPN

- **How it works**: Set Container Apps ingress to `"internal"` — only traffic from within the VNet can reach the service. Users must be on the corporate network via **Azure VPN Gateway** (point-to-site or site-to-site) or **ExpressRoute** (dedicated private link).
- **VPN required**: Yes.
- **Public exposure**: Zero — the Container App URL is not reachable from the public internet.
- **Best for**: Maximum isolation; customers with existing Azure VPN or ExpressRoute infrastructure.

### Option C: Azure Front Door + Private Link

- **How it works**: Azure Front Door provides global edge security (WAF, DDoS protection, geo-filtering) with a Private Link backend connection to Container Apps. Authentication can be enforced at the Front Door layer via Entra ID.
- **VPN required**: No.
- **Public exposure**: Front Door URL is public, but WAF rules + Entra ID authentication filter all traffic before it reaches the app.
- **Best for**: Enterprise deployments needing edge security, global availability, or WAF protection.

### Option D: Azure Application Gateway + WAF

- **How it works**: Regional load balancer with Web Application Firewall and optional Entra ID pre-authentication. Container Apps backend is VNet-internal.
- **VPN required**: No (if using Entra ID auth at the gateway) or Yes (if fully internal).
- **Public exposure**: Configurable — fully internal or public with WAF + auth.
- **Best for**: Regional deployments needing WAF without global Front Door.

---

## 6. Power BI Integration Notes

Azure is a natural fit for customers who use **Power BI** for reporting:

- **Azure Database for PostgreSQL** has a native Power BI connector — connect directly to the managed database.
- Deploy the database in the same region and subscription as the customer's Power BI workspace for lowest latency.
- The Cashflow App includes database views (`vw_phase_comparison`, `vw_per_delivery`) designed for BI tool consumption.
- If the customer's Power BI environment uses Azure SQL, consider the PostgreSQL vs Azure SQL trade-off documented in the [project review](../plans/2026-02-17-project-review-design.md).
