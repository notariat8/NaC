from __future__ import annotations

from dataclasses import dataclass
from typing import Final


WORKSPACE_ID: Final = "notary_team_01"
SHA256_LENGTH: Final = 64
READY_STATUS: Final = "S4E_READY_OFFLINE"
BLOCKED_STATUS: Final = "BLOCKED"


@dataclass(frozen=True, slots=True)
class ProductionAdapterReadinessInput:
    workspace_id: str
    provisioning_principal_sha256: str | None
    write_principal_sha256: str | None
    bff_principal_sha256: str | None
    business_write_executor_principal_sha256: str | None
    write_graph_permissions: tuple[str, ...]
    write_site_roles: tuple[str, ...]
    bff_graph_permissions: tuple[str, ...]
    bff_site_roles: tuple[str, ...]
    owner_verifier_adapter_sha256: str | None
    toolchain_binding_sha256: str | None
    provisioner_bootstrap_binding_sha256: str | None
    public_certificate_sha256: str | None
    write_token_adapter_sha256: str | None
    graph_http_adapter_sha256: str | None
    worm_transport_adapter_sha256: str | None
    worm_target_binding_sha256: str | None
    worm_cmk_binding_sha256: str | None
    worm_encryption_scope_binding_sha256: str | None
    worm_policy_sha256: str | None
    worm_policy_locked: bool
    durable_outbox_adapter_sha256: str | None
    broker_adapter_sha256: str | None
    signature_anchor_adapter_sha256: str | None
    reconciliation_store_adapter_sha256: str | None


def _valid_sha256(value: str | None) -> bool:
    return bool(
        value
        and len(value) == SHA256_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def build_business_case_type_live_write_readiness(
    readiness: ProductionAdapterReadinessInput,
) -> dict[str, object]:
    principal_hashes = (
        readiness.provisioning_principal_sha256,
        readiness.write_principal_sha256,
        readiness.bff_principal_sha256,
    )
    valid_principals = all(_valid_sha256(value) for value in principal_hashes)
    distinct_principals = valid_principals and len(set(principal_hashes)) == 3
    business_write_route_exact = (
        _valid_sha256(readiness.business_write_executor_principal_sha256)
        and readiness.business_write_executor_principal_sha256
        == readiness.write_principal_sha256
        and readiness.business_write_executor_principal_sha256
        not in {
            readiness.provisioning_principal_sha256,
            readiness.bff_principal_sha256,
        }
    )

    checks = {
        "workspace_exact": readiness.workspace_id == WORKSPACE_ID,
        "three_principal_bindings_valid": valid_principals,
        "principals_pairwise_distinct": distinct_principals,
        "business_write_route_exact": business_write_route_exact,
        "write_permission_exact": readiness.write_graph_permissions
        == ("Sites.Selected",),
        "write_site_role_exact": readiness.write_site_roles == ("write",),
        "bff_permission_exact": readiness.bff_graph_permissions
        == ("Sites.Selected",),
        "bff_site_role_exact": readiness.bff_site_roles == ("read",),
        "owner_verifier_adapter_bound": _valid_sha256(
            readiness.owner_verifier_adapter_sha256
        ),
        "toolchain_binding_bound": _valid_sha256(readiness.toolchain_binding_sha256),
        "provisioner_bootstrap_binding_bound": _valid_sha256(
            readiness.provisioner_bootstrap_binding_sha256
        ),
        "public_certificate_bound": _valid_sha256(
            readiness.public_certificate_sha256
        ),
        "write_token_adapter_bound": _valid_sha256(
            readiness.write_token_adapter_sha256
        ),
        "graph_http_adapter_bound": _valid_sha256(
            readiness.graph_http_adapter_sha256
        ),
        "worm_transport_adapter_bound": _valid_sha256(
            readiness.worm_transport_adapter_sha256
        ),
        "worm_target_binding_bound": _valid_sha256(
            readiness.worm_target_binding_sha256
        ),
        "worm_cmk_binding_bound": _valid_sha256(
            readiness.worm_cmk_binding_sha256
        ),
        "worm_encryption_scope_binding_bound": _valid_sha256(
            readiness.worm_encryption_scope_binding_sha256
        ),
        "worm_policy_bound": _valid_sha256(readiness.worm_policy_sha256),
        "worm_policy_locked": readiness.worm_policy_locked,
        "durable_outbox_adapter_bound": _valid_sha256(
            readiness.durable_outbox_adapter_sha256
        ),
        "broker_adapter_bound": _valid_sha256(readiness.broker_adapter_sha256),
        "signature_anchor_adapter_bound": _valid_sha256(
            readiness.signature_anchor_adapter_sha256
        ),
        "reconciliation_store_adapter_bound": _valid_sha256(
            readiness.reconciliation_store_adapter_sha256
        ),
    }
    blockers = sorted(name for name, passed in checks.items() if not passed)
    status = READY_STATUS if not blockers else BLOCKED_STATUS
    return {
        "schema_version": "nac.business-case-type-live-write-readiness-s4e/v0.1",
        "status": status,
        "workspace_id": (
            WORKSPACE_ID
            if readiness.workspace_id == WORKSPACE_ID
            else "<redacted-invalid-workspace>"
        ),
        "assessment_source": "contract_pinned_repository_snapshot",
        "live_state_inspected": False,
        "live_write_authorized": False,
        "provisioning_app_executes_business_writes": (
            readiness.business_write_executor_principal_sha256
            == readiness.provisioning_principal_sha256
        ),
        "checks": checks,
        "blockers": blockers,
        "summary": {
            "checks_total": len(checks),
            "checks_passed": len(checks) - len(blockers),
            "socket_or_dns_calls": 0,
            "external_credential_store_reads": 0,
            "graph_calls": 0,
            "azure_calls": 0,
            "tenant_writes": 0,
        },
    }


def current_business_case_type_live_write_readiness() -> dict[str, object]:
    """Report repository readiness without reading credentials or external state."""
    return build_business_case_type_live_write_readiness(
        ProductionAdapterReadinessInput(
            workspace_id=WORKSPACE_ID,
            provisioning_principal_sha256="1" * SHA256_LENGTH,
            write_principal_sha256=None,
            bff_principal_sha256="2" * SHA256_LENGTH,
            business_write_executor_principal_sha256=None,
            write_graph_permissions=(),
            write_site_roles=(),
            bff_graph_permissions=("Sites.Selected",),
            bff_site_roles=("read",),
            owner_verifier_adapter_sha256=None,
            toolchain_binding_sha256=None,
            provisioner_bootstrap_binding_sha256=None,
            public_certificate_sha256=None,
            write_token_adapter_sha256=None,
            graph_http_adapter_sha256=None,
            worm_transport_adapter_sha256=None,
            worm_target_binding_sha256=None,
            worm_cmk_binding_sha256=None,
            worm_encryption_scope_binding_sha256=None,
            worm_policy_sha256=None,
            worm_policy_locked=False,
            durable_outbox_adapter_sha256=None,
            broker_adapter_sha256=None,
            signature_anchor_adapter_sha256=None,
            reconciliation_store_adapter_sha256=None,
        )
    )


def synthetic_ready_input() -> ProductionAdapterReadinessInput:
    return ProductionAdapterReadinessInput(
        workspace_id=WORKSPACE_ID,
        provisioning_principal_sha256="1" * SHA256_LENGTH,
        write_principal_sha256="2" * SHA256_LENGTH,
        bff_principal_sha256="3" * SHA256_LENGTH,
        business_write_executor_principal_sha256="2" * SHA256_LENGTH,
        write_graph_permissions=("Sites.Selected",),
        write_site_roles=("write",),
        bff_graph_permissions=("Sites.Selected",),
        bff_site_roles=("read",),
        owner_verifier_adapter_sha256="4" * SHA256_LENGTH,
        toolchain_binding_sha256="5" * SHA256_LENGTH,
        provisioner_bootstrap_binding_sha256="6" * SHA256_LENGTH,
        public_certificate_sha256="7" * SHA256_LENGTH,
        write_token_adapter_sha256="8" * SHA256_LENGTH,
        graph_http_adapter_sha256="9" * SHA256_LENGTH,
        worm_transport_adapter_sha256="a" * SHA256_LENGTH,
        worm_target_binding_sha256="b" * SHA256_LENGTH,
        worm_cmk_binding_sha256="c" * SHA256_LENGTH,
        worm_encryption_scope_binding_sha256="d" * SHA256_LENGTH,
        worm_policy_sha256="e" * SHA256_LENGTH,
        worm_policy_locked=True,
        durable_outbox_adapter_sha256="f" * SHA256_LENGTH,
        broker_adapter_sha256="0" * SHA256_LENGTH,
        signature_anchor_adapter_sha256="1" * SHA256_LENGTH,
        reconciliation_store_adapter_sha256="2" * SHA256_LENGTH,
    )


def format_business_case_type_live_write_readiness(
    result: dict[str, object],
) -> str:
    summary = result["summary"]
    assert isinstance(summary, dict)
    blockers = result["blockers"]
    assert isinstance(blockers, list)
    blocker_text = ", ".join(blockers) if blockers else "none"
    return (
        f"BusinessCaseType S4e readiness: {result['status']}\n"
        f"Workspace: {result['workspace_id']}\n"
        f"Checks: {summary['checks_passed']}/{summary['checks_total']}\n"
        f"Blockers: {blocker_text}\n"
        "Live write authorized: false\n"
    )
