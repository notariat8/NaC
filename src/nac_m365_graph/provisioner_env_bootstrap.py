from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


PROVISIONER_ENV_KEYS = [
    "M365_TENANT_ID",
    "M365_PROVISIONER_CLIENT_ID",
    "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH",
    "M365_PROVISIONER_CLIENT_KEY_PATH",
]
PROVISIONER_SECRET_KEYS = [
    "M365_GRAPH_ACCESS_TOKEN",
    "M365_GRAPH_ACCESS_TOKEN_FILE",
    "M365_PROVISIONER_CLIENT_SECRET",
    "M365_PROVISIONER_CLIENT_KEY_PASSWORD",
]


@dataclass(frozen=True, slots=True)
class ProvisionerEnvBootstrap:
    env_overlay: dict[str, str]
    readiness: dict[str, Any]


def load_provisioner_env_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_provisioner_env_bootstrap(
    privileged_apply_state: dict[str, Any],
    *,
    certificate_path: Path | None,
    private_key_path: Path | None,
    env: Mapping[str, str] | None = None,
    now_utc: str | None = None,
) -> ProvisionerEnvBootstrap:
    values = os.environ if env is None else env
    applications = _dict(privileged_apply_state.get("applications"))
    provisioner = _dict(applications.get("m365_provisioning_app"))
    tenant_id = _text(privileged_apply_state.get("tenantId"))
    client_id = _text(provisioner.get("clientId"))
    display_name = _text(provisioner.get("displayName"))
    state_status = _text(privileged_apply_state.get("status"))
    explicit_mode = _explicit_provisioner_credential_mode(values)
    explicit_tenant_id = _text(values.get("M365_TENANT_ID"))
    explicit_client_id = _text(values.get("M365_PROVISIONER_CLIENT_ID"))
    tenant_mismatch = bool(explicit_tenant_id and tenant_id and explicit_tenant_id != tenant_id)
    client_mismatch = bool(explicit_client_id and client_id and explicit_client_id != client_id)

    env_overlay: dict[str, str] = {}
    if explicit_mode in {None, "client_certificate"} and not tenant_mismatch and not client_mismatch:
        _add_if_missing(env_overlay, values, "M365_TENANT_ID", tenant_id)
        _add_if_missing(env_overlay, values, "M365_PROVISIONER_CLIENT_ID", client_id)
        _add_if_missing(
            env_overlay,
            values,
            "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH",
            str(certificate_path) if certificate_path else "",
        )
        _add_if_missing(
            env_overlay,
            values,
            "M365_PROVISIONER_CLIENT_KEY_PATH",
            str(private_key_path) if private_key_path else "",
        )

    effective = dict(values)
    effective.update(env_overlay)
    missing = [key for key in PROVISIONER_ENV_KEYS if not _text(effective.get(key))]
    certificate_files_required = explicit_mode not in {"access_token", "client_secret"}
    effective_certificate = Path(_text(effective.get("M365_PROVISIONER_CLIENT_CERTIFICATE_PATH")))
    effective_private_key = Path(_text(effective.get("M365_PROVISIONER_CLIENT_KEY_PATH")))
    certificate_file_exists = bool(str(effective_certificate)) and effective_certificate.is_file()
    private_key_file_exists = bool(str(effective_private_key)) and effective_private_key.is_file()
    state_is_provisioner = display_name == "NaC M365 Provisioning"

    checks = [
        _check(
            "privileged_apply_state_attached",
            "PASSED" if privileged_apply_state else "BLOCKED",
            "Privileged-apply state is available.",
        ),
        _check(
            "privileged_apply_state_passed",
            "PASSED" if state_status == "PASSED" else "BLOCKED",
            "Privileged-apply state passed its provisioning checks.",
        ),
        _check(
            "dedicated_provisioning_app_resolved",
            "PASSED" if tenant_id and client_id and state_is_provisioner else "BLOCKED",
            "Tenant and dedicated provisioning application are resolved from local non-secret state.",
        ),
        _check(
            "explicit_tenant_matches_state",
            "BLOCKED" if tenant_mismatch else "PASSED",
            "Explicit tenant matches the privileged-apply state."
            if not tenant_mismatch
            else "Explicit tenant conflicts with the privileged-apply state.",
        ),
        _check(
            "explicit_client_matches_provisioning_app",
            "BLOCKED" if client_mismatch else "PASSED",
            "Explicit client ID matches the dedicated provisioning application."
            if not client_mismatch
            else "Explicit client ID is not the dedicated provisioning application.",
        ),
        _check(
            "provisioner_env_overlay_complete",
            "PASSED" if not missing or explicit_mode in {"access_token", "client_secret"} else "BLOCKED",
            "Provisioner environment can be supplied before token acquisition."
            if not missing or explicit_mode in {"access_token", "client_secret"}
            else "Provisioner environment is incomplete: " + ", ".join(missing),
        ),
        _check(
            "certificate_file_presence_checked_without_reading",
            "PASSED" if not certificate_files_required or certificate_file_exists else "BLOCKED",
            "Certificate file path exists; file content was not read."
            if certificate_file_exists
            else "Certificate file is not required for the explicit credential mode."
            if not certificate_files_required
            else "Certificate file path is not present on this host.",
        ),
        _check(
            "private_key_file_presence_checked_without_reading",
            "PASSED" if not certificate_files_required or private_key_file_exists else "BLOCKED",
            "Private-key file path exists; file content was not read."
            if private_key_file_exists
            else "Private-key file is not required for the explicit credential mode."
            if not certificate_files_required
            else "Private-key file path is not present on this host.",
        ),
        _check(
            "secret_values_not_serialized",
            "PASSED",
            "Readiness emits variable names and booleans, not identifiers or credential values.",
        ),
        _check(
            "owner_gate_required_for_live_use",
            "PASSED",
            "The bootstrap performs no Graph request; live schema apply remains owner-gated.",
            owner_gate_required=True,
        ),
    ]
    status = "BLOCKED" if any(check["status"] == "BLOCKED" for check in checks) else "PASSED"
    readiness = {
        "schema_version": "nac.m365-provisioner-env-bootstrap/v0.1",
        "status": status,
        "generated_at": now_utc or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": {
            "privileged_apply_state_attached": bool(privileged_apply_state),
            "dedicated_provisioning_app_resolved": bool(tenant_id and client_id and state_is_provisioner),
            "preferred_authentication_mode": "client_credentials_with_certificate",
            "explicit_provisioner_credential_mode": explicit_mode,
            "explicit_tenant_matches_state": not tenant_mismatch,
            "explicit_client_matches_provisioning_app": not client_mismatch,
            "env_overlay_variable_count": len(env_overlay),
            "env_overlay_variable_names": sorted(env_overlay),
            "required_environment_variables": list(PROVISIONER_ENV_KEYS),
            "secret_environment_variables_supported_but_not_read": list(PROVISIONER_SECRET_KEYS),
            "tenant_id_resolved_from_state": bool(tenant_id),
            "client_id_resolved_from_state": bool(client_id),
            "tenant_id_emitted": False,
            "client_id_emitted": False,
            "certificate_thumbprint_emitted": False,
            "certificate_files_required": certificate_files_required,
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
    return ProvisionerEnvBootstrap(env_overlay=env_overlay, readiness=readiness)


def write_provisioner_env_bootstrap_artifact(readiness: dict[str, Any], output_path: Path) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(readiness, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return readiness


def _explicit_provisioner_credential_mode(values: Mapping[str, str]) -> str | None:
    if _text(values.get("M365_GRAPH_ACCESS_TOKEN")) or _text(values.get("M365_GRAPH_ACCESS_TOKEN_FILE")):
        return "access_token"
    if _text(values.get("M365_PROVISIONER_CLIENT_SECRET")):
        return "client_secret"
    if _text(values.get("M365_PROVISIONER_CLIENT_CERTIFICATE_PATH")) or _text(
        values.get("M365_PROVISIONER_CLIENT_KEY_PATH")
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
