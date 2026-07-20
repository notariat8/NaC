from __future__ import annotations

import copy
import json
import sys
import unittest
import urllib.parse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.business_case_type_live_foundation import (  # noqa: E402
    CATALOG_VERSION,
    FoundationApplyRequest,
    WORKSPACE_ID,
    build_business_case_type_live_foundation_plan,
    load_business_case_type_live_foundation,
    run_business_case_type_live_foundation,
    validate_business_case_type_live_foundation,
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
            self.columns[self.registry_id] = [
                {
                    "name": "Title",
                    "displayName": "Title",
                    "required": False,
                    "text": {},
                },
                *copy.deepcopy(payload["columns"]),
            ]
            self.items[self.registry_id] = []
            return {"id": self.registry_id}
        akten_id = urllib.parse.quote(target["akten_list_id"], safe="")
        if path == f"{prefix}/lists/{akten_id}/columns":
            self.columns[target["akten_list_id"]].append(copy.deepcopy(payload))
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
