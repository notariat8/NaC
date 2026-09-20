from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol

from .current_state_access_gate import CurrentStateRunAuthorization, RunGateReceipt
from .current_state_access_ports import PortReadResult
from .current_state_access_ports import CurrentStateAccessPorts


_HEX64 = re.compile(r"[0-9a-f]{64}")


class CurrentStateReadTransport(Protocol):
    def read(
        self, *, operation: str, target: Mapping[str, str]
    ) -> Mapping[str, Any]: ...


class _AttestedProcessReadTransport:
    """Narrow no-retry bridge to a pre-attested external read-only driver."""

    _OPERATIONS = frozenset(
        {
            "local_git_gate", "github_gate", "client_observation_receipt",
            "teams_tab_metadata", "sharepoint_app_catalog",
            "entra_api_permission", "azure_function_metadata",
            "azure_function_request_log", "sharepoint_access_decision",
        }
    )

    def __init__(
        self,
        *,
        backend: Any,
        executable: Path,
        executable_sha256: str,
        input_root: Path,
        repo_root: Path,
    ) -> None:
        if (
            not executable.is_absolute()
            or not input_root.is_absolute()
            or not repo_root.is_absolute()
            or not _HEX64.fullmatch(executable_sha256)
        ):
            raise RuntimeError("CURRENT_STATE_READ_DRIVER_BINDING_BLOCKED")
        measured = backend.inspect_private_path(
            executable, purpose="issue748-read-driver"
        )
        if measured.sha256 != executable_sha256:
            raise RuntimeError("CURRENT_STATE_READ_DRIVER_ATTESTATION_BLOCKED")
        self._backend = backend
        self._executable = executable
        self._executable_sha256 = executable_sha256
        self._input_root = input_root
        self._repo_root = repo_root
        self._consumed_binding: tuple[str, str] | None = None
        self._provider_context_sha256: str | None = None

    def bind_consumed_run(
        self,
        authorization: CurrentStateRunAuthorization,
        receipt: RunGateReceipt,
    ) -> None:
        if receipt.authorization_sha256 != authorization.authorization_sha256:
            raise RuntimeError("CURRENT_STATE_RUN_GATE_BINDING_BLOCKED")
        if self._consumed_binding is not None:
            raise RuntimeError("CURRENT_STATE_RUN_GATE_ALREADY_BOUND")
        self._consumed_binding = (
            authorization.authorization_sha256,
            receipt.marker_sha256,
        )

    def authorize_provider_reads(
        self,
        authorization: CurrentStateRunAuthorization,
        receipt: RunGateReceipt,
    ) -> None:
        if self._consumed_binding != (
            authorization.authorization_sha256, receipt.marker_sha256
        ):
            raise RuntimeError("CURRENT_STATE_RUN_GATE_BINDING_BLOCKED")
        self._provider_context_sha256 = hashlib.sha256(
            json.dumps(
                {
                    "authorization_sha256": authorization.authorization_sha256,
                    "run_gate_marker_sha256": receipt.marker_sha256,
                    "provider": authorization.provider,
                    "tenant_binding_sha256": authorization.tenant_binding_sha256,
                    "account_permission_sha256": authorization.account_permission_sha256,
                    "target_binding_sha256": authorization.target_binding_sha256,
                    "target_payload_sha256": authorization.target_payload_sha256,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    def read(self, *, operation: str, target: Mapping[str, str]) -> Mapping[str, Any]:
        if operation not in self._OPERATIONS:
            raise RuntimeError("CURRENT_STATE_READ_OPERATION_BLOCKED")
        if self._consumed_binding is None:
            raise RuntimeError("CURRENT_STATE_RUN_GATE_REQUIRED")
        provider_operation = operation not in {"local_git_gate", "github_gate"}
        if provider_operation and self._provider_context_sha256 is None:
            raise RuntimeError("CURRENT_STATE_RUN_GATE_REQUIRED")
        from .activation_security_backend import ProcessSpec

        target_sha256 = hashlib.sha256(
            json.dumps(dict(target), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        environment = {
            key: value
            for key in ("SystemRoot", "TEMP")
            if (value := __import__("os").environ.get(key))
        }
        result = self._backend.launch_attested_process(
            ProcessSpec(
                executable=self._executable,
                arguments=(
                    "--issue748-read", operation,
                    "--input-root", str(self._input_root),
                    "--target-sha256", target_sha256,
                    *( 
                        ("--authorization-context-sha256", self._provider_context_sha256)
                        if provider_operation else ()
                    ),
                ),
                cwd=self._repo_root,
                environment=environment,
                executable_sha256=self._executable_sha256,
                timeout_seconds=60,
                maximum_output_bytes=128 * 1024,
                allowed_exit_codes=(0,),
                credential_write_guard=True,
            )
        )
        if getattr(result, "credential_write_guard_applied", False) is not True:
            raise RuntimeError("CURRENT_STATE_CREDENTIAL_WRITE_GUARD_NOT_ATTESTED")
        try:
            payload = json.loads(result.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("CURRENT_STATE_READ_DRIVER_OUTPUT_BLOCKED") from exc
        expected_keys = (
            {"data", "receipt_sha256", "authorization_context_sha256"}
            if provider_operation else {"data", "receipt_sha256"}
        )
        if not isinstance(payload, dict) or set(payload) != expected_keys:
            raise RuntimeError("CURRENT_STATE_READ_DRIVER_OUTPUT_BLOCKED")
        if provider_operation and payload["authorization_context_sha256"] != self._provider_context_sha256:
            raise RuntimeError("CURRENT_STATE_READ_CONTEXT_ATTESTATION_BLOCKED")
        payload.pop("authorization_context_sha256", None)
        return payload


@dataclass(frozen=True)
class TransportPolicy:
    read_only: bool = True
    follow_redirects: bool = False
    automatic_retries: int = 0
    credential_write_guard_active: bool = True

    def verify(self) -> None:
        if (
            self.read_only is not True
            or self.follow_redirects is not False
            or self.automatic_retries != 0
            or self.credential_write_guard_active is not True
        ):
            raise RuntimeError("CURRENT_STATE_READ_TRANSPORT_POLICY_BLOCKED")


class _BoundReadAdapter:
    operation = ""
    allowed_fields: frozenset[str] = frozenset()

    def __init__(
        self,
        *,
        transport: CurrentStateReadTransport,
        target: Mapping[str, str],
        account_id: str,
        principal_id: str,
        target_binding_sha256: str,
        evidence_verifier: Callable[[], None],
        policy: TransportPolicy,
    ) -> None:
        policy.verify()
        if not self.operation or not self.allowed_fields:
            raise ValueError("adapter contract incomplete")
        self._transport = transport
        self._target = MappingProxyType(dict(target))
        self._account_id = account_id
        self._principal_id = principal_id
        self._target_binding_sha256 = target_binding_sha256
        self._target_payload_sha256 = hashlib.sha256(
            json.dumps(
                dict(self._target), sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        if not callable(evidence_verifier):
            raise RuntimeError("CURRENT_STATE_EVIDENCE_VERIFIER_REQUIRED")
        self._evidence_verifier = evidence_verifier
        self._policy = policy

    def read(self, authorization: CurrentStateRunAuthorization) -> PortReadResult:
        self._policy.verify()
        self._evidence_verifier()
        authorization.verify_for_read(
            account_id=self._account_id,
            principal_id=self._principal_id,
            target_binding_sha256=self._target_binding_sha256,
            target_payload_sha256=self._target_payload_sha256,
            evidence_binding_sha256=authorization.authorization_sha256,
        )
        result = self._transport.read(operation=self.operation, target=self._target)
        if set(result) != {"data", "receipt_sha256"}:
            raise RuntimeError("CURRENT_STATE_READ_RESPONSE_SCHEMA_BLOCKED")
        data = result["data"]
        receipt = result["receipt_sha256"]
        if (
            not isinstance(data, Mapping)
            or frozenset(data) != self.allowed_fields
            or not isinstance(receipt, str)
            or not _HEX64.fullmatch(receipt)
        ):
            raise RuntimeError("CURRENT_STATE_READ_RESPONSE_REDACTION_BLOCKED")
        bound_receipt = hashlib.sha256(
            json.dumps(
                {
                    "operation": self.operation,
                    "target_payload_sha256": self._target_payload_sha256,
                    "authorization_sha256": authorization.authorization_sha256,
                    "result": dict(data),
                    "transport_receipt_sha256": receipt,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return PortReadResult(
            MappingProxyType(dict(data)), bound_receipt, self.operation
        )


class ClientObservationReceiptAdapter(_BoundReadAdapter):
    operation = "client_observation_receipt"
    allowed_fields = frozenset(
        {"ui_state", "spfx_subject_available", "client_receipt_sha256"}
    )


class TeamsTabMetadataReadAdapter(_BoundReadAdapter):
    operation = "teams_tab_metadata"
    allowed_fields = frozenset({"contract_matches", "version_binding"})


class SharePointAppCatalogReadAdapter(_BoundReadAdapter):
    operation = "sharepoint_app_catalog"
    allowed_fields = frozenset(
        {"package_version", "package_digest", "api_permission_match"}
    )


class EntraApiPermissionReadAdapter(_BoundReadAdapter):
    operation = "entra_api_permission"
    allowed_fields = frozenset(
        {"tenant_match", "audience_match", "scope_match", "preauthorization_match"}
    )


class AzureFunctionMetadataReadAdapter(_BoundReadAdapter):
    operation = "azure_function_metadata"
    allowed_fields = frozenset({"deployment_class", "configuration_digest"})


class AzureFunctionRequestLogReadAdapter(_BoundReadAdapter):
    operation = "azure_function_request_log"
    allowed_fields = frozenset(
        {"request_observed", "http_class", "request_correlation_binding_sha256"}
    )


class SharePointAccessDecisionReadAdapter(_BoundReadAdapter):
    operation = "sharepoint_access_decision"
    allowed_fields = frozenset({"evidence_matches"})


def build_current_state_access_ports(
    *,
    transport: CurrentStateReadTransport,
    target: Mapping[str, str],
    authorization: CurrentStateRunAuthorization,
    evidence_verifier: Callable[[], None],
) -> CurrentStateAccessPorts:
    common = {
        "transport": transport,
        "target": target,
        "account_id": authorization.account_id,
        "principal_id": authorization.principal_id,
        "target_binding_sha256": authorization.target_binding_sha256,
        "evidence_verifier": evidence_verifier,
        "policy": TransportPolicy(),
    }
    return CurrentStateAccessPorts(
        ClientObservationReceiptAdapter(**common),
        TeamsTabMetadataReadAdapter(**common),
        SharePointAppCatalogReadAdapter(**common),
        EntraApiPermissionReadAdapter(**common),
        AzureFunctionMetadataReadAdapter(**common),
        AzureFunctionRequestLogReadAdapter(**common),
        SharePointAccessDecisionReadAdapter(**common),
    )


__all__ = [
    "AzureFunctionMetadataReadAdapter",
    "AzureFunctionRequestLogReadAdapter",
    "build_current_state_access_ports",
    "ClientObservationReceiptAdapter",
    "CurrentStateReadTransport",
    "EntraApiPermissionReadAdapter",
    "SharePointAccessDecisionReadAdapter",
    "SharePointAppCatalogReadAdapter",
    "TeamsTabMetadataReadAdapter",
    "TransportPolicy",
]
