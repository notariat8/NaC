"""Owner-bound production ports for the performance infrastructure sequence.

The ports in this module never invoke a process directly.  Deployment commands
can use :class:`AzureCliAdapter` through the adapter below.  The exact ARM GET
commands are deliberately exposed as sealed command objects because the current
Azure CLI allowlist does not admit their resource IDs.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from types import MappingProxyType
from typing import Any, Iterator, Protocol

from .azure_activation import RESOURCE_GROUP, SUBSCRIPTION_ID, TENANT_ID
from .azure_live_commands import AzureCliAdapter, EXPECTED_CLOUD_NAME
from .azure_performance_acceptance import (
    OWNER_ACTION,
    PerformanceExecutionAuthorization,
    build_owner_comment,
    build_performance_acceptance_plan,
)
from .azure_performance_infrastructure_safety import (
    ALLOWED_DATA_ACTIONS,
    CONTAINER_NAME,
    effective_coordination_tags,
)


DEPLOYMENT_SEQUENCE = (
    "deploy_unlocked_worm_baseline",
    "verify_worm_baseline_readback",
    "deploy_performance_coordination",
    "verify_coordination_and_effective_rbac",
    "bootstrap_exact_zero_byte_lease_blob",
    "execute_endpoint_scoped_conservative_measurement",
    "release_lease_and_finalize_redacted_evidence",
)
WORM_TEMPLATE_RELATIVE_PATH = Path(
    "deploy/runtime/azure/immutable-evidence/compiled/main.json"
)
COORDINATION_TEMPLATE_RELATIVE_PATH = Path(
    "deploy/runtime/azure/nac-bff-performance-coordination/compiled/main.json"
)
DEPLOYMENT_API_VERSION = "2022-09-01"
STORAGE_API_VERSION = "2023-05-01"
_ARM_PARAMETERS_SCHEMA = (
    "https://schema.management.azure.com/schemas/"
    "2019-04-01/deploymentParameters.json#"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DEPLOYMENT_NAME_RE = re.compile(r"^nac-bff-[0-9a-f]{12}$")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_OWNER_HEADER = "NAC_BFF_PERFORMANCE_ACCEPTANCE_APPROVAL\n"
_WORM_OUTPUT_KEYS = frozenset(
    {
        "offlineStatus",
        "liveStatus",
        "lockActionStatus",
        "lockTargetResourceId",
        "configuredContainerName",
        "configuredEncryptionScope",
        "providerContextBindingSource",
        "cmkIdentityResourceId",
        "writerIdentityResourceId",
        "writerDataRoleDefinitionId",
        "writerManagementReadRoleDefinitionId",
        "deploymentScopeBinding",
        "deploymentModeBinding",
    }
)
_COORDINATION_OUTPUT_KEYS = frozenset(
    {
        "contractSchemaVersion",
        "storageAccountName",
        "storageAccountResourceId",
        "effectiveTags",
        "bffStorageAccountResourceIdBinding",
        "bffStorageAccountNameBinding",
        "wormStorageAccountResourceIdBinding",
        "wormStorageAccountNameBinding",
        "leaseContainerName",
        "leaseContainerResourceId",
        "leaseBlobPath",
        "leaseBlobUri",
        "requiredLeaseBlobType",
        "requiredLeaseBlobContentLength",
        "targetBindingSha256",
        "leaseDataRoleDefinitionId",
        "provisionerLeaseRoleAssignmentId",
        "exactLeaseBlobCondition",
        "allowedDataActions",
        "deploymentScopeBinding",
        "blobBootstrapRequired",
        "blobBootstrapExecutedByTemplate",
        "azureRbacWriteAuthorizedOperations",
        "azureRbacOperationRestrictionEnforced",
        "operationRestrictionDefenseInDepth",
        "principalSeparationMode",
    }
)


class AzurePerformanceInfrastructurePortError(ValueError):
    """Stable, redacted failure raised before returning provider details."""


@dataclass(frozen=True, slots=True)
class BoundAzureArtifact:
    argument: str
    path: Path
    sha256: str


_COMMAND_SEAL = object()
_ISSUED_COMMANDS: dict[int, "BoundAzureCliCommand"] = {}


@dataclass(frozen=True, slots=True, init=False)
class BoundAzureCliCommand:
    """An exact argv/artifact binding issued by one of the ports below."""

    operation: str
    argv: tuple[str, ...]
    argv_sha256: str
    artifacts: tuple[BoundAzureArtifact, ...]
    read_only: bool
    timeout_seconds: float
    _seal: object

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("bound Azure commands are issued by infrastructure ports")

    def _assert_issued(self) -> None:
        if (
            self._seal is not _COMMAND_SEAL
            or _ISSUED_COMMANDS.get(id(self)) is not self
            or self.argv_sha256 != _sha256_json(list(self.argv))
            or any(
                _SHA256_RE.fullmatch(artifact.sha256) is None
                or artifact.argument not in self.argv
                and f"@{artifact.argument}" not in self.argv
                for artifact in self.artifacts
            )
        ):
            _fail("AZURE_INFRASTRUCTURE_COMMAND_BINDING_INVALID")


class BoundAzureCommandExecutor(Protocol):
    """Sealed execution boundary required by the infrastructure ports."""

    def execute(self, command: BoundAzureCliCommand) -> Mapping[str, Any]: ...


class ExactAzureRestCommandExecutor(Protocol):
    """Integration point for exact REST argv on the sealed Azure CLI runtime."""

    def execute_exact_rest(
        self, command: BoundAzureCliCommand
    ) -> Mapping[str, Any]: ...


class AzureCliPerformanceInfrastructureCommandExecutor:
    """Use AzureCliAdapter where its sealed allowlist is already sufficient."""

    def __init__(
        self,
        azure_cli: AzureCliAdapter,
        *,
        exact_rest_executor: ExactAzureRestCommandExecutor | None = None,
    ) -> None:
        if not isinstance(azure_cli, AzureCliAdapter):
            raise TypeError("azure_cli")
        self._azure_cli = azure_cli
        self._exact_rest_executor = exact_rest_executor

    def execute(self, command: BoundAzureCliCommand) -> Mapping[str, Any]:
        command._assert_issued()
        if command.argv[:2] == ("deployment", "group"):
            if command.read_only or len(command.artifacts) != 2:
                _fail("AZURE_INFRASTRUCTURE_COMMAND_BINDING_INVALID")
            bindings = {
                artifact.argument: (artifact.path, artifact.sha256)
                for artifact in command.artifacts
            }
            return self._azure_cli.run_bound_with_timeout(
                list(command.argv),
                bindings,
                timeout_seconds=command.timeout_seconds,
            )
        if command.argv[:2] == ("account", "show"):
            if not command.read_only or command.artifacts:
                _fail("AZURE_INFRASTRUCTURE_COMMAND_BINDING_INVALID")
            return self._azure_cli.run_with_timeout(
                list(command.argv), timeout_seconds=command.timeout_seconds
            )
        if command.argv[:1] == ("rest",):
            if not command.read_only or command.artifacts:
                _fail("AZURE_INFRASTRUCTURE_COMMAND_BINDING_INVALID")
            if self._exact_rest_executor is None:
                _fail("AZURE_EXACT_REST_BOUNDARY_INTEGRATION_REQUIRED")
            return self._exact_rest_executor.execute_exact_rest(command)
        _fail("AZURE_INFRASTRUCTURE_COMMAND_BLOCKED")


@dataclass(slots=True)
class _AuthorityState:
    repo_root: Path
    owner_binding_sha256: str
    target_binding_sha256: str
    infrastructure_approval: Mapping[str, str]
    infrastructure_parameters: Mapping[str, Any]
    worm_parameters: Mapping[str, Any]
    worm_template_sha256: str
    coordination_template_sha256: str
    next_stage: int = 0
    inflight_stage: str | None = None
    terminal: bool = False


_AUTHORITY_SEAL = object()
_AUTHORITY_LOCK = threading.RLock()
_ISSUED_AUTHORITIES: dict[int, "OwnerBoundInfrastructureDeploymentAuthority"] = {}
_AUTHORITY_STATES: dict[int, _AuthorityState] = {}


@dataclass(frozen=True, slots=True, init=False)
class OwnerBoundInfrastructureDeploymentAuthority:
    """Opaque, one-way authority for the exact approved infrastructure sequence."""

    _seal: object

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("deployment authorities are issued by owner verification")

    def __copy__(self) -> None:
        raise TypeError("deployment authorities cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> None:
        raise TypeError("deployment authorities cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("deployment authorities cannot be serialized")

    @classmethod
    def issue_for_exact_sequence(
        cls,
        *,
        repo_root: Path,
        authorization: PerformanceExecutionAuthorization,
        owner_comment_body: str,
        infrastructure_approval: Mapping[str, str],
        toolchain_attestations: Mapping[str, str],
        infrastructure_parameters: Mapping[str, Any],
        worm_baseline_parameters: Mapping[str, Any],
    ) -> "OwnerBoundInfrastructureDeploymentAuthority":
        """Re-measure and bind the canonical owner comment without live access."""

        try:
            if type(authorization) is not PerformanceExecutionAuthorization:
                raise ValueError
            authorization._assert_issued()
            if (
                not isinstance(owner_comment_body, str)
                or not owner_comment_body.startswith(_OWNER_HEADER)
                or _sha256_text(owner_comment_body)
                != authorization.owner_approval_body_sha256
            ):
                raise ValueError
            payload = json.loads(owner_comment_body[len(_OWNER_HEADER) :])
            if (
                not isinstance(payload, Mapping)
                or payload.get("action") != OWNER_ACTION
                or payload.get("required_owner_login") != authorization.owner_login
                or payload.get("deployment_sequence_sha256")
                != infrastructure_approval.get("deployment_sequence_sha256")
                or payload.get("target_binding_sha256")
                != authorization.target_binding_sha256
            ):
                raise ValueError

            plan = build_performance_acceptance_plan(
                authorization.activation_hash, authorization.contract_sha256
            )
            authorization.validate(plan=plan)
            expected_comment = build_owner_comment(
                authorization.contract_sha256,
                authorization.activation_hash,
                authorization.correlation_id,
                infrastructure_approval,
                str(payload.get("monitor_window_anchor_utc")),
            )
            if expected_comment.get("body") != owner_comment_body:
                raise ValueError

            from .azure_performance_owner_gate import (
                _validate_worm_parameters,
                measure_performance_infrastructure_approval,
            )

            measurement = measure_performance_infrastructure_approval(
                repo_root,
                expected_activation_hash=authorization.activation_hash,
                toolchain_attestations=toolchain_attestations,
                infrastructure_parameters=infrastructure_parameters,
                worm_baseline_parameters=worm_baseline_parameters,
            )
            measured_approval = measurement.get("infrastructure_approval")
            if (
                measurement.get("contract_sha256") != authorization.contract_sha256
                or not isinstance(measured_approval, Mapping)
                or dict(measured_approval) != dict(infrastructure_approval)
                or any(payload.get(key) != value for key, value in measured_approval.items())
            ):
                raise ValueError
            parameters = measurement.get("parameters")
            worm_parameters = _validate_worm_parameters(worm_baseline_parameters)
            if not isinstance(parameters, Mapping):
                raise ValueError
            expected_sequence = _sha256_json(
                {
                    "infrastructure_binding_sha256": measured_approval[
                        "infrastructure_binding_sha256"
                    ],
                    "sequence": list(DEPLOYMENT_SEQUENCE),
                    "worm_baseline_binding_sha256": measured_approval[
                        "worm_baseline_binding_sha256"
                    ],
                }
            )
            if measured_approval["deployment_sequence_sha256"] != expected_sequence:
                raise ValueError

            root = repo_root.expanduser().resolve(strict=True)
            worm_template = _bound_repo_file(root, WORM_TEMPLATE_RELATIVE_PATH)
            coordination_template = _bound_repo_file(
                root, COORDINATION_TEMPLATE_RELATIVE_PATH
            )
            worm_digest = _sha256_file(worm_template)
            coordination_digest = _sha256_file(coordination_template)
            if worm_digest != measured_approval["worm_baseline_compiled_arm_sha256"]:
                raise ValueError
            _validate_pairwise_storage_bindings(parameters, worm_parameters)
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            _fail("OWNER_BOUND_INFRASTRUCTURE_AUTHORITY_INVALID")

        authority = object.__new__(cls)
        object.__setattr__(authority, "_seal", _AUTHORITY_SEAL)
        state = _AuthorityState(
            repo_root=root,
            owner_binding_sha256=authorization.owner_approval_body_sha256,
            target_binding_sha256=authorization.target_binding_sha256,
            infrastructure_approval=MappingProxyType(dict(measured_approval)),
            infrastructure_parameters=MappingProxyType(_deep_copy(parameters)),
            worm_parameters=MappingProxyType(_deep_copy(worm_parameters)),
            worm_template_sha256=worm_digest,
            coordination_template_sha256=coordination_digest,
        )
        with _AUTHORITY_LOCK:
            _ISSUED_AUTHORITIES[id(authority)] = authority
            _AUTHORITY_STATES[id(authority)] = state
        return authority

    def _begin(self, stage: str) -> _AuthorityState:
        with _AUTHORITY_LOCK:
            state = _authority_state(self)
            if (
                state.terminal
                or state.inflight_stage is not None
                or state.next_stage >= 3
                or DEPLOYMENT_SEQUENCE[state.next_stage] != stage
            ):
                state.terminal = True
                _fail("INFRASTRUCTURE_DEPLOYMENT_SEQUENCE_INVALID")
            state.inflight_stage = stage
            return state

    def _finish(self, stage: str) -> None:
        with _AUTHORITY_LOCK:
            state = _authority_state(self)
            if state.terminal or state.inflight_stage != stage:
                state.terminal = True
                _fail("INFRASTRUCTURE_DEPLOYMENT_SEQUENCE_INVALID")
            state.inflight_stage = None
            state.next_stage += 1

    def _abort(self) -> None:
        with _AUTHORITY_LOCK:
            state = _authority_state(self)
            state.terminal = True
            state.inflight_stage = None


_RECEIPT_SEAL = object()
_WORM_RECEIPTS: dict[int, "UnlockedWormBaselineDeploymentReceipt"] = {}
_WORM_READBACKS: dict[int, "VerifiedUnlockedWormBaseline"] = {}
_COORDINATION_RECEIPTS: dict[int, "PerformanceCoordinationDeploymentReceipt"] = {}


@dataclass(frozen=True, slots=True, init=False)
class UnlockedWormBaselineDeploymentReceipt:
    owner_binding_sha256: str
    deployment_receipt_sha256: str
    outputs_sha256: str
    _authority_id: int
    _seal: object

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("WORM deployment receipts are issued by the deployment port")


@dataclass(frozen=True, slots=True, init=False)
class VerifiedUnlockedWormBaseline:
    owner_binding_sha256: str
    worm_baseline_binding_sha256: str
    readback_sha256: str
    policy_state: str
    _authority_id: int
    _seal: object

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("WORM verifications are issued by the readback port")


@dataclass(frozen=True, slots=True, init=False)
class PerformanceCoordinationDeploymentReceipt:
    owner_binding_sha256: str
    deployment_receipt_sha256: str
    outputs_sha256: str
    coordination_storage_account_resource_id: str
    lease_container_resource_id: str
    lease_data_role_definition_id: str
    provisioner_lease_role_assignment_id: str
    _authority_id: int
    _seal: object

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("coordination receipts are issued by the deployment port")


class UnlockedWormBaselineDeploymentPort:
    def __init__(self, command_executor: BoundAzureCommandExecutor) -> None:
        self._executor = command_executor

    def deploy(
        self, authority: OwnerBoundInfrastructureDeploymentAuthority
    ) -> UnlockedWormBaselineDeploymentReceipt:
        stage = DEPLOYMENT_SEQUENCE[0]
        state = authority._begin(stage)
        try:
            template = _bound_repo_file(state.repo_root, WORM_TEMPLATE_RELATIVE_PATH)
            if _sha256_file(template) != state.worm_template_sha256:
                _fail("WORM_BASELINE_ARTIFACT_DRIFT")
            with _parameter_artifact(state.worm_parameters) as (parameter_path, digest):
                name = _deployment_name(
                    state.infrastructure_approval["worm_baseline_binding_sha256"]
                )
                command = _deployment_command(
                    operation=stage,
                    deployment_name=name,
                    template=template,
                    template_sha256=state.worm_template_sha256,
                    parameters=parameter_path,
                    parameters_sha256=digest,
                )
                deployment = _execute_mapping(
                    self._executor, command, "WORM_BASELINE_DEPLOYMENT_FAILED"
                )
            outputs = _validate_worm_deployment(deployment, name, state)
            receipt = _issue_receipt(
                UnlockedWormBaselineDeploymentReceipt,
                _WORM_RECEIPTS,
                _authority_id=id(authority),
                owner_binding_sha256=state.owner_binding_sha256,
                deployment_receipt_sha256=_sha256_json(deployment),
                outputs_sha256=_sha256_json(outputs),
            )
            authority._finish(stage)
            return receipt
        except Exception as error:
            authority._abort()
            if isinstance(error, AzurePerformanceInfrastructurePortError):
                raise
            _fail("WORM_BASELINE_DEPLOYMENT_FAILED")


class UnlockedWormBaselineReadbackPort:
    def __init__(self, command_executor: BoundAzureCommandExecutor) -> None:
        self._executor = command_executor

    def verify_exact_unlocked_baseline(
        self,
        authority: OwnerBoundInfrastructureDeploymentAuthority,
        receipt: UnlockedWormBaselineDeploymentReceipt,
    ) -> VerifiedUnlockedWormBaseline:
        stage = DEPLOYMENT_SEQUENCE[1]
        state = authority._begin(stage)
        try:
            _assert_receipt(receipt, _WORM_RECEIPTS, id(authority), state)
            worm = state.worm_parameters
            deployment_name = _deployment_name(
                state.infrastructure_approval["worm_baseline_binding_sha256"]
            )
            resource_group_scope = _resource_group_scope(str(worm["resourceGroupName"]))
            storage_id = (
                f"{resource_group_scope}/providers/Microsoft.Storage/storageAccounts/"
                f"{worm['storageAccountName']}"
            )
            container_id = (
                f"{storage_id}/blobServices/default/containers/{worm['containerName']}"
            )
            policy_id = f"{container_id}/immutabilityPolicies/default"
            deployment_id = (
                f"{resource_group_scope}/providers/Microsoft.Resources/deployments/"
                f"{deployment_name}"
            )
            urls = {
                "deployment": _arm_url(deployment_id, DEPLOYMENT_API_VERSION),
                "storage": _arm_url(storage_id, STORAGE_API_VERSION),
                "container": _arm_url(container_id, STORAGE_API_VERSION),
                "policy": _arm_url(policy_id, STORAGE_API_VERSION),
            }
            if any("/lock?" in value.casefold() for value in urls.values()):
                _fail("IRREVERSIBLE_WORM_LOCK_FORBIDDEN")
            account = _execute_mapping(
                self._executor,
                _read_command(
                    "worm_account_readback",
                    ("account", "show", "--subscription", SUBSCRIPTION_ID),
                ),
                "WORM_BASELINE_READBACK_FAILED",
            )
            observations = {
                key: _execute_mapping(
                    self._executor,
                    _read_command(
                        f"worm_{key}_readback",
                        ("rest", "--method", "get", "--url", url),
                    ),
                    "WORM_BASELINE_READBACK_FAILED",
                )
                for key, url in urls.items()
            }
            _validate_account(account)
            outputs = _validate_worm_deployment(
                observations["deployment"], deployment_name, state
            )
            if _sha256_json(outputs) != receipt.outputs_sha256:
                _fail("WORM_BASELINE_READBACK_MISMATCH")
            _validate_worm_storage(observations["storage"], storage_id, state)
            _validate_worm_container(
                observations["container"], container_id, state
            )
            _validate_unlocked_policy(observations["policy"], policy_id)
            readback = _issue_receipt(
                VerifiedUnlockedWormBaseline,
                _WORM_READBACKS,
                _authority_id=id(authority),
                owner_binding_sha256=state.owner_binding_sha256,
                worm_baseline_binding_sha256=state.infrastructure_approval[
                    "worm_baseline_binding_sha256"
                ],
                readback_sha256=_sha256_json(
                    {"account": account, **observations}
                ),
                policy_state="Unlocked",
            )
            authority._finish(stage)
            return readback
        except Exception as error:
            authority._abort()
            if isinstance(error, AzurePerformanceInfrastructurePortError):
                raise
            _fail("WORM_BASELINE_READBACK_FAILED")


class PerformanceCoordinationDeploymentPort:
    def __init__(self, command_executor: BoundAzureCommandExecutor) -> None:
        self._executor = command_executor

    def deploy(
        self,
        authority: OwnerBoundInfrastructureDeploymentAuthority,
        worm_readback: VerifiedUnlockedWormBaseline,
    ) -> PerformanceCoordinationDeploymentReceipt:
        stage = DEPLOYMENT_SEQUENCE[2]
        state = authority._begin(stage)
        try:
            _assert_readback(worm_readback, id(authority), state)
            template = _bound_repo_file(
                state.repo_root, COORDINATION_TEMPLATE_RELATIVE_PATH
            )
            if _sha256_file(template) != state.coordination_template_sha256:
                _fail("PERFORMANCE_COORDINATION_ARTIFACT_DRIFT")
            with _parameter_artifact(state.infrastructure_parameters) as (
                parameter_path,
                digest,
            ):
                name = _deployment_name(
                    state.infrastructure_approval["infrastructure_binding_sha256"]
                )
                command = _deployment_command(
                    operation=stage,
                    deployment_name=name,
                    template=template,
                    template_sha256=state.coordination_template_sha256,
                    parameters=parameter_path,
                    parameters_sha256=digest,
                )
                deployment = _execute_mapping(
                    self._executor,
                    command,
                    "PERFORMANCE_COORDINATION_DEPLOYMENT_FAILED",
                )
            outputs = _validate_coordination_deployment(deployment, name, state)
            receipt = _issue_receipt(
                PerformanceCoordinationDeploymentReceipt,
                _COORDINATION_RECEIPTS,
                _authority_id=id(authority),
                owner_binding_sha256=state.owner_binding_sha256,
                deployment_receipt_sha256=_sha256_json(deployment),
                outputs_sha256=_sha256_json(outputs),
                coordination_storage_account_resource_id=outputs[
                    "storageAccountResourceId"
                ],
                lease_container_resource_id=outputs[
                    "leaseContainerResourceId"
                ],
                lease_data_role_definition_id=outputs[
                    "leaseDataRoleDefinitionId"
                ],
                provisioner_lease_role_assignment_id=outputs[
                    "provisionerLeaseRoleAssignmentId"
                ],
            )
            authority._finish(stage)
            return receipt
        except Exception as error:
            authority._abort()
            if isinstance(error, AzurePerformanceInfrastructurePortError):
                raise
            _fail("PERFORMANCE_COORDINATION_DEPLOYMENT_FAILED")


def _validate_worm_deployment(
    deployment: Mapping[str, Any], name: str, state: _AuthorityState
) -> dict[str, Any]:
    worm = state.worm_parameters
    deployment_id = (
        f"{_resource_group_scope(str(worm['resourceGroupName']))}/providers/"
        f"Microsoft.Resources/deployments/{name}"
    )
    properties = _deployment_properties(deployment, deployment_id, name)
    _validate_deployment_parameters(properties, worm)
    outputs = _arm_values(properties.get("outputs"), _WORM_OUTPUT_KEYS)
    storage_id = (
        f"{_resource_group_scope(str(worm['resourceGroupName']))}/providers/"
        f"Microsoft.Storage/storageAccounts/{worm['storageAccountName']}"
    )
    container_id = (
        f"{storage_id}/blobServices/default/containers/{worm['containerName']}"
    )
    expected = {
        "offlineStatus": "S6B_AZURE_WORM_ADAPTER_READY_OFFLINE",
        "liveStatus": "BLOCKED_PENDING_S7_APPROVAL",
        "lockActionStatus": "OWNER_GATED_NOT_EXECUTED",
        "lockTargetResourceId": f"{container_id}/immutabilityPolicies/default",
        "configuredContainerName": worm["containerName"],
        "configuredEncryptionScope": worm["encryptionScopeName"],
        "providerContextBindingSource": (
            "azure-subscription-resource-tenant-readback"
        ),
        "deploymentScopeBinding": (
            f"{TENANT_ID}/{SUBSCRIPTION_ID}/{RESOURCE_GROUP}/Incremental"
        ),
        "deploymentModeBinding": "Incremental",
    }
    if any(not _equal_arm(outputs.get(key), value) for key, value in expected.items()):
        _fail("WORM_BASELINE_OUTPUTS_INVALID")
    identity_prefix = (
        f"{_resource_group_scope(RESOURCE_GROUP)}/providers/"
        "Microsoft.ManagedIdentity/userAssignedIdentities/"
    )
    if not _resource_name_has_prefix(
        outputs.get("cmkIdentityResourceId"), identity_prefix, "id-nac-worm-cmk-"
    ) or not _resource_name_has_prefix(
        outputs.get("writerIdentityResourceId"),
        identity_prefix,
        "id-nac-worm-writer-",
    ):
        _fail("WORM_BASELINE_OUTPUTS_INVALID")
    role_prefix = (
        f"{_resource_group_scope(RESOURCE_GROUP)}/providers/"
        "Microsoft.Authorization/roleDefinitions/"
    )
    for key in (
        "writerDataRoleDefinitionId",
        "writerManagementReadRoleDefinitionId",
    ):
        value = outputs.get(key)
        if (
            not isinstance(value, str)
            or not value.casefold().startswith(role_prefix.casefold())
            or _UUID_RE.fullmatch(value.rsplit("/", 1)[-1]) is None
        ):
            _fail("WORM_BASELINE_OUTPUTS_INVALID")
    return outputs


def _validate_coordination_deployment(
    deployment: Mapping[str, Any], name: str, state: _AuthorityState
) -> dict[str, Any]:
    parameters = state.infrastructure_parameters
    deployment_id = (
        f"{_resource_group_scope(RESOURCE_GROUP)}/providers/"
        f"Microsoft.Resources/deployments/{name}"
    )
    properties = _deployment_properties(deployment, deployment_id, name)
    _validate_deployment_parameters(properties, parameters)
    outputs = _arm_values(properties.get("outputs"), _COORDINATION_OUTPUT_KEYS)
    storage_id = (
        f"{_resource_group_scope(RESOURCE_GROUP)}/providers/"
        f"Microsoft.Storage/storageAccounts/{parameters['storageAccountName']}"
    )
    container_id = f"{storage_id}/blobServices/default/containers/{CONTAINER_NAME}"
    target = parameters["targetBindingSha256"]
    bff_id = str(parameters["bffStorageAccountResourceId"])
    worm_id = str(parameters["wormStorageAccountResourceId"])
    expected = {
        "contractSchemaVersion": "nac.azure-bff-performance-coordination/v1",
        "storageAccountName": parameters["storageAccountName"],
        "storageAccountResourceId": storage_id,
        "effectiveTags": effective_coordination_tags(parameters["tags"], target),
        "bffStorageAccountResourceIdBinding": bff_id,
        "bffStorageAccountNameBinding": bff_id.rsplit("/", 1)[-1],
        "wormStorageAccountResourceIdBinding": worm_id,
        "wormStorageAccountNameBinding": worm_id.rsplit("/", 1)[-1],
        "leaseContainerName": CONTAINER_NAME,
        "leaseContainerResourceId": container_id,
        "leaseBlobPath": f"locks/{target}.lock",
        "leaseBlobUri": (
            f"https://{parameters['storageAccountName']}.blob.core.windows.net/"
            f"{CONTAINER_NAME}/locks/{target}.lock"
        ),
        "requiredLeaseBlobType": "BlockBlob",
        "requiredLeaseBlobContentLength": 0,
        "targetBindingSha256": target,
        "allowedDataActions": sorted(ALLOWED_DATA_ACTIONS),
        "deploymentScopeBinding": f"{TENANT_ID}/{SUBSCRIPTION_ID}/{RESOURCE_GROUP}",
        "blobBootstrapRequired": True,
        "blobBootstrapExecutedByTemplate": False,
        "azureRbacWriteAuthorizedOperations": [
            "blob-create",
            "blob-overwrite",
            "lease-acquire",
            "lease-release",
            "lease-break",
        ],
        "azureRbacOperationRestrictionEnforced": False,
        "operationRestrictionDefenseInDepth": [
            "dedicated-storage-account",
            "exact-container-and-blob-path-abac",
            "sealed-bootstrap-and-runtime-application-apis",
        ],
        "principalSeparationMode": (
            "SINGLE_OWNER_BOUND_PRINCIPAL_FOR_BOOTSTRAP_AND_RUNTIME"
        ),
    }
    if any(not _equal_arm(outputs.get(key), value) for key, value in expected.items()):
        _fail("PERFORMANCE_COORDINATION_OUTPUTS_INVALID")
    for key, prefix in (
        (
            "leaseDataRoleDefinitionId",
            f"{_resource_group_scope(RESOURCE_GROUP)}/providers/"
            "Microsoft.Authorization/roleDefinitions/",
        ),
        (
            "provisionerLeaseRoleAssignmentId",
            f"{container_id}/providers/Microsoft.Authorization/roleAssignments/",
        ),
    ):
        value = outputs.get(key)
        if (
            not isinstance(value, str)
            or not value.casefold().startswith(prefix.casefold())
            or _UUID_RE.fullmatch(value.rsplit("/", 1)[-1]) is None
        ):
            _fail("PERFORMANCE_COORDINATION_OUTPUTS_INVALID")
    condition = outputs.get("exactLeaseBlobCondition")
    if (
        not isinstance(condition, str)
        or CONTAINER_NAME not in condition
        or f"locks/{target}.lock" not in condition
        or "StringEquals" not in condition
        or "StringLike" in condition
    ):
        _fail("PERFORMANCE_COORDINATION_OUTPUTS_INVALID")
    return outputs


def _validate_worm_storage(
    value: Mapping[str, Any], resource_id: str, state: _AuthorityState
) -> None:
    worm = state.worm_parameters
    properties = value.get("properties")
    if (
        not _same_resource_id(value.get("id"), resource_id)
        or value.get("name") != worm["storageAccountName"]
        or str(value.get("type", "")).casefold()
        != "microsoft.storage/storageaccounts"
        or value.get("location") != worm["location"]
        or value.get("kind") != "StorageV2"
        or not isinstance(properties, Mapping)
    ):
        _fail("WORM_BASELINE_STORAGE_READBACK_INVALID")
    expected = {
        "allowBlobPublicAccess": False,
        "allowCrossTenantReplication": False,
        "allowSharedKeyAccess": False,
        "defaultToOAuthAuthentication": True,
        "minimumTlsVersion": "TLS1_2",
        "publicNetworkAccess": "Disabled",
        "supportsHttpsTrafficOnly": True,
    }
    if any(properties.get(key) is not expected_value for key, expected_value in expected.items() if isinstance(expected_value, bool)):
        _fail("WORM_BASELINE_STORAGE_READBACK_INVALID")
    if any(properties.get(key) != expected_value for key, expected_value in expected.items() if not isinstance(expected_value, bool)):
        _fail("WORM_BASELINE_STORAGE_READBACK_INVALID")


def _validate_worm_container(
    value: Mapping[str, Any], resource_id: str, state: _AuthorityState
) -> None:
    worm = state.worm_parameters
    properties = value.get("properties")
    metadata = properties.get("metadata") if isinstance(properties, Mapping) else None
    immutable = (
        properties.get("immutableStorageWithVersioning")
        if isinstance(properties, Mapping)
        else None
    )
    expected_metadata = {
        "nac_schema_version": "nac.azure-blob-worm-container/v0.4",
        "nac_status": "S6B_AZURE_WORM_ADAPTER_READY_OFFLINE",
        "provider_context_binding_source": (
            "azure-subscription-resource-tenant-readback"
        ),
        "provider_binding_material": "runtime-readback-not-template-metadata",
        "legal_hold_capability_source": "container-policy-properties",
        "minimum_retention_days": "3653",
        "encryption_scope": worm["encryptionScopeName"],
        "encryption_key_source": "Microsoft.Keyvault",
    }
    if (
        not _same_resource_id(value.get("id"), resource_id)
        or value.get("name") != worm["containerName"]
        or not isinstance(properties, Mapping)
        or properties.get("defaultEncryptionScope") != worm["encryptionScopeName"]
        or properties.get("denyEncryptionScopeOverride") is not True
        or properties.get("publicAccess") != "None"
        or not isinstance(immutable, Mapping)
        or immutable.get("enabled") is not True
        or metadata != expected_metadata
    ):
        _fail("WORM_BASELINE_CONTAINER_READBACK_INVALID")


def _validate_unlocked_policy(value: Mapping[str, Any], resource_id: str) -> None:
    properties = value.get("properties")
    if (
        not _same_resource_id(value.get("id"), resource_id)
        or value.get("name") != "default"
        or not isinstance(properties, Mapping)
        or properties.get("state") != "Unlocked"
        or properties.get("immutabilityPeriodSinceCreationInDays") != 3653
        or properties.get("allowProtectedAppendWrites") is not False
        or properties.get("allowProtectedAppendWritesAll") is not False
    ):
        _fail("WORM_BASELINE_NOT_EXACTLY_UNLOCKED")


def _validate_account(value: Mapping[str, Any]) -> None:
    if (
        value.get("environmentName") != EXPECTED_CLOUD_NAME
        or value.get("tenantId") != TENANT_ID
        or value.get("id") != SUBSCRIPTION_ID
        or value.get("state") != "Enabled"
    ):
        _fail("WORM_BASELINE_ACCOUNT_SCOPE_INVALID")


def _deployment_properties(
    deployment: Mapping[str, Any], deployment_id: str, name: str
) -> Mapping[str, Any]:
    properties = deployment.get("properties")
    if (
        not _same_resource_id(deployment.get("id"), deployment_id)
        or deployment.get("name") not in (None, name)
        or not isinstance(properties, Mapping)
        or properties.get("provisioningState") != "Succeeded"
    ):
        _fail("AZURE_DEPLOYMENT_RECEIPT_INVALID")
    return properties


def _validate_deployment_parameters(
    properties: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    actual = _arm_values(properties.get("parameters"), frozenset(expected))
    if not _equal_arm(actual, expected):
        _fail("AZURE_DEPLOYMENT_PARAMETERS_MISMATCH")


def _arm_values(value: Any, expected_keys: frozenset[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected_keys:
        _fail("AZURE_DEPLOYMENT_RECEIPT_INVALID")
    result: dict[str, Any] = {}
    for key in sorted(value):
        envelope = value[key]
        if not isinstance(envelope, Mapping) or "value" not in envelope:
            _fail("AZURE_DEPLOYMENT_RECEIPT_INVALID")
        result[key] = _deep_copy(envelope["value"])
    return result


def _deployment_command(
    *,
    operation: str,
    deployment_name: str,
    template: Path,
    template_sha256: str,
    parameters: Path,
    parameters_sha256: str,
) -> BoundAzureCliCommand:
    argv = (
        "deployment",
        "group",
        "create",
        "--name",
        deployment_name,
        "--resource-group",
        RESOURCE_GROUP,
        "--template-file",
        str(template),
        "--parameters",
        f"@{parameters}",
        "--mode",
        "Incremental",
        "--subscription",
        SUBSCRIPTION_ID,
    )
    return _issue_command(
        operation,
        argv,
        artifacts=(
            BoundAzureArtifact(str(template), template, template_sha256),
            BoundAzureArtifact(str(parameters), parameters, parameters_sha256),
        ),
        read_only=False,
        timeout_seconds=900,
    )


def _read_command(operation: str, argv: tuple[str, ...]) -> BoundAzureCliCommand:
    if argv[:1] == ("rest",) and (
        len(argv) != 5
        or argv[1:3] != ("--method", "get")
        or argv[3] != "--url"
        or not argv[4].startswith("https://management.azure.com/")
        or "/lock?" in argv[4].casefold()
    ):
        _fail("AZURE_READBACK_COMMAND_INVALID")
    return _issue_command(
        operation,
        argv,
        artifacts=(),
        read_only=True,
        timeout_seconds=120,
    )


def _issue_command(
    operation: str,
    argv: tuple[str, ...],
    *,
    artifacts: tuple[BoundAzureArtifact, ...],
    read_only: bool,
    timeout_seconds: float,
) -> BoundAzureCliCommand:
    command = object.__new__(BoundAzureCliCommand)
    values = {
        "operation": operation,
        "argv": argv,
        "argv_sha256": _sha256_json(list(argv)),
        "artifacts": artifacts,
        "read_only": read_only,
        "timeout_seconds": timeout_seconds,
        "_seal": _COMMAND_SEAL,
    }
    for key, value in values.items():
        object.__setattr__(command, key, value)
    _ISSUED_COMMANDS[id(command)] = command
    return command


def _execute_mapping(
    executor: BoundAzureCommandExecutor,
    command: BoundAzureCliCommand,
    failure_code: str,
) -> Mapping[str, Any]:
    command._assert_issued()
    try:
        result = executor.execute(command)
    except AzurePerformanceInfrastructurePortError:
        raise
    except Exception:
        _fail(failure_code)
    if (
        not isinstance(result, Mapping)
        or result.get("ok") is not True
        or result.get("code") != "AZURE_CLI_OK"
        or not isinstance(result.get("data"), Mapping)
    ):
        _fail(failure_code)
    return result["data"]


@contextmanager
def _parameter_artifact(
    parameters: Mapping[str, Any]
) -> Iterator[tuple[Path, str]]:
    payload = {
        "$schema": _ARM_PARAMETERS_SCHEMA,
        "contentVersion": "1.0.0.0",
        "parameters": {
            key: {"value": _deep_copy(parameters[key])}
            for key in sorted(parameters)
        },
    }
    content = _canonical_json(payload).encode("ascii")
    with tempfile.TemporaryDirectory(prefix="nac-bff-infrastructure-") as directory:
        path = Path(directory) / "main.parameters.json"
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise
        yield path, hashlib.sha256(content).hexdigest()


def _issue_receipt(
    receipt_type: type[Any], registry: dict[int, Any], **values: Any
) -> Any:
    receipt = object.__new__(receipt_type)
    for key, value in {**values, "_seal": _RECEIPT_SEAL}.items():
        object.__setattr__(receipt, key, value)
    registry[id(receipt)] = receipt
    return receipt


def _assert_receipt(
    receipt: Any,
    registry: Mapping[int, Any],
    authority_id: int,
    state: _AuthorityState,
) -> None:
    if (
        type(receipt) is not UnlockedWormBaselineDeploymentReceipt
        or registry.get(id(receipt)) is not receipt
        or receipt._seal is not _RECEIPT_SEAL
        or receipt._authority_id != authority_id
        or receipt.owner_binding_sha256 != state.owner_binding_sha256
    ):
        _fail("WORM_BASELINE_DEPLOYMENT_RECEIPT_INVALID")


def _assert_readback(
    readback: Any, authority_id: int, state: _AuthorityState
) -> None:
    if (
        type(readback) is not VerifiedUnlockedWormBaseline
        or _WORM_READBACKS.get(id(readback)) is not readback
        or readback._seal is not _RECEIPT_SEAL
        or readback._authority_id != authority_id
        or readback.owner_binding_sha256 != state.owner_binding_sha256
        or readback.worm_baseline_binding_sha256
        != state.infrastructure_approval["worm_baseline_binding_sha256"]
        or readback.policy_state != "Unlocked"
    ):
        _fail("WORM_BASELINE_READBACK_CAPABILITY_INVALID")


def _authority_state(
    authority: OwnerBoundInfrastructureDeploymentAuthority,
) -> _AuthorityState:
    if (
        type(authority) is not OwnerBoundInfrastructureDeploymentAuthority
        or authority._seal is not _AUTHORITY_SEAL
        or _ISSUED_AUTHORITIES.get(id(authority)) is not authority
        or id(authority) not in _AUTHORITY_STATES
    ):
        _fail("OWNER_BOUND_INFRASTRUCTURE_AUTHORITY_INVALID")
    return _AUTHORITY_STATES[id(authority)]


def _validate_pairwise_storage_bindings(
    parameters: Mapping[str, Any], worm_parameters: Mapping[str, Any]
) -> None:
    worm_id = str(parameters["wormStorageAccountResourceId"])
    bff_id = str(parameters["bffStorageAccountResourceId"])
    names = {
        str(parameters["storageAccountName"]).casefold(),
        worm_id.rsplit("/", 1)[-1].casefold(),
        bff_id.rsplit("/", 1)[-1].casefold(),
    }
    expected_worm_id = (
        f"{_resource_group_scope(str(worm_parameters['resourceGroupName']))}/"
        "providers/Microsoft.Storage/storageAccounts/"
        f"{worm_parameters['storageAccountName']}"
    )
    if len(names) != 3 or not _same_resource_id(worm_id, expected_worm_id):
        raise ValueError("storage bindings")


def _bound_repo_file(root: Path, relative: Path) -> Path:
    path = (root / relative).resolve(strict=True)
    if root not in path.parents or not path.is_file() or path.is_symlink():
        raise ValueError("artifact path")
    return path


def _resource_group_scope(resource_group: str) -> str:
    return f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{resource_group}"


def _arm_url(resource_id: str, api_version: str) -> str:
    return f"https://management.azure.com{resource_id}?api-version={api_version}"


def _deployment_name(binding_sha256: str) -> str:
    if _SHA256_RE.fullmatch(binding_sha256) is None:
        _fail("INFRASTRUCTURE_DEPLOYMENT_BINDING_INVALID")
    value = f"nac-bff-{binding_sha256[:12]}"
    if _DEPLOYMENT_NAME_RE.fullmatch(value) is None:
        _fail("INFRASTRUCTURE_DEPLOYMENT_BINDING_INVALID")
    return value


def _resource_name_has_prefix(value: Any, scope: str, prefix: str) -> bool:
    if not isinstance(value, str) or not value.casefold().startswith(scope.casefold()):
        return False
    name = value[len(scope) :]
    return name.startswith(prefix) and len(name) > len(prefix)


def _same_resource_id(left: Any, right: str) -> bool:
    return isinstance(left, str) and left.casefold() == right.casefold()


def _equal_arm(left: Any, right: Any) -> bool:
    return _canonical_json(left) == _canonical_json(right)


def _deep_copy(value: Any) -> Any:
    return json.loads(_canonical_json(value))


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _json_value(value),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _sha256_json(value: Any) -> str:
    return _sha256_text(_canonical_json(value))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _fail(code: str) -> None:
    raise AzurePerformanceInfrastructurePortError(code)


__all__ = [
    "AzureCliPerformanceInfrastructureCommandExecutor",
    "AzurePerformanceInfrastructurePortError",
    "BoundAzureArtifact",
    "BoundAzureCliCommand",
    "BoundAzureCommandExecutor",
    "DEPLOYMENT_SEQUENCE",
    "ExactAzureRestCommandExecutor",
    "OwnerBoundInfrastructureDeploymentAuthority",
    "PerformanceCoordinationDeploymentPort",
    "PerformanceCoordinationDeploymentReceipt",
    "UnlockedWormBaselineDeploymentPort",
    "UnlockedWormBaselineDeploymentReceipt",
    "UnlockedWormBaselineReadbackPort",
    "VerifiedUnlockedWormBaseline",
]
