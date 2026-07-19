from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
import stat
from typing import Any, Mapping

from nac_m365_graph.provisioner_env_bootstrap import (
    PROVISIONER_SECRET_KEYS,
    build_provisioner_env_bootstrap,
)

from .azure_activation import PROVISIONER_CLIENT_ID, TENANT_ID


SCHEMA_VERSION = "nac.m365-azure-bff-provisioner-bootstrap/v1"
_GRAPH_V1 = "https://graph.microsoft.com/v1.0"
_MAX_STATE_BYTES = 128 * 1024
PROVISIONER_BOOTSTRAP_ERROR_CODES = frozenset(
    {
        "PROVISIONER_BOOTSTRAP_BINDING_MISMATCH",
        "PROVISIONER_BOOTSTRAP_INPUTS_REQUIRED",
        "PROVISIONER_CERTIFICATE_FILE_UNTRUSTED",
        "PROVISIONER_CERTIFICATE_MODE_REQUIRED",
        "PROVISIONER_ENV_BOOTSTRAP_FAILED",
        "PROVISIONER_ENV_BINDING_MISMATCH",
        "PROVISIONER_ENV_BOOTSTRAP_NOT_READY",
        "PROVISIONER_GRAPH_BASE_URL_INVALID",
        "PROVISIONER_PRIVATE_KEY_FILE_UNTRUSTED",
        "PROVISIONER_STATE_BINDING_MISMATCH",
        "PROVISIONER_STATE_FILE_UNTRUSTED",
        "PROVISIONER_STATE_INVALID",
    }
)


@dataclass(frozen=True, slots=True)
class ActivationProvisionerBootstrap:
    env_overlay: dict[str, str]
    binding_sha256: str | None
    readiness: dict[str, Any]


def build_activation_provisioner_bootstrap(
    state_path: Path | None,
    certificate_path: Path | None,
    private_key_path: Path | None,
    *,
    env: Mapping[str, str] | None = None,
) -> ActivationProvisionerBootstrap:
    values = os.environ if env is None else env
    if state_path is None or certificate_path is None or private_key_path is None:
        return _blocked("PROVISIONER_BOOTSTRAP_INPUTS_REQUIRED")

    state = state_path.expanduser()
    certificate = certificate_path.expanduser()
    private_key = private_key_path.expanduser()
    state_bytes = _read_trusted_state_bytes(state)
    if state_bytes is None:
        return _blocked("PROVISIONER_STATE_FILE_UNTRUSTED")
    try:
        payload = json.loads(state_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return _blocked("PROVISIONER_STATE_INVALID")
    if not isinstance(payload, dict):
        return _blocked("PROVISIONER_STATE_INVALID")

    applications = payload.get("applications")
    provisioner = (
        applications.get("m365_provisioning_app")
        if isinstance(applications, dict)
        else None
    )
    if (
        str(payload.get("status", "")) != "PASSED"
        or str(payload.get("tenantId", "")).strip().lower() != TENANT_ID
        or not isinstance(provisioner, dict)
        or str(provisioner.get("displayName", "")) != "NaC M365 Provisioning"
        or str(provisioner.get("clientId", "")).strip().lower()
        != PROVISIONER_CLIENT_ID
    ):
        return _blocked("PROVISIONER_STATE_BINDING_MISMATCH")

    if any(str(values.get(name, "")).strip() for name in PROVISIONER_SECRET_KEYS):
        return _blocked("PROVISIONER_CERTIFICATE_MODE_REQUIRED")
    explicit_tenant = str(values.get("M365_TENANT_ID", "")).strip().lower()
    explicit_client = str(
        values.get("M365_PROVISIONER_CLIENT_ID", "")
    ).strip().lower()
    explicit_certificate = str(
        values.get("M365_PROVISIONER_CLIENT_CERTIFICATE_PATH", "")
    ).strip()
    explicit_private_key = str(
        values.get("M365_PROVISIONER_CLIENT_KEY_PATH", "")
    ).strip()
    if (
        explicit_tenant and explicit_tenant != TENANT_ID
        or explicit_client and explicit_client != PROVISIONER_CLIENT_ID
        or explicit_certificate and Path(explicit_certificate).expanduser() != certificate
        or explicit_private_key and Path(explicit_private_key).expanduser() != private_key
    ):
        return _blocked("PROVISIONER_ENV_BINDING_MISMATCH")
    graph_base_url = str(values.get("M365_GRAPH_BASE_URL", _GRAPH_V1)).strip()
    if graph_base_url != _GRAPH_V1:
        return _blocked("PROVISIONER_GRAPH_BASE_URL_INVALID")
    if not _trusted_regular_file_metadata(certificate, private_key=False):
        return _blocked("PROVISIONER_CERTIFICATE_FILE_UNTRUSTED")
    if not _trusted_regular_file_metadata(private_key, private_key=True):
        return _blocked("PROVISIONER_PRIVATE_KEY_FILE_UNTRUSTED")

    bootstrap = build_provisioner_env_bootstrap(
        payload,
        certificate_path=certificate,
        private_key_path=private_key,
        env=values,
    )
    if bootstrap.readiness.get("status") != "PASSED":
        return _blocked("PROVISIONER_ENV_BOOTSTRAP_NOT_READY")
    required_names = {
        "M365_TENANT_ID",
        "M365_PROVISIONER_CLIENT_ID",
        "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH",
        "M365_PROVISIONER_CLIENT_KEY_PATH",
    }
    effective = dict(values)
    effective.update(bootstrap.env_overlay)
    if any(not str(effective.get(name, "")).strip() for name in required_names):
        return _blocked("PROVISIONER_ENV_BOOTSTRAP_NOT_READY")

    binding_sha256 = _bootstrap_binding_sha256(
        state=state,
        state_bytes=state_bytes,
        certificate=certificate,
        private_key=private_key,
        graph_base_url=graph_base_url,
    )
    return ActivationProvisionerBootstrap(
        env_overlay=dict(bootstrap.env_overlay),
        binding_sha256=binding_sha256,
        readiness={
            "schema_version": SCHEMA_VERSION,
            "status": "PASSED",
            "summary": {
                "state_binding_verified": True,
                "certificate_mode_verified": True,
                "certificate_metadata_trusted": True,
                "private_key_metadata_trusted": True,
                "env_overlay_variable_names": sorted(bootstrap.env_overlay),
                "tenant_id_emitted": False,
                "client_id_emitted": False,
                "credential_paths_emitted": False,
                "credential_values_emitted": False,
            },
            "boundaries": _boundaries(),
        },
    )


def _blocked(code: str) -> ActivationProvisionerBootstrap:
    safe_code = (
        code
        if code in PROVISIONER_BOOTSTRAP_ERROR_CODES
        else "PROVISIONER_ENV_BOOTSTRAP_FAILED"
    )
    return ActivationProvisionerBootstrap(
        env_overlay={},
        binding_sha256=None,
        readiness={
            "schema_version": SCHEMA_VERSION,
            "status": "BLOCKED",
            "error_code": safe_code,
            "boundaries": _boundaries(),
        },
    )


def _boundaries() -> dict[str, Any]:
    return {
        "provider_requests_made": 0,
        "private_key_read": False,
        "credential_values_emitted": False,
        "tenant_writes_started": False,
    }


def _read_trusted_state_bytes(path: Path) -> bytes | None:
    if not path.is_absolute() or not _trusted_parent_chain(path.parent):
        return None
    descriptor: int | None = None
    try:
        before = path.lstat()
        if (
            not _trusted_metadata(before, private_key=False)
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > _MAX_STATE_BYTES
        ):
            return None
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        opened = os.fstat(descriptor)
        if not _same_file_snapshot(before, opened):
            return None
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, _MAX_STATE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > _MAX_STATE_BYTES:
                return None
        after = os.fstat(descriptor)
        if not _same_file_snapshot(opened, after) or total != opened.st_size:
            return None
        return b"".join(chunks)
    except OSError:
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _same_file_snapshot(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev,
        left.st_ino,
        left.st_mode,
        left.st_uid,
        left.st_gid,
        left.st_nlink,
        left.st_size,
        left.st_mtime_ns,
        left.st_ctime_ns,
    ) == (
        right.st_dev,
        right.st_ino,
        right.st_mode,
        right.st_uid,
        right.st_gid,
        right.st_nlink,
        right.st_size,
        right.st_mtime_ns,
        right.st_ctime_ns,
    )


def _trusted_regular_file_metadata(path: Path, *, private_key: bool) -> bool:
    if not path.is_absolute() or not _trusted_parent_chain(path.parent):
        return False
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return _trusted_metadata(metadata, private_key=private_key)


def _trusted_metadata(metadata: os.stat_result, *, private_key: bool) -> bool:
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        return False
    if private_key:
        return (
            metadata.st_uid == os.geteuid()
            and stat.S_IMODE(metadata.st_mode) in {0o400, 0o600}
        )
    return (
        metadata.st_uid in {0, os.geteuid()}
        and not metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    )


def _bootstrap_binding_sha256(
    *,
    state: Path,
    state_bytes: bytes,
    certificate: Path,
    private_key: Path,
    graph_base_url: str,
) -> str:
    payload = {
        "certificate_path_sha256": _sha256_text(str(certificate)),
        "graph_base_url": graph_base_url,
        "private_key_path_sha256": _sha256_text(str(private_key)),
        "provisioner_client_id": PROVISIONER_CLIENT_ID,
        "state_path_sha256": _sha256_text(str(state)),
        "state_sha256": hashlib.sha256(state_bytes).hexdigest(),
        "tenant_id": TENANT_ID,
    }
    encoded = json.dumps(
        payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _trusted_parent_chain(path: Path) -> bool:
    try:
        current = path
        while current != current.parent:
            metadata = current.lstat()
            if (
                stat.S_ISLNK(metadata.st_mode)
                or not stat.S_ISDIR(metadata.st_mode)
                or metadata.st_uid not in {0, os.geteuid()}
                or (
                    metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                    and not (
                        metadata.st_uid == 0
                        and metadata.st_mode & stat.S_ISVTX
                    )
                )
            ):
                return False
            current = current.parent
    except OSError:
        return False
    return True
