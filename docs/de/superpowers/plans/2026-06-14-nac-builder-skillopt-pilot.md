# NaC Builder SkillOpt Pilot Implementierungsplan

> **Für agentische Worker:** ERFORDERLICHE SUB-SKILL: Nutze superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans, um diesen Plan Schritt für Schritt umzusetzen. Schritte nutzen Checkboxen (`- [ ]`) zur Nachverfolgung.

**Ziel:** Einen kleinen, lokal prüfbaren SkillOpt-light-Harness bauen, der NaC-Builder- und Review-Anweisungen kontrolliert gegen synthetische Benchmarkfälle bewertet.

**Architektur:** Der Pilot bleibt repo-lokal und deterministisch: Ein JSON-Vertrag definiert Guardrails, ein Benchmark-Manifest beschreibt synthetische Aufgaben für `nac_docs_parity_reviewer`, ein Python-Modul lädt und bewertet Läufe, und ein Validator hängt den Harness an `nac contracts validate` und das strikte Quality Gate. Es gibt keinen Modellaufruf-Optimizer, kein Auto-Merge und keine Verarbeitung echter Mandatsdaten.

**Tech Stack:** Python-Standardbibliothek, `unittest`, JSON-Verträge, JSONL-Nachweise, bestehende `nac`-CLI, bestehende NaC-Validator- und Quality-Gate-Struktur.

---

## Architekturmatrix

| Spezifikationspunkt | Umsetzung |
| --- | --- |
| AC-001: Nur NaC-Erstellung und NaC-Review | `workflows/contracts/nac-builder-skillopt.contract.json` setzt `operating_scope` und verbietet Produktivbetrieb. |
| AC-002: Erstes Zielprofil `nac_docs_parity_reviewer` | Vertrag, Benchmark und Runtime akzeptieren im ersten Slice nur dieses Zielprofil. |
| AC-003: Nur synthetische oder repo-zulässige Daten | Validator scannt Benchmark, Run-Artefakte und Rejected-Edit-Log auf verbotene Marker. |
| AC-004: Akzeptierte Edits brauchen Holdout, Git-Diff, Human Review | Scoring-Entscheidung verlangt `holdout_rationale`, `git_diff_required=true`, `human_review_required=true`. |
| AC-005: Verworfene Edits nachvollziehbar | `workflows/skillopt/rejected-edits.jsonl` wird als leer startendes, validiertes JSONL-Nachweisziel eingeführt. |
| AC-006: Keine produktiven Schreibaktionen, keine echten Mandatsdaten, keine automatische Freigabe | Vertrag, Runtime und Validator erzwingen Guardrails; CLI ist read-only. |
| AC-007: Manueller SkillOpt-light-Harness, kein vollständiger Optimizer | Kein LLM-Aufruf, keine automatische Skill-Datei-Änderung, nur Benchmark-/Score-/Review-Artefakte. |

## File Structure

- Create `workflows/contracts/nac-builder-skillopt.contract.json`: Maschinenlesbarer Vertrag für Scope, Zielprofil, Datenklassen, Edit-Gates und Akzeptanzregeln.
- Create `workflows/skillopt/README.md`: Deutsche Betriebsgrenze und Artefaktübersicht für den Pilot.
- Create `workflows/skillopt/nac-docs-parity-benchmark.json`: Start-Benchmark mit 15 synthetischen Aufgaben, Trainings-/Holdout-Aufteilung und erwarteten Findings.
- Create `workflows/skillopt/rejected-edits.jsonl`: Leeres JSONL-Nachweisziel für verworfene Skill-Edit-Vorschläge.
- Create `src/nac_skillopt/__init__.py`: Modulmarker und öffentliche Exporte.
- Create `src/nac_skillopt/benchmark.py`: lädt Vertrag und Benchmark, validiert Basisstruktur und erzeugt Status-Payloads.
- Create `src/nac_skillopt/scoring.py`: bewertet Baseline-/Kandidatenläufe und entscheidet akzeptieren, verwerfen oder Review nötig.
- Create `scripts/validate_nac_builder_skillopt.py`: deterministischer Validator für Vertrag, Benchmark, JSONL-Nachweise und Guardrails.
- Modify `scripts/quality_gate.py`: striktes Profil führt den neuen Validator aus.
- Modify `src/nac_cli/cli.py`: ergänzt `nac skillopt status` und `nac skillopt score` als read-only Bedienkante.
- Modify `workflows/contracts/README.md`: verlinkt den neuen Vertrag.
- Modify `workflows/GANTT.md`: dokumentiert den Pilot als aktiven Workflow-Harness-Slice.
- Modify `docs/de/codex-parallel-review-workflow.md` and `docs/en/codex-parallel-review-workflow.md`: nennt SkillOpt-light als Entwicklungs-Harness, nicht als Produktivpfad.
- Create `tests/test_nac_builder_skillopt.py`: Unit Tests für Vertrag, Benchmark, Runtime, Scoring, Validator und Guardrails.
- Modify `tests/test_nac_cli.py`: CLI-Abdeckung für `nac skillopt status` und `nac skillopt score`.

---

### Task 1: Vertrag und Benchmark manifestieren

**Files:**
- Create: `workflows/contracts/nac-builder-skillopt.contract.json`
- Create: `workflows/skillopt/README.md`
- Create: `workflows/skillopt/nac-docs-parity-benchmark.json`
- Create: `workflows/skillopt/rejected-edits.jsonl`
- Test: `tests/test_nac_builder_skillopt.py`

- [ ] **Step 1: Failing Contract- und Benchmark-Tests schreiben**

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

- [ ] **Step 2: RED verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt
```

Expected: FAIL with missing `workflows/contracts/nac-builder-skillopt.contract.json` or missing benchmark file.

- [ ] **Step 3: Vertrag anlegen**

Create `workflows/contracts/nac-builder-skillopt.contract.json`:

```json
{
  "schema_version": "nac.builder-skillopt/v0.1",
  "contract_id": "workflow.nac_builder_skillopt",
  "title": "NaC Builder SkillOpt-light Pilot",
  "status": "pilot_design_ready",
  "last_update": "2026-06-14",
  "purpose": "Bewertet NaC-Builder- und Review-Anweisungen gegen synthetische Benchmarkfälle, ohne Modelltraining, Produktivdaten, Auto-Merge oder notarielle Fachentscheidung.",
  "operating_scope": "nac_creation_and_review_only",
  "target_profiles": [
    "nac_docs_parity_reviewer"
  ],
  "artifact_roots": {
    "benchmark": "workflows/skillopt/nac-docs-parity-benchmark.json",
    "rejected_edits": "workflows/skillopt/rejected-edits.jsonl"
  },
  "allowed_inputs": [
    "synthetic_nac_tasks",
    "repo_files_without_real_mandate_data",
    "validator_outputs",
    "git_diffs",
    "review_comments"
  ],
  "prohibited_inputs": [
    "real_mandate_data",
    "real_personal_data",
    "pins",
    "passwords",
    "tokens",
    "productive_system_credentials",
    "secret_upload_or_read_links"
  ],
  "guardrails": {
    "productive_write_allowed": false,
    "real_mandate_data_allowed": false,
    "external_ai_processing_without_gate_allowed": false,
    "automatic_skill_merge_allowed": false,
    "notarial_truth_from_skill_output_allowed": false,
    "human_review_required": true,
    "git_diff_required": true,
    "fresh_validation_required": true
  },
  "acceptance_gate": {
    "holdout_rationale_required": true,
    "critical_errors_must_not_increase": true,
    "guardrail_violations_must_be_zero": true,
    "git_diff_required": true,
    "human_review_required": true,
    "tie_allowed_only_for_shorter_clearer_skill": true
  },
  "required_validation_commands": [
    "python scripts/validate_nac_builder_skillopt.py",
    "python scripts/validate_language_parity.py",
    "python scripts/validate_doc_links.py",
    "python scripts/quality_gate.py --profile strict"
  ],
  "decision_values": [
    "accept",
    "reject",
    "needs_human_review"
  ]
}
```

- [ ] **Step 4: Workflow-Artefaktordner und README anlegen**

Create `workflows/skillopt/README.md`:

```markdown
# NaC Builder SkillOpt-light

Dieser Ordner enthält den mandatsdatenfreien Pilot-Harness für die kontrollierte
Verbesserung von NaC-Builder- und Review-Anweisungen.

## Grenze

Der Harness ist nur für NaC-Erstellung und NaC-Review gedacht. Er darf keine
echten Mandatsdaten, keine echten personenbezogenen Daten, keine produktiven
Zugangsdaten und keine geheimen Links enthalten. Er ändert keine Skill-Dateien
automatisch und ersetzt keine menschliche Freigabe.

## Artefakte

- [nac-docs-parity-benchmark.json](nac-docs-parity-benchmark.json): synthetische
  Trainings- und Holdout-Aufgaben für `nac_docs_parity_reviewer`.
- [rejected-edits.jsonl](rejected-edits.jsonl): Nachweisziel für verworfene
  Skill-Edit-Vorschläge. Die Datei startet leer.

## Bedienkante

Der Pilot wird über diese read-only-Befehle sichtbar:

```bash
python scripts/nac.py skillopt status --format json
python scripts/nac.py skillopt score --run path/to/run.json --format json
```
```

- [ ] **Step 5: Benchmark mit 15 Fällen anlegen**

Create `workflows/skillopt/nac-docs-parity-benchmark.json`:

```json
{
  "schema_version": "nac.builder-skillopt-benchmark/v0.1",
  "benchmark_id": "nac-docs-parity-v0.1",
  "target_profile": "nac_docs_parity_reviewer",
  "description": "Synthetische NaC-Review-Aufgaben für Doku-Parität, Links, Terminologie und Validator-Hinweise.",
  "case_count": 15,
  "cases": [
    {
      "task_id": "DSP-001",
      "split": "train",
      "title": "Deutsche Spec ohne englisches Gegenstück",
      "input_summary": "Eine neue Datei unter docs/de/superpowers/specs wurde ergänzt, aber docs/en fehlt.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["missing_english_mirror", "spec_traceability_check_required"],
      "expected_non_findings": ["real_mandate_data"],
      "validation_commands": ["python scripts/validate_language_parity.py", "python scripts/validate_spec_traceability.py"]
    },
    {
      "task_id": "DSP-002",
      "split": "train",
      "title": "Englischer Plan ohne deutsche Spiegelung",
      "input_summary": "Ein neuer englischer Superpowers-Plan wurde ergänzt, aber die deutsche Plan-Datei fehlt.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["missing_german_mirror", "language_parity_check_required"],
      "expected_non_findings": ["bpmn_validation"],
      "validation_commands": ["python scripts/validate_language_parity.py"]
    },
    {
      "task_id": "DSP-003",
      "split": "train",
      "title": "Interner Doku-Verweis als Code-Span",
      "input_summary": "Ein README nennt docs/de/START_HERE.md in Backticks statt als Markdown-Link.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["markdown_link_required", "doc_links_check_required"],
      "expected_non_findings": ["translation_missing"],
      "validation_commands": ["python scripts/validate_doc_links.py"]
    },
    {
      "task_id": "DSP-004",
      "split": "train",
      "title": "Falscher öffentlicher Begriff",
      "input_summary": "Öffentliche Website-Kopie nutzt generisches workflow statt fachlicher Formulierung.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["public_terminology_violation", "styleguide_reference_required"],
      "expected_non_findings": ["contract_missing"],
      "validation_commands": ["node --test tests/content.test.js"]
    },
    {
      "task_id": "DSP-005",
      "split": "train",
      "title": "Workflow-Vertrag ohne Contract-Index",
      "input_summary": "Ein neuer JSON-Vertrag unter workflows/contracts ist vorhanden, aber README und contracts validate kennen ihn nicht.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["contract_index_missing", "contracts_validate_missing"],
      "expected_non_findings": ["mandate_data"],
      "validation_commands": ["python scripts/nac.py contracts validate"]
    },
    {
      "task_id": "DSP-006",
      "split": "train",
      "title": "Workflow-Scope ohne Gantt-Hinweis",
      "input_summary": "Ein neuer Workflow-Harness verändert Scope und Status, workflows/GANTT.md bleibt unverändert.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["workflow_gantt_update_required"],
      "expected_non_findings": ["usecase_gantt_required"],
      "validation_commands": ["python scripts/validate_gantt_progress.py"]
    },
    {
      "task_id": "DSP-007",
      "split": "train",
      "title": "Quality-Gate-Hinweis fehlt",
      "input_summary": "Ein neuer Validator ist geplant, aber der Review nennt keinen strikten Quality-Gate-Nachweis.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["quality_gate_evidence_missing", "validation_command_missing"],
      "expected_non_findings": ["translation_missing"],
      "validation_commands": ["python scripts/quality_gate.py --profile strict"]
    },
    {
      "task_id": "DSP-008",
      "split": "train",
      "title": "Agentprofil-Änderung ohne Read-only-Grenze",
      "input_summary": "Ein Agentprofil wird geschärft, aber die Review-Anweisung erwähnt Do-not-edit und Sandbox-Grenze nicht.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["agent_read_only_boundary_missing", "codex_parallel_review_validator_required"],
      "expected_non_findings": ["bpmn_model_missing"],
      "validation_commands": ["python scripts/validate_codex_parallel_review.py"]
    },
    {
      "task_id": "DSP-009",
      "split": "train",
      "title": "Deutsche Umlaute in Workflow-Doku fehlen",
      "input_summary": "Workflow-Menschentext nutzt ASCII-Umschreibungen wie fuer oder pruefen.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["german_umlaut_policy_violation", "language_parity_check_required"],
      "expected_non_findings": ["secret_leak"],
      "validation_commands": ["python scripts/validate_language_parity.py"]
    },
    {
      "task_id": "DSP-010",
      "split": "train",
      "title": "Neuer CLI-Befehl ohne Test",
      "input_summary": "Ein nac-Unterbefehl wurde ergänzt, aber tests/test_nac_cli.py deckt ihn nicht ab.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["cli_test_missing", "unit_test_required"],
      "expected_non_findings": ["doc_link_missing"],
      "validation_commands": ["env PYTHONPATH=src python -m unittest tests.test_nac_cli"]
    },
    {
      "task_id": "DSP-011",
      "split": "holdout",
      "title": "Spec-AC ohne Manifest-ID",
      "input_summary": "Eine neue Spec enthält AC-001 im Text, aber das nac-spec-traceability-Manifest fehlt.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["spec_manifest_missing", "acceptance_id_trace_missing"],
      "expected_non_findings": ["real_mandate_data"],
      "validation_commands": ["python scripts/validate_spec_traceability.py"]
    },
    {
      "task_id": "DSP-012",
      "split": "holdout",
      "title": "Englischer Link zeigt auf deutschen relativen Pfad",
      "input_summary": "docs/en verlinkt versehentlich auf docs/de statt auf das englische Gegenstück.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["wrong_link_language", "language_parity_check_required"],
      "expected_non_findings": ["contract_missing"],
      "validation_commands": ["python scripts/validate_language_parity.py"]
    },
    {
      "task_id": "DSP-013",
      "split": "holdout",
      "title": "Validator-Ausgabe nicht in Review übernommen",
      "input_summary": "Ein Review erwähnt Findings, aber nicht den konkreten fehlgeschlagenen Validator und Befehl.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["validator_evidence_missing", "review_output_too_vague"],
      "expected_non_findings": ["public_copy_violation"],
      "validation_commands": ["python scripts/quality_gate.py --profile strict"]
    },
    {
      "task_id": "DSP-014",
      "split": "holdout",
      "title": "Skill-Edit ohne Holdout-Begründung",
      "input_summary": "Ein Skill-Edit wird als Verbesserung vorgeschlagen, aber ohne Holdout-Ergebnis.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["holdout_rationale_missing", "human_review_required"],
      "expected_non_findings": ["translation_missing"],
      "validation_commands": ["python scripts/validate_nac_builder_skillopt.py"]
    },
    {
      "task_id": "DSP-015",
      "split": "holdout",
      "title": "Abgelehnter Edit nicht dokumentiert",
      "input_summary": "Ein Kandidaten-Edit wird verworfen, aber es gibt keinen rejected-edits-Eintrag.",
      "data_boundary": "synthetic_or_repo_allowed",
      "expected_findings": ["rejected_edit_evidence_missing", "negative_example_trace_required"],
      "expected_non_findings": ["auto_merge_required"],
      "validation_commands": ["python scripts/validate_nac_builder_skillopt.py"]
    }
  ]
}
```

- [ ] **Step 6: Leeres Rejected-Edit-Log anlegen**

Create `workflows/skillopt/rejected-edits.jsonl` as an empty file. Keep the file length at zero bytes.

- [ ] **Step 7: GREEN für Task 1 verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_contract_limits_pilot_to_nac_building tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_benchmark_has_train_and_holdout_cases_for_docs_parity tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_rejected_edit_log_exists_and_starts_empty
```

Expected: OK.

- [ ] **Step 8: Task 1 committen**

```bash
git add workflows/contracts/nac-builder-skillopt.contract.json workflows/skillopt/README.md workflows/skillopt/nac-docs-parity-benchmark.json workflows/skillopt/rejected-edits.jsonl tests/test_nac_builder_skillopt.py
git commit -m "feat: add NaC builder SkillOpt pilot contract"
```

---

### Task 2: Runtime-Lader und Scoring-Modell bauen

**Files:**
- Create: `src/nac_skillopt/__init__.py`
- Create: `src/nac_skillopt/benchmark.py`
- Create: `src/nac_skillopt/scoring.py`
- Modify: `tests/test_nac_builder_skillopt.py`

- [ ] **Step 1: Failing Runtime- und Scoring-Tests ergänzen**

Append these tests to `NaCBuilderSkillOptTests` in `tests/test_nac_builder_skillopt.py`:

```python
    def test_status_payload_reports_target_profile_and_split_counts(self) -> None:
        from nac_skillopt.benchmark import build_status_payload

        payload = build_status_payload(REPO_ROOT)

        self.assertEqual(payload["schema_version"], "nac.builder-skillopt-status/v0.1")
        self.assertEqual(payload["target_profile"], "nac_docs_parity_reviewer")
        self.assertEqual(payload["benchmark"]["cases"], 15)
        self.assertEqual(payload["benchmark"]["train_cases"], 10)
        self.assertEqual(payload["benchmark"]["holdout_cases"], 5)
        self.assertFalse(payload["guardrails"]["productive_write_allowed"])
        self.assertFalse(payload["guardrails"]["real_mandate_data_allowed"])

    def test_score_run_counts_required_hits_and_guardrail_violations(self) -> None:
        from nac_skillopt.benchmark import load_benchmark
        from nac_skillopt.scoring import score_run

        benchmark = load_benchmark(REPO_ROOT)
        run_payload = {
            "schema_version": "nac.builder-skillopt-run/v0.1",
            "target_profile": "nac_docs_parity_reviewer",
            "candidate_id": "baseline-current",
            "cases": [
                {
                    "task_id": "DSP-011",
                    "findings": ["spec_manifest_missing"],
                    "validation_commands": ["python scripts/validate_spec_traceability.py"],
                    "boundary_violations": []
                },
                {
                    "task_id": "DSP-014",
                    "findings": ["holdout_rationale_missing", "human_review_required"],
                    "validation_commands": ["python scripts/validate_nac_builder_skillopt.py"],
                    "boundary_violations": ["automatic_skill_merge_allowed"]
                }
            ]
        }

        score = score_run(benchmark, run_payload)

        self.assertEqual(score["schema_version"], "nac.builder-skillopt-score/v0.1")
        self.assertEqual(score["target_profile"], "nac_docs_parity_reviewer")
        self.assertEqual(score["case_scores"]["DSP-011"]["missed_required_findings"], ["acceptance_id_trace_missing"])
        self.assertEqual(score["totals"]["boundary_violations"], 1)
        self.assertEqual(score["decision"], "reject")
```

- [ ] **Step 2: RED verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_status_payload_reports_target_profile_and_split_counts tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_score_run_counts_required_hits_and_guardrail_violations
```

Expected: FAIL because `nac_skillopt` does not exist.

- [ ] **Step 3: Modul-Export anlegen**

Create `src/nac_skillopt/__init__.py`:

```python
from __future__ import annotations

from .benchmark import build_status_payload, load_benchmark, load_contract
from .scoring import compare_scores, score_run

__all__ = [
    "build_status_payload",
    "compare_scores",
    "load_benchmark",
    "load_contract",
    "score_run",
]
```

- [ ] **Step 4: Benchmark-Lader implementieren**

Create `src/nac_skillopt/benchmark.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path("workflows/contracts/nac-builder-skillopt.contract.json")
BENCHMARK_PATH = Path("workflows/skillopt/nac-docs-parity-benchmark.json")


def load_contract(repo_root: Path) -> dict[str, Any]:
    return _read_json(repo_root / CONTRACT_PATH)


def load_benchmark(repo_root: Path) -> dict[str, Any]:
    return _read_json(repo_root / BENCHMARK_PATH)


def build_status_payload(repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    benchmark = load_benchmark(repo_root)
    cases = benchmark.get("cases", [])
    train_cases = [case for case in cases if case.get("split") == "train"]
    holdout_cases = [case for case in cases if case.get("split") == "holdout"]
    return {
        "schema_version": "nac.builder-skillopt-status/v0.1",
        "contract_id": contract["contract_id"],
        "status": contract["status"],
        "target_profile": benchmark["target_profile"],
        "operating_scope": contract["operating_scope"],
        "benchmark": {
            "benchmark_id": benchmark["benchmark_id"],
            "cases": len(cases),
            "train_cases": len(train_cases),
            "holdout_cases": len(holdout_cases),
        },
        "guardrails": contract["guardrails"],
        "acceptance_gate": contract["acceptance_gate"],
        "commands": {
            "validate": "python scripts/validate_nac_builder_skillopt.py",
            "score": "python scripts/nac.py skillopt score --run path/to/run.json --format json",
        },
    }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload
```

- [ ] **Step 5: Scoring implementieren**

Create `src/nac_skillopt/scoring.py`:

```python
from __future__ import annotations

from typing import Any


def score_run(benchmark: dict[str, Any], run_payload: dict[str, Any]) -> dict[str, Any]:
    expected_by_id = {case["task_id"]: case for case in benchmark["cases"]}
    case_scores: dict[str, dict[str, Any]] = {}
    totals = {
        "cases_scored": 0,
        "required_findings": 0,
        "matched_required_findings": 0,
        "missed_required_findings": 0,
        "false_positive_findings": 0,
        "boundary_violations": 0,
        "missing_validation_commands": 0,
    }

    for case_run in run_payload.get("cases", []):
        task_id = case_run.get("task_id", "")
        expected_case = expected_by_id.get(task_id)
        if expected_case is None:
            continue
        expected_findings = set(expected_case.get("expected_findings", []))
        actual_findings = set(case_run.get("findings", []))
        expected_commands = set(expected_case.get("validation_commands", []))
        actual_commands = set(case_run.get("validation_commands", []))
        boundary_violations = list(case_run.get("boundary_violations", []))
        missed = sorted(expected_findings - actual_findings)
        matched = sorted(expected_findings & actual_findings)
        false_positive = sorted(actual_findings - expected_findings)
        missing_commands = sorted(expected_commands - actual_commands)

        case_scores[task_id] = {
            "matched_required_findings": matched,
            "missed_required_findings": missed,
            "false_positive_findings": false_positive,
            "missing_validation_commands": missing_commands,
            "boundary_violations": boundary_violations,
        }
        totals["cases_scored"] += 1
        totals["required_findings"] += len(expected_findings)
        totals["matched_required_findings"] += len(matched)
        totals["missed_required_findings"] += len(missed)
        totals["false_positive_findings"] += len(false_positive)
        totals["missing_validation_commands"] += len(missing_commands)
        totals["boundary_violations"] += len(boundary_violations)

    decision = "needs_human_review"
    if totals["boundary_violations"] > 0:
        decision = "reject"
    elif totals["missed_required_findings"] == 0 and totals["missing_validation_commands"] == 0:
        decision = "accept"

    return {
        "schema_version": "nac.builder-skillopt-score/v0.1",
        "target_profile": run_payload.get("target_profile"),
        "candidate_id": run_payload.get("candidate_id", ""),
        "decision": decision,
        "totals": totals,
        "case_scores": case_scores,
    }


def compare_scores(baseline_score: dict[str, Any], candidate_score: dict[str, Any]) -> dict[str, Any]:
    baseline = baseline_score["totals"]
    candidate = candidate_score["totals"]
    candidate_boundary_clean = candidate["boundary_violations"] == 0
    improved_critical_errors = candidate["missed_required_findings"] < baseline["missed_required_findings"]
    no_false_positive_regression = candidate["false_positive_findings"] <= baseline["false_positive_findings"]
    no_validator_regression = candidate["missing_validation_commands"] <= baseline["missing_validation_commands"]
    accepted = candidate_boundary_clean and improved_critical_errors and no_false_positive_regression and no_validator_regression
    return {
        "schema_version": "nac.builder-skillopt-comparison/v0.1",
        "baseline_candidate_id": baseline_score.get("candidate_id", ""),
        "candidate_id": candidate_score.get("candidate_id", ""),
        "decision": "accept" if accepted else "reject",
        "requires_human_review": True,
        "git_diff_required": True,
        "holdout_rationale_required": True,
        "reasons": {
            "candidate_boundary_clean": candidate_boundary_clean,
            "improved_critical_errors": improved_critical_errors,
            "no_false_positive_regression": no_false_positive_regression,
            "no_validator_regression": no_validator_regression,
        },
    }
```

- [ ] **Step 6: GREEN für Runtime und Scoring verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt
```

Expected: OK.

- [ ] **Step 7: Task 2 committen**

```bash
git add src/nac_skillopt tests/test_nac_builder_skillopt.py
git commit -m "feat: score NaC builder SkillOpt runs"
```

---

### Task 3: Validator und Quality-Gate-Anbindung bauen

**Files:**
- Create: `scripts/validate_nac_builder_skillopt.py`
- Modify: `scripts/quality_gate.py`
- Modify: `src/nac_cli/cli.py`
- Modify: `tests/test_nac_builder_skillopt.py`
- Modify: `tests/test_nac_cli.py`

- [ ] **Step 1: Failing Validator- und Gate-Tests ergänzen**

Append these tests to `tests/test_nac_builder_skillopt.py`:

```python
    def test_validator_accepts_skillopt_artifacts(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_nac_builder_skillopt.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)

    def test_strict_quality_gate_runs_skillopt_validator(self) -> None:
        from scripts import quality_gate

        checks = {check_id: command for check_id, _title, command in quality_gate.build_checks("strict")}

        self.assertIn("nac_builder_skillopt", checks)
        self.assertIn("scripts/validate_nac_builder_skillopt.py", checks["nac_builder_skillopt"])
```

Add this assertion to `tests/test_nac_cli.py::NaCCliTests.test_contracts_validate_secure_document_links`:

```python
        self.assertIn("NaC Builder SkillOpt", output)
```

- [ ] **Step 2: RED verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt tests.test_nac_cli.NaCCliTests.test_contracts_validate_secure_document_links
```

Expected: FAIL because `scripts/validate_nac_builder_skillopt.py`, the Quality-Gate check and `nac contracts validate` integration are missing.

- [ ] **Step 3: Validator implementieren**

Create `scripts/validate_nac_builder_skillopt.py`:

```python
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "nac-builder-skillopt.contract.json"
BENCHMARK_PATH = REPO_ROOT / "workflows" / "skillopt" / "nac-docs-parity-benchmark.json"
REJECTED_EDITS_PATH = REPO_ROOT / "workflows" / "skillopt" / "rejected-edits.jsonl"
REQUIRED_TARGET_PROFILE = "nac_docs_parity_reviewer"
PROHIBITED_MARKERS = {
    "real_mandate_data_sample",
    "secret_upload_link",
    "productive_credential",
    "BEGIN " + "PRIVATE KEY",
    "ghp_",
    "gho_",
}


def validate() -> list[str]:
    errors: list[str] = []
    contract = _read_json(CONTRACT_PATH, errors)
    benchmark = _read_json(BENCHMARK_PATH, errors)
    if contract:
        errors.extend(_validate_contract(contract))
    if benchmark:
        errors.extend(_validate_benchmark(benchmark))
    errors.extend(_validate_rejected_edits())
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"Pflichtdatei fehlt: {path.relative_to(REPO_ROOT)}")
        return {}
    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(REPO_ROOT)} enthält unzulässigen Marker: {marker}")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)} ist kein gültiges JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} muss ein JSON-Objekt sein")
        return {}
    return payload


def _validate_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "nac.builder-skillopt/v0.1":
        errors.append("nac-builder-skillopt.contract.json: falsche schema_version")
    if payload.get("contract_id") != "workflow.nac_builder_skillopt":
        errors.append("nac-builder-skillopt.contract.json: falsche contract_id")
    if payload.get("target_profiles") != [REQUIRED_TARGET_PROFILE]:
        errors.append("nac-builder-skillopt.contract.json: target_profiles muss nur nac_docs_parity_reviewer enthalten")
    if payload.get("operating_scope") != "nac_creation_and_review_only":
        errors.append("nac-builder-skillopt.contract.json: operating_scope muss nac_creation_and_review_only sein")
    guardrails = payload.get("guardrails")
    if not isinstance(guardrails, dict):
        errors.append("nac-builder-skillopt.contract.json: guardrails muss ein Objekt sein")
    else:
        for key in (
            "productive_write_allowed",
            "real_mandate_data_allowed",
            "external_ai_processing_without_gate_allowed",
            "automatic_skill_merge_allowed",
            "notarial_truth_from_skill_output_allowed",
        ):
            if guardrails.get(key) is not False:
                errors.append(f"nac-builder-skillopt.contract.json: guardrails.{key} muss false sein")
        for key in ("human_review_required", "git_diff_required", "fresh_validation_required"):
            if guardrails.get(key) is not True:
                errors.append(f"nac-builder-skillopt.contract.json: guardrails.{key} muss true sein")
    return errors


def _validate_benchmark(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "nac.builder-skillopt-benchmark/v0.1":
        errors.append("nac-docs-parity-benchmark.json: falsche schema_version")
    if payload.get("target_profile") != REQUIRED_TARGET_PROFILE:
        errors.append("nac-docs-parity-benchmark.json: target_profile muss nac_docs_parity_reviewer sein")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        return ["nac-docs-parity-benchmark.json: cases muss eine Liste sein"]
    if not 15 <= len(cases) <= 30:
        errors.append("nac-docs-parity-benchmark.json: cases muss zwischen 15 und 30 Einträge enthalten")
    splits = {case.get("split") for case in cases if isinstance(case, dict)}
    if splits != {"train", "holdout"}:
        errors.append("nac-docs-parity-benchmark.json: split muss train und holdout enthalten")
    seen_ids: set[str] = set()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"case {index}: muss ein Objekt sein")
            continue
        task_id = case.get("task_id")
        if not isinstance(task_id, str) or not task_id.startswith("DSP-"):
            errors.append(f"case {index}: task_id muss mit DSP- beginnen")
        elif task_id in seen_ids:
            errors.append(f"case {index}: task_id doppelt {task_id}")
        else:
            seen_ids.add(task_id)
        if case.get("data_boundary") != "synthetic_or_repo_allowed":
            errors.append(f"{task_id}: data_boundary muss synthetic_or_repo_allowed sein")
        for field in ("expected_findings", "expected_non_findings", "validation_commands"):
            value = case.get(field)
            if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
                errors.append(f"{task_id}: {field} muss eine nicht leere String-Liste sein")
    return errors


def _validate_rejected_edits() -> list[str]:
    errors: list[str] = []
    if not REJECTED_EDITS_PATH.is_file():
        return [f"Pflichtdatei fehlt: {REJECTED_EDITS_PATH.relative_to(REPO_ROOT)}"]
    for line_number, line in enumerate(REJECTED_EDITS_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        for marker in PROHIBITED_MARKERS:
            if marker.lower() in line.lower():
                errors.append(f"rejected-edits.jsonl:{line_number}: unzulässiger Marker {marker}")
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"rejected-edits.jsonl:{line_number}: ungültiges JSON: {exc}")
            continue
        for field in ("edit_id", "target_profile", "rejected_reason", "holdout_result", "human_decision"):
            if not payload.get(field):
                errors.append(f"rejected-edits.jsonl:{line_number}: Pflichtfeld fehlt {field}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: NaC Builder SkillOpt-light Vertrag, Benchmark und Nachweisgrenzen sind gültig.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: `nac contracts validate` anbinden**

In `src/nac_cli/cli.py`, add this tuple to `command_contracts` before the Spec Traceability entry:

```python
            ("NaC Builder SkillOpt", "validate_nac_builder_skillopt.py"),
```

- [ ] **Step 5: Striktes Quality Gate anbinden**

In `scripts/quality_gate.py`, add this strict check after `codex_parallel_review`:

```python
                (
                    "nac_builder_skillopt",
                    "NaC Builder SkillOpt-light",
                    [sys.executable, "scripts/validate_nac_builder_skillopt.py"],
                ),
```

- [ ] **Step 6: GREEN für Validator und Gate verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt tests.test_nac_cli.NaCCliTests.test_contracts_validate_secure_document_links
```

Expected: OK.

- [ ] **Step 7: Task 3 committen**

```bash
git add scripts/validate_nac_builder_skillopt.py scripts/quality_gate.py src/nac_cli/cli.py tests/test_nac_builder_skillopt.py tests/test_nac_cli.py
git commit -m "feat: validate NaC builder SkillOpt pilot"
```

---

### Task 4: Read-only CLI-Bedienkante ergänzen

**Files:**
- Modify: `src/nac_cli/cli.py`
- Modify: `tests/test_nac_cli.py`

- [ ] **Step 1: Failing CLI-Tests schreiben**

Append these tests to `NaCCliTests` in `tests/test_nac_cli.py`:

```python
    def test_skillopt_status_cli_returns_json(self) -> None:
        rc, output = run_cli("skillopt", "status", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.builder-skillopt-status/v0.1")
        self.assertEqual(payload["target_profile"], "nac_docs_parity_reviewer")
        self.assertEqual(payload["benchmark"]["cases"], 15)
        self.assertFalse(payload["guardrails"]["productive_write_allowed"])
        self.assertFalse(payload["guardrails"]["real_mandate_data_allowed"])

    def test_skillopt_score_cli_scores_run_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp) / "run.json"
            run_path.write_text(
                json.dumps(
                    {
                        "schema_version": "nac.builder-skillopt-run/v0.1",
                        "target_profile": "nac_docs_parity_reviewer",
                        "candidate_id": "candidate-review",
                        "cases": [
                            {
                                "task_id": "DSP-014",
                                "findings": ["holdout_rationale_missing", "human_review_required"],
                                "validation_commands": ["python scripts/validate_nac_builder_skillopt.py"],
                                "boundary_violations": []
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            rc, output = run_cli("skillopt", "score", "--run", str(run_path), "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.builder-skillopt-score/v0.1")
        self.assertEqual(payload["candidate_id"], "candidate-review")
        self.assertEqual(payload["decision"], "accept")
```

- [ ] **Step 2: RED verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_cli.NaCCliTests.test_skillopt_status_cli_returns_json tests.test_nac_cli.NaCCliTests.test_skillopt_score_cli_scores_run_json
```

Expected: FAIL because `skillopt` subcommand is not registered.

- [ ] **Step 3: CLI-Imports ergänzen**

In `src/nac_cli/cli.py`, add these imports near the other NaC imports:

```python
from nac_skillopt.benchmark import build_status_payload, load_benchmark
from nac_skillopt.scoring import score_run
```

- [ ] **Step 4: Parser ergänzen**

In `build_parser()`, add this block before the `tenant` parser:

```python
    skillopt = subparsers.add_parser("skillopt", help="Steuert den NaC Builder SkillOpt-light Pilot.")
    skillopt_sub = skillopt.add_subparsers(dest="skillopt_command", required=True)
    skillopt_status = skillopt_sub.add_parser("status", help="Zeigt Vertrag, Benchmark und Guardrails.")
    skillopt_status.add_argument("--format", choices=["text", "json"], default="text")
    skillopt_score = skillopt_sub.add_parser("score", help="Bewertet ein SkillOpt-light Run-Artefakt.")
    skillopt_score.add_argument("--run", type=Path, required=True, help="Pfad zu einem nac.builder-skillopt-run/v0.1 JSON.")
    skillopt_score.add_argument("--format", choices=["text", "json"], default="text")
    skillopt.set_defaults(func=command_skillopt)
```

- [ ] **Step 5: Command-Funktion ergänzen**

Add this function after `command_legal_graph(...)`:

```python
def command_skillopt(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    try:
        if args.skillopt_command == "status":
            payload = build_status_payload(repo_root)
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC Builder SkillOpt-light")
            print(f"- Zielprofil: {payload['target_profile']}")
            print(f"- Benchmark: {payload['benchmark']['cases']} Fälle")
            print(f"- Training: {payload['benchmark']['train_cases']}")
            print(f"- Holdout: {payload['benchmark']['holdout_cases']}")
            print(f"- Produktive Writes: {payload['guardrails']['productive_write_allowed']}")
            return 0

        if args.skillopt_command == "score":
            run_payload = json.loads(args.run.read_text(encoding="utf-8"))
            payload = score_run(load_benchmark(repo_root), run_payload)
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC Builder SkillOpt-light Score")
            print(f"- Kandidat: {payload['candidate_id']}")
            print(f"- Entscheidung: {payload['decision']}")
            print(f"- Bewertete Fälle: {payload['totals']['cases_scored']}")
            print(f"- Verpasste Pflicht-Findings: {payload['totals']['missed_required_findings']}")
            print(f"- Guardrail-Verletzungen: {payload['totals']['boundary_violations']}")
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        if getattr(args, "format", "text") == "json":
            print_json({"schema_version": "nac.error/v0.1", "command": "skillopt", "error": str(exc)})
            return 1
        print(f"ERROR: {exc}")
        return 1

    raise AssertionError(f"Unknown skillopt command: {args.skillopt_command}")
```

- [ ] **Step 6: GREEN für CLI verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_cli.NaCCliTests.test_skillopt_status_cli_returns_json tests.test_nac_cli.NaCCliTests.test_skillopt_score_cli_scores_run_json
```

Expected: OK.

- [ ] **Step 7: Task 4 committen**

```bash
git add src/nac_cli/cli.py tests/test_nac_cli.py
git commit -m "feat: expose NaC builder SkillOpt status"
```

---

### Task 5: Doku, Contract-Index und Workflow-Gantt pflegen

**Files:**
- Modify: `workflows/contracts/README.md`
- Modify: `workflows/GANTT.md`
- Modify: `docs/de/codex-parallel-review-workflow.md`
- Modify: `docs/en/codex-parallel-review-workflow.md`

- [ ] **Step 1: Failing Doku-Test ergänzen**

Append this test to `tests/test_nac_builder_skillopt.py`:

```python
    def test_docs_surface_mentions_skillopt_as_development_harness_only(self) -> None:
        contract_readme = (REPO_ROOT / "workflows" / "contracts" / "README.md").read_text(encoding="utf-8")
        german = (REPO_ROOT / "docs" / "de" / "codex-parallel-review-workflow.md").read_text(encoding="utf-8")
        english = (REPO_ROOT / "docs" / "en" / "codex-parallel-review-workflow.md").read_text(encoding="utf-8")
        gantt = (REPO_ROOT / "workflows" / "GANTT.md").read_text(encoding="utf-8")

        self.assertIn("nac-builder-skillopt.contract.json", contract_readme)
        self.assertIn("SkillOpt-light", german)
        self.assertIn("keine echten Mandatsdaten", german)
        self.assertIn("SkillOpt-light", english)
        self.assertIn("no real mandate data", english)
        self.assertIn("NaC-Builder-SkillOpt-light-Pilot", gantt)
```

- [ ] **Step 2: RED verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_docs_surface_mentions_skillopt_as_development_harness_only
```

Expected: FAIL because the documentation surfaces do not mention the new harness yet.

- [ ] **Step 3: Contract-Index ergänzen**

In `workflows/contracts/README.md`, add this bullet after the Codex Parallel Review contract:

```markdown
- [workflows/contracts/nac-builder-skillopt.contract.json](nac-builder-skillopt.contract.json):
  Vertrag für einen mandatsdatenfreien NaC-Builder-SkillOpt-light-Pilot, der
  `nac_docs_parity_reviewer` gegen synthetische Benchmark- und Holdout-Fälle
  bewertet, ohne Modelltraining, Auto-Merge oder produktive Schreibaktionen.
```

- [ ] **Step 4: Workflow-Gantt ergänzen**

In `workflows/GANTT.md`, update `Letzte Aktualisierung` to `2026-06-14`, then add this line in section `Ausführung` after `Nachweis- und Replay-Prüfungen`:

```markdown
    NaC-Builder-SkillOpt-light-Pilot          :active, w7a, 2026-06-14, 7d
```

In the status table, add this row after `Workflow-Verträge`:

```markdown
| NaC-Builder-SkillOpt-light | `workflows/skillopt/` plus `src/nac_skillopt/` | Pilot | Bewertet NaC-Builder- und Review-Anweisungen gegen synthetische Doku-Paritätsfälle; keine echten Mandatsdaten, kein Auto-Merge und keine automatische Skill-Änderung. |
```

- [ ] **Step 5: Deutsche Codex-Parallel-Review-Doku ergänzen**

In `docs/de/codex-parallel-review-workflow.md`, add this section before `## Grenze`:

```markdown
## SkillOpt-light Für NaC-Builder-Arbeit

Der NaC-Builder-SkillOpt-light-Pilot ergänzt diesen Review-Workflow als
Entwicklungs-Harness. Er bewertet zunächst nur `nac_docs_parity_reviewer` gegen
synthetische Doku-, Link-, Terminologie- und Validatorfälle. Der Pilot erzeugt
Scores und Review-Artefakte, ändert aber keine Skill-Dateien automatisch.

Die Grenze bleibt dieselbe wie beim Parallel Review: keine echten Mandatsdaten,
keine produktiven Schreibaktionen, keine notarielle Wahrheit aus Modelloutput
und keine Freigabe ohne menschliches Review.
```

- [ ] **Step 6: Englische Codex-Parallel-Review-Doku ergänzen**

In `docs/en/codex-parallel-review-workflow.md`, add this section before `## Boundary`:

```markdown
## SkillOpt-light For NaC Builder Work

The NaC Builder SkillOpt-light pilot complements this review workflow as a
development harness. It first evaluates only `nac_docs_parity_reviewer` against
synthetic documentation, link, terminology and validator cases. The pilot
produces scores and review artifacts, but it does not edit skill files
automatically.

The boundary remains the same as for parallel review: no real mandate data, no
productive write actions, no notarial truth from model output and no approval
without human review.
```

- [ ] **Step 7: Doku-Checks verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt.NaCBuilderSkillOptTests.test_docs_surface_mentions_skillopt_as_development_harness_only
/home/ubuntu/.venvs/nac/bin/python scripts/validate_language_parity.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_doc_links.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_gantt_progress.py
```

Expected: all commands pass.

- [ ] **Step 8: Task 5 committen**

```bash
git add workflows/contracts/README.md workflows/GANTT.md docs/de/codex-parallel-review-workflow.md docs/en/codex-parallel-review-workflow.md tests/test_nac_builder_skillopt.py
git commit -m "docs: document NaC builder SkillOpt pilot"
```

---

### Task 6: Vollständige Validierung und Abschluss

**Files:**
- All touched files above.

- [ ] **Step 1: Focused Tests ausführen**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_builder_skillopt tests.test_nac_cli
```

Expected: OK.

- [ ] **Step 2: Contract- und Doku-Validatoren ausführen**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/validate_nac_builder_skillopt.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_codex_parallel_review.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_language_parity.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_doc_links.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_gantt_progress.py
```

Expected: all commands print `STATUS: PASSED` or their existing success line.

- [ ] **Step 3: Strict Quality Gate ausführen**

Run:

```bash
env GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: `STATUS: PASSED`.

- [ ] **Step 4: Arbeitsbaum prüfen**

Run:

```bash
git status --short
```

Expected: no unstaged changes after the final commit.

- [ ] **Step 5: Abschluss-Commit erstellen, falls nach Task 5 noch Änderungen offen sind**

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
