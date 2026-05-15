# Erbausschlagung Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `next10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.erbausschlagung`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `decedent.identity` | Decedent and estate court | `open` | `applicant` | Who died and which estate court receives the declaration? |
| `renouncer.identity` | Renouncer identity and capacity | `open` | `notary` | Who renounces and how are identity and capacity verified? |
| `deadline.status` | Deadline and knowledge date | `open` | `notary` | When did the renouncer learn of the inheritance and is the deadline still open? |
| `heirship.basis` | Inheritance basis and relationship | `open` | `applicant` | Why is the renouncer called as heir or substitute heir? |
| `representation.minors` | Minor, guardian or representative flags | `open` | `notary` | Are minors, guardians, parental representation or approvals involved? |
| `delivery.route` | Estate-court delivery route | `open` | `notary_clerk` | How and when will the declaration reach the competent court? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.renunciation_declaration` | Inheritance renunciation declaration | `open` |
| `doc.death_or_court_reference` | Death or estate court reference | `open` |
| `doc.approval_evidence` | Family or guardianship approval evidence if required | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.deadline_review` | Deadline reviewed | `open` |
| `gate.court_delivery` | Court delivery completed | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
