from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
from typing import Any


MAX_CLIENT_RECEIPT_BYTES = 16 * 1024
CLIENT_RECEIPT_BROWSER_NAME = "nac-issue748-client-observation.json"
CLIENT_RECEIPT_NAME = "client-observation-receipt.json"
CLIENT_RECEIPT_KEYS = {
    "end_utc",
    "request_correlation_binding_sha256",
    "spfx_subject_available",
    "start_utc",
    "ui_state",
    "window_binding_sha256",
}
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


class ClientObservationReceiptError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ClientObservationReceiptError("CLIENT_RECEIPT_DUPLICATE_KEY")
        value[key] = item
    return value


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _canonical_sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or _UTC_TIMESTAMP.fullmatch(value) is None:
        raise ClientObservationReceiptError("CLIENT_RECEIPT_WINDOW_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ClientObservationReceiptError("CLIENT_RECEIPT_WINDOW_INVALID") from exc
    if parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z") != value:
        raise ClientObservationReceiptError("CLIENT_RECEIPT_WINDOW_INVALID")
    return parsed


def validate_client_observation_receipt_bytes(raw: bytes) -> dict[str, Any]:
    if not raw or len(raw) > MAX_CLIENT_RECEIPT_BYTES:
        raise ClientObservationReceiptError("CLIENT_RECEIPT_SIZE_INVALID")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except ClientObservationReceiptError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClientObservationReceiptError("CLIENT_RECEIPT_JSON_INVALID") from exc
    if not isinstance(value, dict) or set(value) != CLIENT_RECEIPT_KEYS:
        raise ClientObservationReceiptError("CLIENT_RECEIPT_SCHEMA_INVALID")
    if value["ui_state"] != "no_access":
        raise ClientObservationReceiptError("CLIENT_RECEIPT_UI_STATE_INVALID")
    if type(value["spfx_subject_available"]) is not bool:
        raise ClientObservationReceiptError("CLIENT_RECEIPT_SUBJECT_FLAG_INVALID")
    for field in (
        "request_correlation_binding_sha256",
        "window_binding_sha256",
    ):
        if not isinstance(value[field], str) or _HEX_64.fullmatch(value[field]) is None:
            raise ClientObservationReceiptError("CLIENT_RECEIPT_HASH_INVALID")
    start = _parse_utc(value["start_utc"])
    end = _parse_utc(value["end_utc"])
    if end <= start or end - start > timedelta(minutes=15):
        raise ClientObservationReceiptError("CLIENT_RECEIPT_WINDOW_INVALID")
    window_core = {
        "end_utc": value["end_utc"],
        "request_correlation_binding_sha256": value[
            "request_correlation_binding_sha256"
        ],
        "spfx_subject_available": value["spfx_subject_available"],
        "start_utc": value["start_utc"],
        "ui_state": value["ui_state"],
    }
    if value["window_binding_sha256"] != _canonical_sha256(window_core):
        raise ClientObservationReceiptError("CLIENT_RECEIPT_WINDOW_BINDING_INVALID")
    return value


def _is_within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def stage_client_observation_receipt(
    *,
    source_path: Path,
    input_root: Path,
    repo_root: Path,
    backend: Any | None = None,
) -> dict[str, Any]:
    source = Path(source_path)
    destination_root = Path(input_root)
    repository = Path(repo_root)
    if not source.is_absolute() or not destination_root.is_absolute():
        raise ClientObservationReceiptError("CLIENT_RECEIPT_ABSOLUTE_PATH_REQUIRED")
    if source.name != CLIENT_RECEIPT_BROWSER_NAME:
        raise ClientObservationReceiptError("CLIENT_RECEIPT_FILENAME_INVALID")
    if _is_within(source, repository) or _is_within(destination_root, repository):
        raise ClientObservationReceiptError("CLIENT_RECEIPT_REPOSITORY_EXTERNAL_REQUIRED")
    if backend is None:
        from .activation_security_backend import get_platform_security_backend

        backend = get_platform_security_backend()
    snapshot = backend.inspect_bound_input_path(
        source, purpose="issue748-client-receipt-download"
    )
    if snapshot.size <= 0 or snapshot.size > MAX_CLIENT_RECEIPT_BYTES:
        raise ClientObservationReceiptError("CLIENT_RECEIPT_SIZE_INVALID")
    with backend.open_bound_input_read(source, snapshot) as stream:
        raw = stream.read(MAX_CLIENT_RECEIPT_BYTES + 1)
    if (
        len(raw) > MAX_CLIENT_RECEIPT_BYTES
        or hashlib.sha256(raw).hexdigest() != snapshot.sha256
    ):
        raise ClientObservationReceiptError("CLIENT_RECEIPT_SOURCE_BINDING_DRIFT")
    receipt = validate_client_observation_receipt_bytes(raw)
    canonical = _canonical_bytes(receipt)
    session = backend.open_secure_directory(
        destination_root,
        create=False,
        require_current_owner=True,
        require_restrictive_dacl=True,
    )
    try:
        staged = session.create_exclusive(CLIENT_RECEIPT_NAME, canonical)
    except FileExistsError as exc:
        raise ClientObservationReceiptError("CLIENT_RECEIPT_ALREADY_EXISTS") from exc
    except RuntimeError as exc:
        if getattr(exc, "code", None) == "SECURE_CHILD_ALREADY_EXISTS":
            raise ClientObservationReceiptError(
                "CLIENT_RECEIPT_ALREADY_EXISTS"
            ) from exc
        raise
    finally:
        session.close()
    return {
        "schema_version": "nac.m365-current-state-access-client-receipt-stage/v1",
        "status": "PASSED",
        "receipt_sha256": staged.sha256,
        "network_reads": 0,
        "credential_writes": 0,
        "provider_writes": 0,
        "live_run_authorized": False,
    }


__all__ = [
    "CLIENT_RECEIPT_KEYS",
    "CLIENT_RECEIPT_BROWSER_NAME",
    "CLIENT_RECEIPT_NAME",
    "ClientObservationReceiptError",
    "MAX_CLIENT_RECEIPT_BYTES",
    "stage_client_observation_receipt",
    "validate_client_observation_receipt_bytes",
]
