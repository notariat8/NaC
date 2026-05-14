# IDaaS Source Summary

Source repository: `ofunk/IDaaS`

## Product Thesis

IDaaS is a Germany-centered identity-verification and IAM-projection concept.
It uses German eID through AusweisApp as the trust anchor and turns verified
claims into purpose-bound assertions or target IAM projections.

## MVP Scope

- verification start and status API
- AusweisApp-oriented eID orchestration
- consent and audit capture
- signed assertions for customer applications
- at least one production-near IAM connector
- claim-to-attribute mapping rules

## Target Systems

- Microsoft Entra ID
- Oracle IAM
- SCIM-compatible targets

## NoC Adaptation

The former standalone SaaS concept is now treated as a NoC plugin. The plugin
does readiness planning, contract review, and metadata-only evidence by default.
Production eID transactions or IAM writes require a separately reviewed
connector and explicit human approval.
