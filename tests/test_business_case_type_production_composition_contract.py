from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_business_case_type_production_composition import (
    validate_domain_contract,
    validate_verification_contract,
)


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeProductionCompositionContractTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.domain = json.loads(
            (
                ROOT
                / "workflows/contracts/"
                "business-case-type-production-composition-s4g.contract.json"
            ).read_text(encoding="utf-8")
        )
        cls.verification = json.loads(
            (
                ROOT
                / "workflows/verification-contracts/"
                "business-case-type-production-composition-s4g."
                "verification.json"
            ).read_text(encoding="utf-8")
        )

    def test_contracts_pass(self) -> None:
        self.assertEqual(
            [],
            validate_domain_contract(copy.deepcopy(self.domain)),
        )
        self.assertEqual(
            [],
            validate_verification_contract(
                copy.deepcopy(self.verification)
            ),
        )

    def test_validator_is_registered_in_strict_quality_gate(self) -> None:
        quality_gate = (ROOT / "scripts/quality_gate.py").read_text()
        self.assertIn(
            "validate_business_case_type_production_composition.py",
            quality_gate,
        )

    def test_status_or_readiness_overclaim_is_rejected(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["liveStatus"] = "LIVE_READY"
        self.assertTrue(validate_domain_contract(payload))

        for key in (
            "productionReadinessClaimed",
            "productionDurabilityClaimed",
            "runtimeFactoryConstructed",
            "liveWriteAuthorized",
        ):
            payload = copy.deepcopy(self.domain)
            payload["offlineCompletion"][key] = True
            self.assertTrue(validate_domain_contract(payload), key)

    def test_identity_identifier_conflation_is_rejected(self) -> None:
        for key in (
            "applicationIdsPairwiseDistinctRequired",
            "servicePrincipalObjectIdsPairwiseDistinctRequired",
            "applicationIdAndObjectIdNamespacesSeparateRequired",
            "principalBindingsSha256Required",
        ):
            payload = copy.deepcopy(self.domain)
            payload["identityInspector"][key] = False
            self.assertTrue(validate_domain_contract(payload), key)

    def test_identity_permissions_cannot_be_broadened(self) -> None:
        cases = (
            ("writerGraphApplicationRolesExact", ["Sites.ReadWrite.All"]),
            ("writerSiteRolesExact", ["fullcontrol"]),
            ("bffGraphApplicationRolesExact", ["Sites.Read.All"]),
            ("bffSiteRolesExact", ["write"]),
        )
        for key, value in cases:
            payload = copy.deepcopy(self.domain)
            payload["identityInspector"][key] = value
            self.assertTrue(validate_domain_contract(payload), key)

    def test_sqlite_paths_cannot_converge_or_gain_authority(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["localSqliteLayout"]["evidenceDatabaseNameExact"] = (
            payload["localSqliteLayout"]["mutationDatabaseNameExact"]
        )
        self.assertTrue(validate_domain_contract(payload))

        for key in (
            "sameDatabaseFileAllowed",
            "syncedRootAllowed",
            "remoteFilesystemAllowed",
            "centralTruth",
            "canCloseMutation",
        ):
            payload = copy.deepcopy(self.domain)
            payload["localSqliteLayout"][key] = True
            self.assertTrue(validate_domain_contract(payload), key)

    def test_azure_transport_cannot_gain_lock_or_broader_io(self) -> None:
        cases = (
            ("methodsExact", ["GET", "PUT", "DELETE"]),
            ("foreignHostsAllowed", True),
            ("redirectsAllowed", True),
            ("automaticRetries", 1),
            ("policyMutationAllowed", True),
            ("irreversibleLockOperationAllowed", True),
            ("deleteOperationAllowed", True),
        )
        for key, value in cases:
            payload = copy.deepcopy(self.domain)
            payload["azureWormRestTransport"][key] = value
            self.assertTrue(validate_domain_contract(payload), key)

    def test_every_central_blocker_is_required(self) -> None:
        for blocker in self.domain["remainingBlockersExact"]:
            payload = copy.deepcopy(self.domain)
            payload["remainingBlockersExact"].remove(blocker)
            self.assertTrue(validate_domain_contract(payload), blocker)

    def test_verification_stays_zero_activity_and_fail_closed(self) -> None:
        payload = copy.deepcopy(self.verification)
        payload["thresholds"]["azureCalls"] = 1
        self.assertTrue(validate_verification_contract(payload))

        payload = copy.deepcopy(self.verification)
        payload["failureBehavior"]["runtimeConstructionAllowed"] = True
        self.assertTrue(validate_verification_contract(payload))


if __name__ == "__main__":
    unittest.main()
