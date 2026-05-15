# Steuer-aaS Tax Readiness Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `active-intake`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.steuer_aas`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `tax.subject` | Tax subject | `open` | `tax_clerk` | Which entity or person is in scope, without committing real identifiers? |
| `tax.type` | Tax process type | `open` | `tax_clerk` | Which tax process, notification, filing or readiness check is needed? |
| `period.scope` | Period and deadline scope | `open` | `tax_clerk` | Which period, statutory deadline and internal review deadline apply? |
| `elster.identity` | ELSTER identity route | `open` | `system_betreuer` | Which local ELSTER/ERIC identity route is available and approved? |
| `documents.package` | Document package | `open` | `tax_clerk` | Which synthetic or metadata-only document references are required? |
| `audit.evidence` | Audit evidence route | `open` | `compliance` | Where is reviewed evidence stored without raw tax data in Git? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.intake_package` | Reviewed intake package | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.identity` | Identity, authority and data minimization reviewed | `open` |
| `gate.notarial_review` | Human notarial review completed | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
