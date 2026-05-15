# Teilungserklaerung nach WEG Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `next10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.teilungserklaerung_weg`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `property.identity` | Base property identity | `open` | `notary_clerk` | Which land register sheet and cadastral object will be divided? |
| `owner.identity` | Owner and authority | `open` | `notary` | Who owns the property and is the owner authorized to divide? |
| `unit.structure` | Unit structure and allocation | `open` | `client` | Which apartment, partial ownership, rooms and special-use rights are planned? |
| `ownership.shares` | Co-ownership shares | `open` | `client` | Which co-ownership fractions are assigned to each unit? |
| `plans.certificates` | Plans and separation certificate | `open` | `client` | Are plans, numbering, completion state and authority certificate available? |
| `encumbrance.handling` | Existing encumbrance allocation | `open` | `notary` | How do existing rights, land charges, easements or restrictions affect the future unit registers? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.division_declaration` | Declaration of division and community rules | `open` |
| `doc.plans_certificate` | Plans and separation certificate reference | `open` |
| `doc.land_register_excerpt` | Current land register excerpt | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.plan_certificate_review` | Plans and certificate reviewed | `open` |
| `gate.land_register_implementation` | Unit-register implementation package ready | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
