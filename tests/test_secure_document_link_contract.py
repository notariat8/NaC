from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "secure-document-link.contract.json"


class SecureDocumentLinkContractTests(unittest.TestCase):
    def load_contract(self) -> dict:
        return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_contract_defines_mobile_secure_link_controls(self) -> None:
        payload = self.load_contract()

        self.assertEqual(payload["contract_id"], "workflow.secure_document_link")
        self.assertIn("n8-demonotariat", payload["client_surfaces"])
        self.assertEqual(
            set(payload["storage_targets"]),
            {"onedrive", "sharepoint_document_library", "sharepoint_list_item_attachment"},
        )
        self.assertEqual(
            set(payload["identity_sources"]),
            {"german_eid_bridge", "m365_group_membership", "microsoft_entra_id", "nac_role_gate"},
        )
        self.assertEqual(payload["link_policy"]["secret_link_stored_in_product_repo"], False)
        self.assertEqual(payload["link_policy"]["requires_matter_binding"], True)
        self.assertEqual(payload["link_policy"]["requires_purpose"], True)
        self.assertEqual(payload["link_policy"]["requires_expiry"], True)
        self.assertEqual(payload["link_policy"]["requires_revocation"], True)
        self.assertEqual(payload["link_policy"]["requires_audit_event"], True)
        self.assertEqual(payload["write_flow"][-1], "human_review_before_matter_attachment")

    def test_contract_evidence_schema_requires_minimum_fields(self) -> None:
        payload = self.load_contract()
        required = set(payload["evidence_schema"]["required"])

        self.assertGreaterEqual(
            required,
            {
                "purpose",
                "expires_at",
                "matter_binding",
                "storage_target",
                "revocation",
                "audit_event",
            },
        )

    def test_validator_accepts_contract(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_secure_document_links.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
