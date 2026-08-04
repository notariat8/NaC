"""Owner-bound Function configuration for the performance lease broker.

The local process may configure the fixed broker surface, but it never receives
an Azure Storage token.  Azure Blob access remains exclusively on the existing
BFF Function managed identity.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Protocol
from uuid import UUID

from .azure_activation import FUNCTION_APP, RESOURCE_GROUP, SUBSCRIPTION_ID
from .azure_live_commands import AzureCliAdapter


SETTING_PREFIX = "NAC_BFF_PERFORMANCE_LEASE_"
SETTING_NAMES = frozenset(
    {
        f"{SETTING_PREFIX}ENABLED",
        f"{SETTING_PREFIX}TENANT_ID",
        f"{SETTING_PREFIX}ACTOR_ID",
        f"{SETTING_PREFIX}OWNER_SUBJECT",
        f"{SETTING_PREFIX}OWNER_BINDING_SHA256",
        f"{SETTING_PREFIX}COMMIT_SHA",
        f"{SETTING_PREFIX}TREE_SHA",
        f"{SETTING_PREFIX}FUNCTION_PACKAGE_SHA256",
        f"{SETTING_PREFIX}PLAN_SHA256",
        f"{SETTING_PREFIX}TARGET_BINDING_SHA256",
        f"{SETTING_PREFIX}BLOB_PATH",
        f"{SETTING_PREFIX}BLOB_URL",
        f"{SETTING_PREFIX}STORAGE_BINDING_ID",
        f"{SETTING_PREFIX}STORAGE_ATTESTATION_B64",
        f"{SETTING_PREFIX}TICKET_ISSUER",
        f"{SETTING_PREFIX}TICKET_KEY_ID",
        f"{SETTING_PREFIX}TICKET_CERTIFICATE_B64",
        f"{SETTING_PREFIX}TICKET_CERTIFICATE_SHA256",
    }
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")


class BrokerFunctionActivationError(ValueError):
    """Stable value-free failure for the broker activation boundary."""


class AzureCommandPort(Protocol):
    def run(self, argv: object) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class BrokerFunctionSettings:
    values: Mapping[str, str]
    settings_sha256: str


def build_broker_function_settings(
    *,
    tenant_id: str,
    actor_id: str,
    owner_binding_sha256: str,
    commit_sha: str,
    tree_sha: str,
    function_package_sha256: str,
    plan_sha256: str,
    target_binding_sha256: str,
    coordination_storage_account_name: str,
    storage_binding_id: str,
    storage_attestation: bytes,
    ticket_certificate: bytes,
    ticket_certificate_sha256: str,
) -> BrokerFunctionSettings:
    blob_path = f"locks/{target_binding_sha256}.lock"
    values = {
        f"{SETTING_PREFIX}ENABLED": "true",
        f"{SETTING_PREFIX}TENANT_ID": tenant_id,
        f"{SETTING_PREFIX}ACTOR_ID": actor_id,
        f"{SETTING_PREFIX}OWNER_SUBJECT": actor_id,
        f"{SETTING_PREFIX}OWNER_BINDING_SHA256": owner_binding_sha256,
        f"{SETTING_PREFIX}COMMIT_SHA": commit_sha,
        f"{SETTING_PREFIX}TREE_SHA": tree_sha,
        f"{SETTING_PREFIX}FUNCTION_PACKAGE_SHA256": function_package_sha256,
        f"{SETTING_PREFIX}PLAN_SHA256": plan_sha256,
        f"{SETTING_PREFIX}TARGET_BINDING_SHA256": target_binding_sha256,
        f"{SETTING_PREFIX}BLOB_PATH": blob_path,
        f"{SETTING_PREFIX}BLOB_URL": (
            f"https://{coordination_storage_account_name}.blob.core.windows.net/"
            f"nac-bff-performance-leases/{blob_path}"
        ),
        f"{SETTING_PREFIX}STORAGE_BINDING_ID": storage_binding_id,
        f"{SETTING_PREFIX}STORAGE_ATTESTATION_B64": base64.b64encode(
            storage_attestation
        ).decode("ascii"),
        f"{SETTING_PREFIX}TICKET_ISSUER": "nac-performance-owner-gate",
        f"{SETTING_PREFIX}TICKET_KEY_ID": ticket_certificate_sha256[:32],
        f"{SETTING_PREFIX}TICKET_CERTIFICATE_B64": base64.b64encode(
            ticket_certificate
        ).decode("ascii"),
        f"{SETTING_PREFIX}TICKET_CERTIFICATE_SHA256": (
            ticket_certificate_sha256
        ),
    }
    _validate_settings(values)
    return BrokerFunctionSettings(
        values=values,
        settings_sha256=_sha256_json(values),
    )


class BrokerFunctionSettingsPort:
    """Merge and read back only the fixed broker setting namespace."""

    def __init__(self, azure_cli: AzureCommandPort) -> None:
        if not isinstance(azure_cli, AzureCliAdapter) and not (
            callable(getattr(azure_cli, "run", None))
        ):
            raise TypeError("azure_cli")
        self._azure_cli = azure_cli

    def configure_and_verify(
        self, settings: BrokerFunctionSettings
    ) -> dict[str, Any]:
        if type(settings) is not BrokerFunctionSettings:
            raise BrokerFunctionActivationError(
                "BROKER_FUNCTION_SETTINGS_INVALID"
            )
        _validate_settings(settings.values)
        if _sha256_json(settings.values) != settings.settings_sha256:
            raise BrokerFunctionActivationError(
                "BROKER_FUNCTION_SETTINGS_INVALID"
            )
        argv = [
            "functionapp",
            "config",
            "appsettings",
            "set",
            "--name",
            FUNCTION_APP,
            "--resource-group",
            RESOURCE_GROUP,
            "--settings",
            *[f"{name}={settings.values[name]}" for name in sorted(SETTING_NAMES)],
            "--subscription",
            SUBSCRIPTION_ID,
        ]
        _require_cli_success(self._azure_cli.run(argv))
        readback = _require_cli_success(
            self._azure_cli.run(
                [
                    "functionapp",
                    "config",
                    "appsettings",
                    "list",
                    "--name",
                    FUNCTION_APP,
                    "--resource-group",
                    RESOURCE_GROUP,
                    "--subscription",
                    SUBSCRIPTION_ID,
                ]
            )
        )
        observed = _extract_settings(readback)
        if observed != dict(settings.values):
            raise BrokerFunctionActivationError(
                "BROKER_FUNCTION_SETTINGS_READBACK_MISMATCH"
            )
        return {
            "status": "VERIFIED",
            "function_app": FUNCTION_APP,
            "setting_count": len(observed),
            "settings_sha256": settings.settings_sha256,
            "values_emitted": False,
        }


def _extract_settings(payload: object) -> dict[str, str]:
    if not isinstance(payload, list):
        raise BrokerFunctionActivationError(
            "BROKER_FUNCTION_SETTINGS_READBACK_INVALID"
        )
    observed: dict[str, str] = {}
    performance_names: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise BrokerFunctionActivationError(
                "BROKER_FUNCTION_SETTINGS_READBACK_INVALID"
            )
        name = item.get("name")
        if isinstance(name, str) and name.startswith(SETTING_PREFIX):
            performance_names.add(name)
            value = item.get("value")
            if (
                name not in SETTING_NAMES
                or not isinstance(value, str)
                or name in observed
            ):
                raise BrokerFunctionActivationError(
                    "BROKER_FUNCTION_SETTINGS_READBACK_MISMATCH"
                )
            observed[name] = value
    if performance_names != set(SETTING_NAMES):
        raise BrokerFunctionActivationError(
            "BROKER_FUNCTION_SETTINGS_READBACK_MISMATCH"
        )
    _validate_settings(observed)
    return observed


def _require_cli_success(result: object) -> object:
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise BrokerFunctionActivationError("BROKER_FUNCTION_AZURE_FAILED")
    value = result.get("value")
    if value is None:
        raise BrokerFunctionActivationError("BROKER_FUNCTION_AZURE_FAILED")
    return value


def _validate_settings(values: Mapping[str, str]) -> None:
    if set(values) != set(SETTING_NAMES):
        raise BrokerFunctionActivationError("BROKER_FUNCTION_SETTINGS_INVALID")
    if values[f"{SETTING_PREFIX}ENABLED"] != "true":
        raise BrokerFunctionActivationError("BROKER_FUNCTION_SETTINGS_INVALID")
    try:
        UUID(values[f"{SETTING_PREFIX}TENANT_ID"])
        UUID(values[f"{SETTING_PREFIX}ACTOR_ID"])
        UUID(values[f"{SETTING_PREFIX}OWNER_SUBJECT"])
    except (TypeError, ValueError):
        raise BrokerFunctionActivationError(
            "BROKER_FUNCTION_SETTINGS_INVALID"
        ) from None
    if (
        values[f"{SETTING_PREFIX}ACTOR_ID"]
        != values[f"{SETTING_PREFIX}OWNER_SUBJECT"]
    ):
        raise BrokerFunctionActivationError("BROKER_FUNCTION_SETTINGS_INVALID")
    if any(
        not isinstance(value, str)
        or not value
        or len(value) > 8192
        or any(character in value for character in "\r\n\x00")
        for value in values.values()
    ):
        raise BrokerFunctionActivationError("BROKER_FUNCTION_SETTINGS_INVALID")
    for name in (
        f"{SETTING_PREFIX}OWNER_BINDING_SHA256",
        f"{SETTING_PREFIX}TREE_SHA",
        f"{SETTING_PREFIX}FUNCTION_PACKAGE_SHA256",
        f"{SETTING_PREFIX}PLAN_SHA256",
        f"{SETTING_PREFIX}TARGET_BINDING_SHA256",
        f"{SETTING_PREFIX}TICKET_CERTIFICATE_SHA256",
    ):
        if _SHA256_RE.fullmatch(values[name]) is None:
            raise BrokerFunctionActivationError(
                "BROKER_FUNCTION_SETTINGS_INVALID"
            )
    if _COMMIT_RE.fullmatch(values[f"{SETTING_PREFIX}COMMIT_SHA"]) is None:
        raise BrokerFunctionActivationError("BROKER_FUNCTION_SETTINGS_INVALID")
    try:
        certificate = base64.b64decode(
            values[f"{SETTING_PREFIX}TICKET_CERTIFICATE_B64"], validate=True
        )
        attestation = base64.b64decode(
            values[f"{SETTING_PREFIX}STORAGE_ATTESTATION_B64"], validate=True
        )
    except Exception:
        raise BrokerFunctionActivationError(
            "BROKER_FUNCTION_SETTINGS_INVALID"
        ) from None
    if (
        hashlib.sha256(certificate).hexdigest()
        != values[f"{SETTING_PREFIX}TICKET_CERTIFICATE_SHA256"]
        or not 32 <= len(attestation) <= 8192
    ):
        raise BrokerFunctionActivationError("BROKER_FUNCTION_SETTINGS_INVALID")


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


__all__ = [
    "BrokerFunctionActivationError",
    "BrokerFunctionSettings",
    "BrokerFunctionSettingsPort",
    "SETTING_NAMES",
    "build_broker_function_settings",
]
