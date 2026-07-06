from __future__ import annotations

import sys
import unittest
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_nac_onprem_agent_runtime import validate_contract  # noqa: E402


class NaCOnPremAgentRuntimeContractTests(unittest.TestCase):
    def test_contract_validator_accepts_repository_contract(self) -> None:
        self.assertEqual(validate_contract(), [])

    def test_runtime_smoke_is_prepared_but_not_executed(self) -> None:
        contract = json.loads(
            (REPO_ROOT / "workflows" / "contracts" / "nac-onprem-agent-runtime.contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["status"], "archived_legacy_no_productive_connector_apply")
        runtime_smoke = contract["target_control"]["runtime_smoke"]

        self.assertEqual(runtime_smoke["status"], "ready_owner_gated_not_executed")
        self.assertTrue(runtime_smoke["owner_apply_required_before_execution"])
        for key in (
            "execution_performed",
            "installation_performed",
            "onboard_performed",
            "rebuild_performed",
            "lifecycle_hooks_enabled",
            "openclaw_runtime_mutation_performed",
            "dashboard_token_captured",
            "github_write_performed",
            "oci_write_performed",
            "secrets_required",
            "matter_data_required",
        ):
            self.assertFalse(runtime_smoke[key], key)


if __name__ == "__main__":
    unittest.main()
