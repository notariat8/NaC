"""Offline readiness boundary for the Azure performance composition.

This module deliberately does not construct live adapters. The current stack
has no sealed production ports for every owner-bound infrastructure step, so a
factory would either skip required verification or depend on caller-supplied
authority. The validator exposes those gaps without touching files, process
state, credentials, Azure, Microsoft 365, DNS, or the network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .azure_live_commands import AzureCliAdapter
from .azure_performance_acceptance import (
    BoundPerformanceAuthorizationVerifier,
    FixedBffPerformanceTransport,
    PerformanceAcceptanceRunner,
    PerformanceArtifactStore,
    TOTAL_REQUEST_LIMIT,
)
from .azure_performance_infrastructure_safety import (
    AzurePerformanceInfrastructureReadbackAdapter,
)
from .azure_performance_lease import (
    AzureBlobLeaseAdapter,
    AzureBlobLeaseBootstrapAdapter,
)
from .azure_performance_monitor import AzurePerformanceMonitorAdapter
from .azure_performance_runtime import (
    LeaseBoundPerformanceAcceptance,
    PerformanceFinalEvidenceStore,
)


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
        None,
        (),
        (
            "no sealed live-action authority covers either exact "
            "infrastructure deployment"
        ),
        owner_bound=True,
    ),
    _PortRequirement(
        "unlocked_worm_baseline_deployment",
        "worm_baseline",
        "UnlockedWormBaselineDeploymentPort.deploy",
        None,
        (),
        "no production port deploys the owner-bound compiled WORM baseline",
        owner_bound=True,
    ),
    _PortRequirement(
        "unlocked_worm_baseline_exact_readback",
        "worm_baseline",
        "UnlockedWormBaselineReadbackPort.verify_exact_unlocked_baseline",
        None,
        (),
        (
            "the existing WORM read verifies only the resource identifier, "
            "not the exact unlocked baseline"
        ),
        owner_bound=True,
    ),
    _PortRequirement(
        "performance_coordination_deployment",
        "coordination_infrastructure",
        "PerformanceCoordinationDeploymentPort.deploy",
        None,
        (),
        "no production port deploys the owner-bound coordination template",
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
        None,
        (),
        (
            "bootstrap returns the strong ETag in memory but no durable port "
            "commits and reloads the exact lease binding"
        ),
        owner_bound=True,
    ),
    _PortRequirement(
        "attested_azure_storage_token_provider",
        "lease_runtime",
        "AttestedAzureStorageTokenProvider.get_token",
        None,
        (),
        (
            "the opaque storage-token issuer has no production provider; "
            "private test issuance is not an admissible runtime port"
        ),
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
        "production_composition_constructed": False,
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


__all__ = [
    "BLOCKED_STATUS",
    "SCHEMA_VERSION",
    "validate_azure_performance_composition_readiness",
]
