from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_business_case_type_graph_write_composition import (
    validate_domain_contract,
    validate_verification_contract,
)


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeGraphWriteCompositionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.domain = json.loads(
            (
                ROOT
                / "workflows/contracts/business-case-type-graph-write-composition-s4c.contract.json"
            ).read_text(encoding="utf-8")
        )
        cls.verification = json.loads(
            (
                ROOT
                / "workflows/verification-contracts/business-case-type-graph-write-composition-s4c.verification.json"
            ).read_text(encoding="utf-8")
        )

    def test_contracts_pass_validator(self) -> None:
        self.assertEqual([], validate_domain_contract(copy.deepcopy(self.domain)))
        self.assertEqual(
            [],
            validate_verification_contract(copy.deepcopy(self.verification)),
        )

    def test_local_durability_envelope_drift_is_rejected(self) -> None:
        for key, value in (
            ("journalModeExact", "WAL"),
            ("synchronousModeExact", "NORMAL"),
            ("networkOrSyncedFilesystemAllowed", True),
            ("powerKernelHardwareOrHostLossDurabilityClaimed", True),
            ("requiredFileModeOctal", "0644"),
        ):
            payload = copy.deepcopy(self.domain)
            payload["stateStore"][key] = value
            self.assertTrue(validate_domain_contract(payload), key)

    def test_transition_matrix_drift_is_rejected(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["stateStore"]["transitionsExact"].remove(
            "required_open_non_closing_readback_event_only"
        )
        self.assertTrue(validate_domain_contract(payload))

    def test_transport_boundary_drift_is_rejected(self) -> None:
        for key, value in (
            ("baseUrlExact", "https://graph.microsoft.com/beta"),
            ("redirectsAllowed", True),
            ("automaticRetries", 1),
            ("collectionPathsBoundAtConstruction", 1),
            ("planShaVerifiedByTransport", True),
        ):
            payload = copy.deepcopy(self.domain)
            payload["transport"][key] = value
            self.assertTrue(validate_domain_contract(payload), key)

    def test_credential_counter_semantics_cannot_collapse(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["credentialBoundary"].pop(
            "syntheticTokenProviderCallsReportedSeparately"
        )
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["credentialBoundary"]["externalCredentialStoreReads"] = 1
        self.assertTrue(validate_domain_contract(payload))

    def test_offline_completion_threshold_drift_is_rejected(self) -> None:
        for key in (
            "socketOrDnsCallsExact",
            "externalCredentialStoreReadsExact",
            "liveGraphCallsExact",
            "tenantWritesExact",
        ):
            payload = copy.deepcopy(self.domain)
            payload["offlineCompletion"][key] = 1
            self.assertTrue(validate_domain_contract(payload), key)

    def test_security_sections_and_cas_fields_are_required(self) -> None:
        for section in ("redaction", "crashRecovery", "outOfScopeExact"):
            payload = copy.deepcopy(self.domain)
            payload.pop(section)
            self.assertTrue(validate_domain_contract(payload), section)

        for section, key in (
            ("stateStore", "compareAndSwapFieldsExact"),
            ("transport", "allowedResponseHeadersExact"),
            ("credentialBoundary", "providerErrorTextPersistedOrReturned"),
        ):
            payload = copy.deepcopy(self.domain)
            payload[section].pop(key)
            self.assertTrue(validate_domain_contract(payload), f"{section}.{key}")

    def test_verification_threshold_drift_is_rejected(self) -> None:
        payload = copy.deepcopy(self.verification)
        payload["thresholds"]["externalCredentialStoreReads"] = 1
        self.assertTrue(validate_verification_contract(payload))

    def test_domain_identity_and_inheritance_drift_is_rejected(self) -> None:
        for key in ("title", "issue", "extendsContract"):
            payload = copy.deepcopy(self.domain)
            payload[key] = "drifted"
            self.assertTrue(validate_domain_contract(payload), key)

    def test_verification_governance_sections_are_exact(self) -> None:
        for key in (
            "schemaVersion",
            "appliesWhen",
            "requiredContext",
            "requiredEvidence",
            "invariants",
        ):
            payload = copy.deepcopy(self.verification)
            payload.pop(key)
            self.assertTrue(validate_verification_contract(payload), key)

    def test_verification_pass_and_failure_behavior_are_exact(self) -> None:
        for section, key, value in (
            ("passCondition", "allChecksPass", False),
            ("failureBehavior", "mode", "warn"),
            ("failureBehavior", "mergeAllowed", True),
        ):
            payload = copy.deepcopy(self.verification)
            payload[section][key] = value
            self.assertTrue(
                validate_verification_contract(payload),
                f"{section}.{key}",
            )


if __name__ == "__main__":
    unittest.main()
