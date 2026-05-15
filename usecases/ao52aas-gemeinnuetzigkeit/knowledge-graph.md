# AO52 Nonprofit Software Company Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `active-intake`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.ao52aas_gemeinnuetzigkeit`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `purpose.model` | Charitable purpose model | `open` | `founder` | Which charitable purpose, beneficiaries and activities define the organization? |
| `entity.form` | Entity and formation route | `open` | `notary_clerk` | Which legal form, founders and register route are intended? |
| `funding.model` | Funding and revenue model | `open` | `founder` | Which grants, donations, services or commercial activities finance the organization? |
| `governance.rules` | Governance and asset-lock rules | `open` | `notary` | Which governance restrictions, asset-lock clauses and conflict rules are required? |
| `tax.precheck` | Tax precheck route | `open` | `tax_specialist` | Which nonprofit/tax precheck route and evidence package are needed? |
| `software.scope` | Software-company operating scope | `open` | `founder` | Which software activities, IP ownership and service boundaries must be reflected? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.intake_package` | Reviewed intake package | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.identity` | Identity, authority and data minimization reviewed | `open` |
| `gate.notarial_review` | Human notarial review completed | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
