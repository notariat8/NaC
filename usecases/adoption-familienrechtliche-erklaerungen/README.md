# Adoption / familienrechtliche Erklaerungen

Status: KG baseline  
KG node: `case.adoption_familienrechtliche_erklaerungen`  
Primary source anchors: BeurkG, BGB Section 1750

## Goal

Prepare a notary-office usecase package for adoption consent and related
family-law declarations where notarial recording or certification is required.
The workflow must treat the matter as highly sensitive and track court route,
capacity, warnings, approvals and delivery evidence.

## Scope

- Intake for declaration type, child/adoptee context, consenting party, court
  destination, warning notes and additional approvals.
- Draft/declaration package for notarial recording.
- Family-court delivery and response tracking.

## Out of Scope

- No family-court decision prediction.
- No real child, adoption or family-sensitive data in Git.
- No declaration without notarial warning and capacity review.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `case.type` | Which adoption or family-law declaration is needed? | Notary | Sensitive family data |
| `child.identity_context` | Which child/adoptee context is relevant? | Client | Sensitive personal data |
| `consenting_party.identity` | Who consents and is capacity reviewed? | Notary | Sensitive personal data |
| `court.destination` | Which family court receives the declaration? | Notary clerk | Mandate metadata |
| `irrevocability.warning` | Which warnings must be documented? | Notary | Sensitive process data |
| `additional.approvals` | Are further consents or approvals required? | Notary | Sensitive family data |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Consent declaration | Core notarial declaration. | Metadata or synthetic only. |
| Court reference | Identifies delivery target. | Evidence reference only. |
| Approval evidence | Supports consent chain. | Evidence reference only. |
| Warning notes | Documents notarial warning gate. | Evidence reference only. |

## Decisions

- Adoption consent, revocation/withdrawal path or other family declaration.
- Additional approval required, available, blocked or unknown.
- Court delivery route.
- Whether capacity/support flags require special handling.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Identity and capacity reviewed | Notary | Declaration |
| Irrevocability and condition warning reviewed | Notary | Execution |
| Additional approval status reviewed | Notary | Court delivery |
| Court delivery package ready | Notary clerk | Submission |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | High-sensitivity family workflow guardrails. |
| `noc-idaas` | Identity support where permitted. |

## Delivery Tasks

1. Define family declaration intake schema.
2. Add high-sensitivity privacy labels and red-flag checks.
3. Add warning and approval review gates.
4. Add family-court delivery state model.
5. Validate with synthetic non-personal fixtures.

## Acceptance Criteria

- Warnings and capacity review block execution.
- Court destination is explicit.
- Approval status is visible.
- No real child or adoption data is committed.

