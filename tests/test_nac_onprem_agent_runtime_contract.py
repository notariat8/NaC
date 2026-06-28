from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_nac_onprem_agent_runtime import validate_contract  # noqa: E402


class NaCOnPremAgentRuntimeContractTests(unittest.TestCase):
    def test_contract_validator_accepts_repository_contract(self) -> None:
        self.assertEqual(validate_contract(), [])


if __name__ == "__main__":
    unittest.main()
