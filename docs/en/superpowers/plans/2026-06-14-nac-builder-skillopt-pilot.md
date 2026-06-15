# NaC Builder SkillOpt Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small, locally verifiable SkillOpt-light harness that evaluates NaC builder and review instructions against synthetic benchmark cases.

**Architecture:** The pilot stays repository-local and deterministic: a JSON contract defines guardrails, a benchmark manifest describes synthetic tasks for `nac_docs_parity_reviewer`, a Python module loads and scores runs, and a validator connects the harness to `nac contracts validate` and the strict Quality Gate. There is no model-call optimizer, no auto-merge and no processing of real mandate data.

**Tech Stack:** Python standard library, `unittest`, JSON contracts, JSONL evidence, existing `nac` CLI, existing NaC validator and Quality Gate structure.

---

## Architecture Matrix

| Spec Point | Implementation |
| --- | --- |
| AC-001: NaC creation and NaC review only | `workflows/contracts/nac-builder-skillopt.contract.json` sets `operating_scope` and forbids productive operation. |
| AC-002: First target profile `nac_docs_parity_reviewer` | Contract, benchmark and runtime accept only this target profile in the first slice. |
| AC-003: Only synthetic or repository-allowed data | Validator scans benchmark, run artifacts and rejected-edit log for prohibited markers. |
| AC-004: Accepted edits need holdout, Git diff and human review | Scoring decision requires `holdout_rationale`, `git_diff_required=true`, `human_review_required=true`. |
| AC-005: Rejected edits stay traceable | `workflows/skillopt/rejected-edits.jsonl` is introduced as an initially empty, validated JSONL evidence target. |
| AC-006: No productive writes, no real mandate data, no automatic approval | Contract, runtime and validator enforce guardrails; CLI is read-only. |
| AC-007: Manual SkillOpt-light harness, no full optimizer | No LLM call, no automatic skill-file change, only benchmark, score and review artifacts. |

## File Structure

- Create `workflows/contracts/nac-builder-skillopt.contract.json`: machine-readable contract for scope, target profile, data classes, edit gates and acceptance rules.
- Create `workflows/skillopt/README.md`: German operating boundary and artifact overview for the pilot.
- Create `workflows/skillopt/nac-docs-parity-benchmark.json`: initial benchmark with 15 synthetic tasks, train/holdout split and expected findings.
- Create `workflows/skillopt/rejected-edits.jsonl`: empty JSONL evidence target for rejected skill-edit proposals.
- Create `src/nac_skillopt/__init__.py`: module marker and public exports.
- Create `src/nac_skillopt/benchmark.py`: loads contract and benchmark, validates basic structure and creates status payloads.
- Create `src/nac_skillopt/scoring.py`: scores baseline/candidate runs and decides accept, reject or needs review.
- Create `scripts/validate_nac_builder_skillopt.py`: deterministic validator for contract, benchmark, JSONL evidence and guardrails.
- Modify `scripts/quality_gate.py`: strict profile runs the new validator.
- Modify `src/nac_cli/cli.py`: adds `nac skillopt status` and `nac skillopt score` as a read-only interface.
- Modify `workflows/contracts/README.md`: links the new contract.
- Modify `workflows/GANTT.md`: documents the pilot as an active workflow-harness slice.
- Modify `docs/de/codex-parallel-review-workflow.md` and `docs/en/codex-parallel-review-workflow.md`: describe SkillOpt-light as a development harness, not a productive path.
- Create `tests/test_nac_builder_skillopt.py`: unit tests for contract, benchmark, runtime, scoring, validator and guardrails.
- Modify `tests/test_nac_cli.py`: CLI coverage for `nac skillopt status` and `nac skillopt score`.

---

### Task 1: Manifest Contract And Benchmark

**Files:**
- Create: `workflows/contracts/nac-builder-skillopt.contract.json`
- Create: `workflows/skillopt/README.md`
- Create: `workflows/skillopt/nac-docs-parity-benchmark.json`
- Create: `workflows/skillopt/rejected-edits.jsonl`
- Test: `tests/test_nac_builder_skillopt.py`

- [ ] **Step 1: Write failing contract and benchmark tests**

Create `tests/test_nac_builder_skillopt.py` with these initial tests:

```python
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "nac-builder-skillopt.contract.json"
BENCHMARK_PATH = REPO_ROOT / "workflows" / "skillopt" / "nac-docs-parity-benchmark.json"
REJECTED_EDITS_PATH = REPO_ROOT / "workflows" / "skillopt" / "rejected-edits.jsonl"


class NaCBuilderSkillOptTests(unittest.TestCase):
    def test_contract_limits_pilot_to_nac_building(self) -> None:
        payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], "nac.builder-skillopt/v0.1")
        self.assertEqual(payload["contract_id"], "workflow.nac_builder_skillopt")
        self.assertEqual(payload["status"], "pilot_design_ready")
        self.assertEqual(payload["target_profiles"], ["nac_docs_parity_reviewer"])
        self.assertEqual(payload["operating_scope"], "nac_creation_and_review_only")
        self.assertFalse(payload["guardrails"]["productive_write_allowed"])
        self.assertFalse(payload["guardrails"]["real_mandate_data_allowed"])
        self.assertFalse(payload["guardrails"]["automatic_skill_merge_allowed"])
        self.assertTrue(payload["guardrails"]["human_review_required"])
        self.assertTrue(payload["acceptance_gate"]["holdout_rationale_required"])
        self.assertTrue(payload["acceptance_gate"]["git_diff_required"])

    def test_benchmark_has_train_and_holdout_cases_for_docs_parity(self) -> None:
        payload = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], "nac.builder-skillopt-benchmark/v0.1")
        self.assertEqual(payload["target_profile"], "nac_docs_parity_reviewer")
        cases = payload["cases"]
        self.assertGreaterEqual(len(cases), 15)
        self.assertLessEqual(len(cases), 30)
        splits = {case["split"] for case in cases}
        self.assertEqual(splits, {"train", "holdout"})
        for case in cases:
            self.assertTrue(case["task_id"].startswith("DSP-"))
            self.assertTrue(case["expected_findings"])
            self.assertTrue(case["validation_commands"])
            self.assertEqual(case["data_boundary"], "synthetic_or_repo_allowed")

    def test_rejected_edit_log_exists_and_starts_empty(self) -> None:
        self.assertTrue(REJECTED_EDITS_PATH.exists())
        self.assertEqual(REJECTED_EDITS_PATH.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Verify RED**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt
```

Expected: FAIL with missing `workflows/contracts/nac-builder-skillopt.contract.json` or missing benchmark file.

- [ ] **Step 3: Create the contract**

Create `workflows/contracts/nac-builder-skillopt.contract.json` with the exact JSON from Task 1 Step 3 in the German plan. Keep field names and values identical.

- [ ] **Step 4: Create the workflow artifact folder and README**

Create `workflows/skillopt/README.md` with the exact German content from Task 1 Step 4 in the German plan. Workflow human text under `workflows/` is German-led.

- [ ] **Step 5: Create the 15-case benchmark**

Create `workflows/skillopt/nac-docs-parity-benchmark.json` with the exact JSON from Task 1 Step 5 in the German plan.

- [ ] **Step 6: Create the empty rejected-edit log**

Create `workflows/skillopt/rejected-edits.jsonl` as an empty file. Keep the file length at zero bytes.

- [ ] **Step 7: Verify GREEN for Task 1**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_contract_limits_pilot_to_nac_building tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_benchmark_has_train_and_holdout_cases_for_docs_parity tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_rejected_edit_log_exists_and_starts_empty
```

Expected: OK.

- [ ] **Step 8: Commit Task 1**

```bash
git add workflows/contracts/nac-builder-skillopt.contract.json workflows/skillopt/README.md workflows/skillopt/nac-docs-parity-benchmark.json workflows/skillopt/rejected-edits.jsonl tests/test_nac_builder_skillopt.py
git commit -m "feat: add NaC builder SkillOpt pilot contract"
```

---

### Task 2: Build Runtime Loader And Scoring Model

**Files:**
- Create: `src/nac_skillopt/__init__.py`
- Create: `src/nac_skillopt/benchmark.py`
- Create: `src/nac_skillopt/scoring.py`
- Modify: `tests/test_nac_builder_skillopt.py`

- [ ] **Step 1: Add failing runtime and scoring tests**

Append the exact tests from Task 2 Step 1 in the German plan to `NaCBuilderSkillOptTests`.

- [ ] **Step 2: Verify RED**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_status_payload_reports_target_profile_and_split_counts tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_score_run_counts_required_hits_and_guardrail_violations
```

Expected: FAIL because `nac_skillopt` does not exist.

- [ ] **Step 3: Create module exports**

Create `src/nac_skillopt/__init__.py` with the exact code from Task 2 Step 3 in the German plan.

- [ ] **Step 4: Implement the benchmark loader**

Create `src/nac_skillopt/benchmark.py` with the exact code from Task 2 Step 4 in the German plan.

- [ ] **Step 5: Implement scoring**

Create `src/nac_skillopt/scoring.py` with the exact code from Task 2 Step 5 in the German plan.

- [ ] **Step 6: Verify GREEN for runtime and scoring**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt
```

Expected: OK.

- [ ] **Step 7: Commit Task 2**

```bash
git add src/nac_skillopt tests/test_nac_builder_skillopt.py
git commit -m "feat: score NaC builder SkillOpt runs"
```

---

### Task 3: Build Validator And Quality-Gate Integration

**Files:**
- Create: `scripts/validate_nac_builder_skillopt.py`
- Modify: `scripts/quality_gate.py`
- Modify: `src/nac_cli/cli.py`
- Modify: `tests/test_nac_builder_skillopt.py`
- Modify: `tests/test_nac_cli.py`

- [ ] **Step 1: Add failing validator and gate tests**

Append the exact tests from Task 3 Step 1 in the German plan.

- [ ] **Step 2: Verify RED**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt tests.test_nac_cli.NaCCliTests.test_contracts_validate_secure_document_links
```

Expected: FAIL because `scripts/validate_nac_builder_skillopt.py`, the Quality-Gate check and `nac contracts validate` integration are missing.

- [ ] **Step 3: Implement the validator**

Create `scripts/validate_nac_builder_skillopt.py` with the exact code from Task 3 Step 3 in the German plan.

- [ ] **Step 4: Connect `nac contracts validate`**

In `src/nac_cli/cli.py`, add this tuple to `command_contracts` before the Spec Traceability entry:

```python
            ("NaC Builder SkillOpt", "validate_nac_builder_skillopt.py"),
```

- [ ] **Step 5: Connect the strict Quality Gate**

In `scripts/quality_gate.py`, add this strict check after `codex_parallel_review`:

```python
                (
                    "nac_builder_skillopt",
                    "NaC Builder SkillOpt-light",
                    [sys.executable, "scripts/validate_nac_builder_skillopt.py"],
                ),
```

- [ ] **Step 6: Verify GREEN for validator and gate**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt tests.test_nac_cli.NaCCliTests.test_contracts_validate_secure_document_links
```

Expected: OK.

- [ ] **Step 7: Commit Task 3**

```bash
git add scripts/validate_nac_builder_skillopt.py scripts/quality_gate.py src/nac_cli/cli.py tests/test_nac_builder_skillopt.py tests/test_nac_cli.py
git commit -m "feat: validate NaC builder SkillOpt pilot"
```

---

### Task 4: Add Read-only CLI Surface

**Files:**
- Modify: `src/nac_cli/cli.py`
- Modify: `tests/test_nac_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Append the exact tests from Task 4 Step 1 in the German plan to `NaCCliTests`.

- [ ] **Step 2: Verify RED**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_cli.NaCCliTests.test_skillopt_status_cli_returns_json tests.test_nac_cli.NaCCliTests.test_skillopt_score_cli_scores_run_json
```

Expected: FAIL because the `skillopt` subcommand is not registered.

- [ ] **Step 3: Add CLI imports**

In `src/nac_cli/cli.py`, add the imports from Task 4 Step 3 in the German plan.

- [ ] **Step 4: Add parser block**

In `build_parser()`, add the parser block from Task 4 Step 4 in the German plan before the `tenant` parser.

- [ ] **Step 5: Add command function**

Add the `command_skillopt(...)` function from Task 4 Step 5 in the German plan after `command_legal_graph(...)`.

- [ ] **Step 6: Verify GREEN for CLI**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_cli.NaCCliTests.test_skillopt_status_cli_returns_json tests.test_nac_cli.NaCCliTests.test_skillopt_score_cli_scores_run_json
```

Expected: OK.

- [ ] **Step 7: Commit Task 4**

```bash
git add src/nac_cli/cli.py tests/test_nac_cli.py
git commit -m "feat: expose NaC builder SkillOpt status"
```

---

### Task 5: Maintain Docs, Contract Index And Workflow Gantt

**Files:**
- Modify: `workflows/contracts/README.md`
- Modify: `workflows/GANTT.md`
- Modify: `docs/de/codex-parallel-review-workflow.md`
- Modify: `docs/en/codex-parallel-review-workflow.md`

- [ ] **Step 1: Add failing documentation test**

Append the exact documentation test from Task 5 Step 1 in the German plan.

- [ ] **Step 2: Verify RED**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_docs_surface_mentions_skillopt_as_development_harness_only
```

Expected: FAIL because the documentation surfaces do not mention the new harness yet.

- [ ] **Step 3: Update contract index**

Add the exact contract-index bullet from Task 5 Step 3 in the German plan.

- [ ] **Step 4: Update workflow Gantt**

Apply the exact `workflows/GANTT.md` changes from Task 5 Step 4 in the German plan.

- [ ] **Step 5: Update German Codex Parallel Review docs**

Add the exact German section from Task 5 Step 5.

- [ ] **Step 6: Update English Codex Parallel Review docs**

Add the exact English section from Task 5 Step 6.

- [ ] **Step 7: Verify documentation checks**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_docs_surface_mentions_skillopt_as_development_harness_only
/home/ubuntu/.venvs/nac/bin/python scripts/validate_language_parity.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_doc_links.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_gantt_progress.py
```

Expected: all commands pass.

- [ ] **Step 8: Commit Task 5**

```bash
git add workflows/contracts/README.md workflows/GANTT.md docs/de/codex-parallel-review-workflow.md docs/en/codex-parallel-review-workflow.md tests/test_nac_builder_skillopt.py
git commit -m "docs: document NaC builder SkillOpt pilot"
```

---

### Task 6: Full Validation And Completion

**Files:**
- All files touched above.

- [ ] **Step 1: Run focused tests**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt tests.test_nac_cli
```

Expected: OK.

- [ ] **Step 2: Run contract and documentation validators**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/validate_nac_builder_skillopt.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_codex_parallel_review.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_language_parity.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_doc_links.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_gantt_progress.py
```

Expected: all commands print `STATUS: PASSED` or their existing success line.

- [ ] **Step 3: Run strict Quality Gate**

Run:

```bash
env GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: `STATUS: PASSED`.

- [ ] **Step 4: Check worktree**

Run:

```bash
git status --short
```

Expected: no unstaged changes after the final commit.

- [ ] **Step 5: Create final commit if changes remain after Task 5**

```bash
git add .
git commit -m "feat: add NaC builder SkillOpt light harness"
```

Skip this commit only when `git status --short` is already clean.

## Self-Review Mapping

- AC-001 is covered by Task 1 contract fields and Task 3 validator.
- AC-002 is covered by Task 1 target profile tests and Task 2 status payload.
- AC-003 is covered by Task 1 benchmark boundaries and Task 3 prohibited-marker validation.
- AC-004 is covered by Task 2 comparison output and Task 3 contract validation.
- AC-005 is covered by Task 1 `rejected-edits.jsonl` and Task 3 JSONL validation.
- AC-006 is covered by Task 1 guardrails, Task 3 validator and Task 4 read-only CLI.
- AC-007 is covered by the absence of optimizer/model-call tasks and by the Task 5 documentation boundary.
