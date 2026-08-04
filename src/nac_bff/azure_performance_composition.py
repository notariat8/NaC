"""Owner-bound Azure BFF performance composition and offline readiness."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import stat
from typing import Any
from uuid import UUID

from .azure_activation_attestations import (
    AZURE_CLI_EXECUTION_PATH,
    GH_CLI_EXECUTION_PATH,
    M365_CLI_EXECUTION_PATH,
    M365_NODE_EXECUTION_PATH,
)
from .azure_activation_composition import GitHubApprovalVerifier
from .azure_live_commands import AzureCliAdapter
from .azure_performance_acceptance import (
    BoundPerformanceAuthorizationVerifier,
    FixedBffPerformanceTransport,
    FixedTransportBindingVerifier,
    M365DelegatedTokenProvider,
    PerformanceAcceptanceRunner,
    PerformanceArtifactStore,
    TOTAL_REQUEST_LIMIT,
    build_owner_comment,
    build_performance_acceptance_plan,
    verify_performance_execution_authorization,
)
from .azure_performance_infrastructure_safety import (
    AzurePerformanceInfrastructureReadbackAdapter,
    begin_azure_performance_infrastructure_readback_session,
    calculate_toolchain_attestations_sha256,
)
from .azure_performance_authorization import VerifiedInfrastructureSafetySource
from .azure_performance_infrastructure_ports import (
    AzureCliPerformanceInfrastructureCommandExecutor,
    OwnerBoundInfrastructureDeploymentAuthority,
    PerformanceCoordinationDeploymentPort,
    UnlockedWormBaselineDeploymentPort,
    UnlockedWormBaselineReadbackPort,
    _deployment_name,
)
from .azure_performance_lease import (
    AzureBlobLeaseAdapter,
    AzureBlobLeaseBootstrapBinding,
    AzureBlobLeaseBootstrapAdapter,
    build_lease_acquisition_safety_evidence,
    calculate_azure_blob_lease_bootstrap_binding_sha256,
)
from .azure_performance_monitor import AzurePerformanceMonitorAdapter
from .azure_performance_storage_ports import (
    AttestedAzureStorageTokenProvider,
    DurableLeaseBindingHandoff,
)
from .azure_performance_runtime import (
    AzurePerformanceRuntimeAdapter,
    LeaseBoundPerformanceAcceptance,
    PerformanceFinalEvidenceStore,
)
from nac_m365_graph.mvp_test_environment_deploy import M365CliCommandRunner
from nac_m365_graph.provisioner_env_bootstrap import load_provisioner_env_state


SCHEMA_VERSION = "nac.m365-azure-bff-performance-composition-readiness/v1"
BLOCKED_STATUS = "BLOCKED_MISSING_PRODUCTION_PORTS"


@dataclass(frozen=True, slots=True)
class _PortRequirement:
    port_id: str
    stage: str
    required_interface: str
    provider: str | None
    callables: tuple[tuple[object, str], ...]
    blocking_reason: str | None = None
    owner_bound: bool = False
    limits: tuple[tuple[str, int], ...] = ()

    def available(self) -> bool:
        return self.provider is not None and all(
            callable(getattr(target, method, None))
            for target, method in self.callables
        )


_PORTS = (
    _PortRequirement(
        "combined_owner_approval_verification",
        "owner_preflight",
        "CombinedPerformanceOwnerApprovalPort.verify",
        "BoundPerformanceAuthorizationVerifier",
        (
            (BoundPerformanceAuthorizationVerifier, "verify"),
            (
                BoundPerformanceAuthorizationVerifier,
                "verify_owner_and_infrastructure_before_lease",
            ),
        ),
        owner_bound=True,
    ),
    _PortRequirement(
        "owner_bound_infrastructure_deployment_authority",
        "owner_preflight",
        "OwnerBoundInfrastructureDeploymentAuthority.issue_for_exact_sequence",
        "OwnerBoundInfrastructureDeploymentAuthority",
        ((OwnerBoundInfrastructureDeploymentAuthority, "issue_for_exact_sequence"),),
        owner_bound=True,
    ),
    _PortRequirement(
        "unlocked_worm_baseline_deployment",
        "worm_baseline",
        "UnlockedWormBaselineDeploymentPort.deploy",
        "UnlockedWormBaselineDeploymentPort",
        ((UnlockedWormBaselineDeploymentPort, "deploy"),),
        owner_bound=True,
    ),
    _PortRequirement(
        "unlocked_worm_baseline_exact_readback",
        "worm_baseline",
        "UnlockedWormBaselineReadbackPort.verify_exact_unlocked_baseline",
        "UnlockedWormBaselineReadbackPort",
        ((UnlockedWormBaselineReadbackPort, "verify_exact_unlocked_baseline"),),
        owner_bound=True,
    ),
    _PortRequirement(
        "performance_coordination_deployment",
        "coordination_infrastructure",
        "PerformanceCoordinationDeploymentPort.deploy",
        "PerformanceCoordinationDeploymentPort",
        ((PerformanceCoordinationDeploymentPort, "deploy"),),
        owner_bound=True,
    ),
    _PortRequirement(
        "performance_coordination_safety_readback",
        "coordination_infrastructure",
        "AzurePerformanceInfrastructureReadbackPort.execute_read",
        "AzurePerformanceInfrastructureReadbackAdapter",
        (
            (AzurePerformanceInfrastructureReadbackAdapter, "execute_read"),
            (
                AzurePerformanceInfrastructureReadbackAdapter,
                "check_storage_account_name_availability",
            ),
            (
                AzurePerformanceInfrastructureReadbackAdapter,
                "read_management_group_ancestry",
            ),
            (
                AzurePerformanceInfrastructureReadbackAdapter,
                "read_effective_rbac",
            ),
        ),
        owner_bound=True,
    ),
    _PortRequirement(
        "lease_blob_bootstrap",
        "lease_bootstrap",
        "AzureBlobLeaseBootstrapPort.bootstrap",
        "AzureBlobLeaseBootstrapAdapter",
        ((AzureBlobLeaseBootstrapAdapter, "bootstrap"),),
        owner_bound=True,
    ),
    _PortRequirement(
        "durable_bootstrap_lease_binding_handoff",
        "lease_bootstrap",
        "DurableLeaseBindingHandoffPort.commit_and_load",
        "DurableLeaseBindingHandoff",
        (
            (DurableLeaseBindingHandoff, "commit_and_load"),
            (DurableLeaseBindingHandoff, "load"),
        ),
        owner_bound=True,
    ),
    _PortRequirement(
        "attested_azure_storage_token_provider",
        "lease_runtime",
        "AttestedAzureStorageTokenProvider.get_token",
        "AttestedAzureStorageTokenProvider",
        ((AttestedAzureStorageTokenProvider, "get_token"),),
        owner_bound=True,
    ),
    _PortRequirement(
        "dedicated_blob_lease",
        "lease_runtime",
        "AzureBlobLeasePort.acquire",
        "AzureBlobLeaseAdapter",
        (
            (AzureBlobLeaseAdapter, "acquire"),
            (AzureBlobLeaseAdapter, "assert_held"),
            (AzureBlobLeaseAdapter, "release"),
            (AzureBlobLeaseAdapter, "execution_fence"),
        ),
        owner_bound=True,
    ),
    _PortRequirement(
        "azure_monitor_observation",
        "measurement",
        "AzurePerformanceMonitorPort.observe",
        "AzurePerformanceMonitorAdapter+AzureCliAdapter",
        (
            (AzurePerformanceMonitorAdapter, "observe"),
            (AzureCliAdapter, "run_monitor_metrics"),
        ),
        owner_bound=True,
    ),
    _PortRequirement(
        "bounded_500_get_runner",
        "measurement",
        "LeaseBoundPerformanceAcceptancePort.run",
        "LeaseBoundPerformanceAcceptance+PerformanceAcceptanceRunner",
        (
            (LeaseBoundPerformanceAcceptance, "run"),
            (PerformanceAcceptanceRunner, "run"),
            (FixedBffPerformanceTransport, "request"),
            (PerformanceArtifactStore, "write_state"),
        ),
        owner_bound=True,
        limits=(
            ("maximum_network_gets", TOTAL_REQUEST_LIMIT),
            ("maximum_concurrency", 1),
            ("maximum_dispatches_per_minute", 6),
        ),
    ),
    _PortRequirement(
        "restartable_final_evidence",
        "finalization",
        "PerformanceFinalEvidencePort.write_final_evidence",
        "PerformanceFinalEvidenceStore+LeaseBoundPerformanceAcceptance",
        (
            (PerformanceFinalEvidenceStore, "load_pending_finalization"),
            (PerformanceFinalEvidenceStore, "write_pending_finalization"),
            (PerformanceFinalEvidenceStore, "write_final_evidence"),
            (LeaseBoundPerformanceAcceptance, "run"),
        ),
        owner_bound=True,
    ),
)


def validate_azure_performance_composition_readiness() -> dict[str, Any]:
    """Return a fresh, redacted, strictly offline production-port assessment."""

    ports: list[dict[str, Any]] = []
    missing: list[str] = []
    for requirement in _PORTS:
        ready = requirement.available()
        if not ready:
            missing.append(requirement.port_id)
        item: dict[str, Any] = {
            "id": requirement.port_id,
            "stage": requirement.stage,
            "status": "READY" if ready else "MISSING",
            "required_interface": requirement.required_interface,
            "provider": requirement.provider if ready else None,
            "owner_bound": requirement.owner_bound,
        }
        if not ready:
            item["blocking_reason"] = requirement.blocking_reason or (
                "required production methods are unavailable"
            )
        item.update(dict(requirement.limits))
        ports.append(item)

    ready = not missing
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "READY" if ready else BLOCKED_STATUS,
        "ready": ready,
        "offline_only": True,
        "assessment_source": "in_process_static_port_inventory",
        "ports": ports,
        "missing_ports": missing,
        "production_composition_constructed": True,
        "owner_approval_verified": False,
        "live_actions_authorized": False,
        "summary": {
            "required_ports": len(ports),
            "ready_ports": len(ports) - len(missing),
            "missing_ports": len(missing),
            "file_reads": 0,
            "environment_reads": 0,
            "credential_reads": 0,
            "process_calls": 0,
            "network_calls": 0,
            "azure_calls": 0,
            "m365_calls": 0,
            "tenant_writes": 0,
        },
    }


def run_azure_performance_acceptance_live(
    *,
    repo_root: Path,
    owner_approved: bool,
    execute_live_acceptance: bool,
    approval_reference: str,
    expected_activation_hash: str,
    correlation_id: str,
    monitor_window_anchor_utc: str,
    toolchain_attestations: dict[str, str],
    infrastructure_parameters: dict[str, Any],
    worm_baseline_parameters: dict[str, Any],
    provisioner_state_path: Path,
    provisioner_certificate_path: Path,
    provisioner_private_key_path: Path,
) -> dict[str, Any]:
    """Execute the exact combined infrastructure and measurement approval."""

    if owner_approved is not True or execute_live_acceptance is not True:
        raise ValueError("PERFORMANCE_ACCEPTANCE_OWNER_GATE_CLOSED")
    from .azure_performance_owner_gate import (
        measure_performance_infrastructure_approval,
    )

    root = repo_root.resolve(strict=True)
    measurement = measure_performance_infrastructure_approval(
        root,
        expected_activation_hash=expected_activation_hash,
        toolchain_attestations=toolchain_attestations,
        infrastructure_parameters=infrastructure_parameters,
        worm_baseline_parameters=worm_baseline_parameters,
    )
    if measurement.get("composition_readiness", {}).get("ready") is not True:
        raise ValueError("PERFORMANCE_PRODUCTION_COMPOSITION_NOT_READY")
    contract_sha256 = str(measurement["contract_sha256"])
    infrastructure_approval = dict(measurement["infrastructure_approval"])
    plan = build_performance_acceptance_plan(
        expected_activation_hash, contract_sha256
    )
    if infrastructure_parameters.get("targetBindingSha256") != plan[
        "target_binding_sha256"
    ]:
        raise ValueError("PERFORMANCE_EXECUTION_BINDING_MISMATCH")

    approval_verifier = GitHubApprovalVerifier(
        binary=GH_CLI_EXECUTION_PATH,
        expected_binary_sha256=toolchain_attestations["gh_cli_sha256"],
    )
    authorization = verify_performance_execution_authorization(
        repo_root=root,
        approval_verifier=approval_verifier,
        approval_reference=approval_reference,
        contract_sha256=contract_sha256,
        activation_hash=expected_activation_hash,
        measurement_preflight_sha256="0" * 64,
        correlation_id=correlation_id,
        infrastructure_approval=infrastructure_approval,
        toolchain_attestations=toolchain_attestations,
        infrastructure_parameters=infrastructure_parameters,
        worm_baseline_parameters=worm_baseline_parameters,
        monitor_window_anchor_utc=monitor_window_anchor_utc,
    )
    owner_comment = build_owner_comment(
        contract_sha256,
        expected_activation_hash,
        correlation_id,
        infrastructure_approval,
        monitor_window_anchor_utc,
    )["body"]
    deployment_authority = (
        OwnerBoundInfrastructureDeploymentAuthority.issue_for_exact_sequence(
            repo_root=root,
            authorization=authorization,
            owner_comment_body=owner_comment,
            infrastructure_approval=infrastructure_approval,
            toolchain_attestations=toolchain_attestations,
            infrastructure_parameters=infrastructure_parameters,
            worm_baseline_parameters=worm_baseline_parameters,
        )
    )

    toolchain_sha256 = calculate_toolchain_attestations_sha256(
        toolchain_attestations
    )
    readback_session = begin_azure_performance_infrastructure_readback_session(
        owner_approval_body_sha256=authorization.owner_approval_body_sha256,
        toolchain_attestations_sha256=toolchain_sha256,
    )
    readback = AzurePerformanceInfrastructureReadbackAdapter(
        readback_session,
        toolchain_attestations=toolchain_attestations,
    )
    name_readback = readback.check_storage_account_name_availability(
        subscription_id=str(infrastructure_parameters["subscriptionId"]),
        storage_account_name=str(infrastructure_parameters["storageAccountName"]),
    )

    azure_cli = AzureCliAdapter(
        binary=AZURE_CLI_EXECUTION_PATH,
        expected_binary_sha256=toolchain_attestations[
            "azure_cli_toolchain_sha256"
        ],
    )
    executor = AzureCliPerformanceInfrastructureCommandExecutor(
        azure_cli, exact_rest_executor=azure_cli
    )
    worm_receipt = UnlockedWormBaselineDeploymentPort(executor).deploy(
        deployment_authority
    )
    worm_readback = UnlockedWormBaselineReadbackPort(
        executor
    ).verify_exact_unlocked_baseline(deployment_authority, worm_receipt)
    coordination = PerformanceCoordinationDeploymentPort(executor).deploy(
        deployment_authority, worm_readback
    )

    verification_arguments = _infrastructure_verification_arguments(
        readback=readback,
        name_readback=name_readback,
        coordination=coordination,
        infrastructure_approval=infrastructure_approval,
        infrastructure_parameters=infrastructure_parameters,
    )
    safety_source = VerifiedInfrastructureSafetySource(
        readback_capability=readback.verification_capability,
        verification_arguments=verification_arguments,
    )
    verifier = BoundPerformanceAuthorizationVerifier(
        repo_root=root,
        approval_verifier=approval_verifier,
        infrastructure_approval=infrastructure_approval,
        toolchain_attestations=toolchain_attestations,
        infrastructure_parameters=infrastructure_parameters,
        worm_baseline_parameters=worm_baseline_parameters,
        monitor_window_anchor_utc=monitor_window_anchor_utc,
        infrastructure_safety_source=safety_source,
    )
    identity = _load_provisioner_identity(provisioner_state_path)
    if (
        identity["tenant_id"].casefold()
        != str(infrastructure_parameters["tenantId"]).casefold()
    ):
        raise ValueError("PERFORMANCE_PROVISIONER_IDENTITY_INVALID")
    storage_token_provider = AttestedAzureStorageTokenProvider(
        tenant_id=identity["tenant_id"],
        client_id=identity["client_id"],
        token_subject=str(infrastructure_parameters["provisionerPrincipalId"]),
        certificate_path=provisioner_certificate_path,
        private_key_path=provisioner_private_key_path,
        expected_certificate_sha256=toolchain_attestations[
            "provisioner_certificate_sha256"
        ],
    )
    bootstrap_binding = _bootstrap_binding(
        authorization=authorization,
        infrastructure_parameters=infrastructure_parameters,
        identity=identity,
    )
    bootstrap_binding_sha256 = (
        calculate_azure_blob_lease_bootstrap_binding_sha256(bootstrap_binding)
    )
    bootstrap_authority = (
        verifier.verify_owner_and_infrastructure_before_bootstrap(
            approval_reference=approval_reference,
            contract_sha256=contract_sha256,
            activation_hash=expected_activation_hash,
            correlation_id=correlation_id,
            bootstrap_binding_sha256=bootstrap_binding_sha256,
        )
    )
    safety_verification = verifier.bootstrap_safety_verification(
        bootstrap_authority
    )
    bootstrap_adapter = AzureBlobLeaseBootstrapAdapter(
        binding=bootstrap_binding,
        infrastructure_safety_evidence=safety_verification,
        token_provider=storage_token_provider,
    )
    if (
        bootstrap_adapter.bootstrap_binding_sha256
        != bootstrap_binding_sha256
    ):
        raise ValueError("PERFORMANCE_BOOTSTRAP_TRANSITION_INVALID")
    lease_binding = bootstrap_adapter.bootstrap(
        bootstrap_authority.capability
    )
    artifact_store = PerformanceArtifactStore(root, plan["plan_sha256"])
    handoff = DurableLeaseBindingHandoff(
        artifact_store.run_dir / "lease-binding-handoff.redacted.json",
        expected_owner_approval_body_sha256=(
            authorization.owner_approval_body_sha256
        ),
        expected_target_binding_sha256=authorization.target_binding_sha256,
        expected_coordination_storage_account_resource_id=(
            coordination.coordination_storage_account_resource_id
        ),
    )
    durable_binding = handoff.commit_and_load(lease_binding)
    handoff_bindings = verifier.record_durable_bootstrap_handoff(
        durable_binding
    )
    acquisition_safety = build_lease_acquisition_safety_evidence(
        binding=durable_binding,
        infrastructure_safety_evidence=safety_verification,
    )
    if (
        acquisition_safety["lease_acquisition_safety_evidence_sha256"]
        != handoff_bindings["lease_acquisition_safety_evidence_sha256"]
    ):
        raise ValueError("PERFORMANCE_BOOTSTRAP_HANDOFF_INVALID")

    lease = AzureBlobLeaseAdapter(
        binding=durable_binding,
        acquisition_safety_evidence=acquisition_safety,
        state_path=artifact_store.run_dir / "lease-lifecycle.redacted.json",
        token_provider=storage_token_provider,
    )
    anchor = _parse_monitor_anchor(monitor_window_anchor_utc)
    lease_id = UUID(
        bytes=hashlib.sha256(
            (authorization.owner_approval_body_sha256 + plan["plan_sha256"]).encode(
                "ascii"
            )
        ).digest()[:16]
    )
    runtime = AzurePerformanceRuntimeAdapter(
        monitor=AzurePerformanceMonitorAdapter(azure_cli),
        lease=lease,
        lease_id=lease_id,
        monitor_window_anchor_utc=anchor,
    )
    m365_runner = M365CliCommandRunner(
        binary=M365_CLI_EXECUTION_PATH,
        node_bin=M365_NODE_EXECUTION_PATH,
        expected_binary_sha256=toolchain_attestations["m365_cli_sha256"],
        expected_node_sha256=toolchain_attestations["m365_node_sha256"],
    )
    transport = FixedBffPerformanceTransport(
        M365DelegatedTokenProvider(m365_runner)
    )
    runner = PerformanceAcceptanceRunner(
        transport=transport,
        checkpoint_store=artifact_store,
        authorization_verifier=verifier,
        measurement_provider=runtime,
        transport_verifier=FixedTransportBindingVerifier(),
        safety_monitor=runtime,
    )
    execution_bindings = dict(bootstrap_authority.execution_bindings)
    execution_bindings.update(
        {
            "lease_binding_sha256": handoff_bindings[
                "lease_binding_sha256"
            ],
            "lease_acquisition_safety_evidence_sha256": handoff_bindings[
                "lease_acquisition_safety_evidence_sha256"
            ],
        }
    )
    final_store = PerformanceFinalEvidenceStore(
        artifact_store.run_dir / "final-evidence.redacted.json"
    )
    final = LeaseBoundPerformanceAcceptance(
        runtime=runtime,
        runner=runner,
        execution_bindings=execution_bindings,
        authorization_verifier=verifier,
        final_evidence_store=final_store,
    ).run(
        plan_sha256=plan["plan_sha256"],
        contract_sha256=contract_sha256,
        activation_hash=expected_activation_hash,
        approval_reference=approval_reference,
        correlation_id=correlation_id,
    )
    return {
        "status": final.get("status"),
        "live_execution_invoked": True,
        "final_evidence_sha256": final.get("final_evidence_sha256"),
        "completion_manifest_sha256": _file_sha256(
            final_store.manifest_path
        ),
    }


def _infrastructure_verification_arguments(
    *,
    readback: AzurePerformanceInfrastructureReadbackAdapter,
    name_readback: Any,
    coordination: Any,
    infrastructure_approval: dict[str, str],
    infrastructure_parameters: dict[str, Any],
) -> dict[str, Any]:
    parameters = infrastructure_parameters
    coordination_id = coordination.coordination_storage_account_resource_id
    blob_service_id = f"{coordination_id}/blobServices/default"
    deployment_id = (
        f"/subscriptions/{parameters['subscriptionId']}/resourceGroups/"
        f"{parameters['resourceGroupName']}/providers/Microsoft.Resources/"
        "deployments/"
        f"{_deployment_name(infrastructure_approval['infrastructure_binding_sha256'])}"
    )
    deployment = readback.execute_read(
        observation_kind="coordination-deployment-receipt",
        resource_id=deployment_id,
    )
    ancestry = readback.read_management_group_ancestry(
        tenant_id=str(parameters["tenantId"]),
        subscription_id=str(parameters["subscriptionId"]),
    )
    ancestor_scopes = _effective_ancestor_scopes(
        ancestry,
        subscription_id=str(parameters["subscriptionId"]),
        resource_group_name=str(parameters["resourceGroupName"]),
        coordination_id=coordination_id,
        blob_service_id=blob_service_id,
        container_id=coordination.lease_container_resource_id,
    )
    effective_rbac = readback.read_effective_rbac(
        principal_id=str(parameters["provisionerPrincipalId"]),
        target_resource_id=coordination.lease_container_resource_id,
        ancestor_scopes=ancestor_scopes,
    )
    return {
        "readback_session": readback.verification_capability,
        "coordination_storage_account_name": parameters["storageAccountName"],
        "coordination_name_readback_envelope": name_readback,
        "deployment_receipt_envelope": deployment,
        "coordination_storage_readback_envelope": readback.execute_read(
            observation_kind="coordination-storage-account-configuration",
            resource_id=coordination_id,
        ),
        "coordination_blob_service_readback_envelope": readback.execute_read(
            observation_kind="coordination-blob-service-configuration",
            resource_id=blob_service_id,
        ),
        "lease_container_readback_envelope": readback.execute_read(
            observation_kind="coordination-lease-container-configuration",
            resource_id=coordination.lease_container_resource_id,
        ),
        "coordination_storage_account_resource_id": coordination_id,
        "bff_storage_account_resource_id": parameters[
            "bffStorageAccountResourceId"
        ],
        "worm_storage_account_resource_id": parameters[
            "wormStorageAccountResourceId"
        ],
        "bff_storage_readback_envelope": readback.execute_read(
            observation_kind="bff-storage-account-resource-id",
            resource_id=parameters["bffStorageAccountResourceId"],
        ),
        "worm_storage_readback_envelope": readback.execute_read(
            observation_kind="worm-storage-account-resource-id",
            resource_id=parameters["wormStorageAccountResourceId"],
        ),
        "provisioner_principal_id": parameters["provisionerPrincipalId"],
        "target_binding_sha256": parameters["targetBindingSha256"],
        "role_definition": readback.execute_read(
            observation_kind="coordination-role-definition",
            resource_id=coordination.lease_data_role_definition_id,
        ),
        "role_assignment": readback.execute_read(
            observation_kind="coordination-role-assignment",
            resource_id=coordination.provisioner_lease_role_assignment_id,
        ),
        "subscription_ancestry_readback_envelope": ancestry,
        "effective_rbac_readback_envelope": effective_rbac,
        "tenant_id": parameters["tenantId"],
        "subscription_id": parameters["subscriptionId"],
        "resource_group_name": parameters["resourceGroupName"],
        "location": parameters["location"],
        "tags": parameters["tags"],
        "allowed_client_ip_address": parameters["allowedClientIpAddress"],
    }


def _effective_ancestor_scopes(
    ancestry: Any,
    *,
    subscription_id: str,
    resource_group_name: str,
    coordination_id: str,
    blob_service_id: str,
    container_id: str,
) -> list[str]:
    payload = ancestry.get("payload") if hasattr(ancestry, "get") else None
    if not isinstance(payload, dict):
        raise ValueError("PERFORMANCE_INFRASTRUCTURE_PREFLIGHT_INVALID")
    relationships = payload.get("management_group_relationships")
    if not isinstance(relationships, list):
        raise ValueError("PERFORMANCE_INFRASTRUCTURE_PREFLIGHT_INVALID")
    scopes = ["/"]
    for item in relationships:
        scope = item.get("scope") if isinstance(item, dict) else None
        if not isinstance(scope, str) or not scope.startswith("/"):
            raise ValueError("PERFORMANCE_INFRASTRUCTURE_PREFLIGHT_INVALID")
        if scope.casefold() not in {value.casefold() for value in scopes}:
            scopes.append(scope)
    scopes.extend(
        [
            f"/subscriptions/{subscription_id}",
            f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}",
            coordination_id,
            blob_service_id,
            container_id,
        ]
    )
    return scopes


def _load_provisioner_identity(path: Path) -> dict[str, str]:
    metadata = path.stat(follow_symlinks=False)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or metadata.st_size > 1024 * 1024
    ):
        raise ValueError("PERFORMANCE_PROVISIONER_IDENTITY_INVALID")
    state = load_provisioner_env_state(path)
    applications = state.get("applications")
    provisioner = (
        applications.get("m365_provisioning_app")
        if isinstance(applications, dict)
        else None
    )
    tenant_id = state.get("tenantId")
    client_id = provisioner.get("clientId") if isinstance(provisioner, dict) else None
    if (
        state.get("status") != "PASSED"
        or not isinstance(tenant_id, str)
        or not isinstance(client_id, str)
        or provisioner.get("displayName") != "NaC M365 Provisioning"
    ):
        raise ValueError("PERFORMANCE_PROVISIONER_IDENTITY_INVALID")
    return {"tenant_id": tenant_id, "client_id": client_id}


def _bootstrap_binding(
    *,
    authorization: Any,
    infrastructure_parameters: dict[str, Any],
    identity: dict[str, str],
) -> AzureBlobLeaseBootstrapBinding:
    parameters = infrastructure_parameters
    identity_base = {
        "owner_approval_body_sha256": authorization.owner_approval_body_sha256,
        "target_binding_sha256": authorization.target_binding_sha256,
        "tenant_id": identity["tenant_id"],
        "client_id": identity["client_id"],
        "principal_id": parameters["provisionerPrincipalId"],
        "coordination_storage_account_resource_id": (
            f"/subscriptions/{parameters['subscriptionId']}/resourceGroups/"
            f"{parameters['resourceGroupName']}/providers/Microsoft.Storage/"
            f"storageAccounts/{parameters['storageAccountName']}"
        ),
    }
    return AzureBlobLeaseBootstrapBinding(
        account_name=str(parameters["storageAccountName"]),
        bff_account_name=_storage_account_name(
            str(parameters["bffStorageAccountResourceId"])
        ),
        worm_account_name=_storage_account_name(
            str(parameters["wormStorageAccountResourceId"])
        ),
        coordination_storage_account_resource_id=identity_base[
            "coordination_storage_account_resource_id"
        ],
        owner_approval_body_sha256=authorization.owner_approval_body_sha256,
        token_subject=str(parameters["provisionerPrincipalId"]),
        token_tenant_id=identity["tenant_id"],
        target_binding_sha256=authorization.target_binding_sha256,
        read_identity_binding_sha256=_sha256_json(
            {**identity_base, "operation": "blob-read"}
        ),
        write_identity_binding_sha256=_sha256_json(
            {**identity_base, "operation": "blob-write"}
        ),
    )


def _storage_account_name(resource_id: str) -> str:
    value = resource_id.rstrip("/").rsplit("/", 1)[-1]
    if not value or value.casefold() == resource_id.casefold():
        raise ValueError("PERFORMANCE_EXECUTION_BINDING_MISMATCH")
    return value


def _parse_monitor_anchor(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValueError("PERFORMANCE_MONITOR_WINDOW_ANCHOR_INVALID") from None
    if parsed.tzinfo is None:
        raise ValueError("PERFORMANCE_MONITOR_WINDOW_ANCHOR_INVALID")
    return parsed.astimezone(UTC)


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


__all__ = [
    "BLOCKED_STATUS",
    "SCHEMA_VERSION",
    "run_azure_performance_acceptance_live",
    "validate_azure_performance_composition_readiness",
]
