# Cashflow App — Slide Deck Content

> Copy each slide's content into your PowerPoint/Google Slides presentation.
> Presenter notes are included below each slide.

---

## Slide 1: Title

**Cashflow App**
Architecture & Hosting Overview

*Your company logo / client logo*

> **Presenter notes:** This presentation covers the application architecture, cloud hosting model, data residency guarantees, and security posture. The key message: everything runs in your cloud, under your control.

---

## Slide 2: What It Does

**12-Month Rolling Cash Flow Projections**

- Replaces Excel-based cashflow workflows with a purpose-built web app
- Import data from existing Excel workbooks or enter manually
- Real-time recalculation across all phases when any input changes
- 5 views: Dashboard, Forecast, Phase Comparison, P&L, Data Entry

> **Presenter notes:** The app automates the manual processes currently done in Excel. Any data change triggers a cascade recalculation — NCF, phase summaries, P&L — all update instantly.

---

## Slide 3: Application Architecture

**Three-Tier, Single Container**

- **Frontend**: React 19 single-page application
- **Backend**: Python / FastAPI async API with calculation engine
- **Database**: PostgreSQL 16 (managed cloud service)
- Packaged as a **single Docker image** for simple deployment
- Runs as a **non-root user** inside the container

*[Include System Architecture diagram from architecture-overview.md]*

> **Presenter notes:** The multi-stage Docker build compiles the React frontend and bundles it with the Python backend into one image. No separate web server needed — FastAPI serves both the API and the UI. The container runs as a non-root user for security.

---

## Slide 4: Cloud Hosting

**Fully Hosted in Your Cloud Account**

- **Container service** — serverless container hosting (pay-per-use)
- **Managed PostgreSQL** — database with automated backups
- **Container registry** — stores the application image
- **Private networking** — database and internal traffic stay private
- **Managed HTTPS** — TLS certificates handled automatically

Deployable to **Google Cloud**, **AWS**, or **Azure** — see provider appendices for details.

*[Include Cloud Hosting diagram from architecture-overview.md]*

> **Presenter notes:** Everything runs within your cloud account. The container service is serverless — you pay only for active usage, with generous free tiers. The database is fully managed with automated backups. All components communicate over private networking. The app works on any major cloud provider.

---

## Slide 5: Data Residency & Sovereignty

**Your Data Never Leaves Your Cloud**

- All data stored in **your cloud account**, in **your chosen region**
- The application makes **zero external API calls** — no outbound data
- **No telemetry, no analytics, no third-party services**
- **No shared infrastructure** — single-tenant, dedicated instance
- You **own all data and resources** — delete anytime, no vendor lock-in
- Standard PostgreSQL — export via `pg_dump` at any time

> **Presenter notes:** This is the key slide. The application is entirely self-contained. It doesn't call any external services, doesn't send telemetry, and doesn't share infrastructure with anyone. All data sits in your PostgreSQL database, in your chosen region, under your IAM control. PostgreSQL is an open standard — there's no vendor lock-in on the data layer.

---

## Slide 6: Network Security

**Defence in Depth**

- Database has **no public IP** — private access only within the virtual network
- Container service is **VPC-connected** — all database traffic stays private
- **TLS 1.2+** enforced on all external connections
- **Firewall rules** restrict traffic to required ports only
- **Provider IAM** controls who can manage infrastructure
- All management operations recorded in **audit logs**

*[Include Network Security diagram from architecture-overview.md]*

> **Presenter notes:** The database is completely invisible to the public internet. Only the application container can reach it via a private connection. External users connect through managed HTTPS ingress. You can audit all network traffic with your cloud provider's flow logs.

---

## Slide 7: Authentication & Private Access

**Secure Access with Your Existing Identity**

- Integrates with your **existing corporate identity** (Microsoft Entra ID, Google Workspace, Okta, etc.)
- Users sign in with their **existing credentials** — no separate passwords
- All major providers offer **proxy-level authentication** requiring zero app changes
- Optional: restrict to **internal-only access** via VPN or private endpoints

| Approach | Public Internet? | VPN Required? |
|----------|-----------------|---------------|
| Identity-aware proxy | URL reachable, but only authenticated users pass | No |
| Internal ingress + VPN | Not reachable from internet | Yes |

> **Presenter notes:** The app is designed to work with the customer's existing identity system. Every major cloud provider has a proxy service that authenticates users before they can reach the app — this requires zero code changes. For maximum isolation, the app can be deployed as internal-only, accessible only via corporate VPN.

---

## Slide 8: Deployment & Updates

**Automated, Zero-Downtime Deployments**

- CI/CD pipeline: code push → automated tests → build → deploy
- All backend and frontend tests must pass before deployment
- Docker image pushed to **your container registry**
- **Database migrations run automatically** on container startup
- **Zero-downtime** via container service revision management
- Instant **rollback** if health checks fail

> **Presenter notes:** Every code change goes through automated testing before it can be deployed. The deployment creates a new revision — traffic shifts to the new version only after it passes health checks. If anything goes wrong, the previous version is still running and can take over immediately.

---

## Slide 9: Monthly Cost Estimate

**Lightweight, Pay-Per-Use Infrastructure**

| Cost Category | Est. Monthly Cost (USD) |
|---------------|------------------------|
| Container compute (pay-per-use) | $0–10 |
| Managed PostgreSQL | $8–15 |
| Container registry | $1–5 |
| Networking / TLS | Included |
| **Total (typical range)** | **$15–40** |

- Actual cost depends on provider, region, and tier chosen
- All providers offer generous free tiers for low-traffic apps
- No minimum commitment — scale as needed

> **Presenter notes:** These are estimates for a low-traffic deployment (~1,000 requests/day). Google Cloud tends to be cheapest ($10-20/month) due to Cloud Run's free tier. AWS and Azure are similar ($15-30/month). Provider-specific breakdowns are in the appendices.

---

## Slide 10: Security Roadmap

**Planned Enhancements**

| Enhancement | Description |
|------------|-------------|
| **User Authentication** | Corporate identity provider SSO (OIDC/SAML) |
| **Secrets Management** | Cloud-native secrets service with workload identity |
| **Audit Logging** | Tamper-resistant record of all data changes |
| **Rate Limiting** | API-level protection against abuse |

Current foundation: network isolation + data sovereignty + non-root container + automated testing

> **Presenter notes:** The current security posture is built on strong network isolation — the database has no public IP, everything runs in the customer's private network. These planned enhancements add application-level security on top of that foundation. Identity integration means users will authenticate with their existing corporate credentials.

---

## Slide 11: Summary

**Key Takeaways**

1. **Your cloud, your data** — everything runs in your cloud account
2. **No external dependencies** — zero outbound calls, no third-party services
3. **Network-isolated** — database has no public IP
4. **Cloud-agnostic** — deployable to Google Cloud, AWS, or Azure
5. **Cost-effective** — estimated $15–40 USD/month
6. **Zero-downtime deployments** — automated testing and instant rollback
7. **No vendor lock-in** — standard PostgreSQL, exportable at any time

> **Presenter notes:** Reinforce the core message: this is a modern, secure application that runs entirely within the customer's control. They own the data, the infrastructure, and can audit everything. The app works on any major cloud provider, so there's no lock-in on either the data or the hosting side.
