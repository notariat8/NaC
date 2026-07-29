from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_business_case_type_production_adapters import (
    validate_domain_contract,
    validate_verification_contract,
)


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeProductionAdaptersContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.domain = json.loads(
            (ROOT / "workflows/contracts/business-case-type-production-adapters-s4f.contract.json").read_text(encoding="utf-8")
        )
        cls.verification = json.loads(
            (ROOT / "workflows/verification-contracts/business-case-type-production-adapters-s4f.verification.json").read_text(encoding="utf-8")
        )

    def test_contracts_pass(self) -> None:
        self.assertEqual([], validate_domain_contract(copy.deepcopy(self.domain)))
        self.assertEqual([], validate_verification_contract(copy.deepcopy(self.verification)))

    def test_readiness_overclaim_is_rejected(self) -> None:
        for key in (
            "productionReadinessClaimed",
            "runtimeCompositionEnabled",
            "liveWriteAuthorized",
        ):
            payload = copy.deepcopy(self.domain)
            payload["offlineCompletion"][key] = True
            self.assertTrue(validate_domain_contract(payload), key)

    def test_local_staging_cannot_gain_completion_authority(self) -> None:
        for key in (
            "centralTruth",
            "canCloseMutation",
            "promotionSupported",
            "centralAcknowledgementSupported",
            "cleanupSupported",
        ):
            payload = copy.deepcopy(self.domain)
            payload["localStagingOutbox"][key] = True
            self.assertTrue(validate_domain_contract(payload), key)

    def test_required_blockers_cannot_be_removed(self) -> None:
        for blocker in (
            "central_postgresql_outbox_promotion_ack_retention_cleanup",
            "production_identity_inspection_readback",
            "azure_blob_worm_policy_lock",
            "broker_product_owner_decision",
            "synced_filesystem_runtime_detection",
            "signature_anchor_owner_decision",
        ):
            payload = copy.deepcopy(self.domain)
            payload["remainingBlockersExact"].remove(blocker)
            self.assertTrue(validate_domain_contract(payload), blocker)

    def test_verification_thresholds_and_failure_mode_fail_closed(self) -> None:
        payload = copy.deepcopy(self.verification)
        payload["thresholds"]["tenantWrites"] = 1
        self.assertTrue(validate_verification_contract(payload))
        payload = copy.deepcopy(self.verification)
        payload["failureBehavior"]["mergeAllowed"] = True
        self.assertTrue(validate_verification_contract(payload))


if __name__ == "__main__":
    unittest.main()
