# Immobilienkaufvertrag Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `top10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.immobilienkaufvertrag`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `property.identity` | Property identity | `open` | `notary_clerk` | Which land register district, sheet, parcel, unit and current designation identify the object? |
| `seller.identity` | Seller identity and capacity | `open` | `notary_clerk` | Who sells, how is identity and capacity verified, and is representation involved? |
| `buyer.identity` | Buyer identity and acquisition structure | `open` | `notary_clerk` | Who buys, in which shares, with which address and with which representation? |
| `purchase.price` | Purchase price and maturity model | `open` | `notary` | What is the purchase price, payment route, maturity prerequisites and due date mechanism? |
| `encumbrances.current` | Current encumbrances and deletion plan | `open` | `notary_clerk` | Which rights, liens, easements or restrictions remain, are deleted or are assumed? |
| `financing.required` | Buyer financing and new land charge need | `open` | `notary_clerk` | Is financing required and must a new land charge appointment be coordinated? |
| `possession.transfer` | Possession, benefits, burdens and risk transfer | `open` | `notary` | When do possession, utilities, insurance risk, public charges and economic burdens transfer? |
| `public.approvals` | Pre-emption, tax and approval requirements | `open` | `notary_clerk` | Which municipal, tax, family, court, administrator or public approvals are required? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.land_register_excerpt` | Current land register excerpt | `open` |
| `doc.contract_draft` | Draft purchase contract with attachments | `open` |
| `doc.approvals` | Approval, pre-emption and tax-clearance evidence | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.land_register_review` | Land register reviewed by notary | `open` |
| `gate.consumer_draft_period` | Consumer draft review period checked where applicable | `open` |
| `gate.execution_readiness` | Payment maturity and filing package ready | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
