# Vereinsregisteranmeldung Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `next10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.vereinsregisteranmeldung`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `association.identity` | Association and register identity | `open` | `notary_clerk` | Which e.V., register court and register number are affected? |
| `filing.type` | Filing type | `open` | `notary` | Is this board change, articles amendment, formation, dissolution or another filing? |
| `board.identity` | Board signers and authority | `open` | `notary_clerk` | Which board members must sign and what representation rule applies? |
| `resolution.evidence` | Meeting and resolution evidence | `open` | `association` | Which minutes, election records or articles amendment resolutions are needed? |
| `articles.current` | Current articles and changed wording | `open` | `association` | What is the current articles text and which changes are registered? |
| `filing.route` | Court filing route and copies | `open` | `notary_clerk` | Which paper or electronic route and copy package does the register court require? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.register_application` | Association-register application | `open` |
| `doc.minutes_resolution` | Minutes, election or resolution evidence | `open` |
| `doc.articles` | Articles or amended articles wording | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.signer_authority` | Board signer authority reviewed | `open` |
| `gate.register_package_ready` | Association-register package ready | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
