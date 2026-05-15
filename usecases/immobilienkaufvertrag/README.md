# Immobilienkaufvertrag

Status: KG baseline  
KG node: `case.immobilienkaufvertrag`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)
Primary source anchors: BeurkG, BGB Section 311b, GBO

## Goal

Prepare a notary-office usecase package for purchase or sale of land, a house,
apartment ownership, partial ownership or comparable real-estate assets. The
package must collect open information, bind land-register and XNP readiness,
support draft preparation and track execution evidence without storing real
mandate data in Git.

## Scope

- Intake for seller, buyer, property, purchase price, possession transfer,
  encumbrances, approvals and financing.
- Draft package preparation for human notarial review.
- Land-register, approval, tax and payment-maturity evidence references.
- Filing and Day2 follow-up metadata after execution.

## Out of Scope

- No automated legal advice as final truth.
- No portal scraping or filing without a reviewed connector.
- No real land-register excerpts, IDs, addresses, prices or mandate documents
  in the repository.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `property.identity` | Which land register district, sheet, parcel, unit and designation identify the object? | Notary clerk | Property register data |
| `seller.identity` | Who sells and how are identity, capacity and authority verified? | Notary clerk | Personal data |
| `buyer.identity` | Who buys, in which shares and through which representation? | Notary clerk | Personal data |
| `purchase.price` | Which price, payment route and maturity conditions apply? | Notary | Financial data |
| `encumbrances.current` | Which rights remain, are deleted or are assumed? | Notary clerk | Property register data |
| `financing.required` | Is a new financing land charge needed? | Notary clerk | Financial data |
| `possession.transfer` | When do possession, benefits, burdens and risks transfer? | Notary | Mandate metadata |
| `public.approvals` | Which approvals, pre-emption waivers and tax clearances are needed? | Notary clerk | Mandate metadata |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Current land register excerpt | Confirms ownership, property and rights. | Evidence reference only in Git. |
| Draft purchase contract | Human-reviewed draft and release trace. | Synthetic or metadata only in Git. |
| Approval and tax-clearance evidence | Tracks municipal, court, administrator, spouse, bank or tax steps. | External reviewed evidence store. |
| Filing trace | Tracks land-register application, notices and completion. | Metadata only. |

## Decisions

- Financing route: separate appointment, combined appointment, not required or
  unknown.
- Encumbrance handling: delete, assume, preserve, mixed or unknown.
- Consumer draft period applicability and proof.
- Whether additional approvals are blockers before filing.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Identity, capacity and representation review | Notary | Appointment and execution |
| Land-register review | Notary | Draft release |
| Consumer draft period check where applicable | Notary | Beurkundung |
| Payment maturity and filing package ready | Notary clerk | Closing execution |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Regulated workflow guardrails and evidence model. |
| `noc-grundbuch-portal` | Land-register access/readiness companion. |
| `noc-bnotk-xnp` | Notary workstation and filing route readiness where needed. |

## Workflow Dependencies

- `workflows/contracts/`: intake schema, approval contract and evidence fields.
- `workflows/python/`: deterministic completeness checks and plan preview.

## Delivery Tasks

1. Convert KG nodes into a typed intake contract.
2. Bind land-register plugin output to `property.identity` and
   `encumbrances.current`.
3. Add draft-generation prompt contract with explicit human review gate.
4. Add maturity, approval and filing state machine.
5. Validate with a synthetic property and synthetic parties.

## Acceptance Criteria

- All required KG nodes can be marked open or in progress without real values.
- Missing land-register evidence blocks draft release.
- Missing identity or representation evidence blocks appointment readiness.
- Financing and encumbrance decisions are explicit before execution.
- `scripts/validate_knowledge_graph.py` passes.

