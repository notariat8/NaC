# Testament / Erbvertrag Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `top10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.testament_erbvertrag`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `testator.identity` | Testator identities | `open` | `notary` | Who makes the disposition and how are identity and capacity reviewed? |
| `capacity.flags` | Capacity and communication flags | `open` | `notary` | Are there capacity, language, hearing, sight, illness or support flags? |
| `family.structure` | Family and heirship situation | `open` | `testator` | Which spouse, children, relatives, prior marriages or relevant dependents exist? |
| `assets.categories` | Estate asset categories | `open` | `testator` | Which relevant asset categories exist without storing detailed values in Git? |
| `dispositions.wishes` | Desired dispositions | `open` | `testator` | Who should inherit, receive legacies, be executor or be subject to conditions? |
| `prior.dispositions` | Prior wills, inheritance contracts and revocation needs | `open` | `notary` | Do earlier dispositions exist and are they revocable or binding? |
| `executor.choice` | Executor and substitute arrangements | `open` | `testator` | Should an executor, substitute heirs, guardianship wishes or administration rules be included? |
| `custody.register` | Custody and central register route | `open` | `notary_clerk` | Which custody and registration steps are required after execution? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.disposition_draft` | Draft testament or inheritance contract | `open` |
| `doc.prior_dispositions` | Prior dispositions evidence reference | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.capacity_review` | Capacity and free will reviewed by notary | `open` |
| `gate.binding_effect_review` | Binding effects and revocations reviewed | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
