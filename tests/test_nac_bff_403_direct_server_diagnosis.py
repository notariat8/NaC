"""Offline, synthetic Stage A checks for the Issue #756 server diagnosis."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import unittest

from nac_bff.bff_403_direct_server_diagnosis import (
    StageAReadBlocked,
    StageAReadGate,
    create_production_read_gate,
    evaluate_stage_a_evidence,
)
from scripts.validate_m365_bff_403_direct_server_diagnosis import (
    CONTRACT_PATH,
    validate_contract,
)
from scripts import validate_m365_bff_403_direct_server_diagnosis as validator


def _digest(label: str) -> str:
    return hashlib.sha256(f"synthetic:{label}".encode("ascii")).hexdigest()


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _synthetic_read_contract() -> dict:
    value = deepcopy(_contract())
    value["status"] = "SYNTHETIC_TEST_ONLY"
    for key in value["target"]:
        if key != "workspace_class":
            value["target"][key] = _digest(key)
    for resource in value["resources"]:
        resource["endpoint_binding_sha256"] = _digest(resource["id"])
        resource["maximum_reads"] = 1
        if resource["id"] == "azure_function_request_log":
            resource["query_sha256"] = _digest("query")
    value["gates"]["provider_read_authorized"] = True
    value["gates"]["credential_access_authorized"] = True
    value["gates"]["no_refresh_capability_proven"] = True
    value["gates"]["maximum_provider_reads"] = 3
    return value


class StageAContractTests(unittest.TestCase):
    def test_repository_contract_is_closed_and_inactive(self) -> None:
        self.assertEqual(validate_contract(_contract()), [])
        self.assertFalse(_contract()["gates"]["provider_read_authorized"])
        self.assertEqual(_contract()["gates"]["maximum_provider_reads"], 0)

    def test_contract_rejects_extra_fields_raw_target_and_enabled_gate(self) -> None:
        for mutate in (
            lambda c: c.update({"free_form_query": "synthetic"}),
            lambda c: c["target"].update({"tenant_binding_sha256": "tenant:real"}),
            lambda c: c["resources"][2].update({"maximum_reads": 1}),
            lambda c: c["gates"].update({"provider_read_authorized": True}),
            lambda c: c["gates"].update({"provider_read_authorized": 0}),
            lambda c: c["gates"].update({"maximum_provider_reads": False}),
            lambda c: c["resources"][2].update({"maximum_reads": 0.0}),
        ):
            with self.subTest(mutate=mutate):
                value = deepcopy(_contract())
                mutate(value)
                self.assertTrue(validate_contract(value))

    def test_workspace_and_dpa_evidence_must_remain_unbound(self) -> None:
        contract = _contract()
        self.assertEqual(contract["target"]["workspace_binding_sha256"], "UNBOUND")
        self.assertEqual(contract["target"]["avv_dpa_binding_sha256"], "UNBOUND")
        for field in ("workspace_binding_sha256", "avv_dpa_binding_sha256"):
            changed = deepcopy(contract)
            changed["target"][field] = _digest(field)
            self.assertTrue(validate_contract(changed))

    def test_synthetic_projection_cannot_be_widened(self) -> None:
        widened = _synthetic_read_contract()
        widened["resources"][2]["projection"].append("raw_user")
        with self.assertRaises(StageAReadBlocked):
            StageAReadGate(widened)

    def test_owner_solo_cannot_impersonate_four_eyes_or_ignore_cited_duty(self) -> None:
        for field, value in (
            ("same_principal_accounts_are_distinct_approvers", True),
            ("solo_four_eyes_satisfied", True),
            ("uncited_two_person_duty", "OWNER_SOLO_APPROVAL"),
            ("cited_two_person_duty_with_one_principal", "OWNER_SOLO_APPROVAL"),
        ):
            with self.subTest(field=field):
                contract = _contract()
                contract["approval_boundary"][field] = value
                self.assertTrue(validate_contract(contract))

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            json.loads('{"status":"LOCAL_INACTIVE_ONLY","status":"SYNTHETIC_TEST_ONLY"}',
                       object_pairs_hook=validator._unique_pairs)

    def test_production_gate_blocks_before_any_factory(self) -> None:
        calls: list[str] = []

        def credential() -> object:
            calls.append("credential")
            raise AssertionError("credential factory must not run")

        def transport() -> object:
            calls.append("transport")
            raise AssertionError("transport factory must not run")

        with self.assertRaises(StageAReadBlocked) as caught:
            create_production_read_gate(
                credential_provider=credential, transport_provider=transport
            )
        self.assertEqual(caught.exception.code, "BLOCKED_NO_REFRESH_CAPABILITY")
        self.assertEqual(calls, [])


class StageAReadGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = _synthetic_read_contract()
        self.gate = StageAReadGate(self.contract)

    def reserve(self, operation: str = "azure_function_metadata", **overrides: object) -> None:
        resource = next(
            (item for item in self.contract["resources"] if item["id"] == operation),
            None,
        )
        arguments = {
            "operation_id": operation,
            "current_target": deepcopy(self.contract["target"]),
            "endpoint_bytes": f"synthetic:{operation}".encode("ascii"),
            "query_bytes": b"synthetic:query" if operation == "azure_function_request_log" else None,
            "method": "GET",
            "no_refresh_proven": True,
            "redirect": False,
            "retry": False,
            "paging": False,
            "body": False,
            "resource_discovery": False,
        }
        arguments.update(overrides)
        self.gate.reserve(**arguments)

    def test_exact_reads_consume_individual_budgets_once(self) -> None:
        self.reserve()
        self.reserve("application_insights_metadata")
        self.reserve("azure_function_request_log")
        with self.assertRaises(StageAReadBlocked):
            self.reserve("azure_function_request_log")

    def test_each_read_rechecks_target_and_no_refresh(self) -> None:
        self.reserve()
        drift = deepcopy(self.contract["target"])
        drift["tenant_binding_sha256"] = _digest("other-tenant")
        with self.assertRaises(StageAReadBlocked):
            self.reserve("application_insights_metadata", current_target=drift)
        with self.assertRaises(StageAReadBlocked):
            self.reserve("application_insights_metadata", no_refresh_proven=False)
        self.reserve("application_insights_metadata")

    def test_query_endpoint_method_and_transport_flags_fail_closed(self) -> None:
        invalid = (
            {"method": "POST"},
            {"redirect": True},
            {"retry": True},
            {"paging": True},
            {"body": True},
            {"resource_discovery": True},
            {"endpoint_bytes": b"synthetic:other-endpoint"},
            {"query_bytes": b"synthetic:other-query"},
        )
        for change in invalid:
            with self.subTest(change=change):
                with self.assertRaises(StageAReadBlocked):
                    self.reserve("azure_function_request_log", **change)
        self.reserve("azure_function_request_log")

    def test_extra_operation_and_disabled_gate_fail_closed(self) -> None:
        with self.assertRaises(StageAReadBlocked):
            self.reserve(operation="free_form_search")
        disabled = deepcopy(self.contract)
        disabled["gates"]["provider_read_authorized"] = False
        with self.assertRaises(StageAReadBlocked):
            StageAReadGate(disabled).reserve(
                operation_id="azure_function_metadata",
                current_target=deepcopy(disabled["target"]),
                endpoint_bytes=b"synthetic:azure_function_metadata",
                query_bytes=None,
                method="GET",
                no_refresh_proven=True,
                redirect=False,
                retry=False,
                paging=False,
                body=False,
                resource_discovery=False,
            )

    def test_budget_is_atomic_for_concurrent_reservations(self) -> None:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.reserve) for _ in range(2)]
        outcomes = [future.exception() for future in futures]
        self.assertEqual(sum(value is None for value in outcomes), 1)
        self.assertEqual(sum(isinstance(value, StageAReadBlocked) for value in outcomes), 1)


class StageAEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.function = {"deployment_class": "deployed", "configuration_digest": _digest("configuration")}
        self.insights = {"capture_enabled": True, "retention_covers_window": True}
        self.log = {
            "request_observed": True,
            "http_class": "403",
            "request_correlation_binding_sha256": _digest("receipt"),
        }

    def evaluate(self, **overrides: object) -> str:
        arguments = {
            "function_metadata": self.function,
            "insights_metadata": self.insights,
            "request_log": self.log,
            "expected_receipt_binding_sha256": _digest("receipt"),
            "target_binding_verified": True,
            "metadata_authoritative": True,
            "receipt_provenance_verified": True,
            "unique_correlation_verified": True,
        }
        arguments.update(overrides)
        return evaluate_stage_a_evidence(**arguments)

    def test_proven_non_deployment_is_distinct_from_ambiguous_404(self) -> None:
        function = {"deployment_class": "not_deployed", "configuration_digest": _digest("configuration")}
        empty = {"request_observed": False, "http_class": "none", "request_correlation_binding_sha256": _digest("receipt")}
        self.assertEqual(self.evaluate(function_metadata=function, request_log=empty), "BFF_NOT_DEPLOYED")
        self.assertEqual(self.evaluate(function_metadata=function, request_log=empty, metadata_authoritative=False), "UNPROVEN")
        self.assertEqual(self.evaluate(function_metadata=function), "UNPROVEN")

    def test_correlation_proves_status_only_not_denial_cause(self) -> None:
        self.assertEqual(self.evaluate(), "REQUEST_ATTRIBUTED_STATUS_ONLY")
        self.assertEqual(self.evaluate(receipt_provenance_verified=False), "UNPROVEN")
        self.assertEqual(self.evaluate(unique_correlation_verified=False), "UNPROVEN")
        self.assertEqual(self.evaluate(expected_receipt_binding_sha256=_digest("other")), "UNPROVEN")
        self.assertEqual(self.evaluate(metadata_authoritative=False), "UNPROVEN")

    def test_empty_or_expired_logs_remain_unproven(self) -> None:
        empty = {"request_observed": False, "http_class": "none", "request_correlation_binding_sha256": _digest("receipt")}
        self.assertEqual(self.evaluate(request_log=empty), "UNPROVEN")
        self.assertEqual(self.evaluate(insights_metadata={"capture_enabled": True, "retention_covers_window": False}), "UNPROVEN")
        self.assertEqual(self.evaluate(target_binding_verified=False), "UNPROVEN")

    def test_unredactable_fields_block_instead_of_leaking(self) -> None:
        with self.assertRaises(StageAReadBlocked):
            self.evaluate(request_log={**self.log, "raw_user": "synthetic"})
        with self.assertRaises(StageAReadBlocked):
            self.evaluate(function_metadata={**self.function, "url": "https://example.com"})


if __name__ == "__main__":
    unittest.main()
