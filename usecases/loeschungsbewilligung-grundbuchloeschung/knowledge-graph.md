# Loeschungsbewilligung / Grundbuchloeschung Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `next10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.loeschungsbewilligung_grundbuchloeschung`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `property.identity` | Property and register identity | `open` | `notary_clerk` | Which land register district, sheet, section and entry are affected? |
| `right.identity` | Right to be deleted | `open` | `notary_clerk` | Which land charge, mortgage, easement, restriction or other right should be deleted? |
| `creditor.authorization` | Creditor or beneficiary authorization | `open` | `notary` | Who is the current beneficiary and how is authorization to consent to deletion proven? |
| `owner.consent` | Owner consent and representation | `open` | `notary_clerk` | Is owner consent required and who may sign for the owner? |
| `brief.status` | Brief or book right status | `open` | `notary_clerk` | Is the right certificated by a letter, and if so where is the letter or replacement evidence? |
| `filing.route` | Filing route and post-deletion notification | `open` | `notary_clerk` | Which notary filing route, portal and completion notification should be used? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.deletion_consent` | Deletion authorization or consent | `open` |
| `doc.land_register_excerpt` | Current land register excerpt | `open` |
| `doc.right_letter` | Land-charge, mortgage or replacement letter evidence if required | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.authority_review` | Beneficiary authorization reviewed | `open` |
| `gate.filing_ready` | Deletion filing package ready | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
