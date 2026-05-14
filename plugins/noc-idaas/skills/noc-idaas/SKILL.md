---
name: noc-idaas
description: Use when planning German eID verification readiness, AusweisApp-oriented identity checks, verified-claim minimization, consent/audit evidence, or IAM projection readiness for Entra ID, Oracle IAM, or SCIM targets in regulated NoC workflows.
---

# NoC IDaaS

## Operating Boundary

Runtime mode: `local-eid-iam-readiness-companion`.

This plugin plans eID and IAM projection workflows. It does not execute
production eID transactions, store identity documents, write to IAM systems, or
submit external API calls unless a separate reviewed connector explicitly
implements that action. Default to plan-preview, metadata-only evidence, and
human approval before any external or personal-data processing step.

## Allowed Work

- Classify the verification purpose, actor role, tenant, target application,
  data class, and review owner.
- Define minimal claim sets such as `fullName`, `dateOfBirth` or `ageOverX`,
  `verificationLevel`, `verificationSource`, `verifiedAt`, and
  `consentPurpose`.
- Prepare German eID and AusweisApp readiness checklists.
- Prepare IAM projection readiness for Entra ID, Oracle IAM, and SCIM targets.
- Review API and event contracts in dry-run form.
- Create metadata-only evidence templates for consent, verification, projection,
  revocation, and Day2 follow-up.

## Prohibited Work

- Store eID raw data, full identity-document dumps, tax IDs, secrets, private
  keys, certificate material, access tokens, one-time codes, or session cookies
  in Git.
- Upload real identity data or client personal data to an LLM without an
  explicit approved data-processing basis.
- Start production eID transactions, write to IAM systems, or call protected
  identity APIs without reviewed connector code and human approval.
- Reuse verified claims beyond the documented purpose.

## Workflow

1. Classify the business context, purpose, tenant, target system, actor role,
   reviewer role, and data class.
2. Define the minimum claim set and retention expectation for the concrete
   purpose.
3. Check readiness for AusweisApp, client application redirects, webhook or
   polling mode, consent text, audit storage, and tenant isolation.
4. If IAM projection is requested, classify target type: `entra`, `oracle`, or
   `scim`.
5. Produce a plan preview before any external or personal-data processing.
6. Ask for explicit human approval before production eID, IAM, or API actions.
7. Capture evidence metadata only: timestamp, actor role, purpose, claim-set
   version, tenant, target system, decision, result, and follow-up owner.
8. For Day2, report expired assertions, revocations, failed projections,
   retention drift, and connector recertification tasks.

## Output Shape

Return concise sections named `Readiness`, `Claim Set`, `Projection`, `Approval
Needed`, `Evidence`, and `Day2 Follow-up`.

## Source Plan

- `docs/plugin-plans/idaas-plugin-integration.md`
