# NoC Build Now

Status: active development  
Last update: 2026-05-15  
Branch: `codex-gantt-usecase-structure`

## What Is Being Built

NoC is now in implementation mode. The first executable development increment is
the notarial KG runtime:

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . case bautraegervertrag
```

The runtime reads the static KG catalogs, summarizes development readiness and
exposes case-level open questions, gates, documents and plugin dependencies.

## Current Executable Surface

| Surface | Status | Evidence |
| --- | --- | --- |
| KG catalogs | Implemented | `knowledge-graph/notarial-top10.graph.json`, `knowledge-graph/notarial-next10.graph.json` |
| KG validator | Implemented | `scripts/validate_knowledge_graph.py` |
| KG runtime package | Implemented | `src/notary_kg/` |
| KG CLI | Implemented | `scripts/notary_kg.py`, `notary-kg` after package install |
| Unit tests | Implemented | `tests/test_notary_kg.py` |
| Strict quality gate | Active | `python scripts/quality_gate.py --profile strict` |

## Sprint 0 Development Board

| ID | Work item | Status | Done means |
| --- | --- | --- | --- |
| DEV-0001 | Static KG catalogs for Top-10 and Next-10 | Done | JSON catalogs validate and have review Markdown. |
| DEV-0002 | KG validator in strict quality gate | Done | `knowledge_graph` appears in strict quality output. |
| DEV-0003 | Executable KG status CLI | Done | CLI summarizes catalogs, cases and open nodes. |
| DEV-0004 | Case-level KG CLI view | Done | CLI returns one case by slug and fails unknown slugs. |
| DEV-0005 | Workflow contract generator from KG | Next | Generates a draft contract skeleton for one case without real mandate data. |
| DEV-0006 | First pilot workflow: GmbH/UG formation | Next | Reads KG node and creates deterministic intake checklist. |
| DEV-0007 | First plugin-bound workflow: XNP reader prompt gate | Next | Consumes `noc-bnotk-xnp` readiness evidence. |
| DEV-0008 | Developer CI comment renderer | Next | Shows build status and KG readiness in PR comments. |

## Local Developer Commands

```bash
python scripts/quality_gate.py --profile strict
python scripts/validate_knowledge_graph.py
python scripts/notary_kg.py --repo-root . --format json status
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
