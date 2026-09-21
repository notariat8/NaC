from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .current_state_access_diagnostic import (
    AcquisitionEnvelope,
    DiagnosticBlockedError,
    DiagnosticSnapshot,
    build_decision_projection,
    build_snapshot,
    compare_snapshots,
)
from .current_state_access_gate import (
    CurrentStateRunAuthorization,
    GateInput,
    _authorize_protected_current_state_run,
    consume_current_state_run_gate,
    verify_consumed_current_state_run_gate,
)
from .current_state_access_ports import CurrentStateAccessPorts, PortReadResult
from .current_state_access_adapters import (
    _AttestedProcessReadTransport,
    build_current_state_access_ports,
)


PROTECTED_INPUT_FILES = (
    "contract.json",
    "resolver.json",
    "target.json",
    "dpa-avv-agreement-evidence.json",
    "dpa-avv-receipt.json",
    "client-observation-receipt.json",
    "owner-approval.json",
    "toolchain.json",
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _load_protected_payloads(*, input_path: Path, backend: Any):
    payloads: dict[str, dict[str, Any]] = {}
    snapshots: dict[str, Any] = {}
    for name in PROTECTED_INPUT_FILES:
        path = input_path / name
        snapshot = backend.inspect_private_path(path, purpose=f"issue748-{name}")
        if snapshot.size > 128 * 1024:
            raise ValueError("protected input exceeds size limit")
        with backend.open_bound_read(path, snapshot) as handle:
            raw = handle.read(128 * 1024 + 1)
        if len(raw) > 128 * 1024 or hashlib.sha256(raw).hexdigest() != snapshot.sha256:
            raise ValueError("protected input binding drift")
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
        if not isinstance(value, dict):
            raise ValueError("protected input must be a JSON object")
        payloads[name] = value
        snapshots[name] = snapshot
    return payloads, snapshots


def _closed(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise DiagnosticBlockedError(code)
    return value


def _hex(value: Any, code: str, *, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise DiagnosticBlockedError(code)
    return value


def _string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value:
        raise DiagnosticBlockedError(code)
    return value


def _bool(value: Any, code: str) -> bool:
    if type(value) is not bool:
        raise DiagnosticBlockedError(code)
    return value


def _integer(value: Any, expected: int, code: str) -> int:
    if type(value) is not int or value != expected:
        raise DiagnosticBlockedError(code)
    return value


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def preflight_current_state_access_diagnostic(
    *, input_root: Any, evidence_root: Any, repo_root: Any, backend: Any | None = None
) -> dict[str, Any]:
    from pathlib import Path

    input_path = Path(input_root)
    evidence_path = Path(evidence_root)
    repository = Path(repo_root).resolve()
    if not input_path.is_absolute() or not evidence_path.is_absolute():
        return _blocked("PROTECTED_ABSOLUTE_PATH_REQUIRED")
    for candidate in (input_path, evidence_path):
        try:
            candidate.resolve().relative_to(repository)
        except ValueError:
            pass
        else:
            return _blocked("PROTECTED_PATH_MUST_BE_REPOSITORY_EXTERNAL")
    try:
        if backend is None:
            from .activation_security_backend import get_platform_security_backend

            backend = get_platform_security_backend()
        _load_protected_payloads(input_path=input_path, backend=backend)
        session = backend.open_secure_directory(
            evidence_path,
            create=False,
            require_current_owner=True,
            require_restrictive_dacl=True,
        )
        session.close()
    except (OSError, RuntimeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return _blocked("PROTECTED_INPUT_BINDING_INVALID")
    return {
        "schema_version": "nac.m365-current-state-access-diagnostic-preflight/v1",
        "status": "READY",
        "provider_ports_created": 0,
        "network_reads": 0,
        "credential_writes": 0,
        "provider_writes": 0,
        "live_run_authorized": False,
    }


def _blocked(code: str) -> dict[str, Any]:
    return {
        "schema_version": "nac.m365-current-state-access-diagnostic-preflight/v1",
        "status": "BLOCKED",
        "reason_code": code,
        "provider_ports_created": 0,
        "network_reads": 0,
        "credential_writes": 0,
        "provider_writes": 0,
        "live_run_authorized": False,
    }


def _sha256_receipts(receipts: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(receipts, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _acquire(
    *,
    sequence: int,
    authorization: CurrentStateRunAuthorization,
    ports: CurrentStateAccessPorts,
    bindings: Mapping[str, str],
    observation_window: Mapping[str, str],
    target_projection: Mapping[str, str],
    protected_client_fact: Mapping[str, Any] | None,
    clock: Callable[[], datetime],
) -> DiagnosticSnapshot:
    initial_results: list[PortReadResult] = [
        ports.client_observation.read(authorization),
        ports.app_catalog.read(authorization),
        ports.request_log.read(authorization),
    ]
    if [result.operation for result in initial_results] != [
        "client_observation_receipt",
        "sharepoint_app_catalog",
        "azure_function_request_log",
    ]:
        raise DiagnosticBlockedError("BLOCKED_PORT_RECEIPT_ORDER")
    client, catalog, request = (result.data for result in initial_results)
    if protected_client_fact is not None and (
        client["ui_state"] != protected_client_fact["ui_state"]
        or client["spfx_subject_available"]
        is not protected_client_fact["spfx_subject_available"]
    ):
        raise DiagnosticBlockedError("BLOCKED_CLIENT_RECEIPT_FACT_DRIFT")
    if (
        client["client_receipt_sha256"]
        != observation_window["client_receipt_sha256"]
        or request["request_correlation_binding_sha256"]
        != observation_window["request_correlation_binding_sha256"]
    ):
        raise DiagnosticBlockedError("BLOCKED_OBSERVATION_CORRELATION_BINDING")
    if catalog["api_permission_match"] is not True:
        raise DiagnosticBlockedError("BLOCKED_DEPLOYED_CLIENT_BINDING_UNAVAILABLE")
    if client["spfx_subject_available"] is False:
        results = initial_results
        delegated_matches = True
        access_matches = True
        network_reads = 2
    else:
        remaining_results: list[PortReadResult] = [
            ports.teams_tab.read(authorization),
            ports.entra_permissions.read(authorization),
            ports.function_metadata.read(authorization),
            ports.access_decision.read(authorization),
        ]
        if [result.operation for result in remaining_results] != [
            "teams_tab_metadata",
            "entra_api_permission",
            "azure_function_metadata",
            "sharepoint_access_decision",
        ]:
            raise DiagnosticBlockedError("BLOCKED_PORT_RECEIPT_ORDER")
        results = [*initial_results, *remaining_results]
        teams, entra, function, access = (
            result.data for result in remaining_results
        )
        if (
            teams["contract_matches"] is not True
            or function["deployment_class"] not in {"deployed", "not_deployed"}
        ):
            raise DiagnosticBlockedError("BLOCKED_DEPLOYED_CLIENT_BINDING_UNAVAILABLE")
        delegated_matches = all(
            value is True
            for value in (
                entra["tenant_match"],
                entra["audience_match"],
                entra["scope_match"],
                entra["preauthorization_match"],
                catalog["api_permission_match"],
            )
        )
        access_matches = access["evidence_matches"]
        network_reads = 6
    projection = build_decision_projection(
        target=target_projection,
        bindings=bindings,
        observation_window=observation_window,
        observations={
            "spfx_subject_available": client["spfx_subject_available"],
            "matching_bff_request_observed": request["request_observed"],
            "bff_http_class": request["http_class"],
            "delegated_scope_contract_matches": delegated_matches,
            "access_decision_evidence_matches": access_matches,
        },
        side_effect_counters={
            "port_factory": 1,
            "network_read": network_reads,
            "run_gate_consume_write": 1,
            "result_evidence_write": 1,
            **{
                key: 0
                for key in (
                    "login", "device_code", "browser_authentication",
                    "token_refresh", "token_import", "credential_export",
                    "credential_write", "cache_write", "configuration_write",
                    "redirect_follow", "retry", "second_real_run",
                    "tenant_write", "provider_write", "deployment",
                    "issue_739_release", "issue_632_authorization",
                )
            },
        },
    )
    acquired_at = clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
    return build_snapshot(
        envelope=AcquisitionEnvelope(
            sequence,
            acquired_at,
            _sha256_receipts([result.receipt_sha256 for result in results]),
            tuple(result.receipt_sha256 for result in results),
        ),
        projection=projection,
    )


def run_double_snapshot_diagnostic(
    *,
    authorization: CurrentStateRunAuthorization,
    ports: CurrentStateAccessPorts,
    bindings: Mapping[str, str],
    observation_window: Mapping[str, str],
    target_projection: Mapping[str, str] = {
        "workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"
    },
    protected_client_fact: Mapping[str, Any] | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> tuple[str, DiagnosticSnapshot, DiagnosticSnapshot]:
    first = _acquire(
        sequence=1,
        authorization=authorization,
        ports=ports,
        bindings=bindings,
        observation_window=observation_window,
        target_projection=target_projection,
        protected_client_fact=protected_client_fact,
        clock=clock,
    )
    second = _acquire(
        sequence=2,
        authorization=authorization,
        ports=ports,
        bindings=bindings,
        observation_window=observation_window,
        target_projection=target_projection,
        protected_client_fact=protected_client_fact,
        clock=clock,
    )
    return compare_snapshots(first, second), first, second


def run_current_state_access_diagnostic_from_protected_inputs(
    *,
    input_root: Path,
    evidence_root: Path,
    repo_root: Path,
    backend: Any | None = None,
) -> tuple[str, DiagnosticSnapshot, DiagnosticSnapshot]:
    """Load authoritative protected evidence and run the single read-only diagnostic."""

    if backend is None:
        from .activation_security_backend import get_platform_security_backend

        backend = get_platform_security_backend()
    preflight = preflight_current_state_access_diagnostic(
        input_root=input_root, evidence_root=evidence_root, repo_root=repo_root,
        backend=backend,
    )
    if preflight["status"] != "READY":
        raise DiagnosticBlockedError(str(preflight["reason_code"]))
    payloads, snapshots = _load_protected_payloads(
        input_path=input_root, backend=backend
    )
    contract = _closed(
        payloads["contract.json"],
        {
            "schema_version", "issue", "pr", "base_pr", "base_merge_commit",
            "base_tree", "final_head", "final_tree", "required_checks_sha256",
        },
        "BLOCKED_CONTRACT_SCHEMA",
    )
    resolver = _closed(
        payloads["resolver.json"],
        {
            "schema_version", "operator_account_id", "operator_principal_id",
            "authorized_account_id", "authorized_principal_id", "provider",
        },
        "BLOCKED_RESOLVER_SCHEMA",
    )
    target_doc = _closed(
        payloads["target.json"],
        {
            "schema_version", "tenant_binding_sha256", "target_binding_sha256",
            "account_permission_sha256", "target", "bindings", "observation_window",
        },
        "BLOCKED_TARGET_SCHEMA",
    )
    dpa = _closed(
        payloads["dpa-avv-receipt.json"],
        {
            "schema_version", "status", "basis", "purpose",
            "scope_binding_sha256", "policy_reference", "policy_sha256",
            "permitted_data_scope", "retention_days", "deletion_mode",
            "retention_binding_sha256", "approval_core_sha256", "run_nonce_sha256",
            "agreement_evidence_sha256",
        },
        "BLOCKED_DPA_AVV_BINDING",
    )
    dpa_evidence = _closed(
        payloads["dpa-avv-agreement-evidence.json"],
        {
            "schema_version", "provider", "tenant_binding_sha256",
            "target_payload_sha256", "agreement_status",
            "agreement_identifier_sha256", "effective_from_utc",
            "expires_at_utc",
        },
        "BLOCKED_DPA_AVV_BINDING",
    )
    approval = _closed(
        payloads["owner-approval.json"],
        {
            "schema_version", "approval_mode",
            "four_eyes_satisfied", "external_two_person_required",
            "external_requirement_citation", "run_nonce_sha256", "head", "tree",
            "target_payload_sha256", "operator_account_binding_sha256",
            "operator_principal_binding_sha256", "dpa_avv_binding_sha256",
            "contract_sha256", "toolchain_sha256", "evidence_root_binding_sha256",
            "client_receipt_sha256", "observation_window_sha256",
            "request_correlation_binding_sha256",
        },
        "BLOCKED_APPROVAL_SCHEMA",
    )
    client_receipt = _closed(
        payloads["client-observation-receipt.json"],
        {
            "window_binding_sha256", "request_correlation_binding_sha256",
            "start_utc", "end_utc", "ui_state", "spfx_subject_available",
        },
        "BLOCKED_CLIENT_RECEIPT_SCHEMA",
    )
    toolchain = _closed(
        payloads["toolchain.json"],
        {"schema_version", "read_driver_path", "read_driver_sha256"},
        "BLOCKED_TOOLCHAIN_SCHEMA",
    )
    for document in (
        contract, resolver, target_doc, dpa, dpa_evidence, approval, toolchain
    ):
        if document.get("schema_version") != "v1":
            raise DiagnosticBlockedError("BLOCKED_SCHEMA_VERSION")
    if dpa["status"] != "valid":
        raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING")
    target = target_doc["target"]
    if target != {
        "workspace_id": "notary_team_01",
        "app_id": "nac-vorgangsansicht",
    }:
        raise DiagnosticBlockedError("BLOCKED_TARGET_SCHEMA")
    for code, value in (
        ("BLOCKED_CONTRACT_SCHEMA", contract["base_merge_commit"]),
        ("BLOCKED_CONTRACT_SCHEMA", contract["base_tree"]),
        ("BLOCKED_CONTRACT_SCHEMA", contract["final_head"]),
        ("BLOCKED_CONTRACT_SCHEMA", contract["final_tree"]),
    ):
        _hex(value, code, length=40)
    _integer(contract["issue"], 748, "BLOCKED_CONTRACT_SCHEMA")
    _integer(contract["pr"], 749, "BLOCKED_CONTRACT_SCHEMA")
    _integer(contract["base_pr"], 747, "BLOCKED_CONTRACT_SCHEMA")
    _hex(contract["required_checks_sha256"], "BLOCKED_CONTRACT_SCHEMA")
    for field in (
        "tenant_binding_sha256", "target_binding_sha256",
        "account_permission_sha256",
    ):
        _hex(target_doc[field], "BLOCKED_TARGET_SCHEMA")
    if not isinstance(target_doc["bindings"], dict) or not isinstance(
        target_doc["observation_window"], dict
    ):
        raise DiagnosticBlockedError("BLOCKED_TARGET_SCHEMA")
    observation_window = _closed(
        target_doc["observation_window"],
        {
            "start_utc", "end_utc", "window_binding_sha256",
            "client_receipt_sha256", "request_correlation_binding_sha256",
        },
        "BLOCKED_TARGET_SCHEMA",
    )
    for field in (
        "window_binding_sha256", "client_receipt_sha256",
        "request_correlation_binding_sha256",
    ):
        _hex(observation_window[field], "BLOCKED_TARGET_SCHEMA")
    _string(observation_window["start_utc"], "BLOCKED_TARGET_SCHEMA")
    _string(observation_window["end_utc"], "BLOCKED_TARGET_SCHEMA")
    target_payload_sha256 = _canonical_sha256(target)
    if target_doc["target_binding_sha256"] != target_payload_sha256:
        raise DiagnosticBlockedError("BLOCKED_TARGET_BINDING")
    client_snapshot_sha256 = snapshots["client-observation-receipt.json"].sha256
    if (
        client_receipt["window_binding_sha256"]
        != observation_window["window_binding_sha256"]
        or client_receipt["request_correlation_binding_sha256"]
        != observation_window["request_correlation_binding_sha256"]
        or client_receipt["start_utc"] != observation_window["start_utc"]
        or client_receipt["end_utc"] != observation_window["end_utc"]
        or client_snapshot_sha256 != observation_window["client_receipt_sha256"]
    ):
        raise DiagnosticBlockedError("BLOCKED_CLIENT_RECEIPT_BINDING")
    if (
        client_receipt["ui_state"] != "no_access"
        or type(client_receipt["spfx_subject_available"]) is not bool
        or client_receipt["window_binding_sha256"]
        != _canonical_sha256(
            {
                "end_utc": client_receipt["end_utc"],
                "request_correlation_binding_sha256": client_receipt[
                    "request_correlation_binding_sha256"
                ],
                "spfx_subject_available": client_receipt[
                    "spfx_subject_available"
                ],
                "start_utc": client_receipt["start_utc"],
                "ui_state": client_receipt["ui_state"],
            }
        )
    ):
        raise DiagnosticBlockedError("BLOCKED_CLIENT_RECEIPT_SCHEMA")
    expected_dpa_scope = _canonical_sha256(
        {
            "provider": resolver["provider"],
            "tenant_binding_sha256": target_doc["tenant_binding_sha256"],
            "target_payload_sha256": target_payload_sha256,
        }
    )
    if (
        resolver["provider"] != "microsoft"
        or not resolver["operator_account_id"].startswith("microsoft:")
        or not resolver["authorized_account_id"].startswith("microsoft:")
    ):
        raise DiagnosticBlockedError("BLOCKED_ACCOUNT_PERMISSION_BINDING")
    if dpa["scope_binding_sha256"] != expected_dpa_scope:
        raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING")
    allowed_provider_operations = [
        "client_observation_receipt", "teams_tab_metadata",
        "sharepoint_app_catalog", "entra_api_permission",
        "azure_function_metadata", "azure_function_request_log",
        "sharepoint_access_decision",
    ]
    expected_account_permission = _canonical_sha256(
        {
            "account_id": resolver["operator_account_id"],
            "provider": resolver["provider"],
            "tenant_binding_sha256": target_doc["tenant_binding_sha256"],
            "target_payload_sha256": target_payload_sha256,
            "operations": allowed_provider_operations,
        }
    )
    if target_doc["account_permission_sha256"] != expected_account_permission:
        raise DiagnosticBlockedError("BLOCKED_ACCOUNT_PERMISSION_BINDING")
    if (
        dpa["basis"] != "applicable_dpa"
        or dpa["purpose"] != "issue748_current_state_access_read_only"
        or dpa["policy_reference"] != "policies/data-protection-policy.yaml"
    ):
        raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING")
    for field in (
        "policy_sha256", "retention_binding_sha256", "approval_core_sha256",
        "run_nonce_sha256", "agreement_evidence_sha256",
    ):
        _hex(dpa[field], "BLOCKED_DPA_AVV_BINDING")
    policy_path = repo_root.resolve() / dpa["policy_reference"]
    policy_snapshot = backend.inspect_bound_input_path(
        policy_path, purpose="issue748-dpa-policy"
    )
    with backend.open_bound_input_read(
        policy_path, policy_snapshot
    ) as policy_handle:
        policy_bytes = policy_handle.read(128 * 1024 + 1)
    if (
        len(policy_bytes) > 128 * 1024
        or hashlib.sha256(policy_bytes).hexdigest() != policy_snapshot.sha256
        or dpa["policy_sha256"] != policy_snapshot.sha256
    ):
        raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING")
    for field in (
        "tenant_binding_sha256", "target_payload_sha256",
        "agreement_identifier_sha256",
    ):
        _hex(dpa_evidence[field], "BLOCKED_DPA_AVV_BINDING")
    try:
        effective_from = datetime.fromisoformat(
            str(dpa_evidence["effective_from_utc"]).replace("Z", "+00:00")
        )
        expires_at = datetime.fromisoformat(
            str(dpa_evidence["expires_at_utc"]).replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING") from exc
    def verify_dpa_effective_now() -> None:
        if (
            dpa_evidence["agreement_status"] != "effective"
            or not (effective_from <= _utc_now() < expires_at)
        ):
            raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING")

    if (
        dpa_evidence["provider"] != resolver["provider"]
        or dpa_evidence["tenant_binding_sha256"]
        != target_doc["tenant_binding_sha256"]
        or dpa_evidence["target_payload_sha256"] != target_payload_sha256
        or dpa["agreement_evidence_sha256"]
        != snapshots["dpa-avv-agreement-evidence.json"].sha256
    ):
        raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING")
    verify_dpa_effective_now()
    expected_data_scope = [
        "redacted_client_state",
        "deployment_metadata",
        "redacted_request_class",
        "access_decision_evidence",
    ]
    if (
        dpa["permitted_data_scope"] != expected_data_scope
        or type(dpa["retention_days"]) is not int
        or dpa["retention_days"] != 30
        or dpa["deletion_mode"] != "protected_evidence_expiry"
        or dpa["retention_binding_sha256"]
        != _canonical_sha256(
            {
                "permitted_data_scope": expected_data_scope,
                "retention_days": 30,
                "deletion_mode": "protected_evidence_expiry",
                "purpose": "issue748_current_state_access_read_only",
            }
        )
    ):
        raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING")
    for field in (
        "operator_account_id", "operator_principal_id", "authorized_account_id",
        "authorized_principal_id", "provider",
    ):
        _string(resolver[field], "BLOCKED_RESOLVER_SCHEMA")
    _string(toolchain["read_driver_path"], "BLOCKED_TOOLCHAIN_SCHEMA")
    _hex(toolchain["read_driver_sha256"], "BLOCKED_TOOLCHAIN_SCHEMA")
    _string(approval["approval_mode"], "BLOCKED_APPROVAL_SCHEMA")
    _bool(approval["four_eyes_satisfied"], "BLOCKED_APPROVAL_SCHEMA")
    _bool(approval["external_two_person_required"], "BLOCKED_APPROVAL_SCHEMA")
    if approval["external_requirement_citation"] is not None and not isinstance(
        approval["external_requirement_citation"], str
    ):
        raise DiagnosticBlockedError("BLOCKED_APPROVAL_SCHEMA")
    initial_binding_keys = {
        "final_head_sha256", "final_tree_sha256", "contract_sha256",
        "resolver_sha256", "dpa_avv_binding_sha256",
    }
    if set(target_doc["bindings"]) != initial_binding_keys:
        raise DiagnosticBlockedError("BLOCKED_BINDING_SCHEMA")
    approval_sha256 = _canonical_sha256(approval)
    approval_core = {
        key: value for key, value in approval.items()
        if key != "dpa_avv_binding_sha256"
    }
    if dpa["approval_core_sha256"] != _canonical_sha256(approval_core):
        raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING")
    contract_sha256 = snapshots["contract.json"].sha256
    toolchain_sha256 = snapshots["toolchain.json"].sha256
    dpa_sha256 = snapshots["dpa-avv-receipt.json"].sha256
    run_nonce = _hex(approval["run_nonce_sha256"], "BLOCKED_APPROVAL_SCHEMA")
    if dpa["run_nonce_sha256"] != run_nonce:
        raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING")
    _hex(approval["head"], "BLOCKED_APPROVAL_SCHEMA", length=40)
    _hex(approval["tree"], "BLOCKED_APPROVAL_SCHEMA", length=40)
    for field in (
        "target_payload_sha256", "operator_account_binding_sha256",
        "operator_principal_binding_sha256", "dpa_avv_binding_sha256",
        "contract_sha256", "toolchain_sha256", "evidence_root_binding_sha256",
        "client_receipt_sha256", "observation_window_sha256",
        "request_correlation_binding_sha256",
    ):
        _hex(approval[field], "BLOCKED_APPROVAL_SCHEMA")
    account_binding = hmac.new(
        bytes.fromhex(run_nonce), str(resolver["operator_account_id"]).encode(), hashlib.sha256
    ).hexdigest()
    principal_binding = hmac.new(
        bytes.fromhex(run_nonce), str(resolver["operator_principal_id"]).encode(), hashlib.sha256
    ).hexdigest()
    actual_evidence_root_binding = hashlib.sha256(
        str(evidence_root.resolve()).encode("utf-8")
    ).hexdigest()
    expected_bindings = {
        "final_head_sha256": hashlib.sha256(contract["final_head"].encode()).hexdigest(),
        "final_tree_sha256": hashlib.sha256(contract["final_tree"].encode()).hexdigest(),
        "contract_sha256": contract_sha256,
        "resolver_sha256": snapshots["resolver.json"].sha256,
        "dpa_avv_binding_sha256": dpa_sha256,
    }
    if (
        approval["head"] != contract["final_head"]
        or approval["tree"] != contract["final_tree"]
        or approval["target_payload_sha256"] != target_payload_sha256
        or approval["operator_account_binding_sha256"] != account_binding
        or approval["operator_principal_binding_sha256"] != principal_binding
        or approval["dpa_avv_binding_sha256"] != dpa_sha256
        or approval["contract_sha256"] != contract_sha256
        or approval["toolchain_sha256"] != toolchain_sha256
        or approval["evidence_root_binding_sha256"] != actual_evidence_root_binding
        or approval["client_receipt_sha256"] != client_snapshot_sha256
        or approval["observation_window_sha256"]
        != _canonical_sha256(observation_window)
        or approval["request_correlation_binding_sha256"]
        != observation_window["request_correlation_binding_sha256"]
        or target_doc["bindings"] != expected_bindings
    ):
        raise DiagnosticBlockedError("BLOCKED_APPROVAL_BINDING")
    pre_gate_input = GateInput(
        issue=contract["issue"], pr=contract["pr"], base_pr=contract["base_pr"],
        base_merge_commit=contract["base_merge_commit"], base_tree=contract["base_tree"],
        head=contract["final_head"], tree=contract["final_tree"],
        head_descends_from_base=True,
        resolver_sha256=snapshots["resolver.json"].sha256,
        operator_account_id=resolver["operator_account_id"],
        operator_principal_id=resolver["operator_principal_id"],
        authorized_account_id=resolver["authorized_account_id"],
        authorized_principal_id=resolver["authorized_principal_id"],
        provider=resolver["provider"],
        tenant_binding_sha256=target_doc["tenant_binding_sha256"],
        account_permission_sha256=target_doc["account_permission_sha256"],
        target_binding_sha256=target_doc["target_binding_sha256"],
        target_payload_sha256=target_payload_sha256,
        dpa_avv_binding_sha256=dpa_sha256, contract_sha256=contract_sha256,
        toolchain_sha256=toolchain_sha256, approval_sha256=approval_sha256,
        run_nonce_sha256=run_nonce, approval_mode=approval["approval_mode"],
        four_eyes_satisfied=approval["four_eyes_satisfied"],
        external_two_person_required=approval["external_two_person_required"],
        external_requirement_citation=approval["external_requirement_citation"],
        required_checks_successful=True,
        required_checks_sha256=contract["required_checks_sha256"],
        worktree_clean=True, credential_write_guard_active=True,
        evidence_root_binding_sha256=actual_evidence_root_binding,
    )
    authorization = _authorize_protected_current_state_run(pre_gate_input)
    run_gate_receipt = consume_current_state_run_gate(
        authorization, evidence_root=evidence_root, backend=backend
    )
    transport = _AttestedProcessReadTransport(
        backend=backend,
        executable=Path(str(toolchain["read_driver_path"])),
        executable_sha256=str(toolchain["read_driver_sha256"]),
        input_root=input_root,
        repo_root=repo_root,
    )
    transport.bind_consumed_run(authorization, run_gate_receipt)
    verify_consumed_current_state_run_gate(
        authorization, run_gate_receipt,
        evidence_root=evidence_root, backend=backend,
    )
    verify_dpa_effective_now()
    local_gate = transport.read(operation="local_git_gate", target=target)["data"]
    verify_consumed_current_state_run_gate(
        authorization, run_gate_receipt,
        evidence_root=evidence_root, backend=backend,
    )
    verify_dpa_effective_now()
    github_gate = transport.read(operation="github_gate", target=target)["data"]
    _closed(
        local_gate,
        {"head", "tree", "head_descends_from_base", "worktree_clean"},
        "BLOCKED_GIT_GATE",
    )
    _closed(
        github_gate,
        {
            "repository", "pr", "base_pr", "base_merge_commit", "base_tree",
            "head", "required_checks_successful", "required_checks_sha256",
            "approval_sha256",
        },
        "BLOCKED_GITHUB_GATE",
    )
    _hex(local_gate["head"], "BLOCKED_GIT_GATE", length=40)
    _hex(local_gate["tree"], "BLOCKED_GIT_GATE", length=40)
    _bool(local_gate["head_descends_from_base"], "BLOCKED_GIT_GATE")
    _bool(local_gate["worktree_clean"], "BLOCKED_GIT_GATE")
    _string(github_gate["repository"], "BLOCKED_GITHUB_GATE")
    _integer(github_gate["pr"], 749, "BLOCKED_GITHUB_GATE")
    _integer(github_gate["base_pr"], 747, "BLOCKED_GITHUB_GATE")
    _hex(github_gate["base_merge_commit"], "BLOCKED_GITHUB_GATE", length=40)
    _hex(github_gate["base_tree"], "BLOCKED_GITHUB_GATE", length=40)
    _hex(github_gate["head"], "BLOCKED_GITHUB_GATE", length=40)
    _bool(github_gate["required_checks_successful"], "BLOCKED_GITHUB_GATE")
    for field in (
        "required_checks_sha256", "approval_sha256"
    ):
        _hex(github_gate[field], "BLOCKED_GITHUB_GATE")
    approval_sha256 = _canonical_sha256(approval)
    contract_sha256 = snapshots["contract.json"].sha256
    toolchain_sha256 = snapshots["toolchain.json"].sha256
    dpa_sha256 = snapshots["dpa-avv-receipt.json"].sha256
    expected_bindings = {
        "final_head_sha256": hashlib.sha256(local_gate["head"].encode()).hexdigest(),
        "final_tree_sha256": hashlib.sha256(local_gate["tree"].encode()).hexdigest(),
        "contract_sha256": contract_sha256,
        "resolver_sha256": snapshots["resolver.json"].sha256,
        "dpa_avv_binding_sha256": dpa_sha256,
    }
    run_nonce = _hex(approval["run_nonce_sha256"], "BLOCKED_APPROVAL_SCHEMA")
    if dpa["run_nonce_sha256"] != run_nonce:
        raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING")
    _hex(approval["head"], "BLOCKED_APPROVAL_SCHEMA", length=40)
    _hex(approval["tree"], "BLOCKED_APPROVAL_SCHEMA", length=40)
    for field in (
        "target_payload_sha256", "operator_account_binding_sha256",
        "operator_principal_binding_sha256", "dpa_avv_binding_sha256",
        "contract_sha256", "toolchain_sha256",
        "evidence_root_binding_sha256",
    ):
        _hex(approval[field], "BLOCKED_APPROVAL_SCHEMA")
    account_binding = hmac.new(
        bytes.fromhex(run_nonce), str(resolver["operator_account_id"]).encode(), hashlib.sha256
    ).hexdigest()
    principal_binding = hmac.new(
        bytes.fromhex(run_nonce), str(resolver["operator_principal_id"]).encode(), hashlib.sha256
    ).hexdigest()
    actual_evidence_root_binding = hashlib.sha256(
        str(evidence_root.resolve()).encode("utf-8")
    ).hexdigest()
    if (
        github_gate["repository"] != "notariat8/NaC"
        or github_gate["pr"] != 749
        or github_gate["base_pr"] != 747
        or github_gate["head"] != local_gate["head"]
        or contract["final_head"] != local_gate["head"]
        or contract["final_tree"] != local_gate["tree"]
        or contract["base_merge_commit"] != github_gate["base_merge_commit"]
        or contract["base_tree"] != github_gate["base_tree"]
        or approval_sha256 != github_gate["approval_sha256"]
        or contract["required_checks_sha256"] != github_gate["required_checks_sha256"]
        or approval["head"] != local_gate["head"]
        or approval["tree"] != local_gate["tree"]
        or approval["target_payload_sha256"] != target_payload_sha256
        or approval["operator_account_binding_sha256"] != account_binding
        or approval["operator_principal_binding_sha256"] != principal_binding
        or approval["dpa_avv_binding_sha256"] != dpa_sha256
        or approval["contract_sha256"] != contract_sha256
        or approval["toolchain_sha256"] != toolchain_sha256
        or approval["evidence_root_binding_sha256"] != actual_evidence_root_binding
        or target_doc["bindings"] != expected_bindings
    ):
        raise DiagnosticBlockedError("BLOCKED_FINAL_GATE_BINDING")
    value = GateInput(
        issue=contract["issue"], pr=contract["pr"], base_pr=contract["base_pr"],
        base_merge_commit=github_gate["base_merge_commit"],
        base_tree=github_gate["base_tree"], head=local_gate["head"],
        tree=local_gate["tree"],
        head_descends_from_base=local_gate["head_descends_from_base"],
        resolver_sha256=snapshots["resolver.json"].sha256,
        operator_account_id=resolver["operator_account_id"],
        operator_principal_id=resolver["operator_principal_id"],
        authorized_account_id=resolver["authorized_account_id"],
        authorized_principal_id=resolver["authorized_principal_id"],
        provider=resolver["provider"],
        tenant_binding_sha256=target_doc["tenant_binding_sha256"],
        account_permission_sha256=target_doc["account_permission_sha256"],
        target_binding_sha256=target_doc["target_binding_sha256"],
        target_payload_sha256=target_payload_sha256,
        dpa_avv_binding_sha256=dpa_sha256,
        contract_sha256=contract_sha256,
        toolchain_sha256=toolchain_sha256,
        approval_sha256=approval_sha256,
        run_nonce_sha256=approval["run_nonce_sha256"],
        approval_mode=approval["approval_mode"],
        four_eyes_satisfied=approval["four_eyes_satisfied"],
        external_two_person_required=approval["external_two_person_required"],
        external_requirement_citation=approval["external_requirement_citation"],
        required_checks_successful=github_gate["required_checks_successful"],
        required_checks_sha256=github_gate["required_checks_sha256"],
        worktree_clean=local_gate["worktree_clean"],
        credential_write_guard_active=True,
        evidence_root_binding_sha256=actual_evidence_root_binding,
    )
    verified_authorization = _authorize_protected_current_state_run(value)
    if verified_authorization.authorization_sha256 != authorization.authorization_sha256:
        raise DiagnosticBlockedError("BLOCKED_PRE_GATE_AUTHORIZATION_DRIFT")
    transport.authorize_provider_reads(authorization, run_gate_receipt)

    def revalidate() -> None:
        verify_dpa_effective_now()
        verify_consumed_current_state_run_gate(
            authorization, run_gate_receipt,
            evidence_root=evidence_root, backend=backend,
        )
        for name, expected in snapshots.items():
            actual = backend.inspect_private_path(
                input_root / name, purpose=f"issue748-revalidate-{name}"
            )
            if actual != expected:
                raise DiagnosticBlockedError("BLOCKED_PROTECTED_INPUT_DRIFT")
        if backend.inspect_bound_input_path(
            policy_path, purpose="issue748-revalidate-dpa-policy"
        ) != policy_snapshot:
            raise DiagnosticBlockedError("BLOCKED_DPA_AVV_BINDING")
        verify_consumed_current_state_run_gate(
            authorization, run_gate_receipt,
            evidence_root=evidence_root, backend=backend,
        )
        verify_dpa_effective_now()
        if transport.read(operation="local_git_gate", target=target)["data"] != local_gate:
            raise DiagnosticBlockedError("BLOCKED_GIT_GATE_DRIFT")
        verify_consumed_current_state_run_gate(
            authorization, run_gate_receipt,
            evidence_root=evidence_root, backend=backend,
        )
        verify_dpa_effective_now()
        if transport.read(operation="github_gate", target=target)["data"] != github_gate:
            raise DiagnosticBlockedError("BLOCKED_GITHUB_GATE_DRIFT")
        verify_consumed_current_state_run_gate(
            authorization, run_gate_receipt,
            evidence_root=evidence_root, backend=backend
        )
        verify_dpa_effective_now()

    key = bytes.fromhex(authorization.authorization_sha256)
    bindings = dict(target_doc["bindings"])
    bindings["account_run_binding"] = hmac.new(
        key, authorization.account_id.encode(), hashlib.sha256
    ).hexdigest()
    bindings["principal_run_binding"] = hmac.new(
        key, authorization.principal_id.encode(), hashlib.sha256
    ).hexdigest()
    verify_consumed_current_state_run_gate(
        authorization, run_gate_receipt,
        evidence_root=evidence_root, backend=backend,
    )
    ports = build_current_state_access_ports(
        transport=transport,
        target=target,
        authorization=authorization,
        evidence_verifier=revalidate,
    )
    classification, first, second = run_double_snapshot_diagnostic(
        authorization=authorization,
        ports=ports,
        bindings=bindings,
        observation_window=observation_window,
        target_projection=target,
        protected_client_fact={
            "ui_state": client_receipt["ui_state"],
            "spfx_subject_available": client_receipt["spfx_subject_available"],
        },
    )
    session = backend.open_secure_directory(
        evidence_root,
        create=False,
        require_current_owner=True,
        require_restrictive_dacl=True,
    )
    try:
        payload = json.dumps(
            {
                "schema_version": "nac.m365-current-state-access-diagnostic-result/v1",
                "classification": classification,
                "authorization_sha256": authorization.authorization_sha256,
                "run_gate_marker_sha256": run_gate_receipt.marker_sha256,
                "first_projection_sha256": first.decision_projection_sha256,
                "second_projection_sha256": second.decision_projection_sha256,
                "first_provider_receipt_sha256": first.acquisition_envelope.provider_read_receipt_sha256,
                "second_provider_receipt_sha256": second.acquisition_envelope.provider_read_receipt_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        result_snapshot = session.create_exclusive(
            f"issue748-{authorization.authorization_sha256}.result.json", payload
        )
        if getattr(result_snapshot, "sha256", "") != hashlib.sha256(payload).hexdigest():
            raise DiagnosticBlockedError("BLOCKED_RESULT_EVIDENCE_DURABILITY")
    finally:
        session.close()
    return classification, first, second


__all__ = [
    "PROTECTED_INPUT_FILES",
    "preflight_current_state_access_diagnostic",
    "run_current_state_access_diagnostic_from_protected_inputs",
    "run_double_snapshot_diagnostic",
]
