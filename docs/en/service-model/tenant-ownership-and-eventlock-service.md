# Tenant Ownership And EventLock As A Service

## Question

Who should be the cloud tenant owner for audit-proof eventstreaming, and is a
central EventLock service operated by Function8 useful?

## Short Answer

Yes. A central EventLock-as-a-Service is useful for non-IT organizations **if**
each customer receives a dedicated subinstance with separate keys and isolated
retention.

## Recommended Target Model

Recommendation: `provider_managed_dedicated_subtenant`

- Function8 operates the platform centrally: operations, security baseline and
  SLA.
- Each customer receives a dedicated subinstance, namespace or account with a
  separate journal.
- Each customer receives tenant-specific keys and immutable retention.
- Critical changes, such as retention or legal hold, require dual control.

## Why This Model Fits

- Reduces administration effort for notaries and law firms without deep cloud
  expertise.
- Satisfies compliance requirements through isolation and a clear
  responsibility matrix.
- Enables standardized, repeatable audit processes across many customers.

## Responsibility Matrix

### Function8, Provider

- Platform operation and monitoring.
- Security baseline and incident process.
- Maintenance of eventstream components.

### Customer, Tenant Or Organization

- Data classification.
- Legal-hold decisions.
- Approval of audit access.
- Role and access approvals for own files.

## Technical Guardrails Per Customer Subinstance

- Dedicated stream namespace.
- Dedicated immutable journal bucket or container.
- Dedicated KMS, Key Vault or Vault key.
- Dedicated evidence-index area.
- Tenant-specific access policies.

## Operating Process For New Customers

1. Provision customer subinstance.
2. Create and assign tenant key.
3. Enable immutable retention.
4. Adopt role model from the fork.
5. Enable audit read path and reporting.
6. Accept with go-live checklist per cloud runbook.

## Connection To Customer Forks

Every customer fork references these policies as binding:

- [policies/tenant-ownership-policy.yaml](../../../policies/tenant-ownership-policy.yaml)
- [policies/access-control-policy.yaml](../../../policies/access-control-policy.yaml)
- [policies/revisionssicherheit-eventstream-policy.yaml](../../../policies/revisionssicherheit-eventstream-policy.yaml)

This keeps operating model, rights and audit-proof evidence synchronized.
