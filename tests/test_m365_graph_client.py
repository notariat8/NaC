from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.graph_client import GraphRestClient  # noqa: E402


class GraphRestClientTests(unittest.TestCase):
    def test_get_with_sharepoint_fields_filter_sets_nonindexed_query_prefer_header(self) -> None:
        client = GraphRestClient(_TokenProvider())

        with patch("nac_m365_graph.graph_client.urllib.request.urlopen", return_value=_JsonResponse({})) as urlopen:
            client.get("/sites/site-id/lists/list-id/items?$expand=fields&$filter=fields/NacCaseId%20eq%20%27case-1%27")

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
