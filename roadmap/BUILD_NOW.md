# NaC Build Now

Status: active development
Last update: 2026-06-29
Branch: `main`

## What Is Being Built

NaC is now in implementation mode. The first executable development increment is
the notarial KG runtime:

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . case bautraegervertrag
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
```

The runtime reads the usecase-local static KG files, summarizes development
readiness and exposes case-level open questions, gates, documents and plugin
dependencies. The editor view renders the same KG as safe forms and checklists
for Fachpersonal without exposing `value` fields.

## Current Executable Surface

| Surface | Status | Evidence |
| --- | --- | --- |
| Case-local KG files | Implemented | `usecases/*/knowledge-graph.graph.json`, `usecases/*/knowledge-graph.md` |
| KG validator | Implemented | `scripts/validate_knowledge_graph.py` |
| KG runtime package | Implemented | `src/notary_kg/` |
| KG CLI | Implemented | `scripts/notary_kg.py`, `notary-kg` after package install |
| KG editor view | Implemented | `src/notary_kg/editor.py`, `schemas/kg-editor-patch.schema.json`, `workflows/contracts/kg-editor.contract.json` |
| Workflow contract draft generator | Implemented | `src/notary_kg/workflow_contract.py`, `nac kg workflow-contract <slug>`, `tests/test_notary_kg.py` |
| GmbH/UG pilot intake checklist | Implemented | `src/notary_kg/pilot_checklist.py`, `nac kg pilot-checklist online-gmbh-gruendung`, `tests/test_notary_kg.py` |
| Legal Graph source pilot | In review | `workflows/legal-graph/sources/erbrecht-primary-source.json`, `nac legal-graph sources` |
| Legal Graph contract validator | Implemented | `scripts/validate_legal_graph_contracts.py`, strict quality gate |
| Legal model customization gates | Implemented | `workflows/contracts/legal-research-connectors.contract.json`, `workflows/contracts/legal-model-customization-readiness.contract.json`, `workflows/contracts/legal-model-evaluation-benchmark.contract.json`, strict quality gate |
| Unit tests | Implemented | `tests/test_notary_kg.py` |
| Strict quality gate | Active | `python scripts/quality_gate.py --profile strict` |

## Sprint 0 Development Board

| ID | Work item | Status | Done means |
| --- | --- | --- | --- |
| DEV-0001 | Case-local static KGs for Top-10, Next-10 and active intake usecases | Done | Every usecase folder has one JSON graph and one review Markdown file. |
| DEV-0002 | KG validator in strict quality gate | Done | `knowledge_graph` appears in strict quality output. |
| DEV-0003 | Executable KG status CLI | Done | CLI summarizes catalogs, cases and open nodes. |
| DEV-0004 | Case-level KG CLI view | Done | CLI returns one case by slug and fails unknown slugs. |
| DEV-0005 | No-code KG editor view and patch contract | Done | CLI returns four safe editor tabs, patch actions and blocked `value` fields. |
| DEV-0006 | Workflow contract generator from KG | Done | `nac kg workflow-contract <slug>` generates a draft contract skeleton for one case without real mandate data. |
| DEV-0007 | First pilot workflow: GmbH/UG formation | Done | `nac kg pilot-checklist online-gmbh-gruendung` reads the KG node and creates a deterministic intake checklist without real mandate data. |
| DEV-0008 | First plugin-bound workflow: XNP reader prompt gate | Next | Consumes `nac-bnotk-xnp` readiness evidence. |
| DEV-0009 | Developer CI comment renderer | Next | Shows build status and KG readiness in PR comments. |
| DEV-0010 | Legal Graph primary-source pilot without commentary access | In review | `nac legal-graph sources` reports Erbrecht as metadata-only, with commentary access, provider queries and credentials blocked. |
| DEV-0011 | Legal Nemotron fine-tuning source and evaluation plan | Done | Records NVIDIA Nemotron Legal, Rechtsquelle concept framing and `recht.bund.de` BGBl data access as metadata-only candidates, adds readiness and German-law benchmark contracts, and keeps fine-tuning, checkpoint publication and legal-answer use blocked before license/TDM, source hierarchy, evaluation, model-card, AI-SBOM and owner-apply gates are approved. |

## Roadmap Review Notes

| Date | Topic | Decision | Follow-up trigger |
| --- | --- | --- | --- |
| 2026-06-16 | Fabro / Graphviz workflow orchestration | Not an active NaC roadmap item. Fabro complements the NaC BPMN line only as a possible future agentic execution and review harness; it does not replace BPMN 2.0 as the canonical subject-matter process source. | Revisit only if Codex Parallel Review, Time Ledger, Quality Gate or PR handoff work shows a repeated need for a durable external workflow engine. |
| 2026-06-28 | Legal Nemotron fine-tuning with public legal sources | Add as a gated roadmap track, not as an active training job. NVIDIA Nemotron Legal is an English CC-BY-4.0 pretraining dataset candidate, `Rechtsquelle` is a concept anchor for source hierarchy, and `recht.bund.de` is an official BGBl publication access path. | Continue only with source inventory, license/TDM review, model-card delta, AI-SBOM update, approved runnable config and owner apply approval; never use mandate data or treat generated answers as legal truth. |
| 2026-06-29 | Legal Nemotron gates after PRs 326-328 | Mark source candidates, readiness gates and German-law evaluation benchmark as implemented planning contracts. This closes the planning-board item without enabling training, dataset generation, checkpoint publication or legal-answer automation. | Next work item must be a separate gated contract or implementation PR for source inventory, model-card delta, AI-SBOM delta or approved benchmark generation. |
| 2026-06-29 | Immutable.js for editor state | Defer. Immutable.js can be reconsidered only as a future frontend/editor state tool for undo, redo, snapshots and deterministic proposal diffs; it is not an audit, governance, retention, WORM, signature or notarial truth layer. No dependency or architecture change now. | Revisit only when NaC starts a real React, BPMN-js or xyflow editor-sidecar implementation and can keep exported artifacts as canonical JSON, BPMN or XML with hash, validator, PR review and event-journal evidence. |

## Local Developer Commands

```bash
python scripts/quality_gate.py --profile strict
python scripts/validate_kg_editor.py
python scripts/validate_knowledge_graph.py
python scripts/nac.py legal-graph sources --format json
python scripts/validate_legal_model_customization_readiness.py
python scripts/validate_legal_model_evaluation_benchmark.py
python scripts/notary_kg.py --repo-root . --format json status
python scripts/notary_kg.py --repo-root . --format json editor-view immobilienkaufvertrag
python scripts/notary_kg.py --repo-root . --format json workflow-contract immobilienkaufvertrag
python scripts/notary_kg.py --repo-root . --format json pilot-checklist online-gmbh-gruendung
```

## Rule

New conceptual work must be paired with at least one of these executable
changes:

- Python runtime code
- validator or quality gate coverage
- unit tests
- workflow contract scaffold
- plugin script or schema
- CI/reporting integration
