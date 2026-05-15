# Handelsregisteranmeldung Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `top10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.handelsregisteranmeldung`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `entity.identity` | Entity, register court and register number | `open` | `notary_clerk` | Which entity and register sheet are affected? |
| `event.type` | Register event type | `open` | `notary` | Which event is being registered: management, seat, capital, company name, object, prokura or other? |
| `signers.identity` | Signing persons and signing authority | `open` | `notary_clerk` | Who must sign and how is authority proven? |
| `corporate.resolution` | Corporate resolution or legal basis | `open` | `notary` | Which resolution, articles clause or external fact authorizes the application? |
| `attachments.required` | Required attachments | `open` | `notary_clerk` | Which documents must be filed in machine-readable electronic form? |
| `effective.date` | Effective date and wording | `open` | `notary` | Is the change already effective, conditional, future-dated or register-effective only? |
| `xnp.route` | XNP and signature route | `open` | `notary_clerk` | Which notary card, XNP workspace and EGVP/beN route will be used? |
| `fees.costs` | Cost and invoice metadata | `open` | `notary_clerk` | Which value or cost metadata is required for GNotKG and office billing? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.register_application` | Publicly certified electronic register application | `open` |
| `doc.corporate_evidence` | Resolution, appointment, articles or related evidence | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.public_certification` | Public certification requirements met | `open` |
| `gate.electronic_format` | Electronic machine-readable package checked | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
