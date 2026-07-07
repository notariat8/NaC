from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_ENV_BOOTSTRAP_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "runtime-env-bootstrap.redacted.json"
)
DEFAULT_RUNTIME_CERTIFICATE_PATH = Path("/tmp/nac-m365-tools/runtime-cert/nac-m365-runtime.cert.pem")
DEFAULT_RUNTIME_PRIVATE_KEY_PATH = Path("/tmp/nac-m365-tools/runtime-cert/nac-m365-runtime.key.pem")

RUNTIME_ENV_KEYS = [
    "M365_TENANT_ID",
    "M365_RUNTIME_CLIENT_ID",
    "M365_RUNTIME_CLIENT_CERTIFICATE_PATH",
    "M365_RUNTIME_CLIENT_KEY_PATH",
]
RUNTIME_SECRET_KEYS = [
    "M365_RUNTIME_GRAPH_ACCESS_TOKEN",
    "M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE",
    "M365_RUNTIME_CLIENT_SECRET",
    "M365_RUNTIME_CLIENT_KEY_PASSWORD",
]


@dataclass(frozen=True, slots=True)
class RuntimeEnvBootstrap:
    env_overlay: dict[str, str]
    readiness: dict[str, Any]


def load_runtime_env_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_runtime_env_bootstrap(
    runtime_smoke_state: dict[str, Any],
    *,
    certificate_path: Path = DEFAULT_RUNTIME_CERTIFICATE_PATH,
    private_key_path: Path = DEFAULT_RUNTIME_PRIVATE_KEY_PATH,
    env: Mapping[str, str] | None = None,
    now_utc: str | None = None,
) -> RuntimeEnvBootstrap:
    values = env or os.environ
    runtime_application = _dict(runtime_smoke_state.get("runtime_application"))
    tenant = _dict(runtime_smoke_state.get("tenant"))
    tenant_id = _text(tenant.get("tenant_id"))
    client_id = _text(runtime_application.get("client_id"))
    auth_mode = _text(runtime_application.get("authentication_mode"))
    explicit_mode = _explicit_runtime_credential_mode(values)

    env_overlay: dict[str, str] = {}
    if explicit_mode in {None, "client_certificate"}:
        _add_if_missing(env_overlay, values, "M365_TENANT_ID", tenant_id)
        _add_if_missing(env_overlay, values, "M365_RUNTIME_CLIENT_ID", client_id)
        _add_if_missing(env_overlay, values, "M365_RUNTIME_CLIENT_CERTIFICATE_PATH", str(certificate_path))
        _add_if_missing(env_overlay, values, "M365_RUNTIME_CLIENT_KEY_PATH", str(private_key_path))

    effective = dict(values)
    effective.update(env_overlay)
    missing = [key for key in RUNTIME_ENV_KEYS if not _text(effective.get(key))]
    certificate_files_required = explicit_mode not in {"access_token", "client_secret"}
    certificate_file_exists = certificate_path.exists()
    private_key_file_exists = private_key_path.exists()
    checks = [
        _check(
            "runtime_state_attached",
            "PASSED" if runtime_smoke_state else "BLOCKED",
            "Runtime smoke state is available.",
        ),
        _check(
            "certificate_auth_mode_declared",
            "PASSED" if auth_mode == "client_credentials_with_certificate" else "BLOCKED",
            "Runtime smoke state declares certificate-based client credentials.",
        ),
        _check(
            "tenant_and_client_present_in_state",
            "PASSED" if tenant_id and client_id else "BLOCKED",
            "Tenant ID and runtime client ID can be resolved from non-secret runtime state.",
        ),
        _check(
            "runtime_env_overlay_complete",
            "PASSED" if not missing or explicit_mode in {"access_token", "client_secret"} else "BLOCKED",
            "Runtime environment can be supplied to release-gate child processes."
            if not missing or explicit_mode in {"access_token", "client_secret"}
            else "Runtime environment is incomplete: " + ", ".join(missing),
        ),
        _check(
            "certificate_file_presence_checked_without_reading",
            "PASSED" if not certificate_files_required or certificate_file_exists else "REVIEW_REQUIRED",
            "Certificate file path exists; file content was not read."
            if certificate_file_exists
            else "Certificate file is not required for the explicit runtime credential mode."
            if not certificate_files_required
            else "Certificate file path is not present on this host.",
        ),
        _check(
            "private_key_file_presence_checked_without_reading",
            "PASSED" if not certificate_files_required or private_key_file_exists else "REVIEW_REQUIRED",
            "Private-key file path exists; file content was not read."
            if private_key_file_exists
            else "Private-key file is not required for the explicit runtime credential mode."
            if not certificate_files_required
            else "Private-key file path is not present on this host.",
        ),
        _check(
            "secret_values_not_serialized",
            "PASSED",
            "Readiness emits environment variable names and booleans, not values.",
        ),
        _check(
            "owner_gate_required_for_live_use",
            "PASSED",
            "The bootstrap only prepares child-process environment; live release-gate use remains owner-gated.",
            owner_gate_required=True,
        ),
    ]
    status = (
        "BLOCKED"
        if any(check["status"] == "BLOCKED" for check in checks)
        else "REVIEW_REQUIRED"
        if any(check["status"] == "REVIEW_REQUIRED" for check in checks)
        else "PASSED"
    )
    readiness = {
        "schema_version": "nac.m365-runtime-env-bootstrap/v0.1",
        "status": status,
        "generated_at": now_utc or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": {
            "runtime_state_attached": bool(runtime_smoke_state),
            "preferred_authentication_mode": "client_credentials_with_certificate",
            "runtime_authentication_mode": auth_mode,
            "explicit_runtime_credential_mode": explicit_mode,
            "env_overlay_variable_count": len(env_overlay),
            "env_overlay_variable_names": sorted(env_overlay),
            "required_environment_variables": list(RUNTIME_ENV_KEYS),
            "secret_environment_variables_supported_but_not_read": list(RUNTIME_SECRET_KEYS),
            "tenant_id_resolved_from_state": bool(tenant_id),
            "client_id_resolved_from_state": bool(client_id),
            "tenant_id_emitted": False,
            "client_id_emitted": False,
            "certificate_thumbprint_emitted": False,
            "certificate_files_required": certificate_files_required,
            "certificate_path_supplied": bool(certificate_path),
            "private_key_path_supplied": bool(private_key_path),
            "certificate_file_exists": certificate_file_exists,
            "private_key_file_exists": private_key_file_exists,
            "credential_files_read": False,
            "secret_env_values_read": False,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "stores_tokens_or_secrets": False,
            "owner_gate_required_for_live_use": True,
        },
        "checks": checks,
        "errors": [check["message"] for check in checks if check["status"] == "BLOCKED"],
    }
    return RuntimeEnvBootstrap(env_overlay=env_overlay, readiness=readiness)


def write_runtime_env_bootstrap_artifact(readiness: dict[str, Any], output_path: Path) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(readiness, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return readiness


def _explicit_runtime_credential_mode(values: Mapping[str, str]) -> str | None:
    if _text(values.get("M365_RUNTIME_GRAPH_ACCESS_TOKEN")) or _text(values.get("M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE")):
        return "access_token"
    if _text(values.get("M365_RUNTIME_CLIENT_SECRET")):
        return "client_secret"
    if _text(values.get("M365_RUNTIME_CLIENT_CERTIFICATE_PATH")) or _text(
        values.get("M365_RUNTIME_CLIENT_KEY_PATH")
    ):
        return "client_certificate"
    return None


def _add_if_missing(target: dict[str, str], values: Mapping[str, str], key: str, value: str) -> None:
    if not _text(values.get(key)) and value:
        target[key] = value


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _check(
    check_id: str,
    status: str,
    message: str,
    *,
    owner_gate_required: bool = False,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": status,
        "message": message,
        "owner_gate_required": owner_gate_required,
    }
