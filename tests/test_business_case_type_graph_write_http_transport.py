from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_m365_graph.business_case_type_write_plan import GraphWriteRequest
from nac_m365_graph.business_case_type_write_transport import (
    MAX_RESPONSE_BYTES,
    GraphRestV1WriteTransport,
    GraphWriteTransportError,
    HttpTransportResponse,
)


AKTEN_COLLECTION = (
    "https://graph.microsoft.com/v1.0/sites/site-id/lists/akten-list/items"
)
AUFGABEN_COLLECTION = (
    "https://graph.microsoft.com/v1.0/sites/site-id/lists/aufgaben-list/items"
)
AKTEN_ITEM_GET = (
    f"{AKTEN_COLLECTION}/17?"
    "$select=id,eTag&$expand=fields($select=Status)"
)


class _TokenProvider:
    def __init__(self, token: str = "synthetic-token") -> None:
        self.token = token
        self.calls = 0

    def fetch_access_token(self) -> str:
        self.calls += 1
        return self.token


class _ScriptedHttpPort:
    def __init__(self, response: HttpTransportResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def request(self, **request: object) -> HttpTransportResponse:
        self.calls.append(request)
        return self.response


def _transport(
    response: HttpTransportResponse,
) -> tuple[GraphRestV1WriteTransport, _TokenProvider, _ScriptedHttpPort]:
    provider = _TokenProvider()
    http_port = _ScriptedHttpPort(response)
    return (
        GraphRestV1WriteTransport(
            provider,
            http_port,
            (AKTEN_COLLECTION, AUFGABEN_COLLECTION),
        ),
        provider,
        http_port,
    )


class GraphRestV1WriteTransportTests(unittest.TestCase):
    def test_get_uses_exact_policy_and_filters_response_headers(self) -> None:
        transport, provider, http_port = _transport(
            HttpTransportResponse(
                200,
                b'{"eTag":"etag-17","id":"17"}',
                {
                    "etag": "etag-17",
                    "Location": f"{AKTEN_COLLECTION}/17",
                    "Retry-After": "3",
                    "request-id": "raw-request-id",
                },
            )
        )

        response = transport.request(
            GraphWriteRequest(
                method="GET",
                url=AKTEN_ITEM_GET,
                headers={},
                payload=None,
                phase="freshness",
            )
        )

        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(http_port.calls), 1)
        self.assertEqual(
            http_port.calls[0],
            {
                "method": "GET",
                "url": AKTEN_ITEM_GET,
                "headers": {
                    "Authorization": "Bearer synthetic-token",
                    "Accept": "application/json",
                },
                "body": None,
                "follow_redirects": False,
                "automatic_retries": 0,
                "max_response_bytes": MAX_RESPONSE_BYTES,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, {"eTag": "etag-17", "id": "17"})
        self.assertEqual(
            response.headers,
            {
                "ETag": "etag-17",
                "Location": f"{AKTEN_COLLECTION}/17",
                "Retry-After": "3",
            },
        )

    def test_post_and_patch_send_canonical_json_and_exact_headers(self) -> None:
        transport, _, http_port = _transport(
            HttpTransportResponse(200, b'{"id":"17"}')
        )
        transport.request(
            GraphWriteRequest(
                method="POST",
                url=AKTEN_COLLECTION,
                headers={"Content-Type": "application/json"},
                payload={"fields": {"b": True, "a": "Umlaut: \u00e4"}},
                phase="write",
            )
        )
        transport.request(
            GraphWriteRequest(
                method="PATCH",
                url=f"{AUFGABEN_COLLECTION}/23/fields",
                headers={
                    "Content-Type": "application/json",
                    "If-Match": 'W/"etag-23"',
                },
                payload={"Status": "Erledigt"},
                phase="write",
            )
        )

        self.assertEqual(len(http_port.calls), 2)
        self.assertEqual(
            http_port.calls[0]["headers"],
            {
                "Authorization": "Bearer synthetic-token",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        self.assertEqual(
            http_port.calls[0]["body"],
            '{"fields":{"a":"Umlaut: \u00e4","b":true}}'.encode(),
        )
        self.assertEqual(
            http_port.calls[1]["headers"],
            {
                "Authorization": "Bearer synthetic-token",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "If-Match": 'W/"etag-23"',
            },
        )

    def test_only_two_exact_graph_v1_collection_bindings_are_accepted(self) -> None:
        provider = _TokenProvider()
        http_port = _ScriptedHttpPort(HttpTransportResponse(200, b"{}"))
        invalid_bindings = (
            (AKTEN_COLLECTION,),
            (AKTEN_COLLECTION, AKTEN_COLLECTION),
            (
                AKTEN_COLLECTION,
                "https://graph.microsoft.com/beta/sites/site-id/lists/list/items",
            ),
            (
                AKTEN_COLLECTION,
                "https://graph.microsoft.com/v1.0/sites/site-id/_api/list/items",
            ),
        )

        for bindings in invalid_bindings:
            with self.subTest(bindings=bindings):
                with self.assertRaises(ValueError):
                    GraphRestV1WriteTransport(provider, http_port, bindings)  # type: ignore[arg-type]

    def test_rejected_requests_do_not_fetch_a_token_or_call_http(self) -> None:
        transport, provider, http_port = _transport(
            HttpTransportResponse(200, b"{}")
        )
        rejected = (
            GraphWriteRequest(
                "DELETE", AKTEN_COLLECTION, {}, None, "write"
            ),
            GraphWriteRequest(
                "GET",
                "https://graph.microsoft.com/beta/sites/site-id/lists/list/items",
                {},
                None,
                "readback",
            ),
            GraphWriteRequest(
                "GET",
                "https://graph.microsoft.com/v1.0/sites/site-id/lists/foreign/items",
                {},
                None,
                "readback",
            ),
            GraphWriteRequest(
                "GET",
                f"{AKTEN_COLLECTION}/../foreign",
                {},
                None,
                "readback",
            ),
            GraphWriteRequest(
                "GET",
                AKTEN_COLLECTION,
                {"Accept": "application/json"},
                None,
                "readback",
            ),
            GraphWriteRequest(
                "POST",
                AKTEN_COLLECTION,
                {"Content-Type": "application/json; charset=utf-8"},
                {},
                "write",
            ),
            GraphWriteRequest(
                "PATCH",
                f"{AKTEN_COLLECTION}/17/fields",
                {"Content-Type": "application/json"},
                {},
                "write",
            ),
            GraphWriteRequest(
                "POST",
                f"{AKTEN_COLLECTION}/17/driveItem/createLink",
                {"Content-Type": "application/json"},
                {},
                "write",
            ),
            GraphWriteRequest(
                "PATCH",
                f"{AKTEN_COLLECTION}/17/fields/anything",
                {
                    "Content-Type": "application/json",
                    "If-Match": "synthetic-etag-17",
                },
                {},
                "write",
            ),
            GraphWriteRequest(
                "PATCH",
                f"{AKTEN_COLLECTION}/17/fields",
                {
                    "Content-Type": "application/json",
                    "If-Match": "*",
                },
                {},
                "write",
            ),
            GraphWriteRequest(
                "GET",
                AKTEN_ITEM_GET,
                {},
                None,
                "write",
            ),
        )

        for request in rejected:
            with self.subTest(request=request):
                with self.assertRaisesRegex(
                    GraphWriteTransportError, r"\Arequest_not_allowed\Z"
                ):
                    transport.request(request)
        self.assertEqual(provider.calls, 0)
        self.assertEqual(http_port.calls, [])

    def test_response_is_bounded_and_must_be_an_object_or_empty(self) -> None:
        invalid_bodies = (
            b"[]",
            b"null",
            b'"text"',
            b" ",
            b'{"duplicate":1,"duplicate":2}',
            b'{"number":NaN}',
            b"x" * (MAX_RESPONSE_BYTES + 1),
        )

        for body in invalid_bodies:
            with self.subTest(body_length=len(body)):
                transport, _, http_port = _transport(
                    HttpTransportResponse(200, body)
                )
                with self.assertRaises(GraphWriteTransportError):
                    transport.request(
                        GraphWriteRequest(
                            "GET", AKTEN_ITEM_GET, {}, None, "readback"
                        )
                    )
                self.assertEqual(len(http_port.calls), 1)

        transport, _, _ = _transport(HttpTransportResponse(204, b""))
        self.assertEqual(
            transport.request(
                GraphWriteRequest("GET", AKTEN_ITEM_GET, {}, None, "readback")
            ).body,
            {},
        )

    def test_http_error_body_is_redacted_and_redirect_is_not_followed(self) -> None:
        transport, _, http_port = _transport(
            HttpTransportResponse(
                429,
                b'{"error":{"message":"raw tenant detail"}}',
                {"Retry-After": "5"},
            )
        )

        response = transport.request(
            GraphWriteRequest("GET", AKTEN_ITEM_GET, {}, None, "readback")
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.body, {})
        self.assertEqual(response.headers, {"Retry-After": "5"})
        self.assertIs(http_port.calls[0]["follow_redirects"], False)
        self.assertEqual(http_port.calls[0]["automatic_retries"], 0)


if __name__ == "__main__":
    unittest.main()
