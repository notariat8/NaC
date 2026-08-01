from __future__ import annotations

import json
import copy
import tomllib
import unittest
from pathlib import Path

import yaml

from scripts import validate_codex_subagent_operating_gate as validator


REPO_ROOT = Path(__file__).resolve().parents[1]


class CodexSubagentOperatingGateTests(unittest.TestCase):
    def test_validator_fails_closed_on_full_history_policy_drift(self) -> None:
        payload = _read_json("agent-context/subagent-registry.json")
        changed = copy.deepcopy(payload)
        changed["context_isolation"]["full_history_fork_allowed"] = True

        errors = validator._validate_registry(changed)

        self.assertTrue(any("fork_context:false" in error for error in errors))

    def test_process_policy_is_the_context_isolation_source_of_truth(self) -> None:
        payload = yaml.safe_load(
            (REPO_ROOT / "policies" / "process-policy.yaml").read_text(
                encoding="utf-8"
            )
        )
        isolation = payload["agent_workflows"]["codex_subagent_context_isolation"]
        self.assertFalse(isolation["fork_context_default"])
        self.assertFalse(isolation["full_history_fork_allowed"])
        self.assertEqual(
            isolation["required_prompt_context"],
            ["task", "paths", "issue_or_pr", "applicable_rules"],
        )
        self.assertTrue(isolation["close_completed_subagents_immediately"])
        self.assertTrue(isolation["prohibit_parent_task_session_duplication"])
        implementation_context = validator._python_set_constant(
            REPO_ROOT / "src/nac_agent_ops/batch_run_envelope.py",
            "REQUIRED_SUBAGENT_PROMPT_CONTEXT",
            [],
        )
        self.assertEqual(implementation_context, set(isolation["required_prompt_context"]))

    def test_registry_has_exact_read_only_profiles(self) -> None:
        payload = _read_json("agent-context/subagent-registry.json")

        self.assertEqual(payload["schema_version"], "nac.codex-subagent-registry/v0.1")
        self.assertEqual(payload["default_sandbox_mode"], "read-only")
        self.assertEqual(payload["limits"]["max_threads"], 6)
        self.assertEqual(payload["limits"]["max_depth"], 1)
        self.assertEqual(payload["limits"]["job_max_runtime_seconds"], 1800)
        self.assertEqual(
            payload["context_isolation"],
            {
                "fork_context_default": False,
                "full_history_fork_allowed": False,
                "scoped_prompt_required": True,
                "required_prompt_context": [
                    "task", "paths", "issue_or_pr", "applicable_rules"
                ],
                "close_completed_subagents_immediately": True,
            },
        )
        names = {item["name"] for item in payload["allowed_profiles"]}
        self.assertEqual(
            names,
            {
                "nac_scope_mapper",
                "nac_kg_reviewer",
                "nac_bpmn_reviewer",
                "nac_policy_reviewer",
                "nac_docs_parity_reviewer",
                "nac_validation_reviewer",
            },
        )
        for profile in payload["allowed_profiles"]:
            self.assertEqual(profile["sandbox_mode"], "read-only")
            self.assertFalse(profile["may_edit_files"])

    def test_registry_matches_agent_toml_files_exactly(self) -> None:
        payload = _read_json("agent-context/subagent-registry.json")
        registry_paths = {item["path"] for item in payload["allowed_profiles"]}
        actual_paths = {
            item.relative_to(REPO_ROOT).as_posix()
            for item in (REPO_ROOT / ".codex" / "agents").glob("*.toml")
        }

        self.assertEqual(actual_paths, registry_paths)
        for profile in payload["allowed_profiles"]:
            text = (REPO_ROOT / profile["path"]).read_text(encoding="utf-8")
            toml_payload = tomllib.loads(text)
            self.assertEqual(toml_payload["name"], profile["name"])
            self.assertEqual(toml_payload["sandbox_mode"], "read-only")
            self.assertIn("Do not edit files.", toml_payload["developer_instructions"])

    def test_contract_and_verification_reference_subagent_gate(self) -> None:
        contract = _read_json("workflows/contracts/codex-parallel-review.contract.json")
        verification = _read_json(
            "workflows/verification-contracts/codex-subagent-operating-gate.verification.json"
        )

        self.assertIn(
            "workflows/verification-contracts/codex-subagent-operating-gate.verification.json",
            contract["verification_contracts"],
        )
        self.assertIn(
            "python scripts/validate_codex_subagent_operating_gate.py",
            contract["validation_commands"],
        )
        self.assertEqual(verification["contract_id"], "verification.codex_subagent_operating_gate")
        self.assertEqual(verification["thresholds"]["required_profile_count"], 6)
        self.assertEqual(verification["thresholds"]["minimum_independent_questions_for_subagents"], 2)
        self.assertFalse(verification["thresholds"]["fork_context_default"])
        self.assertFalse(verification["thresholds"]["full_history_fork_allowed"])
        gate = contract["subagent_operating_gate"]
        self.assertFalse(gate["fork_context_default"])
        self.assertFalse(gate["full_history_fork_allowed"])
        self.assertTrue(gate["scoped_prompt_required"])
        self.assertEqual(
            gate["required_prompt_context"],
            ["task", "paths", "issue_or_pr", "applicable_rules"],
        )

    def test_contract_fails_closed_when_prompt_context_drifts(self) -> None:
        contract = _read_json("workflows/contracts/codex-parallel-review.contract.json")
        registry = _read_json("agent-context/subagent-registry.json")
        changed = copy.deepcopy(contract)
        changed["subagent_operating_gate"]["required_prompt_context"] = ["task"]

        errors = validator._validate_contract(changed, registry)

        self.assertTrue(any("required_prompt_context" in error for error in errors))

    def test_verification_contract_fails_closed_when_isolation_is_removed(self) -> None:
        payload = _read_json(
            "workflows/verification-contracts/codex-subagent-operating-gate.verification.json"
        )
        changed = copy.deepcopy(payload)
        changed["invariants"] = [
            item for item in changed["invariants"] if "full-history" not in item
        ]
        changed["required_evidence"].remove("context_isolation_policy")
        changed["pass_condition"].pop("context_isolation_enforced")
        changed["failure_behavior"].pop("full_history_fork")

        errors = validator._validate_verification_contract(changed)

        self.assertTrue(any("Isolation-Invariante" in error for error in errors))
        self.assertTrue(any("context_isolation_policy" in error for error in errors))
        self.assertTrue(any("context_isolation_enforced" in error for error in errors))
        self.assertTrue(any("full_history_fork" in error for error in errors))

    def test_docs_require_complete_context_isolation_language(self) -> None:
        for rel_path, markers in validator.DOC_CONTEXT_ISOLATION_MARKERS.items():
            text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            for marker in markers:
                self.assertNotIn(
                    marker,
                    validator._missing_doc_context_markers(rel_path, text),
                )

    def test_docs_fail_when_parent_task_duplication_prohibition_is_removed(self) -> None:
        for rel_path, markers in validator.DOC_CONTEXT_ISOLATION_MARKERS.items():
            text = " ".join((REPO_ROOT / rel_path).read_text(encoding="utf-8").split())
            duplication_marker = markers[-1]
            changed = text.replace(duplication_marker, "")

            missing = validator._missing_doc_context_markers(rel_path, changed)

            self.assertIn(duplication_marker, missing)

    def test_agent_context_routes_subagent_operating_gate(self) -> None:
        payload = _read_json("agent-context/index.json")
        categories = {
            category["id"]: category["paths"]
            for layer in payload["layers"]
            for category in layer.get("categories", [])
        }

        self.assertIn("subagent_operating_gate", categories)
        self.assertIn("agent-context/subagent-registry.json", categories["subagent_operating_gate"])
        self.assertIn(
            "workflows/verification-contracts/codex-subagent-operating-gate.verification.json",
            payload["verification_contracts"],
        )


def _read_json(rel_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
