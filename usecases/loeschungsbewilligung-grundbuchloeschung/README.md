# Loeschungsbewilligung / Grundbuchloeschung

Status: KG baseline  
KG node: `case.loeschungsbewilligung_grundbuchloeschung`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)
Primary source anchors: BeurkG, GBO Sections 19/29/46, BGB Section 875

## Goal

Prepare a notary-office usecase package for deletion of registered land rights,
especially old land charges after loan repayment. The package must verify the
right, beneficiary authority, owner consent where required, letter handling and
land-register filing evidence.

## Scope

- Intake for property, affected right, beneficiary, owner and filing route.
- Review of deletion authorization, public form and evidence package.
- Handling of book rights, letter rights and replacement evidence.
- Filing and completion trace after land-register deletion.

## Out of Scope

- No deletion without authority and land-register review.
- No real land-register excerpts, bank consents or letters in Git.
- No assumption that every old right is deletable without further evidence.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `property.identity` | Which land register district, sheet, section and entry are affected? | Notary clerk | Property register data |
| `right.identity` | Which right should be deleted? | Notary clerk | Property register data |
| `creditor.authorization` | Who may consent to deletion and how is authority proven? | Notary | Company or financial data |
| `owner.consent` | Is owner consent or representation needed? | Notary clerk | Personal or company data |
| `brief.status` | Is this a book right or is a land-charge/mortgage letter involved? | Notary clerk | Financial metadata |
| `filing.route` | Which XNP/land-register filing route and completion notice apply? | Notary clerk | Technical metadata |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Deletion authorization | Proves beneficiary consent. | Evidence reference only. |
| Land-register excerpt | Confirms affected right and current owner. | Evidence reference only. |
| Letter or replacement evidence | Supports deletion of letter rights. | External reviewed evidence store. |
| Filing response | Confirms application and completion. | Metadata only. |

## Decisions

- Full deletion, partial deletion or correction.
- Book right, letter present, replacement evidence or blocked.
- Whether owner consent is necessary.
- Whether creditor identity changed by merger, assignment or succession.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Beneficiary authorization reviewed | Notary | Filing |
| Letter/evidence handling complete | Notary clerk | Filing |
| Land-register entry matched | Notary | Draft/application release |
| Completion notice reviewed | Notary clerk | Closing |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Guardrails and evidence model. |
| `noc-grundbuch-portal` | Land-register state review. |
| `noc-bnotk-xnp` | Notary filing route readiness. |

## Delivery Tasks

1. Convert KG nodes into a deletion intake schema.
2. Add evidence checklist for book and letter rights.
3. Bind land-register review to affected-right matching.
4. Add filing/completion state machine.
5. Validate with synthetic bank and property fixtures.

## Acceptance Criteria

- Missing beneficiary authority blocks filing.
- Missing letter/replacement evidence blocks letter-right deletion.
- The affected right is matched against current land-register metadata.
- No real bank or property data is committed.

