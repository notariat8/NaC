from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Mapping

from nac_runtime.sqlite_evidence_staging_outbox import (
    _is_explicitly_local_filesystem,
)

from .business_case_type_write_identity_inspection import (
    BusinessCaseTypeWriteIdentityInspectionAdapter,
    IdentityInspectionError,
    BusinessCaseTypeWriteIdentitySnapshot,
    EntraPrincipalReference,
    EntraPrincipalSnapshot,
    SiteRoleAssignmentSnapshot,
    SnapshotIdentityInspectionPort,
    ValidatedBusinessCaseTypeWriteIdentity,
)


WORKSPACE_ID: Final = "notary_team_01"
S4G_STATUS: Final = "S4G_PRODUCTION_EDGE_COMPOSITION_VERIFIED_OFFLINE"
LIVE_STATUS: Final = "BLOCKED_PENDING_CENTRAL_EVIDENCE_AND_OWNER_GATED_ACTIVATION"
_SYNCED_COMPONENTS: Final = frozenset(
    {
        "dropbox",
        "google drive",
        "icloud drive",
        "onedrive",
        "sharepoint",
        "syncthing",
    }
)
_CENTRAL_BLOCKERS: Final = (
    "central_postgresql_promotion_ack_retention_cleanup",
    "broker_product_owner_decision",
    "signature_anchor_owner_decision",
    "durable_reconciliation_store",
    "irreversible_worm_policy_lock",
    "owner_gated_live_activation",
)
_COMPONENT_BINDING_FILES: Final = {
    "identity_inspector_implementation_sha256": (
        "identity-inspector-implementation",
        "src/nac_m365_graph/business_case_type_write_identity_inspection.py",
    ),
    "owner_verifier_sha256": (
        "owner-verifier",
        "src/nac_m365_graph/business_case_type_production_adapters.py",
    ),
    "write_token_factory_sha256": (
        "write-token-factory",
        "src/nac_m365_graph/business_case_type_production_adapters.py",
    ),
    "graph_http_transport_sha256": (
        "graph-http-transport",
        "src/nac_m365_graph/business_case_type_production_adapters.py",
    ),
    "azure_worm_transport_sha256": (
        "azure-worm-rest-transport",
        "src/nac_runtime/azure_blob_worm_rest_transport.py",
    ),
}
_CONTRACT_BINDING_FILES: Final = {
    "s4d_contract_sha256": (
        "s4d-contract",
        "workflows/contracts/business-case-type-live-write-boundary-s4d.contract.json",
    ),
    "s4f_contract_sha256": (
        "s4f-contract",
        "workflows/contracts/business-case-type-production-adapters-s4f.contract.json",
    ),
    "s6b_contract_sha256": (
        "s6b-contract",
        "workflows/contracts/business-case-type-azure-blob-worm-s6b.contract.json",
    ),
}


@dataclass(frozen=True, slots=True)
class ProductionCompositionBindings:
    workspace_id: str
    provisioner_principal_sha256: str
    writer_principal_sha256: str
    bff_principal_sha256: str
    identity_inspection_sha256: str
    identity_inspector_implementation_sha256: str
    owner_verifier_sha256: str
    write_token_factory_sha256: str
    graph_http_transport_sha256: str
    azure_worm_transport_sha256: str
    worm_target_binding_sha256: str
    s4d_contract_sha256: str
    s4f_contract_sha256: str
    s6b_contract_sha256: str
    mutation_database_path: Path
    evidence_database_path: Path


def assess_production_composition(
    bindings: ProductionCompositionBindings,
    *,
    identity_port: SnapshotIdentityInspectionPort,
    repository_root: Path,
) -> dict[str, object]:
    validated: ValidatedBusinessCaseTypeWriteIdentity | None = None
    expected: Mapping[str, str] = {}
    try:
        if type(identity_port) is not SnapshotIdentityInspectionPort:
            raise ValueError("identity_port_not_offline_snapshot")
        validated = BusinessCaseTypeWriteIdentityInspectionAdapter(
            identity_port
        ).inspect()
        expected = _expected_repository_bindings(repository_root)
    except (IdentityInspectionError, OSError, ValueError):
        pass

    principal_bindings = (
        bindings.provisioner_principal_sha256,
        bindings.writer_principal_sha256,
        bindings.bff_principal_sha256,
    )
    expected_principal_bindings = (
        validated.provisioner_principal_binding_sha256,
        validated.writer_principal_binding_sha256,
        validated.bff_principal_binding_sha256,
    ) if validated is not None else ()
    component_fields = tuple(_COMPONENT_BINDING_FILES) + (
        "worm_target_binding_sha256",
    )
    contract_fields = tuple(_CONTRACT_BINDING_FILES)
    checks = {
        "workspace_exact": bindings.workspace_id == WORKSPACE_ID,
        "identity_snapshot_valid": validated is not None,
        "principal_bindings_valid": all(
            _valid_sha256(value) for value in principal_bindings
        ),
        "principal_bindings_exact": (
            principal_bindings == expected_principal_bindings
        ),
        "principal_bindings_pairwise_distinct": (
            len(set(principal_bindings)) == len(principal_bindings)
        ),
        "identity_inspection_exact": (
            validated is not None
            and bindings.identity_inspection_sha256
            == validated.identity_inspection_binding_sha256
        ),
        "component_bindings_repository_exact": (
            bool(expected)
            and all(
                getattr(bindings, field) == expected.get(field)
                for field in component_fields
            )
        ),
        "ancestor_contracts_repository_exact": (
            bool(expected)
            and all(
                getattr(bindings, field) == expected.get(field)
                for field in contract_fields
            )
        ),
        "local_runtime_layout_exact": _valid_runtime_layout(
            bindings.mutation_database_path,
            bindings.evidence_database_path,
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    verified = not failed
    return {
        "schema_version": "nac.business-case-type-production-composition/v0.1",
        "status": S4G_STATUS if verified else "BLOCKED",
        "live_status": LIVE_STATUS,
        "workspace_id": WORKSPACE_ID,
        "assessment_source": "offline_repository_bound_snapshot",
        "checks": checks,
        "failed_checks": failed,
        "remaining_blockers": list(_CENTRAL_BLOCKERS),
        "runtime_factory_constructed": False,
        "writer_credentials_read": False,
        "production_durability_claimed": False,
        "live_write_authorized": False,
        "summary": {
            "checks_total": len(checks),
            "checks_passed": len(checks) - len(failed),
            "socket_or_dns_calls": 0,
            "external_credential_store_reads": 0,
            "graph_calls": 0,
            "azure_calls": 0,
            "tenant_writes": 0,
        },
    }


def synthetic_offline_bindings(
    repository_root: Path,
    runtime_root: Path,
) -> ProductionCompositionBindings:
    validated = BusinessCaseTypeWriteIdentityInspectionAdapter(
        SnapshotIdentityInspectionPort(synthetic_identity_snapshot())
    ).inspect()
    expected = _expected_repository_bindings(repository_root)
    return ProductionCompositionBindings(
        workspace_id=WORKSPACE_ID,
        provisioner_principal_sha256=(
            validated.provisioner_principal_binding_sha256
        ),
        writer_principal_sha256=validated.writer_principal_binding_sha256,
        bff_principal_sha256=validated.bff_principal_binding_sha256,
        identity_inspection_sha256=(
            validated.identity_inspection_binding_sha256
        ),
        identity_inspector_implementation_sha256=expected[
            "identity_inspector_implementation_sha256"
        ],
        owner_verifier_sha256=expected["owner_verifier_sha256"],
        write_token_factory_sha256=expected["write_token_factory_sha256"],
        graph_http_transport_sha256=expected["graph_http_transport_sha256"],
        azure_worm_transport_sha256=expected["azure_worm_transport_sha256"],
        worm_target_binding_sha256=expected["worm_target_binding_sha256"],
        s4d_contract_sha256=expected["s4d_contract_sha256"],
        s4f_contract_sha256=expected["s4f_contract_sha256"],
        s6b_contract_sha256=expected["s6b_contract_sha256"],
        mutation_database_path=runtime_root / "mutation-state.sqlite3",
        evidence_database_path=runtime_root / "evidence-staging.sqlite3",
    )


def assess_synthetic_offline_composition(
    repository_root: Path,
    runtime_root: Path,
) -> dict[str, object]:
    snapshot = synthetic_identity_snapshot()
    return assess_production_composition(
        synthetic_offline_bindings(repository_root, runtime_root),
        identity_port=SnapshotIdentityInspectionPort(snapshot),
        repository_root=repository_root,
    )


def _expected_repository_bindings(
    repository_root: Path,
) -> dict[str, str]:
    if not isinstance(repository_root, Path) or not repository_root.is_absolute():
        raise ValueError("repository_root_invalid")
    root = repository_root.resolve(strict=True)
    if not (root / "AGENTS.md").is_file():
        raise ValueError("repository_root_invalid")
    result: dict[str, str] = {}
    for field, (domain, relative) in {
        **_COMPONENT_BINDING_FILES,
        **_CONTRACT_BINDING_FILES,
    }.items():
        result[field] = _repository_file_binding(root, domain, relative)
    result["worm_target_binding_sha256"] = _domain_binding(
        "worm-target",
        "offline-unconfigured:notary_team_01",
    )
    return result


def _repository_file_binding(
    root: Path,
    domain: str,
    relative: str,
) -> str:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("repository_binding_source_invalid")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError("repository_binding_source_invalid")
    content_sha256 = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return _domain_binding(domain, f"{relative}|{content_sha256}")


def _domain_binding(domain: str, value: str) -> str:
    return hashlib.sha256(
        f"nac.s4g.repository-binding.v1|{domain}|{value}".encode(
            "utf-8"
        )
    ).hexdigest()


def format_production_composition(result: Mapping[str, object]) -> str:
    summary = result["summary"]
    if not isinstance(summary, Mapping):
        raise ValueError("summary_invalid")
    blockers = result["remaining_blockers"]
    if not isinstance(blockers, list):
        raise ValueError("blockers_invalid")
    return (
        f"BusinessCaseType S4g composition: {result['status']}\n"
        f"Live status: {result['live_status']}\n"
        f"Checks: {summary['checks_passed']}/{summary['checks_total']}\n"
        f"Central blockers: {len(blockers)}\n"
        "Runtime factory constructed: false\n"
        "Live write authorized: false\n"
    )


def synthetic_identity_snapshot() -> BusinessCaseTypeWriteIdentitySnapshot:
    provisioner = EntraPrincipalSnapshot(
        app_id="10000000-0000-0000-0000-000000000001",
        service_principal_object_id="20000000-0000-0000-0000-000000000001",
        graph_application_roles=(),
    )
    writer = EntraPrincipalSnapshot(
        app_id="30000000-0000-0000-0000-000000000001",
        service_principal_object_id="40000000-0000-0000-0000-000000000001",
        graph_application_roles=("Sites.Selected",),
    )
    bff = EntraPrincipalSnapshot(
        app_id="50000000-0000-0000-0000-000000000001",
        service_principal_object_id="60000000-0000-0000-0000-000000000001",
        graph_application_roles=("Sites.Selected",),
    )
    writer_reference = EntraPrincipalReference(
        app_id=writer.app_id,
        service_principal_object_id=writer.service_principal_object_id,
    )
    return BusinessCaseTypeWriteIdentitySnapshot(
        site_binding_sha256="d" * 64,
        provisioner=provisioner,
        writer=writer,
        bff=bff,
        writer_site_assignment=SiteRoleAssignmentSnapshot(
            service_principal_object_id=writer.service_principal_object_id,
            roles=("write",),
        ),
        bff_site_assignment=SiteRoleAssignmentSnapshot(
            service_principal_object_id=bff.service_principal_object_id,
            roles=("read",),
        ),
        business_writer=writer_reference,
        write_token_source=writer_reference,
    )


def _valid_runtime_layout(
    mutation_database_path: Path,
    evidence_database_path: Path,
) -> bool:
    if (
        not isinstance(mutation_database_path, Path)
        or not isinstance(evidence_database_path, Path)
        or not mutation_database_path.is_absolute()
        or not evidence_database_path.is_absolute()
        or mutation_database_path.name != "mutation-state.sqlite3"
        or evidence_database_path.name != "evidence-staging.sqlite3"
        or mutation_database_path == evidence_database_path
        or mutation_database_path.parent != evidence_database_path.parent
    ):
        return False
    root = mutation_database_path.parent
    if _looks_synced(root):
        return False
    try:
        canonical_root = root.resolve(strict=True)
        if canonical_root != root or root.is_symlink():
            return False
        metadata = root.lstat()
        local_filesystem = _is_explicitly_local_filesystem(root)
    except OSError:
        return False
    if not (
        os.name == "posix"
        and local_filesystem
        and stat.S_ISDIR(metadata.st_mode)
        and not stat.S_ISLNK(metadata.st_mode)
        and metadata.st_uid == os.geteuid()
        and stat.S_IMODE(metadata.st_mode) == 0o700
    ):
        return False

    mutation_exists = os.path.lexists(mutation_database_path)
    evidence_exists = os.path.lexists(evidence_database_path)
    if mutation_exists != evidence_exists:
        return False
    if not mutation_exists:
        return True
    try:
        mutation = mutation_database_path.lstat()
        evidence = evidence_database_path.lstat()
        mutation_resolved = mutation_database_path.resolve(strict=True)
        evidence_resolved = evidence_database_path.resolve(strict=True)
    except OSError:
        return False
    return (
        stat.S_ISREG(mutation.st_mode)
        and stat.S_ISREG(evidence.st_mode)
        and not stat.S_ISLNK(mutation.st_mode)
        and not stat.S_ISLNK(evidence.st_mode)
        and mutation.st_uid == os.geteuid()
        and evidence.st_uid == os.geteuid()
        and mutation.st_nlink == 1
        and evidence.st_nlink == 1
        and stat.S_IMODE(mutation.st_mode) == 0o600
        and stat.S_IMODE(evidence.st_mode) == 0o600
        and mutation_resolved.parent == canonical_root
        and evidence_resolved.parent == canonical_root
        and (mutation.st_dev, mutation.st_ino)
        != (evidence.st_dev, evidence.st_ino)
    )


def _looks_synced(path: Path) -> bool:
    return any(
        component.casefold() in _SYNCED_COMPONENTS
        for component in path.parts
    )


def _valid_sha256(value: object) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
