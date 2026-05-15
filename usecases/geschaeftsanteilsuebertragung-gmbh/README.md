# Geschaeftsanteilsuebertragung GmbH

Status: KG baseline  
KG node: `case.geschaeftsanteilsuebertragung_gmbh`  
Primary source anchors: BeurkG, GmbHG Section 15, HGB Section 12

## Goal

Prepare a notary-office usecase package for sale, gift or other transfer of
GmbH shares. The workflow must capture share identity, chain of title, parties,
consent restrictions, AML/beneficial-owner flags, consideration, updated
shareholder list and submission evidence.

## Scope

- Intake for company, shares, seller, buyer, price/gift route and consents.
- Review of articles restrictions, pre-emption rights and authority.
- Preparation of transfer deed and shareholder list.
- Filing/submission trace for register-relevant documents.

## Out of Scope

- No tax advice as final truth.
- No real shareholder, price or AML data in Git.
- No register submission without reviewed notarial execution.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `company.identity` | Which GmbH and register data define the target? | Notary clerk | Company register data |
| `share.identity` | Which shares and chain of title are transferred? | Notary | Company financial data |
| `seller.identity` | Who transfers and how is authority proven? | Notary clerk | Personal or company data |
| `buyer.identity` | Who acquires and which AML flags apply? | Notary | Compliance data |
| `consents.restrictions` | Are consent restrictions or pre-emption rights triggered? | Notary | Company data |
| `consideration.tax` | Is this sale, gift, mixed transfer or other route? | Notary | Financial data |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Share transfer agreement | Human-reviewed notarial deed. | Synthetic or metadata only. |
| Updated shareholder list | Register-relevant follow-up artifact. | Evidence reference only. |
| Consent/waiver evidence | Confirms restrictions are handled. | Evidence reference only. |
| AML/beneficial-owner review | Compliance gate evidence. | Metadata only. |

## Decisions

- Sale, gift, mixed transfer, pool/trust or other route.
- Consent or waiver needed.
- Shareholder list ready or blocked.
- Whether post-closing register or transparency-register work is triggered.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Chain of title and restrictions reviewed | Notary | Deed release |
| Seller/buyer identity and authority reviewed | Notary | Execution |
| AML and beneficial-owner flags reviewed | Notary | Closing |
| Updated shareholder list ready | Notary clerk | Submission |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Company workflow guardrails and evidence model. |
| `noc-bnotk-xnp` | Notary filing route readiness. |
| `noc-handelsregister` | Shareholder-list submission route. |
| `noc-idaas` | Identity support where permitted. |

## Delivery Tasks

1. Build share-transfer intake schema.
2. Add share chain and consent checklist.
3. Add shareholder-list generation/review workflow.
4. Add AML red-flag metadata.
5. Validate with synthetic shareholder fixtures.

## Acceptance Criteria

- Chain of title and consent review block execution.
- Updated shareholder list cannot be marked ready before transfer review.
- AML flags are explicit.
- No real price, identity or ownership data is committed.

