# Vollmacht fuer Immobilien- oder Gesellschaftsgeschaefte Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `next10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.vollmacht_immobilien_gesellschaft`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `principal.identity` | Principal identity and capacity | `open` | `notary` | Who grants the power and how are identity and capacity verified? |
| `agent.identity` | Agent identity and relation | `open` | `principal` | Who is authorized and what relationship or conflict flags exist? |
| `transaction.scope` | Transaction scope | `open` | `notary` | Which real-estate, register, shareholder or share-transfer acts are covered? |
| `form.requirement` | Required form | `open` | `notary` | Is public certification enough or is notarial recording required for the intended transaction? |
| `limitations.expiry` | Limitations, substitution and expiry | `open` | `notary` | Which restrictions, self-dealing release, sub-authorization, duration or revocation rules apply? |
| `delivery.evidence` | Original, copies and recipient route | `open` | `notary_clerk` | Who receives originals or certified copies and how is use evidenced? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.power_of_attorney` | Power of attorney deed or certification | `open` |
| `doc.scope_reference` | Transaction or register scope reference | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.form_review` | Form and scope reviewed | `open` |
| `gate.delivery_control` | Original and copy handling controlled | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
