# Schenkungsvertrag / Uebertragungsvertrag Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `top10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.schenkungsvertrag_uebertragung`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `transferor.identity` | Transferor identity and capacity | `open` | `notary_clerk` | Who transfers and are identity, capacity and ownership verified? |
| `transferee.identity` | Transferee identity and family relation | `open` | `notary_clerk` | Who receives and what family or tax relationship is relevant? |
| `asset.identity` | Transferred asset or property | `open` | `notary_clerk` | Which property, share, business interest or other asset is transferred? |
| `reserved.rights` | Reserved rights | `open` | `notary` | Are usufruct, residential rights, maintenance, care obligations or usage rights reserved? |
| `reversion.rights` | Reversion, revocation and securing rights | `open` | `notary` | Which retransfer events, revocation grounds or notices should be secured? |
| `consideration.obligations` | Consideration and obligations | `open` | `notary` | Is the transfer gratuitous, mixed, subject to debts, care or equalization payments? |
| `consents.approvals` | Consents and approvals | `open` | `notary_clerk` | Are spouse, court, guardian, administrator, bank, co-owner or public approvals required? |
| `tax.family.flags` | Tax, succession and mandatory-share flags | `open` | `notary` | Which gift tax, succession, care, equalization or mandatory-share clarification flags apply? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.transfer_draft` | Transfer agreement draft | `open` |
| `doc.land_register_excerpt` | Land register excerpt if real estate is involved | `open` |
| `doc.approvals` | Approval and consent evidence | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.asset_review` | Asset and ownership reviewed | `open` |
| `gate.family_tax_review` | Family, tax and succession flags reviewed | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
