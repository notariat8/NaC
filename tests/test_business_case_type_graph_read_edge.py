from __future__ import annotations

import io
import sys
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_m365_graph.business_case_type_registry import (  # noqa: E402
    GRAPH_BASE_URL,
    MAX_RESPONSE_BYTES,
    GraphBusinessCaseTypeHttpError,
    GraphBusinessCaseTypeRegistryReadAdapter,
    GraphBusinessCaseTypeRegistryReadScope,
    GraphBusinessCaseTypeResponseError,
    GraphBusinessCaseTypeRestClient,
    NoRedirectHandler,
)
from nac_m365_graph.graph_client import GraphHttpError, GraphRestClient  # noqa: E402


TYPE_ID = "immobilienkaufvertrag"
VERSION = "a" * 64


class FakeGraphClient:
    base_url = GRAPH_BASE_URL
    redirects_allowed = False
    retains_error_body = False

    def __init__(self, responses=()):
        self.responses = list(responses)
        self.calls: list[str] = []

    def get(self, path: str) -> dict[str, object]:
        self.calls.append(path)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def scope(**changes) -> GraphBusinessCaseTypeRegistryReadScope:
    values = {
        "site_id": "site-approved",
        "list_id": "list-approved",
        "operation": "case_create_validation",
        "role": "notary",
        "runtime_permission": "Sites.Selected",
        "site_grant_role": "read",
    }
    values.update(changes)
    return GraphBusinessCaseTypeRegistryReadScope(**values)


def item(**changes) -> dict[str, object]:
    values: dict[str, object] = {
        "id": "graph-item-redacted-at-boundary",
        "eTag": '"etag-1"',
        "fields": {
            "BusinessCaseTypeId": TYPE_ID,
            "LifecycleStatus": "active",
            "Selectable": True,
            "CatalogVersion": VERSION,
            "ViewerUrl": "ignored",
        },
        "unexpected": "ignored",
    }
    values.update(changes)
    return values


def page(*rows, next_link=None):
    payload = {"value": list(rows)}
    if next_link is not None:
        payload["@odata.nextLink"] = next_link
    return payload


def adapter(client, read_scope=None):
    return GraphBusinessCaseTypeRegistryReadAdapter(client, read_scope or scope())


def fetch(target, **changes):
    values = {
        "site_id": "site-approved",
        "business_case_type_id": TYPE_ID,
        "catalog_version": VERSION,
        "if_none_match": None,
    }
    values.update(changes)
    return target.fetch_registry(**values)


def next_link(skiptoken="page-2", **changes):
    values = {
        "$select": "id,eTag",
        "$expand": "fields($select=BusinessCaseTypeId,LifecycleStatus,Selectable,CatalogVersion)",
        "$filter": f"fields/BusinessCaseTypeId eq '{TYPE_ID}' and fields/CatalogVersion eq '{VERSION}'",
    }
    if skiptoken is not None:
        values["$skiptoken"] = skiptoken
    values.update(changes.pop("query", {}))
    path = changes.pop("path", "/v1.0/sites/site-approved/lists/list-approved/items")
    host = changes.pop("host", "graph.microsoft.com")
    scheme = changes.pop("scheme", "https")
    assert not changes
    return urllib.parse.urlunsplit(
        (scheme, host, path, urllib.parse.urlencode(values, quote_via=urllib.parse.quote), "")
    )


class GraphBusinessCaseTypeRegistryReadAdapterTests(unittest.TestCase):
    def test_client_capabilities_are_required_before_transport(self):
        class MissingCapabilities:
            def __init__(self):
                self.calls = []

            def get(self, path):
                self.calls.append(path)
                return page()

        class MissingBase(FakeGraphClient):
            base_url = None

        for client in (MissingCapabilities(), MissingBase()):
            with self.subTest(client=type(client).__name__):
                self.assertEqual("UNAVAILABLE", fetch(adapter(client)).status)
                self.assertEqual([], client.calls)

    def test_existing_graph_rest_client_is_incompatible_before_transport(self):
        class TokenProvider:
            def __init__(self):
                self.calls = 0

            def fetch_access_token(self):
                self.calls += 1
                return "must-not-be-read"

        token_provider = TokenProvider()
        result = fetch(adapter(GraphRestClient(token_provider)))
        self.assertEqual("UNAVAILABLE", result.status)
        self.assertEqual(0, token_provider.calls)

    def test_initial_get_has_bound_relative_path_exact_projection_and_filter(self):
        client = FakeGraphClient([page(item())])
        result = fetch(adapter(client))

        self.assertEqual("OK", result.status)
        self.assertTrue(result.pages_complete)
        self.assertEqual(1, len(result.rows))
        self.assertNotIn("graph-item", repr(result))
        self.assertEqual(1, len(client.calls))
        parsed = urllib.parse.urlsplit(client.calls[0])
        self.assertEqual("", parsed.scheme)
        self.assertEqual("/sites/site-approved/lists/list-approved/items", parsed.path)
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual({"id,eTag"}, set(query["$select"]))
        self.assertEqual(
            {"fields($select=BusinessCaseTypeId,LifecycleStatus,Selectable,CatalogVersion)"},
            set(query["$expand"]),
        )
        self.assertEqual(
            {f"fields/BusinessCaseTypeId eq '{TYPE_ID}' and fields/CatalogVersion eq '{VERSION}'"},
            set(query["$filter"]),
        )

    def test_scope_errors_block_before_transport(self):
        invalid_scopes = [
            scope(site_id=""),
            scope(list_id=""),
            scope(operation="schema_apply"),
            scope(role="Viewer"),
            scope(runtime_permission="Sites.Read.All"),
            scope(site_grant_role="write"),
        ]
        for invalid_scope in invalid_scopes:
            with self.subTest(invalid_scope=invalid_scope.operation):
                client = FakeGraphClient()
                result = fetch(adapter(client, invalid_scope))
                self.assertEqual("UNAVAILABLE", result.status)
                self.assertEqual([], client.calls)

        client = FakeGraphClient()
        result = fetch(adapter(client), site_id="site-other")
        self.assertEqual("UNAVAILABLE", result.status)
        self.assertEqual([], client.calls)

    def test_all_contract_operation_role_bindings_are_accepted(self):
        bindings = {
            "case_create_validation": "runtime_service",
            "matter_type_correction_validation": "MatterCorrector",
            "backfill_validation": "BackfillOperator",
            "optional_process_read": "notary_clerk",
        }
        for operation, role in bindings.items():
            with self.subTest(operation=operation):
                client = FakeGraphClient([page()])
                result = fetch(adapter(client, scope(operation=operation, role=role)))
                self.assertEqual("OK", result.status)

    def test_wrong_graph_base_blocks_before_transport(self):
        client = FakeGraphClient()
        client.base_url = "https://graph.microsoft.com/beta"
        self.assertEqual("UNAVAILABLE", fetch(adapter(client)).status)
        self.assertEqual([], client.calls)

    def test_multipage_read_uses_validated_relative_followup(self):
        link = next_link()
        client = FakeGraphClient([page(item(), next_link=link), page()])
        result = fetch(adapter(client))

        self.assertEqual("OK", result.status)
        self.assertEqual(1, len(result.rows))
        self.assertEqual(2, len(client.calls))
        self.assertTrue(client.calls[1].startswith("/sites/site-approved/lists/list-approved/items?"))

    def test_next_link_host_version_site_list_collection_and_query_drift_fail_closed(self):
        invalid_links = [
            next_link(host="example.invalid"),
            next_link(scheme="http"),
            next_link(path="/beta/sites/site-approved/lists/list-approved/items"),
            next_link(path="/v1.0/sites/site-other/lists/list-approved/items"),
            next_link(path="/v1.0/sites/site-approved/lists/list-other/items"),
            next_link(path="/v1.0/sites/site-approved/lists/list-approved/items/1"),
            next_link(query={"$select": "id"}),
            next_link(query={"$expand": "fields"}),
            next_link(query={"$filter": "fields/BusinessCaseTypeId eq 'other'"}),
            next_link(query={"$top": "1"}),
            "/v1.0/sites/site-approved/lists/list-approved/items",
        ]
        for link in invalid_links:
            with self.subTest(link=link):
                client = FakeGraphClient([page(item(), next_link=link)])
                result = fetch(adapter(client))
                self.assertEqual("UNAVAILABLE", result.status)
                self.assertFalse(result.pages_complete)
                self.assertEqual((), result.rows)
                self.assertEqual(1, len(client.calls))

    def test_loop_and_page_limit_fail_without_partial_rows(self):
        link = next_link()
        loop_client = FakeGraphClient([page(item(), next_link=link), page(next_link=link)])
        loop_result = fetch(adapter(loop_client))
        self.assertEqual("UNAVAILABLE", loop_result.status)
        self.assertEqual((), loop_result.rows)

        links = [next_link(str(index)) for index in range(1, 101)]
        responses = [page(next_link=link) for link in links]
        page_client = FakeGraphClient(responses)
        page_result = fetch(adapter(page_client))
        self.assertEqual("UNAVAILABLE", page_result.status)
        self.assertEqual(100, len(page_client.calls))

    def test_next_link_to_initial_page_is_an_immediate_loop(self):
        client = FakeGraphClient([page(item(), next_link=next_link(None))])
        result = fetch(adapter(client))
        self.assertEqual("UNAVAILABLE", result.status)
        self.assertEqual(1, len(client.calls))
        self.assertEqual((), result.rows)

    def test_item_limit_accepts_1000_and_rejects_1001(self):
        accepted = FakeGraphClient([page(*(item(id=str(index)) for index in range(1000)))])
        accepted_result = fetch(adapter(accepted))
        self.assertEqual("OK", accepted_result.status)
        self.assertEqual(1000, len(accepted_result.rows))

        rejected = FakeGraphClient([page(*(item(id=str(index)) for index in range(1001)))])
        rejected_result = fetch(adapter(rejected))
        self.assertEqual("UNAVAILABLE", rejected_result.status)
        self.assertEqual((), rejected_result.rows)

    def test_malformed_payloads_and_field_types_fail_closed(self):
        malformed = [
            None,
            {},
            {"value": None},
            {"value": [None]},
            page({"id": "1", "eTag": '"e"'}),
            page(item(id=None)),
            page(item(eTag=1)),
            page(item(fields={"BusinessCaseTypeId": TYPE_ID})),
            page(
                item(
                    fields={
                        "BusinessCaseTypeId": TYPE_ID,
                        "LifecycleStatus": "active",
                        "Selectable": 1,
                        "CatalogVersion": VERSION,
                    }
                )
            ),
            {"value": [], "@odata.nextLink": None},
        ]
        for payload in malformed:
            with self.subTest(payload=payload):
                result = fetch(adapter(FakeGraphClient([payload])))
                self.assertEqual("UNAVAILABLE", result.status)
                self.assertEqual((), result.rows)

    def test_zero_and_duplicate_rows_are_complete_ok_for_domain_decision(self):
        zero = fetch(adapter(FakeGraphClient([page()])), if_none_match='"etag-1"')
        duplicate = fetch(
            adapter(FakeGraphClient([page(item(), item(id="second"))])),
            if_none_match='"etag-1"',
        )
        self.assertEqual(("OK", True, 0), (zero.status, zero.pages_complete, len(zero.rows)))
        self.assertEqual(("OK", True, 2), (duplicate.status, duplicate.pages_complete, len(duplicate.rows)))

    def test_not_modified_requires_one_exact_row_after_complete_read(self):
        link = next_link()
        client = FakeGraphClient([page(next_link=link), page(item())])
        unchanged = fetch(adapter(client), if_none_match='"etag-1"')
        self.assertEqual("NOT_MODIFIED", unchanged.status)
        self.assertEqual(2, len(client.calls))
        self.assertTrue(all("If-None-Match" not in call for call in client.calls))

        changed = fetch(adapter(FakeGraphClient([page(item(eTag='"etag-2"'))])), if_none_match='"etag-1"')
        wrong_id_fields = dict(item()["fields"])
        wrong_id_fields["BusinessCaseTypeId"] = "other"
        wrong_id = fetch(adapter(FakeGraphClient([page(item(fields=wrong_id_fields))])), if_none_match='"etag-1"')
        self.assertEqual("OK", changed.status)
        self.assertEqual("OK", wrong_id.status)

    def test_http_timeout_and_unknown_errors_map_to_safe_codes(self):
        cases = [
            (GraphBusinessCaseTypeHttpError(401), "transport_authentication_failed"),
            (GraphBusinessCaseTypeHttpError(403), "transport_authorization_failed"),
            (GraphBusinessCaseTypeHttpError(429), "transport_rate_limited"),
            (GraphBusinessCaseTypeHttpError(504), "transport_timeout"),
            (GraphHttpError(401, "sensitive body"), "transport_unavailable"),
            (GraphHttpError(500, "sensitive body"), "transport_unavailable"),
            (TimeoutError("sensitive path"), "transport_timeout"),
            (RuntimeError("sensitive id and body"), "transport_unavailable"),
        ]
        for error, reason_code in cases:
            with self.subTest(error=type(error).__name__):
                result = fetch(adapter(FakeGraphClient([error])))
                self.assertEqual("UNAVAILABLE", result.status)
                self.assertEqual(reason_code, result.reason_code)
                self.assertEqual((), result.rows)
                self.assertNotIn("sensitive", repr(result))


class GraphBusinessCaseTypeRestClientTests(unittest.TestCase):
    class TokenProvider:
        def fetch_access_token(self):
            return "synthetic-access-value"

    def test_uses_no_redirect_handler_and_rejects_opener_injection(self):
        client = GraphBusinessCaseTypeRestClient(self.TokenProvider())
        handler = NoRedirectHandler()
        self.assertIsNone(
            handler.redirect_request(None, None, 302, "Found", {}, "https://example.invalid")
        )
        with self.assertRaises(TypeError):
            GraphBusinessCaseTypeRestClient(self.TokenProvider(), opener=object())
        fake_opener = mock.Mock()
        fake_response = object()
        fake_opener.open.return_value = fake_response
        request = urllib.request.Request(GRAPH_BASE_URL + "/sites/redacted")
        with mock.patch("urllib.request.build_opener", return_value=fake_opener) as build_opener:
            self.assertIs(fake_response, client._open(request))
        self.assertIsInstance(build_opener.call_args.args[0], NoRedirectHandler)
        fake_opener.open.assert_called_once_with(request, timeout=30)
        self.assertFalse(client.redirects_allowed)
        self.assertFalse(client.retains_error_body)

    def test_http_exception_retains_status_but_no_raw_body_or_url(self):
        sensitive_body = b"sensitive-body-must-not-be-retained"

        class RejectingOpener:
            def open(self, request, timeout):
                raise urllib.error.HTTPError(
                    request.full_url,
                    403,
                    "Forbidden",
                    {},
                    io.BytesIO(sensitive_body),
                )

        client = GraphBusinessCaseTypeRestClient(self.TokenProvider())
        client._open = lambda request: RejectingOpener().open(request, 30)
        with self.assertRaises(GraphBusinessCaseTypeHttpError) as raised:
            client.get("/sites/redacted")
        error = raised.exception
        self.assertEqual(403, error.status)
        self.assertFalse(hasattr(error, "body"))
        self.assertIsNone(error.__context__)
        self.assertNotIn("sensitive", repr(error))
        self.assertNotIn("sites", repr(error))

    def test_oversized_response_is_rejected_before_json_parsing(self):
        class OversizedResponse:
            requested_size = None

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self, size=-1):
                self.requested_size = size
                return b"x" * size

        response = OversizedResponse()
        client = GraphBusinessCaseTypeRestClient(self.TokenProvider())
        client._open = lambda _request: response
        with self.assertRaises(GraphBusinessCaseTypeResponseError):
            client.get("/sites/redacted")
        self.assertEqual(MAX_RESPONSE_BYTES + 1, response.requested_size)

    def test_dedicated_client_is_get_only_with_exact_base(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self, size=-1):
                return b'{"value": []}'[:size]

        class RecordingOpener:
            def __init__(self):
                self.requests = []

            def open(self, request, timeout):
                self.requests.append((request, timeout))
                return Response()

        opener = RecordingOpener()
        client = GraphBusinessCaseTypeRestClient(self.TokenProvider())
        client._open = lambda request: opener.open(request, 30)
        self.assertEqual({"value": []}, client.get("/sites/redacted"))
        request, timeout = opener.requests[0]
        self.assertEqual("GET", request.get_method())
        self.assertEqual(GRAPH_BASE_URL + "/sites/redacted", request.full_url)
        self.assertEqual(30, timeout)

        wrong_base = GraphBusinessCaseTypeRestClient(
            self.TokenProvider(),
            base_url="https://graph.microsoft.com/beta",
        )
        with self.assertRaisesRegex(ValueError, "v1.0"):
            wrong_base.get("/sites/redacted")


if __name__ == "__main__":
    unittest.main()
