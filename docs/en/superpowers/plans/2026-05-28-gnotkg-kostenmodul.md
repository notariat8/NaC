# GNotKG Cost Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one central, tested GNotKG cost module with usecase gates and an `xyflow`-ready review view.

**Architecture:** The Python engine calculates deterministically. Usecase KGs store only gate and review structure. `xyflow` later renders the graph contract, not the source of truth.

**Tech Stack:** Python standard library, `unittest`, existing NaC CLI, usecase-local JSON KGs.

---

### Task 1: Build The Cost Core With Tests

**Files:**
- Create: `src/nac_gnotkg/__init__.py`
- Create: `src/nac_gnotkg/costs.py`
- Test: `tests/test_gnotkg_costs.py`

- [ ] Test table A/B against known values from GNotKG section 34 and annex 2.
- [ ] Implement `Decimal` based value fees.
- [ ] Test fee rates, minimum fee and JSON output.

### Task 2: Build The Cost Review Graph

**Files:**
- Create: `src/nac_gnotkg/views.py`
- Modify: `src/notary_kg/cli.py`
- Modify: `src/nac_cli/cli.py`
- Test: `tests/test_notary_kg.py`
- Test: `tests/test_nac_cli.py`

- [ ] Test `build_cost_review_view(repo_root, "immobilienkaufvertrag")`.
- [ ] Implement mandate-data-free nodes and edges.
- [ ] Add `nac kg cost-view <slug>`.
- [ ] Add `nac gnotkg quote`.

### Task 3: Add Usecase KGs And Governance Rule

**Files:**
- Modify: `usecases/*/knowledge-graph.graph.json`
- Modify: `usecases/*/knowledge-graph.md`
- Modify: `scripts/validate_knowledge_graph.py`
- Test: `tests/test_notary_kg.py`

- [ ] Add cost information, decision, gate and evidence to every usecase.
- [ ] Enforce those nodes in the KG validator.
- [ ] Keep all `value` fields empty.

### Task 4: Add Contracts And Documentation

**Files:**
- Create: `workflows/contracts/gnotkg-cost-review.contract.json`
- Modify: `workflows/contracts/README.md`
- Modify: `docs/de/cli.md`
- Modify: `docs/en/cli.md`
- Modify: `docs/de/kg-editor-workstream.md`
- Modify: `docs/en/kg-editor-workstream.md`

- [ ] Document engine, CLI and review boundary.
- [ ] Describe `xyflow` as rendering layer above the contract.
- [ ] Link GNotKG sources as official sources.

### Task 5: Verify And Open PR

**Files:**
- Modify only if checks require it.

- [ ] `git diff --check`
- [ ] `env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests -p "test_*.py"`
- [ ] `/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict`
- [ ] Push branch and open protected PR.
