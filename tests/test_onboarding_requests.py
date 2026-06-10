from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class OnboardingRequestTests(unittest.TestCase):
    def test_build_onboarding_request_creates_stable_non_secret_id(self) -> None:
        from nac_identity.onboarding_requests import build_onboarding_request

        request = build_onboarding_request(
            domain="MYJUR.DE",
            tenant_slug="MyJur",
            admin_email="OFunk@MyJur.DE",
            dns_status="verified",
            now="2026-06-10T00:00:00Z",
        )
        serialized = json.dumps(request, sort_keys=True).lower()

        self.assertEqual(request["schema_version"], "nac.onboarding-request/v0.1")
        self.assertEqual(request["request_id"], "onr_myjur_20260610_000000")
        self.assertEqual(request["domain"], "myjur.de")
        self.assertEqual(request["tenant_slug"], "myjur")
        self.assertEqual(request["admin_email"], "ofunk@myjur.de")
        self.assertEqual(request["dns_status"], "verified")
        self.assertEqual(request["request_status"], "submitted")
        self.assertEqual(request["invitation_status"], "not_sent")
        self.assertEqual(request["created_by_surface"], "app.notariat8.de")
        self.assertNotIn("ofunk", request["request_id"])
        self.assertNotIn("@", request["request_id"])
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("private_key", serialized)

    def test_build_onboarding_request_rejects_unready_dns_status(self) -> None:
        from nac_identity.onboarding_requests import build_onboarding_request

        with self.assertRaises(ValueError) as ctx:
            build_onboarding_request(
                domain="myjur.de",
                tenant_slug="myjur",
                admin_email="ofunk@myjur.de",
                dns_status="pending",
                now="2026-06-10T00:00:00Z",
            )

        self.assertIn("dns_status_not_verified", str(ctx.exception))

    def test_disabled_store_fails_closed_without_writing(self) -> None:
        from nac_identity.onboarding_requests import DisabledOnboardingRequestStore, OnboardingRequestStoreDisabled

        store = DisabledOnboardingRequestStore()

        with self.assertRaises(OnboardingRequestStoreDisabled):
            store.create_request({"request_id": "onr_myjur_20260610_000000"})
        with self.assertRaises(OnboardingRequestStoreDisabled):
            store.get_request("onr_myjur_20260610_000000")
        with self.assertRaises(OnboardingRequestStoreDisabled):
            store.list_requests()


if __name__ == "__main__":
    unittest.main()
