from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from typing import Any

from nac_m365_graph.mcp_runtime import DEFAULT_MCP_CONTRACT, load_mcp_contract
from nac_m365_graph.mvp_test_environment_smoke import (
    EXPECTED_WORKSPACE_ID,
    SYNTHETIC_CASE_ID,
    SYNTHETIC_DEADLINE_DUE_DATE,
    SYNTHETIC_TASK_IDS,
    run_mvp_test_environment_smoke,
    run_mvp_test_environment_smoke_from_paths,
)
from nac_m365_graph.privileged_change import DEFAULT_PROVISIONED_STATE, load_provisioned_state


class FakeGraphClient:
    def __init__(
        self,
        *,
        fail_post_number: int | None = None,
        fail_readback_once: bool = False,
        missing_response_id_post_number: int | None = None,
        mismatched_response_id_post_number: int | None = None,
    ) -> None:
        self.fail_post_number = fail_post_number
        self.fail_readback_once = fail_readback_once
        self.missing_response_id_post_number = missing_response_id_post_number
        self.mismatched_response_id_post_number = mismatched_response_id_post_number
        self._readback_failed = False
        self._next_id = 1
        self.items: dict[str, dict[str, dict[str, Any]]] = {}
        self.posts: list[tuple[str, dict[str, Any]]] = []
        self.gets: list[str] = []
        self.deletes: list[str] = []

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.posts.append((path, copy.deepcopy(payload)))
        if self.fail_post_number == len(self.posts):
            raise RuntimeError("raw fake write failure")
        item_id = f"raw-item-{self._next_id}"
        self._next_id += 1
        self.items.setdefault(path, {})[item_id] = {"id": item_id, "fields": copy.deepcopy(payload["fields"])}
        if self.missing_response_id_post_number == len(self.posts):
            return {"fields": copy.deepcopy(payload["fields"])}
        response_id = (
            "foreign-existing-item"
            if self.mismatched_response_id_post_number == len(self.posts)
            else item_id
        )
        return {"id": response_id, "fields": copy.deepcopy(payload["fields"])}

    def get(self, path: str) -> dict[str, Any]:
        self.gets.append(path)
        if self.fail_readback_once and len(self.posts) == 3 and not self._readback_failed:
            self._readback_failed = True
            raise RuntimeError("raw fake readback failure")
        collection = path.split("?", 1)[0]
        decoded = urllib.parse.unquote(path)
        match = re.search(r"fields/([A-Za-z0-9_]+) eq '([^']*)'", decoded)
        values = list(self.items.get(collection, {}).values())
        if match:
            field, value = match.groups()
            values = [item for item in values if item["fields"].get(field) == value]
        return {"value": copy.deepcopy(values)}

    def delete(self, path: str) -> dict[str, Any]:
        self.deletes.append(path)
        collection, item_id = path.rsplit("/", 1)
        self.items.get(collection, {}).pop(urllib.parse.unquote(item_id), None)
        return {}


def allow_expected_decisions(request: dict[str, str]) -> dict[str, str]:
    if request["scenario"] == "deny":
        return {"decision": "DENY", "code": "SYNTHETIC_DENY"}
    return {"decision": "ALLOW", "code": f"SYNTHETIC_{request['scenario'].upper()}"}


def provisioned_state() -> dict[str, Any]:
    return load_provisioned_state(DEFAULT_PROVISIONED_STATE)


class MvpTestEnvironmentSmokeTests(unittest.TestCase):
    def run_smoke(
        self,
        client: FakeGraphClient,
        decision_function=allow_expected_decisions,
        *,
        workspace_id: str = EXPECTED_WORKSPACE_ID,
        owner_approved: bool = True,
        state: dict[str, Any] | None = None,
        contract: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return run_mvp_test_environment_smoke(
            client,
            contract or load_mcp_contract(DEFAULT_MCP_CONTRACT),
            state or provisioned_state(),
            decision_function,
            workspace_id=workspace_id,
            owner_approved=owner_approved,
            correlation_id="raw-correlation-id",
            timestamp="2026-07-13T12:00:00Z",
        )

    def test_success_writes_reads_roles_fixture_and_cleans_exact_items(self) -> None:
        client = FakeGraphClient()

        result = self.run_smoke(client)

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["matterWriteCount"], 1)
        self.assertEqual(result["summary"]["taskDeadlineWriteCount"], 2)
        self.assertEqual(result["summary"]["targetedReadbackCount"], 3)
        self.assertEqual([check["actual"] for check in result["roleChecks"]], ["ALLOW", "ALLOW", "DENY"])
        self.assertTrue(result["bpmnFixture"]["verified"])
        self.assertTrue(result["bpmnFixture"]["packageBound"])
        self.assertTrue(result["summary"]["canonicalInputBindingVerified"])
        self.assertTrue(all(result["inputBinding"].values()))
        self.assertEqual(len(client.posts), 3)
        self.assertEqual(client.posts[2][1]["fields"]["DueDate"], SYNTHETIC_DEADLINE_DUE_DATE)
        self.assertEqual(len(client.deletes), 3)
        self.assertTrue(all(not items for items in client.items.values()))
        serialized = json.dumps(result, ensure_ascii=False)
        for raw_value in (
            EXPECTED_WORKSPACE_ID,
            SYNTHETIC_CASE_ID,
            SYNTHETIC_DEADLINE_DUE_DATE,
            *SYNTHETIC_TASK_IDS,
            "raw-correlation-id",
            "raw-item-1",
            "funktion8.sharepoint.com",
            "588d4a41-f538-4f37-acfb-63ff283e0910",
            "fields",
        ):
            self.assertNotIn(raw_value, serialized)

    def test_owner_deny_fails_before_graph_calls(self) -> None:
        client = FakeGraphClient()

        result = self.run_smoke(client, owner_approved=False)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "OWNER_GATE_CLOSED")
        self.assertEqual(client.posts, [])
        self.assertEqual(client.gets, [])
        self.assertEqual(client.deletes, [])

    def test_role_deny_mismatch_fails_closed_before_graph_calls(self) -> None:
        client = FakeGraphClient()

        def deny_mismatch(request: dict[str, str]) -> str:
            return "ALLOW"

        result = self.run_smoke(client, deny_mismatch)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "ACCESS_DECISION_FAILED")
        self.assertEqual(client.posts, [])
        self.assertEqual(client.gets, [])
        self.assertEqual(client.deletes, [])

    def test_wrong_workspace_fails_before_graph_calls(self) -> None:
        client = FakeGraphClient()

        result = self.run_smoke(client, workspace_id="notary_team_02")

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "WORKSPACE_SCOPE_REJECTED")
        self.assertEqual(client.posts, [])
        self.assertEqual(client.gets, [])
        self.assertEqual(client.deletes, [])

    def test_manipulated_state_cannot_redirect_notary_team_01(self) -> None:
        client = FakeGraphClient()
        state = provisioned_state()
        team_01 = next(item for item in state["workspaces"] if item["id"] == EXPECTED_WORKSPACE_ID)
        team_02 = next(item for item in state["workspaces"] if item["id"] == "notary_team_02")
        team_01["team_id"] = team_02["team_id"]
        team_01["site_id"] = team_02["site_id"]
        team_01["site_url"] = team_02["site_url"]
        team_01["lists"] = copy.deepcopy(team_02["lists"])

        result = self.run_smoke(client, state=state)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "PROVISIONED_STATE_BINDING_MISMATCH")
        self.assertFalse(result["summary"]["canonicalInputBindingVerified"])
        self.assertEqual(client.posts, [])
        self.assertEqual(client.gets, [])
        self.assertEqual(client.deletes, [])

    def test_custom_state_path_with_redirected_ids_fails_before_graph_calls(self) -> None:
        client = FakeGraphClient()
        state = provisioned_state()
        team_01 = next(item for item in state["workspaces"] if item["id"] == EXPECTED_WORKSPACE_ID)
        team_02 = next(item for item in state["workspaces"] if item["id"] == "notary_team_02")
        team_01["site_id"] = team_02["site_id"]
        team_01["lists"] = copy.deepcopy(team_02["lists"])
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "redirected-state.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            result = run_mvp_test_environment_smoke_from_paths(
                client,
                allow_expected_decisions,
                workspace_id=EXPECTED_WORKSPACE_ID,
                owner_approved=True,
                provisioned_state_path=state_path,
                correlation_id="raw-correlation-id",
            )

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "PROVISIONED_STATE_BINDING_MISMATCH")
        self.assertEqual(client.posts, [])
        self.assertEqual(client.gets, [])
        self.assertEqual(client.deletes, [])

    def test_modified_mcp_contract_fails_before_graph_calls(self) -> None:
        client = FakeGraphClient()
        contract = load_mcp_contract(DEFAULT_MCP_CONTRACT)
        contract["tools"][0]["graph_path_template"] = "/sites/redirected/lists/redirected/items"

        result = self.run_smoke(client, contract=contract)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "MCP_CONTRACT_BINDING_MISMATCH")
        self.assertEqual(client.posts, [])
        self.assertEqual(client.gets, [])
        self.assertEqual(client.deletes, [])

    def test_write_failure_returns_redacted_error_and_cleans_prior_write(self) -> None:
        client = FakeGraphClient(fail_post_number=2)

        result = self.run_smoke(client)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "WRITE_FAILED")
        self.assertEqual(result["cleanup"]["deleteCount"], 1)
        self.assertTrue(all(not items for items in client.items.values()))
        self.assertNotIn("raw fake write failure", json.dumps(result))

    def test_post_without_id_is_never_deleted_or_reported_absent(self) -> None:
        client = FakeGraphClient(missing_response_id_post_number=1)

        result = self.run_smoke(client)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "WRITE_RESPONSE_INVALID")
        self.assertEqual(result["error"]["cleanupCode"], "CLEANUP_FAILED")
        self.assertEqual(result["cleanup"]["deleteCount"], 0)
        self.assertEqual(result["cleanup"]["verifiedAbsentCount"], 0)
        self.assertEqual(client.deletes, [])
        self.assertTrue(any(client.items.values()))

    def test_cleanup_refuses_post_id_that_does_not_match_synthetic_key_read(self) -> None:
        client = FakeGraphClient(mismatched_response_id_post_number=1)

        result = self.run_smoke(client)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "READBACK_ITEM_MISMATCH")
        self.assertEqual(result["error"]["cleanupCode"], "CLEANUP_FAILED")
        self.assertEqual(result["cleanup"]["deleteCount"], 2)
        self.assertTrue(all("foreign-existing-item" not in path for path in client.deletes))
        self.assertEqual(sum(len(items) for items in client.items.values()), 1)

    def test_cleanup_runs_in_finally_after_readback_error(self) -> None:
        client = FakeGraphClient(fail_readback_once=True)

        result = self.run_smoke(client)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "READBACK_FAILED")
        self.assertTrue(result["cleanup"]["finallyExecuted"])
        self.assertEqual(result["cleanup"]["deleteCount"], 3)
        self.assertEqual(result["cleanup"]["verifiedAbsentCount"], 3)
        self.assertTrue(all(not items for items in client.items.values()))


if __name__ == "__main__":
    unittest.main()
