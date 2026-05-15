# Adoption / familienrechtliche Erklaerungen Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `next10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.adoption_familienrechtliche_erklaerungen`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `case.type` | Declaration type | `open` | `notary` | Which adoption or family-law declaration is needed? |
| `child.identity_context` | Child or adoptee context | `open` | `client` | Which child/adoptee context is relevant without storing raw data in Git? |
| `consenting_party.identity` | Consenting party identity and capacity | `open` | `notary` | Who gives consent and are capacity, age or support flags present? |
| `court.destination` | Family court destination | `open` | `notary_clerk` | Which court receives the declaration and which reference is used? |
| `irrevocability.warning` | Irrevocability and condition prohibition flags | `open` | `notary` | Which warnings about irrevocability, conditions or timing must be documented? |
| `additional.approvals` | Additional consents or approvals | `open` | `notary` | Are parental, guardian, spouse, agency or court approvals relevant? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.consent_declaration` | Adoption or family-law consent declaration | `open` |
| `doc.court_reference` | Family-court reference and delivery evidence | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.capacity_and_warning` | Capacity and warning review completed | `open` |
| `gate.court_delivery` | Court delivery package ready | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
