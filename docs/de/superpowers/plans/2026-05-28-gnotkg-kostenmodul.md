# GNotKG-Kostenmodul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein zentrales, getestetes GNotKG-Kostenmodul mit Usecase-Gate und `xyflow`-fähiger Reviewansicht bauen.

**Architecture:** Die Python-Engine berechnet deterministisch. Usecase-KGs speichern nur Gate- und Reviewstruktur. `xyflow` rendert später den Graph-Vertrag, nicht die fachliche Wahrheit.

**Tech Stack:** Python Standard Library, `unittest`, bestehende NaC-CLI, usecase-lokale JSON-KGs.

---

### Task 1: Kostenkern testgetrieben bauen

**Files:**
- Create: `src/nac_gnotkg/__init__.py`
- Create: `src/nac_gnotkg/costs.py`
- Test: `tests/test_gnotkg_costs.py`

- [ ] Teste Tabelle A/B mit bekannten Werten aus GNotKG § 34 und Anlage 2.
- [ ] Implementiere `Decimal`-basierte Wertgebühren.
- [ ] Teste Gebührensatz, Mindestgebühr und JSON-Ausgabe.

### Task 2: Kosten-Review-Graph bauen

**Files:**
- Create: `src/nac_gnotkg/views.py`
- Modify: `src/notary_kg/cli.py`
- Modify: `src/nac_cli/cli.py`
- Test: `tests/test_notary_kg.py`
- Test: `tests/test_nac_cli.py`

- [ ] Teste `build_cost_review_view(repo_root, "immobilienkaufvertrag")`.
- [ ] Implementiere mandatsdatenfreie Nodes/Edges.
- [ ] Ergänze `nac kg cost-view <slug>`.
- [ ] Ergänze `nac gnotkg quote`.

### Task 3: Usecase-KGs und Governance-Regel ergänzen

**Files:**
- Modify: `usecases/*/knowledge-graph.graph.json`
- Modify: `usecases/*/knowledge-graph.md`
- Modify: `scripts/validate_knowledge_graph.py`
- Test: `tests/test_notary_kg.py`

- [ ] Ergänze in jedem Usecase Kostenangabe, Entscheidung, Gate und Nachweis.
- [ ] Erzwinge diese Knoten im KG-Validator.
- [ ] Halte alle `value`-Felder leer.

### Task 4: Verträge und Dokumentation ergänzen

**Files:**
- Create: `workflows/contracts/gnotkg-cost-review.contract.json`
- Modify: `workflows/contracts/README.md`
- Modify: `docs/de/cli.md`
- Modify: `docs/en/cli.md`
- Modify: `docs/de/kg-editor-workstream.md`
- Modify: `docs/en/kg-editor-workstream.md`

- [ ] Dokumentiere Engine, CLI und Review-Grenze.
- [ ] Beschreibe `xyflow` als Rendering-Schicht über dem Vertrag.
- [ ] Verlinke GNotKG-Quellen als offizielle Quellen.

### Task 5: Verifikation und PR

**Files:**
- Modify only if checks require it.

- [ ] `git diff --check`
- [ ] `env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests -p "test_*.py"`
- [ ] `/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict`
- [ ] Push branch and open protected PR.
