from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from notary_kg.business_case_type_immutable_evidence import (  # noqa: E402
    build_synthetic_evidence_dry_run,
)


class BusinessCaseTypeImmutableEvidenceTests(unittest.TestCase):
    def test_synthetic_dry_run_is_complete_but_keeps_live_blocked(self) -> None:
        output = build_synthetic_evidence_dry_run()

        self.assertEqual(output["status"], "S6_OFFLINE_FOUNDATION")
        self.assertEqual(output["live_status"], "BLOCKED_PENDING_S7_APPROVAL")
        self.assertTrue(output["normal_chain"]["complete"])
        self.assertTrue(output["reconciliation_chain"]["complete"])
        self.assertTrue(output["reconciliation_store_clear"])
        for field in (
            "network_calls",
            "provider_calls",
            "tenant_calls",
            "tenant_writes",
            "credential_reads",
            "live_mutations",
        ):
            self.assertEqual(output[field], 0)
        self.assertEqual(output["credential_reads"], 0)
        self.assertFalse(output["production_worm_claim"])

    def test_synthetic_output_contains_no_raw_identity_or_secret_material(self) -> None:
        serialized = json.dumps(build_synthetic_evidence_dry_run(), sort_keys=True)

        for forbidden in (
            "00000000-0000-4000-8000-000000000001",
            "11111111-1111-4111-8111-111111111111",
            "22222222-2222-4222-8222-222222222222",
            "33333333-3333-4333-8333-333333333333",
            "client_secret",
            "private_key",
            "access_token",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
