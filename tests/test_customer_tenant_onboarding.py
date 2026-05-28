from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class CustomerTenantOnboardingTests(unittest.TestCase):
    def test_contract_declares_customer_and_saas_admin_journeys(self) -> None:
        contract = json.loads(
            (REPO_ROOT / "workflows/contracts/customer-tenant-onboarding.contract.json").read_text(encoding="utf-8")
        )

        self.assertEqual(contract["schema_version"], "nac.customer-tenant-onboarding/v0.1")
        self.assertEqual(contract["public_entry_surface"], "www-n8")
        self.assertEqual(contract["app_surface"], "app.notariat8.de")
        self.assertIn("customer_domain_readiness", contract["customer_journey"])
        self.assertIn("saas_admin_review_queue", contract["saas_admin_journey"])
        self.assertFalse(contract["guardrails"]["customer_oci_console_required"])


if __name__ == "__main__":
    unittest.main()
