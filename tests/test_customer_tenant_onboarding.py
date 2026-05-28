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

    def test_customer_tenant_plan_uses_compartment_and_shared_atp_mapping(self) -> None:
        from nac_identity.customer_onboarding import build_customer_tenant_plan

        plan = build_customer_tenant_plan(
            domain="kanzlei-notariat.example",
            tenant_slug="kanzlei-notariat",
            admin_email="admin@kanzlei-notariat.example",
            saas_admin_email="saas-owner@example.com",
        )
        serialized = json.dumps(plan, sort_keys=True).lower()

        self.assertEqual(plan["schema_version"], "nac.customer-tenant-plan/v0.1")
        self.assertEqual(plan["tenant"]["domain"], "kanzlei-notariat.example")
        self.assertEqual(plan["admin_user"]["email"], "admin@kanzlei-notariat.example")
        self.assertEqual(plan["oci"]["identity"]["customer_domain_strategy"], "single_secondary_domain")
        self.assertEqual(plan["oci"]["resource_isolation"]["compartment_strategy"], "one_compartment_per_customer_domain")
        self.assertEqual(plan["atp"]["strategy"], "shared_atp_with_tenant_id")
        self.assertIn("tenant_id", plan["atp"]["required_controls"])
        self.assertTrue(plan["requires_owner_apply"])
        self.assertNotIn("private_key", serialized)
        self.assertNotIn("client_secret", serialized)

    def test_dns_check_result_explains_propagation_delay(self) -> None:
        from nac_identity.customer_onboarding import build_dns_check_result

        result = build_dns_check_result(
            expected_name="_nac.kanzlei-notariat.example",
            expected_value="nac-domain-verification=abc123",
            observed_values=[],
            resolver_error="not_found",
        )

        self.assertEqual(result["status"], "pending")
        self.assertIn("dns_record_not_found", result["findings"])
        self.assertTrue(result["retry_allowed"])
        self.assertIn("propagation", result["customer_guidance"])


if __name__ == "__main__":
    unittest.main()
