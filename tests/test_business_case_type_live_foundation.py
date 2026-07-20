from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import nac_m365_graph.business_case_type_live_foundation as foundation_module  # noqa: E402
from nac_m365_graph.business_case_type_live_foundation import (  # noqa: E402
    CATALOG_VERSION,
    FoundationApplyRequest,
    SYSTEM_COLUMN_BASELINE_PATH,
    SYSTEM_COLUMN_COUNT,
    WORKSPACE_ID,
    build_business_case_type_live_foundation_plan,
    load_business_case_type_live_foundation,
    run_business_case_type_live_foundation,
    validate_business_case_type_live_foundation,
    _SafetyStop,
    _get_collection,
    _validate_provisioner_source_contract,
)


class FakeFoundationGraph:
    def __init__(self, manifest: dict) -> None:
        self.manifest = manifest
        self.calls: list[tuple[str, str, dict | None]] = []
        target = manifest["target"]
        self.site = {
            "id": target["site_id"],
            "displayName": target["team_display_name"],
            "webUrl": target["site_url"],
        }
        self.lists = [
            {
                "id": target["akten_list_id"],
                "displayName": "Akten",
                "list": {"template": "genericList"},
            }
        ]
        legacy = manifest["schema"]["legacy_akten_column"]
        self.columns = {
            target["akten_list_id"]: [
                {
                    "name": "Vorgangstyp",
                    "displayName": "Vorgangstyp",
                    "required": True,
                    "choice": {
                        "allowTextEntry": False,
                        "choices": list(legacy["choices"]),
                    },
                }
            ]
        }
        self.items: dict[str, list[dict]] = {}
        self.registry_id = "registry-list-001"

    @property
    def post_count(self) -> int:
        return sum(1 for method, _path, _payload in self.calls if method == "POST")

    def get(self, path: str) -> dict:
        self.calls.append(("GET", path, None))
        target = self.manifest["target"]
        site = urllib.parse.quote(target["site_id"], safe="")
        prefix = f"/sites/{site}"
        if path.startswith(f"{prefix}?"):
            return copy.deepcopy(self.site)
        if path.startswith(f"{prefix}/lists?"):
            return {"value": copy.deepcopy(self.lists)}
        for list_id, columns in self.columns.items():
            encoded = urllib.parse.quote(list_id, safe="")
            if path.startswith(f"{prefix}/lists/{encoded}/columns?"):
                return {"value": copy.deepcopy(columns)}
        for list_id, items in self.items.items():
            encoded = urllib.parse.quote(list_id, safe="")
            if path.startswith(f"{prefix}/lists/{encoded}/items?"):
                return {"value": copy.deepcopy(items)}
        raise AssertionError(f"unexpected fake GET path: {path}")

    def post(self, path: str, payload: dict) -> dict:
        self.calls.append(("POST", path, copy.deepcopy(payload)))
        target = self.manifest["target"]
        site = urllib.parse.quote(target["site_id"], safe="")
        prefix = f"/sites/{site}"
        if path == f"{prefix}/lists":
            self.lists.append(
                {
                    "id": self.registry_id,
                    "displayName": payload["displayName"],
                    "list": copy.deepcopy(payload["list"]),
                }
            )
            system_columns = json.loads(
                (REPO_ROOT / SYSTEM_COLUMN_BASELINE_PATH).read_text(encoding="utf-8")
            )["columns"]
            for column in system_columns:
                if column["name"] == "Title":
                    column["text"] = {}
            self.columns[self.registry_id] = [
                *copy.deepcopy(system_columns),
                *(
                    {**copy.deepcopy(column), "hidden": False, "readOnly": False}
                    for column in payload["columns"]
                ),
            ]
            self.items[self.registry_id] = []
            return {"id": self.registry_id}
        akten_id = urllib.parse.quote(target["akten_list_id"], safe="")
        if path == f"{prefix}/lists/{akten_id}/columns":
            self.columns[target["akten_list_id"]].append(
                {**copy.deepcopy(payload), "hidden": False, "readOnly": False}
            )
            return {"id": "akten-vorgangstyp-id"}
        registry_id = urllib.parse.quote(self.registry_id, safe="")
        if path == f"{prefix}/lists/{registry_id}/items":
            item = {
                "id": str(len(self.items[self.registry_id]) + 1),
                "eTag": f"etag-{len(self.items[self.registry_id]) + 1}",
                "fields": copy.deepcopy(payload["fields"]),
            }
            self.items[self.registry_id].append(item)
            return copy.deepcopy(item)
        raise AssertionError(f"unexpected fake POST path: {path}")


def owner_request(plan_sha256: str, **overrides: object) -> FoundationApplyRequest:
    values = {
        "workspace_id": WORKSPACE_ID,
        "expected_plan_sha256": plan_sha256,
        "approval_reference": "issue-678-owner-approval",
        "reason": "Create the additive canonical registry foundation",
        "owner_approved": True,
        "execute_live_foundation": True,
    }
    values.update(overrides)
    return FoundationApplyRequest(**values)


class BusinessCaseTypeLiveFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_business_case_type_live_foundation(REPO_ROOT)
        self.plan = build_business_case_type_live_foundation_plan(REPO_ROOT)

    def test_manifest_and_plan_bind_exact_additive_foundation(self) -> None:
        validation = validate_business_case_type_live_foundation(REPO_ROOT, self.manifest)
        self.assertEqual(validation.errors, ())
        self.assertEqual(self.plan["status"], "PASSED")
        self.assertEqual(self.plan["summary"]["maximum_mutation_count"], 22)
        self.assertEqual(self.plan["summary"]["canonical_registry_row_count"], 20)
        self.assertEqual(self.plan["summary"]["alias_registry_row_count"], 0)
        self.assertEqual(len(self.plan["binding"]["graph_sha256"]), 64)
        self.assertEqual(
            len(self.plan["binding"]["provisioner_source_contract_sha256"]), 64
        )
        self.assertEqual(
            len(self.plan["binding"]["system_column_baseline_sha256"]), 64
        )
        system_baseline = json.loads(
            (REPO_ROOT / SYSTEM_COLUMN_BASELINE_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(system_baseline["system_column_count"], 85)
        self.assertEqual(system_baseline["source_writes"], 0)
        self.assertEqual(self.manifest["registry"]["catalog_version"], CATALOG_VERSION)
        self.assertEqual(self.manifest["graph"]["application_permission"], "Sites.FullControl.All")
        self.assertEqual(
            self.manifest["graph"]["provisioner_binding"]["application_display_name"],
            "NaC M365 Provisioning",
        )
        self.assertFalse(
            self.manifest["graph"]["provisioner_binding"]["permission_change_required"]
        )
        self.assertFalse(
            self.manifest["graph"]["provisioner_binding"]["permission_mutation_allowed"]
        )
        self.assertTrue(
            all(row["CatalogVersion"] == CATALOG_VERSION for row in self.manifest["registry"]["rows"])
        )
        self.assertTrue(all(row["LifecycleStatus"] == "active" for row in self.manifest["registry"]["rows"]))
        self.assertTrue(all(row["Selectable"] is True for row in self.manifest["registry"]["rows"]))
        rendered = json.dumps(self.plan, sort_keys=True)
        self.assertNotIn('"method": "PATCH"', rendered)
        self.assertNotIn('"method": "DELETE"', rendered)
        self.assertNotIn("migrate", rendered.lower())
        self.assertNotIn("Vorgangstyp/columns", rendered)

    def test_provisioner_source_digest_changes_plan_hash(self) -> None:
        with mock.patch.object(
            foundation_module, "_sha256_file", return_value="0" * 64
        ):
            changed = build_business_case_type_live_foundation_plan(REPO_ROOT)
        self.assertEqual(
            changed["binding"]["provisioner_source_contract_sha256"], "0" * 64
        )
        self.assertNotEqual(changed["plan_sha256"], self.plan["plan_sha256"])

    def test_internally_consistent_84_column_baseline_is_rejected(self) -> None:
        baseline = copy.deepcopy(
            json.loads(
                (REPO_ROOT / SYSTEM_COLUMN_BASELINE_PATH).read_text(encoding="utf-8")
            )
        )
        baseline["columns"].pop()
        baseline["system_column_count"] = len(baseline["columns"])
        baseline["system_columns_sha256"] = foundation_module._sha256_json(
            baseline["columns"]
        )
        with mock.patch.object(
            foundation_module, "_load_system_column_baseline", return_value=baseline
        ):
            errors = foundation_module._validate_system_column_baseline(
                REPO_ROOT, self.manifest["graph"]
            )
        self.assertEqual(errors, ["system column baseline contract drift"])
        self.assertEqual(SYSTEM_COLUMN_COUNT, 85)

    def test_provisioner_source_contract_drift_is_rejected(self) -> None:
        graph = copy.deepcopy(self.manifest["graph"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / graph["provisioner_binding"]["source_contract"]
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "permission_boundary": {
                            "provisioner_site_permission_administration": {
                                "provisioner_display_name_exact": "NaC M365 Provisioning",
                                "required_application_permission_exact": "Sites.Manage.All",
                            },
                            "provisioner_graph_application_roles_exact": [
                                "Sites.Manage.All"
                            ],
                            "provisioner_additional_graph_roles_allowed": False,
                        }
                    }
                ),
                encoding="utf-8",
            )
            errors = _validate_provisioner_source_contract(root, graph)
        self.assertEqual(
            errors, ["provisioner source contract permission boundary drift"]
        )

    def test_wrong_workspace_stops_before_graph_call(self) -> None:
        client = FakeFoundationGraph(self.manifest)
        result = run_business_case_type_live_foundation(
            client,
            REPO_ROOT,
            owner_request(self.plan["plan_sha256"], workspace_id="notary_team_02"),
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error_code"], "WORKSPACE_SCOPE_MISMATCH")
        self.assertEqual(client.calls, [])

    def test_manifest_snapshot_drift_stops_before_graph_call(self) -> None:
        client = FakeFoundationGraph(self.manifest)
        snapshot = foundation_module._load_foundation_runtime_snapshot(REPO_ROOT)
        tampered_manifest = copy.deepcopy(snapshot.manifest)
        tampered_manifest["target"]["site_id"] = "unauthorized-site"
        tampered_snapshot = foundation_module._FoundationRuntimeSnapshot(
            tampered_manifest,
            snapshot.system_column_baseline,
            foundation_module._foundation_binding(REPO_ROOT, tampered_manifest),
        )
        with mock.patch.object(
            foundation_module,
            "_load_foundation_runtime_snapshot",
            return_value=tampered_snapshot,
        ):
            result = run_business_case_type_live_foundation(
                client, REPO_ROOT, owner_request(self.plan["plan_sha256"])
            )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error_code"], "PLAN_SNAPSHOT_DRIFT")
        self.assertEqual(client.calls, [])

    def test_owner_gate_stops_before_graph_call(self) -> None:
        client = FakeFoundationGraph(self.manifest)
        result = run_business_case_type_live_foundation(
            client,
            REPO_ROOT,
            owner_request(self.plan["plan_sha256"], owner_approved=False),
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error_code"], "OWNER_GATE_CLOSED")
        self.assertEqual(client.calls, [])

    def test_whitespace_approval_fields_stop_before_graph_call(self) -> None:
        for field in ("approval_reference", "reason"):
            with self.subTest(field=field):
                client = FakeFoundationGraph(self.manifest)
                result = run_business_case_type_live_foundation(
                    client,
                    REPO_ROOT,
                    owner_request(self.plan["plan_sha256"], **{field: "  \t  "}),
                )
                self.assertEqual(result["status"], "BLOCKED")
                self.assertIn(
                    "APPROVAL_REFERENCE_MISSING"
                    if field == "approval_reference"
                    else "REASON_MISSING",
                    result["error_code"],
                )
                self.assertEqual(client.calls, [])

    def test_non_string_approval_fields_stop_with_stable_code(self) -> None:
        for field in ("approval_reference", "reason"):
            with self.subTest(field=field):
                client = FakeFoundationGraph(self.manifest)
                result = run_business_case_type_live_foundation(
                    client,
                    REPO_ROOT,
                    owner_request(self.plan["plan_sha256"], **{field: None}),
                )
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(
                    result["error_code"],
                    "APPROVAL_REFERENCE_MISSING"
                    if field == "approval_reference"
                    else "REASON_MISSING",
                )
                self.assertEqual(client.calls, [])

    def test_legacy_schema_drift_stops_before_write(self) -> None:
        client = FakeFoundationGraph(self.manifest)
        client.columns[self.manifest["target"]["akten_list_id"]][0]["choice"]["choices"].append(
            "unexpected"
        )
        result = run_business_case_type_live_foundation(
            client, REPO_ROOT, owner_request(self.plan["plan_sha256"])
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error_code"], "LEGACY_VORGANGSTYP_SCHEMA_DRIFT")
        self.assertEqual(client.post_count, 0)

    def test_first_run_converges_and_second_run_has_zero_mutations(self) -> None:
        client = FakeFoundationGraph(self.manifest)
        legacy_before = copy.deepcopy(client.columns[self.manifest["target"]["akten_list_id"]][0])
        request = owner_request(self.plan["plan_sha256"])

        first = run_business_case_type_live_foundation(client, REPO_ROOT, request)
        first_post_count = client.post_count
        second = run_business_case_type_live_foundation(client, REPO_ROOT, request)

        self.assertEqual(first["status"], "PASSED")
        self.assertEqual(first["summary"]["mutation_count"], 22)
        self.assertEqual(first["summary"]["registry_list_create_count"], 1)
        self.assertEqual(first["summary"]["akten_column_create_count"], 1)
        self.assertEqual(first["summary"]["registry_row_create_count"], 20)
        self.assertEqual(second["status"], "PASSED")
        self.assertEqual(second["summary"]["mutation_count"], 0)
        self.assertEqual(client.post_count, first_post_count)
        self.assertEqual(
            client.columns[self.manifest["target"]["akten_list_id"]][0], legacy_before
        )
        self.assertEqual(len(client.items[client.registry_id]), 20)

        evidence = json.dumps(first, sort_keys=True)
        self.assertNotIn(self.manifest["target"]["site_id"], evidence)
        self.assertNotIn(request.approval_reference, evidence)
        self.assertNotIn(request.reason, evidence)
        self.assertNotIn("Authorization", evidence)
        self.assertNotIn("Bearer", evidence)
        self.assertEqual(first["summary"]["delete_count"], 0)
        self.assertEqual(first["summary"]["rollback_count"], 0)

    def test_extra_mutable_registry_column_stops_before_write(self) -> None:
        client = FakeFoundationGraph(self.manifest)
        request = owner_request(self.plan["plan_sha256"])
        self.assertEqual(
            run_business_case_type_live_foundation(client, REPO_ROOT, request)["status"],
            "PASSED",
        )
        client.columns[client.registry_id].append(
            {
                "name": "UnexpectedCustom",
                "displayName": "UnexpectedCustom",
                "required": False,
                "hidden": False,
                "readOnly": False,
                "text": {"allowMultipleLines": False, "maxLength": 64},
            }
        )
        post_count = client.post_count
        result = run_business_case_type_live_foundation(client, REPO_ROOT, request)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error_code"], "REGISTRY_CUSTOM_COLUMN_SET_DRIFT")
        self.assertEqual(client.post_count, post_count)

    def test_read_only_hidden_extra_registry_column_stops_before_write(self) -> None:
        client = FakeFoundationGraph(self.manifest)
        request = owner_request(self.plan["plan_sha256"])
        self.assertEqual(
            run_business_case_type_live_foundation(client, REPO_ROOT, request)["status"],
            "PASSED",
        )
        client.columns[client.registry_id].append(
            {
                "name": "UnexpectedHiddenCustom",
                "displayName": "UnexpectedHiddenCustom",
                "required": False,
                "hidden": True,
                "readOnly": True,
                "text": {"allowMultipleLines": False, "maxLength": 64},
            }
        )
        post_count = client.post_count
        result = run_business_case_type_live_foundation(client, REPO_ROOT, request)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error_code"], "REGISTRY_CUSTOM_COLUMN_SET_DRIFT")
        self.assertEqual(client.post_count, post_count)

    def test_system_column_baseline_drift_stops_before_write(self) -> None:
        client = FakeFoundationGraph(self.manifest)
        request = owner_request(self.plan["plan_sha256"])
        self.assertEqual(
            run_business_case_type_live_foundation(client, REPO_ROOT, request)["status"],
            "PASSED",
        )
        column = next(
            item
            for item in client.columns[client.registry_id]
            if item["name"] == "Attachments"
        )
        column["hidden"] = not column["hidden"]
        post_count = client.post_count
        result = run_business_case_type_live_foundation(client, REPO_ROOT, request)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["error_code"], "REGISTRY_SYSTEM_COLUMN_BASELINE_DRIFT"
        )
        self.assertEqual(client.post_count, post_count)

    def test_hidden_registry_column_stops_before_write(self) -> None:
        client = FakeFoundationGraph(self.manifest)
        request = owner_request(self.plan["plan_sha256"])
        self.assertEqual(
            run_business_case_type_live_foundation(client, REPO_ROOT, request)["status"],
            "PASSED",
        )
        column = next(
            item
            for item in client.columns[client.registry_id]
            if item["name"] == "BusinessCaseTypeId"
        )
        column["hidden"] = True
        post_count = client.post_count
        result = run_business_case_type_live_foundation(client, REPO_ROOT, request)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error_code"], "REGISTRY_COLUMN_SCHEMA_DRIFT")
        self.assertEqual(client.post_count, post_count)

    def test_paging_rejects_query_changes_duplicates_and_fragments(self) -> None:
        path = "/sites/site/lists?$select=id&$top=1"
        next_links = (
            "https://graph.microsoft.com/v1.0/sites/site/lists?$select=displayName&$top=1&$skiptoken=x",
            "https://graph.microsoft.com/v1.0/sites/site/lists?$select=id&$select=displayName&$top=1&$skiptoken=x",
            "https://graph.microsoft.com/v1.0/sites/site/lists?$select=id&$top=1&$skiptoken=x#fragment",
        )
        for next_link in next_links:
            with self.subTest(next_link=next_link):
                class PagingClient:
                    def get(self, _path: str) -> dict:
                        return {"value": [], "@odata.nextLink": next_link}

                with self.assertRaisesRegex(_SafetyStop, "GRAPH_PAGING_INVALID"):
                    _get_collection(PagingClient(), path, {"reads": 0})

    def test_paging_accepts_preserved_query_and_rotating_skiptoken(self) -> None:
        path = "/sites/site/lists?$select=id&$top=1"

        class PagingClient:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def get(self, current: str) -> dict:
                self.calls.append(current)
                if len(self.calls) == 1:
                    return {
                        "value": [{"id": "1"}],
                        "@odata.nextLink": (
                            "https://graph.microsoft.com/v1.0/sites/site/lists?"
                            "$select=id&$top=1&$skiptoken=first"
                        ),
                    }
                if len(self.calls) == 2:
                    return {
                        "value": [{"id": "2"}],
                        "@odata.nextLink": (
                            "https://graph.microsoft.com/v1.0/sites/site/lists?"
                            "$select=id&$top=1&$skiptoken=second"
                        ),
                    }
                return {"value": [{"id": "3"}]}

        client = PagingClient()
        items = _get_collection(client, path, {"reads": 0})
        self.assertEqual([item["id"] for item in items], ["1", "2", "3"])
        self.assertEqual(len(client.calls), 3)

    def test_existing_registry_row_drift_stops_before_write(self) -> None:
        client = FakeFoundationGraph(self.manifest)
        request = owner_request(self.plan["plan_sha256"])
        first = run_business_case_type_live_foundation(client, REPO_ROOT, request)
        self.assertEqual(first["status"], "PASSED")
        client.items[client.registry_id][0]["fields"]["Selectable"] = False
        post_count = client.post_count

        result = run_business_case_type_live_foundation(client, REPO_ROOT, request)

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error_code"], "REGISTRY_ROW_SCHEMA_DRIFT")
        self.assertEqual(client.post_count, post_count)


if __name__ == "__main__":
    unittest.main()
