from __future__ import annotations

import sys
import unittest
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_notarial_onprem_connector_boundaries import validate_contract  # noqa: E402


class NotarialOnPremConnectorBoundariesContractTests(unittest.TestCase):
    def test_contract_validator_accepts_repository_contract(self) -> None:
        self.assertEqual(validate_contract(), [])

    def test_contract_is_archived_legacy_not_active_gate(self) -> None:
        contract = json.loads(
            (
                REPO_ROOT
                / "workflows"
                / "contracts"
                / "notarial-onprem-connector-boundaries.contract.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(contract["status"], "archived_legacy_no_live_apply")


if __name__ == "__main__":
    unittest.main()
