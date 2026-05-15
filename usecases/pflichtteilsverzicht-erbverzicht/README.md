# Pflichtteilsverzicht / Erbverzicht

Status: KG baseline  
KG node: `case.pflichtteilsverzicht_erbverzicht`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)
Primary source anchors: BeurkG, BGB Sections 2346 and 2348

## Goal

Prepare a notary-office usecase package for inheritance waiver and
compulsory-share waiver contracts. The workflow must capture parties, waiver
scope, descendant effects, compensation, approval issues and fairness flags.

## Scope

- Intake for future decedent, waiving party, family context and scope.
- Contract drafting support for inheritance or compulsory-share waiver.
- Compensation and tax/family metadata.
- Personal participation, fairness and approval review gates.

## Out of Scope

- No automated succession-planning advice as final truth.
- No real family, wealth or compensation data in Git.
- No execution without notarial fairness review.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `future_decedent.identity` | Who contracts with the waiving party? | Notary | Personal data |
| `waiver_party.identity` | Who waives and are approvals required? | Notary | Family data |
| `waiver.scope` | Is waiver full, compulsory-share only or limited? | Notary | Sensitive legal data |
| `descendant.effect` | Does the waiver extend to descendants? | Notary | Family data |
| `compensation.model` | Is compensation paid or transferred? | Client | Financial data |
| `family.fairness_flags` | Are dependency, pressure or imbalance flags present? | Notary | Sensitive family data |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Waiver contract draft | Human-reviewed deed. | Synthetic or metadata only. |
| Compensation evidence | Supports settlement route. | Evidence reference only. |
| Fairness review notes | Captures sensitive review gate. | Evidence reference only. |
| Execution and copy trace | Tracks closing. | Metadata only. |

## Decisions

- Erbverzicht, Pflichtteilsverzicht or limited waiver.
- Compensation: none, cash, asset transfer or mixed.
- Descendant extension included or excluded.
- Whether family-law, guardianship or tax review is needed.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Personal participation reviewed | Notary | Appointment |
| Fairness and family flags reviewed | Notary | Draft release |
| Compensation route reviewed | Notary | Execution |
| Copies and storage handled | Notary clerk | Closing |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Sensitive family/succession workflow guardrails. |
| `noc-idaas` | Identity support where permitted. |

## Delivery Tasks

1. Define waiver-intake schema.
2. Add descendant-effect decision model.
3. Add compensation and fairness checklist.
4. Add execution/copy evidence model.
5. Validate with synthetic family fixtures.

## Acceptance Criteria

- Waiver scope is explicit before drafting.
- Fairness flags block release until reviewed.
- Compensation route is captured.
- No real family or financial data is committed.

