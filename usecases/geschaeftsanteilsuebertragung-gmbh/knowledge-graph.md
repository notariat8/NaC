# Geschaeftsanteilsuebertragung GmbH Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `next10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.geschaeftsanteilsuebertragung_gmbh`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `company.identity` | Company and register identity | `open` | `notary_clerk` | Which GmbH and register data define the target company? |
| `share.identity` | Shares and chain of title | `open` | `notary` | Which business shares, nominal amounts and chain of title are transferred? |
| `seller.identity` | Transferor identity and authority | `open` | `notary_clerk` | Who transfers and how is authority verified? |
| `buyer.identity` | Acquirer identity and beneficial-owner flags | `open` | `notary` | Who acquires and which beneficial-owner or AML flags must be reviewed? |
| `consents.restrictions` | Consent restrictions and pre-emption rights | `open` | `notary` | Do articles, side agreements or shareholder resolutions require consent? |
| `consideration.tax` | Purchase price, gift and tax flags | `open` | `notary` | Is this a sale, gift, mixed transfer or other transaction with tax flags? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.transfer_agreement` | Notarial share transfer agreement | `open` |
| `doc.shareholder_list` | Updated shareholder list | `open` |
| `doc.consent_evidence` | Consent, waiver or resolution evidence | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.chain_of_title_review` | Share chain and restrictions reviewed | `open` |
| `gate.shareholder_list_ready` | Updated shareholder list ready | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
