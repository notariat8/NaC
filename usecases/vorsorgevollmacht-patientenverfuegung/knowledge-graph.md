# Vorsorgevollmacht und Patientenverfuegung Knowledge Graph

Status: case-local static KG baseline  
Last update: 2026-05-15  
Catalog group: `top10`  
Usecase: [README.md](README.md)  
Machine-readable KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG node: `case.vorsorgevollmacht_patientenverfuegung`

## Operating Model

This file is the human review view for the case-local static KG. The JSON
file next to it is the machine-readable workflow state. Workflows may update
status and evidence references through reviewed Git changes, but real mandate
values must stay outside the repository.

## Open Information Nodes

| ID | Label | Status | Owner | Open question |
| --- | --- | --- | --- | --- |
| `principal.identity` | Principal identity and capacity | `open` | `notary` | Who grants the power and how is capacity reviewed? |
| `agent.identities` | Agents and substitutes | `open` | `principal` | Who should act as agent, substitute or joint agent? |
| `authority.financial` | Financial and asset authority scope | `open` | `principal` | Which financial, banking, property and business powers are intended? |
| `authority.health` | Health, residence and care authority scope | `open` | `principal` | Which health, residence, care, communication and authority powers are intended? |
| `patient.directive` | Patient directive decisions | `open` | `principal` | Which treatment situations and medical wishes should be documented? |
| `effectiveness.rules` | Effectiveness, revocation and copies | `open` | `notary` | When should the power be usable, how is revocation handled and who receives copies? |
| `self_dealing.release` | Self-dealing and sub-delegation rules | `open` | `notary` | Should self-dealing, sub-delegation or substitute powers be permitted? |
| `central_register` | Central register registration | `open` | `notary_clerk` | Should a registration instruction be prepared for the central precautionary register? |

## Documents

| ID | Label | Status |
| --- | --- | --- |
| `doc.power_of_attorney_draft` | Precautionary power of attorney draft | `open` |
| `doc.patient_directive_draft` | Patient directive draft or attachment | `open` |

## Review Gates

| ID | Label | Status |
| --- | --- | --- |
| `gate.capacity_review` | Capacity and free will reviewed | `open` |
| `gate.health_scope_review` | Health-care and patient-directive wording reviewed | `open` |

## Privacy Rule

All `value` fields remain empty in Git. The KG stores workflow state, open
questions and evidence references only; it does not store real mandate data,
secrets or personal data.
