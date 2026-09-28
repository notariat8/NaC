"""Synthetic, offline-first tests for the inactive Issue #756 operator read."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import unittest
from unittest.mock import patch

from nac_bff.bff_403_operator_read import (
    OperatorReadBlocked,
    classify_function_metadata,
    classify_historical_summary,
    compile_request,
    create_production_operator_read,
    select_insights_component,
    validate_component_projection,
    validate_workspace_projection,
)
from scripts.validate_m365_bff_403_operator_read import CONTRACT_PATH, validate_contract


SUBSCRIPTION = "00000000-0000-4000-8000-000000000001"
APP_ID = "00000000-0000-4000-8000-000000000002"
COMPONENT = "appi-nac-bff-test-synthetic"
WORKSPACE = (
    "/subscriptions/00000000-0000-4000-8000-000000000001/"
    "resourceGroups/rg-nac-bff-test/providers/Microsoft.OperationalInsights/"
    "workspaces/log-nac-bff-test-synthetic"
)


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _bindings() -> dict[str, str]:
    return {
        "subscription": SUBSCRIPTION,
        "component": COMPONENT,
        "app_id": APP_ID,
        "workspace": WORKSPACE,
    }


class ContractTests(unittest.TestCase):
    def test_checked_in_contract_is_inactive_and_v1_is_separate(self) -> None:
        contract = _contract()
        self.assertEqual(validate_contract(contract), [])
        self.assertEqual(contract["status"], "LOCAL_INACTIVE_ONLY")
        self.assertEqual([r["maximum_reads"] for r in contract["resources"]], [0] * 5)
        self.assertFalse(contract["gates"]["provider_read_authorized"])
        self.assertEqual(contract["gates"]["maximum_provider_reads"], 0)

    def test_contract_rejects_scope_widening_and_gate_activation(self) -> None:
        mutations = (
            lambda c: c["resources"][0].update({"method": "POST"}),
            lambda c: c["resources"][1].update({"top": 100}),
            lambda c: c["resources"][2]["projection"].append("ConnectionString"),
            lambda c: c["resources"][4]["query_lines"].append("| take 100"),
            lambda c: c["resources"][4].update({"maximum_reads": 1}),
            lambda c: c["read_policy"].update({"redirect_allowed": True}),
            lambda c: c["read_policy"].update({"pre_get_component_projection_required": False}),
            lambda c: c["gates"].update({"provider_read_authorized": True}),
            lambda c: c["gates"].update({"maximum_provider_reads": False}),
            lambda c: c["target"].update({"permission_binding_sha256": "synthetic"}),
            lambda c: c["approval_boundary"].update({"solo_four_eyes_satisfied": True}),
            lambda c: c["approval_boundary"].update({"cited_two_person_duty_with_one_principal": "OWNER_SOLO_APPROVAL"}),
            lambda c: c.update({"free_url": "https://example.com"}),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                contract = deepcopy(_contract())
                mutate(contract)
                self.assertTrue(validate_contract(contract))

    def test_semantic_guard_survives_a_recomputed_contract_checksum(self) -> None:
        for change in (
            lambda c: c["resources"][0].update({"host": "example.com"}),
            lambda c: c["resources"][4].update({"maximum_reads": 1}),
            lambda c: c["gates"].update({"provider_read_authorized": True}),
            lambda c: c["approval_boundary"].update({"solo_four_eyes_satisfied": True}),
        ):
            with self.subTest(change=change):
                contract = deepcopy(_contract())
                change(contract)
                digest = hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
                with patch("nac_bff.bff_403_operator_read._CONTRACT_SHA256", digest):
                    self.assertTrue(validate_contract(contract))

    def test_production_factory_blocks_before_credential_or_transport(self) -> None:
        calls: list[str] = []

        def credential() -> object:
            calls.append("credential")
            raise AssertionError("must not run")

        def transport() -> object:
            calls.append("transport")
            raise AssertionError("must not run")

        with self.assertRaises(OperatorReadBlocked) as caught:
            create_production_operator_read(credential, transport)
        self.assertEqual(caught.exception.code, "BLOCKED_NO_REFRESH_CAPABILITY")
        self.assertEqual(calls, [])


class RequestCompilerTests(unittest.TestCase):
    def test_closed_requests_are_deterministic_and_get_only(self) -> None:
        bindings = _bindings()
        function_uri, function_query = compile_request("azure_function_metadata", bindings)
        self.assertEqual(function_query, None)
        self.assertEqual(
            function_uri.decode("ascii"),
            "https://management.azure.com/subscriptions/" + SUBSCRIPTION
            + "/resourceGroups/rg-nac-bff-test/providers/Microsoft.Web/sites/"
            "func-nac-bff-test-funktion8?api-version=2025-03-01",
        )
        discovery_uri, _ = compile_request("insights_component_discovery", bindings)
        self.assertIn(b"$top=2", discovery_uri)
        self.assertIn(b"resourceType%20eq%20", discovery_uri)
        self.assertNotIn(b" ", discovery_uri)
        component_uri, _ = compile_request("insights_component_metadata", bindings)
        self.assertIn(COMPONENT.encode("ascii"), component_uri)
        workspace_uri, _ = compile_request("log_analytics_workspace_metadata", bindings)
        self.assertIn(WORKSPACE.encode("ascii"), workspace_uri)
        log_uri, query = compile_request("historical_request_summary", bindings)
        self.assertIsNotNone(query)
        self.assertEqual(hashlib.sha256(query).hexdigest(), hashlib.sha256(
            "\n".join(_contract()["resources"][4]["query_lines"]).encode("utf-8")
        ).hexdigest())
        self.assertIn(b"/v1/apps/" + APP_ID.encode("ascii") + b"/query?query=", log_uri)
        self.assertNotIn(b" ", log_uri)

    def test_no_free_url_wrong_scope_or_query_injection(self) -> None:
        for operation, change in (
            ("azure_function_metadata", {"subscription": "../other"}),
            ("insights_component_metadata", {"component": "other-app"}),
            ("insights_component_metadata", {"component": COMPONENT + "?x=1"}),
            ("log_analytics_workspace_metadata", {"workspace": WORKSPACE + "?x=1"}),
            ("log_analytics_workspace_metadata", {"workspace": WORKSPACE.replace(SUBSCRIPTION, APP_ID)}),
            ("historical_request_summary", {"app_id": "not-a-uuid"}),
        ):
            with self.subTest(operation=operation, change=change):
                with self.assertRaises(OperatorReadBlocked):
                    compile_request(operation, {**_bindings(), **change})
        with self.assertRaises(OperatorReadBlocked):
            compile_request("free_search", _bindings())
        with self.assertRaises(OperatorReadBlocked):
            compile_request("azure_function_metadata", {**_bindings(), "url": "https://example.com"})


class EvidenceTests(unittest.TestCase):
    def test_function_404_requires_exact_scope_and_right(self) -> None:
        self.assertEqual(classify_function_metadata(404, None, target_proven=True, read_right_proven=True), "BFF_NOT_DEPLOYED")
        self.assertEqual(classify_function_metadata(404, None, target_proven=False, read_right_proven=True), "UNPROVEN")
        self.assertEqual(classify_function_metadata(404, None, target_proven=True, read_right_proven=False), "UNPROVEN")
        for status in (401, 403, 500):
            self.assertEqual(classify_function_metadata(status, None, target_proven=True, read_right_proven=True), "UNPROVEN")
        with self.assertRaises(OperatorReadBlocked):
            classify_function_metadata(200, {"id": "synthetic", "ConnectionString": "synthetic"}, target_proven=True, read_right_proven=True)

    def test_discovery_requires_one_exact_component_without_paging(self) -> None:
        resource = {"id": "/subscriptions/" + SUBSCRIPTION + "/resourceGroups/rg-nac-bff-test/providers/Microsoft.Insights/components/" + COMPONENT,
                    "type": "Microsoft.Insights/components", "name": COMPONENT}
        self.assertEqual(select_insights_component({"value": [resource]}, SUBSCRIPTION), COMPONENT)
        for projected in ({"value": []}, {"value": [resource, resource]},
                          {"value": [resource], "nextLink": "synthetic"},
                          {"value": [{**resource, "name": "other"}]},
                          {"value": [{**resource, "raw_user": "synthetic"}]}):
            with self.subTest(projected=projected):
                with self.assertRaises(OperatorReadBlocked):
                    select_insights_component(projected, SUBSCRIPTION)

    def test_component_and_workspace_require_proofs_and_closed_fields(self) -> None:
        component = {"id": "/subscriptions/" + SUBSCRIPTION + "/resourceGroups/rg-nac-bff-test/providers/Microsoft.Insights/components/" + COMPONENT, "properties.AppId": APP_ID,
                     "properties.IngestionMode": "LogAnalytics", "properties.WorkspaceResourceId": WORKSPACE,
                     "properties.RetentionInDays": 90, "properties.SamplingPercentage": 100,
                     "properties.provisioningState": "Succeeded"}
        expected_id = component["id"]
        with self.assertRaises(OperatorReadBlocked):
            validate_component_projection(component, expected_component_id=expected_id, pre_get_projection_proven=False, link_proven=True)
        with self.assertRaises(OperatorReadBlocked):
            validate_component_projection(component, expected_component_id=expected_id, pre_get_projection_proven=True, link_proven=False)
        with self.assertRaises(OperatorReadBlocked):
            validate_component_projection({**component, "ConnectionString": "synthetic"}, expected_component_id=expected_id, pre_get_projection_proven=True, link_proven=True)
        self.assertEqual(validate_component_projection(component, expected_component_id=expected_id, pre_get_projection_proven=True, link_proven=True), APP_ID)
        with self.assertRaises(OperatorReadBlocked):
            validate_component_projection({**component, "properties.WorkspaceResourceId": WORKSPACE.replace(SUBSCRIPTION, APP_ID)}, expected_component_id=expected_id, pre_get_projection_proven=True, link_proven=True)
        with self.assertRaises(OperatorReadBlocked):
            validate_component_projection({**component, "id": "synthetic"}, expected_component_id=expected_id, pre_get_projection_proven=True, link_proven=True)
        with self.assertRaises(OperatorReadBlocked):
            validate_component_projection(component, expected_component_id=expected_id.replace(SUBSCRIPTION, APP_ID), pre_get_projection_proven=True, link_proven=True)
        self.assertEqual(validate_component_projection({**component, "properties.RetentionInDays": 365}, expected_component_id=expected_id, pre_get_projection_proven=True, link_proven=True), APP_ID)
        with self.assertRaises(OperatorReadBlocked):
            validate_component_projection({**component, "properties.provisioningState": {"raw": "synthetic"}}, expected_component_id=expected_id, pre_get_projection_proven=True, link_proven=True)
        as_of = datetime(2026, 9, 28, tzinfo=timezone.utc)
        self.assertTrue(validate_workspace_projection({"id": WORKSPACE, "properties.retentionInDays": 90}, WORKSPACE, as_of_utc=as_of))
        with self.assertRaises(OperatorReadBlocked):
            validate_workspace_projection({"id": WORKSPACE, "properties.retentionInDays": 1}, WORKSPACE, as_of_utc=as_of)
        with self.assertRaises(OperatorReadBlocked):
            validate_workspace_projection({"id": WORKSPACE, "properties.retentionInDays": 90}, WORKSPACE + "?x=1", as_of_utc=as_of)
        with self.assertRaises(OperatorReadBlocked):
            validate_workspace_projection({"id": WORKSPACE, "properties.retentionInDays": 10**100}, WORKSPACE, as_of_utc=as_of)

    def test_historical_counts_cannot_prove_denial_cause(self) -> None:
        summary = {"telemetry_rows": 1, "http_401": 0, "http_403": 1, "other": 0}
        self.assertEqual(classify_historical_summary(summary, capture_proven=True, retention_proven=True,
            link_proven=True, permission_proven=True), "TEMPORAL_STATUS_ONLY")
        for missing in ("capture_proven", "retention_proven", "link_proven", "permission_proven"):
            args = {"capture_proven": True, "retention_proven": True, "link_proven": True, "permission_proven": True}
            args[missing] = False
            self.assertEqual(classify_historical_summary(summary, **args), "UNPROVEN")
        self.assertEqual(classify_historical_summary({**summary, "telemetry_rows": 0, "http_403": 0},
            capture_proven=True, retention_proven=True, link_proven=True, permission_proven=True), "UNPROVEN")
        with self.assertRaises(OperatorReadBlocked):
            classify_historical_summary({**summary, "raw_url": "synthetic"}, capture_proven=True,
                retention_proven=True, link_proven=True, permission_proven=True)


if __name__ == "__main__":
    unittest.main()
