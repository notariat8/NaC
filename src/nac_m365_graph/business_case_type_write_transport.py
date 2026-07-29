from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Protocol

from .business_case_type_write_edge import GraphResponse
from .business_case_type_write_plan import GRAPH_BASE_URL, GraphWriteRequest


MAX_RESPONSE_BYTES = 1024 * 1024
_ALLOWED_METHODS = frozenset({"GET", "POST", "PATCH"})
_ALLOWED_RESPONSE_HEADERS = {
    "etag": "ETag",
    "location": "Location",
    "retry-after": "Retry-After",
}
_HEX_PAIR = re.compile(r"[0-9A-Fa-f]{2}\Z")
_ITEM_PATH = re.compile(r"/(?P<item_id>[1-9][0-9]{0,18})\Z")
_FIELD_LIST = r"[A-Za-z][A-Za-z0-9]*(?:,[A-Za-z][A-Za-z0-9]*)*"
_DEDUPE_QUERY = re.compile(
    rf"expand=fields\(select=(?P<fields>{_FIELD_LIST})\)"
    rf"&\$filter=fields/(?P<dedupe_field>[A-Za-z][A-Za-z0-9]*)"
    r"%20eq%20%27(?:[A-Za-z0-9._~-]|%[0-9A-Fa-f]{2})+%27\Z"
)
_ITEM_QUERY = re.compile(
    rf"\$select=id,eTag&\$expand=fields\(\$select={_FIELD_LIST}\)\Z"
)
_ETAG = re.compile(
    r"(?:W/)?\"[^\"\r\n]{1,1024}\"|[A-Za-z0-9][A-Za-z0-9._:-]{0,1023}\Z"
)


class GraphWriteAccessTokenProvider(Protocol):
    def fetch_access_token(self) -> str: ...


@dataclass(frozen=True, slots=True)
class HttpTransportResponse:
    status_code: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)


class HttpTransportPort(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        follow_redirects: Literal[False],
        automatic_retries: Literal[0],
        max_response_bytes: int,
    ) -> HttpTransportResponse: ...


class GraphWriteTransportError(RuntimeError):
    """Stable, redacted failure raised by the Graph REST transport."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class GraphRestV1WriteTransport:
    def __init__(
        self,
        token_provider: GraphWriteAccessTokenProvider,
        http_port: HttpTransportPort,
        allowed_collection_urls: tuple[str, str],
    ) -> None:
        self._token_provider = token_provider
        self._http_port = http_port
        self._allowed_collection_urls = _validated_collection_urls(
            allowed_collection_urls
        )

    def request(self, request: GraphWriteRequest) -> GraphResponse:
        method, url, headers, body = _prepare_request(
            request, self._allowed_collection_urls
        )
        token = _fetch_token(self._token_provider)
        outbound_headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            **headers,
        }

        failed = False
        response: object | None = None
        try:
            response = self._http_port.request(
                method=method,
                url=url,
                headers=outbound_headers,
                body=body,
                follow_redirects=False,
                automatic_retries=0,
                max_response_bytes=MAX_RESPONSE_BYTES,
            )
        except Exception:
            failed = True
        if failed:
            raise GraphWriteTransportError("http_transport_unavailable")
        return _graph_response(response)


def _validated_collection_urls(
    collection_urls: tuple[str, str],
) -> tuple[str, str]:
    if type(collection_urls) is not tuple or len(collection_urls) != 2:
        raise ValueError("allowed_collection_urls_must_contain_exactly_two_urls")
    first, second = collection_urls
    if first == second:
        raise ValueError("allowed_collection_urls_must_be_distinct")
    for url in collection_urls:
        if not _is_collection_url(url):
            raise ValueError("allowed_collection_url_invalid")
    return collection_urls


def _is_collection_url(value: object) -> bool:
    if type(value) is not str or not _safe_url_text(value):
        return False
    prefix = f"{GRAPH_BASE_URL}/"
    if not value.startswith(prefix) or "?" in value or "#" in value:
        return False
    suffix = value[len(prefix) :]
    segments = suffix.split("/")
    return bool(
        len(segments) == 5
        and segments[0] == "sites"
        and segments[1]
        and segments[2] == "lists"
        and segments[3]
        and segments[4] == "items"
        and all(segment not in {".", ".."} for segment in segments)
        and all(not _contains_blocked_percent_escape(segment) for segment in segments)
        and all(segment.lower() != "_api" for segment in segments)
    )


def _prepare_request(
    request: GraphWriteRequest,
    allowed_collection_urls: tuple[str, str],
) -> tuple[str, str, dict[str, str], bytes | None]:
    if not isinstance(request, GraphWriteRequest):
        raise GraphWriteTransportError("request_not_allowed")
    method = request.method
    url = request.url
    if method not in _ALLOWED_METHODS:
        raise GraphWriteTransportError("request_not_allowed")
    if not _is_bound_request_url(
        url,
        allowed_collection_urls,
        method=method,
        phase=request.phase,
    ):
        raise GraphWriteTransportError("request_not_allowed")

    headers = _validated_request_headers(method, request.headers)
    if method == "GET":
        if request.payload is not None:
            raise GraphWriteTransportError("request_not_allowed")
        return method, url, headers, None
    if not isinstance(request.payload, Mapping):
        raise GraphWriteTransportError("request_not_allowed")
    try:
        plain_payload = _plain_json_object(request.payload)
        body = json.dumps(
            plain_payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        raise GraphWriteTransportError("request_not_allowed") from None
    return method, url, headers, body


def _is_bound_request_url(
    value: object,
    allowed_collection_urls: tuple[str, str],
    *,
    method: str,
    phase: str,
) -> bool:
    if type(value) is not str or not _safe_url_text(value) or "#" in value:
        return False
    if not value.startswith(f"{GRAPH_BASE_URL}/"):
        return False
    path, separator, query = value.partition("?")
    if separator and not query:
        return False
    if _contains_blocked_percent_escape(path):
        return False
    if any(segment in {".", ".."} for segment in path.split("/")):
        return False
    if any(segment.lower() == "_api" for segment in path.split("/")):
        return False
    for collection_url in allowed_collection_urls:
        if method == "POST":
            if phase == "write" and value == collection_url:
                return True
            continue
        if method == "PATCH":
            suffix = path.removeprefix(collection_url)
            if (
                not separator
                and phase == "write"
                and suffix.endswith("/fields")
                and _ITEM_PATH.fullmatch(suffix[: -len("/fields")])
            ):
                return True
            continue
        if method != "GET" or not separator:
            continue
        if path == collection_url and phase in {"dedupe", "readback"}:
            match = _DEDUPE_QUERY.fullmatch(query)
            if match is None:
                return False
            return match.group("dedupe_field") in match.group("fields").split(",")
        suffix = path.removeprefix(collection_url)
        if (
            phase in {"freshness", "readback"}
            and _ITEM_PATH.fullmatch(suffix)
            and _ITEM_QUERY.fullmatch(query)
        ):
            return True
    return False


def _safe_url_text(value: str) -> bool:
    if not value or "\\" in value or any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        return False
    index = 0
    while True:
        index = value.find("%", index)
        if index < 0:
            return True
        if index + 2 >= len(value) or _HEX_PAIR.fullmatch(value[index + 1 : index + 3]) is None:
            return False
        index += 3


def _contains_blocked_percent_escape(value: str) -> bool:
    lowered = value.lower()
    return any(escape in lowered for escape in ("%2e", "%2f", "%5c", "%3f", "%23"))


def _validated_request_headers(
    method: str, headers: Mapping[str, str]
) -> dict[str, str]:
    if not isinstance(headers, Mapping):
        raise GraphWriteTransportError("request_not_allowed")
    try:
        copied = dict(headers)
    except Exception:
        raise GraphWriteTransportError("request_not_allowed") from None
    if any(type(key) is not str or type(value) is not str for key, value in copied.items()):
        raise GraphWriteTransportError("request_not_allowed")
    if method == "GET":
        if copied:
            raise GraphWriteTransportError("request_not_allowed")
        return {}
    expected_keys = (
        {"Content-Type"}
        if method == "POST"
        else {"Content-Type", "If-Match"}
    )
    if set(copied) != expected_keys:
        raise GraphWriteTransportError("request_not_allowed")
    if copied["Content-Type"] != "application/json":
        raise GraphWriteTransportError("request_not_allowed")
    if (
        method == "PATCH"
        and (
            not _safe_header_value(copied["If-Match"])
            or _ETAG.fullmatch(copied["If-Match"]) is None
        )
    ):
        raise GraphWriteTransportError("request_not_allowed")
    return copied


def _safe_header_value(value: str) -> bool:
    return bool(
        value
        and len(value) <= 16_384
        and all(ord(char) >= 0x20 and ord(char) != 0x7F for char in value)
    )


def _plain_json_object(value: Mapping[str, Any]) -> dict[str, Any]:
    return _plain_json(value, require_object=True)


def _plain_json(value: Any, *, require_object: bool = False) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str or key in result:
                raise ValueError
            result[key] = _plain_json(item)
        return result
    if require_object:
        raise ValueError
    if isinstance(value, (list, tuple)):
        return [_plain_json(item) for item in value]
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise ValueError


def _fetch_token(provider: GraphWriteAccessTokenProvider) -> str:
    failed = False
    token: object | None = None
    try:
        token = provider.fetch_access_token()
    except Exception:
        failed = True
    if (
        failed
        or type(token) is not str
        or not token
        or len(token) > 16_384
        or any(char.isspace() or ord(char) < 0x21 or ord(char) == 0x7F for char in token)
    ):
        raise GraphWriteTransportError("access_token_unavailable")
    return token


def _graph_response(response: object) -> GraphResponse:
    if not isinstance(response, HttpTransportResponse):
        raise GraphWriteTransportError("http_response_invalid")
    status_code = response.status_code
    body = response.body
    if type(status_code) is not int or not 100 <= status_code <= 599:
        raise GraphWriteTransportError("http_response_invalid")
    if type(body) is not bytes:
        raise GraphWriteTransportError("http_response_invalid")
    if len(body) > MAX_RESPONSE_BYTES:
        raise GraphWriteTransportError("http_response_too_large")
    headers = _allowlisted_response_headers(response.headers)
    parsed_body = _response_json_object(body)
    if not 200 <= status_code <= 299:
        parsed_body = {}
    return GraphResponse(
        status_code=status_code,
        body=parsed_body,
        headers=headers,
    )


def _allowlisted_response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(headers, Mapping):
        raise GraphWriteTransportError("http_response_invalid")
    result: dict[str, str] = {}
    try:
        items = tuple(headers.items())
    except Exception:
        raise GraphWriteTransportError("http_response_invalid") from None
    for key, value in items:
        if type(key) is not str or type(value) is not str:
            raise GraphWriteTransportError("http_response_invalid")
        canonical_name = _ALLOWED_RESPONSE_HEADERS.get(key.lower())
        if canonical_name is None:
            continue
        if canonical_name in result or not _safe_header_value(value):
            raise GraphWriteTransportError("http_response_invalid")
        result[canonical_name] = value
    return result


def _response_json_object(body: bytes) -> dict[str, Any]:
    if not body:
        return {}

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    try:
        parsed = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=object_pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        raise GraphWriteTransportError("http_response_invalid") from None
    if type(parsed) is not dict:
        raise GraphWriteTransportError("http_response_invalid")
    return parsed
