from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CodexSubagentOperatingGateTests(unittest.TestCase):
    def test_registry_has_exact_read_only_profiles(self) -> None:
        payload = _read_json("agent-context/subagent-registry.json")

        self.assertEqual(payload["schema_version"], "nac.codex-subagent-registry/v0.1")
        self.assertEqual(payload["default_sandbox_mode"], "read-only")
        self.assertEqual(payload["limits"]["max_threads"], 6)
        self.assertEqual(payload["limits"]["max_depth"], 1)
        self.assertEqual(payload["limits"]["job_max_runtime_seconds"], 1800)
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
