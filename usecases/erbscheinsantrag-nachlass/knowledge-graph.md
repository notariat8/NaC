# Erbscheinsantrag / Nachlassangelegenheiten Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `top10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.erbscheinsantrag_nachlass`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `decedent.identity` | Decedent identity and death metadata | `open` | `applicant` | Who died, when and where, and which evidence confirms this? |
| `residence.jurisdiction` | Last habitual residence and jurisdiction | `open` | `notary_clerk` | Which estate court has jurisdiction based on last habitual residence or other route? |
| `applicants.identity` | Applicant identities and application authority | `open` | `notary_clerk` | Who applies and in which legal position? |
| `heirship.basis` | Heirship basis | `open` | `notary` | Is heirship based on statutory succession, will, inheritance contract or European certificate context? |
| `family.evidence` | Family and civil-status evidence | `open` | `applicant` | Which birth, marriage, divorce, adoption or death evidence is required? |
| `dispositions.evidence` | Wills, inheritance contracts and opening records | `open` | `notary_clerk` | Which dispositions and opening records exist and where are they referenced? |
| `renunciations.disclaimers` | Renunciations, disclaimers and contests | `open` | `notary` | Are there renunciations, disclaimers, contests, disinheritance or mandatory-share issues? |
| `oath.statement` | Eidesstattliche Versicherung statement scope | `open` | `notary` | Which facts must be declared under oath and by whom? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.death_certificate_reference` | Death certificate or official death evidence reference | `open` |
| `doc.application_draft` | Certificate of inheritance application draft | `open` |
| `doc.family_evidence` | Civil-status evidence package | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.heirship_review` | Heirship and evidence reviewed by notary | `open` |
| `gate.oath_readiness` | Oath statement and appointment readiness checked | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
