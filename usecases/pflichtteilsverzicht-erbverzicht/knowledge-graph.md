# Pflichtteilsverzicht / Erbverzicht Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `next10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.pflichtteilsverzicht_erbverzicht`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `future_decedent.identity` | Future decedent identity and capacity | `open` | `notary` | Who contracts with the waiving party and how is capacity reviewed? |
| `waiver_party.identity` | Waiving party identity | `open` | `notary` | Who waives and are representation or approval issues present? |
| `waiver.scope` | Waiver scope | `open` | `notary` | Is the waiver full inheritance waiver, compulsory-share waiver or limited arrangement? |
| `descendant.effect` | Effect on descendants | `open` | `notary` | Should or does the waiver extend to descendants? |
| `compensation.model` | Compensation or settlement | `open` | `client` | Is compensation, settlement, transfer or no consideration intended? |
| `family.fairness_flags` | Family and fairness flags | `open` | `notary` | Are pressure, dependency, minors, care or imbalance flags present? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.waiver_contract` | Inheritance or compulsory-share waiver contract | `open` |
| `doc.compensation_evidence` | Compensation or settlement evidence reference | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.personal_presence_review` | Required personal participation reviewed | `open` |
| `gate.fairness_review` | Family and fairness review completed | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
