# Grundschuld / Hypothekenbestellung Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `top10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.grundschuld_hypothek`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `property.identity` | Charged property identity | `open` | `notary_clerk` | Which property or unit is to be charged and which land register excerpt is current? |
| `owner.identity` | Owner and representation | `open` | `notary_clerk` | Who grants the charge and does the signer have authority? |
| `debtor.identity` | Personal debtor and borrower relation | `open` | `notary` | Who is the borrower or personal debtor and is this identical with the owner? |
| `lender.identity` | Creditor bank and contact route | `open` | `notary_clerk` | Which bank is creditor and which reviewed instruction channel applies? |
| `charge.amount` | Amount, currency, interest and ancillary charges | `open` | `notary_clerk` | What amount, currency, annual interest and ancillary performance are requested? |
| `security.purpose` | Security purpose and underlying transaction | `open` | `notary` | Which financing or refinancing context explains the security purpose? |
| `ranking.requirement` | Rank, prior rights and deletion consents | `open` | `notary_clerk` | Which rank is required and do prior rights or deletion consents affect the application? |
| `enforcement.clause` | Submission to immediate enforcement | `open` | `notary` | Is submission to immediate enforcement requested against property, personal assets, or both? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.bank_instruction` | Bank land charge order | `open` |
| `doc.land_register_excerpt` | Land register excerpt | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.bank_instruction_review` | Bank instruction matched to draft | `open` |
| `gate.rank_review` | Rank and prior-rights review completed | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
