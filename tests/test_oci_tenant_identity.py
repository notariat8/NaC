from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class NaCOciTenantIdentityTests(unittest.TestCase):
    def test_contract_declares_dry_run_only_boundary(self) -> None:
        contract = json.loads(
            (REPO_ROOT / "workflows/contracts/oci-tenant-identity.contract.json").read_text(encoding="utf-8")
        )

        self.assertEqual(contract["schema_version"], "nac.oci-tenant-identity-contract/v0.1")
        self.assertFalse(contract["productive_identity_writes_allowed"])
        self.assertIn("domain_ready", contract["required_gates"])
        self.assertIn("owner_apply_approval", contract["required_gates"])
        self.assertIn("/admin/v1/Users", contract["oci_identity_domain_endpoints"])
        self.assertIn("/admin/v1/Groups", contract["oci_identity_domain_endpoints"])

    def test_domain_check_accepts_notary_domain_and_admin_email(self) -> None:
        from nac_identity.oci_tenant import check_domain_ready

        result = check_domain_ready(
            domain="kanzlei-notariat.example",
            tenant_slug="kanzlei-notariat",
            admin_email="admin@kanzlei-notariat.example",
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["schema_version"], "nac.tenant-domain-readiness/v0.1")
        self.assertEqual(result["domain"], "kanzlei-notariat.example")
        self.assertEqual(result["tenant_slug"], "kanzlei-notariat")
        self.assertEqual(result["blocking_findings"], [])
        self.assertEqual(result["verification"]["dns_record_name"], "_nac.kanzlei-notariat.example")
        self.assertTrue(result["verification"]["dns_record_value"].startswith("nac-domain-verification="))

    def test_domain_check_rejects_freemail_admin(self) -> None:
        from nac_identity.oci_tenant import check_domain_ready

        result = check_domain_ready(
            domain="kanzlei-notariat.example",
            tenant_slug="kanzlei-notariat",
            admin_email="admin@gmail.com",
        )

        self.assertFalse(result["ready"])
        self.assertIn("admin_email_domain_mismatch", result["blocking_findings"])
        self.assertIn("admin_email_freemail_domain", result["blocking_findings"])

    def test_domain_check_rejects_unstable_tenant_slug(self) -> None:
        from nac_identity.oci_tenant import check_domain_ready

        result = check_domain_ready(
            domain="kanzlei-notariat.example",
            tenant_slug="NaC Admin",
            admin_email="admin@kanzlei-notariat.example",
        )

        self.assertFalse(result["ready"])
        self.assertIn("tenant_slug_invalid", result["blocking_findings"])

    def test_admin_provisioning_plan_is_dry_run_and_uses_oci_identity_domain_paths(self) -> None:
        from nac_identity.oci_tenant import build_admin_provisioning_plan

        plan = build_admin_provisioning_plan(
            tenant_slug="kanzlei-notariat",
            domain="kanzlei-notariat.example",
            admin_email="admin@kanzlei-notariat.example",
            admin_display_name="Admin Notariat",
            identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
            identity_domain_id="ocid1.domain.oc1.example",
        )

        serialized = json.dumps(plan, sort_keys=True).lower()
        self.assertEqual(plan["schema_version"], "nac.oci-admin-provisioning-plan/v0.1")
        self.assertEqual(plan["mode"], "dry_run")
        self.assertTrue(plan["requires_human_approval"])
        self.assertFalse(plan["console_access_required_for_end_users"])
        self.assertEqual(plan["target"]["users_endpoint"], "https://idcs.example.identity.oraclecloud.com:443/admin/v1/Users")
        self.assertEqual(plan["target"]["groups_endpoint"], "https://idcs.example.identity.oraclecloud.com:443/admin/v1/Groups")
        self.assertEqual(plan["admin_user"]["user_name"], "admin@kanzlei-notariat.example")
        self.assertIn("nac-tenant-admin", plan["groups"])
        self.assertIn("users.create", plan["planned_writes"])
        self.assertNotIn("secret", serialized)
        self.assertNotIn("token", serialized)
        self.assertNotIn("private_key", serialized)

    def test_admin_provisioning_plan_refuses_unready_domain(self) -> None:
        from nac_identity.oci_tenant import build_admin_provisioning_plan

        with self.assertRaises(ValueError) as error:
            build_admin_provisioning_plan(
                tenant_slug="kanzlei-notariat",
                domain="kanzlei-notariat.example",
                admin_email="admin@gmail.com",
                admin_display_name="Admin Notariat",
                identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
                identity_domain_id="ocid1.domain.oc1.example",
            )

        self.assertIn("admin_email_domain_mismatch", str(error.exception))

    def test_apply_request_requires_all_apply_gates(self) -> None:
        from nac_identity.oci_tenant import build_admin_provisioning_plan, build_apply_request

        plan = build_admin_provisioning_plan(
            tenant_slug="kanzlei-notariat",
            domain="kanzlei-notariat.example",
            admin_email="admin@kanzlei-notariat.example",
            admin_display_name="Admin Notariat",
            identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
            identity_domain_id="ocid1.domain.oc1.example",
        )

        request = build_apply_request(
            plan,
            dns_verified=False,
            owner_approval_id="",
            audit_event_id="",
            rollback_plan_id="",
        )

        self.assertEqual(request["schema_version"], "nac.oci-identity-apply-request/v0.1")
        self.assertFalse(request["ready_to_apply"])
        self.assertEqual(request["mode"], "review_artifact_only")
        self.assertIn("dns_not_verified", request["blocking_findings"])
        self.assertIn("owner_apply_approval_missing", request["blocking_findings"])
        self.assertIn("audit_event_missing", request["blocking_findings"])
        self.assertIn("rollback_plan_missing", request["blocking_findings"])

    def test_apply_request_ready_artifact_is_secret_free(self) -> None:
        from nac_identity.oci_tenant import build_admin_provisioning_plan, build_apply_request

        plan = build_admin_provisioning_plan(
            tenant_slug="kanzlei-notariat",
            domain="kanzlei-notariat.example",
            admin_email="admin@kanzlei-notariat.example",
            admin_display_name="Admin Notariat",
            identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
            identity_domain_id="ocid1.domain.oc1.example",
        )

        request = build_apply_request(
            plan,
            dns_verified=True,
            owner_approval_id="OWNER-APPROVED-32",
            audit_event_id="AUDIT-32",
            rollback_plan_id="ROLLBACK-32",
        )
        serialized = json.dumps(request, sort_keys=True).lower()

        self.assertTrue(request["ready_to_apply"])
        self.assertEqual(request["blocking_findings"], [])
        self.assertEqual(request["approval"]["owner_approval_id"], "OWNER-APPROVED-32")
        self.assertEqual(request["audit"]["audit_event_id"], "AUDIT-32")
        self.assertEqual(request["rollback"]["rollback_plan_id"], "ROLLBACK-32")
        self.assertFalse(request["productive_write_executed"])
        self.assertIn("users.create", request["planned_writes"])
        self.assertNotIn("secret", serialized)
        self.assertNotIn("token", serialized)
        self.assertNotIn("private_key", serialized)


if __name__ == "__main__":
    unittest.main()
