"""Owner-bound Azure BFF performance composition and offline readiness."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import wraps
import hashlib
import json
from pathlib import Path
import re
import stat
from typing import Any
from uuid import UUID

from .azure_activation_attestations import (
    AZURE_CLI_EXECUTION_PATH,
    GH_CLI_EXECUTION_PATH,
    M365_CLI_EXECUTION_PATH,
    M365_NODE_EXECUTION_PATH,
)
from .azure_activation_composition import (
    GitHubApprovalVerifier,
    _bound_provisioner_token_provider,
)
from .azure_live_commands import AzureCliAdapter
from .azure_performance_acceptance import (
    BoundPerformanceAuthorizationVerifier,
    FixedBffPerformanceTransport,
    FixedTransportBindingVerifier,
    M365DelegatedTokenProvider,
    PerformanceAcceptanceRunner,
    PerformanceArtifactStore,
    OUTPUT_ROOT,
    TOTAL_REQUEST_LIMIT,
    build_owner_comment,
    build_performance_acceptance_plan,
    verify_performance_execution_authorization,
)
from .azure_performance_broker_activation import (
    BrokerFunctionSettingsPort,
    build_broker_function_settings,
)
from .azure_performance_infrastructure_safety import (
    AzurePerformanceInfrastructureReadbackAdapter,
    AzurePerformanceInfrastructureRestartReceiptStore,
    begin_azure_performance_infrastructure_readback_session,
    build_infrastructure_restart_receipt_binding,
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
from .azure_performance_lease_broker_auth import (
    CertificateBffAppTokenProvider,
    RsaActivationTicketSigner,
    broker_binding_fingerprint,
    broker_storage_attestation,
)
from .azure_performance_lease_broker_client import (
    BrokeredAzureBlobLeaseAdapter,
)
from .azure_performance_lease_broker_storage import (
    AzureBlobAtomicLeaseStateMachine,
)
from .azure_performance_monitor import AzurePerformanceMonitorAdapter
from .azure_performance_storage_ports import PerformanceExecutionFence
from .azure_performance_runtime import (
    AzurePerformanceRuntimeAdapter,
    LeaseBoundPerformanceAcceptance,
    PerformanceFinalEvidenceStore,
)
from .graph_activation import (
    ensure_provisioner_performance_lease,
    inspect_provisioner_performance_lease,
)
from nac_m365_graph.graph_client import GraphRestClient
from nac_m365_graph.mvp_test_environment_deploy import M365CliCommandRunner
from nac_m365_graph.provisioner_env_bootstrap import load_provisioner_env_state


SCHEMA_VERSION = "nac.m365-azure-bff-performance-composition-readiness/v1"
BLOCKED_STATUS = "BLOCKED_MISSING_PRODUCTION_PORTS"


def _full_lifecycle_fence(function):  # type: ignore[no-untyped-def]
    """Serialize one full live lifecycle before owner or provider access."""

    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
        if args:
            raise TypeError("live composition accepts keyword-only arguments")
        if (
            kwargs.get("owner_approved") is not True
            or kwargs.get("execute_live_acceptance") is not True
        ):
            return function(**kwargs)
        root = Path(kwargs["repo_root"]).expanduser().resolve(strict=True)
        fence = PerformanceExecutionFence(
            root / OUTPUT_ROOT / ".composition-execution-fence.lock"
        )
        with fence.hold():
            return function(**kwargs)

    return wrapped


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
        "immutable_infrastructure_restart_receipts",
        "coordination_infrastructure",
        "AzurePerformanceInfrastructureRestartReceiptStore.reconcile_successful_deployment",
        "AzurePerformanceInfrastructureRestartReceiptStore",
        (
            (AzurePerformanceInfrastructureRestartReceiptStore, "load"),
            (
                AzurePerformanceInfrastructureRestartReceiptStore,
                "persist_original_name_available",
            ),
            (
                AzurePerformanceInfrastructureRestartReceiptStore,
                "persist_successful_deployment",
            ),
            (
                AzurePerformanceInfrastructureRestartReceiptStore,
                "reconcile_successful_deployment",
            ),
        ),
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
        "provisioner_performance_lease_app_role",
        "broker_activation",
        "ensure_provisioner_performance_lease",
        "GraphRestClient",
        ((ensure_provisioner_performance_lease, "__call__"),),
        owner_bound=True,
    ),
    _PortRequirement(
        "broker_function_settings_activation",
        "broker_activation",
        "BrokerFunctionSettingsPort.configure_and_verify",
        "BrokerFunctionSettingsPort",
        ((BrokerFunctionSettingsPort, "configure_and_verify"),),
        owner_bound=True,
    ),
    _PortRequirement(
        "owner_bound_bff_app_token",
        "lease_broker_client",
        "CertificateBffAppTokenProvider.__call__",
        "CertificateBffAppTokenProvider",
        (
            (CertificateBffAppTokenProvider, "validate_local_credentials"),
            (CertificateBffAppTokenProvider, "__call__"),
        ),
        owner_bound=True,
    ),
    _PortRequirement(
        "short_lived_signed_broker_ticket",
        "lease_broker_client",
        "RsaActivationTicketSigner.__call__",
        "RsaActivationTicketSigner",
        ((RsaActivationTicketSigner, "__call__"),),
        owner_bound=True,
    ),
    _PortRequirement(
        "full_lifecycle_process_fence",
        "owner_preflight",
        "PerformanceExecutionFence.hold",
        "PerformanceExecutionFence",
        ((PerformanceExecutionFence, "hold"),),
        owner_bound=True,
    ),
    _PortRequirement(
        "brokered_dedicated_blob_lease",
        "lease_runtime",
        "AzureBlobLeasePort.acquire",
        "BrokeredAzureBlobLeaseAdapter",
        (
            (BrokeredAzureBlobLeaseAdapter, "acquire"),
            (BrokeredAzureBlobLeaseAdapter, "assert_held"),
            (BrokeredAzureBlobLeaseAdapter, "release"),
            (BrokeredAzureBlobLeaseAdapter, "execution_fence"),
        ),
        owner_bound=True,
    ),
    _PortRequirement(
        "server_side_atomic_blob_lease_state_machine",
        "lease_broker_server",
        "AzureBlobAtomicLeaseStateMachine.acquire/assert_held/release",
        "AzureBlobAtomicLeaseStateMachine",
        (
            (AzureBlobAtomicLeaseStateMachine, "acquire"),
            (AzureBlobAtomicLeaseStateMachine, "assert_held"),
            (AzureBlobAtomicLeaseStateMachine, "release"),
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


@_full_lifecycle_fence
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
    runtime_state_path: Path | None = None,
    runtime_certificate_path: Path | None = None,
    runtime_private_key_path: Path | None = None,
) -> dict[str, Any]:
    """Execute the exact combined infrastructure and measurement approval."""

    del runtime_state_path, runtime_certificate_path, runtime_private_key_path

    if owner_approved is not True or execute_live_acceptance is not True:
        raise ValueError("PERFORMANCE_ACCEPTANCE_OWNER_GATE_CLOSED")
    readiness = validate_azure_performance_composition_readiness()
    if readiness.get("ready") is not True:
        raise ValueError("PERFORMANCE_PRODUCTION_COMPOSITION_NOT_READY")
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
    contract_sha256 = str(measurement["contract_sha256"])
    infrastructure_approval = dict(measurement["infrastructure_approval"])
    plan = build_performance_acceptance_plan(
        expected_activation_hash, contract_sha256
    )
    artifact_store = PerformanceArtifactStore(root, plan["plan_sha256"])
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

    broker_caller_identity = _load_application_identity(
        provisioner_state_path,
        application_key="m365_provisioning_app",
        expected_display_name="NaC M365 Provisioning",
    )
    expected_tenant_id = str(infrastructure_parameters["tenantId"])
    if (
        broker_caller_identity["tenant_id"].casefold()
        != expected_tenant_id.casefold()
        or broker_caller_identity["service_principal_id"].casefold()
        != str(
            infrastructure_parameters["brokerCallerServicePrincipalId"]
        ).casefold()
        or broker_caller_identity["service_principal_id"].casefold()
        == str(infrastructure_parameters["brokerPrincipalId"]).casefold()
    ):
        raise ValueError("PERFORMANCE_PROVISIONER_IDENTITY_INVALID")
    bff_token_provider = CertificateBffAppTokenProvider(
        tenant_id=broker_caller_identity["tenant_id"],
        client_id=broker_caller_identity["client_id"],
        service_principal_id=broker_caller_identity["service_principal_id"],
        certificate_path=provisioner_certificate_path,
        private_key_path=provisioner_private_key_path,
        expected_certificate_sha256=str(
            infrastructure_parameters[
                "brokerTicketVerificationCertificateSha256"
            ]
        ),
    )
    bff_token_provider.validate_local_credentials()
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
    azure_cli = AzureCliAdapter(
        binary=AZURE_CLI_EXECUTION_PATH,
        expected_binary_sha256=toolchain_attestations[
            "azure_cli_toolchain_sha256"
        ],
    )
    executor = AzureCliPerformanceInfrastructureCommandExecutor(
        azure_cli, exact_rest_executor=azure_cli
    )
    deployment_id = _coordination_deployment_id(
        infrastructure_parameters=infrastructure_parameters,
        infrastructure_approval=infrastructure_approval,
    )
    restart_store = AzurePerformanceInfrastructureRestartReceiptStore(
        artifact_store.run_dir / "infrastructure-restart-receipts",
        binding=build_infrastructure_restart_receipt_binding(
            owner_binding_sha256=authorization.owner_approval_body_sha256,
            deployment_id=deployment_id,
            infrastructure_approval=infrastructure_approval,
            infrastructure_parameters=infrastructure_parameters,
        ),
    )
    coordination, name_readback, deployment_readback, complete_restart = (
        _prepare_performance_infrastructure(
            readback=readback,
            receipt_store=restart_store,
            deployment_authority=deployment_authority,
            executor=executor,
            deployment_id=deployment_id,
            infrastructure_parameters=infrastructure_parameters,
        )
    )
    performance_lease_assignment = _performance_lease_app_role_state(
        identity=broker_caller_identity,
        certificate_path=provisioner_certificate_path,
        private_key_path=provisioner_private_key_path,
        expected_certificate_sha256=str(
            infrastructure_parameters[
                "brokerTicketVerificationCertificateSha256"
            ]
        ),
        read_only=complete_restart,
    )

    verification_arguments = _infrastructure_verification_arguments(
        readback=readback,
        name_readback=name_readback,
        deployment_readback=deployment_readback,
        coordination=coordination,
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
    coordination_storage_account_resource_id = (
        f"/subscriptions/{infrastructure_parameters['subscriptionId']}"
        f"/resourceGroups/{infrastructure_parameters['resourceGroupName']}"
        "/providers/Microsoft.Storage/storageAccounts/"
        f"{infrastructure_parameters['storageAccountName']}"
    )
    storage_binding_id = (
        "nac-performance-" + authorization.target_binding_sha256[:32]
    )
    storage_attestation = broker_storage_attestation(
        owner_binding_sha256=authorization.owner_approval_body_sha256,
        target_binding_sha256=authorization.target_binding_sha256,
        coordination_storage_account_resource_id=(
            coordination_storage_account_resource_id
        ),
        broker_principal_id=str(infrastructure_parameters["brokerPrincipalId"]),
        broker_function_package_sha256=str(
            infrastructure_parameters["brokerFunctionPackageSha256"]
        ),
        broker_ticket_certificate_sha256=str(
            infrastructure_parameters[
                "brokerTicketVerificationCertificateSha256"
            ]
        ),
    )
    lease_binding_sha256 = broker_binding_fingerprint(
        storage_binding_id, storage_attestation
    )
    bootstrap_authority = (
        verifier.verify_owner_and_infrastructure_before_bootstrap(
            approval_reference=approval_reference,
            contract_sha256=contract_sha256,
            activation_hash=expected_activation_hash,
            correlation_id=correlation_id,
            bootstrap_binding_sha256=lease_binding_sha256,
        )
    )
    safety_verification = verifier.bootstrap_safety_verification(
        bootstrap_authority
    )
    ticket_certificate = provisioner_certificate_path.read_bytes()
    if (
        hashlib.sha256(ticket_certificate).hexdigest()
        != str(
            infrastructure_parameters[
                "brokerTicketVerificationCertificateSha256"
            ]
        )
    ):
        raise ValueError("PERFORMANCE_BROKER_CERTIFICATE_BINDING_MISMATCH")
    broker_settings = build_broker_function_settings(
        tenant_id=broker_caller_identity["tenant_id"],
        actor_id=broker_caller_identity["service_principal_id"],
        owner_binding_sha256=authorization.owner_approval_body_sha256,
        commit_sha=str(infrastructure_approval["approved_commit_sha"]),
        tree_sha=str(infrastructure_approval["approved_tree_sha"]),
        function_package_sha256=str(
            infrastructure_parameters["brokerFunctionPackageSha256"]
        ),
        plan_sha256=plan["plan_sha256"],
        target_binding_sha256=authorization.target_binding_sha256,
        coordination_storage_account_name=str(
            infrastructure_parameters["storageAccountName"]
        ),
        storage_binding_id=storage_binding_id,
        storage_attestation=storage_attestation,
        ticket_certificate=ticket_certificate,
        ticket_certificate_sha256=str(
            infrastructure_parameters[
                "brokerTicketVerificationCertificateSha256"
            ]
        ),
    )
    settings_port = BrokerFunctionSettingsPort(azure_cli)
    broker_function_activation = (
        settings_port.verify_current(broker_settings)
        if complete_restart
        else settings_port.configure_and_verify(broker_settings)
    )
    acquisition_safety_sha256 = _sha256_json(
        {
            "broker_binding_fingerprint": lease_binding_sha256,
            "infrastructure_safety_evidence_sha256": safety_verification[
                "infrastructure_safety_evidence_sha256"
            ],
            "owner_approval_body_sha256": (
                authorization.owner_approval_body_sha256
            ),
            "target_binding_sha256": authorization.target_binding_sha256,
        }
    )
    handoff_bindings = verifier.record_broker_lease_handoff(
        lease_binding_sha256=lease_binding_sha256,
        lease_acquisition_safety_evidence_sha256=(
            acquisition_safety_sha256
        ),
    )
    ticket_signer = RsaActivationTicketSigner(
        key_id=str(
            infrastructure_parameters[
                "brokerTicketVerificationCertificateSha256"
            ]
        )[:32],
        certificate_path=provisioner_certificate_path,
        private_key_path=provisioner_private_key_path,
        expected_certificate_sha256=str(
            infrastructure_parameters[
                "brokerTicketVerificationCertificateSha256"
            ]
        ),
        issuer="nac-performance-owner-gate",
        tenant_id=broker_caller_identity["tenant_id"],
        actor_id=broker_caller_identity["service_principal_id"],
        owner_binding_sha256=authorization.owner_approval_body_sha256,
        commit_sha=str(infrastructure_approval["approved_commit_sha"]),
        tree_sha=str(infrastructure_approval["approved_tree_sha"]),
        function_package_sha256=str(
            infrastructure_parameters["brokerFunctionPackageSha256"]
        ),
        plan_sha256=plan["plan_sha256"],
        target_binding_sha256=authorization.target_binding_sha256,
        storage_binding=storage_binding_id,
    )
    lease = BrokeredAzureBlobLeaseAdapter(
        broker_base_url=_function_app_base_url(
            str(infrastructure_parameters["brokerFunctionAppResourceId"])
        ),
        token_provider=bff_token_provider,
        ticket_provider=ticket_signer,
        target_binding_sha256=authorization.target_binding_sha256,
        lease_binding_sha256=handoff_bindings["lease_binding_sha256"],
        infrastructure_safety_evidence_sha256=safety_verification[
            "infrastructure_safety_evidence_sha256"
        ],
        lease_acquisition_safety_evidence_sha256=handoff_bindings[
            "lease_acquisition_safety_evidence_sha256"
        ],
        expected_broker_binding_fingerprint=lease_binding_sha256,
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
        "broker_function_settings_sha256": broker_function_activation.get(
            "settings_sha256"
        ),
        "performance_lease_assignment_sha256": _sha256_json(
            performance_lease_assignment
        ),
        "final_evidence_sha256": final.get("final_evidence_sha256"),
        "completion_manifest_sha256": _file_sha256(
            final_store.manifest_path
        ),
    }


@dataclass(frozen=True, slots=True)
class _CoordinationResources:
    coordination_storage_account_resource_id: str
    lease_container_resource_id: str
    broker_lease_data_role_definition_id: str
    broker_lease_role_assignment_id: str


def _prepare_performance_infrastructure(
    *,
    readback: Any,
    receipt_store: Any,
    deployment_authority: OwnerBoundInfrastructureDeploymentAuthority,
    executor: AzureCliPerformanceInfrastructureCommandExecutor,
    deployment_id: str,
    infrastructure_parameters: dict[str, Any],
) -> tuple[Any, Any, Any, bool]:
    """Choose the fresh or strictly read-only restart path before mutation."""

    state = receipt_store.load()
    status = state.get("status") if isinstance(state, dict) else None
    if status == "COMPLETE":
        deployment = readback.execute_read(
            observation_kind="coordination-deployment-receipt",
            resource_id=deployment_id,
        )
        successful = receipt_store.reconcile_successful_deployment(deployment)
        resources = successful.get("coordination_resources")
        if not isinstance(resources, dict):
            raise ValueError("PERFORMANCE_INFRASTRUCTURE_RESTART_RECEIPT_INVALID")
        return (
            _CoordinationResources(**resources),
            state["original_name_receipt"],
            deployment,
            True,
        )
    if status not in {"EMPTY", "NAME_ONLY"}:
        raise ValueError("PERFORMANCE_INFRASTRUCTURE_RESTART_RECEIPT_INVALID")

    name_readback = readback.check_storage_account_name_availability(
        subscription_id=str(infrastructure_parameters["subscriptionId"]),
        storage_account_name=str(infrastructure_parameters["storageAccountName"]),
    )
    if status == "EMPTY":
        receipt_store.persist_original_name_available(name_readback)
    else:
        receipt_store.require_current_name_available(name_readback)

    worm_receipt = UnlockedWormBaselineDeploymentPort(executor).deploy(
        deployment_authority
    )
    worm_readback = UnlockedWormBaselineReadbackPort(
        executor
    ).verify_exact_unlocked_baseline(deployment_authority, worm_receipt)
    coordination = PerformanceCoordinationDeploymentPort(executor).deploy(
        deployment_authority, worm_readback
    )
    deployment = readback.execute_read(
        observation_kind="coordination-deployment-receipt",
        resource_id=deployment_id,
    )
    receipt_store.persist_successful_deployment(
        deployment,
        coordination_resources=_coordination_resource_bindings(coordination),
        create_deployment_receipt_sha256=(
            coordination.deployment_receipt_sha256
        ),
        deployment_outputs_sha256=coordination.outputs_sha256,
    )
    return coordination, name_readback, deployment, False


def _coordination_resource_bindings(coordination: Any) -> dict[str, str]:
    return {
        "coordination_storage_account_resource_id": (
            coordination.coordination_storage_account_resource_id
        ),
        "lease_container_resource_id": coordination.lease_container_resource_id,
        "broker_lease_data_role_definition_id": (
            coordination.broker_lease_data_role_definition_id
        ),
        "broker_lease_role_assignment_id": (
            coordination.broker_lease_role_assignment_id
        ),
    }


def _coordination_deployment_id(
    *,
    infrastructure_parameters: dict[str, Any],
    infrastructure_approval: dict[str, str],
) -> str:
    return (
        f"/subscriptions/{infrastructure_parameters['subscriptionId']}/resourceGroups/"
        f"{infrastructure_parameters['resourceGroupName']}/providers/"
        "Microsoft.Resources/deployments/"
        f"{_deployment_name(infrastructure_approval['infrastructure_binding_sha256'])}"
    )


def _infrastructure_verification_arguments(
    *,
    readback: AzurePerformanceInfrastructureReadbackAdapter,
    name_readback: Any,
    deployment_readback: Any,
    coordination: Any,
    infrastructure_parameters: dict[str, Any],
) -> dict[str, Any]:
    parameters = infrastructure_parameters
    coordination_id = coordination.coordination_storage_account_resource_id
    blob_service_id = f"{coordination_id}/blobServices/default"
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
    broker_effective_rbac = readback.read_effective_rbac(
        principal_id=str(parameters["brokerPrincipalId"]),
        target_resource_id=coordination.lease_container_resource_id,
        ancestor_scopes=ancestor_scopes,
    )
    broker_caller_effective_rbac = readback.read_effective_rbac(
        principal_id=str(parameters["brokerCallerServicePrincipalId"]),
        target_resource_id=coordination.lease_container_resource_id,
        ancestor_scopes=ancestor_scopes,
    )
    return {
        "readback_session": readback.verification_capability,
        "coordination_storage_account_name": parameters["storageAccountName"],
        "coordination_name_readback_envelope": name_readback,
        "deployment_receipt_envelope": deployment_readback,
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
        "broker_principal_id": parameters["brokerPrincipalId"],
        "broker_caller_service_principal_id": parameters[
            "brokerCallerServicePrincipalId"
        ],
        "broker_function_app_resource_id": parameters[
            "brokerFunctionAppResourceId"
        ],
        "broker_function_package_sha256": parameters[
            "brokerFunctionPackageSha256"
        ],
        "broker_ticket_verification_certificate_sha256": parameters[
            "brokerTicketVerificationCertificateSha256"
        ],
        "broker_outbound_ip_addresses": parameters[
            "brokerOutboundIpAddresses"
        ],
        "target_binding_sha256": parameters["targetBindingSha256"],
        "broker_role_definition": readback.execute_read(
            observation_kind="coordination-broker-role-definition",
            resource_id=coordination.broker_lease_data_role_definition_id,
        ),
        "broker_role_assignment": readback.execute_read(
            observation_kind="coordination-broker-role-assignment",
            resource_id=coordination.broker_lease_role_assignment_id,
        ),
        "broker_function_app_readback_envelope": readback.execute_read(
            observation_kind="coordination-broker-function-app",
            resource_id=parameters["brokerFunctionAppResourceId"],
        ),
        "subscription_ancestry_readback_envelope": ancestry,
        "broker_effective_rbac_readback_envelope": (
            broker_effective_rbac
        ),
        "broker_caller_effective_rbac_readback_envelope": (
            broker_caller_effective_rbac
        ),
        "tenant_id": parameters["tenantId"],
        "subscription_id": parameters["subscriptionId"],
        "resource_group_name": parameters["resourceGroupName"],
        "location": parameters["location"],
        "tags": parameters["tags"],
        "broker_outbound_ip_addresses": parameters[
            "brokerOutboundIpAddresses"
        ],
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


def _load_application_identity(
    path: Path,
    *,
    application_key: str,
    expected_display_name: str,
) -> dict[str, str]:
    metadata = path.stat(follow_symlinks=False)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or metadata.st_size > 1024 * 1024
    ):
        raise ValueError("PERFORMANCE_PROVISIONER_IDENTITY_INVALID")
    state = load_provisioner_env_state(path)
    applications = state.get("applications")
    application = (
        applications.get(application_key)
        if isinstance(applications, dict)
        else None
    )
    tenant_id = state.get("tenantId") or state.get("tenant_id")
    client_id = (
        application.get("clientId") or application.get("client_id")
        if isinstance(application, dict)
        else None
    )
    service_principal_id = (
        application.get("servicePrincipalId")
        or application.get("service_principal_id")
        if isinstance(application, dict)
        else None
    )
    display_name = (
        application.get("displayName") or application.get("display_name")
        if isinstance(application, dict)
        else None
    )
    if (
        state.get("status") != "PASSED"
        or not isinstance(tenant_id, str)
        or not isinstance(client_id, str)
        or not isinstance(service_principal_id, str)
        or display_name != expected_display_name
    ):
        raise ValueError("PERFORMANCE_PROVISIONER_IDENTITY_INVALID")
    return {
        "tenant_id": str(UUID(tenant_id)),
        "client_id": str(UUID(client_id)),
        "service_principal_id": str(UUID(service_principal_id)),
    }


def _function_app_base_url(resource_id: str) -> str:
    segments = resource_id.strip().split("/")
    if (
        len(segments) != 9
        or segments[0] != ""
        or segments[1].casefold() != "subscriptions"
        or segments[3].casefold() != "resourcegroups"
        or segments[5].casefold() != "providers"
        or segments[6].casefold() != "microsoft.web"
        or segments[7].casefold() != "sites"
        or not segments[8]
    ):
        raise ValueError("PERFORMANCE_BROKER_FUNCTION_RESOURCE_ID_INVALID")
    hostname = segments[8].casefold()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,58}[a-z0-9])?", hostname):
        raise ValueError("PERFORMANCE_BROKER_FUNCTION_RESOURCE_ID_INVALID")
    return f"https://{hostname}.azurewebsites.net"


def _ensure_performance_lease_app_role(
    *,
    identity: dict[str, str],
    certificate_path: Path,
    private_key_path: Path,
    expected_certificate_sha256: str,
) -> dict[str, Any]:
    return _performance_lease_app_role_state(
        identity=identity,
        certificate_path=certificate_path,
        private_key_path=private_key_path,
        expected_certificate_sha256=expected_certificate_sha256,
        read_only=False,
    )


def _performance_lease_app_role_state(
    *,
    identity: dict[str, str],
    certificate_path: Path,
    private_key_path: Path,
    expected_certificate_sha256: str,
    read_only: bool,
) -> dict[str, Any]:
    graph = GraphRestClient(
        _bound_provisioner_token_provider(
            {
                "M365_TENANT_ID": identity["tenant_id"],
                "M365_PROVISIONER_CLIENT_ID": identity["client_id"],
                "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH": str(
                    certificate_path
                ),
                "M365_PROVISIONER_CLIENT_KEY_PATH": str(private_key_path),
            },
            expected_certificate_sha256=expected_certificate_sha256,
        )
    )
    result = (
        inspect_provisioner_performance_lease(graph)
        if read_only
        else ensure_provisioner_performance_lease(graph)
    )
    if (
        result.get("status") != "present"
        or result.get("assignment_count") != 1
    ):
        raise ValueError("PERFORMANCE_LEASE_APP_ROLE_READBACK_MISMATCH")
    return result


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
