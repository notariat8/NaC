from __future__ import annotations

import copy
import json
import unittest
from types import SimpleNamespace
from unittest import mock
from pathlib import Path

from scripts.validate_business_case_type_graph_read_edge import (
    validate_adapter_behavior,
    validate_domain_contract,
    validate_verification_contract,
)

from nac_m365_graph import business_case_type_registry as registry


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeGraphReadEdgeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.domain = json.loads((ROOT / "workflows/contracts/business-case-type-graph-read-edge.contract.json").read_text(encoding="utf-8"))
        cls.verification = json.loads((ROOT / "workflows/verification-contracts/business-case-type-graph-read-edge.verification.json").read_text(encoding="utf-8"))

    def test_approved_contracts_pass_validator_functions(self):
        self.assertEqual([], validate_domain_contract(copy.deepcopy(self.domain)))
        self.assertEqual([], validate_verification_contract(copy.deepcopy(self.verification)))

    def assert_domain_mutation_rejected(self, mutate):
        payload = copy.deepcopy(self.domain)
        mutate(payload)
        self.assertTrue(validate_domain_contract(payload))

    def test_permission_mutation_is_rejected(self):
        self.assert_domain_mutation_rejected(
            lambda payload: payload["authorization"].update(allowed_runtime_permissions_exact=["Sites.Read.All"])
        )

    def test_site_grant_mutation_is_rejected(self):
        self.assert_domain_mutation_rejected(
            lambda payload: payload["binding"].update(site_grant_role_exact="write")
        )

    def test_same_filter_paging_mutation_is_rejected(self):
        self.assert_domain_mutation_rejected(
            lambda payload: payload["paging"].update(next_link_same_catalog_version_filter_required=False)
        )

    def test_cli_path_mutation_is_rejected(self):
        self.assert_domain_mutation_rejected(
            lambda payload: payload["offline_cli"].update(command="nac m365 business-case-type-read-plan")
        )

    def test_live_call_mutation_is_rejected(self):
        self.assert_domain_mutation_rejected(
            lambda payload: payload["offline_cli"].update(live_calls_allowed=1)
        )

    def test_acceptance_criterion_drift_is_rejected(self):
        self.assert_domain_mutation_rejected(
            lambda payload: payload["acceptance_criteria"][3].update(requirement="Sites.Selected is preferred.")
        )

    def test_verification_live_call_mutation_is_rejected(self):
        payload = copy.deepcopy(self.verification)
        payload["thresholds"]["allowed_live_graph_calls"] = 1
        self.assertTrue(validate_verification_contract(payload))

    def test_runtime_behavior_baseline_passes(self):
        self.assertEqual([], validate_adapter_behavior())

    def test_runtime_filter_mutation_is_rejected(self):
        with mock.patch.object(registry, "_filter_expression", return_value="fields/BusinessCaseTypeId eq 'other'"):
            errors = validate_adapter_behavior()
        self.assertTrue(any("projection/filter" in error for error in errors))

    def test_runtime_pretransport_mutation_is_rejected(self):
        with mock.patch.object(registry.GraphBusinessCaseTypeRegistryReadAdapter, "_request_is_allowed", return_value=True):
            errors = validate_adapter_behavior()
        self.assertTrue(any("pretransport" in error for error in errors))

    def test_runtime_nextlink_filter_mutation_is_rejected(self):
        def accept_next_link(next_link, _collection_path, _filter_expression):
            return next_link, "/sites/site-validator/lists/list-validator/items?$skiptoken=unsafe"

        with mock.patch.object(registry, "_validated_next_link", side_effect=accept_next_link):
            errors = validate_adapter_behavior()
        self.assertTrue(any("same-filter drift" in error for error in errors))

    def test_runtime_local_etag_mutation_is_rejected(self):
        with mock.patch.object(
            registry.RegistryFetchResult,
            "not_modified",
            return_value=registry.RegistryFetchResult.unavailable(),
        ):
            errors = validate_adapter_behavior()
        self.assertTrue(any("local ETag" in error for error in errors))

    def test_runtime_redaction_mutation_is_rejected(self):
        with mock.patch.object(registry, "_http_reason_code", return_value="sensitive token path body"):
            errors = validate_adapter_behavior()
        self.assertTrue(any("redacted transport" in error for error in errors))

    def test_offline_cli_matrix_mutation_is_rejected(self):
        mutated_plan = SimpleNamespace(
            build_business_case_type_read_plan=lambda *_args, **_kwargs: {"status": "PASSED", "method": "POST"}
        )
        errors = validate_adapter_behavior(plan_module=mutated_plan)
        self.assertTrue(any("offline CLI" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
