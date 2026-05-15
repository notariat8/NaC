# Beglaubigung von Unterschriften Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `top10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.unterschriftsbeglaubigung`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `signer.identity` | Signer identity | `open` | `notary_clerk` | Who signs and how is identity established? |
| `document.purpose` | Document purpose and recipient | `open` | `notary_clerk` | What is the document used for and who receives it? |
| `signature.mode` | Signature already made or made before notary | `open` | `notary` | Is the signature acknowledged or executed in front of the notary? |
| `language.understanding` | Language and understanding flags | `open` | `notary` | Can the signer understand the relevant language or is translation/support needed? |
| `representation.context` | Representation or company role | `open` | `notary_clerk` | Does the signer act personally, as representative, organ, guardian or agent? |
| `copies.routing` | Copies, electronic certificate and routing | `open` | `notary_clerk` | Which copies, electronic witnesses or delivery routes are required? |
| `special.form` | Special form or legalization need | `open` | `notary` | Is apostille, legalization, register-specific form or foreign use involved? |
| `fee.metadata` | Fee value and billing metadata | `open` | `notary_clerk` | Which value or fee metadata is needed for billing? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.signed_document` | Document with signature to certify | `open` |
| `doc.certification_note` | Certification note or electronic witness | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.identity_and_signature` | Identity and signature act reviewed | `open` |
| `gate.form_route` | Correct form and route selected | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
