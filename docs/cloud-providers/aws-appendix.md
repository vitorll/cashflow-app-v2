# Amazon Web Services — Deployment Appendix

This appendix maps the Cashflow App's [generic architecture](../architecture-overview.md) to AWS services.

---

## 1. Service Mapping

| Generic Term | AWS Service |
|-------------|------------|
| Managed container service | **ECS Fargate** or **AWS App Runner** |
| Managed PostgreSQL | **Amazon RDS for PostgreSQL** |
| Container registry | **Amazon ECR** |
| Private networking | **VPC** + **VPC Endpoints** |
| HTTPS ingress | **Application Load Balancer (ALB)** + **ACM** certificates |
| IAM | **AWS IAM** + **IAM Identity Center** |
| Secrets management | **AWS Secrets Manager** |
| Audit logs | **AWS CloudTrail** |
| Network flow logs | **VPC Flow Logs** |
| Logging | **Amazon CloudWatch Logs** |

### Which Container Service?

| | ECS Fargate | App Runner |
|--|------------|------------|
| **Simplicity** | More configuration (task defs, services, ALB) | Simpler (source → running service) |
| **VPC integration** | Native (tasks run in VPC subnets) | Supported via VPC connector |
| **Scaling** | Fine-grained control | Automatic, less configurable |
| **Cost** | Higher (ALB has fixed ~$16/month) | Lower for low-traffic apps |
| **Best for** | Enterprise environments needing full control | Simple deployments, cost-sensitive |

**Recommendation**: App Runner for most single-tenant deployments (simpler, cheaper). ECS Fargate when the customer needs full VPC control or already uses ECS.

---

## 2. Hosting Setup

### App Runner

- **Source**: ECR image (automatic deployments on image push)
- **CPU/Memory**: 0.25 vCPU / 0.5 GB for low traffic
- **VPC connector**: Required for private RDS access
- **Auto-scaling**: Min 1, max 5 instances
- **Health check**: `/health` endpoint

### ECS Fargate (if chosen)

- **Task definition**: 0.25 vCPU, 0.5 GB memory
- **Service**: 1 desired task (scale as needed)
- **ALB**: Application Load Balancer with ACM TLS certificate
- **Subnets**: Tasks in private subnets, ALB in public subnets
- **Security groups**: ALB → tasks on port 8000; tasks → RDS on port 5432

### Amazon RDS for PostgreSQL

- **Instance class**: `db.t4g.micro` (2 vCPU, 1 GB RAM) — eligible for free tier (first 12 months)
- **Storage**: 20 GB gp3 SSD
- **Network**: Private subnets only (no public access)
- **Backups**: Automated daily snapshots, 7-day retention
- **Multi-AZ**: Optional — adds a standby replica for high availability

### Amazon ECR

- Private Docker repository in the customer's AWS account. Images are scanned for vulnerabilities on push.

### Region Selection

Choose based on data residency requirements:
- **Australia**: `ap-southeast-2` (Sydney)
- **US**: `us-east-1` (N. Virginia) or `us-west-2` (Oregon)
- **Europe**: `eu-west-1` (Ireland) or `eu-central-1` (Frankfurt)

---

## 3. Cost Estimate

Approximate monthly costs for a single-tenant deployment (~1,000 requests/day):

### App Runner (Recommended)

| Service | Configuration | Est. Monthly Cost (USD) |
|---------|--------------|------------------------|
| App Runner | 0.25 vCPU, 0.5 GB, pay-per-use | $5–10 |
| RDS for PostgreSQL | db.t4g.micro | $12–15 |
| ECR | Storage-based | $1–2 |
| **Total** | | **$15–25** |

### ECS Fargate + ALB

| Service | Configuration | Est. Monthly Cost (USD) |
|---------|--------------|------------------------|
| ECS Fargate | 0.25 vCPU, 0.5 GB, 1 task | $5–8 |
| ALB | Fixed + usage | $16–20 |
| RDS for PostgreSQL | db.t4g.micro | $12–15 |
| ECR | Storage-based | $1–2 |
| **Total** | | **$35–45** |

> The ALB fixed cost ($16/month) makes ECS significantly more expensive for low-traffic apps. App Runner avoids this overhead.

> RDS free tier (first 12 months): 750 hours/month of db.t4g.micro + 20 GB storage.

Verify current pricing: [AWS Pricing Calculator](https://calculator.aws/)

---

## 4. SSO / Authentication Options

### Option A: ALB + OIDC — Recommended (ECS deployments)

The Application Load Balancer can natively authenticate users via any OIDC-compliant identity provider before forwarding requests to the app.

- **How it works**: Configure an OIDC authentication action on the ALB listener rule. Unauthenticated users are redirected to the IdP login page. After authentication, the ALB forwards verified user claims in HTTP headers (`x-amzn-oidc-data`, `x-amzn-oidc-identity`).
- **Customer identity**: Works with any OIDC provider — Azure AD (Entra ID), Okta, Google Workspace, Ping, Auth0, etc.
- **No app code changes**: The app receives pre-authenticated requests with identity headers.
- **Limitation**: Only available with ALB (ECS deployments), not App Runner.

### Option B: Amazon Cognito

Managed user directory with built-in OIDC/SAML federation:

- **How it works**: Create a Cognito User Pool, configure federation with the customer's IdP. The app validates Cognito-issued JWTs in the FastAPI backend.
- **Customer identity**: Supports SAML 2.0 and OIDC federation with Azure AD, Okta, Google, and others. Users sign in with their existing corporate credentials via Cognito's hosted UI.
- **Features**: MFA, custom domains, adaptive authentication, user migration lambdas.
- **Best for**: When you need a managed user directory or App Runner deployments (where ALB+OIDC isn't available).

### Option C: AWS Verified Access

AWS's zero-trust network access service:

- **How it works**: Verified Access evaluates identity (from IAM Identity Center or third-party IdP) and optionally device posture before granting access to the application.
- **Customer identity**: Supports IAM Identity Center (with SAML federation to external IdPs) and direct OIDC providers.
- **No VPN required**: Users access the app via a Verified Access endpoint over the internet, but only after identity and policy evaluation.
- **Best for**: Enterprise zero-trust requirements with device posture checks.

---

## 5. Private Access (No Public Exposure)

### Option A: ALB + OIDC Pre-Authentication — Recommended

- **How it works**: Public-facing ALB, but the OIDC authentication rule ensures only authenticated corporate users can access the app. Unauthenticated requests never reach the container.
- **VPN required**: No — works over the public internet with identity verification.
- **Public exposure**: The ALB URL is reachable, but only authenticated traffic passes through.
- **Best for**: Simple setup, no VPN infrastructure needed.

### Option B: Private Subnets + Internal ALB + VPN

- **How it works**: Deploy ECS tasks and ALB in private subnets. Users access via **AWS Client VPN** or **Site-to-Site VPN**.
- **VPN required**: Yes.
- **Public exposure**: Zero — nothing is reachable from the public internet.
- **Best for**: Maximum isolation; customers with existing AWS VPN infrastructure.

### Option C: AWS Verified Access

- **How it works**: Verified Access provides an access endpoint that validates identity and device posture. No VPN needed, but only verified users can connect.
- **VPN required**: No.
- **Public exposure**: The Verified Access endpoint is reachable, but unauthenticated/unauthorized requests are rejected.
- **Best for**: Zero-trust access with device compliance checks.

### Option D: AWS PrivateLink

- **How it works**: Expose the service via a VPC endpoint service. Customers with **AWS Direct Connect** or **VPN** access the app through a private endpoint in their VPC.
- **VPN required**: Yes (via Direct Connect or VPN).
- **Public exposure**: Zero.
- **Best for**: Customers with existing Direct Connect links or multi-account AWS environments.
