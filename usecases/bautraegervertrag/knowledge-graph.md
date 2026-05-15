# Bautraegervertrag Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `next10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.bautraegervertrag`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `developer.identity` | Developer identity and authority | `open` | `notary_clerk` | Who is developer and how are register, authority and representation proven? |
| `buyer.identity` | Buyer identity and consumer status | `open` | `notary` | Who buys and is consumer-protection handling required? |
| `object.identity` | Object, unit and land-register state | `open` | `notary_clerk` | Which unit, property, construction phase and land-register state are involved? |
| `construction.specification` | Construction specification and completion state | `open` | `developer` | Which building description, plans, permits and completion state define performance? |
| `installment.plan` | Installment and maturity plan | `open` | `notary` | Which installment schedule, security model and maturity prerequisites apply? |
| `defects.acceptance` | Acceptance, defects and handover model | `open` | `notary` | How are acceptance, defects, common property and handover handled? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.developer_contract_draft` | Developer contract draft | `open` |
| `doc.specification_package` | Building specification, plans and permits reference | `open` |
| `doc.land_register_state` | Land-register and division state reference | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.consumer_draft_period` | Consumer draft review period checked | `open` |
| `gate.installment_review` | Installment and security model reviewed | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
