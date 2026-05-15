# Ehevertrag / Scheidungsfolgenvereinbarung Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `top10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.ehevertrag_scheidungsfolgen`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `spouses.identity` | Spouse identities and personal status | `open` | `notary_clerk` | Who are the spouses or intended spouses and what status applies? |
| `marriage.context` | Marriage, separation or divorce context | `open` | `notary` | Is this pre-marriage, during marriage, separation, divorce pending or post-divorce? |
| `property.regime` | Property regime and equalization target | `open` | `notary` | Should statutory property regime be modified, excluded or replaced? |
| `asset.disclosure` | Asset and debt disclosure categories | `open` | `spouses` | Which asset categories, business interests, debts or pensions are relevant without committing real values? |
| `maintenance.rules` | Maintenance provisions | `open` | `notary` | Which spousal maintenance rules or waivers are intended and are fairness limits triggered? |
| `pension.equalization` | Pension equalization provisions | `open` | `notary` | Should pension equalization be modified and is court review expected? |
| `child.family.flags` | Child and family dependency flags | `open` | `notary` | Are child-care, dependency, pregnancy or imbalance flags relevant to fairness review? |
| `asset.transfer` | Asset transfers and register consequences | `open` | `notary_clerk` | Are real estate, company share, account or debt transfers part of the agreement? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.agreement_draft` | Marriage contract or divorce consequences agreement draft | `open` |
| `doc.asset_schedule_reference` | Asset schedule evidence reference | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.fairness_review` | Fairness and imbalance review completed by notary | `open` |
| `gate.simultaneous_presence` | Simultaneous personal presence route checked | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
