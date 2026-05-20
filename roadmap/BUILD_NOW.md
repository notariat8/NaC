# NaC Build Now

Status: active development
Last update: 2026-05-15
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
| DEV-0006 | Workflow contract generator from KG | Next | Generates a draft contract skeleton for one case without real mandate data. |
| DEV-0007 | First pilot workflow: GmbH/UG formation | Next | Reads KG node and creates deterministic intake checklist. |
| DEV-0008 | First plugin-bound workflow: XNP reader prompt gate | Next | Consumes `nac-bnotk-xnp` readiness evidence. |
| DEV-0009 | Developer CI comment renderer | Next | Shows build status and KG readiness in PR comments. |

## Local Developer Commands

```bash
python scripts/quality_gate.py --profile strict
python scripts/validate_kg_editor.py
python scripts/validate_knowledge_graph.py
python scripts/notary_kg.py --repo-root . --format json status
python scripts/notary_kg.py --repo-root . --format json editor-view immobilienkaufvertrag
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
