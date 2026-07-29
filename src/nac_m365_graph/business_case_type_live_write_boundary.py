from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from notary_kg.business_case_type_mutation import canonical_hash

from .business_case_type_live_write_evidence import (
    LiveWriteEvidenceContext,
    S4dMutationEvidenceHook,
    s4d_evidence_operation_binding_sha256,
)
from .business_case_type_live_write_gate import (
    LiveWriteApprovalAttestation,
    LiveWriteGateBlocked,
    OwnerApprovalVerifierPort,
    WriteIdentityFactoryPort,
    WriteIdentityInspectionPort,
    verify_live_write_owner_approval,
    validate_write_identity_context,
)
from .business_case_type_write_composition import collection_urls
from .business_case_type_write_edge import (
    BusinessCaseTypeGraphWriteEdge,
    mutation_evidence_binding,
)
from .business_case_type_write_plan import (
    GRAPH_BASE_URL,
    BoundWriteTarget,
    BusinessCaseTypeWritePlan,
    BusinessCaseTypeWritePlanBuilder,
    approval_plan_binding_sha256,
)
from .business_case_type_write_state import SqliteMutationEvidenceHook
from .business_case_type_write_transport import (
    GraphRestV1WriteTransport,
    HttpTransportPort,
)
from nac_runtime.immutable_evidence import (
    ImmutableEvidencePublisher,
    OutboxPort,
)


@dataclass(frozen=True, slots=True)
class LiveWriteBoundaryResult:
    status: str
    operation: str
    mutation_sha256: str
    transport_calls: int
    write_attempts: int
    reconciliation_required: bool
    reason_code: str
    plan_sha256: str
    publication_chain_head_sha256: str | None
    worm_readback_verified: bool


class BusinessCaseTypeLiveWriteBoundary:
    """Production-shaped S4d composition with injected, offline-safe ports."""

    def __init__(
        self,
        *,
        target: BoundWriteTarget,
        tenant_binding_sha256: str,
        database_path: Path,
        attestation: LiveWriteApprovalAttestation,
        expected_attestation: Mapping[str, str],
        owner_approval_verifier: OwnerApprovalVerifierPort,
        identity_inspector: WriteIdentityInspectionPort,
        identity_factory: WriteIdentityFactoryPort,
        http_port: HttpTransportPort,
        outbox: OutboxPort,
        publisher: ImmutableEvidencePublisher,
        evidence_context_factory: Callable[
            [BusinessCaseTypeWritePlan], LiveWriteEvidenceContext
        ],
    ) -> None:
        self._target = target
        self._tenant_binding_sha256 = tenant_binding_sha256
        self._database_path = database_path
        self._attestation = attestation
        self._expected_attestation = dict(expected_attestation)
        self._owner_approval_verifier = owner_approval_verifier
        self._identity_inspector = identity_inspector
        self._identity_factory = identity_factory
        self._http_port = http_port
        self._outbox = outbox
        self._publisher = publisher
        self._evidence_context_factory = evidence_context_factory

    def execute(
        self,
        *,
        plan: BusinessCaseTypeWritePlan,
        plan_builder: BusinessCaseTypeWritePlanBuilder,
    ) -> LiveWriteBoundaryResult:
        try:
            self._validate_static_bindings(plan, plan_builder)
        except Exception:
            return _blocked(plan, "static_owner_binding_drift")
        try:
            identity = self._identity_inspector.readback()
            validate_write_identity_context(
                identity,
                workspace_id=self._target.workspace_id,
                site_binding_sha256=site_binding_sha256(self._target.site_id),
                write_principal_binding_sha256=principal_binding_sha256(
                    self._target.write_identity_id
                ),
                bff_principal_binding_sha256=principal_binding_sha256(
                    self._target.bff_uami_identity_id
                ),
                inspection_principal_binding_sha256=(
                    self._attestation.inspection_principal_binding_sha256
                ),
                inspection_approval_sha256=(
                    self._attestation.owner_comment_sha256
                ),
            )
        except Exception:
            return _blocked(plan, "identity_readback_not_exact")
        try:
            token_provider = self._identity_factory.build(identity)
            transport = GraphRestV1WriteTransport(
                token_provider,
                self._http_port,
                allowed_collection_urls=collection_urls(self._target),
            )
            local = SqliteMutationEvidenceHook(self._database_path)
            evidence_context = self._evidence_context_factory(plan)
            expected_operation_binding = (
                s4d_evidence_operation_binding_sha256(
                    mutation_evidence_binding(plan)
                )
            )
            if (
                evidence_context.operation_binding_sha256
                != expected_operation_binding
            ):
                raise LiveWriteGateBlocked(
                    "evidence operation binding drift"
                )
            evidence = S4dMutationEvidenceHook(
                local=local,
                outbox=self._outbox,
                publisher=self._publisher,
                context=evidence_context,
            )
            edge = BusinessCaseTypeGraphWriteEdge(
                transport, evidence, plan_builder
            )
        except Exception:
            return _blocked(plan, "runtime_composition_unavailable")
        try:
            result = edge.execute(plan)
        except Exception:
            return _uncertain(plan)
        publication = evidence.publication_result
        verified = bool(
            publication is not None
            and publication.get("worm_readback_verified") is True
        )
        status = (
            "S4D_WRITE_VERIFIED"
            if result.status
            in {
                "APPLIED",
                "DEDUPLICATED",
                "PRECONDITION_FAILED",
                "PRECONDITION_FAILED_ALREADY_APPLIED",
                "RETRYABLE_NOT_APPLIED",
                "RETRYABLE_RESPONSE_STATE_ALREADY_APPLIED",
                "WRITE_REJECTED",
                "WRITE_REJECTED_STATE_ALREADY_APPLIED",
            }
            and verified
            else result.status
        )
        return LiveWriteBoundaryResult(
            status=status,
            operation=result.operation,
            mutation_sha256=result.mutation_id,
            transport_calls=result.transport_calls,
            write_attempts=result.write_attempts,
            reconciliation_required=result.reconciliation_required,
            reason_code=result.reason_code,
            plan_sha256=plan.plan_sha256,
            publication_chain_head_sha256=(
                publication.get("chain_head_sha256")
                if publication is not None
                else None
            ),
            worm_readback_verified=verified,
        )

    def _validate_static_bindings(
        self,
        plan: BusinessCaseTypeWritePlan,
        plan_builder: BusinessCaseTypeWritePlanBuilder,
    ) -> None:
        revalidated = plan_builder.revalidate(plan)
        if revalidated != plan:
            raise LiveWriteGateBlocked("final plan revalidation drift")
        if plan.authorization.approval_ref != self._attestation.approval_ref:
            raise LiveWriteGateBlocked("plan approval reference drift")
        expected = dict(self._expected_attestation)
        expected["workspace_id"] = self._target.workspace_id
        expected["plan_binding_sha256"] = approval_plan_binding_sha256(plan)
        expected["target_binding_sha256"] = live_target_binding_sha256(
            self._target,
            tenant_binding_sha256=self._tenant_binding_sha256,
        )
        expected["write_principal_binding_sha256"] = (
            principal_binding_sha256(self._target.write_identity_id)
        )
        expected["bff_principal_binding_sha256"] = (
            principal_binding_sha256(self._target.bff_uami_identity_id)
        )
        verify_live_write_owner_approval(
            self._attestation,
            expected=expected,
            verifier=self._owner_approval_verifier,
        )


def principal_binding_sha256(principal_id: str) -> str:
    return canonical_hash(
        {
            "schema_version": "nac.s4d-principal-binding/v0.1",
            "principal_id": principal_id,
        }
    )


def site_binding_sha256(site_id: str) -> str:
    return canonical_hash(
        {
            "schema_version": "nac.s4d-site-binding/v0.1",
            "site_id": site_id,
        }
    )


def live_target_binding_sha256(
    target: BoundWriteTarget, *, tenant_binding_sha256: str
) -> str:
    return canonical_hash(
        {
            "schema_version": "nac.s4d-live-target-binding/v0.1",
            "tenant_binding_sha256": tenant_binding_sha256,
            "workspace_id": target.workspace_id,
            "site_id": target.site_id,
            "akten_list_id": target.akten_list_id,
            "aufgaben_list_id": target.aufgaben_list_id,
            "graph_base_url": GRAPH_BASE_URL,
        }
    )


def _blocked(
    plan: BusinessCaseTypeWritePlan, reason_code: str
) -> LiveWriteBoundaryResult:
    return LiveWriteBoundaryResult(
        status="S4D_BLOCKED",
        operation=(
            plan.mutation.operation
            if isinstance(plan, BusinessCaseTypeWritePlan)
            else "blocked"
        ),
        mutation_sha256=(
            plan.mutation.mutation_id
            if isinstance(plan, BusinessCaseTypeWritePlan)
            else "0" * 64
        ),
        transport_calls=0,
        write_attempts=0,
        reconciliation_required=False,
        reason_code=reason_code,
        plan_sha256=(
            plan.plan_sha256
            if isinstance(plan, BusinessCaseTypeWritePlan)
            else "0" * 64
        ),
        publication_chain_head_sha256=None,
        worm_readback_verified=False,
    )


def _uncertain(plan: BusinessCaseTypeWritePlan) -> LiveWriteBoundaryResult:
    return LiveWriteBoundaryResult(
        status="S4D_RECONCILIATION_REQUIRED",
        operation=plan.mutation.operation,
        mutation_sha256=plan.mutation.mutation_id,
        transport_calls=1,
        write_attempts=1,
        reconciliation_required=True,
        reason_code="runtime_execution_state_uncertain",
        plan_sha256=plan.plan_sha256,
        publication_chain_head_sha256=None,
        worm_readback_verified=False,
    )
