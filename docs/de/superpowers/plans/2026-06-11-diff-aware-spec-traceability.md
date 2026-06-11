# Diff-aware Spec-Traceability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Neue oder fachlich geänderte Spec-Dateien müssen einen gültigen `nac-spec-traceability`-Block enthalten, während unveränderte historische Specs nicht blockieren.

**Architecture:** Der bestehende Validator `scripts/validate_spec_traceability.py` bleibt die einzige Prüfoberfläche. Er ergänzt die vorhandene Manifestvalidierung um eine Diff-Ermittlung nach bestehendem Repo-Muster: `GITHUB_BASE_REF` gegen `origin/<base>...HEAD`, sonst lokaler `git diff HEAD` plus ungetrackte Dateien.

**Tech Stack:** Python Standardbibliothek, `unittest`, bestehendes NaC Quality Gate.

---

### Task 1: Diff-Ermittlung testgetrieben ergänzen

**Files:**
- Modify: `scripts/validate_spec_traceability.py`
- Test: `tests/test_spec_traceability.py`

- [ ] **Step 1: Write the failing test**

Add tests that create a temporary git repository, set `validate_spec_traceability.REPO_ROOT` to that repository and assert that changed tracked files and untracked files are returned as repository-relative paths.

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_spec_traceability`

Expected: failure because the validator has no changed-file helper.

- [ ] **Step 3: Write minimal implementation**

Add `run_git()` and `changed_files()` to `scripts/validate_spec_traceability.py`, following the same command pattern used by other governance validators.

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_spec_traceability`

Expected: pass.

### Task 2: Manifestpflicht für neue/geänderte Specs erzwingen

**Files:**
- Modify: `scripts/validate_spec_traceability.py`
- Test: `tests/test_spec_traceability.py`

- [ ] **Step 1: Write failing tests**

Add tests for:
- a new spec under `docs/de/superpowers/specs/` without manifest failing;
- an unchanged historical spec without manifest passing;
- a non-spec Markdown change not triggering the manifest requirement.

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_spec_traceability`

Expected: failure because changed specs without manifest are not enforced yet.

- [ ] **Step 3: Write minimal implementation**

Add `validate_changed_spec_manifests()` and call it from `main()` after existing manifest validation. The function must only inspect changed files under `SPEC_ROOTS` with suffix `.md`.

- [ ] **Step 4: Run tests**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_spec_traceability`

Expected: pass.

### Task 3: Quality Gate und PR abschliessen

**Files:**
- Modify: `scripts/validate_spec_traceability.py`
- Modify: `tests/test_spec_traceability.py`
- Create: `docs/de/superpowers/plans/2026-06-11-diff-aware-spec-traceability.md`
- Create: `docs/en/superpowers/plans/2026-06-11-diff-aware-spec-traceability.md`

- [ ] **Step 1: Run focused validator tests**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_spec_traceability`

- [ ] **Step 2: Run strict quality gate**

Run: `/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict`

- [ ] **Step 3: Commit, push and open PR**

Commit message: `feat: enforce diff-aware spec traceability`

Open a protected PR linking `notariat8/NaC#90`.
