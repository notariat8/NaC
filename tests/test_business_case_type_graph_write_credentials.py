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


class _FailingTokenProvider:
    def __init__(self) -> None:
        self.calls = 0

    def fetch_access_token(self) -> str:
        self.calls += 1
        raise RuntimeError(
            "raw-provider-secret token=must-not-escape certificate=/private/path"
        )


class _TokenProvider:
    def __init__(self, token: object) -> None:
        self.token = token
        self.calls = 0

    def fetch_access_token(self) -> str:
        self.calls += 1
        return self.token  # type: ignore[return-value]


class _RecordingHttpPort:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def request(self, **request: object) -> HttpTransportResponse:
        self.calls.append(request)
        if self.fail:
            raise RuntimeError(
                "raw-http-secret Authorization=Bearer must-not-escape"
            )
        return HttpTransportResponse(200, b"{}")


class GraphRestV1WriteCredentialBoundaryTests(unittest.TestCase):
    def test_provider_failure_is_stable_redacted_and_skips_http(self) -> None:
        provider = _FailingTokenProvider()
        http_port = _RecordingHttpPort()
        transport = GraphRestV1WriteTransport(
            provider,
            http_port,
            (AKTEN_COLLECTION, AUFGABEN_COLLECTION),
        )

        with self.assertRaises(GraphWriteTransportError) as raised:
            transport.request(
                GraphWriteRequest("GET", AKTEN_ITEM_GET, {}, None, "freshness")
            )

        self.assertEqual(raised.exception.reason_code, "access_token_unavailable")
        self.assertEqual(str(raised.exception), "access_token_unavailable")
        self.assertNotIn("raw-provider-secret", repr(raised.exception))
        self.assertEqual(provider.calls, 1)
        self.assertEqual(http_port.calls, [])

    def test_invalid_token_values_are_redacted_and_skip_http(self) -> None:
        for token in (None, "", "token with spaces", "token\r\nInjected: value"):
            with self.subTest(token_type=type(token).__name__):
                provider = _TokenProvider(token)
                http_port = _RecordingHttpPort()
                transport = GraphRestV1WriteTransport(
                    provider,
                    http_port,
                    (AKTEN_COLLECTION, AUFGABEN_COLLECTION),
                )

                with self.assertRaisesRegex(
                    GraphWriteTransportError,
                    r"\Aaccess_token_unavailable\Z",
                ):
                    transport.request(
                        GraphWriteRequest(
                            "GET", AKTEN_ITEM_GET, {}, None, "freshness"
                        )
                    )
                self.assertEqual(provider.calls, 1)
                self.assertEqual(http_port.calls, [])

    def test_http_exception_is_stable_redacted_and_not_retried(self) -> None:
        provider = _TokenProvider("synthetic-token")
        http_port = _RecordingHttpPort(fail=True)
        transport = GraphRestV1WriteTransport(
            provider,
            http_port,
            (AKTEN_COLLECTION, AUFGABEN_COLLECTION),
        )

        with self.assertRaises(GraphWriteTransportError) as raised:
            transport.request(
                GraphWriteRequest("GET", AKTEN_ITEM_GET, {}, None, "freshness")
            )

        self.assertEqual(raised.exception.reason_code, "http_transport_unavailable")
        self.assertEqual(str(raised.exception), "http_transport_unavailable")
        self.assertNotIn("raw-http-secret", repr(raised.exception))
        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(http_port.calls), 1)

    def test_preflight_rejection_does_not_touch_credentials(self) -> None:
        provider = _FailingTokenProvider()
        http_port = _RecordingHttpPort()
        transport = GraphRestV1WriteTransport(
            provider,
            http_port,
            (AKTEN_COLLECTION, AUFGABEN_COLLECTION),
        )

        with self.assertRaisesRegex(
            GraphWriteTransportError, r"\Arequest_not_allowed\Z"
        ):
            transport.request(
                GraphWriteRequest(
                    "POST",
                    "https://example.invalid/v1.0/sites/site/lists/list/items",
                    {"Content-Type": "application/json"},
                    {},
                    "write",
                )
            )

        self.assertEqual(provider.calls, 0)
        self.assertEqual(http_port.calls, [])

    def test_valid_token_is_visible_only_at_the_http_boundary(self) -> None:
        provider = _TokenProvider("synthetic-token")
        http_port = _RecordingHttpPort()
        transport = GraphRestV1WriteTransport(
            provider,
            http_port,
            (AKTEN_COLLECTION, AUFGABEN_COLLECTION),
        )

        transport.request(
            GraphWriteRequest("GET", AKTEN_ITEM_GET, {}, None, "freshness")
        )

        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(http_port.calls), 1)
        self.assertEqual(
            http_port.calls[0]["headers"],
            {
                "Authorization": "Bearer synthetic-token",
                "Accept": "application/json",
            },
        )


if __name__ == "__main__":
    unittest.main()
