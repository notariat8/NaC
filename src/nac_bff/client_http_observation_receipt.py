"""Offline verification of a privacy-minimal client HTTP companion receipt.

This module intentionally has no provider, credential or staging operation.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from src.nac_bff.current_state_access_client_receipt import (
    ClientObservationReceiptError,
    validate_client_observation_receipt_bytes,
)

_KEYS = frozenset({
    "base_receipt_sha256",
    "client_http_class",
    "observation_binding_sha256",
    "schema_version",
})
_HEX = re.compile(r"^[0-9a-f]{64}$")


class ClientHttpObservationError(ValueError):
    pass


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ClientHttpObservationError("CLIENT_HTTP_DUPLICATE_KEY")
        value[key] = item
    return value


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def validate_client_http_observation_receipt_bytes(
    base_receipt_raw: bytes, companion_raw: bytes
) -> dict[str, Any]:
    """Validate only a local pair; do not admit it to the historic #748 gate."""
    try:
        base = validate_client_observation_receipt_bytes(base_receipt_raw)
    except ClientObservationReceiptError as exc:
        raise ClientHttpObservationError("CLIENT_HTTP_BASE_INVALID") from exc
    if base_receipt_raw != _canonical(base):
        raise ClientHttpObservationError("CLIENT_HTTP_BASE_NONCANONICAL")
    if not companion_raw or len(companion_raw) > 1024:
        raise ClientHttpObservationError("CLIENT_HTTP_SIZE_INVALID")
    try:
        value = json.loads(
            companion_raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_keys,
        )
    except ClientHttpObservationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClientHttpObservationError("CLIENT_HTTP_JSON_INVALID") from exc
    if not isinstance(value, dict) or frozenset(value) != _KEYS:
        raise ClientHttpObservationError("CLIENT_HTTP_SCHEMA_INVALID")
    if companion_raw != _canonical(value):
        raise ClientHttpObservationError("CLIENT_HTTP_NONCANONICAL")
    if value["schema_version"] != "nac.client-http-observation/v0.1":
        raise ClientHttpObservationError("CLIENT_HTTP_VERSION_INVALID")
    if value["client_http_class"] not in ("none", "401", "403"):
        raise ClientHttpObservationError("CLIENT_HTTP_CLASS_INVALID")
    if not base["spfx_subject_available"] and value["client_http_class"] != "none":
        raise ClientHttpObservationError("CLIENT_HTTP_SUBJECT_CLASS_CONFLICT")
    for key in ("base_receipt_sha256", "observation_binding_sha256"):
        if not isinstance(value[key], str) or _HEX.fullmatch(value[key]) is None:
            raise ClientHttpObservationError("CLIENT_HTTP_HASH_INVALID")
    if value["base_receipt_sha256"] != hashlib.sha256(base_receipt_raw).hexdigest():
        raise ClientHttpObservationError("CLIENT_HTTP_BASE_BINDING_INVALID")
    core = {key: value[key] for key in _KEYS if key != "observation_binding_sha256"}
    if value["observation_binding_sha256"] != hashlib.sha256(_canonical(core)).hexdigest():
        raise ClientHttpObservationError("CLIENT_HTTP_OBSERVATION_BINDING_INVALID")
    return value
