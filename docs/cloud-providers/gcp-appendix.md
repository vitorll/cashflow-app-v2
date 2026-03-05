# Google Cloud Platform — Deployment Appendix

This appendix maps the Cashflow App's [generic architecture](../architecture-overview.md) to Google Cloud services.

---

## 1. Service Mapping

| Generic Term | GCP Service |
|-------------|-------------|
| Managed container service | **Cloud Run** |
| Managed PostgreSQL | **Cloud SQL for PostgreSQL** |
| Container registry | **Artifact Registry** |
| Private networking | **VPC** + **Private Service Connect** |
| HTTPS ingress | **Cloud Run managed ingress** (auto-provisioned TLS) |
| IAM | **Cloud IAM** |
| Secrets management | **Google Cloud Secret Manager** |
| Audit logs | **Cloud Audit Logs** |
| Network flow logs | **VPC Flow Logs** |
| Logging | **Cloud Logging** |

---

## 2. Hosting Setup

### Cloud Run

- **Plan**: Pay-per-use (no reserved instances needed for low traffic)
- **VPC connector**: Required for private database access
- **Min instances**: 0 (scales to zero when idle) or 1 (avoids cold starts)
- **Max instances**: 5–10 for a single-tenant deployment
- **CPU/Memory**: 1 vCPU, 512 MB is sufficient for low traffic
- **Concurrency**: 80 requests per instance (default)

### Cloud SQL for PostgreSQL

- **Tier**: `db-f1-micro` (shared vCPU, 0.6 GB RAM, 10 GB SSD) for low traffic; upgrade to `db-g1-small` for better performance
- **IP**: Private IP only (no public IP) via Private Service Connect
- **Backups**: Automated daily backups enabled, 7-day retention
- **High availability**: Optional — adds a standby instance in a second zone
- **Maintenance window**: Configure during off-peak hours

### Artifact Registry

- Docker repository in the customer's GCP project. Images are pulled privately by Cloud Run — no public access needed.

### Region Selection

Choose based on data residency requirements:
- **Australia**: `australia-southeast1` (Sydney) or `australia-southeast2` (Melbourne)
- **US**: `us-central1` (Iowa) or `us-east1` (South Carolina)
- **Europe**: `europe-west1` (Belgium) or `europe-west2` (London)

---

## 3. Cost Estimate

Approximate monthly costs for a single-tenant deployment (~1,000 requests/day):

| Service | Configuration | Est. Monthly Cost (USD) |
|---------|--------------|------------------------|
| Cloud Run | Pay-per-use | $0–5 |
| Cloud SQL for PostgreSQL | db-f1-micro | $8–10 |
| Artifact Registry | Storage-based | $1–2 |
| VPC / Private Service Connect | Included | $0 |
| Managed TLS / Ingress | Included with Cloud Run | $0 |
| **Total** | | **$10–20** |

> Cloud Run's free tier includes 2 million requests/month and 360,000 vCPU-seconds. A low-traffic app may fall largely within it.

Verify current pricing: [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator)

---

## 4. SSO / Authentication Options

### Option A: Identity-Aware Proxy (IAP) — Recommended

Google's **Identity-Aware Proxy** sits in front of Cloud Run and authenticates users before any request reaches the application. No application code changes required.

- **How it works**: IAP intercepts all requests to Cloud Run, redirects unauthenticated users to a Google sign-in page, and forwards verified identity headers (`X-Goog-Authenticated-User-Email`, `X-Goog-IAP-JWT-Assertion`) to the app.
- **Customer identity**: Supports Google Workspace accounts natively. For customers using a non-Google IdP (Okta, Azure AD, etc.), configure **Workforce Identity Federation** to federate the external IdP into IAP.
- **MFA**: Enforced via the customer's IdP policies.
- **Best for**: Fastest path to authenticated access with zero app changes.

### Option B: Workforce Identity Federation + Direct JWT Validation

For more control over the authentication flow:

- **How it works**: Configure Workforce Identity Federation to trust the customer's OIDC/SAML provider. The app's FastAPI backend validates tokens from the federated identity pool using standard JWT validation.
- **Customer identity**: Works with any OIDC/SAML provider (Azure AD, Okta, Google Workspace, Ping Identity, etc.).
- **Best for**: When the app needs fine-grained user identity for audit logging or role-based access.

### Option C: Google Workspace SSO

For customers already using Google Workspace:

- **How it works**: Google acts as the OIDC provider. Users sign in with their corporate Google accounts. FastAPI validates Google-issued JWTs.
- **Best for**: Google-native organisations with no external IdP.

---

## 5. Private Access (No Public Exposure)

### Option A: Identity-Aware Proxy (IAP) — Recommended

- **How it works**: IAP authenticates users at the proxy layer before forwarding requests. The Cloud Run service URL is public, but only IAP-authenticated users can reach the app.
- **VPN required**: No — works over the public internet with identity verification.
- **Public exposure**: The URL is reachable, but unauthenticated requests receive a 403/redirect. The app itself is never exposed to unauthenticated traffic.
- **Best for**: Zero-trust access without VPN infrastructure.

### Option B: Cloud Run Internal Ingress + VPN

- **How it works**: Set Cloud Run ingress to `"internal"` — only traffic from within the VPC can reach the service. Users must be on the corporate network via **Cloud VPN** (IPsec tunnels) or **Cloud Interconnect** (dedicated link).
- **VPN required**: Yes.
- **Public exposure**: Zero — the Cloud Run URL is not reachable from the public internet.
- **Best for**: Maximum isolation; customers with existing VPN infrastructure.

### Option C: Internal HTTPS Load Balancer

- **How it works**: Place Cloud Run behind an internal HTTPS load balancer. Only reachable from peered VPC networks or via VPN/Interconnect.
- **VPN required**: Yes.
- **Public exposure**: Zero.
- **Best for**: Customers with complex network topologies or multi-VPC environments.
