# GmbH-Gruendung / UG-Gruendung Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `top10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.online_gmbh_gruendung`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `company.name` | Company name and legal form | `open` | `notary_clerk` | Which company name and legal form are intended and are name risks known? |
| `company.seat` | Registered seat and domestic business address | `open` | `founder` | Where are seat and business address located? |
| `company.object` | Business object | `open` | `founder` | What business object should be registered and are permits relevant? |
| `founders.identity` | Founder identities and share allocation | `open` | `notary_clerk` | Who are the founders and which nominal shares do they take? |
| `capital.structure` | Share capital, nominal shares and contribution type | `open` | `notary` | What capital is subscribed and are cash or in-kind contributions planned? |
| `management.appointment` | Managing directors and representation | `open` | `notary_clerk` | Who is appointed managing director and what representation rule applies? |
| `register.route` | Online or in-office register filing route | `open` | `notary_clerk` | Which XNP, card, signature and Handelsregister route is used? |
| `beneficial.owner.flags` | Beneficial-owner and AML flags | `open` | `notary` | Which beneficial-owner, sanctions, PEP or AML clarification flags must be reviewed? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.articles` | Articles or model protocol draft | `open` |
| `doc.shareholder_list` | Initial shareholder list | `open` |
| `doc.register_application` | Commercial register application | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.card_xnp_readiness` | Card, XNP and signature route checked | `open` |
| `gate.register_filing_ready` | Register application reviewed and ready | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
