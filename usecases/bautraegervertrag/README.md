# Bautraegervertrag

Status: KG baseline  
KG node: `case.bautraegervertrag`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)
Primary source anchors: BeurkG, BGB Sections 311b and 650u, AbschlagsV, GBO

## Goal

Prepare a notary-office usecase package for developer contracts covering a
property or unit and construction/renovation obligations. The workflow must
capture developer authority, buyer status, object state, construction
specification, installment plan, security model, acceptance and evidence.

## Scope

- Intake for developer, buyer, land-register state, unit/object and construction
  phase.
- Building specification, permits, plan attachments and maturity evidence.
- Consumer draft period, installment plan and security review gates.
- Filing, completion, handover and defect/acceptance metadata.

## Out of Scope

- No construction-technical assessment as final truth.
- No real buyer, price, plan or permit documents in Git.
- No automated acceptance or payment release.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `developer.identity` | Who is developer and who may represent it? | Notary clerk | Company data |
| `buyer.identity` | Who buys and is consumer handling required? | Notary | Personal data |
| `object.identity` | Which unit/property and construction phase are involved? | Notary clerk | Property register data |
| `construction.specification` | Which plans, permits and building description define performance? | Developer | Property metadata |
| `installment.plan` | Which installment and maturity model applies? | Notary | Financial data |
| `defects.acceptance` | How are acceptance, handover and defects handled? | Notary | Mandate metadata |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Developer contract draft | Human-reviewed deed. | Synthetic or metadata only. |
| Building specification and plans | Defines construction performance. | Evidence reference only. |
| Land-register and division state | Confirms property route. | Evidence reference only. |
| Consumer and installment evidence | Tracks review and maturity requirements. | Metadata only. |

## Decisions

- Installment schedule or alternative security model.
- Planned, under-construction, completed or mixed object state.
- Whether WEG division, buyer financing or land charge workflow is linked.
- Whether consumer draft period blocks appointment.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Consumer draft period checked | Notary | Appointment |
| Installment/security model reviewed | Notary | Draft release |
| Building specification package complete | Notary clerk | Execution |
| Filing and maturity package ready | Notary clerk | Closing |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Guardrails and evidence model. |
| `noc-grundbuch-portal` | Land-register and division state review. |
| `noc-bnotk-xnp` | Filing route readiness. |
| `noc-idaas` | Identity support where permitted. |

## Delivery Tasks

1. Build developer-contract intake schema.
2. Add consumer and installment warning gates.
3. Link optional WEG division and financing/land-charge dependencies.
4. Add construction evidence package state model.
5. Validate with synthetic developer and buyer fixtures.

## Acceptance Criteria

- Consumer and installment gates block appointment/release where incomplete.
- Object state and construction package are explicit.
- Linked land-register and WEG dependencies are visible.
- No real plan, permit or price data is committed.

