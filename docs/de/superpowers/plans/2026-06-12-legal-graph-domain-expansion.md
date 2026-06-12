# Legal Graph Domain Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Familienrecht und Gesellschaftsrecht als mandatsdatenfreie Legal-Graph-Domänen ergänzen und die Kommentar-Connector-Vertragsprüfung vertiefen.

**Architecture:** Die bestehende `nac_legal_graph`-Loader- und Patch-Schicht bleibt generisch. Neue Domänen werden als `workflows/legal-graph/domains/*.graph.json` plus optionale Update-Fixtures ergänzt. Der bestehende Validator prüft alle Domänen und Fixtures, während der Kommentar-Connector-Vertrag strengere Provider-, Evidence- und Aktivierungsregeln erhält.

**Tech Stack:** Python `unittest`, JSON-Artefakte, `nac` CLI, bestehender Strict Quality Gate.

---

### Task 1: Multi-Domain Tests

**Files:**
- Modify: `tests/test_legal_graph.py`
- Modify: `tests/test_legal_graph_contracts.py`
- Modify: `tests/test_nac_cli.py`

- [ ] **Step 1: Write failing tests**

Tests verlangen drei Domänen (`erbrecht`, `familienrecht`, `gesellschaftsrecht`), stabile Knoten wie `usecase.ehevertrag` und `usecase.gmbh-gruendung`, und `nac legal-graph status --format json` mit drei Domain-Einträgen.

- [ ] **Step 2: Run tests and verify red**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_legal_graph tests.test_legal_graph_contracts tests.test_nac_cli
```

Expected: failure because the two new graph files and contract domain entries do not exist.

### Task 2: Add Family And Corporate Graphs

**Files:**
- Create: `workflows/legal-graph/domains/familienrecht.graph.json`
- Create: `workflows/legal-graph/domains/gesellschaftsrecht.graph.json`
- Modify: `workflows/contracts/legal-graph.contract.json`

- [ ] **Step 1: Add metadata-only domain graphs**

Each graph includes primary-source placeholders, relevant norm nodes, notarial usecase nodes, review points, one commentary connector node, and validated edges. No `value`, credentials or commentary full text are allowed.

- [ ] **Step 2: Run tests and validator**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_legal_graph tests.test_legal_graph_contracts tests.test_nac_cli
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python scripts/nac.py contracts validate
```

Expected: all pass.

### Task 3: Deepen Commentary Connector Contract

**Files:**
- Modify: `workflows/contracts/legal-commentary-connectors.contract.json`
- Modify: `scripts/validate_legal_graph_contracts.py`
- Modify: `tests/test_legal_graph_contracts.py`

- [ ] **Step 1: Write failing policy tests**

Tests require every provider to expose `license_status`, `allowed_evidence_fields`, `activation_gate`, `permitted_outputs`, and `blocked_actions`; approved access must still disallow credentials, mandate data and full text in the product repo.

- [ ] **Step 2: Implement minimal contract and validator checks**

Extend provider entries and validate the required metadata, blocked actions and permitted-output boundaries.

- [ ] **Step 3: Run full verification**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: `STATUS: PASSED`.
