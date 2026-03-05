# Cloud Provider Appendices

The Cashflow App is **cloud-agnostic** — it runs as a standard Docker container with a PostgreSQL database, deployable to any major cloud provider. The [Architecture Overview](../architecture-overview.md) describes the application in generic terms.

These appendices map the generic architecture to specific cloud provider services, including setup notes, cost estimates, authentication options, and private access configurations.

## Provider Appendices

| Provider | Appendix | Best For |
|----------|----------|----------|
| [Google Cloud](gcp-appendix.md) | GCP services, IAP, Workforce Identity Federation | Teams already in the Google ecosystem |
| [Amazon Web Services](aws-appendix.md) | AWS services, ALB+OIDC, Cognito, Verified Access | Teams already in the AWS ecosystem |
| [Microsoft Azure](azure-appendix.md) | Azure services, Easy Auth, Entra ID | Teams already using Microsoft 365 / Entra ID |

## Choosing a Provider

The application requires only two managed services:

1. **A container hosting service** that can run a Docker image with HTTPS ingress
2. **A managed PostgreSQL instance** with private networking

Any cloud provider offering these (including smaller providers like DigitalOcean, Fly.io, or Railway) can host the application. The appendices above cover the three major providers in detail because they also offer enterprise features like identity federation, private networking, and compliance certifications that most customers require.
