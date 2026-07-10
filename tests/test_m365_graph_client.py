from __future__ import annotations

import json
import sys
import traceback
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.graph_client import GraphHttpError, GraphRestClient  # noqa: E402


SENSITIVE_GRAPH_BODY = json.dumps(
    {
        "accessToken": "TOKEN_SENTINEL_606",
        "siteId": "SITE_ID_SENTINEL_606",
        "listId": "LIST_ID_SENTINEL_606",
        "path": "/sites/PATH_SENTINEL_606/lists/private/items",
        "requestId": "REQUEST_ID_SENTINEL_606",
        "matterText": "MATTER_TEXT_SENTINEL_606",
        "error": {"message": "GRAPH_MESSAGE_SENTINEL_606"},
    }
)
SENSITIVE_SENTINELS = (
    "TOKEN_SENTINEL_606",
    "SITE_ID_SENTINEL_606",
    "LIST_ID_SENTINEL_606",
    "PATH_SENTINEL_606",
    "REQUEST_ID_SENTINEL_606",
    "MATTER_TEXT_SENTINEL_606",
    "GRAPH_MESSAGE_SENTINEL_606",
)


class GraphRestClientTests(unittest.TestCase):
    def test_graph_http_error_rendering_exposes_only_status_and_generic_message(self) -> None:
        error = GraphHttpError(503, SENSITIVE_GRAPH_BODY)

        rendered = (str(error), repr(error), "".join(traceback.format_exception(error)))

        self.assertEqual(str(error), "Microsoft Graph request failed with HTTP 503")
        self.assertEqual(repr(error), "GraphHttpError('Microsoft Graph request failed with HTTP 503')")
        for output in rendered:
            for sentinel in SENSITIVE_SENTINELS:
                self.assertNotIn(sentinel, output)
        self.assertEqual(error.status, 503)
        self.assertEqual(error.body, SENSITIVE_GRAPH_BODY)

    def test_graph_http_error_chain_does_not_render_raw_response_body(self) -> None:
        client = GraphRestClient(_TokenProvider())
        http_error = HTTPError(
            url="https://graph.microsoft.com/v1.0/sites/redacted",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=BytesIO(SENSITIVE_GRAPH_BODY.encode("utf-8")),
        )

        with patch("nac_m365_graph.graph_client.urllib.request.urlopen", side_effect=http_error):
            with self.assertRaises(GraphHttpError) as raised:
                client.get("/sites/site-id/lists/list-id/items")

        error = raised.exception
        rendered = (str(error), repr(error), "".join(traceback.format_exception(error)))
        for output in rendered:
            for sentinel in SENSITIVE_SENTINELS:
                self.assertNotIn(sentinel, output)
        self.assertEqual(error.status, 429)
        self.assertEqual(error.body, SENSITIVE_GRAPH_BODY)

    def test_get_with_sharepoint_fields_filter_sets_nonindexed_query_prefer_header(self) -> None:
        client = GraphRestClient(_TokenProvider())

        with patch("nac_m365_graph.graph_client.urllib.request.urlopen", return_value=_JsonResponse({})) as urlopen:
            client.get("/sites/site-id/lists/list-id/items?$expand=fields&$filter=fields/NacCaseId%20eq%20%27case-1%27")

        request = urlopen.call_args.args[0]

        self.assertEqual(request.headers["Prefer"], "HonorNonIndexedQueriesWarningMayFailRandomly")

    def test_get_with_sharepoint_startswith_fields_filter_sets_nonindexed_query_prefer_header(self) -> None:
        client = GraphRestClient(_TokenProvider())

        with patch("nac_m365_graph.graph_client.urllib.request.urlopen", return_value=_JsonResponse({})) as urlopen:
            client.get("/sites/site-id/lists/list-id/items?$filter=startswith(fields/NacCaseId,'NAC-SMOKE')")

        request = urlopen.call_args.args[0]

        self.assertEqual(request.headers["Prefer"], "HonorNonIndexedQueriesWarningMayFailRandomly")

    def test_get_without_sharepoint_fields_filter_does_not_set_prefer_header(self) -> None:
        client = GraphRestClient(_TokenProvider())

        with patch("nac_m365_graph.graph_client.urllib.request.urlopen", return_value=_JsonResponse({})) as urlopen:
            client.get("/sites/site-id/lists?$select=id,displayName")

        request = urlopen.call_args.args[0]

        self.assertNotIn("Prefer", request.headers)

    def test_delete_uses_graph_delete_without_payload(self) -> None:
        client = GraphRestClient(_TokenProvider())

        with patch("nac_m365_graph.graph_client.urllib.request.urlopen", return_value=_JsonResponse({})) as urlopen:
            result = client.delete("/sites/site-id/lists/list-id/items/item-id")

        request = urlopen.call_args.args[0]

        self.assertEqual(result, {})
        self.assertEqual(request.get_method(), "DELETE")
        self.assertIsNone(request.data)


class _TokenProvider:
    def fetch_access_token(self) -> str:
        return "token"


class _JsonResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self) -> "_JsonResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
