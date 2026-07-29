from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nac_runtime.azure_blob_worm import (
    AzureBlobContainerPolicy,
    AzureBlobProviderContext,
    AzureBlobWormJournal,
    AzureProviderContextAttestation,
    FakeAzureBlobWormTransport,
    azure_provider_context_attestation_sha256,
    azure_provider_context_binding_sha256,
)
from nac_runtime.immutable_evidence import (
    EvidenceRecord,
    ImmutableEvidencePublisher,
    InMemoryEvidenceOutbox,
    InMemoryReconciliationStore,
    REGISTERED_BUSINESS_CASE_TYPE_IDS,
    REGISTERED_CATALOG_VERSIONS,
    actor_ref,
    correlation_ref,
    typed_identifier_registry,
)

from .business_case_type_live_write_boundary import (
    BusinessCaseTypeLiveWriteBoundary,
    live_target_binding_sha256,
    principal_binding_sha256,
    site_binding_sha256,
)
from .business_case_type_live_write_evidence import (
    LiveWriteEvidenceContext,
    s4d_evidence_operation_binding_sha256,
)
from .business_case_type_live_write_gate import (
    S4D_READY_OFFLINE,
    OwnerApprovalVerification,
    WriteIdentityContext,
    build_unverified_live_write_approval_attestation,
)
from .business_case_type_write_composition_smoke import (
    _ScriptedHttpPort,
    _SyntheticTokenProvider,
    _authorization,
    _authorization_for,
    _mutations,
    _responses,
    _target,
)
from .business_case_type_write_edge import mutation_evidence_binding
from .business_case_type_write_plan import (
    BusinessCaseTypeWritePlanBuilder,
    approval_plan_binding_sha256,
)


_TENANT_ID = "11111111-1111-4111-8111-111111111111"
_ACTOR_ID = "22222222-2222-4222-8222-222222222222"
_ACTOR_KEY = b"actor-key-for-immutable-evidence"
_PRINCIPAL_KEY = b"stable-principal-binding-key-0001"
_CATALOG_VERSION = next(iter(REGISTERED_CATALOG_VERSIONS))
_IDENTIFIER_REGISTRY = typed_identifier_registry(
    business_case_type_ids=REGISTERED_BUSINESS_CASE_TYPE_IDS,
    catalog_versions=REGISTERED_CATALOG_VERSIONS,
)


class _IdentityInspector:
    def __init__(self) -> None:
        self._context: WriteIdentityContext | None = None
        self.calls = 0

    def bind(self, context: WriteIdentityContext) -> None:
        self._context = context

    def readback(self) -> WriteIdentityContext:
        self.calls += 1
        if self._context is None:
            raise RuntimeError("synthetic identity context is absent")
        return self._context


class _IdentityFactory:
    def __init__(self, token_provider: _SyntheticTokenProvider) -> None:
        self._token_provider = token_provider
        self.calls = 0

    def build(
        self, context: WriteIdentityContext
    ) -> _SyntheticTokenProvider:
        self.calls += 1
        return self._token_provider


class _OwnerApprovalVerifier:
    def __init__(self, *, verified: bool = True) -> None:
        self.calls = 0
        self._verified = verified

    def verify(self, attestation, *, expected):
        self.calls += 1
        return OwnerApprovalVerification(
            source="github_issue_owner_comment",
            issue_ref="https://github.com/notariat8/NaC/issues/700",
            owner_comment_sha256=attestation.owner_comment_sha256,
            owner_principal_binding_sha256="d" * 64,
            verifier_principal_binding_sha256=(
                attestation.owner_verifier_binding_sha256
            ),
            owner_allowlist_sha256=attestation.owner_allowlist_sha256,
            observed_at="2026-07-29T11:59:59Z",
            verified=self._verified,
        )


class _Broker:
    def __init__(self) -> None:
        self.calls = 0

    def publish(self, record: EvidenceRecord) -> dict[str, Any]:
        self.calls += 1
        return {
            "ack_ref": f"broker-ack-v1-{record.event_sha256}",
            "event_id": record.event["event_id"],
            "event_sha256": record.event_sha256,
            "idempotency_key_sha256": record.event[
                "idempotency_key_sha256"
            ],
            "delivery_key_sha256": record.event["delivery_key_sha256"],
        }


class _Anchor:
    def __init__(self) -> None:
        self._receipts: dict[str, dict[str, Any]] = {}
        self.calls = 0

    def anchor(
        self,
        records: tuple[EvidenceRecord, ...],
        *,
        idempotency_key_sha256: str,
    ) -> dict[str, Any]:
        self.calls += 1
        head = records[-1].event_sha256
        receipt = {
            "anchor_ref": f"anchor-v1-{head}",
            "signature_ref": f"signature-v1-{head}",
            "record_count": len(records),
            "first_event_sha256": records[0].event_sha256,
            "last_event_sha256": head,
            "head_sha256": head,
        }
        self._receipts[receipt["anchor_ref"]] = receipt
        return dict(receipt)

    def readback(self, anchor_ref: str) -> dict[str, Any]:
        return dict(self._receipts[anchor_ref])


def _utc_now_seconds() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def build_business_case_type_live_write_smoke(
    *, database_path: Path, fault: str | None = None
) -> dict[str, Any]:
    if not isinstance(database_path, Path) or not database_path.is_absolute():
        raise ValueError("database_path must be absolute")
    if fault not in {
        None,
        "owner_verification",
        "plan_sha",
        "approval_ref",
        "identity_provenance",
    }:
        raise ValueError("fault is outside the synthetic allowlist")
    target = replace(_target(), workspace_id="notary_team_01")
    mutations = _mutations()
    http_port = _ScriptedHttpPort(_responses(mutations))
    token_provider = _SyntheticTokenProvider()
    write_principal_binding = principal_binding_sha256(
        target.write_identity_id
    )
    bff_principal_binding = principal_binding_sha256(
        target.bff_uami_identity_id
    )
    inspection_principal_binding = "e" * 64
    owner_verifier = _OwnerApprovalVerifier(
        verified=fault != "owner_verification"
    )
    inspector = _IdentityInspector()
    identity_factory = _IdentityFactory(token_provider)
    base_authorization = _authorization(target)
    tenant_binding = _tenant_binding_sha256()
    actor = actor_ref(
        tenant_id=_TENANT_ID,
        actor_object_id=_ACTOR_ID,
        key_version=1,
        key=_ACTOR_KEY,
        principal_key=_PRINCIPAL_KEY,
    )
    results: list[dict[str, Any]] = []
    broker_calls = 0
    anchor_calls = 0
    worm_puts = 0

    for index, mutation in enumerate(mutations, start=1):
        draft_authorization = _authorization_for(
            base_authorization, target, mutation
        )
        draft_builder = BusinessCaseTypeWritePlanBuilder(target)
        draft_plan = draft_builder.build(mutation, draft_authorization)
        common = {
            "workspace_id": target.workspace_id,
            "commit_sha": "1" * 40,
            "tree_sha": "2" * 40,
            "domain_contract_sha256": "3" * 64,
            "verification_contract_sha256": "4" * 64,
            "plan_binding_sha256": approval_plan_binding_sha256(draft_plan),
            "toolchain_sha256": "5" * 64,
            "step_sequence_sha256": "6" * 64,
            "evidence_policy_sha256": "7" * 64,
            "target_binding_sha256": live_target_binding_sha256(
                target, tenant_binding_sha256=tenant_binding
            ),
            "write_principal_binding_sha256": (
                write_principal_binding
            ),
            "bff_principal_binding_sha256": (
                bff_principal_binding
            ),
            "owner_verifier_binding_sha256": "b" * 64,
            "owner_allowlist_sha256": "c" * 64,
            "inspection_principal_binding_sha256": (
                inspection_principal_binding
            ),
        }
        attestation = build_unverified_live_write_approval_attestation(
            **common
        )
        final_authorization = replace(
            draft_authorization,
            approval_ref=(
                "owner-approval-v1-" + "0" * 64
                if fault == "approval_ref"
                else attestation.approval_ref
            ),
        )
        builder = BusinessCaseTypeWritePlanBuilder(target)
        plan = builder.build(mutation, final_authorization)
        if fault == "plan_sha":
            plan = replace(plan, plan_sha256="f" * 64)
        identity_context = WriteIdentityContext(
            workspace_id=target.workspace_id,
            site_binding_sha256=site_binding_sha256(target.site_id),
            write_principal_binding_sha256=write_principal_binding,
            write_graph_permissions=("Sites.Selected",),
            write_site_roles=("write",),
            bff_principal_binding_sha256=bff_principal_binding,
            bff_graph_permissions=("Sites.Selected",),
            bff_site_roles=("read",),
            inspection_source=(
                "drifted-inspection-source"
                if fault == "identity_provenance"
                else "synthetic-offline-owner-bound-readback"
            ),
            inspection_observed_at=_utc_now_seconds(),
            inspection_principal_binding_sha256=(
                inspection_principal_binding
            ),
            inspection_approval_sha256=attestation.owner_comment_sha256,
        )
        inspector.bind(identity_context)
        outbox = InMemoryEvidenceOutbox()
        broker = _Broker()
        anchor = _Anchor()
        worm_transport, worm_journal = _worm_journal()
        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=broker,
            signature_anchor=anchor,
            worm_journal=worm_journal,
            reconciliation_store=InMemoryReconciliationStore(),
        )
        source_id = f"33333333-3333-4333-8333-{index:012d}"
        correlation = correlation_ref(
            tenant_id=_TENANT_ID,
            source_object_id=source_id,
            key_version=1,
            key=_ACTOR_KEY,
        )
        context = LiveWriteEvidenceContext(
            correlation_id=correlation,
            actor_ref_value=actor,
            tool_id="tool-nac-cli",
            role_id="role-automation",
            action=mutation.operation,
            business_case_type_id="immobilienkaufvertrag",
            catalog_version=_CATALOG_VERSION,
            identifier_registry=_IDENTIFIER_REGISTRY,
            manifest_sha256="8" * 64,
            etag_hmac_key=_ACTOR_KEY,
            etag_hmac_key_version=1,
            occurred_at=lambda: "2026-07-29T12:00:00Z",
            operation_binding_sha256=(
                s4d_evidence_operation_binding_sha256(
                    mutation_evidence_binding(plan)
                )
            ),
        )
        boundary = BusinessCaseTypeLiveWriteBoundary(
            target=target,
            tenant_binding_sha256=tenant_binding,
            database_path=database_path,
            attestation=attestation,
            expected_attestation={
                key: value
                for key, value in common.items()
                if key
                not in {
                    "workspace_id",
                    "plan_binding_sha256",
                    "target_binding_sha256",
                    "write_principal_binding_sha256",
                    "bff_principal_binding_sha256",
                }
            },
            owner_approval_verifier=owner_verifier,
            identity_inspector=inspector,
            identity_factory=identity_factory,
            http_port=http_port,
            outbox=outbox,
            publisher=publisher,
            evidence_context_factory=lambda _plan, value=context: value,
        )
        result = boundary.execute(plan=plan, plan_builder=builder)
        results.append(
            {
                "operation": result.operation,
                "status": result.status,
                "reason_code": result.reason_code,
                "transport_calls": result.transport_calls,
                "write_attempts": result.write_attempts,
                "worm_readback_verified": result.worm_readback_verified,
                "plan_sha256": result.plan_sha256,
                "publication_chain_head_sha256": (
                    result.publication_chain_head_sha256
                ),
            }
        )
        broker_calls += broker.calls
        anchor_calls += anchor.calls
        worm_puts += worm_transport.put_calls

    ready = bool(
        [item["operation"] for item in results]
        == [mutation.operation for mutation in mutations]
        and all(item["status"] == "S4D_WRITE_VERIFIED" for item in results)
        and all(item["worm_readback_verified"] is True for item in results)
        and http_port.exhausted
        and token_provider.calls == 15
        and owner_verifier.calls == 5
        and inspector.calls == 5
        and identity_factory.calls == 5
        and broker_calls == 15
        and anchor_calls == 5
        and worm_puts == 5
    )
    return {
        "schema_version":
            "nac.business-case-type-live-write-smoke/v0.1",
        "status": S4D_READY_OFFLINE if ready else "BLOCKED",
        "operations": results,
        "summary": {
            "owner_approval_verification_calls": owner_verifier.calls,
            "identity_readback_calls": inspector.calls,
            "identity_factory_calls": identity_factory.calls,
            "synthetic_token_provider_calls": token_provider.calls,
            "synthetic_http_port_calls": http_port.calls,
            "broker_ack_count": broker_calls,
            "signature_anchor_count": anchor_calls,
            "azure_blob_worm_put_count": worm_puts,
            "socket_or_dns_calls": 0,
            "external_credential_store_reads": 0,
            "live_graph_calls": 0,
            "azure_live_calls": 0,
            "tenant_writes": 0,
            "production_durability_claim": False,
        },
        "live_status": (
            "BLOCKED_PENDING_OWNER_GATED_PRODUCTION_ADAPTERS"
        ),
    }


def format_business_case_type_live_write_smoke(
    result: dict[str, Any],
) -> str:
    lines = [
        f"Status: {result.get('status', 'BLOCKED')}",
        f"Live-Status: {result.get('live_status', 'BLOCKED')}",
    ]
    for operation in result.get("operations", []):
        lines.append(
            f"- {operation.get('operation', 'unknown')}: "
            f"{operation.get('status', 'BLOCKED')}"
        )
    return "\n".join(lines) + "\n"


def _worm_journal() -> tuple[
    FakeAzureBlobWormTransport, AzureBlobWormJournal
]:
    provider_tenant = "44444444-4444-4444-8444-444444444444"
    subscription = (
        "/subscriptions/55555555-5555-4555-8555-555555555555"
    )
    resource = (
        subscription
        + "/resourceGroups/rg-nac-worm/providers/Microsoft.Storage/"
        + "storageAccounts/stnacworms4doffline"
    )
    provider = AzureBlobProviderContext(
        tenant_id=provider_tenant,
        subscription_resource_id=subscription,
        resource_id=resource,
        readback_source="azure-subscription-resource-tenant-readback",
    )
    provider_binding = azure_provider_context_binding_sha256(provider)
    attestation = AzureProviderContextAttestation(
        schema_version="nac.azure-provider-context-attestation/v0.1",
        source="owner-approved-commit-hash-bound-deployment-attestation",
        owner_approval_sha256="9" * 64,
        deployment_commit_sha256="a" * 64,
        deployment_tree_sha256="b" * 64,
        deployment_plan_sha256="c" * 64,
        provider_context_binding_sha256=provider_binding,
    )
    tenant_binding = _tenant_binding_sha256()
    provider_tenant_binding = hashlib.sha256(
        ("nac.azure-provider-tenant.v1|" + provider_tenant).encode(
            "ascii"
        )
    ).hexdigest()
    subscription_binding = hashlib.sha256(
        ("nac.azure-subscription-resource.v1|" + subscription).encode(
            "ascii"
        )
    ).hexdigest()
    resource_binding = hashlib.sha256(
        ("nac.azure-storage-resource.v1|" + resource).encode("ascii")
    ).hexdigest()
    policy = AzureBlobContainerPolicy(
        default_immutability_policy_mode="Locked",
        default_retention_days=3653,
        legal_hold_capable=True,
        legal_hold_capability_source="container-policy-properties",
        encryption_scope="nac-worm-s4d-offline",
        encryption_key_source="Microsoft.Keyvault",
        customer_managed_key_ref_sha256="d" * 64,
        provider_tenant_binding_sha256=provider_tenant_binding,
        provider_subscription_binding_sha256=subscription_binding,
        provider_resource_binding_sha256=resource_binding,
        provider_context_binding_sha256=provider_binding,
        provider_context_binding_source=(
            "azure-subscription-resource-tenant-readback"
        ),
    )
    transport = FakeAzureBlobWormTransport(
        container_name="nac-worm-s4d-offline",
        tenant_binding_sha256=tenant_binding,
        policy=policy,
        provider_context=provider,
    )
    journal = AzureBlobWormJournal(
        transport=transport,
        container_name="nac-worm-s4d-offline",
        tenant_binding_sha256=tenant_binding,
        encryption_scope="nac-worm-s4d-offline",
        customer_managed_key_ref_sha256="d" * 64,
        provider_context_attestation=attestation,
        approved_provider_context_attestation_sha256=(
            azure_provider_context_attestation_sha256(attestation)
        ),
    )
    return transport, journal


def _tenant_binding_sha256() -> str:
    return hashlib.sha256(
        b"nac.tenant-binding.v1\x00" + _TENANT_ID.encode("ascii")
    ).hexdigest()
