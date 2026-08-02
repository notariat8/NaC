from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import unittest
import urllib.error


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.live_access_decision import LiveAccessDecisionAdapter  # noqa: E402
from nac_bff.synthetic_workspace_graph import (  # noqa: E402
    AZURE_HTTP_LIMIT_SECONDS,
    GRAPH_BASE_URL,
    GRAPH_IO_TIMEOUT_SECONDS,
    GRAPH_REQUEST_DEADLINE_SECONDS,
    MAX_BFF_GRAPH_REQUESTS,
    MAX_RESPONSE_BYTES,
    GraphRequestError,
    GraphResponseError,
    RawGraphV1Client,
    SyntheticWorkspaceGraphRestAdapter,
    read_bounded_collection,
    synthetic_list_binding,
)
from nac_bff.test_environment import (  # noqa: E402
    ALLOWED_MATTER_ID,
    ALLOWED_PURPOSE,
    ALLOWED_WORKSPACE_ID,
    AccessDecision,
    AccessMode,
    TestEnvironmentBff,
    ValidatedClaims,
)
from nac_mvp_test_environment import (  # noqa: E402
    BUSINESS_CASE_TYPE_ID,
    DEADLINE,
    MATTER_STATUS,
    TASKS,
)


class _FakeGraphClient:
    base_url = GRAPH_BASE_URL
    redirects_allowed = False
    retains_error_body = False

    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.paths: list[str] = []

    def get(self, path: str) -> dict[str, object]:
        self.paths.append(path)
        if not self.responses:
            raise AssertionError("unexpected Graph GET")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if not isinstance(response, dict):
            raise AssertionError("fake response must be a dict")
        return response


class _TokenProvider:
    def fetch_access_token(self) -> str:
        return "offline-fake-token"


class _MonotonicClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


class _Response:
    def __init__(self, payload: object) -> None:
        self.raw = json.dumps(payload).encode("utf-8") if not isinstance(payload, bytes) else payload
        self.headers = {"Content-Length": str(len(self.raw))}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self, limit: int) -> bytes:
        return self.raw[:limit]


class _ScriptedRawClient(RawGraphV1Client):
    def __init__(self, *results: object, sleep, **client_kwargs) -> None:
        super().__init__(_TokenProvider(), sleep=sleep, **client_kwargs)
        self.results = list(results)
        self.requests = []
        self.timeouts: list[float] = []

    def _open(self, request, *, timeout_seconds: float):
        self.requests.append(request)
        self.timeouts.append(timeout_seconds)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _http_error(status: int, retry_after: str | None = None) -> urllib.error.HTTPError:
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    return urllib.error.HTTPError(
        "https://graph.microsoft.com/v1.0/sites/fixed",
        status,
        "offline fake",
        headers,
        io.BytesIO(b"SENSITIVE ERROR BODY"),
    )


def _page(*rows: dict, next_link: str | None = None) -> dict:
    payload: dict[str, object] = {
        "value": [
            {"id": f"offline-item-{index}", "fields": row}
            for index, row in enumerate(rows, start=1)
        ]
    }
    if next_link is not None:
        payload["@odata.nextLink"] = next_link
    return payload


def _case_projection() -> dict:
    return {
        "NacCaseId": ALLOWED_MATTER_ID,
        "Vorgangstyp": BUSINESS_CASE_TYPE_ID,
        "Status": MATTER_STATUS,
        "FristNaechsteAktion": DEADLINE,
    }


def _task_projection(task: dict) -> dict:
    return {
        "NacTaskId": task["task_id"],
        "NacCaseId": ALLOWED_MATTER_ID,
        "BpmnStepCode": task["step_code"],
        "Status": task["status"],
        "RequiresNotaryApproval": task["requires_notary_approval"],
        "DueDate": task["due_at"],
    }


def _access_case(*, notary: object = "actor-notary", clerks: object = ["actor-clerk"]) -> dict:
    return {
        "NacCaseId": ALLOWED_MATTER_ID,
        "NotarTeam": "NaC-Notar-01",
        "FederfuehrenderNotar": notary,
        "Sachbearbeitung": clerks,
    }


def _grant(**changes: object) -> dict:
    value = {
        "GrantId": "NAC-SYN-GRANT-001",
        "NacCaseId": ALLOWED_MATTER_ID,
        "FromUser": "actor-notary",
        "ToUser": "actor-deputy",
        "GrantedRole": "SachbearbeitungVertretung",
        "Reason": "Synthetische Urlaubsvertretung",
        "ValidFrom": "2026-07-14T08:00:00Z",
        "ValidUntil": "2026-07-14T18:00:00Z",
        "ApprovedBy": "actor-notary",
        "Status": "Aktiv",
        "AuditCorrelationId": "NAC-SYN-AUDIT-001",
    }
    value.update(changes)
    return value


def _audit(**changes: object) -> dict:
    value = {
        "NacCaseId": ALLOWED_MATTER_ID,
        "Action": "GrantApproved",
        "ObjectId": "NAC-SYN-GRANT-001",
        "CorrelationId": "NAC-SYN-AUDIT-001",
    }
    value.update(changes)
    return value


class RawGraphV1ClientTests(unittest.TestCase):
    def test_get_is_raw_v1_get_without_redirect_or_error_body_retention(self) -> None:
        client = _ScriptedRawClient(_Response({"value": []}), sleep=lambda _: None)

        payload = client.get("/sites/fixed/lists/fixed/items")

        self.assertEqual(payload, {"value": []})
        self.assertFalse(client.redirects_allowed)
        self.assertFalse(client.retains_error_body)
        self.assertEqual(client.requests[0].method, "GET")
        self.assertEqual(client.requests[0].full_url, f"{GRAPH_BASE_URL}/sites/fixed/lists/fixed/items")
        self.assertEqual(client.requests[0].headers["Accept"], "application/json")
        self.assertEqual(client.timeouts, [GRAPH_IO_TIMEOUT_SECONDS])
        self.assertLess(
            MAX_BFF_GRAPH_REQUESTS * GRAPH_REQUEST_DEADLINE_SECONDS,
            AZURE_HTTP_LIMIT_SECONDS,
        )

    def test_retries_only_429_and_503_and_caps_retry_after(self) -> None:
        sleeps: list[float] = []
        client = _ScriptedRawClient(
            _http_error(429, "99"),
            _http_error(503, "0.5"),
            _Response({"value": []}),
            sleep=sleeps.append,
        )

        self.assertEqual(client.get("/sites/fixed/lists/fixed/items"), {"value": []})
        self.assertEqual(sleeps, [2.0, 0.5])
        self.assertEqual(len(client.requests), 3)

        for status in (302, 400, 401, 403, 404, 500, 504):
            with self.subTest(status=status):
                no_retry = _ScriptedRawClient(_http_error(status, "0"), sleep=lambda _: None)
                with self.assertRaises(GraphRequestError) as raised:
                    no_retry.get("/sites/fixed/lists/fixed/items")
                self.assertNotIn("SENSITIVE", str(raised.exception))
                self.assertEqual(len(no_retry.requests), 1)

    def test_monotonic_deadline_bounds_the_complete_retry_sequence(self) -> None:
        clock = _MonotonicClock()
        client = _ScriptedRawClient(
            _http_error(429, "2"),
            _http_error(503, "2"),
            _Response({"value": []}),
            sleep=clock.sleep,
            monotonic=clock,
            request_deadline_seconds=3.0,
        )

        with self.assertRaises(GraphRequestError) as raised:
            client.get("/sites/fixed/lists/fixed/items")

        self.assertIn("deadline", str(raised.exception))
        self.assertEqual(clock.sleeps, [2.0])
        self.assertEqual(client.timeouts, [3.0, 1.0])
        self.assertEqual(len(client.requests), 2)

    def test_request_budget_spans_access_and_workspace_graph_reads(self) -> None:
        clock = _MonotonicClock()

        class _AdvancingResponse(_Response):
            def __enter__(self):
                clock.value += 2.0
                return self

        client = _ScriptedRawClient(
            _AdvancingResponse({}),
            _AdvancingResponse({}),
            sleep=clock.sleep,
            monotonic=clock,
            request_budget_seconds=3.0,
        )

        class _Access:
            def decide(self, **_: str) -> AccessDecision:
                client.get("/sites/fixed/lists/fixed/items")
                return AccessDecision.assigned()

        class _Workspace:
            def read_synthetic_workspace(self, **_: str) -> dict:
                client.get("/sites/fixed/lists/fixed/items")
                return {}

        bff = TestEnvironmentBff(
            expected_tenant_id="synthetic-tenant",
            access_decision_port=_Access(),
            graph_rest_port=_Workspace(),
            bpmn_asset_port=object(),
            request_budget_factory=client.request_budget,
        )
        response = bff.get_workspace(
            claims=ValidatedClaims(
                object_id="actor-notary",
                tenant_id="synthetic-tenant",
                subject="actor-notary",
            ),
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

        self.assertEqual(
            (response.status_code, response.body),
            (503, {"status": 503, "error": {"code": "SERVICE_UNAVAILABLE"}}),
        )
        self.assertEqual(client.timeouts, [3.0, 1.0])

    def test_timeout_configuration_can_only_tighten_production_bounds(self) -> None:
        for options in (
            {"timeout_seconds": GRAPH_IO_TIMEOUT_SECONDS + 0.1},
            {"request_deadline_seconds": GRAPH_REQUEST_DEADLINE_SECONDS + 0.1},
        ):
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    RawGraphV1Client(_TokenProvider(), **options)

    def test_rejects_oversized_or_non_object_responses(self) -> None:
        oversized = _ScriptedRawClient(
            _Response(b"x" * (MAX_RESPONSE_BYTES + 1)), sleep=lambda _: None
        )
        with self.assertRaises(GraphResponseError):
            oversized.get("/sites/fixed/lists/fixed/items")

        non_object = _ScriptedRawClient(_Response([]), sleep=lambda _: None)
        with self.assertRaises(GraphResponseError):
            non_object.get("/sites/fixed/lists/fixed/items")


class SyntheticWorkspaceGraphRestAdapterTests(unittest.TestCase):
    def test_reads_only_fixed_lists_and_returns_strict_projection(self) -> None:
        client = _FakeGraphClient(
            _page(_case_projection()),
            _page(*(_task_projection(task) for task in TASKS)),
        )
        adapter = SyntheticWorkspaceGraphRestAdapter(client)

        result = adapter.read_synthetic_workspace(
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
        )

        self.assertEqual(
            result,
            {
                "status": MATTER_STATUS,
                "deadline": DEADLINE,
                "tasks": [
                    {
                        "taskId": task["task_id"],
                        "title": task["title"],
                        "stepCode": task["step_code"],
                        "status": task["status"],
                        "requiresNotaryApproval": task["requires_notary_approval"],
                        "dueAt": task["due_at"],
                    }
                    for task in TASKS
                ],
            },
        )
        self.assertNotIn("bpmn", result)
        self.assertEqual(len(client.paths), 2)
        self.assertIn("/lists/588d4a41-f538-4f37-acfb-63ff283e0910/items?", client.paths[0])
        self.assertIn("$expand=fields($select=NacCaseId,Vorgangstyp,Status,FristNaechsteAktion)", client.paths[0])
        self.assertIn("/lists/720ef1d4-8496-4ecb-aa1f-5fa4568343f2/items?", client.paths[1])
        self.assertNotIn("funktion8.sharepoint.com/sites/NaC-Notar-01", "".join(client.paths))

    def test_manipulated_scope_is_absent_without_graph_call(self) -> None:
        client = _FakeGraphClient()
        adapter = SyntheticWorkspaceGraphRestAdapter(client)

        for workspace_id, matter_id in (
            ("notary_team_02", ALLOWED_MATTER_ID),
            (ALLOWED_WORKSPACE_ID, "NAC-SYN-MATTER-999"),
        ):
            with self.subTest(workspace_id=workspace_id, matter_id=matter_id):
                self.assertIsNone(
                    adapter.read_synthetic_workspace(
                        workspace_id=workspace_id,
                        matter_id=matter_id,
                    )
                )
        self.assertEqual(client.paths, [])

    def test_missing_case_is_absent_but_duplicate_or_broad_projection_fails(self) -> None:
        missing = SyntheticWorkspaceGraphRestAdapter(_FakeGraphClient(_page()))
        self.assertIsNone(
            missing.read_synthetic_workspace(
                workspace_id=ALLOWED_WORKSPACE_ID,
                matter_id=ALLOWED_MATTER_ID,
            )
        )

        duplicate = SyntheticWorkspaceGraphRestAdapter(
            _FakeGraphClient(_page(_case_projection(), _case_projection()))
        )
        with self.assertRaises(GraphResponseError):
            duplicate.read_synthetic_workspace(
                workspace_id=ALLOWED_WORKSPACE_ID,
                matter_id=ALLOWED_MATTER_ID,
            )

        broad_case = _case_projection()
        broad_case["Mandant"] = "DO_NOT_EXPOSE"
        broad = SyntheticWorkspaceGraphRestAdapter(_FakeGraphClient(_page(broad_case)))
        with self.assertRaises(GraphResponseError):
            broad.read_synthetic_workspace(
                workspace_id=ALLOWED_WORKSPACE_ID,
                matter_id=ALLOWED_MATTER_ID,
            )

    def test_rejects_next_link_to_another_host(self) -> None:
        client = _FakeGraphClient(
            _page(
                _case_projection(),
                next_link="https://example.invalid/v1.0/sites/fixed/lists/fixed/items?$skiptoken=x",
            )
        )
        adapter = SyntheticWorkspaceGraphRestAdapter(client)

        with self.assertRaises(GraphResponseError):
            adapter.read_synthetic_workspace(
                workspace_id=ALLOWED_WORKSPACE_ID,
                matter_id=ALLOWED_MATTER_ID,
            )
        self.assertEqual(len(client.paths), 1)

    def test_collection_reader_rejects_unhardened_client(self) -> None:
        client = _FakeGraphClient(_page())
        client.redirects_allowed = True
        with self.assertRaises(GraphRequestError):
            read_bounded_collection(
                client,
                binding=synthetic_list_binding("Akten"),
                fields=("NacCaseId",),
                filter_expression=f"fields/NacCaseId eq '{ALLOWED_MATTER_ID}'",
                top=2,
            )


class LiveAccessDecisionAdapterTests(unittest.TestCase):
    def _adapter(self, *responses: object) -> tuple[LiveAccessDecisionAdapter, _FakeGraphClient]:
        client = _FakeGraphClient(*responses)
        return (
            LiveAccessDecisionAdapter(
                client,
                expected_tenant_id="synthetic-tenant",
                reference_time="2026-07-14T12:00:00Z",
            ),
            client,
        )

    def _decide(self, adapter: LiveAccessDecisionAdapter, actor_id: str):
        return adapter.decide(
            actor_id=actor_id,
            tenant_id="synthetic-tenant",
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

    def test_lead_notary_and_assigned_clerk_are_assigned_without_grant_read(self) -> None:
        for actor, role in (
            ("actor-notary", "notary"),
            ("actor-clerk", "notary_clerk"),
        ):
            with self.subTest(actor=actor, role=role):
                adapter, client = self._adapter(_page(_access_case()))
                decision = self._decide(adapter, actor)
                self.assertIs(decision.mode, AccessMode.ASSIGNED)
                self.assertEqual(decision.subject_id, actor)
                self.assertEqual(decision.role, role)
                self.assertEqual(decision.decision_id, "access:NAC-SYN-MATTER-001:1")
                self.assertEqual(decision.decision_version, "policy-v1")
                self.assertEqual(decision.issued_at, "2026-07-14T12:00:00Z")
                self.assertEqual(decision.expires_at, "2026-07-14T12:05:00Z")
                self.assertIsNone(decision.reason)
                self.assertEqual(len(client.paths), 1)
                self.assertIn("FederfuehrenderNotar,Sachbearbeitung", client.paths[0])

    def test_active_time_bounded_and_audited_deputy_is_allowed(self) -> None:
        adapter, client = self._adapter(
            _page(_access_case()),
            _page(_grant()),
            _page(_audit()),
        )

        decision = self._decide(adapter, "actor-deputy")
        self.assertIs(decision.mode, AccessMode.DEPUTY)
        self.assertEqual(decision.subject_id, "actor-deputy")
        self.assertEqual(decision.role, "deputy_clerk")
        self.assertEqual(decision.reason, "Synthetische Urlaubsvertretung")
        self.assertEqual(decision.expires_at, "2026-07-14T12:05:00Z")
        self.assertTrue(decision.active_approved_grant)
        self.assertTrue(decision.matching_audit_event)
        self.assertEqual(len(client.paths), 3)
        self.assertIn("/lists/ec12d339-d9b7-45e9-be45-38dadd917746/items?", client.paths[1])
        self.assertIn("/lists/327181c2-e402-48e9-bcfa-1f5081b45d9c/items?", client.paths[2])
        self.assertIn("CorrelationId", client.paths[2])

    def test_notary_deputy_grant_maps_to_canonical_role(self) -> None:
        adapter, _ = self._adapter(
            _page(_access_case()),
            _page(_grant(GrantedRole="NotarVertretung")),
            _page(_audit()),
        )

        decision = self._decide(adapter, "actor-deputy")

        self.assertIs(decision.mode, AccessMode.DEPUTY)
        self.assertEqual(decision.role, "deputy_notary")

    def test_deputy_fails_closed_for_invalid_role_window_approval_or_audit(self) -> None:
        invalid_grants = (
            _grant(GrantedRole="NurLesen"),
            _grant(ValidFrom="2026-07-14T12:00:01Z"),
            _grant(ValidUntil="2026-07-14T12:00:00Z"),
            _grant(Reason=" "),
            _grant(Reason="Vertretung fuer Max Mustermann"),
            _grant(Status="Widerrufen"),
            _grant(ApprovedBy="other-notary"),
            _grant(AuditCorrelationId=""),
        )
        for grant in invalid_grants:
            with self.subTest(grant=grant):
                adapter, client = self._adapter(_page(_access_case()), _page(grant))
                self.assertIs(self._decide(adapter, "actor-deputy").mode, AccessMode.DENY)
                self.assertEqual(len(client.paths), 2)

        for audit in (_audit(Action="GrantRequested"), _audit(ObjectId="other"), None):
            with self.subTest(audit=audit):
                audit_page = _page() if audit is None else _page(audit)
                adapter, _ = self._adapter(_page(_access_case()), _page(_grant()), audit_page)
                self.assertIs(self._decide(adapter, "actor-deputy").mode, AccessMode.DENY)

    def test_wrong_scope_and_missing_matter_are_indistinguishable_denials(self) -> None:
        adapter, client = self._adapter()
        requests = (
            {"tenant_id": "other-tenant"},
            {"workspace_id": "notary_team_02"},
            {"matter_id": "NAC-SYN-MATTER-999"},
            {"purpose": "export_all_matters"},
        )
        for changes in requests:
            request = {
                "actor_id": "actor-notary",
                "tenant_id": "synthetic-tenant",
                "workspace_id": ALLOWED_WORKSPACE_ID,
                "matter_id": ALLOWED_MATTER_ID,
                "purpose": ALLOWED_PURPOSE,
            }
            request.update(changes)
            self.assertIs(adapter.decide(**request).mode, AccessMode.DENY)
        self.assertEqual(client.paths, [])

        missing, _ = self._adapter(_page())
        failed, _ = self._adapter(GraphRequestError("SENSITIVE GRAPH FAILURE"))
        self.assertIs(self._decide(missing, "actor-notary").mode, AccessMode.DENY)
        self.assertIs(self._decide(failed, "actor-notary").mode, AccessMode.DENY)

    def test_ambiguous_assignment_or_grant_fails_closed(self) -> None:
        duplicate_case, _ = self._adapter(_page(_access_case(), _access_case()))
        self.assertIs(self._decide(duplicate_case, "actor-notary").mode, AccessMode.DENY)

        duplicate_grant, _ = self._adapter(
            _page(_access_case()),
            _page(_grant(), _grant(GrantId="NAC-SYN-GRANT-002")),
        )
        self.assertIs(self._decide(duplicate_grant, "actor-deputy").mode, AccessMode.DENY)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
