# Grundschuld / Hypothekenbestellung

Status: KG baseline  
KG node: `case.grundschuld_hypothek`  
Primary source anchors: BeurkG, GBO, BGB land-charge rules

## Goal

Prepare a notary-office usecase package for creation, amendment or refinancing
of a land charge or mortgage. The workflow must capture bank instructions,
owner and debtor data, charge amount, rank, prior rights and enforcement-clause
scope, then produce a reviewed filing package.

## Scope

- Intake for property, owner, borrower/debtor, bank, amount and rank.
- Bank instruction review and deviation tracking.
- Land-register filing readiness and evidence metadata.
- Consumer and enforcement-clause review flags where applicable.

## Out of Scope

- No automatic acceptance of bank order text.
- No real bank instructions or land-register excerpts in Git.
- No filing without notarial review and connector approval.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `property.identity` | Which property or unit is to be charged? | Notary clerk | Property register data |
| `owner.identity` | Who grants the charge and with which authority? | Notary clerk | Personal or company data |
| `debtor.identity` | Who is the borrower or personal debtor? | Notary | Financial data |
| `lender.identity` | Which creditor bank and channel apply? | Notary clerk | Mandate metadata |
| `charge.amount` | Which amount, interest and ancillary charges are requested? | Notary clerk | Financial data |
| `security.purpose` | Which financing context is secured? | Notary | Financial data |
| `ranking.requirement` | Which rank is needed and which rights precede it? | Notary clerk | Property register data |
| `enforcement.clause` | Which immediate-enforcement scope is requested? | Notary | Financial data |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Bank land-charge order | Source for amount, creditor, wording and filing request. | Evidence reference only. |
| Land-register excerpt | Confirms ownership and rank situation. | Evidence reference only. |
| Draft deed | Human-reviewed land-charge or mortgage deed. | Synthetic or metadata only. |
| Filing response | Tracks land-register application and completion. | Metadata only. |

## Decisions

- Instrument: land charge, mortgage, amendment or refinancing.
- Enforcement clause: property only, personal assets, both or not requested.
- Rank handling: first rank, subordinate rank, deletion of prior rights or
  consent required.
- Bank instruction deviations: accepted, corrected, blocked or pending.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Bank instruction matched to draft | Notary clerk | Draft release |
| Rank and prior-rights review | Notary | Filing |
| Owner/debtor identity and representation | Notary | Appointment |
| Enforcement-clause review | Notary | Execution |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Shared guardrails and evidence model. |
| `noc-grundbuch-portal` | Property and rank review support. |
| `noc-bnotk-xnp` | XNP route readiness for filing. |

## Delivery Tasks

1. Define bank-instruction intake contract.
2. Add deterministic comparison between bank order and deed metadata.
3. Bind land-register rank state to filing readiness.
4. Add enforcement-clause review marker.
5. Validate with synthetic bank and property fixtures.

## Acceptance Criteria

- Amount, creditor, debtor, property and rank must be complete before filing.
- Deviations from bank instruction are explicit and reviewed.
- Missing rank review blocks execution.
- No real financial or property data is committed.

