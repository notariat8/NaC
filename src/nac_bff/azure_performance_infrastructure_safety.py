from __future__ import annotations

from collections.abc import Mapping
import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import wraps
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
from typing import Any
from uuid import UUID

from .azure_activation_attestations import (
    AZURE_CLI_EXECUTION_PATH,
    TOOLCHAIN_ATTESTATION_FIELDS,
    calculate_toolchain_attestations_sha256,
)
from .azure_live_commands import calculate_azure_cli_toolchain_sha256
from .azure_live_commands import _prepare_bound_runtime


CONTAINER_NAME = "nac-bff-performance-leases"
ALLOWED_DATA_ACTIONS = frozenset(
    {
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
    }
)

PROVENANCE_READBACK_SCHEMA = "nac.azure-provenance-readback/v1"
EFFECTIVE_RBAC_READBACK_SCHEMA = "nac.azure-effective-rbac-readback/v1"
STORAGE_API_VERSION = "2023-05-01"
AUTHORIZATION_API_VERSION = "2022-04-01"
MICROSOFT_GRAPH_API_VERSION = "v1.0"
DEPLOYMENT_API_VERSION = "2022-09-01"
MANAGEMENT_GROUP_API_VERSION = "2021-04-01"
INFRASTRUCTURE_SAFETY_EVIDENCE_SCHEMA = (
    "nac.azure-bff-performance-infrastructure-safety-evidence/v3"
)
READBACK_SESSION_SCHEMA = "nac.azure-bff-performance-readback-session/v1"
SEALED_AZURE_READ_SCHEMA = "nac.azure-sealed-readback-command/v3"
MANDATORY_COORDINATION_TAGS = {
    "blobPrecreation": "owner-gated-before-runtime",
    "dataClassification": "synthetic-only",
    "environment": "test",
    "managedBy": "bicep",
    "storageBoundary": "dedicated-from-bff-and-worm",
    "workload": "nac-bff-performance-coordination",
}
_INFRASTRUCTURE_SAFETY_EVIDENCE_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "infrastructure_safety_policy_sha256",
        "target_binding_sha256",
        "tenant_id",
        "subscription_id",
        "resource_group_name",
        "location",
        "tags_sha256",
        "effective_tags_sha256",
        "allowed_client_ip_address_sha256",
        "toolchain_attestations_sha256",
        "readback_session_sha256",
        "readback_nonce_sha256",
        "owner_binding_sha256",
        "execution_attestation_sha256",
        "verified_at_utc",
        "coordination_storage_account_name",
        "coordination_storage_account_resource_id",
        "bff_storage_account_resource_id",
        "worm_storage_account_resource_id",
        "lease_container_resource_id",
        "lease_blob_path",
        "provisioner_principal_id",
        "role_definition_id",
        "role_assignment_id",
        "condition",
        "condition_version",
        "data_actions",
        "effective_assignment_count",
        "effective_principal_count",
        "attested_ancestor_scope_count",
        "tenant_root_management_group_scope",
        "deployment_receipt_sha256",
        "storage_configuration_sha256",
        "readback_observation_sha256",
        "readback_transcript",
        "network_accessed",
        "infrastructure_safety_evidence_sha256",
    }
)

_STORAGE_ACCOUNT_NAME_RE = re.compile(r"^[a-z0-9]{3,24}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OBSERVED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_NONCE_RE = re.compile(r"^[0-9a-f]{64}$")
_LOCATION_RE = re.compile(r"^[a-z0-9-]{2,40}$")
_PREDEPLOY_MAX_AGE = timedelta(minutes=30)
_POSTDEPLOY_MAX_AGE = timedelta(minutes=5)
_MAX_FUTURE_SKEW = timedelta(seconds=30)
_MAX_SESSION_AGE = timedelta(minutes=30)
_STORAGE_ACCOUNT_ID_RE = re.compile(
    r"^/subscriptions/(?P<subscription>[^/]+)/resourceGroups/(?P<resource_group>[^/]+)"
    r"/providers/Microsoft\.Storage/storageAccounts/(?P<name>[^/]+)$",
    re.IGNORECASE,
)
_MANAGEMENT_GROUP_SCOPE_RE = re.compile(
    r"^/providers/Microsoft\.Management/managementGroups/(?P<name>[^/]+)$",
    re.IGNORECASE,
)
_DEPLOYMENT_ID_RE = re.compile(
    r"^/subscriptions/(?P<subscription>[^/]+)/resourceGroups/"
    r"(?P<resource_group>[^/]+)/providers/Microsoft\.Resources/deployments/[^/]+$",
    re.IGNORECASE,
)

_SEALED_OPERATION_KEYS = frozenset(
    {
        "executable_path_sha256",
        "executable_sha256",
        "argv",
        "argv_sha256",
        "environment",
        "environment_sha256",
        "api_version",
        "resource_id",
        "raw_response_base64",
        "response_sha256",
    }
)
_SEALED_EXECUTION_KEYS = frozenset({"schema_version", "operations"})
_READBACK_TRANSCRIPT_KEYS = frozenset(
    {
        "bff_storage",
        "worm_storage",
        "coordination_name",
        "deployment_receipt",
        "coordination_storage",
        "blob_service",
        "lease_container",
        "role_definition",
        "role_assignment",
        "subscription_ancestry",
        "effective_rbac",
    }
)
_SEALED_READ_SPECS = {
    "bff-storage-account-resource-id": (
        STORAGE_API_VERSION,
        "azure-resource-manager/storage-accounts-get",
    ),
    "worm-storage-account-resource-id": (
        STORAGE_API_VERSION,
        "azure-resource-manager/storage-accounts-get",
    ),
    "coordination-storage-account-configuration": (
        STORAGE_API_VERSION,
        "azure-resource-manager/storage-accounts-get",
    ),
    "coordination-blob-service-configuration": (
        STORAGE_API_VERSION,
        "azure-resource-manager/blob-services-get",
    ),
    "coordination-lease-container-configuration": (
        STORAGE_API_VERSION,
        "azure-resource-manager/blob-containers-get",
    ),
    "coordination-role-definition": (
        AUTHORIZATION_API_VERSION,
        "azure-resource-manager/role-definitions-get",
    ),
    "coordination-role-assignment": (
        AUTHORIZATION_API_VERSION,
        "azure-resource-manager/role-assignments-get",
    ),
    "coordination-deployment-receipt": (
        DEPLOYMENT_API_VERSION,
        "azure-resource-manager/deployments-get",
    ),
}


@dataclass(frozen=True, slots=True)
class AzurePerformanceInfrastructureReadbackSession:
    """Opaque owner-bound capability for one fresh readback sequence."""

    created_at_utc: str
    owner_binding_sha256: str
    toolchain_attestations_sha256: str
    nonce: str
    nonce_sha256: str
    executable_path_sha256: str
    executable_sha256: str
    argv_sha256: str
    session_sha256: str
    execution_attestation_sha256: str


@dataclass(frozen=True, slots=True, init=False)
class AzurePerformanceInfrastructureReadbackCapability:
    """Adapter-issued authority to verify one measured readback session."""

    session: AzurePerformanceInfrastructureReadbackSession
    executable_path_sha256: str
    executable_sha256: str
    azure_cli_toolchain_sha256: str
    _authenticator: bytes

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("readback capabilities are issued by the sealed adapter")

    def __copy__(self) -> None:
        raise TypeError("readback capabilities cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> None:
        raise TypeError("readback capabilities cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("readback capabilities cannot be serialized")


class AzurePerformanceInfrastructureReadbackResult(Mapping[str, Any]):
    """Immutable adapter result carrying non-serializable verifier authority."""

    __slots__ = ("_canonical_evidence", "_capability", "_authenticator")

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("readback results are issued by the sealed adapter")

    def _as_dict(self) -> dict[str, Any]:
        if not _authenticate_readback_result(self, self._capability):
            _fail("SEALED_READBACK_CAPABILITY_INVALID")
        value = json.loads(self._canonical_evidence)
        if not isinstance(value, dict):
            _fail("SEALED_READBACK_CAPABILITY_INVALID")
        return value

    def __getitem__(self, key: str) -> Any:
        return self._as_dict()[key]

    def __iter__(self):
        return iter(self._as_dict())

    def __len__(self) -> int:
        return len(self._as_dict())

    def __deepcopy__(self, memo: dict[int, Any]) -> dict[str, Any]:
        del memo
        return self._as_dict()

    def __copy__(self) -> dict[str, Any]:
        return self._as_dict()

    def __reduce__(self) -> None:
        raise TypeError("readback results cannot be serialized")


class AzurePerformanceInfrastructureSafetyVerification(dict[str, Any]):
    """Immutable SAFE result that cannot be recreated from an evidence mapping."""

    __slots__ = (
        "_canonical_evidence",
        "_readback_capability",
        "_authenticator",
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("safety verifications are issued by the verifier")

    def _assert_valid_capability(self) -> None:
        if not _authenticate_safety_verification(self):
            _fail("INFRASTRUCTURE_SAFETY_CAPABILITY_INVALID")

    def __setitem__(self, _key: str, _value: Any) -> None:
        raise TypeError("safety verification is immutable")

    def __delitem__(self, _key: str) -> None:
        raise TypeError("safety verification is immutable")

    def clear(self) -> None:
        raise TypeError("safety verification is immutable")

    def pop(self, _key: str, _default: Any = None) -> Any:
        raise TypeError("safety verification is immutable")

    def popitem(self) -> tuple[str, Any]:
        raise TypeError("safety verification is immutable")

    def setdefault(self, _key: str, _default: Any = None) -> Any:
        raise TypeError("safety verification is immutable")

    def update(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("safety verification is immutable")

    def __ior__(self, _other: object):
        raise TypeError("safety verification is immutable")

    def __deepcopy__(self, memo: dict[int, Any]) -> dict[str, Any]:
        del memo
        return json.loads(_canonical_json_bytes(self))

    def __copy__(self) -> dict[str, Any]:
        return json.loads(_canonical_json_bytes(self))

    def __reduce__(self) -> None:
        raise TypeError("safety verifications cannot be serialized")


@dataclass(frozen=True, slots=True)
class _SealedAzureExecution:
    executable_path_sha256: str
    executable_sha256: str
    argv: tuple[str, ...]
    argv_sha256: str
    environment: Mapping[str, str]
    environment_sha256: str
    api_version: str
    resource_id: str
    raw_response_base64: str
    response_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "executable_path_sha256": self.executable_path_sha256,
            "executable_sha256": self.executable_sha256,
            "argv": list(self.argv),
            "argv_sha256": self.argv_sha256,
            "environment": dict(self.environment),
            "environment_sha256": self.environment_sha256,
            "api_version": self.api_version,
            "resource_id": self.resource_id,
            "raw_response_base64": self.raw_response_base64,
            "response_sha256": self.response_sha256,
        }


class _ProcessReadbackAuthority:
    """Immutable process-local MAC verifier; issuance also requires a hidden token."""

    __slots__ = ("__issuer", "__secret")

    def __init__(self, issuer: object) -> None:
        object.__setattr__(
            self,
            "_ProcessReadbackAuthority__secret",
            secrets.token_bytes(32),
        )
        object.__setattr__(self, "_ProcessReadbackAuthority__issuer", issuer)

    def __setattr__(self, _name: str, _value: object) -> None:
        raise TypeError("process readback authority is immutable")

    def _mac(self, domain: bytes, *values: bytes) -> bytes:
        framed = bytearray(domain)
        for value in values:
            framed.extend(len(value).to_bytes(8, "big"))
            framed.extend(value)
        return hmac.digest(self.__secret, framed, "sha256")

    @staticmethod
    def _object_identity_bytes(value: object) -> bytes:
        return id(value).to_bytes((sys.maxsize.bit_length() + 7) // 8, "big")

    @staticmethod
    def _session_bytes(
        session: AzurePerformanceInfrastructureReadbackSession,
    ) -> bytes:
        return _canonical_json_bytes(
            {
                "argv_sha256": session.argv_sha256,
                "created_at_utc": session.created_at_utc,
                "executable_path_sha256": session.executable_path_sha256,
                "executable_sha256": session.executable_sha256,
                "execution_attestation_sha256": session.execution_attestation_sha256,
                "nonce": session.nonce,
                "nonce_sha256": session.nonce_sha256,
                "owner_binding_sha256": session.owner_binding_sha256,
                "session_sha256": session.session_sha256,
                "toolchain_attestations_sha256": session.toolchain_attestations_sha256,
            }
        )

    def _capability_bytes(
        self,
        capability: AzurePerformanceInfrastructureReadbackCapability,
    ) -> bytes:
        return _canonical_json_bytes(
            {
                "azure_cli_toolchain_sha256": capability.azure_cli_toolchain_sha256,
                "executable_path_sha256": capability.executable_path_sha256,
                "executable_sha256": capability.executable_sha256,
                "session": json.loads(self._session_bytes(capability.session)),
            }
        )

    def _issue_capability(
        self,
        issuer: object,
        session: AzurePerformanceInfrastructureReadbackSession,
        executable_path_sha256: str,
        executable_sha256: str,
        azure_cli_toolchain_sha256: str,
    ) -> AzurePerformanceInfrastructureReadbackCapability:
        if issuer is not self.__issuer:
            raise TypeError("readback capability issuer")
        instance = object.__new__(AzurePerformanceInfrastructureReadbackCapability)
        object.__setattr__(instance, "session", session)
        object.__setattr__(instance, "executable_path_sha256", executable_path_sha256)
        object.__setattr__(instance, "executable_sha256", executable_sha256)
        object.__setattr__(
            instance, "azure_cli_toolchain_sha256", azure_cli_toolchain_sha256
        )
        object.__setattr__(
            instance,
            "_authenticator",
            self._mac(
                b"nac/readback-capability/v1",
                self._object_identity_bytes(instance),
                self._capability_bytes(instance),
            ),
        )
        return instance

    def valid_capability(self, value: Any) -> bool:
        if type(value) is not AzurePerformanceInfrastructureReadbackCapability:
            return False
        try:
            supplied = value._authenticator
            expected = self._mac(
                b"nac/readback-capability/v1",
                self._object_identity_bytes(value),
                self._capability_bytes(value),
            )
        except (AttributeError, TypeError, ValueError):
            return False
        return isinstance(supplied, bytes) and hmac.compare_digest(supplied, expected)

    def _issue_result(
        self,
        issuer: object,
        value: Mapping[str, Any],
        capability: AzurePerformanceInfrastructureReadbackCapability,
    ) -> AzurePerformanceInfrastructureReadbackResult:
        if issuer is not self.__issuer or not self.valid_capability(capability):
            raise TypeError("readback result issuer")
        instance = object.__new__(AzurePerformanceInfrastructureReadbackResult)
        canonical = _canonical_json_bytes(value)
        object.__setattr__(instance, "_canonical_evidence", canonical)
        object.__setattr__(instance, "_capability", capability)
        object.__setattr__(
            instance,
            "_authenticator",
            self._mac(
                b"nac/readback-result/v1",
                self._object_identity_bytes(instance),
                self._capability_bytes(capability),
                capability._authenticator,
                canonical,
            ),
        )
        return instance

    def valid_result(
        self,
        value: Any,
        capability: AzurePerformanceInfrastructureReadbackCapability,
    ) -> bool:
        if type(value) is not AzurePerformanceInfrastructureReadbackResult:
            return False
        try:
            if value._capability is not capability:
                return False
            supplied = value._authenticator
            canonical = value._canonical_evidence
            expected = self._mac(
                b"nac/readback-result/v1",
                self._object_identity_bytes(value),
                self._capability_bytes(capability),
                capability._authenticator,
                canonical,
            )
        except (AttributeError, TypeError, ValueError):
            return False
        return (
            self.valid_capability(capability)
            and isinstance(canonical, bytes)
            and isinstance(supplied, bytes)
            and hmac.compare_digest(supplied, expected)
        )

    def _issue_verification(
        self,
        issuer: object,
        value: Mapping[str, Any],
        capability: AzurePerformanceInfrastructureReadbackCapability,
    ) -> AzurePerformanceInfrastructureSafetyVerification:
        if issuer is not self.__issuer or not self.valid_capability(capability):
            raise TypeError("safety verification issuer")
        instance = dict.__new__(AzurePerformanceInfrastructureSafetyVerification)
        dict.__init__(instance, json.loads(_canonical_json_bytes(value)))
        canonical = _canonical_json_bytes(instance)
        instance._canonical_evidence = canonical
        instance._readback_capability = capability
        instance._authenticator = self._mac(
            b"nac/safety-verification/v1",
            self._object_identity_bytes(instance),
            self._capability_bytes(capability),
            capability._authenticator,
            canonical,
        )
        return instance

    def valid_verification(self, value: Any) -> bool:
        if type(value) is not AzurePerformanceInfrastructureSafetyVerification:
            return False
        try:
            capability = value._readback_capability
            supplied = value._authenticator
            canonical = _canonical_json_bytes(value)
            expected = self._mac(
                b"nac/safety-verification/v1",
                self._object_identity_bytes(value),
                self._capability_bytes(capability),
                capability._authenticator,
                canonical,
            )
        except (AttributeError, TypeError, ValueError):
            return False
        return (
            self.valid_capability(capability)
            and isinstance(supplied, bytes)
            and isinstance(value._canonical_evidence, bytes)
            and hmac.compare_digest(canonical, value._canonical_evidence)
            and hmac.compare_digest(supplied, expected)
        )


def _create_process_authority():
    # Python cannot protect against arbitrary code execution in this trusted process.
    # The closure removes ordinary import-and-mutate access to the issuance token.
    issuer = object()
    authority = _ProcessReadbackAuthority(issuer)

    def seal_adapter(adapter_type):
        original_init = adapter_type.__init__

        @wraps(original_init)
        def sealed_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self._verification_capability = authority._issue_capability(
                issuer,
                self._session,
                self._executable_path_sha256,
                self._executable_sha256,
                self._azure_cli_toolchain_sha256,
            )

        def issue_result(self, value):
            return authority._issue_result(
                issuer, value, self._verification_capability
            )

        adapter_type.__init__ = sealed_init
        adapter_type._issue_result = issue_result
        return adapter_type

    def seal_verifier(verifier):
        @wraps(verifier)
        def sealed_verifier(*args, **kwargs):
            evidence, capability = verifier(*args, **kwargs)
            return authority._issue_verification(issuer, evidence, capability)

        return sealed_verifier

    def authenticate_capability(value):
        return authority.valid_capability(value)

    def authenticate_result(value, capability):
        return authority.valid_result(value, capability)

    def authenticate_verification(value):
        return authority.valid_verification(value)

    return (
        seal_adapter,
        seal_verifier,
        authenticate_capability,
        authenticate_result,
        authenticate_verification,
    )


(
    _seal_readback_adapter,
    _seal_safety_verifier,
    _authenticate_readback_capability,
    _authenticate_readback_result,
    _authenticate_safety_verification,
) = _create_process_authority()
del _create_process_authority
del _ProcessReadbackAuthority


_READBACK_REPLAY_LEDGER_DIRECTORY = (
    Path.home() / ".nac" / "state" / "azure-performance-readback-replay-v1"
)


class AzurePerformanceInfrastructureSafetyError(ValueError):
    """Fail-closed error raised for unsafe coordination infrastructure."""


@_seal_readback_adapter
class AzurePerformanceInfrastructureReadbackAdapter:
    """Execute only fixed Azure reads and seal their exact raw responses."""

    def __init__(
        self,
        session: AzurePerformanceInfrastructureReadbackSession,
        *,
        toolchain_attestations: Mapping[str, str],
    ) -> None:
        if not isinstance(session, AzurePerformanceInfrastructureReadbackSession):
            _fail("READBACK_SESSION_INVALID")
        _validate_readback_session_integrity(session, check_execution_identity=True)
        if not isinstance(toolchain_attestations, Mapping) or set(
            toolchain_attestations
        ) != set(TOOLCHAIN_ATTESTATION_FIELDS):
            _fail("TOOLCHAIN_ATTESTATIONS_INVALID")
        manifest = {
            name: toolchain_attestations[name]
            for name in TOOLCHAIN_ATTESTATION_FIELDS
        }
        if any(
            not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None
            for digest in manifest.values()
        ):
            _fail("TOOLCHAIN_ATTESTATIONS_INVALID")
        if (
            calculate_toolchain_attestations_sha256(manifest)
            != session.toolchain_attestations_sha256
        ):
            _fail("TOOLCHAIN_ATTESTATIONS_MISMATCH")
        azure_cli_toolchain_sha256 = manifest["azure_cli_toolchain_sha256"]
        executable = AZURE_CLI_EXECUTION_PATH.resolve(strict=True)
        measured_toolchain = calculate_azure_cli_toolchain_sha256(executable)
        if measured_toolchain != azure_cli_toolchain_sha256:
            _fail("AZURE_CLI_TOOLCHAIN_MISMATCH")
        self._session = session
        self._executable = executable
        self._azure_cli_toolchain_sha256 = azure_cli_toolchain_sha256
        self._executable_path_sha256 = hashlib.sha256(
            os.fsencode(str(executable))
        ).hexdigest()
        self._executable_sha256 = hashlib.sha256(executable.read_bytes()).hexdigest()
        azure_config_dir = Path(
            os.environ.get("AZURE_CONFIG_DIR", str(Path.home() / ".azure"))
        ).expanduser().resolve()
        self._environment = {
            "AZURE_CONFIG_DIR": str(azure_config_dir),
            "AZURE_CORE_COLLECT_TELEMETRY": "no",
            "HOME": str(Path.home().resolve()),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        }
        self._environment_sha256 = hashlib.sha256(
            _canonical_json_bytes(self._environment)
        ).hexdigest()

    @property
    def session(self) -> AzurePerformanceInfrastructureReadbackSession:
        return self._session

    @property
    def verification_capability(
        self,
    ) -> AzurePerformanceInfrastructureReadbackCapability:
        return self._verification_capability

    def _issue_result(
        self, value: Mapping[str, Any]
    ) -> AzurePerformanceInfrastructureReadbackResult:
        raise AssertionError("sealed adapter authority was not installed")

    def execute_read(
        self,
        *,
        observation_kind: str,
        resource_id: str,
    ) -> AzurePerformanceInfrastructureReadbackResult:
        """Execute one allowlisted ARM GET and return its sealed envelope."""

        spec = _SEALED_READ_SPECS.get(observation_kind)
        if spec is None:
            _fail("SEALED_AZURE_READ_COMMAND_NOT_ALLOWED")
        api_version, source = spec
        normalized_resource = _require_arm_id(
            resource_id, "SEALED_AZURE_READ_RESOURCE_INVALID"
        )
        url = (
            f"https://management.azure.com{normalized_resource}"
            f"?api-version={api_version}"
        )
        argv = (
            str(self._executable),
            "rest",
            "--method",
            "get",
            "--url",
            url,
            "--only-show-errors",
            "--output",
            "json",
        )
        response_bytes = self._run(argv)
        response = _decode_azure_json_response(response_bytes)
        payload: Mapping[str, Any]
        if observation_kind in {
            "bff-storage-account-resource-id",
            "worm-storage-account-resource-id",
        }:
            payload = {"resource_id": response.get("id")}
        elif observation_kind in {
            "coordination-role-definition",
            "coordination-role-assignment",
        }:
            payload = {"resource": response}
        elif observation_kind == "coordination-storage-account-configuration":
            payload = _storage_configuration_payload(response)
        elif observation_kind == "coordination-blob-service-configuration":
            payload = _blob_service_configuration_payload(response)
        elif observation_kind == "coordination-lease-container-configuration":
            payload = _lease_container_configuration_payload(response)
        elif observation_kind == "coordination-deployment-receipt":
            payload = _deployment_receipt_payload(response)
        else:
            payload = response
        envelope = {
            "schema_version": PROVENANCE_READBACK_SCHEMA,
            "observation_kind": observation_kind,
            "api_version": api_version,
            "observed_at_utc": _format_utc(_trusted_now()),
            "observation_source": source,
            "payload": payload,
        }
        return self._issue_result(
            _seal_executed_observation(
                envelope,
                session=self._session,
                executable_path_sha256=self._executable_path_sha256,
                executable_sha256=self._executable_sha256,
                environment_sha256=self._environment_sha256,
                environment=self._environment,
                argv=argv,
                api_version=api_version,
                resource_id=normalized_resource,
                response_bytes=response_bytes,
            )
        )

    def check_storage_account_name_availability(
        self,
        *,
        subscription_id: str,
        storage_account_name: str,
    ) -> AzurePerformanceInfrastructureReadbackResult:
        """Execute the one fixed predeployment storage-name check."""

        subscription = _canonical_uuid(
            subscription_id, "SUBSCRIPTION_ID_INVALID"
        )
        if _STORAGE_ACCOUNT_NAME_RE.fullmatch(storage_account_name) is None:
            _fail("COORDINATION_STORAGE_NAME_UNAVAILABLE")
        resource_id = (
            f"/subscriptions/{subscription}/providers/Microsoft.Storage/"
            "checkNameAvailability"
        )
        body = _canonical_json_bytes(
            {"name": storage_account_name, "type": "Microsoft.Storage/storageAccounts"}
        ).decode("ascii")
        url = (
            f"https://management.azure.com{resource_id}"
            f"?api-version={STORAGE_API_VERSION}"
        )
        argv = (
            str(self._executable),
            "rest",
            "--method",
            "post",
            "--url",
            url,
            "--body",
            body,
            "--only-show-errors",
            "--output",
            "json",
        )
        response_bytes = self._run(argv)
        response = _decode_azure_json_response(response_bytes)
        envelope = {
            "schema_version": PROVENANCE_READBACK_SCHEMA,
            "observation_kind": "coordination-storage-name-availability",
            "api_version": STORAGE_API_VERSION,
            "observed_at_utc": _format_utc(_trusted_now()),
            "observation_source": (
                "azure-resource-manager/storage-accounts-check-name-availability"
            ),
            "payload": {
                "name": storage_account_name,
                "name_available": response.get("nameAvailable"),
            },
        }
        return self._issue_result(
            _seal_executed_observation(
                envelope,
                session=self._session,
                executable_path_sha256=self._executable_path_sha256,
                executable_sha256=self._executable_sha256,
                environment_sha256=self._environment_sha256,
                environment=self._environment,
                argv=argv,
                api_version=STORAGE_API_VERSION,
                resource_id=resource_id,
                response_bytes=response_bytes,
            )
        )

    def read_management_group_ancestry(
        self,
        *,
        tenant_id: str,
        subscription_id: str,
    ) -> AzurePerformanceInfrastructureReadbackResult:
        """Read the recursive tenant-root hierarchy and seal the exact chain."""

        tenant = _canonical_uuid(tenant_id, "TENANT_ID_INVALID")
        subscription = _canonical_uuid(
            subscription_id, "SUBSCRIPTION_ID_INVALID"
        )
        resource_id = (
            "/providers/Microsoft.Management/managementGroups/" + tenant
        )
        url = (
            f"https://management.azure.com{resource_id}"
            f"?api-version={MANAGEMENT_GROUP_API_VERSION}"
            "&$expand=children&$recurse=true"
        )
        argv = (
            str(self._executable),
            "rest",
            "--method",
            "get",
            "--url",
            url,
            "--only-show-errors",
            "--output",
            "json",
        )
        response_bytes = self._run(argv)
        response = _decode_azure_json_response(response_bytes)
        payload = _management_group_ancestry_payload(
            response,
            tenant_id=tenant,
            subscription_id=subscription,
        )
        envelope = {
            "schema_version": PROVENANCE_READBACK_SCHEMA,
            "observation_kind": "subscription-management-group-ancestry",
            "api_version": MANAGEMENT_GROUP_API_VERSION,
            "observed_at_utc": _format_utc(_trusted_now()),
            "observation_source": (
                "azure-resource-manager/management-groups-subscriptions-get"
            ),
            "payload": payload,
        }
        return self._issue_result(
            _seal_executed_observation(
                envelope,
                session=self._session,
                executable_path_sha256=self._executable_path_sha256,
                executable_sha256=self._executable_sha256,
                environment_sha256=self._environment_sha256,
                environment=self._environment,
                argv=argv,
                api_version=MANAGEMENT_GROUP_API_VERSION,
                resource_id=resource_id,
                response_bytes=response_bytes,
            )
        )

    def read_effective_rbac(
        self,
        *,
        principal_id: str,
        target_resource_id: str,
        ancestor_scopes: list[str],
    ) -> AzurePerformanceInfrastructureReadbackResult:
        """Read transitive groups and all at-scope ARM assignments."""

        principal = _canonical_uuid(
            principal_id, "PROVISIONER_PRINCIPAL_INVALID"
        )
        target = _require_arm_id(
            target_resource_id, "EFFECTIVE_RBAC_READBACK_INVALID"
        )
        if (
            not isinstance(ancestor_scopes, list)
            or not ancestor_scopes
            or ancestor_scopes[-1].casefold() != target.casefold()
            or any(
                not isinstance(scope, str) or not scope.startswith("/")
                for scope in ancestor_scopes
            )
        ):
            _fail("EFFECTIVE_RBAC_ANCESTRY_INVALID")
        operations: list[dict[str, Any]] = []
        graph_resource = (
            f"/servicePrincipals/{principal}/transitiveMemberOf/"
            "microsoft.graph.group?$select=id"
        )
        graph_url = f"https://graph.microsoft.com/v1.0{graph_resource}"
        graph_response = self._execute_json_operation(
            graph_url,
            api_version=MICROSOFT_GRAPH_API_VERSION,
            resource_id=graph_resource,
            operations=operations,
        )
        if set(graph_response) - {"value", "@odata.context"}:
            _fail("EFFECTIVE_RBAC_READBACK_INCOMPLETE")
        group_items = graph_response.get("value")
        if not isinstance(group_items, list):
            _fail("EFFECTIVE_PRINCIPAL_EXPANSION_INVALID")
        groups = sorted(
            _canonical_uuid(item.get("id"), "EFFECTIVE_PRINCIPAL_EXPANSION_INVALID")
            for item in group_items
            if isinstance(item, Mapping)
        )
        if len(groups) != len(group_items) or len(groups) != len(set(groups)):
            _fail("EFFECTIVE_PRINCIPAL_EXPANSION_INVALID")

        relevant = {principal, *groups}
        assignments: list[dict[str, Any]] = []
        pending_assignments: list[tuple[dict[str, Any], str, str]] = []
        role_definitions: dict[str, dict[str, Any]] = {}
        for scope in ancestor_scopes:
            prefix = "" if scope == "/" else scope
            collection = (
                f"{prefix}/providers/Microsoft.Authorization/roleAssignments"
            )
            url = (
                f"https://management.azure.com{collection}"
                f"?api-version={AUTHORIZATION_API_VERSION}&$filter=atScope()"
            )
            response = self._execute_json_operation(
                url,
                api_version=AUTHORIZATION_API_VERSION,
                resource_id=collection,
                operations=operations,
            )
            if set(response) - {"value"} or not isinstance(response.get("value"), list):
                _fail("EFFECTIVE_RBAC_READBACK_INCOMPLETE")
            for item in response["value"]:
                properties = _properties(item, "EFFECTIVE_ASSIGNMENTS_INVALID")
                candidate_principal = _canonical_uuid(
                    properties.get("principalId"), "EFFECTIVE_ASSIGNMENTS_INVALID"
                )
                if candidate_principal not in relevant:
                    continue
                role_id = _require_arm_id(
                    properties.get("roleDefinitionId"),
                    "EFFECTIVE_ASSIGNMENT_DATA_ACTIONS_UNRESOLVED",
                )
                pending_assignments.append((dict(item), scope, role_id))
        for expanded, scope, role_id in pending_assignments:
            if role_id.casefold() not in role_definitions:
                role_url = (
                    f"https://management.azure.com{role_id}"
                    f"?api-version={AUTHORIZATION_API_VERSION}"
                )
                role_definitions[role_id.casefold()] = self._execute_json_operation(
                    role_url,
                    api_version=AUTHORIZATION_API_VERSION,
                    resource_id=role_id,
                    operations=operations,
                )
            expanded["scope"] = scope
            expanded["roleDefinition"] = role_definitions[role_id.casefold()]
            assignments.append(expanded)
        payload = {
            "target_resource_id": target,
            "principal_id": principal,
            "transitive_group_principal_ids": groups,
            "ancestor_scopes": list(ancestor_scopes),
            "effective_role_assignments": assignments,
            "completeness_attestation": {
                "root_ancestry_complete": True,
                "management_group_ancestry_complete": True,
                "transitive_group_membership_complete": True,
                "role_assignments_complete": True,
                "role_definitions_expanded": True,
            },
        }
        envelope = {
            "schema_version": EFFECTIVE_RBAC_READBACK_SCHEMA,
            "observation_kind": "effective-rbac-abac",
            "api_versions": {
                "azure_authorization": AUTHORIZATION_API_VERSION,
                "microsoft_graph": MICROSOFT_GRAPH_API_VERSION,
            },
            "observed_at_utc": _format_utc(_trusted_now()),
            "observation_source": (
                "azure-resource-manager-and-microsoft-graph-effective-access-readback"
            ),
            "payload": payload,
        }
        return self._issue_result(
            _seal_operation_transcript(
                envelope, session=self._session, operations=operations
            )
        )

    def _execute_json_operation(
        self,
        url: str,
        *,
        api_version: str,
        resource_id: str,
        operations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        argv = (
            str(self._executable), "rest", "--method", "get", "--url", url,
            "--only-show-errors", "--output", "json",
        )
        response_bytes = self._run(argv)
        response = _decode_azure_json_response(response_bytes)
        operations.append(
            _sealed_operation(
                executable_path_sha256=self._executable_path_sha256,
                executable_sha256=self._executable_sha256,
                environment=self._environment,
                environment_sha256=self._environment_sha256,
                argv=argv,
                api_version=api_version,
                resource_id=resource_id,
                response_bytes=response_bytes,
            )
        )
        return response

    def _run(self, argv: tuple[str, ...]) -> bytes:
        # The fresh path measurement authorizes immutable runtime construction;
        # subprocess receives only the resulting sealed descriptors.
        self._assert_executable_unchanged()
        runtime = _prepare_bound_runtime(
            self._executable,
            expected_sha256=self._azure_cli_toolchain_sha256,
            cloud_selection_sha256=None,
        )
        if runtime is None:
            _fail("AZURE_CLI_RUNTIME_BINDING_FAILED")
        try:
            with runtime:
                completed = subprocess.run(
                    runtime.command(list(argv[1:])),
                    check=False,
                    capture_output=True,
                    env=dict(self._environment),
                    stdin=subprocess.DEVNULL,
                    timeout=30,
                    shell=False,
                    pass_fds=runtime.pass_fds,
                )
        except (OSError, subprocess.SubprocessError):
            _fail("SEALED_AZURE_READ_EXECUTION_FAILED")
        if completed.returncode != 0 or not isinstance(completed.stdout, bytes):
            _fail("SEALED_AZURE_READ_EXECUTION_FAILED")
        return completed.stdout

    def _assert_executable_unchanged(self) -> None:
        if (
            calculate_azure_cli_toolchain_sha256(self._executable)
            != self._azure_cli_toolchain_sha256
            or hashlib.sha256(self._executable.read_bytes()).hexdigest()
            != self._executable_sha256
        ):
            _fail("AZURE_CLI_TOOLCHAIN_CHANGED_DURING_READBACK")


del _seal_readback_adapter


def begin_azure_performance_infrastructure_readback_session(
    *,
    owner_approval_body_sha256: str,
    toolchain_attestations_sha256: str,
) -> AzurePerformanceInfrastructureReadbackSession:
    """Create one internally timed, non-replayable readback capability."""

    _require_named_sha256(
        owner_approval_body_sha256, "OWNER_BINDING_INVALID"
    )
    _require_named_sha256(
        toolchain_attestations_sha256, "TOOLCHAIN_ATTESTATIONS_INVALID"
    )
    created_at_utc = _format_utc(_trusted_now())
    nonce = secrets.token_hex(32)
    nonce_sha256 = hashlib.sha256(nonce.encode("ascii")).hexdigest()
    execution = _capture_execution_identity()
    session_payload = {
        "schema_version": READBACK_SESSION_SCHEMA,
        "created_at_utc": created_at_utc,
        "owner_binding_sha256": owner_approval_body_sha256,
        "toolchain_attestations_sha256": toolchain_attestations_sha256,
        "nonce_sha256": nonce_sha256,
        **execution,
    }
    session_sha256 = _sha256_json(session_payload)
    attestation = {
        **session_payload,
        "readback_session_sha256": session_sha256,
    }
    execution_attestation_sha256 = _sha256_json(attestation)
    session = AzurePerformanceInfrastructureReadbackSession(
        created_at_utc=created_at_utc,
        owner_binding_sha256=owner_approval_body_sha256,
        toolchain_attestations_sha256=toolchain_attestations_sha256,
        nonce=nonce,
        nonce_sha256=nonce_sha256,
        executable_path_sha256=execution["executable_path_sha256"],
        executable_sha256=execution["executable_sha256"],
        argv_sha256=execution["argv_sha256"],
        session_sha256=session_sha256,
        execution_attestation_sha256=execution_attestation_sha256,
    )
    return session


def readback_session_attestation(
    session: AzurePerformanceInfrastructureReadbackSession,
) -> dict[str, str]:
    """Return the exact public attestation required on every session envelope."""

    if not isinstance(session, AzurePerformanceInfrastructureReadbackSession):
        _fail("READBACK_SESSION_INVALID")
    return {
        "schema_version": READBACK_SESSION_SCHEMA,
        "created_at_utc": session.created_at_utc,
        "owner_binding_sha256": session.owner_binding_sha256,
        "toolchain_attestations_sha256": session.toolchain_attestations_sha256,
        "nonce_sha256": session.nonce_sha256,
        "executable_path_sha256": session.executable_path_sha256,
        "executable_sha256": session.executable_sha256,
        "argv_sha256": session.argv_sha256,
        "readback_session_sha256": session.session_sha256,
    }


def effective_coordination_tags(
    tags: Mapping[str, str], target_binding_sha256: str
) -> dict[str, str]:
    """Return the canonical effective tag set emitted by the Bicep template."""

    supplied = _canonical_tags(tags)
    _require_sha256(target_binding_sha256)
    return {
        key: value
        for key, value in sorted(
            {
                **supplied,
                **MANDATORY_COORDINATION_TAGS,
                "targetBindingSha256": target_binding_sha256,
            }.items()
        )
    }


def canonical_observation_sha256(value: Mapping[str, Any]) -> str:
    """Digest a canonical observation envelope, excluding its digest field."""

    if not isinstance(value, Mapping):
        raise TypeError("observation envelope must be a mapping")
    payload = {key: item for key, item in value.items() if key != "observation_sha256"}
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _seal_executed_observation(
    value: Mapping[str, Any],
    *,
    session: AzurePerformanceInfrastructureReadbackSession,
    executable_path_sha256: str,
    executable_sha256: str,
    environment_sha256: str,
    environment: Mapping[str, str] | None = None,
    argv: tuple[str, ...],
    api_version: str,
    resource_id: str,
    response_bytes: bytes,
) -> dict[str, Any]:
    """Seal one already executed fixed command; not a public envelope helper."""

    if not isinstance(session, AzurePerformanceInfrastructureReadbackSession):
        _fail("READBACK_SESSION_INVALID")
    _require_named_sha256(executable_path_sha256, "SEALED_EXECUTION_INVALID")
    _require_named_sha256(executable_sha256, "SEALED_EXECUTION_INVALID")
    _require_named_sha256(environment_sha256, "SEALED_EXECUTION_INVALID")
    if (
        not isinstance(argv, tuple)
        or not argv
        or any(not isinstance(item, str) or not item for item in argv)
        or not isinstance(api_version, str)
        or not api_version
        or not isinstance(resource_id, str)
        or not resource_id.startswith("/")
        or not isinstance(response_bytes, bytes)
    ):
        _fail("SEALED_EXECUTION_INVALID")
    response_sha256 = hashlib.sha256(response_bytes).hexdigest()
    execution = _SealedAzureExecution(
        executable_path_sha256=executable_path_sha256,
        executable_sha256=executable_sha256,
        argv=argv,
        argv_sha256=hashlib.sha256(_canonical_json_bytes(list(argv))).hexdigest(),
        environment=dict(environment or {}),
        environment_sha256=environment_sha256,
        api_version=api_version,
        resource_id=resource_id,
        raw_response_base64=base64.b64encode(response_bytes).decode("ascii"),
        response_sha256=response_sha256,
    )
    sealed_execution = {
        "schema_version": SEALED_AZURE_READ_SCHEMA,
        "operations": [execution.as_dict()],
    }
    envelope = {
        **dict(value),
        "sealed_execution": sealed_execution,
        "response_sha256": response_sha256,
        "toolchain_attestations_sha256": session.toolchain_attestations_sha256,
        "readback_session_sha256": session.session_sha256,
        "readback_nonce": session.nonce,
        "execution_attestation": readback_session_attestation(session),
    }
    command_payload = {
        "schema_version": SEALED_AZURE_READ_SCHEMA,
        "observation_kind": envelope.get("observation_kind"),
        "readback_session_sha256": session.session_sha256,
        "nonce_sha256": session.nonce_sha256,
        "execution_attestation_sha256": session.execution_attestation_sha256,
        "sealed_execution": sealed_execution,
    }
    envelope["observation_command_sha256"] = _sha256_json(command_payload)
    envelope["observation_sha256"] = canonical_observation_sha256(envelope)
    return envelope


def _sealed_operation(
    *,
    executable_path_sha256: str,
    executable_sha256: str,
    environment: Mapping[str, str],
    environment_sha256: str,
    argv: tuple[str, ...],
    api_version: str,
    resource_id: str,
    response_bytes: bytes,
) -> dict[str, Any]:
    response_sha256 = hashlib.sha256(response_bytes).hexdigest()
    return _SealedAzureExecution(
        executable_path_sha256=executable_path_sha256,
        executable_sha256=executable_sha256,
        argv=argv,
        argv_sha256=hashlib.sha256(_canonical_json_bytes(list(argv))).hexdigest(),
        environment=dict(environment),
        environment_sha256=environment_sha256,
        api_version=api_version,
        resource_id=resource_id,
        raw_response_base64=base64.b64encode(response_bytes).decode("ascii"),
        response_sha256=response_sha256,
    ).as_dict()


def _seal_operation_transcript(
    value: Mapping[str, Any],
    *,
    session: AzurePerformanceInfrastructureReadbackSession,
    operations: list[dict[str, Any]],
) -> dict[str, Any]:
    if not operations:
        _fail("SEALED_EXECUTION_INVALID")
    sealed_execution = {
        "schema_version": SEALED_AZURE_READ_SCHEMA,
        "operations": operations,
    }
    response_sha256 = hashlib.sha256(
        _canonical_json_bytes([item["response_sha256"] for item in operations])
    ).hexdigest()
    envelope = {
        **dict(value),
        "sealed_execution": sealed_execution,
        "response_sha256": response_sha256,
        "toolchain_attestations_sha256": session.toolchain_attestations_sha256,
        "readback_session_sha256": session.session_sha256,
        "readback_nonce": session.nonce,
        "execution_attestation": readback_session_attestation(session),
    }
    envelope["observation_command_sha256"] = _sha256_json(
        {
            "schema_version": SEALED_AZURE_READ_SCHEMA,
            "observation_kind": envelope.get("observation_kind"),
            "readback_session_sha256": session.session_sha256,
            "nonce_sha256": session.nonce_sha256,
            "execution_attestation_sha256": session.execution_attestation_sha256,
            "sealed_execution": sealed_execution,
        }
    )
    envelope["observation_sha256"] = canonical_observation_sha256(envelope)
    return envelope


def _decode_azure_json_response(value: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("SEALED_AZURE_READ_RESPONSE_INVALID")
    if not isinstance(decoded, Mapping):
        _fail("SEALED_AZURE_READ_RESPONSE_INVALID")
    return dict(decoded)


def _storage_configuration_payload(response: Mapping[str, Any]) -> dict[str, Any]:
    properties = response.get("properties")
    sku = response.get("sku")
    tags = response.get("tags")
    if not all(isinstance(item, Mapping) for item in (properties, sku, tags)):
        _fail("SEALED_AZURE_READ_RESPONSE_INVALID")
    network = properties.get("networkAcls")
    if not isinstance(network, Mapping):
        _fail("SEALED_AZURE_READ_RESPONSE_INVALID")
    return {
        "id": response.get("id"),
        "name": response.get("name"),
        "type": response.get("type"),
        "location": response.get("location"),
        "kind": response.get("kind"),
        "sku": {"name": sku.get("name"), "tier": sku.get("tier")},
        "tags": dict(tags),
        "properties": {
            name: properties.get(name)
            for name in (
                "accessTier",
                "allowBlobPublicAccess",
                "allowCrossTenantReplication",
                "allowSharedKeyAccess",
                "defaultToOAuthAuthentication",
                "isHnsEnabled",
                "minimumTlsVersion",
            )
        }
        | {
            "networkAcls": {
                "bypass": network.get("bypass"),
                "defaultAction": network.get("defaultAction"),
                "ipRules": network.get("ipRules"),
                "resourceAccessRules": network.get("resourceAccessRules"),
                "virtualNetworkRules": network.get("virtualNetworkRules"),
            },
            "publicNetworkAccess": properties.get("publicNetworkAccess"),
            "supportsHttpsTrafficOnly": properties.get("supportsHttpsTrafficOnly"),
        },
    }


def _blob_service_configuration_payload(
    response: Mapping[str, Any],
) -> dict[str, Any]:
    properties = response.get("properties")
    if not isinstance(properties, Mapping):
        _fail("SEALED_AZURE_READ_RESPONSE_INVALID")
    delete_retention = properties.get("deleteRetentionPolicy")
    container_delete_retention = properties.get("containerDeleteRetentionPolicy")
    if not isinstance(delete_retention, Mapping) or not isinstance(
        container_delete_retention, Mapping
    ):
        _fail("SEALED_AZURE_READ_RESPONSE_INVALID")
    return {
        "id": response.get("id"),
        "name": response.get("name"),
        "type": response.get("type"),
        "properties": {
            "isVersioningEnabled": properties.get("isVersioningEnabled"),
            "deleteRetentionPolicy": {
                "enabled": delete_retention.get("enabled")
            },
            "containerDeleteRetentionPolicy": {
                "enabled": container_delete_retention.get("enabled")
            },
        },
    }


def _lease_container_configuration_payload(
    response: Mapping[str, Any],
) -> dict[str, Any]:
    properties = response.get("properties")
    if not isinstance(properties, Mapping):
        _fail("SEALED_AZURE_READ_RESPONSE_INVALID")
    metadata = properties.get("metadata")
    if not isinstance(metadata, Mapping):
        _fail("SEALED_AZURE_READ_RESPONSE_INVALID")
    return {
        "id": response.get("id"),
        "name": response.get("name"),
        "type": response.get("type"),
        "properties": {
            "publicAccess": properties.get("publicAccess"),
            "metadata": dict(metadata),
        },
    }


def _deployment_receipt_payload(response: Mapping[str, Any]) -> dict[str, Any]:
    properties = response.get("properties")
    if not isinstance(properties, Mapping):
        _fail("SEALED_AZURE_READ_RESPONSE_INVALID")
    parameters = properties.get("parameters")
    if not isinstance(parameters, Mapping):
        _fail("SEALED_AZURE_READ_RESPONSE_INVALID")

    def parameter(name: str) -> Any:
        item = parameters.get(name)
        if not isinstance(item, Mapping) or set(item) != {"value"}:
            _fail("SEALED_AZURE_READ_RESPONSE_INVALID")
        return item["value"]

    completed = properties.get("timestamp")
    started = properties.get("startTime")
    if started is None:
        started = completed
    tags = effective_coordination_tags(
        parameter("tags"), str(parameter("targetBindingSha256"))
    )
    coordination_id = (
        f"/subscriptions/{parameter('subscriptionId')}/resourceGroups/"
        f"{parameter('resourceGroupName')}/providers/Microsoft.Storage/"
        f"storageAccounts/{parameter('storageAccountName')}"
    )
    storage = _expected_storage_configuration(
        coordination=_storage_account_id(coordination_id),
        location=str(parameter("location")),
        effective_tags=tags,
        allowed_client_ip_address=str(parameter("allowedClientIpAddress")),
    )
    return {
        "deployment_id": response.get("id"),
        "provisioning_state": properties.get("provisioningState"),
        "started_at_utc": started,
        "completed_at_utc": completed,
        "tenant_id": parameter("tenantId"),
        "coordination_storage_account_resource_id": coordination_id,
        "target_binding_sha256": parameter("targetBindingSha256"),
        "provisioner_principal_id": parameter("provisionerPrincipalId"),
        "effective_tags_sha256": _sha256_json(tags),
        "storage_configuration_sha256": _sha256_json(storage),
    }


def _management_group_ancestry_payload(
    response: Mapping[str, Any],
    *,
    tenant_id: str,
    subscription_id: str,
) -> dict[str, Any]:
    root_scope = (
        f"/providers/Microsoft.Management/managementGroups/{tenant_id}"
    )
    if not isinstance(response, Mapping) or str(response.get("id", "")).casefold() != (
        root_scope.casefold()
    ):
        _fail("SUBSCRIPTION_ANCESTRY_READBACK_INVALID")
    subscription_scope = f"/subscriptions/{subscription_id}"
    matches: list[list[str]] = []

    def children(node: Mapping[str, Any]) -> list[Any]:
        direct = node.get("children")
        properties = node.get("properties")
        nested = properties.get("children") if isinstance(properties, Mapping) else None
        selected = direct if isinstance(direct, list) else nested
        if not isinstance(selected, list):
            return []
        return selected

    def walk(node: Mapping[str, Any], chain: list[str]) -> None:
        for child in children(node):
            if not isinstance(child, Mapping) or not isinstance(child.get("id"), str):
                _fail("SUBSCRIPTION_ANCESTRY_READBACK_INVALID")
            child_id = child["id"]
            if child_id.casefold() == subscription_scope.casefold():
                matches.append(chain)
                continue
            if _MANAGEMENT_GROUP_SCOPE_RE.fullmatch(child_id) is None:
                continue
            if any(child_id.casefold() == item.casefold() for item in chain):
                _fail("SUBSCRIPTION_ANCESTRY_READBACK_INVALID")
            walk(child, [*chain, child_id])

    walk(response, [root_scope])
    if len(matches) != 1:
        _fail("SUBSCRIPTION_ANCESTRY_READBACK_INVALID")
    chain = matches[0]
    relationships = [
        {
            "scope": scope,
            "parent_scope": "/" if index == 0 else chain[index - 1],
        }
        for index, scope in enumerate(chain)
    ]
    return {
        "tenant_id": tenant_id,
        "subscription_id": subscription_id,
        "tenant_root_scope": "/",
        "tenant_root_management_group_scope": root_scope,
        "management_group_relationships": relationships,
        "subscription_attachment": {
            "subscription_scope": subscription_scope,
            "parent_management_group_scope": chain[-1],
        },
        "ancestry_complete": True,
    }


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError):
        _fail("CANONICAL_JSON_INVALID")


def infrastructure_safety_policy_sha256() -> str:
    """Bind the exact readback-provenance and effective-RBAC safety policy."""

    policy = {
        "schema_version": "nac.azure-bff-performance-infrastructure-safety/v8",
        "container_name": CONTAINER_NAME,
        "data_actions": sorted(ALLOWED_DATA_ACTIONS),
        "predeployment_coordination_name_available_required": True,
        "postdeployment_coordination_resource_readback_required": True,
        "exact_full_storage_and_network_readback_required": True,
        "exact_blob_service_resource_readback_required": True,
        "blob_versioning_enabled": False,
        "blob_delete_retention_enabled": False,
        "container_delete_retention_enabled": False,
        "exact_lease_container_resource_readback_required": True,
        "lease_container_public_access": "None",
        "exact_lease_container_metadata_required": True,
        "effective_tags_must_match_bicep": True,
        "authoritative_bff_storage_account_resource_id_readback_required": True,
        "authoritative_worm_storage_account_resource_id_readback_required": True,
        "canonical_provenance_readback_schema": PROVENANCE_READBACK_SCHEMA,
        "effective_rbac_readback_schema": EFFECTIVE_RBAC_READBACK_SCHEMA,
        "effective_role_assignments": "complete-for-expanded-principals-and-ancestry",
        "authoritative_subscription_management_group_ancestry_required": True,
        "effective_assignment_ancestor_scopes": [
            "tenant_root",
            "management_group_chain",
            "subscription",
            "resource_group",
            "storage_account",
            "blob_service",
            "container",
        ],
        "transitive_entra_group_principals_required": True,
        "completeness_attestation_required": True,
        "broader_effective_data_assignment_allowed": False,
        "effective_control_plane_assignment_allowed": False,
        "freshness": {
            "predeployment_max_age_seconds": int(_PREDEPLOY_MAX_AGE.total_seconds()),
            "postdeployment_max_age_seconds": int(_POSTDEPLOY_MAX_AGE.total_seconds()),
            "maximum_future_skew_seconds": int(_MAX_FUTURE_SKEW.total_seconds()),
        },
        "toolchain_and_session_binding_required": True,
        "internally_generated_trusted_time_required": True,
        "internally_generated_nonce_binding_required": True,
        "actual_executable_and_argv_attestation_required": True,
        "fixed_azure_read_command_allowlist_required": True,
        "fixed_microsoft_graph_read_command_allowlist_required": True,
        "sanitized_subprocess_environment_required": True,
        "python_user_site_and_unsafe_path_disabled": True,
        "subprocess_environment_digest_required": True,
        "toolchain_remeasured_immediately_before_subprocess": True,
        "immutable_fd_backed_azure_cli_runtime_required": True,
        "adapter_issued_readback_result_capability_required": True,
        "approved_executable_digest_bound_to_every_operation": True,
        "sealed_api_and_resource_binding_required": True,
        "raw_azure_response_sha256_required": True,
        "self_contained_raw_response_transcript_required": True,
        "public_raw_transcript_revalidation_required": True,
        "serialized_evidence_reauthorization_allowed": False,
        "live_safety_verification_capability_required": True,
        "private_durable_nonce_replay_ledger_required": True,
        "process_ephemeral_keyed_mac_authority_required": True,
        "capability_result_and_verification_mac_binding_required": True,
        "constant_time_mac_verification_required": True,
        "process_restart_requires_fresh_reattestation": True,
        "module_level_issuance_registry_allowed": False,
        "trusted_process_arbitrary_code_execution_out_of_scope": True,
        "public_envelope_fabrication_rejected": True,
        "arm_principal_ids_canonicalized_case_insensitively": True,
        "management_group_parent_child_chain_required": True,
        "subscription_attachment_required": True,
        "deployment_receipt_and_timestamp_continuity_required": True,
        "expected_effective_assignment_count": 1,
        "condition_version": "2.0",
    }
    encoded = json.dumps(
        policy,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def exact_lease_blob_condition(target_binding_sha256: str) -> str:
    """Return the one accepted Azure ABAC condition for the lease blob."""

    _require_sha256(target_binding_sha256)
    read = "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
    add = (
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/"
        "add/action"
    )
    write = "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write"
    path = f"locks/{target_binding_sha256}.lock"
    return (
        f"((!(ActionMatches{{'{read}'}}) AND !(ActionMatches{{'{add}'}}) AND "
        f"!(ActionMatches{{'{write}'}})) OR (@Resource[Microsoft.Storage/"
        "storageAccounts/blobServices/containers:name] StringEquals "
        f"'{CONTAINER_NAME}' AND @Resource[Microsoft.Storage/storageAccounts/"
        f"blobServices/containers/blobs:path] StringEquals '{path}'))"
    )


@_seal_safety_verifier
def verify_azure_performance_infrastructure_safety(
    *,
    readback_session: (
        AzurePerformanceInfrastructureReadbackSession
        | AzurePerformanceInfrastructureReadbackCapability
    ),
    coordination_storage_account_name: str | None,
    coordination_name_readback_envelope: Mapping[str, Any],
    deployment_receipt_envelope: Mapping[str, Any],
    coordination_storage_readback_envelope: Mapping[str, Any],
    coordination_blob_service_readback_envelope: Mapping[str, Any],
    lease_container_readback_envelope: Mapping[str, Any],
    coordination_storage_account_resource_id: str,
    bff_storage_account_resource_id: str,
    worm_storage_account_resource_id: str,
    bff_storage_readback_envelope: Mapping[str, Any],
    worm_storage_readback_envelope: Mapping[str, Any],
    provisioner_principal_id: str,
    target_binding_sha256: str,
    role_definition: Mapping[str, Any],
    role_assignment: Mapping[str, Any],
    subscription_ancestry_readback_envelope: Mapping[str, Any],
    effective_rbac_readback_envelope: Mapping[str, Any],
    tenant_id: str,
    subscription_id: str,
    resource_group_name: str,
    location: str,
    tags: Mapping[str, str],
    allowed_client_ip_address: str,
) -> tuple[
    Mapping[str, Any], AzurePerformanceInfrastructureReadbackCapability
]:
    """Consume and verify one complete owner-bound infrastructure observation."""

    capability = _require_readback_capability(readback_session)
    _require_adapter_results(
        capability,
        coordination_name_readback_envelope,
        deployment_receipt_envelope,
        coordination_storage_readback_envelope,
        coordination_blob_service_readback_envelope,
        lease_container_readback_envelope,
        bff_storage_readback_envelope,
        worm_storage_readback_envelope,
        role_definition,
        role_assignment,
        subscription_ancestry_readback_envelope,
        effective_rbac_readback_envelope,
    )
    session = capability.session
    verified_at = _claim_readback_session(session)
    evidence = _verify_azure_performance_infrastructure_safety(
        readback_session=session,
        coordination_storage_account_name=coordination_storage_account_name,
        coordination_name_readback_envelope=coordination_name_readback_envelope,
        deployment_receipt_envelope=deployment_receipt_envelope,
        coordination_storage_readback_envelope=coordination_storage_readback_envelope,
        coordination_blob_service_readback_envelope=(
            coordination_blob_service_readback_envelope
        ),
        lease_container_readback_envelope=lease_container_readback_envelope,
        coordination_storage_account_resource_id=(
            coordination_storage_account_resource_id
        ),
        bff_storage_account_resource_id=bff_storage_account_resource_id,
        worm_storage_account_resource_id=worm_storage_account_resource_id,
        bff_storage_readback_envelope=bff_storage_readback_envelope,
        worm_storage_readback_envelope=worm_storage_readback_envelope,
        provisioner_principal_id=provisioner_principal_id,
        target_binding_sha256=target_binding_sha256,
        role_definition=role_definition,
        role_assignment=role_assignment,
        subscription_ancestry_readback_envelope=(
            subscription_ancestry_readback_envelope
        ),
        effective_rbac_readback_envelope=effective_rbac_readback_envelope,
        tenant_id=tenant_id,
        subscription_id=subscription_id,
        resource_group_name=resource_group_name,
        location=location,
        tags=tags,
        allowed_client_ip_address=allowed_client_ip_address,
        verified_at=verified_at,
    )
    return evidence, capability


del _seal_safety_verifier


def _verify_azure_performance_infrastructure_safety(
    *,
    readback_session: AzurePerformanceInfrastructureReadbackSession,
    coordination_storage_account_name: str | None,
    coordination_name_readback_envelope: Mapping[str, Any],
    deployment_receipt_envelope: Mapping[str, Any],
    coordination_storage_readback_envelope: Mapping[str, Any],
    coordination_blob_service_readback_envelope: Mapping[str, Any],
    lease_container_readback_envelope: Mapping[str, Any],
    coordination_storage_account_resource_id: str,
    bff_storage_account_resource_id: str,
    worm_storage_account_resource_id: str,
    bff_storage_readback_envelope: Mapping[str, Any],
    worm_storage_readback_envelope: Mapping[str, Any],
    provisioner_principal_id: str,
    target_binding_sha256: str,
    role_definition: Mapping[str, Any],
    role_assignment: Mapping[str, Any],
    subscription_ancestry_readback_envelope: Mapping[str, Any],
    effective_rbac_readback_envelope: Mapping[str, Any],
    tenant_id: str,
    subscription_id: str,
    resource_group_name: str,
    location: str,
    tags: Mapping[str, str],
    allowed_client_ip_address: str,
    verified_at: datetime,
) -> dict[str, Any]:
    verified_at_utc = _format_utc(verified_at)
    toolchain_attestations_sha256 = readback_session.toolchain_attestations_sha256
    readback_session_sha256 = readback_session.session_sha256
    if (
        not isinstance(coordination_storage_account_name, str)
        or _STORAGE_ACCOUNT_NAME_RE.fullmatch(coordination_storage_account_name)
        is None
    ):
        _fail("COORDINATION_STORAGE_NAME_UNAVAILABLE")
    _require_sha256(target_binding_sha256)
    tenant = _canonical_uuid(tenant_id, "TENANT_ID_INVALID")
    subscription = _canonical_uuid(subscription_id, "SUBSCRIPTION_ID_INVALID")
    if not isinstance(resource_group_name, str) or not resource_group_name:
        _fail("RESOURCE_GROUP_NAME_INVALID")
    if not isinstance(location, str) or _LOCATION_RE.fullmatch(location) is None:
        _fail("LOCATION_INVALID")
    canonical_tags = _canonical_tags(tags)
    effective_tags = effective_coordination_tags(tags, target_binding_sha256)
    if not isinstance(allowed_client_ip_address, str) or not allowed_client_ip_address:
        _fail("ALLOWED_CLIENT_IP_INVALID")
    principal_id = _canonical_uuid(
        provisioner_principal_id, "PROVISIONER_PRINCIPAL_INVALID"
    )

    coordination = _storage_account_id(coordination_storage_account_resource_id)
    bff = _storage_account_id(bff_storage_account_resource_id)
    worm = _storage_account_id(worm_storage_account_resource_id)
    authoritative_bff_storage_account_resource_id = _resource_readback_id(
        bff_storage_readback_envelope,
        observation_kind="bff-storage-account-resource-id",
        error_prefix="AUTHORITATIVE_BFF_READBACK",
        verified_at=verified_at,
        session=readback_session,
    )
    authoritative_worm_storage_account_resource_id = _resource_readback_id(
        worm_storage_readback_envelope,
        observation_kind="worm-storage-account-resource-id",
        error_prefix="AUTHORITATIVE_WORM_READBACK",
        verified_at=verified_at,
        session=readback_session,
    )
    name_observed_at = _verify_name_readback(
        coordination_name_readback_envelope,
        expected_name=coordination_storage_account_name,
        verified_at=verified_at,
        session=readback_session,
    )
    storage_configuration = _expected_storage_configuration(
        coordination=coordination,
        location=location,
        effective_tags=effective_tags,
        allowed_client_ip_address=allowed_client_ip_address,
    )
    deployment = _verify_deployment_receipt(
        deployment_receipt_envelope,
        coordination=coordination,
        tenant_id=tenant,
        target_binding_sha256=target_binding_sha256,
        principal_id=principal_id,
        storage_configuration_sha256=_sha256_json(storage_configuration),
        effective_tags_sha256=_sha256_json(effective_tags),
        name_observed_at=name_observed_at,
        verified_at=verified_at,
        session=readback_session,
    )
    coordination_resource, coordination_observed_at = _coordination_resource_readback(
        coordination_storage_readback_envelope,
        expected_configuration=storage_configuration,
        verified_at=verified_at,
        session=readback_session,
    )
    blob_service_configuration = _expected_blob_service_configuration(coordination)
    blob_service_resource, blob_service_observed_at = (
        _coordination_child_resource_readback(
            coordination_blob_service_readback_envelope,
            observation_kind="coordination-blob-service-configuration",
            observation_source="azure-resource-manager/blob-services-get",
            expected_configuration=blob_service_configuration,
            error_prefix="COORDINATION_BLOB_SERVICE_READBACK",
            mismatch_error="COORDINATION_BLOB_SERVICE_CONFIGURATION_MISMATCH",
            verified_at=verified_at,
            session=readback_session,
        )
    )
    lease_container_configuration = _expected_lease_container_configuration(
        coordination, target_binding_sha256
    )
    lease_container_resource, lease_container_observed_at = (
        _coordination_child_resource_readback(
            lease_container_readback_envelope,
            observation_kind="coordination-lease-container-configuration",
            observation_source="azure-resource-manager/blob-containers-get",
            expected_configuration=lease_container_configuration,
            error_prefix="LEASE_CONTAINER_READBACK",
            mismatch_error="LEASE_CONTAINER_CONFIGURATION_MISMATCH",
            verified_at=verified_at,
            session=readback_session,
        )
    )

    if coordination["name"] != coordination_storage_account_name:
        _fail("COORDINATION_STORAGE_NAME_MISMATCH")
    if coordination_resource["id"].casefold() != coordination["id"].casefold():
        _fail("COORDINATION_STORAGE_READBACK_MISMATCH")
    if bff["id"].casefold() != authoritative_bff_storage_account_resource_id.casefold():
        _fail("AUTHORITATIVE_BFF_STORAGE_MISMATCH")
    if (
        worm["id"].casefold()
        != authoritative_worm_storage_account_resource_id.casefold()
    ):
        _fail("AUTHORITATIVE_WORM_STORAGE_MISMATCH")
    if (
        bff["subscription"] != coordination["subscription"]
        or worm["subscription"] != coordination["subscription"]
    ):
        _fail("STORAGE_ACCOUNT_SUBSCRIPTION_MISMATCH")
    if coordination["subscription"] != subscription:
        _fail("SUBSCRIPTION_ID_MISMATCH")
    if coordination["resource_group"] != resource_group_name:
        _fail("RESOURCE_GROUP_NAME_MISMATCH")
    if len({coordination["name"], bff["name"], worm["name"]}) != 3:
        _fail("COORDINATION_STORAGE_NOT_DEDICATED")

    container_scope = (
        f"{coordination['id']}/blobServices/default/containers/{CONTAINER_NAME}"
    )
    blob_service_scope = f"{coordination['id']}/blobServices/default"
    if blob_service_resource["id"].casefold() != blob_service_scope.casefold():
        _fail("COORDINATION_BLOB_SERVICE_READBACK_MISMATCH")
    if lease_container_resource["id"].casefold() != container_scope.casefold():
        _fail("LEASE_CONTAINER_READBACK_MISMATCH")
    resource_group_scope = (
        f"/subscriptions/{coordination['subscription']}/resourceGroups/"
        f"{coordination['resource_group']}"
    )
    condition = exact_lease_blob_condition(target_binding_sha256)
    role_definition_value, role_definition_observed_at = _arm_object_readback(
        role_definition,
        observation_kind="coordination-role-definition",
        observation_source="azure-resource-manager/role-definitions-get",
        verified_at=verified_at,
        session=readback_session,
    )
    role_definition_id = _verify_role_definition(
        role_definition_value, resource_group_scope
    )
    role_assignment_value, role_assignment_observed_at = _arm_object_readback(
        role_assignment,
        observation_kind="coordination-role-assignment",
        observation_source="azure-resource-manager/role-assignments-get",
        verified_at=verified_at,
        session=readback_session,
    )
    role_assignment_id = _verify_role_assignment(
        role_assignment_value,
        principal_id=principal_id,
        scope=container_scope,
        role_definition_id=role_definition_id,
        condition=condition,
    )
    ancestry, ancestry_observed_at = _verify_subscription_ancestry_readback(
        subscription_ancestry_readback_envelope,
        tenant_id=tenant,
        subscription_id=subscription,
        verified_at=verified_at,
        session=readback_session,
    )
    rbac = _verify_effective_rbac_readback(
        effective_rbac_readback_envelope,
        coordination=coordination,
        principal_id=principal_id,
        expected_assignment_id=role_assignment_id,
        expected_scope=container_scope,
        expected_role_definition_id=role_definition_id,
        expected_condition=condition,
        authoritative_management_group_scopes=ancestry["management_group_scopes"],
        verified_at=verified_at,
        session=readback_session,
    )
    postdeployment_observed_at = {
        "bff_storage": _envelope_observed_at(bff_storage_readback_envelope),
        "worm_storage": _envelope_observed_at(worm_storage_readback_envelope),
        "coordination_storage": coordination_observed_at,
        "blob_service": blob_service_observed_at,
        "lease_container": lease_container_observed_at,
        "role_definition": role_definition_observed_at,
        "role_assignment": role_assignment_observed_at,
        "subscription_ancestry": ancestry_observed_at,
        "effective_rbac": rbac["observed_at"],
    }
    if any(
        observed_at <= deployment["receipt_observed_at"]
        for observed_at in postdeployment_observed_at.values()
    ):
        _fail("READBACK_TIMESTAMP_CONTINUITY_INVALID")

    readback_transcript = {
        "bff_storage": dict(bff_storage_readback_envelope),
        "worm_storage": dict(worm_storage_readback_envelope),
        "coordination_name": dict(coordination_name_readback_envelope),
        "deployment_receipt": dict(deployment_receipt_envelope),
        "coordination_storage": dict(coordination_storage_readback_envelope),
        "blob_service": dict(coordination_blob_service_readback_envelope),
        "lease_container": dict(lease_container_readback_envelope),
        "role_definition": dict(role_definition),
        "role_assignment": dict(role_assignment),
        "subscription_ancestry": dict(subscription_ancestry_readback_envelope),
        "effective_rbac": dict(effective_rbac_readback_envelope),
    }
    evidence = {
        "schema_version": INFRASTRUCTURE_SAFETY_EVIDENCE_SCHEMA,
        "status": "SAFE",
        "infrastructure_safety_policy_sha256": (
            infrastructure_safety_policy_sha256()
        ),
        "target_binding_sha256": target_binding_sha256,
        "tenant_id": tenant,
        "subscription_id": subscription,
        "resource_group_name": resource_group_name,
        "location": location,
        "tags_sha256": _sha256_json(canonical_tags),
        "effective_tags_sha256": _sha256_json(effective_tags),
        "allowed_client_ip_address_sha256": hashlib.sha256(
            allowed_client_ip_address.encode("utf-8")
        ).hexdigest(),
        "toolchain_attestations_sha256": toolchain_attestations_sha256,
        "readback_session_sha256": readback_session_sha256,
        "readback_nonce_sha256": readback_session.nonce_sha256,
        "owner_binding_sha256": readback_session.owner_binding_sha256,
        "execution_attestation_sha256": (
            readback_session.execution_attestation_sha256
        ),
        "verified_at_utc": verified_at_utc,
        "coordination_storage_account_name": coordination_storage_account_name,
        "coordination_storage_account_resource_id": coordination["id"],
        "bff_storage_account_resource_id": bff["id"],
        "worm_storage_account_resource_id": worm["id"],
        "lease_container_resource_id": container_scope,
        "lease_blob_path": f"locks/{target_binding_sha256}.lock",
        "provisioner_principal_id": principal_id,
        "role_definition_id": role_definition_id,
        "role_assignment_id": role_assignment_id,
        "condition": condition,
        "condition_version": "2.0",
        "data_actions": sorted(ALLOWED_DATA_ACTIONS),
        "effective_assignment_count": 1,
        "effective_principal_count": rbac["principal_count"],
        "attested_ancestor_scope_count": rbac["ancestor_scope_count"],
        "tenant_root_management_group_scope": ancestry[
            "tenant_root_management_group_scope"
        ],
        "deployment_receipt_sha256": deployment_receipt_envelope[
            "observation_sha256"
        ],
        "storage_configuration_sha256": _sha256_json(storage_configuration),
        "readback_observation_sha256": {
            key: envelope["observation_sha256"]
            for key, envelope in readback_transcript.items()
        },
        "readback_transcript": readback_transcript,
        "network_accessed": True,
    }
    result = {
        **evidence,
        "infrastructure_safety_evidence_sha256": _sha256_json(evidence),
    }
    return result


def validate_infrastructure_safety_evidence(
    value: AzurePerformanceInfrastructureSafetyVerification,
) -> AzurePerformanceInfrastructureSafetyVerification:
    """Require a live verifier-issued SAFE capability before runtime use."""

    if type(value) is not AzurePerformanceInfrastructureSafetyVerification:
        _fail("INFRASTRUCTURE_SAFETY_CAPABILITY_REQUIRED")
    value._assert_valid_capability()
    result = dict(value)
    if set(result) != _INFRASTRUCTURE_SAFETY_EVIDENCE_KEYS:
        _fail("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")
    digest = result.pop("infrastructure_safety_evidence_sha256", None)
    observation_digests = result.get("readback_observation_sha256")
    transcript = result.get("readback_transcript")
    if (
        result.get("schema_version")
        != INFRASTRUCTURE_SAFETY_EVIDENCE_SCHEMA
        or result.get("status") != "SAFE"
        or result.get("infrastructure_safety_policy_sha256")
        != infrastructure_safety_policy_sha256()
        or not isinstance(result.get("target_binding_sha256"), str)
        or _SHA256_RE.fullmatch(result["target_binding_sha256"]) is None
        or result.get("network_accessed") is not True
        or not isinstance(result.get("owner_binding_sha256"), str)
        or _SHA256_RE.fullmatch(result["owner_binding_sha256"]) is None
        or not _fresh_evidence_timestamp(result.get("verified_at_utc"))
        or result.get("effective_assignment_count") != 1
        or not isinstance(observation_digests, Mapping)
        or set(observation_digests) != _READBACK_TRANSCRIPT_KEYS
        or any(
            not isinstance(item, str) or _SHA256_RE.fullmatch(item) is None
            for item in observation_digests.values()
        )
        or not isinstance(transcript, Mapping)
        or set(transcript) != _READBACK_TRANSCRIPT_KEYS
        or any(not isinstance(item, Mapping) for item in transcript.values())
        or not isinstance(digest, str)
        or _SHA256_RE.fullmatch(digest) is None
        or digest != _sha256_json(result)
    ):
        _fail("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")
    try:
        session = _session_from_evidence(result, transcript)
        capability = value._readback_capability
        if session != capability.session:
            _fail("INFRASTRUCTURE_SAFETY_CAPABILITY_INVALID")
        deployment_inputs = _deployment_inputs_from_transcript(
            transcript["deployment_receipt"]
        )
        expected = _verify_azure_performance_infrastructure_safety(
            readback_session=session,
            coordination_storage_account_name=deployment_inputs[
                "storageAccountName"
            ],
            coordination_name_readback_envelope=transcript["coordination_name"],
            deployment_receipt_envelope=transcript["deployment_receipt"],
            coordination_storage_readback_envelope=transcript[
                "coordination_storage"
            ],
            coordination_blob_service_readback_envelope=transcript[
                "blob_service"
            ],
            lease_container_readback_envelope=transcript["lease_container"],
            coordination_storage_account_resource_id=result[
                "coordination_storage_account_resource_id"
            ],
            bff_storage_account_resource_id=result[
                "bff_storage_account_resource_id"
            ],
            worm_storage_account_resource_id=result[
                "worm_storage_account_resource_id"
            ],
            bff_storage_readback_envelope=transcript["bff_storage"],
            worm_storage_readback_envelope=transcript["worm_storage"],
            provisioner_principal_id=deployment_inputs[
                "provisionerPrincipalId"
            ],
            target_binding_sha256=deployment_inputs["targetBindingSha256"],
            role_definition=transcript["role_definition"],
            role_assignment=transcript["role_assignment"],
            subscription_ancestry_readback_envelope=transcript[
                "subscription_ancestry"
            ],
            effective_rbac_readback_envelope=transcript["effective_rbac"],
            tenant_id=deployment_inputs["tenantId"],
            subscription_id=deployment_inputs["subscriptionId"],
            resource_group_name=deployment_inputs["resourceGroupName"],
            location=deployment_inputs["location"],
            tags=deployment_inputs["tags"],
            allowed_client_ip_address=deployment_inputs[
                "allowedClientIpAddress"
            ],
            verified_at=_parse_observed_at(
                result["verified_at_utc"],
                "INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID",
            ),
        )
    except (AzurePerformanceInfrastructureSafetyError, KeyError, TypeError, ValueError):
        _fail("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")
    expected_without_digest = dict(expected)
    expected_without_digest.pop("infrastructure_safety_evidence_sha256", None)
    if expected_without_digest != result:
        _fail("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")
    return value


def _session_from_evidence(
    evidence: Mapping[str, Any], transcript: Mapping[str, Mapping[str, Any]]
) -> AzurePerformanceInfrastructureReadbackSession:
    first = transcript["deployment_receipt"]
    attestation = first.get("execution_attestation")
    nonce = first.get("readback_nonce")
    if not isinstance(attestation, Mapping) or not isinstance(nonce, str):
        _fail("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")
    expected_keys = {
        "schema_version",
        "created_at_utc",
        "owner_binding_sha256",
        "toolchain_attestations_sha256",
        "nonce_sha256",
        "executable_path_sha256",
        "executable_sha256",
        "argv_sha256",
        "readback_session_sha256",
    }
    if set(attestation) != expected_keys:
        _fail("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")
    session = AzurePerformanceInfrastructureReadbackSession(
        created_at_utc=attestation["created_at_utc"],
        owner_binding_sha256=attestation["owner_binding_sha256"],
        toolchain_attestations_sha256=attestation[
            "toolchain_attestations_sha256"
        ],
        nonce=nonce,
        nonce_sha256=attestation["nonce_sha256"],
        executable_path_sha256=attestation["executable_path_sha256"],
        executable_sha256=attestation["executable_sha256"],
        argv_sha256=attestation["argv_sha256"],
        session_sha256=attestation["readback_session_sha256"],
        execution_attestation_sha256=evidence[
            "execution_attestation_sha256"
        ],
    )
    _validate_readback_session_integrity(session, check_execution_identity=False)
    return session


def _deployment_inputs_from_transcript(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    sealed = envelope.get("sealed_execution")
    if not isinstance(sealed, Mapping) or set(sealed) != _SEALED_EXECUTION_KEYS:
        _fail("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")
    operations = sealed.get("operations")
    if (
        not isinstance(operations, list)
        or len(operations) != 1
        or not _valid_sealed_operation(operations[0])
    ):
        _fail("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")
    response = _decode_azure_json_response(
        base64.b64decode(operations[0]["raw_response_base64"], validate=True)
    )
    properties = response.get("properties")
    parameters = (
        properties.get("parameters") if isinstance(properties, Mapping) else None
    )
    required = {
        "tenantId",
        "subscriptionId",
        "resourceGroupName",
        "storageAccountName",
        "provisionerPrincipalId",
        "allowedClientIpAddress",
        "targetBindingSha256",
        "location",
        "tags",
    }
    if not isinstance(parameters, Mapping) or not required.issubset(parameters):
        _fail("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")
    result: dict[str, Any] = {}
    for name in required:
        parameter = parameters.get(name)
        if not isinstance(parameter, Mapping) or set(parameter) != {"value"}:
            _fail("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")
        result[name] = parameter["value"]
    if not isinstance(result["tags"], Mapping):
        _fail("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")
    return result


def _resource_readback_id(
    value: Mapping[str, Any],
    *,
    observation_kind: str,
    error_prefix: str,
    verified_at: datetime,
    session: AzurePerformanceInfrastructureReadbackSession,
) -> str:
    _verify_envelope_shape_and_digest(
        value,
        expected_keys={
            "schema_version",
            "observation_kind",
            "api_version",
            "observed_at_utc",
            "observation_source",
            "observation_command_sha256",
            "toolchain_attestations_sha256",
            "readback_session_sha256",
            "readback_nonce",
            "execution_attestation",
            "payload",
            "sealed_execution",
            "response_sha256",
            "observation_sha256",
        },
        error_prefix=error_prefix,
    )
    payload = value.get("payload")
    if (
        value.get("schema_version") != PROVENANCE_READBACK_SCHEMA
        or value.get("observation_kind") != observation_kind
        or value.get("api_version") != STORAGE_API_VERSION
        or value.get("observation_source")
        != "azure-resource-manager/storage-accounts-get"
        or not _valid_provenance_binding(
            value,
            verified_at=verified_at,
            maximum_age=_POSTDEPLOY_MAX_AGE,
            session=session,
        )
        or not isinstance(payload, Mapping)
        or set(payload) != {"resource_id"}
    ):
        _fail(f"{error_prefix}_INVALID")
    return _storage_account_id(payload.get("resource_id"))["id"]


def _coordination_resource_readback(
    value: Mapping[str, Any],
    *,
    expected_configuration: Mapping[str, Any],
    verified_at: datetime,
    session: AzurePerformanceInfrastructureReadbackSession,
) -> tuple[dict[str, Any], datetime]:
    prefix = "COORDINATION_STORAGE_READBACK"
    _verify_envelope_shape_and_digest(
        value,
        expected_keys={
            "schema_version",
            "observation_kind",
            "api_version",
            "observed_at_utc",
            "observation_source",
            "observation_command_sha256",
            "toolchain_attestations_sha256",
            "readback_session_sha256",
            "readback_nonce",
            "execution_attestation",
            "payload",
            "sealed_execution",
            "response_sha256",
            "observation_sha256",
        },
        error_prefix=prefix,
    )
    payload = value.get("payload")
    if (
        value.get("schema_version") != PROVENANCE_READBACK_SCHEMA
        or value.get("observation_kind")
        != "coordination-storage-account-configuration"
        or value.get("api_version") != STORAGE_API_VERSION
        or value.get("observation_source")
        != "azure-resource-manager/storage-accounts-get"
        or not _valid_provenance_binding(
            value,
            verified_at=verified_at,
            maximum_age=_POSTDEPLOY_MAX_AGE,
            session=session,
        )
        or not isinstance(payload, Mapping)
    ):
        _fail(f"{prefix}_INVALID")
    if payload != expected_configuration:
        _fail("COORDINATION_STORAGE_CONFIGURATION_MISMATCH")
    return dict(payload), _envelope_observed_at(value)


def _coordination_child_resource_readback(
    value: Mapping[str, Any],
    *,
    observation_kind: str,
    observation_source: str,
    expected_configuration: Mapping[str, Any],
    error_prefix: str,
    mismatch_error: str,
    verified_at: datetime,
    session: AzurePerformanceInfrastructureReadbackSession,
) -> tuple[dict[str, Any], datetime]:
    _verify_envelope_shape_and_digest(
        value,
        expected_keys=_provenance_envelope_keys(),
        error_prefix=error_prefix,
    )
    payload = value.get("payload")
    expected_resource_id = expected_configuration.get("id")
    sealed = value.get("sealed_execution")
    operations = sealed.get("operations") if isinstance(sealed, Mapping) else None
    expected_url = (
        f"https://management.azure.com{expected_resource_id}"
        f"?api-version={STORAGE_API_VERSION}"
    )
    if (
        value.get("schema_version") != PROVENANCE_READBACK_SCHEMA
        or value.get("observation_kind") != observation_kind
        or value.get("api_version") != STORAGE_API_VERSION
        or value.get("observation_source") != observation_source
        or not _valid_provenance_binding(
            value,
            verified_at=verified_at,
            maximum_age=_POSTDEPLOY_MAX_AGE,
            session=session,
        )
        or not isinstance(payload, Mapping)
        or not isinstance(expected_resource_id, str)
        or not isinstance(operations, list)
        or len(operations) != 1
        or not _operation_is_exact_get(
            operations[0],
            expected_url,
            STORAGE_API_VERSION,
            expected_resource_id,
        )
    ):
        _fail(f"{error_prefix}_INVALID")
    if payload != expected_configuration:
        _fail(mismatch_error)
    return dict(payload), _envelope_observed_at(value)


def _verify_name_readback(
    value: Mapping[str, Any],
    *,
    expected_name: str,
    verified_at: datetime,
    session: AzurePerformanceInfrastructureReadbackSession,
) -> datetime:
    prefix = "COORDINATION_NAME_READBACK"
    _verify_envelope_shape_and_digest(
        value,
        expected_keys={
            "schema_version",
            "observation_kind",
            "api_version",
            "observed_at_utc",
            "observation_source",
            "observation_command_sha256",
            "toolchain_attestations_sha256",
            "readback_session_sha256",
            "readback_nonce",
            "execution_attestation",
            "payload",
            "sealed_execution",
            "response_sha256",
            "observation_sha256",
        },
        error_prefix=prefix,
    )
    payload = value.get("payload")
    if (
        value.get("schema_version") != PROVENANCE_READBACK_SCHEMA
        or value.get("observation_kind")
        != "coordination-storage-name-availability"
        or value.get("api_version") != STORAGE_API_VERSION
        or value.get("observation_source")
        != "azure-resource-manager/storage-accounts-check-name-availability"
        or not _valid_provenance_binding(
            value,
            verified_at=verified_at,
            maximum_age=_PREDEPLOY_MAX_AGE,
            session=session,
        )
        or not isinstance(payload, Mapping)
        or set(payload) != {"name", "name_available"}
        or not isinstance(payload.get("name"), str)
        or _STORAGE_ACCOUNT_NAME_RE.fullmatch(payload["name"]) is None
        or not isinstance(payload.get("name_available"), bool)
    ):
        _fail(f"{prefix}_INVALID")
    if payload["name"] != expected_name:
        _fail("COORDINATION_STORAGE_NAME_MISMATCH")
    if payload["name_available"] is not True:
        _fail("COORDINATION_STORAGE_NAME_UNAVAILABLE")
    return _envelope_observed_at(value)


def _expected_storage_configuration(
    *,
    coordination: Mapping[str, str],
    location: str,
    effective_tags: Mapping[str, str],
    allowed_client_ip_address: str,
) -> dict[str, Any]:
    return {
        "id": coordination["id"],
        "name": coordination["name"],
        "type": "Microsoft.Storage/storageAccounts",
        "location": location,
        "kind": "StorageV2",
        "sku": {"name": "Standard_LRS", "tier": "Standard"},
        "tags": dict(effective_tags),
        "properties": {
            "accessTier": "Hot",
            "allowBlobPublicAccess": False,
            "allowCrossTenantReplication": False,
            "allowSharedKeyAccess": False,
            "defaultToOAuthAuthentication": True,
            "isHnsEnabled": False,
            "minimumTlsVersion": "TLS1_2",
            "networkAcls": {
                "bypass": "None",
                "defaultAction": "Deny",
                "ipRules": [
                    {"action": "Allow", "value": allowed_client_ip_address}
                ],
                "resourceAccessRules": [],
                "virtualNetworkRules": [],
            },
            "publicNetworkAccess": "Enabled",
            "supportsHttpsTrafficOnly": True,
        },
    }


def _expected_blob_service_configuration(
    coordination: Mapping[str, str],
) -> dict[str, Any]:
    resource_id = f"{coordination['id']}/blobServices/default"
    return {
        "id": resource_id,
        "name": "default",
        "type": "Microsoft.Storage/storageAccounts/blobServices",
        "properties": {
            "isVersioningEnabled": False,
            "deleteRetentionPolicy": {"enabled": False},
            "containerDeleteRetentionPolicy": {"enabled": False},
        },
    }


def _expected_lease_container_configuration(
    coordination: Mapping[str, str], target_binding_sha256: str
) -> dict[str, Any]:
    resource_id = (
        f"{coordination['id']}/blobServices/default/containers/{CONTAINER_NAME}"
    )
    return {
        "id": resource_id,
        "name": CONTAINER_NAME,
        "type": "Microsoft.Storage/storageAccounts/blobServices/containers",
        "properties": {
            "publicAccess": "None",
            "metadata": {
                "nac_schema_version": (
                    "nac.azure-bff-performance-coordination/v1"
                ),
                "data_classification": "synthetic-only",
                "lease_blob_path": f"locks/{target_binding_sha256}.lock",
                "lease_blob_type": "BlockBlob",
                "lease_blob_content_length": "0",
                "lease_blob_bootstrap": (
                    "owner-gated-put-if-absent-before-runtime"
                ),
                "azure_blob_write_authorization": (
                    "includes-create-overwrite-lease-and-break"
                ),
                "operation_restriction_boundary": (
                    "sealed-app-api-defense-in-depth-not-azure-enforced"
                ),
                "principal_separation": (
                    "single-owner-bound-bootstrap-and-runtime-principal"
                ),
            },
        },
    }


def _verify_deployment_receipt(
    value: Mapping[str, Any],
    *,
    coordination: Mapping[str, str],
    tenant_id: str,
    target_binding_sha256: str,
    principal_id: str,
    storage_configuration_sha256: str,
    effective_tags_sha256: str,
    name_observed_at: datetime,
    verified_at: datetime,
    session: AzurePerformanceInfrastructureReadbackSession,
) -> dict[str, datetime]:
    prefix = "DEPLOYMENT_RECEIPT"
    _verify_envelope_shape_and_digest(
        value,
        expected_keys=_provenance_envelope_keys(),
        error_prefix=prefix,
    )
    payload = value.get("payload")
    expected_payload_keys = {
        "deployment_id",
        "provisioning_state",
        "started_at_utc",
        "completed_at_utc",
        "tenant_id",
        "coordination_storage_account_resource_id",
        "target_binding_sha256",
        "provisioner_principal_id",
        "effective_tags_sha256",
        "storage_configuration_sha256",
    }
    if (
        value.get("schema_version") != PROVENANCE_READBACK_SCHEMA
        or value.get("observation_kind") != "coordination-deployment-receipt"
        or value.get("api_version") != DEPLOYMENT_API_VERSION
        or value.get("observation_source")
        != "azure-resource-manager/deployments-get"
        or not _valid_provenance_binding(
            value,
            verified_at=verified_at,
            maximum_age=_POSTDEPLOY_MAX_AGE,
            session=session,
        )
        or not isinstance(payload, Mapping)
        or set(payload) != expected_payload_keys
    ):
        _fail(f"{prefix}_INVALID")
    deployment_id = payload.get("deployment_id")
    match = (
        _DEPLOYMENT_ID_RE.fullmatch(deployment_id)
        if isinstance(deployment_id, str)
        else None
    )
    if (
        match is None
        or _canonical_uuid(match.group("subscription"), f"{prefix}_INVALID")
        != coordination["subscription"]
        or match.group("resource_group").casefold()
        != coordination["resource_group"].casefold()
        or payload.get("provisioning_state") != "Succeeded"
        or _canonical_uuid(payload.get("tenant_id"), f"{prefix}_INVALID")
        != tenant_id
        or str(payload.get("coordination_storage_account_resource_id", "")).casefold()
        != coordination["id"].casefold()
        or payload.get("target_binding_sha256") != target_binding_sha256
        or _canonical_uuid(
            payload.get("provisioner_principal_id"), f"{prefix}_INVALID"
        )
        != principal_id
        or payload.get("effective_tags_sha256") != effective_tags_sha256
        or payload.get("storage_configuration_sha256")
        != storage_configuration_sha256
    ):
        _fail(f"{prefix}_INVALID")
    started_at = _parse_observed_at(
        payload.get("started_at_utc"), f"{prefix}_INVALID"
    )
    completed_at = _parse_observed_at(
        payload.get("completed_at_utc"), f"{prefix}_INVALID"
    )
    receipt_observed_at = _envelope_observed_at(value)
    if not (
        name_observed_at < started_at <= completed_at <= receipt_observed_at
    ):
        _fail("READBACK_TIMESTAMP_CONTINUITY_INVALID")
    return {
        "started_at": started_at,
        "completed_at": completed_at,
        "receipt_observed_at": receipt_observed_at,
    }


def _arm_object_readback(
    value: Mapping[str, Any],
    *,
    observation_kind: str,
    observation_source: str,
    verified_at: datetime,
    session: AzurePerformanceInfrastructureReadbackSession,
) -> tuple[Mapping[str, Any], datetime]:
    prefix = observation_kind.replace("-", "_").upper()
    _verify_envelope_shape_and_digest(
        value,
        expected_keys=_provenance_envelope_keys(),
        error_prefix=prefix,
    )
    payload = value.get("payload")
    if (
        value.get("schema_version") != PROVENANCE_READBACK_SCHEMA
        or value.get("observation_kind") != observation_kind
        or value.get("api_version") != AUTHORIZATION_API_VERSION
        or value.get("observation_source") != observation_source
        or not _valid_provenance_binding(
            value,
            verified_at=verified_at,
            maximum_age=_POSTDEPLOY_MAX_AGE,
            session=session,
        )
        or not isinstance(payload, Mapping)
        or set(payload) != {"resource"}
        or not isinstance(payload.get("resource"), Mapping)
    ):
        _fail(f"{prefix}_INVALID")
    return payload["resource"], _envelope_observed_at(value)


def _verify_subscription_ancestry_readback(
    value: Mapping[str, Any],
    *,
    tenant_id: str,
    subscription_id: str,
    verified_at: datetime,
    session: AzurePerformanceInfrastructureReadbackSession,
) -> tuple[dict[str, Any], datetime]:
    prefix = "SUBSCRIPTION_ANCESTRY_READBACK"
    _verify_envelope_shape_and_digest(
        value,
        expected_keys=_provenance_envelope_keys(),
        error_prefix=prefix,
    )
    payload = value.get("payload")
    if (
        value.get("schema_version") != PROVENANCE_READBACK_SCHEMA
        or value.get("observation_kind")
        != "subscription-management-group-ancestry"
        or value.get("api_version") != MANAGEMENT_GROUP_API_VERSION
        or value.get("observation_source")
        != "azure-resource-manager/management-groups-subscriptions-get"
        or not _valid_provenance_binding(
            value,
            verified_at=verified_at,
            maximum_age=_POSTDEPLOY_MAX_AGE,
            session=session,
        )
        or not isinstance(payload, Mapping)
        or set(payload)
        != {
            "tenant_id",
            "subscription_id",
            "tenant_root_scope",
            "tenant_root_management_group_scope",
            "management_group_relationships",
            "subscription_attachment",
            "ancestry_complete",
        }
    ):
        _fail(f"{prefix}_INVALID")
    relationships = payload.get("management_group_relationships")
    attachment = payload.get("subscription_attachment")
    root_scope = payload.get("tenant_root_management_group_scope")
    root_match = (
        _MANAGEMENT_GROUP_SCOPE_RE.fullmatch(root_scope)
        if isinstance(root_scope, str)
        else None
    )
    if (
        _canonical_uuid(payload.get("tenant_id"), f"{prefix}_INVALID")
        != tenant_id
        or _canonical_uuid(payload.get("subscription_id"), f"{prefix}_INVALID")
        != subscription_id
        or payload.get("tenant_root_scope") != "/"
        or payload.get("ancestry_complete") is not True
        or root_match is None
        or root_match.group("name").casefold() != tenant_id.casefold()
        or not isinstance(relationships, list)
        or not relationships
        or not isinstance(attachment, Mapping)
    ):
        _fail("EFFECTIVE_RBAC_ANCESTRY_INVALID")
    scopes: list[str] = []
    expected_parent = "/"
    for index, relationship in enumerate(relationships):
        if (
            not isinstance(relationship, Mapping)
            or set(relationship) != {"scope", "parent_scope"}
            or not isinstance(relationship.get("scope"), str)
            or _MANAGEMENT_GROUP_SCOPE_RE.fullmatch(relationship["scope"])
            is None
            or relationship.get("parent_scope") != expected_parent
            or (index == 0 and relationship["scope"] != root_scope)
        ):
            _fail("EFFECTIVE_RBAC_ANCESTRY_INVALID")
        scopes.append(relationship["scope"])
        expected_parent = relationship["scope"]
    subscription_scope = f"/subscriptions/{subscription_id}"
    if (
        set(attachment) != {
            "subscription_scope",
            "parent_management_group_scope",
        }
        or not isinstance(attachment.get("subscription_scope"), str)
        or attachment["subscription_scope"].casefold()
        != subscription_scope.casefold()
        or attachment.get("parent_management_group_scope") != scopes[-1]
        or len({scope.casefold() for scope in scopes}) != len(scopes)
    ):
        _fail("EFFECTIVE_RBAC_ANCESTRY_INVALID")
    return {
        "tenant_root_management_group_scope": root_scope,
        "management_group_scopes": scopes,
    }, _envelope_observed_at(value)


def _verify_effective_rbac_readback(
    value: Mapping[str, Any],
    *,
    coordination: Mapping[str, str],
    principal_id: str,
    expected_assignment_id: str,
    expected_scope: str,
    expected_role_definition_id: str,
    expected_condition: str,
    authoritative_management_group_scopes: list[str],
    verified_at: datetime,
    session: AzurePerformanceInfrastructureReadbackSession,
) -> dict[str, Any]:
    prefix = "EFFECTIVE_RBAC_READBACK"
    _verify_envelope_shape_and_digest(
        value,
        expected_keys={
            "schema_version",
            "observation_kind",
            "api_versions",
            "observed_at_utc",
            "observation_source",
            "observation_command_sha256",
            "toolchain_attestations_sha256",
            "readback_session_sha256",
            "readback_nonce",
            "execution_attestation",
            "payload",
            "sealed_execution",
            "response_sha256",
            "observation_sha256",
        },
        error_prefix=prefix,
    )
    if (
        value.get("schema_version") != EFFECTIVE_RBAC_READBACK_SCHEMA
        or value.get("observation_kind") != "effective-rbac-abac"
        or value.get("api_versions")
        != {
            "azure_authorization": AUTHORIZATION_API_VERSION,
            "microsoft_graph": MICROSOFT_GRAPH_API_VERSION,
        }
        or value.get("observation_source")
        != "azure-resource-manager-and-microsoft-graph-effective-access-readback"
        or not _valid_provenance_binding(
            value,
            verified_at=verified_at,
            maximum_age=_POSTDEPLOY_MAX_AGE,
            session=session,
        )
    ):
        _fail(f"{prefix}_INVALID")
    payload = value.get("payload")
    expected_payload_keys = {
        "target_resource_id",
        "principal_id",
        "transitive_group_principal_ids",
        "ancestor_scopes",
        "effective_role_assignments",
        "completeness_attestation",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected_payload_keys:
        _fail(f"{prefix}_INVALID")
    completeness = payload.get("completeness_attestation")
    required_completeness = {
        "root_ancestry_complete": True,
        "management_group_ancestry_complete": True,
        "transitive_group_membership_complete": True,
        "role_assignments_complete": True,
        "role_definitions_expanded": True,
    }
    if completeness != required_completeness:
        _fail("EFFECTIVE_RBAC_READBACK_INCOMPLETE")
    if (
        not isinstance(payload.get("target_resource_id"), str)
        or payload["target_resource_id"].casefold() != expected_scope.casefold()
        or _canonical_uuid(
            payload.get("principal_id"), "EFFECTIVE_RBAC_READBACK_INVALID"
        )
        != principal_id
    ):
        _fail("EFFECTIVE_RBAC_READBACK_INVALID")

    groups_value = payload.get("transitive_group_principal_ids")
    if not isinstance(groups_value, list):
        _fail("EFFECTIVE_PRINCIPAL_EXPANSION_INVALID")
    groups = [
        _canonical_uuid(group, "EFFECTIVE_PRINCIPAL_EXPANSION_INVALID")
        for group in groups_value
    ]
    if len(groups) != len(set(groups)) or principal_id in groups:
        _fail("EFFECTIVE_PRINCIPAL_EXPANSION_INVALID")

    ancestor_scopes = _verify_ancestor_scopes(
        payload.get("ancestor_scopes"),
        coordination=coordination,
        authoritative_management_group_scopes=(
            authoritative_management_group_scopes
        ),
    )
    assignments = payload.get("effective_role_assignments")
    exact_count = _verify_effective_assignments(
        assignments,
        principal_id=principal_id,
        group_principal_ids=frozenset(groups),
        expected_assignment_id=expected_assignment_id,
        expected_scope=expected_scope,
        expected_role_definition_id=expected_role_definition_id,
        expected_condition=expected_condition,
        ancestor_scopes=ancestor_scopes,
    )
    if exact_count != 1:
        _fail("EXPECTED_EFFECTIVE_ASSIGNMENT_NOT_UNIQUE")
    return {
        "principal_count": 1 + len(groups),
        "ancestor_scope_count": len(ancestor_scopes),
        "observed_at": _envelope_observed_at(value),
    }


def _verify_ancestor_scopes(
    value: Any,
    *,
    coordination: Mapping[str, str],
    authoritative_management_group_scopes: list[str],
) -> set[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(scope, str) for scope in value)
    ):
        _fail("EFFECTIVE_RBAC_ANCESTRY_INVALID")
    scopes = list(value)
    folded = [scope.casefold() for scope in scopes]
    if len(scopes) != len(set(folded)) or not scopes or scopes[0] != "/":
        _fail("EFFECTIVE_RBAC_ANCESTRY_INVALID")
    expected = [
        "/",
        *authoritative_management_group_scopes,
        f"/subscriptions/{coordination['subscription']}",
        (
            f"/subscriptions/{coordination['subscription']}/resourceGroups/"
            f"{coordination['resource_group']}"
        ),
        coordination["id"],
        f"{coordination['id']}/blobServices/default",
        f"{coordination['id']}/blobServices/default/containers/{CONTAINER_NAME}",
    ]
    if [scope.casefold() for scope in scopes] != [
        scope.casefold() for scope in expected
    ]:
        _fail("EFFECTIVE_RBAC_ANCESTRY_INVALID")
    return set(folded)


def _verify_role_definition(
    value: Mapping[str, Any], expected_assignable_scope: str
) -> str:
    properties = _properties(value, "ROLE_DEFINITION_INVALID")
    permissions = properties.get("permissions")
    if (
        properties.get("type") != "CustomRole"
        or not isinstance(permissions, list)
        or len(permissions) != 1
        or not isinstance(permissions[0], Mapping)
        or permissions[0].get("actions") != []
        or permissions[0].get("notActions") != []
        or permissions[0].get("notDataActions") != []
        or _exact_data_actions(permissions[0].get("dataActions"))
        != ALLOWED_DATA_ACTIONS
    ):
        _fail("ROLE_DEFINITION_DATA_ACTIONS_INVALID")
    scopes = properties.get("assignableScopes")
    if (
        not isinstance(scopes, list)
        or len(scopes) != 1
        or not isinstance(scopes[0], str)
        or scopes[0].casefold() != expected_assignable_scope.casefold()
    ):
        _fail("ROLE_DEFINITION_SCOPE_INVALID")
    return _require_arm_id(value.get("id"), "ROLE_DEFINITION_ID_INVALID")


def _verify_role_assignment(
    value: Mapping[str, Any],
    *,
    principal_id: str,
    scope: str,
    role_definition_id: str,
    condition: str,
) -> str:
    properties = _properties(value, "ROLE_ASSIGNMENT_INVALID")
    if _canonical_uuid(
        properties.get("principalId"), "ROLE_ASSIGNMENT_PRINCIPAL_INVALID"
    ) != principal_id:
        _fail("ROLE_ASSIGNMENT_PRINCIPAL_INVALID")
    if properties.get("principalType") != "ServicePrincipal":
        _fail("ROLE_ASSIGNMENT_PRINCIPAL_INVALID")
    actual_scope = _field(value, properties, "scope")
    if not isinstance(actual_scope, str) or actual_scope.casefold() != scope.casefold():
        _fail("ROLE_ASSIGNMENT_SCOPE_INVALID")
    actual_role = properties.get("roleDefinitionId")
    if (
        not isinstance(actual_role, str)
        or actual_role.casefold() != role_definition_id.casefold()
    ):
        _fail("ROLE_ASSIGNMENT_ROLE_DEFINITION_INVALID")
    if properties.get("conditionVersion") != "2.0":
        _fail("ROLE_ASSIGNMENT_CONDITION_INVALID")
    if properties.get("condition") != condition:
        _fail("ROLE_ASSIGNMENT_CONDITION_INVALID")
    assignment_id = _require_arm_id(
        value.get("id"), "ROLE_ASSIGNMENT_ID_INVALID"
    )
    expected_prefix = (
        f"{scope}/providers/Microsoft.Authorization/roleAssignments/".casefold()
    )
    if not assignment_id.casefold().startswith(expected_prefix):
        _fail("ROLE_ASSIGNMENT_SCOPE_INVALID")
    return assignment_id


def _verify_effective_assignments(
    values: Any,
    *,
    principal_id: str,
    group_principal_ids: frozenset[str],
    expected_assignment_id: str,
    expected_scope: str,
    expected_role_definition_id: str,
    expected_condition: str,
    ancestor_scopes: set[str],
) -> int:
    if not isinstance(values, list):
        _fail("EFFECTIVE_ASSIGNMENTS_INVALID")
    exact_count = 0
    relevant_principals = {principal_id, *group_principal_ids}
    for value in values:
        properties = _properties(value, "EFFECTIVE_ASSIGNMENTS_INVALID")
        candidate_principal = _canonical_uuid(
            properties.get("principalId"), "EFFECTIVE_ASSIGNMENTS_INVALID"
        )
        if candidate_principal not in relevant_principals:
            continue
        expected_principal_type = (
            "ServicePrincipal"
            if candidate_principal == principal_id
            else "Group"
        )
        if properties.get("principalType") != expected_principal_type:
            _fail("EFFECTIVE_PRINCIPAL_EXPANSION_INVALID")
        scope = _field(value, properties, "scope")
        if not isinstance(scope, str) or scope.casefold() not in ancestor_scopes:
            _fail("EFFECTIVE_ASSIGNMENT_SCOPE_INVALID")
        assignment_id = _require_arm_id(
            value.get("id"), "EFFECTIVE_ASSIGNMENTS_INVALID"
        )
        data_actions = _expanded_permission_actions(
            value, properties, field_name="dataActions"
        )
        control_actions = _expanded_permission_actions(
            value, properties, field_name="actions"
        )
        if data_actions is None or control_actions is None:
            _fail("EFFECTIVE_ASSIGNMENT_DATA_ACTIONS_UNRESOLVED")
        if control_actions:
            _fail("BROADER_EFFECTIVE_CONTROL_PLANE_ASSIGNMENT_PRESENT")
        if assignment_id.casefold() == expected_assignment_id.casefold():
            candidate_role_definition_id = properties.get("roleDefinitionId")
            if (
                candidate_principal != principal_id
                or scope.casefold() != expected_scope.casefold()
                or not isinstance(candidate_role_definition_id, str)
                or candidate_role_definition_id.casefold()
                != expected_role_definition_id.casefold()
                or properties.get("condition") != expected_condition
                or properties.get("conditionVersion") != "2.0"
                or data_actions != ALLOWED_DATA_ACTIONS
            ):
                _fail("EXPECTED_EFFECTIVE_ASSIGNMENT_INVALID")
            exact_count += 1
        elif data_actions:
            _fail("BROADER_EFFECTIVE_ASSIGNMENT_PRESENT")
    return exact_count


def _expanded_permission_actions(
    value: Mapping[str, Any],
    properties: Mapping[str, Any],
    *,
    field_name: str,
) -> frozenset[str] | None:
    direct = _field(value, properties, field_name)
    if direct is not None:
        return _data_actions(direct)
    role = value.get("roleDefinition")
    if not isinstance(role, Mapping):
        return None
    role_properties = role.get("properties", role)
    if not isinstance(role_properties, Mapping):
        return None
    permissions = role_properties.get("permissions")
    if not isinstance(permissions, list) or not permissions:
        return None
    expanded: set[str] = set()
    for permission in permissions:
        if not isinstance(permission, Mapping):
            return None
        actions = _data_actions(permission.get(field_name))
        if actions is None:
            return None
        expanded.update(actions)
    return frozenset(expanded)


def _verify_envelope_shape_and_digest(
    value: Any, *, expected_keys: set[str], error_prefix: str
) -> None:
    if not isinstance(value, Mapping) or set(value) != expected_keys:
        _fail(f"{error_prefix}_INVALID")
    digest = value.get("observation_sha256")
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        _fail(f"{error_prefix}_INVALID")
    try:
        measured = canonical_observation_sha256(value)
    except (TypeError, ValueError):
        _fail(f"{error_prefix}_INVALID")
    if digest != measured:
        _fail(f"{error_prefix}_DIGEST_MISMATCH")


def _provenance_envelope_keys() -> set[str]:
    return {
        "schema_version",
        "observation_kind",
        "api_version",
        "observed_at_utc",
        "observation_source",
        "observation_command_sha256",
        "toolchain_attestations_sha256",
        "readback_session_sha256",
        "readback_nonce",
        "execution_attestation",
        "payload",
        "sealed_execution",
        "response_sha256",
        "observation_sha256",
    }


def _is_canonical_observed_at(value: Any) -> bool:
    if not isinstance(value, str) or _OBSERVED_AT_RE.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value


def _parse_observed_at(value: Any, error_code: str) -> datetime:
    if not _is_canonical_observed_at(value):
        _fail(error_code)
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _valid_provenance_binding(
    value: Mapping[str, Any],
    *,
    verified_at: datetime,
    maximum_age: timedelta,
    session: AzurePerformanceInfrastructureReadbackSession,
) -> bool:
    if not _is_canonical_observed_at(value.get("observed_at_utc")):
        return False
    observed_at = datetime.strptime(
        value["observed_at_utc"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=UTC)
    age = verified_at - observed_at
    attestation = value.get("execution_attestation")
    return (
        -_MAX_FUTURE_SKEW <= age <= maximum_age
        and observed_at
        >= _parse_observed_at(session.created_at_utc, "READBACK_SESSION_INVALID")
        - _MAX_FUTURE_SKEW
        and _sealed_observation_matches(value, session=session)
        and value.get("toolchain_attestations_sha256")
        == session.toolchain_attestations_sha256
        and value.get("readback_session_sha256") == session.session_sha256
        and value.get("readback_nonce") == session.nonce
        and attestation == readback_session_attestation(session)
        and _sha256_json(attestation)
        == session.execution_attestation_sha256
    )


def _valid_readback_capability(value: Any) -> bool:
    return _authenticate_readback_capability(value)


def _require_readback_capability(
    value: (
        AzurePerformanceInfrastructureReadbackSession
        | AzurePerformanceInfrastructureReadbackCapability
    ),
) -> AzurePerformanceInfrastructureReadbackCapability:
    if type(value) is not AzurePerformanceInfrastructureReadbackCapability:
        _fail("READBACK_SESSION_CAPABILITY_INVALID")
    capability = value
    if not _valid_readback_capability(capability):
        _fail("READBACK_SESSION_CAPABILITY_INVALID")
    return capability


def _require_adapter_results(
    capability: AzurePerformanceInfrastructureReadbackCapability,
    *values: Mapping[str, Any],
) -> None:
    if any(
        not _authenticate_readback_result(value, capability)
        for value in values
    ):
        _fail("SEALED_READBACK_CAPABILITY_INVALID")


def _envelope_observed_at(value: Mapping[str, Any]) -> datetime:
    return _parse_observed_at(value.get("observed_at_utc"), "OBSERVED_AT_INVALID")


def _claim_readback_session(
    session: AzurePerformanceInfrastructureReadbackSession,
) -> datetime:
    verified_at = _trusted_now()
    created_at = _validate_readback_session_integrity(
        session, check_execution_identity=True
    )
    if not (-_MAX_FUTURE_SKEW <= verified_at - created_at <= _MAX_SESSION_AGE):
        _fail("READBACK_SESSION_EXPIRED")
    _record_readback_session_claim(session)
    return verified_at


def _validate_readback_session_integrity(
    session: AzurePerformanceInfrastructureReadbackSession,
    *,
    check_execution_identity: bool,
) -> datetime:
    if not isinstance(session, AzurePerformanceInfrastructureReadbackSession):
        _fail("READBACK_SESSION_INVALID")
    sha_values = (
        session.owner_binding_sha256,
        session.toolchain_attestations_sha256,
        session.nonce_sha256,
        session.executable_path_sha256,
        session.executable_sha256,
        session.argv_sha256,
        session.session_sha256,
        session.execution_attestation_sha256,
    )
    if (
        any(
            not isinstance(item, str) or _SHA256_RE.fullmatch(item) is None
            for item in sha_values
        )
        or not isinstance(session.nonce, str)
        or _NONCE_RE.fullmatch(session.nonce) is None
        or hashlib.sha256(session.nonce.encode("ascii")).hexdigest()
        != session.nonce_sha256
    ):
        _fail("READBACK_SESSION_INVALID")
    attestation = readback_session_attestation(session)
    session_payload = dict(attestation)
    session_payload.pop("readback_session_sha256")
    if (
        _sha256_json(session_payload) != session.session_sha256
        or _sha256_json(attestation) != session.execution_attestation_sha256
    ):
        _fail("READBACK_SESSION_INVALID")
    if check_execution_identity and _capture_execution_identity() != {
        "executable_path_sha256": session.executable_path_sha256,
        "executable_sha256": session.executable_sha256,
        "argv_sha256": session.argv_sha256,
    }:
        _fail("READBACK_EXECUTION_ATTESTATION_MISMATCH")
    return _parse_observed_at(session.created_at_utc, "READBACK_SESSION_INVALID")


def _record_readback_session_claim(
    session: AzurePerformanceInfrastructureReadbackSession,
) -> None:
    directory = _open_private_replay_ledger_directory()
    descriptor = -1
    name = f"{session.nonce_sha256}.json"
    record = _canonical_json_bytes(
        {
            "nonce_sha256": session.nonce_sha256,
            "readback_session_sha256": session.session_sha256,
            "schema_version": READBACK_SESSION_SCHEMA,
        }
    ) + b"\n"
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=directory,
        )
    except FileExistsError:
        os.close(directory)
        _fail("READBACK_SESSION_REPLAYED")
    except OSError:
        os.close(directory)
        _fail("READBACK_REPLAY_LEDGER_INVALID")
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
        ):
            _fail("READBACK_REPLAY_LEDGER_INVALID")
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(record)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(directory)
    except OSError:
        _fail("READBACK_REPLAY_LEDGER_INVALID")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(directory)


def _open_private_replay_ledger_directory() -> int:
    path = _READBACK_REPLAY_LEDGER_DIRECTORY
    if not isinstance(path, Path) or not path.is_absolute() or ".." in path.parts:
        _fail("READBACK_REPLAY_LEDGER_INVALID")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        descriptor = os.open("/", flags)
        for index, part in enumerate(path.parts[1:]):
            try:
                child = os.open(part, flags, dir_fd=descriptor)
            except FileNotFoundError:
                parent = os.fstat(descriptor)
                if (
                    parent.st_uid != os.geteuid()
                    or stat.S_IMODE(parent.st_mode) & 0o022
                ):
                    raise OSError
                os.mkdir(part, 0o700, dir_fd=descriptor)
                child = os.open(part, flags, dir_fd=descriptor)
            metadata = os.fstat(child)
            mode = stat.S_IMODE(metadata.st_mode)
            is_final = index == len(path.parts[1:]) - 1
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or (
                    mode & 0o022
                    and not mode & stat.S_ISVTX
                )
                or (
                    is_final
                    and (metadata.st_uid != os.geteuid() or mode != 0o700)
                )
            ):
                os.close(child)
                raise OSError
            os.close(descriptor)
            descriptor = child
        return descriptor
    except OSError:
        try:
            os.close(descriptor)
        except (OSError, UnboundLocalError):
            pass
        _fail("READBACK_REPLAY_LEDGER_INVALID")


def _sealed_observation_matches(
    value: Mapping[str, Any],
    *,
    session: AzurePerformanceInfrastructureReadbackSession,
) -> bool:
    digest = value.get("observation_sha256")
    command_sha256 = value.get("observation_command_sha256")
    execution = value.get("sealed_execution")
    response_sha256 = value.get("response_sha256")
    if (
        not isinstance(digest, str)
        or not isinstance(command_sha256, str)
        or not isinstance(execution, Mapping)
        or set(execution) != _SEALED_EXECUTION_KEYS
        or execution.get("schema_version") != SEALED_AZURE_READ_SCHEMA
        or not isinstance(execution.get("operations"), list)
        or not execution["operations"]
        or not isinstance(response_sha256, str)
        or _SHA256_RE.fullmatch(response_sha256) is None
    ):
        return False
    operations = execution["operations"]
    if value.get("observation_kind") == "effective-rbac-abac":
        if any(
            not _valid_sealed_operation(item)
            for item in operations
        ):
            return False
        measured_response_sha256 = hashlib.sha256(
            _canonical_json_bytes([item["response_sha256"] for item in operations])
        ).hexdigest()
        if response_sha256 != measured_response_sha256:
            return False
        expected = _effective_rbac_payload_from_operations(value, operations)
        operation = None
    else:
        if len(operations) != 1 or not _valid_sealed_operation(
            operations[0],
            response_sha256=response_sha256,
        ):
            return False
        operation = operations[0]
        expected = _expected_operation_for_envelope(value, operation)
    envelope_api_version = value.get("api_version")
    if (
        isinstance(envelope_api_version, str)
        and operation is not None
        and operation["api_version"] != envelope_api_version
    ):
        return False
    if expected is None:
        return False
    expected_command = _sha256_json(
        {
            "schema_version": SEALED_AZURE_READ_SCHEMA,
            "observation_kind": value.get("observation_kind"),
            "readback_session_sha256": session.session_sha256,
            "nonce_sha256": session.nonce_sha256,
            "execution_attestation_sha256": session.execution_attestation_sha256,
            "sealed_execution": execution,
        }
    )
    return command_sha256 == expected_command and value.get("payload") == expected


def _valid_sealed_operation(
    operation: Any,
    *,
    response_sha256: str | None = None,
    capability: AzurePerformanceInfrastructureReadbackCapability | None = None,
) -> bool:
    if not isinstance(operation, Mapping) or set(operation) != _SEALED_OPERATION_KEYS:
        return False
    argv = operation.get("argv")
    environment = operation.get("environment")
    raw = operation.get("raw_response_base64")
    if (
        not isinstance(argv, list)
        or any(not isinstance(item, str) or not item for item in argv)
        or any(
            not isinstance(operation.get(key), str)
            or _SHA256_RE.fullmatch(operation[key]) is None
            for key in (
                "executable_path_sha256",
                "executable_sha256",
                "argv_sha256",
                "environment_sha256",
                "response_sha256",
            )
        )
        or (
            response_sha256 is not None
            and operation.get("response_sha256") != response_sha256
        )
        or operation.get("argv_sha256")
        != hashlib.sha256(_canonical_json_bytes(argv)).hexdigest()
        or not Path(argv[0]).is_absolute()
        or operation.get("executable_path_sha256")
        != hashlib.sha256(os.fsencode(argv[0])).hexdigest()
        or (
            capability is not None
            and (
                operation.get("executable_path_sha256")
                != capability.executable_path_sha256
                or operation.get("executable_sha256")
                != capability.executable_sha256
            )
        )
        or not isinstance(environment, Mapping)
        or set(environment)
        != {
            "AZURE_CONFIG_DIR",
            "AZURE_CORE_COLLECT_TELEMETRY",
            "HOME",
            "LANG",
            "LC_ALL",
            "PATH",
            "PYTHONNOUSERSITE",
            "PYTHONSAFEPATH",
        }
        or environment.get("AZURE_CORE_COLLECT_TELEMETRY") != "no"
        or environment.get("LANG") != "C.UTF-8"
        or environment.get("LC_ALL") != "C.UTF-8"
        or environment.get("PYTHONNOUSERSITE") != "1"
        or environment.get("PYTHONSAFEPATH") != "1"
        or environment.get("PATH")
        != "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        or not Path(str(environment.get("HOME", ""))).is_absolute()
        or not Path(str(environment.get("AZURE_CONFIG_DIR", ""))).is_absolute()
        or any(not isinstance(item, str) or not item for item in environment.values())
        or operation.get("environment_sha256")
        != hashlib.sha256(_canonical_json_bytes(environment)).hexdigest()
        or not isinstance(raw, str)
    ):
        return False
    try:
        response_bytes = base64.b64decode(raw, validate=True)
    except (ValueError, TypeError):
        return False
    return hashlib.sha256(response_bytes).hexdigest() == operation["response_sha256"]


def _expected_operation_for_envelope(
    value: Mapping[str, Any], operation: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    try:
        response_bytes = base64.b64decode(
            operation["raw_response_base64"], validate=True
        )
        response = _decode_azure_json_response(response_bytes)
    except AzurePerformanceInfrastructureSafetyError:
        return None
    kind = value.get("observation_kind")
    api_version = operation.get("api_version")
    resource_id = operation.get("resource_id")
    argv = operation.get("argv")
    method = "post" if kind == "coordination-storage-name-availability" else "get"
    if not isinstance(resource_id, str) or not resource_id.startswith("/"):
        return None
    url = f"https://management.azure.com{resource_id}?api-version={api_version}"
    if kind == "subscription-management-group-ancestry":
        url += "&$expand=children&$recurse=true"
    expected_argv = [
        argv[0] if isinstance(argv, list) and argv else "",
        "rest", "--method", method, "--url", url,
    ]
    if kind == "coordination-storage-name-availability":
        payload = value.get("payload")
        if not isinstance(payload, Mapping):
            return None
        body = _canonical_json_bytes(
            {"name": payload.get("name"), "type": "Microsoft.Storage/storageAccounts"}
        ).decode("ascii")
        expected_argv.extend(["--body", body])
    expected_argv.extend(["--only-show-errors", "--output", "json"])
    if argv != expected_argv:
        return None
    if kind in {"bff-storage-account-resource-id", "worm-storage-account-resource-id"}:
        return {"resource_id": response.get("id")}
    if kind in {"coordination-role-definition", "coordination-role-assignment"}:
        return {"resource": response}
    if kind == "coordination-storage-account-configuration":
        return _storage_configuration_payload(response)
    if kind == "coordination-blob-service-configuration":
        return _blob_service_configuration_payload(response)
    if kind == "coordination-lease-container-configuration":
        return _lease_container_configuration_payload(response)
    if kind == "coordination-deployment-receipt":
        return _deployment_receipt_payload(response)
    if kind == "coordination-storage-name-availability":
        return {
            "name": value["payload"].get("name"),
            "name_available": response.get("nameAvailable"),
        }
    if kind == "subscription-management-group-ancestry":
        attestation = value.get("execution_attestation")
        payload = value.get("payload")
        if not isinstance(attestation, Mapping) or not isinstance(payload, Mapping):
            return None
        return _management_group_ancestry_payload(
            response,
            tenant_id=str(payload.get("tenant_id")),
            subscription_id=str(payload.get("subscription_id")),
        )
    return None


def _effective_rbac_payload_from_operations(
    value: Mapping[str, Any], operations: list[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    payload = value.get("payload")
    if not isinstance(payload, Mapping):
        return None
    principal = payload.get("principal_id")
    scopes = payload.get("ancestor_scopes")
    target = payload.get("target_resource_id")
    if (
        not isinstance(principal, str)
        or not isinstance(target, str)
        or not isinstance(scopes, list)
        or not scopes
    ):
        return None
    try:
        principal = _canonical_uuid(principal, "EFFECTIVE_RBAC_READBACK_INVALID")
    except AzurePerformanceInfrastructureSafetyError:
        return None

    def decoded(operation: Mapping[str, Any]) -> dict[str, Any] | None:
        try:
            return _decode_azure_json_response(
                base64.b64decode(operation["raw_response_base64"], validate=True)
            )
        except AzurePerformanceInfrastructureSafetyError:
            return None

    index = 0
    graph_resource = (
        f"/servicePrincipals/{principal}/transitiveMemberOf/"
        "microsoft.graph.group?$select=id"
    )
    graph_url = f"https://graph.microsoft.com/v1.0{graph_resource}"
    if not _operation_is_exact_get(
        operations[index], graph_url, MICROSOFT_GRAPH_API_VERSION, graph_resource
    ):
        return None
    graph = decoded(operations[index])
    index += 1
    if graph is None or set(graph) - {"value", "@odata.context"}:
        return None
    graph_values = graph.get("value")
    if not isinstance(graph_values, list):
        return None
    try:
        groups = sorted(
            _canonical_uuid(item.get("id"), "EFFECTIVE_PRINCIPAL_EXPANSION_INVALID")
            for item in graph_values
            if isinstance(item, Mapping)
        )
    except AzurePerformanceInfrastructureSafetyError:
        return None
    if len(groups) != len(graph_values):
        return None
    relevant = {principal, *groups}
    assignments: list[dict[str, Any]] = []
    pending: list[tuple[dict[str, Any], str, str]] = []
    for scope in scopes:
        if index >= len(operations) or not isinstance(scope, str):
            return None
        prefix = "" if scope == "/" else scope
        resource = f"{prefix}/providers/Microsoft.Authorization/roleAssignments"
        url = (
            f"https://management.azure.com{resource}"
            f"?api-version={AUTHORIZATION_API_VERSION}&$filter=atScope()"
        )
        if not _operation_is_exact_get(
            operations[index], url, AUTHORIZATION_API_VERSION, resource
        ):
            return None
        response = decoded(operations[index])
        index += 1
        if (
            response is None
            or set(response) - {"value"}
            or not isinstance(response.get("value"), list)
        ):
            return None
        for item in response["value"]:
            if not isinstance(item, Mapping):
                return None
            properties = item.get("properties")
            if (
                not isinstance(properties, Mapping)
            ):
                return None
            try:
                candidate_principal = _canonical_uuid(
                    properties.get("principalId"), "EFFECTIVE_ASSIGNMENTS_INVALID"
                )
            except AzurePerformanceInfrastructureSafetyError:
                return None
            if candidate_principal not in relevant:
                continue
            role_id = properties.get("roleDefinitionId")
            if not isinstance(role_id, str):
                return None
            pending.append((dict(item), scope, role_id))
    role_cache: dict[str, dict[str, Any]] = {}
    for item, scope, role_id in pending:
        key = role_id.casefold()
        if key not in role_cache:
            if index >= len(operations):
                return None
            url = (
                f"https://management.azure.com{role_id}"
                f"?api-version={AUTHORIZATION_API_VERSION}"
            )
            if not _operation_is_exact_get(
                operations[index], url, AUTHORIZATION_API_VERSION, role_id
            ):
                return None
            role = decoded(operations[index])
            index += 1
            if role is None:
                return None
            role_cache[key] = role
        item["scope"] = scope
        item["roleDefinition"] = role_cache[key]
        assignments.append(item)
    if index != len(operations):
        return None
    return {
        "target_resource_id": target,
        "principal_id": principal,
        "transitive_group_principal_ids": groups,
        "ancestor_scopes": scopes,
        "effective_role_assignments": assignments,
        "completeness_attestation": {
            "root_ancestry_complete": True,
            "management_group_ancestry_complete": True,
            "transitive_group_membership_complete": True,
            "role_assignments_complete": True,
            "role_definitions_expanded": True,
        },
    }


def _operation_is_exact_get(
    operation: Mapping[str, Any], url: str, api_version: str, resource_id: str
) -> bool:
    argv = operation.get("argv")
    return (
        isinstance(argv, list)
        and len(argv) == 9
        and argv[1:] == [
            "rest", "--method", "get", "--url", url,
            "--only-show-errors", "--output", "json",
        ]
        and operation.get("api_version") == api_version
        and operation.get("resource_id") == resource_id
    )


def _fresh_evidence_timestamp(value: Any) -> bool:
    if not _is_canonical_observed_at(value):
        return False
    verified_at = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=UTC
    )
    age = _trusted_now() - verified_at
    return -_MAX_FUTURE_SKEW <= age <= _POSTDEPLOY_MAX_AGE


def _capture_execution_identity() -> dict[str, str]:
    executable = Path(sys.executable).expanduser().resolve(strict=True)
    executable_bytes = executable.read_bytes()
    argv = [os.fsdecode(argument) for argument in sys.argv]
    return {
        "executable_path_sha256": hashlib.sha256(
            os.fsencode(str(executable))
        ).hexdigest(),
        "executable_sha256": hashlib.sha256(executable_bytes).hexdigest(),
        "argv_sha256": hashlib.sha256(
            json.dumps(
                argv,
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("ascii")
        ).hexdigest(),
    }


def _trusted_now() -> datetime:
    return datetime.now(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def canonical_observation_command_sha256(
    observation_kind: str,
    *,
    session: AzurePerformanceInfrastructureReadbackSession,
) -> str:
    if not isinstance(observation_kind, str) or not observation_kind:
        raise TypeError("observation_kind")
    if not isinstance(session, AzurePerformanceInfrastructureReadbackSession):
        raise TypeError("session")
    return _sha256_json(
        {
            "schema_version": "nac.azure-sealed-readback-command/v2",
            "observation_kind": observation_kind,
            "readback_session_sha256": session.session_sha256,
            "nonce_sha256": session.nonce_sha256,
            "execution_attestation_sha256": (
                session.execution_attestation_sha256
            ),
            "executable_sha256": session.executable_sha256,
            "argv_sha256": session.argv_sha256,
        }
    )


def _canonical_tags(value: Any) -> dict[str, str]:
    if (
        not isinstance(value, Mapping)
        or any(
            not isinstance(key, str)
            or not key
            or not isinstance(item, str)
            or not item
            for key, item in value.items()
        )
    ):
        _fail("TAGS_INVALID")
    return {key: value[key] for key in sorted(value)}


def _exact_data_actions(value: Any) -> frozenset[str] | None:
    actions = _data_actions(value)
    if actions is None or not isinstance(value, list) or len(value) != len(actions):
        return None
    return actions


def _data_actions(value: Any) -> frozenset[str] | None:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item for item in value)
    ):
        return None
    return frozenset(value)


def _properties(value: Any, error_code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(error_code)
    properties = value.get("properties", value)
    if not isinstance(properties, Mapping):
        _fail(error_code)
    return properties


def _field(
    value: Mapping[str, Any], properties: Mapping[str, Any], name: str
) -> Any:
    return value[name] if name in value else properties.get(name)


def _storage_account_id(value: Any) -> dict[str, str]:
    if not isinstance(value, str):
        _fail("STORAGE_ACCOUNT_RESOURCE_ID_INVALID")
    match = _STORAGE_ACCOUNT_ID_RE.fullmatch(value)
    if match is None:
        _fail("STORAGE_ACCOUNT_RESOURCE_ID_INVALID")
    name = match.group("name")
    if _STORAGE_ACCOUNT_NAME_RE.fullmatch(name) is None:
        _fail("STORAGE_ACCOUNT_RESOURCE_ID_INVALID")
    subscription = _canonical_uuid(
        match.group("subscription"), "STORAGE_ACCOUNT_RESOURCE_ID_INVALID"
    )
    resource_group = match.group("resource_group")
    canonical = (
        f"/subscriptions/{subscription}/resourceGroups/{resource_group}/providers/"
        f"Microsoft.Storage/storageAccounts/{name}"
    )
    return {
        "id": canonical,
        "subscription": subscription,
        "resource_group": resource_group,
        "name": name,
    }


def _require_arm_id(value: Any, error_code: str) -> str:
    if not isinstance(value, str) or not value.startswith("/") or value.endswith("/"):
        _fail(error_code)
    return value


def _canonical_uuid(value: Any, error_code: str) -> str:
    if not isinstance(value, str):
        _fail(error_code)
    try:
        return str(UUID(value))
    except ValueError:
        _fail(error_code)


def _require_sha256(value: Any) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        _fail("TARGET_BINDING_INVALID")


def _require_named_sha256(value: Any, error_code: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        _fail(error_code)


def _sha256_json(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _fail(error_code: str) -> None:
    raise AzurePerformanceInfrastructureSafetyError(error_code)


verify_performance_coordination_infrastructure_safety = (
    verify_azure_performance_infrastructure_safety
)


__all__ = [
    "ALLOWED_DATA_ACTIONS",
    "AzurePerformanceInfrastructureReadbackAdapter",
    "AzurePerformanceInfrastructureReadbackCapability",
    "AzurePerformanceInfrastructureReadbackResult",
    "AzurePerformanceInfrastructureReadbackSession",
    "AzurePerformanceInfrastructureSafetyVerification",
    "AzurePerformanceInfrastructureSafetyError",
    "CONTAINER_NAME",
    "MANDATORY_COORDINATION_TAGS",
    "begin_azure_performance_infrastructure_readback_session",
    "canonical_observation_command_sha256",
    "canonical_observation_sha256",
    "effective_coordination_tags",
    "exact_lease_blob_condition",
    "infrastructure_safety_policy_sha256",
    "readback_session_attestation",
    "validate_infrastructure_safety_evidence",
    "verify_azure_performance_infrastructure_safety",
    "verify_performance_coordination_infrastructure_safety",
]
