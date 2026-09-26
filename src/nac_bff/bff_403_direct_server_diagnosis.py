"""Offline Stage A gate and redacted-evidence evaluator for Issue #756.

This module has no Microsoft transport. Its in-memory read-budget gate is only
usable with synthetic test bindings; production construction fails before a
credential provider or a transport provider can be called.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
import hashlib
import hmac
import re
from threading import Lock
from typing import Any

from nac_bff.current_state_read_driver import (
    ReadDriverBlocked,
    validate_redacted_projection,
)


class StageAReadBlocked(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_TARGET_BINDINGS = frozenset({
    "workspace_binding_sha256",
    "app_id_binding_sha256",
    "function_binding_sha256",
    "application_insights_binding_sha256",
    "tenant_binding_sha256",
    "package_binding_sha256",
    "account_binding_sha256",
    "principal_id_binding_sha256",
    "permission_binding_sha256",
    "source_evidence_binding_sha256",
    "avv_dpa_binding_sha256",
    "observation_window_binding_sha256",
    "receipt_binding_sha256",
    "retention_binding_sha256",
    "no_refresh_capability_binding_sha256",
    "commit_binding_sha256",
    "tree_binding_sha256",
    "toolchain_binding_sha256",
})
_OPERATIONS = frozenset({
    "azure_function_metadata",
    "application_insights_metadata",
    "azure_function_request_log",
})
_PROJECTIONS = {
    "azure_function_metadata": ["deployment_class", "configuration_digest"],
    "application_insights_metadata": ["capture_enabled", "retention_covers_window"],
    "azure_function_request_log": [
        "request_observed", "http_class", "request_correlation_binding_sha256"
    ],
}
_REQUIRED_TRUE_GATES = frozenset({
    "provider_read_authorized",
    "credential_access_authorized",
    "no_refresh_capability_proven",
})
_REQUIRED_FALSE_GATES = frozenset({
    "token_refresh_authorized",
    "login_authorized",
    "tenant_write_authorized",
    "deployment_authorized",
    "new_reproduction_authorized",
    "issue_739_release_authorized",
    "issue_632_live_authorized",
})


def _digest(value: object) -> bool:
    return type(value) is str and _HEX64.fullmatch(value) is not None


def _closed_synthetic_contract(contract: object) -> bool:
    """Permit only the tiny in-memory shape used by hermetic gate tests."""
    if not isinstance(contract, dict) or contract.get("status") != "SYNTHETIC_TEST_ONLY":
        return False
    target = contract.get("target")
    if (
        not isinstance(target, dict)
        or set(target) != _TARGET_BINDINGS | {"workspace_class"}
        or target.get("workspace_class") != "synthetic_notary_team_01"
        or not all(_digest(target[name]) for name in _TARGET_BINDINGS)
    ):
        return False
    gates = contract.get("gates")
    if (
        not isinstance(gates, dict)
        or set(gates) != _REQUIRED_TRUE_GATES
        | _REQUIRED_FALSE_GATES
        | {"maximum_provider_reads", "maximum_tenant_writes", "maximum_deployments"}
        or any(gates[name] is not True for name in _REQUIRED_TRUE_GATES)
        or any(gates[name] is not False for name in _REQUIRED_FALSE_GATES)
        or type(gates["maximum_provider_reads"]) is not int
        or gates["maximum_provider_reads"] != 3
        or type(gates["maximum_tenant_writes"]) is not int
        or gates["maximum_tenant_writes"] != 0
        or type(gates["maximum_deployments"]) is not int
        or gates["maximum_deployments"] != 0
    ):
        return False
    resources = contract.get("resources")
    if not isinstance(resources, list) or len(resources) != 3:
        return False
    if {item.get("id") for item in resources if isinstance(item, dict)} != _OPERATIONS:
        return False
    for resource in resources:
        if not isinstance(resource, dict) or resource.get("method") != "GET":
            return False
        operation = resource["id"]
        expected_fields = {
            "id", "method", "endpoint_binding_sha256", "projection", "maximum_reads"
        }
        if operation == "azure_function_request_log":
            expected_fields.add("query_sha256")
        if (
            set(resource) != expected_fields
            or not _digest(resource.get("endpoint_binding_sha256"))
            or type(resource.get("maximum_reads")) is not int
            or resource["maximum_reads"] != 1
            or resource.get("projection") != _PROJECTIONS[operation]
        ):
            return False
        if operation == "azure_function_request_log" and not _digest(resource.get("query_sha256")):
            return False
    policy = contract.get("read_policy")
    if not isinstance(policy, dict) or any(
        policy.get(name) is not False
        for name in (
            "redirect_allowed", "retry_allowed", "paging_allowed", "body_allowed",
            "resource_discovery_allowed",
        )
    ):
        return False
    return (
        policy.get("required_before_port_factory") is True
        and policy.get("required_before_every_read") is True
        and policy.get("atomic_budget_consume") is True
        and policy.get("maximum_historical_query_gets") == 1
        and policy.get("no_refresh_proof_required") is True
        and policy.get("receipt_provenance_required") is True
    )


class StageAReadGate:
    """Reserve one synthetic GET only after exact per-read binding checks."""

    def __init__(self, contract: Mapping[str, Any]) -> None:
        try:
            frozen = deepcopy(dict(contract))
        except (TypeError, ValueError):
            raise StageAReadBlocked("BLOCKED_CONTRACT_BINDING") from None
        if not _closed_synthetic_contract(frozen):
            raise StageAReadBlocked("BLOCKED_CONTRACT_BINDING")
        self._contract = frozen
        self._counts = {name: 0 for name in _OPERATIONS}
        self._lock = Lock()

    def reserve(
        self,
        *,
        operation_id: str,
        current_target: Mapping[str, str],
        endpoint_bytes: bytes,
        query_bytes: bytes | None,
        method: str,
        no_refresh_proven: bool,
        redirect: bool,
        retry: bool,
        paging: bool,
        body: bool,
        resource_discovery: bool,
    ) -> None:
        """Consume a single budget atomically; no transport is invoked here."""
        with self._lock:
            if (
                type(operation_id) is not str
                or operation_id not in _OPERATIONS
                or type(method) is not str
                or method != "GET"
                or no_refresh_proven is not True
                or redirect is not False
                or retry is not False
                or paging is not False
                or body is not False
                or resource_discovery is not False
                or not isinstance(current_target, Mapping)
                or dict(current_target) != self._contract["target"]
                or type(endpoint_bytes) is not bytes
                or (query_bytes is not None and type(query_bytes) is not bytes)
            ):
                raise StageAReadBlocked("BLOCKED_READ_BINDING")
            resource = next(
                item for item in self._contract["resources"] if item["id"] == operation_id
            )
            if (
                not hmac.compare_digest(
                    hashlib.sha256(endpoint_bytes).hexdigest(),
                    resource["endpoint_binding_sha256"],
                )
                or (
                    hashlib.sha256(query_bytes).hexdigest() if query_bytes is not None else None
                ) != resource.get("query_sha256")
            ):
                raise StageAReadBlocked("BLOCKED_READ_BINDING")
            if (
                self._counts[operation_id] >= resource["maximum_reads"]
                or sum(self._counts.values()) >= self._contract["gates"]["maximum_provider_reads"]
            ):
                raise StageAReadBlocked("BLOCKED_READ_BUDGET")
            self._counts[operation_id] += 1


def create_production_read_gate(
    *, credential_provider: Callable[[], object], transport_provider: Callable[[], object]
) -> StageAReadGate:
    """The product has no reviewed no-refresh read capability for this path."""
    del credential_provider, transport_provider
    raise StageAReadBlocked("BLOCKED_NO_REFRESH_CAPABILITY")


def _projection(operation: str, value: object) -> dict[str, Any]:
    try:
        return validate_redacted_projection(operation, value)
    except (ReadDriverBlocked, TypeError, ValueError):
        raise StageAReadBlocked("BLOCKED_RESPONSE_REDACTION") from None


def evaluate_stage_a_evidence(
    *,
    function_metadata: object,
    insights_metadata: object,
    request_log: object,
    expected_receipt_binding_sha256: str,
    target_binding_verified: bool,
    metadata_authoritative: bool,
    receipt_provenance_verified: bool,
    unique_correlation_verified: bool,
) -> str:
    """Classify closed redacted evidence, never infer the underlying 403 cause."""
    function = _projection("azure_function_metadata", function_metadata)
    log = _projection("azure_function_request_log", request_log)
    if (
        not isinstance(insights_metadata, Mapping)
        or set(insights_metadata) != {"capture_enabled", "retention_covers_window"}
        or any(type(value) is not bool for value in insights_metadata.values())
    ):
        raise StageAReadBlocked("BLOCKED_RESPONSE_REDACTION")
    if not _digest(expected_receipt_binding_sha256):
        raise StageAReadBlocked("BLOCKED_RECEIPT_BINDING")
    if target_binding_verified is not True:
        return "UNPROVEN"
    if function["deployment_class"] == "not_deployed":
        return (
            "BFF_NOT_DEPLOYED"
            if metadata_authoritative is True and log["request_observed"] is False
            else "UNPROVEN"
        )
    if (
        insights_metadata["capture_enabled"] is not True
        or insights_metadata["retention_covers_window"] is not True
        or log["request_observed"] is not True
        or log["http_class"] not in {"401", "403"}
        or metadata_authoritative is not True
        or receipt_provenance_verified is not True
        or unique_correlation_verified is not True
    ):
        return "UNPROVEN"
    if not hmac.compare_digest(
        expected_receipt_binding_sha256,
        log["request_correlation_binding_sha256"],
    ):
        return "UNPROVEN"
    return "REQUEST_ATTRIBUTED_STATUS_ONLY"


__all__ = [
    "StageAReadBlocked",
    "StageAReadGate",
    "create_production_read_gate",
    "evaluate_stage_a_evidence",
]
