# Gesellschafterbeschluss bei GmbH/UG Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `next10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.gesellschafterbeschluss_gmbh_ug`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `company.identity` | Company and register identity | `open` | `notary_clerk` | Which GmbH/UG, register court and register number are affected? |
| `resolution.type` | Resolution type and legal basis | `open` | `notary` | Is this an articles amendment, capital measure, appointment, consent or other resolution? |
| `shareholders.present` | Shareholders, votes and representation | `open` | `notary_clerk` | Who participates, which votes exist and which representatives act? |
| `majority.requirement` | Majority and consent requirements | `open` | `notary` | Which statutory and articles-based majority or unanimity requirements apply? |
| `articles.wording` | Current and amended articles wording | `open` | `notary` | Which current article text is changed and what new wording is proposed? |
| `register.filing` | Register filing and notarized certificate route | `open` | `notary_clerk` | Which register application, notary certificate and XNP route are required? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.resolution_minutes` | Shareholder resolution minutes | `open` |
| `doc.current_articles` | Current articles and amended wording | `open` |
| `doc.register_application` | Commercial-register application and certificate | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.quorum_majority_review` | Quorum, votes and majority reviewed | `open` |
| `gate.register_package_ready` | Register package ready | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
