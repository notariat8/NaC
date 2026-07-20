from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from nac_bff.test_environment import ALLOWED_MATTER_ID, ALLOWED_WORKSPACE_ID
from nac_mvp_test_environment import (
    BUSINESS_CASE_TYPE_ID,
    DEADLINE,
    MATTER_STATUS,
    TASKS,
)


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
MAX_RESPONSE_BYTES = 262_144
MAX_PAGES = 4
MAX_ITEMS = 16
MAX_ATTEMPTS = 3
MAX_RETRY_AFTER_SECONDS = 2.0
DEFAULT_RETRY_AFTER_SECONDS = 0.25
GRAPH_IO_TIMEOUT_SECONDS = 5.0
GRAPH_REQUEST_DEADLINE_SECONDS = 8.0
GRAPH_REQUEST_BUDGET_SECONDS = 20.0
GRAPH_TOKEN_ACQUISITION_TIMEOUT_SECONDS = 5.0
_ACTIVE_GRAPH_DEADLINE: ContextVar[float | None] = ContextVar(
    "nac_bff_graph_deadline", default=None
)

MAX_BFF_GRAPH_REQUESTS = 5 * MAX_PAGES
AZURE_HTTP_LIMIT_SECONDS = 230.0

SYNTHETIC_SITE_ID = (
    "funktion8.sharepoint.com,31324d31-3074-4f1c-ba45-3b3fd5f5ce97,"
    "56fc9349-e123-4252-ae2a-05d5d61c9b38"
)
SYNTHETIC_LIST_IDS = {
    "Akten": "588d4a41-f538-4f37-acfb-63ff283e0910",
    "AufgabenFristen": "720ef1d4-8496-4ecb-aa1f-5fa4568343f2",
    "Vertretungsfreigaben": "ec12d339-d9b7-45e9-be45-38dadd917746",
    "AuditJournalLite": "327181c2-e402-48e9-bcfa-1f5081b45d9c",
}


class GraphTokenProvider(Protocol):
    def fetch_access_token(self) -> str: ...


class GraphGetClient(Protocol):
    base_url: str
    redirects_allowed: bool
    retains_error_body: bool

    def get(self, path: str) -> dict[str, object]: ...


class GraphRequestError(RuntimeError):
    """Generic transport failure that deliberately carries no response body."""


class GraphResponseError(RuntimeError):
    """Graph returned data outside the adapter's bounded response contract."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RawGraphV1Client:
    """Minimal raw Graph GET client with a fixed v1.0 origin."""

    redirects_allowed = False
    retains_error_body = False

    def __init__(
        self,
        token_provider: GraphTokenProvider,
        *,
        base_url: str = GRAPH_BASE_URL,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        timeout_seconds: float = GRAPH_IO_TIMEOUT_SECONDS,
        request_deadline_seconds: float = GRAPH_REQUEST_DEADLINE_SECONDS,
        request_budget_seconds: float = GRAPH_REQUEST_BUDGET_SECONDS,
        token_acquisition_timeout_seconds: float = GRAPH_TOKEN_ACQUISITION_TIMEOUT_SECONDS,
    ) -> None:
        if base_url != GRAPH_BASE_URL:
            raise ValueError("Only Microsoft Graph v1.0 is allowed")
        if not callable(sleep) or not callable(monotonic):
            raise ValueError("Graph timing hooks must be callable")
        self.token_provider = token_provider
        self.base_url = base_url
        self._sleep = sleep
        self._monotonic = monotonic
        self._timeout_seconds = _bounded_positive_finite_seconds(
            timeout_seconds, "timeout_seconds", maximum=GRAPH_IO_TIMEOUT_SECONDS
        )
        self._request_deadline_seconds = _bounded_positive_finite_seconds(
            request_deadline_seconds,
            "request_deadline_seconds",
            maximum=GRAPH_REQUEST_DEADLINE_SECONDS,
        )
        self._request_budget_seconds = _bounded_positive_finite_seconds(
            request_budget_seconds,
            "request_budget_seconds",
            maximum=GRAPH_REQUEST_BUDGET_SECONDS,
        )
        self._token_acquisition_timeout_seconds = _bounded_positive_finite_seconds(
            token_acquisition_timeout_seconds,
            "token_acquisition_timeout_seconds",
            maximum=GRAPH_TOKEN_ACQUISITION_TIMEOUT_SECONDS,
        )

    @contextmanager
    def request_budget(self):
        """Bind one monotonic deadline to all Graph work in this request context."""

        deadline = self._clock_value() + self._request_budget_seconds
        outer_deadline = _ACTIVE_GRAPH_DEADLINE.get()
        if outer_deadline is not None:
            deadline = min(deadline, outer_deadline)
        context_token = _ACTIVE_GRAPH_DEADLINE.set(deadline)
        try:
            yield
        finally:
            _ACTIVE_GRAPH_DEADLINE.reset(context_token)

    def get(self, path: str) -> dict[str, object]:
        _validate_relative_graph_path(path)
        deadline = self._clock_value() + self._request_deadline_seconds
        aggregate_deadline = _ACTIVE_GRAPH_DEADLINE.get()
        if aggregate_deadline is not None:
            deadline = min(deadline, aggregate_deadline)
        try:
            bounded_fetch = getattr(
                self.token_provider, "fetch_access_token_with_timeout", None
            )
            if callable(bounded_fetch):
                token = bounded_fetch(
                    timeout_seconds=min(
                        self._token_acquisition_timeout_seconds,
                        self._remaining_seconds(deadline),
                    )
                )
            else:
                token = self.token_provider.fetch_access_token()
            self._remaining_seconds(deadline)
        except Exception:
            raise GraphRequestError("Microsoft Graph authentication failed") from None
        if (
            not isinstance(token, str)
            or not token
            or len(token) > 8192
            or "\n" in token
            or "\r" in token
        ):
            raise GraphRequestError("Microsoft Graph authentication failed")

        request = urllib.request.Request(
            self.base_url + path,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            method="GET",
        )
        for attempt in range(MAX_ATTEMPTS):
            timeout_seconds = min(
                self._timeout_seconds, self._remaining_seconds(deadline)
            )
            try:
                with self._open(request, timeout_seconds=timeout_seconds) as response:
                    content_length = response.headers.get("Content-Length")
                    if content_length is not None and _content_length_exceeds_limit(content_length):
                        raise GraphResponseError("Microsoft Graph response exceeded the byte limit")
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise GraphResponseError("Microsoft Graph response exceeded the byte limit")
                self._remaining_seconds(deadline)
                payload = _decode_object(raw)
                self._remaining_seconds(deadline)
                return payload
            except urllib.error.HTTPError as error:
                status = error.code
                retry_after = error.headers.get("Retry-After") if error.headers is not None else None
                error.close()
                if status not in {429, 503} or attempt + 1 >= MAX_ATTEMPTS:
                    raise GraphRequestError("Microsoft Graph request failed") from None
                self._sleep_with_deadline(_bounded_retry_after(retry_after), deadline)
            except GraphResponseError:
                raise
            except (TimeoutError, OSError, urllib.error.URLError):
                raise GraphRequestError("Microsoft Graph request failed") from None
        raise GraphRequestError("Microsoft Graph request failed")

    def _open(
        self, request: urllib.request.Request, *, timeout_seconds: float
    ):
        return urllib.request.build_opener(_NoRedirectHandler()).open(
            request, timeout=timeout_seconds
        )

    def _clock_value(self) -> float:
        value = self._monotonic()
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise GraphRequestError("Microsoft Graph request failed")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise GraphRequestError("Microsoft Graph request failed")
        return numeric

    def _remaining_seconds(self, deadline: float) -> float:
        remaining = deadline - self._clock_value()
        if remaining <= 0:
            raise GraphRequestError("Microsoft Graph request deadline exceeded")
        return remaining

    def _sleep_with_deadline(self, delay: float, deadline: float) -> None:
        if delay >= self._remaining_seconds(deadline):
            raise GraphRequestError("Microsoft Graph request deadline exceeded")
        self._sleep(delay)
        self._remaining_seconds(deadline)


@dataclass(frozen=True, slots=True)
class FixedListBinding:
    name: str
    site_id: str
    list_id: str

    @property
    def collection_path(self) -> str:
        site = urllib.parse.quote(self.site_id, safe="")
        list_id = urllib.parse.quote(self.list_id, safe="")
        return f"/sites/{site}/lists/{list_id}/items"


def synthetic_list_binding(name: str) -> FixedListBinding:
    try:
        list_id = SYNTHETIC_LIST_IDS[name]
    except (KeyError, TypeError):
        raise ValueError("Unknown synthetic SharePoint list") from None
    return FixedListBinding(name=name, site_id=SYNTHETIC_SITE_ID, list_id=list_id)


def read_bounded_collection(
    client: GraphGetClient,
    *,
    binding: FixedListBinding,
    fields: tuple[str, ...],
    filter_expression: str,
    top: int,
    max_items: int = MAX_ITEMS,
) -> list[dict[str, Any]]:
    """Read one fixed list with strict projection and same-collection paging."""

    if not _client_is_hardened(client):
        raise GraphRequestError("Microsoft Graph client boundary is invalid")
    if binding.site_id != SYNTHETIC_SITE_ID or SYNTHETIC_LIST_IDS.get(binding.name) != binding.list_id:
        raise GraphRequestError("Microsoft Graph list binding is invalid")
    if (
        not fields
        or any(not isinstance(field, str) or not field for field in fields)
        or not isinstance(filter_expression, str)
        or not filter_expression
        or type(top) is not int
        or top < 1
        or top > MAX_ITEMS
        or type(max_items) is not int
        or max_items < 1
        or max_items > MAX_ITEMS
    ):
        raise GraphRequestError("Microsoft Graph query boundary is invalid")

    projection = ",".join(fields)
    path = _collection_query(binding.collection_path, projection, filter_expression, top)
    seen = {_canonical_url(path)}
    rows: list[dict[str, Any]] = []
    pages = 0
    while True:
        if pages >= MAX_PAGES:
            raise GraphResponseError("Microsoft Graph paging limit exceeded")
        payload = client.get(path)
        pages += 1
        page, next_link = _parse_page(payload, fields)
        if len(rows) + len(page) > max_items:
            raise GraphResponseError("Microsoft Graph item limit exceeded")
        rows.extend(page)
        if next_link is None:
            return rows
        path = _validated_next_path(
            next_link,
            collection_path=binding.collection_path,
            projection=projection,
            filter_expression=filter_expression,
            top=top,
        )
        canonical = _canonical_url(path)
        if canonical in seen:
            raise GraphResponseError("Microsoft Graph paging cycle detected")
        seen.add(canonical)


class SyntheticWorkspaceGraphRestAdapter:
    """GraphRestPort implementation for the single synthetic workspace."""

    def __init__(self, client: GraphGetClient) -> None:
        self._client = client

    def read_synthetic_workspace(
        self,
        *,
        workspace_id: str,
        matter_id: str,
    ) -> Mapping[str, Any] | None:
        if workspace_id != ALLOWED_WORKSPACE_ID or matter_id != ALLOWED_MATTER_ID:
            return None

        case_rows = read_bounded_collection(
            self._client,
            binding=synthetic_list_binding("Akten"),
            fields=("NacCaseId", "Vorgangstyp", "Status", "FristNaechsteAktion"),
            filter_expression=_equals("NacCaseId", ALLOWED_MATTER_ID),
            top=2,
            max_items=2,
        )
        if not case_rows:
            return None
        if len(case_rows) != 1:
            raise GraphResponseError("Synthetic matter cardinality is invalid")
        case = case_rows[0]
        if (
            case.get("NacCaseId") != ALLOWED_MATTER_ID
            or case.get("Vorgangstyp") != BUSINESS_CASE_TYPE_ID
            or case.get("Status") != MATTER_STATUS
            or case.get("FristNaechsteAktion") != DEADLINE
        ):
            raise GraphResponseError("Synthetic matter fields are invalid")

        task_rows = read_bounded_collection(
            self._client,
            binding=synthetic_list_binding("AufgabenFristen"),
            fields=(
                "NacTaskId",
                "NacCaseId",
                "BpmnStepCode",
                "Status",
                "RequiresNotaryApproval",
                "DueDate",
            ),
            filter_expression=_equals("NacCaseId", ALLOWED_MATTER_ID),
            top=4,
            max_items=4,
        )
        tasks_by_id = {row.get("NacTaskId"): row for row in task_rows}
        if len(task_rows) != len(TASKS) or len(tasks_by_id) != len(TASKS):
            raise GraphResponseError("Synthetic task cardinality is invalid")

        projected_tasks: list[dict[str, Any]] = []
        for expected in TASKS:
            row = tasks_by_id.get(expected["task_id"])
            if not isinstance(row, dict) or (
                row.get("NacCaseId") != ALLOWED_MATTER_ID
                or row.get("BpmnStepCode") != expected["step_code"]
                or row.get("Status") != expected["status"]
                or row.get("RequiresNotaryApproval") is not expected["requires_notary_approval"]
                or row.get("DueDate") != expected["due_at"]
            ):
                raise GraphResponseError("Synthetic task fields are invalid")
            projected_tasks.append(
                {
                    "taskId": expected["task_id"],
                    "title": expected["title"],
                    "stepCode": expected["step_code"],
                    "status": expected["status"],
                    "requiresNotaryApproval": expected["requires_notary_approval"],
                    "dueAt": expected["due_at"],
                }
            )

        return {
            "status": MATTER_STATUS,
            "deadline": DEADLINE,
            "tasks": projected_tasks,
        }


# Concise compatibility name for composition roots and tests.
GraphRestPortAdapter = SyntheticWorkspaceGraphRestAdapter


def _equals(field: str, value: str) -> str:
    return f"fields/{field} eq '{value.replace(chr(39), chr(39) * 2)}'"


def _collection_query(collection_path: str, projection: str, filter_expression: str, top: int) -> str:
    encoded_filter = urllib.parse.quote(filter_expression, safe="/'")
    return (
        f"{collection_path}?$select=id&$expand=fields($select={projection})"
        f"&$filter={encoded_filter}&$top={top}"
    )


def _parse_page(
    payload: object,
    fields: tuple[str, ...],
) -> tuple[list[dict[str, Any]], str | None]:
    if type(payload) is not dict or type(payload.get("value")) is not list:
        raise GraphResponseError("Microsoft Graph collection response is invalid")
    next_link = payload.get("@odata.nextLink")
    if next_link is not None and (type(next_link) is not str or not next_link):
        raise GraphResponseError("Microsoft Graph nextLink is invalid")

    allowed_fields = set(fields)
    rows: list[dict[str, Any]] = []
    for item in payload["value"]:
        if type(item) is not dict or not isinstance(item.get("id"), str) or not item["id"]:
            raise GraphResponseError("Microsoft Graph list item is invalid")
        if set(item) - {"id", "fields", "@odata.etag"}:
            raise GraphResponseError("Microsoft Graph list item projection is too broad")
        item_fields = item.get("fields")
        if type(item_fields) is not dict or set(item_fields) - allowed_fields:
            raise GraphResponseError("Microsoft Graph field projection is too broad")
        rows.append(dict(item_fields))
    return rows, next_link


def _validated_next_path(
    next_link: str,
    *,
    collection_path: str,
    projection: str,
    filter_expression: str,
    top: int,
) -> str:
    try:
        parsed = urllib.parse.urlsplit(next_link)
        pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    except (TypeError, ValueError, UnicodeError):
        raise GraphResponseError("Microsoft Graph nextLink is invalid") from None
    expected_path = f"/v1.0{collection_path}"
    if (
        parsed.scheme != "https"
        or parsed.netloc != "graph.microsoft.com"
        or parsed.path != expected_path
        or parsed.fragment
    ):
        raise GraphResponseError("Microsoft Graph nextLink escaped the fixed collection")
    query: dict[str, str] = {}
    for key, value in pairs:
        if key in query:
            raise GraphResponseError("Microsoft Graph nextLink contains duplicate parameters")
        query[key] = value
    required = {
        "$select": "id",
        "$expand": f"fields($select={projection})",
        "$filter": filter_expression,
        "$top": str(top),
    }
    if any(query.get(key) != value for key, value in required.items()):
        raise GraphResponseError("Microsoft Graph nextLink changed the fixed projection")
    if set(query) - set(required) - {"$skiptoken"} or not query.get("$skiptoken"):
        raise GraphResponseError("Microsoft Graph nextLink paging token is invalid")
    canonical_query = urllib.parse.urlencode(sorted(query.items()), quote_via=urllib.parse.quote)
    return f"{collection_path}?{canonical_query}"


def _canonical_url(path: str) -> str:
    parsed = urllib.parse.urlsplit(path)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    query = urllib.parse.urlencode(sorted(pairs), quote_via=urllib.parse.quote)
    return f"{GRAPH_BASE_URL}{parsed.path}?{query}"


def _client_is_hardened(client: object) -> bool:
    try:
        return (
            client.base_url == GRAPH_BASE_URL
            and client.redirects_allowed is False
            and client.retains_error_body is False
            and callable(client.get)
        )
    except Exception:
        return False


def _validate_relative_graph_path(path: object) -> None:
    if type(path) is not str or not path.startswith("/sites/"):
        raise ValueError("A fixed relative Microsoft Graph site path is required")
    parsed = urllib.parse.urlsplit(path)
    if parsed.scheme or parsed.netloc or parsed.fragment or "//" in parsed.path:
        raise ValueError("A fixed relative Microsoft Graph site path is required")


def _decode_object(raw: bytes) -> dict[str, object]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise GraphResponseError("Microsoft Graph returned invalid JSON") from None
    if type(value) is not dict:
        raise GraphResponseError("Microsoft Graph returned an invalid JSON object")
    return value


def _content_length_exceeds_limit(value: str) -> bool:
    try:
        length = int(value)
    except (TypeError, ValueError):
        raise GraphResponseError("Microsoft Graph returned an invalid Content-Length") from None
    return length < 0 or length > MAX_RESPONSE_BYTES


def _bounded_positive_finite_seconds(
    value: object, name: str, *, maximum: float
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive finite number")
    numeric = float(value)
    if not math.isfinite(numeric) or not 0 < numeric <= maximum:
        raise ValueError(
            f"{name} must be a positive finite number no greater than {maximum}"
        )
    return numeric


def _bounded_retry_after(value: object) -> float:
    if value is None:
        return DEFAULT_RETRY_AFTER_SECONDS
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        raise GraphRequestError("Microsoft Graph returned an invalid Retry-After") from None
    if not math.isfinite(seconds) or seconds < 0:
        raise GraphRequestError("Microsoft Graph returned an invalid Retry-After")
    return min(seconds, MAX_RETRY_AFTER_SECONDS)
