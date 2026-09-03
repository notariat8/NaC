from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import sys
import unittest
import urllib.parse


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.azure_activation import LIST_IDS, MATTER_ID, SITE_ID  # noqa: E402
from nac_bff.live_synthetic_workspace import (  # noqa: E402
    GRAPH_BASE_URL,
    LiveSyntheticWorkspaceError,
    LiveSyntheticWorkspaceManager,
    SYNTHETIC_LIVE_ACTOR_ID,
)


ACTOR = "11111111-1111-4111-8111-111111111111"
CORRELATION = "nac-bff-live-20260714-001"
SECRET = "SECRET_SENTINEL_DO_NOT_EXPOSE"


class _GraphClient:
    base_url = GRAPH_BASE_URL

    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = {value: [] for value in LIST_IDS.values()}
        self.calls: list[tuple[str, str, dict | None]] = []
        self.next_id = 1
        self.malformed_get: object | None = None
        self.malformed_post: object | None = None
        self.extra_get_key: str | None = None
        self.live_odata_shape = False

    def get(self, path: str) -> dict:
        self.calls.append(("GET", path, None))
        if self.malformed_get is not None:
            return self.malformed_get  # type: ignore[return-value]
        list_id = self._list_id(path)
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
        expression = query.get("$filter", [""])[0]
        match = re.fullmatch(r"fields/([A-Za-z0-9]+) eq '([^']+)'", expression)
        if match is None:
            raise AssertionError(f"unexpected filter: {expression}")
        key, value = match.groups()
        rows = [copy.deepcopy(row) for row in self.rows[list_id] if row["fields"].get(key) == value]
        if self.live_odata_shape:
            for row in rows:
                row["fields@odata.context"] = "https://graph.microsoft.com/v1.0/$metadata#fields/$entity"
                row["fields"]["@odata.etag"] = '"metadata-only"'
                for field, value in tuple(row["fields"].items()):
                    if value == "" or value is None:
                        del row["fields"][field]
        payload: dict = {"value": rows}
        if self.extra_get_key:
            payload[self.extra_get_key] = SECRET
        return payload

    def post(self, path: str, payload: dict) -> dict:
        self.calls.append(("POST", path, copy.deepcopy(payload)))
        if self.malformed_post is not None:
            return self.malformed_post  # type: ignore[return-value]
        list_id = self._list_id(path)
        item_id = f"item-{self.next_id}"
        self.next_id += 1
        self.rows[list_id].append({"id": item_id, "fields": copy.deepcopy(payload["fields"])})
        return {"id": item_id, "fields": {"ignored": SECRET}}

    def patch(self, path: str, payload: dict) -> dict:
        self.calls.append(("PATCH", path, copy.deepcopy(payload)))
        list_id = self._list_id(path)
        item_id = urllib.parse.unquote(path.split("/items/", 1)[1].split("/", 1)[0])
        matches = [row for row in self.rows[list_id] if row["id"] == item_id]
        if len(matches) != 1:
            raise AssertionError("patch target missing")
        matches[0]["fields"].update(copy.deepcopy(payload))
        return {}

    def _list_id(self, path: str) -> str:
        prefix = f"/sites/{urllib.parse.quote(SITE_ID, safe='')}/lists/"
        if not path.startswith(prefix) or "/items" not in path:
            raise AssertionError(f"path outside fixed site: {path}")
        list_id = urllib.parse.unquote(path[len(prefix) :].split("/", 1)[0])
        if list_id not in self.rows:
            raise AssertionError(f"path outside fixed lists: {path}")
        return list_id

    def list_rows(self, name: str) -> list[dict]:
        return self.rows[LIST_IDS[name]]


class LiveSyntheticWorkspaceManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _GraphClient()
        self.manager = LiveSyntheticWorkspaceManager(self.client)

    def test_inspect_seed_is_read_only_for_absent_and_existing_rows(self) -> None:
        absent = self.manager.inspect_seed(ACTOR, CORRELATION)
        self.assertEqual(absent["absent_count"], 5)
        self.assertEqual(absent["verified_count"], 0)
        self.assertTrue(all(call[0] == "GET" for call in self.client.calls))

        self.manager.ensure_seed(ACTOR, CORRELATION)
        self.client.calls.clear()
        existing = self.manager.inspect_seed(ACTOR, CORRELATION)
        self.assertEqual(existing["absent_count"], 0)
        self.assertEqual(existing["verified_count"], 5)
        self.assertTrue(all(call[0] == "GET" for call in self.client.calls))
        serialized = json.dumps(existing, sort_keys=True)
        for raw in (ACTOR, CORRELATION, MATTER_ID, SITE_ID, *LIST_IDS.values()):
            self.assertNotIn(raw, serialized)

    def test_inspect_seed_blocks_duplicate_without_mutation(self) -> None:
        self.manager.ensure_seed(ACTOR, CORRELATION)
        self.client.list_rows("Akten").append(
            copy.deepcopy(self.client.list_rows("Akten")[0])
        )
        self.client.calls.clear()
        with self.assertRaisesRegex(
            LiveSyntheticWorkspaceError,
            "SYNTHETIC_DUPLICATE_BLOCKED",
        ):
            self.manager.inspect_seed(ACTOR, CORRELATION)
        self.assertTrue(all(call[0] == "GET" for call in self.client.calls))

    def test_seed_creates_exact_canonical_rows_and_reuses_them(self) -> None:
        first = self.manager.ensure_seed(ACTOR, CORRELATION)
        second = self.manager.ensure_seed(ACTOR, CORRELATION)

        self.assertEqual(first["created_count"], 5)
        self.assertEqual(second["created_count"], 0)
        self.assertEqual(second["patched_count"], 0)
        self.assertEqual(len(self.client.list_rows("Akten")), 1)
        self.assertEqual(len(self.client.list_rows("AufgabenFristen")), 2)
        self.assertEqual(len(self.client.list_rows("Vertretungsfreigaben")), 1)
        self.assertEqual(len(self.client.list_rows("AuditJournalLite")), 1)
        matter = self.client.list_rows("Akten")[0]["fields"]
        self.assertEqual(matter["NacCaseId"], MATTER_ID)
        self.assertEqual(matter["FederfuehrenderNotar"], ACTOR)
        self.assertEqual(
            {row["fields"]["NacTaskId"] for row in self.client.list_rows("AufgabenFristen")},
            {"NAC-SYN-TASK-001", "NAC-SYN-DEADLINE-001"},
        )

    def test_live_odata_metadata_and_omitted_empty_fields_are_normalized(self) -> None:
        self.manager.ensure_seed(ACTOR, CORRELATION)
        self.client.live_odata_shape = True

        reused = self.manager.ensure_seed(ACTOR, CORRELATION)
        deputy = self.manager.set_access_mode("deputy", ACTOR, CORRELATION)
        restored = self.manager.restore_assigned(ACTOR, CORRELATION)

        self.assertEqual(reused["created_count"], 0)
        self.assertEqual(deputy["mode"], "deputy")
        self.assertEqual(restored["mode"], "assigned")

    def test_fixed_live_actor_uses_sharepoint_person_lookup_fields(self) -> None:
        self.manager.ensure_seed(SYNTHETIC_LIVE_ACTOR_ID, CORRELATION)

        posts = [payload for method, _, payload in self.client.calls if method == "POST"]
        matter = posts[0]["fields"]
        grant = posts[-2]["fields"]
        audit = posts[-1]["fields"]
        self.assertEqual(matter["FederfuehrenderNotarLookupId"], "11")
        self.assertEqual(matter["SachbearbeitungLookupId"], "")
        self.assertEqual(grant["FromUserLookupId"], "12")
        self.assertEqual(grant["ToUserLookupId"], "11")
        self.assertEqual(grant["ApprovedByLookupId"], "12")
        self.assertEqual(audit["ActorLookupId"], "12")

    def test_access_modes_use_only_bounded_patches_and_restore_assigned(self) -> None:
        self.manager.ensure_seed(ACTOR, CORRELATION)
        self.client.calls.clear()

        deputy = self.manager.set_access_mode("deputy", ACTOR, CORRELATION)
        denied = self.manager.set_access_mode("denied", ACTOR, CORRELATION)
        restored = self.manager.restore_assigned(ACTOR, CORRELATION)

        self.assertEqual((deputy["mode"], denied["mode"], restored["mode"]), ("deputy", "denied", "assigned"))
        patch_calls = [call for call in self.client.calls if call[0] == "PATCH"]
        self.assertEqual(len(patch_calls), 4)
        allowed_lists = {LIST_IDS["Akten"], LIST_IDS["Vertretungsfreigaben"]}
        for _, path, payload in patch_calls:
            self.assertTrue(path.endswith("/fields"))
            self.assertTrue(any(f"/lists/{list_id}/" in path for list_id in allowed_lists))
            self.assertNotIn(MATTER_ID, json.dumps(payload))
        matter = self.client.list_rows("Akten")[0]["fields"]
        grant = self.client.list_rows("Vertretungsfreigaben")[0]["fields"]
        self.assertEqual(matter["FederfuehrenderNotar"], ACTOR)
        self.assertEqual(grant["Status"], "Inaktiv")
        self.assertEqual(len(self.client.list_rows("AuditJournalLite")), 1)

    def test_verify_idempotency_is_read_only_and_redacted(self) -> None:
        self.manager.ensure_seed(ACTOR, CORRELATION)
        self.client.calls.clear()

        result = self.manager.verify_idempotency(ACTOR, CORRELATION)

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["created_count"], 0)
        self.assertEqual(result["patched_count"], 0)
        self.assertTrue(all(call[0] == "GET" for call in self.client.calls))
        serialized = json.dumps(result, sort_keys=True)
        for raw in (ACTOR, CORRELATION, MATTER_ID, SITE_ID, *LIST_IDS.values(), GRAPH_BASE_URL):
            self.assertNotIn(raw, serialized)

    def test_duplicate_matter_is_blocked_without_mutation(self) -> None:
        self.manager.ensure_seed(ACTOR, CORRELATION)
        self.client.list_rows("Akten").append(copy.deepcopy(self.client.list_rows("Akten")[0]))
        self.client.calls.clear()

        with self.assertRaisesRegex(LiveSyntheticWorkspaceError, "SYNTHETIC_DUPLICATE_BLOCKED"):
            self.manager.ensure_seed(ACTOR, CORRELATION)

        self.assertTrue(all(call[0] == "GET" for call in self.client.calls))

    def test_divergent_foreign_value_is_blocked(self) -> None:
        self.manager.ensure_seed(ACTOR, CORRELATION)
        self.client.list_rows("AufgabenFristen")[0]["fields"]["Status"] = "Foreign"

        with self.assertRaisesRegex(LiveSyntheticWorkspaceError, "SYNTHETIC_ROW_DIVERGED"):
            self.manager.ensure_seed(ACTOR, CORRELATION)

    def test_wrong_workspace_is_rejected_before_graph(self) -> None:
        with self.assertRaisesRegex(LiveSyntheticWorkspaceError, "WORKSPACE_SCOPE_INVALID"):
            self.manager.ensure_seed(ACTOR, CORRELATION, workspace_id="other_team")
        self.assertEqual(self.client.calls, [])

    def test_invalid_actor_correlation_and_mode_are_rejected_before_graph(self) -> None:
        for actor, correlation, code in (
            ("not-an-object-id", CORRELATION, "ACTOR_ID_INVALID"),
            (ACTOR, "bad value", "CORRELATION_ID_INVALID"),
        ):
            with self.subTest(code=code):
                with self.assertRaisesRegex(LiveSyntheticWorkspaceError, code):
                    self.manager.ensure_seed(actor, correlation)
        with self.assertRaisesRegex(LiveSyntheticWorkspaceError, "ACCESS_MODE_INVALID"):
            self.manager.set_access_mode("owner", ACTOR, CORRELATION)
        self.assertEqual(self.client.calls, [])

    def test_non_v1_client_is_rejected(self) -> None:
        self.client.base_url = "https://graph.microsoft.com/beta"
        with self.assertRaisesRegex(LiveSyntheticWorkspaceError, "GRAPH_V1_BOUNDARY_INVALID"):
            LiveSyntheticWorkspaceManager(self.client)

    def test_malformed_and_broad_graph_responses_are_blocked(self) -> None:
        for payload, code in (
            ({}, "GRAPH_RESPONSE_INVALID"),
            ({"value": "not-a-list"}, "GRAPH_RESPONSE_INVALID"),
            ({"value": [], "@odata.nextLink": "https://example.invalid"}, "GRAPH_PAGING_BLOCKED"),
        ):
            with self.subTest(code=code):
                client = _GraphClient()
                client.malformed_get = payload
                with self.assertRaisesRegex(LiveSyntheticWorkspaceError, code):
                    LiveSyntheticWorkspaceManager(client).ensure_seed(ACTOR, CORRELATION)

        self.client.extra_get_key = "rawSecret"
        with self.assertRaisesRegex(LiveSyntheticWorkspaceError, "GRAPH_RESPONSE_TOO_BROAD"):
            self.manager.ensure_seed(ACTOR, CORRELATION)

    def test_malformed_create_response_is_blocked(self) -> None:
        self.client.malformed_post = {"id": "bad/id", "rawSecret": SECRET}
        with self.assertRaisesRegex(LiveSyntheticWorkspaceError, "CREATE_RESPONSE_INVALID"):
            self.manager.ensure_seed(ACTOR, CORRELATION)

    def test_secret_sentinel_never_appears_in_result_or_error(self) -> None:
        result = self.manager.ensure_seed(ACTOR, CORRELATION)
        self.assertNotIn(SECRET, json.dumps(result, sort_keys=True))

        self.client.extra_get_key = "rawSecret"
        try:
            self.manager.verify_idempotency(ACTOR, CORRELATION)
        except LiveSyntheticWorkspaceError as exc:
            self.assertNotIn(SECRET, str(exc))
            self.assertEqual(exc.code, "GRAPH_RESPONSE_TOO_BROAD")
        else:
            self.fail("expected fail-closed response validation")

    def test_graph_transport_error_body_is_replaced_by_stable_code(self) -> None:
        class _FailingClient(_GraphClient):
            def get(self, path: str) -> dict:
                raise RuntimeError(SECRET)

        manager = LiveSyntheticWorkspaceManager(_FailingClient())
        with self.assertRaises(LiveSyntheticWorkspaceError) as raised:
            manager.ensure_seed(ACTOR, CORRELATION)
        self.assertEqual(raised.exception.code, "GRAPH_REQUEST_FAILED")
        self.assertNotIn(SECRET, str(raised.exception))

    def test_all_writes_are_fixed_graph_v1_site_and_list_paths(self) -> None:
        self.manager.ensure_seed(ACTOR, CORRELATION)
        self.manager.set_access_mode("deputy", ACTOR, CORRELATION)
        self.manager.set_access_mode("denied", ACTOR, CORRELATION)
        self.manager.restore_assigned(ACTOR, CORRELATION)

        expected_site = urllib.parse.quote(SITE_ID, safe="")
        for method, path, _ in self.client.calls:
            self.assertTrue(path.startswith(f"/sites/{expected_site}/lists/"))
            self.assertNotIn("/_api", path)
            self.assertNotIn("/beta", path)
            if method in {"POST", "PATCH"}:
                self.assertTrue(any(f"/lists/{list_id}/items" in path for list_id in LIST_IDS.values()))


if __name__ == "__main__":
    unittest.main()
