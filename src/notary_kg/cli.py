from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path

from nac_gnotkg.views import build_cost_review_view
from nac_m365_graph.auth import token_provider_from_env
from nac_m365_graph.graph_client import GraphRestClient
from nac_runtime.azure_blob_worm import build_azure_blob_worm_readiness
from nac_m365_graph.provisioner_env_bootstrap import (
    build_provisioner_env_bootstrap,
    load_provisioner_env_state,
    write_provisioner_env_bootstrap_artifact,
)

from .business_case_inventory import build_business_case_inventory
from .business_case_type_cache import BusinessCaseTypeRegistryCache
from .business_case_type_immutable_evidence import build_synthetic_evidence_dry_run
from .business_case_type_runtime import (
    BusinessCaseTypeCatalog,
    BusinessCaseTypeLookupRequest,
    business_case_type_get,
)
from .business_case_type_transport import BusinessCaseTypeRegistryRow, RegistryFetchResult
from .business_case_type_migration import MigrationValidationError
from .business_case_type_migration_quarantine import ArtifactWriteError
from .business_case_type_migration_runner import (
    DEFAULT_OUTPUT as BUSINESS_CASE_TYPE_MIGRATION_DEFAULT_OUTPUT,
    MigrationContractError,
    RepositoryStateError,
    run_offline_migration,
)
from .catalog import all_case_summaries, find_case, load_catalogs
from .deep_process_routing import build_deep_process_candidate_routing
from .editor import build_editor_view
from .first_wave_gap_review import (
    ARTIFACT_SCHEMA_VERSION as FIRST_WAVE_GAP_REVIEW_ARTIFACT_SCHEMA_VERSION,
    build_first_wave_bpmn_outline_gap_review,
    write_first_wave_bpmn_outline_gap_review_artifact,
)
from .first_wave_outline import build_first_wave_bpmn_outline
from .first_wave_process_deep_model import build_first_wave_process_deep_model
from .ontology_scale_budget import build_ontology_scale_budget_smoke
from .ontology_storage_contract import build_ontology_storage_contract
from .pilot_checklist import build_pilot_intake_checklist
from .process_ontology_contract import build_process_ontology_contract
from .process_ontology_schema_apply_plan import build_process_ontology_sharepoint_schema_apply_plan
from .process_ontology_schema_apply_execution_contract import (
    build_process_ontology_sharepoint_schema_apply_execution_contract,
)
from .process_ontology_schema_apply_graph_dispatcher import (
    SUPPORTED_SCHEMA_VERSIONS as PROCESS_ONTOLOGY_SCHEMA_APPLY_GRAPH_DISPATCHER_SCHEMA_VERSIONS,
    write_process_ontology_sharepoint_schema_apply_graph_dispatcher_artifact,
)
from .process_ontology_schema_apply_owner_gated_live_plan import (
    SCHEMA_VERSION as PROCESS_ONTOLOGY_SCHEMA_APPLY_OWNER_GATED_LIVE_PLAN_SCHEMA_VERSION,
    write_process_ontology_sharepoint_schema_apply_owner_gated_live_plan,
)
from .process_ontology_schema_apply_owner_gated_runner_contract import (
    SCHEMA_VERSION as PROCESS_ONTOLOGY_SCHEMA_APPLY_OWNER_GATED_RUNNER_CONTRACT_SCHEMA_VERSION,
    write_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract,
)
from .process_ontology_schema_apply_live_runner import (
    SCHEMA_VERSION as PROCESS_ONTOLOGY_SCHEMA_APPLY_LIVE_RUNNER_SCHEMA_VERSION,
    write_process_ontology_sharepoint_schema_apply_live_runner,
)
from .process_ontology_schema_apply_readiness import build_process_ontology_sharepoint_schema_apply_readiness
from .process_ontology_schema_apply_runner_dry_run import (
    ARTIFACT_INDEX_SCHEMA_VERSION as PROCESS_ONTOLOGY_SCHEMA_APPLY_ARTIFACT_INDEX_SCHEMA_VERSION,
    ARTIFACT_SCHEMA_VERSION as PROCESS_ONTOLOGY_SCHEMA_APPLY_RUNNER_DRY_RUN_ARTIFACT_SCHEMA_VERSION,
    LIVE_READINESS_GATE_SCHEMA_VERSION as PROCESS_ONTOLOGY_SCHEMA_APPLY_LIVE_READINESS_GATE_SCHEMA_VERSION,
    build_process_ontology_sharepoint_schema_apply_runner_dry_run,
    write_process_ontology_sharepoint_schema_apply_artifact_index,
    write_process_ontology_sharepoint_schema_apply_live_readiness_gate,
    write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact,
)
from .process_ontology_schema_gap import build_process_ontology_sharepoint_schema_gap
from .workflow_contract import build_workflow_contract_draft


BUSINESS_CASE_INVENTORY_SCHEMA_VERSIONS = {
    "nac.notarial-business-case-inventory/v0.1",
    "nac.notarial-business-case-inventory/v0.2",
}
PROCESS_ONTOLOGY_SCHEMA_VERSIONS = {
    "nac.notarial-process-ontology/v1",
    "nac.notarial-process-ontology/v2",
}
PROCESS_ONTOLOGY_SCHEMA_GAP_VERSIONS = {
    "nac.process-ontology-sharepoint-schema-gap/v0.1",
    "nac.process-ontology-sharepoint-schema-gap/v0.2",
}
PROCESS_ONTOLOGY_SCHEMA_APPLY_PLAN_VERSIONS = {
    "nac.process-ontology-sharepoint-schema-apply-plan/v0.1",
    "nac.process-ontology-sharepoint-schema-apply-plan/v0.2",
}
PROCESS_ONTOLOGY_SCHEMA_APPLY_READINESS_VERSIONS = {
    "nac.process-ontology-sharepoint-schema-apply-readiness/v0.1",
    "nac.process-ontology-sharepoint-schema-apply-readiness/v0.2",
}
PROCESS_ONTOLOGY_SCHEMA_APPLY_EXECUTION_CONTRACT_VERSIONS = {
    "nac.process-ontology-sharepoint-schema-apply-execution-contract/v0.1",
    "nac.process-ontology-sharepoint-schema-apply-execution-contract/v0.2",
}
PROCESS_ONTOLOGY_SCHEMA_APPLY_RUNNER_DRY_RUN_VERSIONS = {
    "nac.process-ontology-sharepoint-schema-apply-runner-dry-run/v0.1",
    "nac.process-ontology-sharepoint-schema-apply-runner-dry-run/v0.2",
}
LIVE_EXECUTION_APPROVAL_STATE = "BLOCKED_PENDING_S6_S7_APPROVAL"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notary-kg",
        description="Executable status tooling for NaC notarial knowledge graphs.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the repository root.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show executable KG development status.")

    case_parser = subparsers.add_parser("case", help="Show one KG case by slug.")
    case_parser.add_argument("slug")

    editor_parser = subparsers.add_parser(
        "editor-view",
        help="Show the safe no-code editor view for one KG case.",
    )
    editor_parser.add_argument("slug")

    cost_parser = subparsers.add_parser(
        "cost-view",
        help="Show the safe GNotKG cost review graph for one KG case.",
    )
    cost_parser.add_argument("slug")

    workflow_contract_parser = subparsers.add_parser(
        "workflow-contract",
        help="Generate a safe workflow-contract draft from one KG case.",
    )
    workflow_contract_parser.add_argument("slug")

    pilot_checklist_parser = subparsers.add_parser(
        "pilot-checklist",
        help="Generate a deterministic pilot intake checklist from one KG case.",
    )
    pilot_checklist_parser.add_argument("slug")

    subparsers.add_parser(
        "business-case-inventory",
        help="Build the canonical notarial business-case type inventory, including legacy aliases.",
    )

    business_case_type_get_parser = subparsers.add_parser(
        "business-case-type-get",
        help="Validate one business-case type through the offline registry fixture port.",
    )
    business_case_type_get_parser.add_argument("identifier")
    business_case_type_get_parser.add_argument("--site-id", required=True)
    business_case_type_get_parser.add_argument(
        "--purpose",
        choices=["canonical_assignment", "legacy_read", "migration"],
        required=True,
    )
    business_case_type_get_parser.add_argument("--registry-fixture", type=Path, required=True)

    business_case_type_migration = subparsers.add_parser(
        "business-case-type-migration-dry-run",
        help="Run the synthetic-only S5 inventory, pinned N/N-1 profile evaluation, and readiness check offline.",
    )
    business_case_type_migration.add_argument("--fixture", type=Path, required=True)
    business_case_type_migration.add_argument("--quarantine-state", type=Path, required=True)
    business_case_type_migration.add_argument(
        "--output", type=Path, default=BUSINESS_CASE_TYPE_MIGRATION_DEFAULT_OUTPUT
    )

    subparsers.add_parser(
        "business-case-type-evidence-dry-run",
        help="Run the synthetic-only S6 immutable-evidence contract core without provider access.",
    )

    subparsers.add_parser(
        "business-case-type-azure-worm-readiness",
        help="Report provider-free S6b Azure Blob WORM adapter and lock readiness.",
    )

    subparsers.add_parser(
        "ontology-storage-contract",
        help="Evaluate the notarial ontology sizing and storage contract.",
    )

    subparsers.add_parser(
        "process-ontology-contract",
        help="Evaluate canonical type identity and viewer-independent process ontology validity.",
    )

    subparsers.add_parser(
        "process-ontology-schema-gap",
        help="Compare required type-registry and optional process/viewer projections with SharePoint.",
    )

    subparsers.add_parser(
        "process-ontology-schema-apply-plan",
        help="Build the offline S2 Graph REST plan without patching legacy Akten.Vorgangstyp.",
    )

    subparsers.add_parser(
        "process-ontology-schema-apply-readiness",
        help="Check offline workspace, ID, permission and ordering readiness for a future schema apply.",
    )

    subparsers.add_parser(
        "process-ontology-schema-apply-execution-contract",
        help="Build the offline owner-gated execution contract for a future Graph REST schema apply.",
    )

    subparsers.add_parser(
        "process-ontology-schema-apply-runner-dry-run",
        help="Build the offline dry-run runner plan for a future Graph REST schema apply.",
    )

    process_ontology_schema_apply_runner_dry_run_artifact = subparsers.add_parser(
        "process-ontology-schema-apply-runner-dry-run-artifact",
        help="Write a redacted offline dry-run artifact for a future Graph REST schema apply.",
    )
    process_ontology_schema_apply_runner_dry_run_artifact.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "JSON artifact path. Default: "
            "out/notary-kg/process-ontology-schema-apply-runner-dry-run.redacted.json."
        ),
    )
    process_ontology_schema_apply_runner_dry_run_artifact.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help=(
            "Markdown artifact path. Default: "
            "out/notary-kg/process-ontology-schema-apply-runner-dry-run.redacted.md."
        ),
    )

    process_ontology_schema_apply_artifact_index = subparsers.add_parser(
        "process-ontology-schema-apply-artifact-index",
        help="Write a redacted offline index over process ontology schema apply dry-run artifacts.",
    )
    process_ontology_schema_apply_artifact_index.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="Artifact root to scan. Default: out/notary-kg.",
    )
    process_ontology_schema_apply_artifact_index.add_argument(
        "--query",
        default=None,
        help="Optional case-insensitive filter over artifact id, path, schema and status.",
    )
    process_ontology_schema_apply_artifact_index.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON index path. Default: out/notary-kg/process-ontology-schema-apply-artifact-index.redacted.json.",
    )
    process_ontology_schema_apply_artifact_index.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help="Markdown index path. Default: out/notary-kg/process-ontology-schema-apply-artifact-index.redacted.md.",
    )
    process_ontology_schema_apply_artifact_index.add_argument(
        "--no-ensure-default-artifact",
        action="store_true",
        help="Do not create the default redacted dry-run artifact before indexing.",
    )

    process_ontology_schema_apply_live_readiness_gate = subparsers.add_parser(
        "process-ontology-schema-apply-live-readiness-gate",
        help="Write an offline readiness gate before a future owner-gated Graph REST schema apply.",
    )
    process_ontology_schema_apply_live_readiness_gate.add_argument(
        "--workspace-id",
        choices=["notary_team_01"],
        required=True,
        help="Explicit live-apply workspace. This slice only enables notary_team_01.",
    )
    process_ontology_schema_apply_live_readiness_gate.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="Artifact root to scan. Default: out/notary-kg.",
    )
    process_ontology_schema_apply_live_readiness_gate.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "JSON gate path. Default: "
            "out/notary-kg/process-ontology-schema-apply-live-readiness-gate.redacted.json."
        ),
    )
    process_ontology_schema_apply_live_readiness_gate.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help=(
            "Markdown gate path. Default: "
            "out/notary-kg/process-ontology-schema-apply-live-readiness-gate.redacted.md."
        ),
    )
    process_ontology_schema_apply_live_readiness_gate.add_argument(
        "--no-ensure-default-artifacts",
        action="store_true",
        help="Do not create default redacted dry-run/index artifacts before evaluating readiness.",
    )

    process_ontology_schema_apply_owner_gated_live_plan = subparsers.add_parser(
        "process-ontology-schema-apply-owner-gated-live-plan",
        help="Write an offline owner-gated live plan for a later Graph REST schema apply.",
    )
    process_ontology_schema_apply_owner_gated_live_plan.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="Artifact root to scan and write supporting readiness artifacts. Default: out/notary-kg.",
    )
    process_ontology_schema_apply_owner_gated_live_plan.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "JSON live-plan path. Default: "
            "out/notary-kg/process-ontology-schema-apply-owner-gated-live-plan.redacted.json."
        ),
    )
    process_ontology_schema_apply_owner_gated_live_plan.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help=(
            "Markdown live-plan path. Default: "
            "out/notary-kg/process-ontology-schema-apply-owner-gated-live-plan.redacted.md."
        ),
    )
    process_ontology_schema_apply_owner_gated_live_plan.add_argument(
        "--no-ensure-default-artifacts",
        action="store_true",
        help="Do not create default redacted readiness artifacts before evaluating the live plan.",
    )

    process_ontology_schema_apply_owner_gated_runner_contract = subparsers.add_parser(
        "process-ontology-schema-apply-owner-gated-runner-contract",
        help="Write an offline owner-gated runner contract for the later Graph REST schema apply.",
    )
    process_ontology_schema_apply_owner_gated_runner_contract.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="Artifact root to scan and write supporting readiness artifacts. Default: out/notary-kg.",
    )
    process_ontology_schema_apply_owner_gated_runner_contract.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "JSON runner-contract path. Default: "
            "out/notary-kg/process-ontology-schema-apply-owner-gated-runner-contract.redacted.json."
        ),
    )
    process_ontology_schema_apply_owner_gated_runner_contract.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help=(
            "Markdown runner-contract path. Default: "
            "out/notary-kg/process-ontology-schema-apply-owner-gated-runner-contract.redacted.md."
        ),
    )
    process_ontology_schema_apply_owner_gated_runner_contract.add_argument(
        "--no-ensure-default-artifacts",
        action="store_true",
        help="Do not create default redacted readiness artifacts before evaluating the runner contract.",
    )

    process_ontology_schema_apply_live = subparsers.add_parser(
        "process-ontology-schema-apply-live",
        help="Write the owner-gated live runner envelope for the Graph REST schema apply.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--workspace-id",
        choices=["notary_team_01"],
        required=True,
        help="Single workspace ID bound by the live-readiness gate.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="Artifact root to scan and write supporting readiness artifacts. Default: out/notary-kg.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--live-readiness-gate",
        type=Path,
        default=None,
        help="Path to a passed live-readiness gate JSON artifact.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--correlation-id",
        default=None,
        help="Non-secret correlation ID for the owner-gated run.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--owner-approval-reference",
        required=True,
        help="Non-secret reference to the recorded owner approval.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--reason",
        required=True,
        help="Reason for the approved live schema apply.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--owner-approved",
        action="store_true",
        help="Owner approval for the live schema apply runner gate.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--execute-live-schema-apply",
        action="store_true",
        help="Explicitly acknowledge that this runner is the live schema apply path.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--write-redacted-evidence",
        action="store_true",
        help="Require redacted evidence before the first Graph REST mutation.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON live-runner path. Default: out/notary-kg/process-ontology-schema-apply-live.redacted.json.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help="Markdown live-runner path. Default: out/notary-kg/process-ontology-schema-apply-live.redacted.md.",
    )
    process_ontology_schema_apply_live.add_argument(
        "--no-ensure-default-artifacts",
        action="store_true",
        help="Do not create default redacted readiness artifacts before evaluating the live runner.",
    )

    process_ontology_schema_apply_live_dispatch = subparsers.add_parser(
        "process-ontology-schema-apply-live-dispatch",
        help="Execute the owner-gated Graph REST dispatcher for the SharePoint schema apply.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--workspace-id",
        choices=["notary_team_01"],
        required=True,
        help="Single workspace ID bound by the live-readiness gate.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--live-readiness-gate",
        type=Path,
        required=True,
        help="Path to a passed live-readiness gate JSON artifact.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--provisioner-state",
        type=Path,
        required=True,
        help="Local non-secret privileged-apply state containing the dedicated provisioning application.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--provisioner-certificate-path",
        type=Path,
        default=None,
        help="Local public certificate path used for provisioning app authentication.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--provisioner-private-key-path",
        type=Path,
        default=None,
        help="Local private-key path used for provisioning app authentication.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--provisioner-env-bootstrap-output",
        type=Path,
        default=None,
        help="Redacted provisioner bootstrap evidence path.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--correlation-id",
        required=True,
        help="Non-secret correlation ID for the owner-gated Graph REST dispatch.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--owner-approval-reference",
        required=True,
        help="Non-secret reference to the recorded owner approval.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--reason",
        required=True,
        help="Reason for the approved live schema apply dispatch.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--owner-approved",
        action="store_true",
        help="Owner approval for the live schema apply Graph dispatcher.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--execute-live-schema-apply",
        action="store_true",
        help="Explicitly acknowledge that Graph REST schema mutations may be executed.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--write-redacted-evidence",
        action="store_true",
        help="Write redacted dispatcher evidence.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Optional owner-gated staged dispatch limit for a live rollout.",
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "JSON dispatcher artifact path. Default: "
            "out/notary-kg/process-ontology-schema-apply-graph-dispatcher.redacted.json."
        ),
    )
    process_ontology_schema_apply_live_dispatch.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help=(
            "Markdown dispatcher artifact path. Default: "
            "out/notary-kg/process-ontology-schema-apply-graph-dispatcher.redacted.md."
        ),
    )

    subparsers.add_parser(
        "deep-process-candidates",
        help="Route notarial business cases into deep BPMN/ontology modeling candidates.",
    )

    subparsers.add_parser(
        "first-wave-bpmn-outline",
        help="Build offline BPMN/ontology outline plans for first-wave deep-process cases.",
    )

    subparsers.add_parser(
        "first-wave-gap-review",
        help="Review first-wave BPMN outlines for SharePoint, BPMN and ontology projection gaps.",
    )

    subparsers.add_parser(
        "first-wave-process-deep-model",
        help="Build the offline deep process model contract for first-wave notarial cases.",
    )

    first_wave_gap_review_artifact = subparsers.add_parser(
        "first-wave-gap-review-artifact",
        help="Write a redacted offline first-wave gap-review artifact for release/readiness evidence.",
    )
    first_wave_gap_review_artifact.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON artifact path. Default: out/notary-kg/first-wave-gap-review.redacted.json.",
    )
    first_wave_gap_review_artifact.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help="Markdown artifact path. Default: out/notary-kg/first-wave-gap-review.redacted.md.",
    )

    subparsers.add_parser(
        "ontology-scale-budget",
        help="Evaluate offline ontology scale budgets across the full notarial inventory.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    catalogs = load_catalogs(repo_root)

    if args.command == "status":
        payload = _status_payload(catalogs)
        _print_payload(payload, args.format)
        return 0

    if args.command == "case":
        summary = find_case(catalogs, args.slug)
        if summary is None:
            print(f"ERROR: Unknown KG case slug: {args.slug}")
            return 1
        _print_payload(summary.to_dict(), args.format)
        return 0

    if args.command == "editor-view":
        try:
            payload = build_editor_view(repo_root, args.slug)
        except KeyError:
            print(f"ERROR: Unknown KG case slug: {args.slug}")
            return 1
        _print_payload(payload, args.format)
        return 0

    if args.command == "cost-view":
        try:
            payload = build_cost_review_view(repo_root, args.slug)
        except KeyError:
            print(f"ERROR: Unknown KG case slug: {args.slug}")
            return 1
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 1
        _print_payload(payload, args.format)
        return 0

    if args.command == "workflow-contract":
        try:
            payload = build_workflow_contract_draft(repo_root, args.slug)
        except KeyError:
            print(f"ERROR: Unknown KG case slug: {args.slug}")
            return 1
        _print_payload(payload, args.format)
        return 0

    if args.command == "pilot-checklist":
        try:
            payload = build_pilot_intake_checklist(repo_root, args.slug)
        except KeyError:
            print(f"ERROR: Unknown KG case slug: {args.slug}")
            return 1
        _print_payload(payload, args.format)
        return 0

    if args.command == "business-case-inventory":
        payload = build_business_case_inventory(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "business-case-type-get":
        fixture_path = args.registry_fixture
        if not fixture_path.is_absolute():
            fixture_path = repo_root / fixture_path
        try:
            read_port = _FixtureBusinessCaseTypeRegistryReadPort.from_path(fixture_path)
            catalog = BusinessCaseTypeCatalog.from_repo(repo_root)
            result = business_case_type_get(
                BusinessCaseTypeLookupRequest(
                    site_id=args.site_id,
                    identifier=args.identifier,
                    purpose=args.purpose,
                ),
                catalog=catalog,
                read_port=read_port,
                registry_cache=BusinessCaseTypeRegistryCache(),
            )
            payload = asdict(result)
            _print_business_case_type_lookup(payload, args.format)
            return 0 if result.status == "VALID" else 1
        except Exception:
            # This offline CLI is a redaction boundary. Runtime and fixture
            # details must never escape through tracebacks or exception text.
            print("ERROR: business-case-type lookup failed")
            return 1

    if args.command == "business-case-type-migration-dry-run":
        try:
            rc, payload = run_offline_migration(
                repo_root,
                fixture=args.fixture,
                quarantine_state=args.quarantine_state,
                output=args.output,
            )
            _print_business_case_type_migration(payload, args.format)
            return rc
        except RepositoryStateError:
            reason_code = "repository_state_unavailable"
        except ArtifactWriteError:
            reason_code = "artifact_write_failed"
        except MigrationContractError:
            reason_code = "contract_invalid"
        except (MigrationValidationError, OSError, UnicodeError, json.JSONDecodeError):
            reason_code = "fixture_invalid"
        payload = {
            "status": "ERROR",
            "readiness_scope": "S5_OFFLINE_ONLY",
            "live_cutover_status": "BLOCKED_PENDING_S6_S7_APPROVAL",
            "allowed_live_calls": 0,
            "allowed_tenant_writes": 0,
            "reason_codes": [reason_code],
            "class_counts": {},
            "top_level_hashes": {},
        }
        _print_business_case_type_migration(payload, args.format)
        return 1

    if args.command == "business-case-type-evidence-dry-run":
        payload = build_synthetic_evidence_dry_run()
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "S6_OFFLINE_FOUNDATION" else 1

    if args.command == "business-case-type-azure-worm-readiness":
        payload = dict(build_azure_blob_worm_readiness())
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "S6B_AZURE_WORM_ADAPTER_READY_OFFLINE" else 1

    if args.command == "ontology-storage-contract":
        payload = build_ontology_storage_contract(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "process-ontology-contract":
        payload = build_process_ontology_contract(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "process-ontology-schema-gap":
        payload = build_process_ontology_sharepoint_schema_gap(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "process-ontology-schema-apply-plan":
        payload = build_process_ontology_sharepoint_schema_apply_plan(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "process-ontology-schema-apply-readiness":
        payload = build_process_ontology_sharepoint_schema_apply_readiness(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "process-ontology-schema-apply-execution-contract":
        payload = build_process_ontology_sharepoint_schema_apply_execution_contract(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "process-ontology-schema-apply-runner-dry-run":
        payload = build_process_ontology_sharepoint_schema_apply_runner_dry_run(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "process-ontology-schema-apply-runner-dry-run-artifact":
        payload = write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
            repo_root,
            args.output,
            args.markdown_output,
        )
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "process-ontology-schema-apply-artifact-index":
        payload = write_process_ontology_sharepoint_schema_apply_artifact_index(
            repo_root,
            args.artifact_root,
            args.output,
            args.markdown_output,
            args.query,
            ensure_default_artifact=not args.no_ensure_default_artifact,
        )
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "process-ontology-schema-apply-live-readiness-gate":
        payload = write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
            repo_root,
            args.artifact_root,
            args.output,
            args.markdown_output,
            workspace_ids=[args.workspace_id],
            ensure_default_artifacts=not args.no_ensure_default_artifacts,
        )
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "process-ontology-schema-apply-owner-gated-live-plan":
        payload = write_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(
            repo_root,
            args.artifact_root,
            args.output,
            args.markdown_output,
            ensure_default_artifacts=not args.no_ensure_default_artifacts,
        )
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "READY_FOR_OWNER_APPROVAL" else 1

    if args.command == "process-ontology-schema-apply-owner-gated-runner-contract":
        payload = write_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract(
            repo_root,
            args.artifact_root,
            args.output,
            args.markdown_output,
            ensure_default_artifacts=not args.no_ensure_default_artifacts,
        )
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "process-ontology-schema-apply-live":
        payload = write_process_ontology_sharepoint_schema_apply_live_runner(
            repo_root,
            args.artifact_root,
            args.output,
            args.markdown_output,
            live_readiness_gate=args.live_readiness_gate,
            workspace_id=args.workspace_id,
            correlation_id=args.correlation_id,
            owner_approval_reference=args.owner_approval_reference,
            reason=args.reason,
            owner_approved=args.owner_approved,
            execute_live_schema_apply=args.execute_live_schema_apply,
            write_redacted_evidence=args.write_redacted_evidence,
            ensure_default_artifacts=not args.no_ensure_default_artifacts,
        )
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "READY_FOR_GRAPH_REST_DISPATCH" else 1

    if args.command == "process-ontology-schema-apply-live-dispatch":
        state_path = _resolve_repo_path(repo_root, args.provisioner_state)
        certificate_path = _resolve_optional_repo_path(repo_root, args.provisioner_certificate_path)
        private_key_path = _resolve_optional_repo_path(repo_root, args.provisioner_private_key_path)
        try:
            provisioner_state = load_provisioner_env_state(state_path)
        except (OSError, json.JSONDecodeError):
            provisioner_state = {}
        bootstrap = build_provisioner_env_bootstrap(
            provisioner_state,
            certificate_path=certificate_path,
            private_key_path=private_key_path,
            env=os.environ,
        )
        bootstrap_output = args.provisioner_env_bootstrap_output
        if bootstrap_output is None:
            output_parent = args.output.parent if args.output is not None else Path("out/notary-kg")
            bootstrap_output = output_parent / "provisioner-env-bootstrap.redacted.json"
        write_provisioner_env_bootstrap_artifact(
            bootstrap.readiness,
            _resolve_repo_path(repo_root, bootstrap_output),
        )
        if bootstrap.readiness["status"] != "PASSED":
            _print_payload(bootstrap.readiness, args.format)
            return 1
        effective_env = dict(os.environ)
        effective_env.update(bootstrap.env_overlay)
        client = GraphRestClient(token_provider_from_env(effective_env))
        payload = write_process_ontology_sharepoint_schema_apply_graph_dispatcher_artifact(
            client,
            repo_root,
            args.output,
            args.markdown_output,
            live_readiness_gate=args.live_readiness_gate,
            workspace_id=args.workspace_id,
            correlation_id=args.correlation_id,
            owner_approval_reference=args.owner_approval_reference,
            reason=args.reason,
            owner_approved=args.owner_approved,
            execute_live_schema_apply=args.execute_live_schema_apply,
            write_redacted_evidence=args.write_redacted_evidence,
            max_steps=args.max_steps,
        )
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "deep-process-candidates":
        payload = build_deep_process_candidate_routing(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "first-wave-bpmn-outline":
        payload = build_first_wave_bpmn_outline(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "first-wave-gap-review":
        payload = build_first_wave_bpmn_outline_gap_review(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "first-wave-process-deep-model":
        payload = build_first_wave_process_deep_model(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "first-wave-gap-review-artifact":
        payload = write_first_wave_bpmn_outline_gap_review_artifact(repo_root, args.output, args.markdown_output)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    if args.command == "ontology-scale-budget":
        payload = build_ontology_scale_budget_smoke(repo_root)
        _print_payload(payload, args.format)
        return 0 if payload["status"] == "PASSED" else 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _resolve_repo_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _resolve_optional_repo_path(repo_root: Path, path: Path | None) -> Path | None:
    return _resolve_repo_path(repo_root, path) if path is not None else None


def _legacy_vorgangstyp_patch_planned(payload: dict) -> bool:
    return any(
        step.get("target") == "Akten"
        and (
            step.get("source_gap_id") == "Akten.Vorgangstyp.choices"
            or step.get("request", {}).get("body", {}).get("name") == "Vorgangstyp"
        )
        for step in payload.get("steps", [])
    )


def _status_payload(catalogs) -> dict:
    catalog_summaries = [catalog.summary() for catalog in catalogs]
    case_summaries = all_case_summaries(catalogs)
    p0_cases = [case for case in case_summaries if case.priority == "P0"]
    return {
        "catalogs": [summary.to_dict() for summary in catalog_summaries],
        "totals": {
            "catalogs": len(catalog_summaries),
            "cases": len(case_summaries),
            "p0_cases": len(p0_cases),
            "open_required_information": sum(case.open_required_information for case in case_summaries),
            "cases_ready_for_development": sum(1 for case in case_summaries if case.ready_for_development),
        },
        "active_development_candidates": [
            {
                "slug": case.slug,
                "title": case.title,
                "catalog_id": case.catalog_id,
                "open_required_information": case.open_required_information,
                "plugins": list(case.plugin_dependencies),
            }
            for case in p0_cases[:8]
        ],
    }


def _print_payload(payload: dict, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if "totals" in payload:
        totals = payload["totals"]
        print("NaC KG development status")
        print(f"- catalogs: {totals['catalogs']}")
        print(f"- cases: {totals['cases']}")
        print(f"- P0 cases: {totals['p0_cases']}")
        print(f"- open required-information nodes: {totals['open_required_information']}")
        print(f"- cases ready for development: {totals['cases_ready_for_development']}")
        print("")
        print("Active development candidates")
        for item in payload["active_development_candidates"]:
            print(f"- {item['slug']}: {item['open_required_information']} open nodes")
        return

    if payload.get("schema_version") == "nac.kg-editor-view/v0.1":
        print(f"KG editor view: {payload['usecase_slug']} ({payload['graph_id']})")
        print(f"- title: {payload['title']}")
        print(f"- json role: {payload['editor_model']['json_role']}")
        print(f"- interaction: {payload['editor_model']['interaction_model']}")
        print("")
        print("Tabs")
        for tab in payload["editor_model"]["tabs"]:
            print(
                f"- {tab['label_de']} / {tab['label_en']}: "
                f"{tab['item_count']} items ({tab['render_as']})"
            )
        print("")
        print("Actions")
        for action in payload["actions"]:
            print(f"- {action['name']}")
        print("")
        print("Patch policy")
        print(f"- mode: {payload['patch_policy']['mode']}")
        print(f"- forbidden fields: {', '.join(payload['patch_policy']['forbidden_fields'])}")
        print(f"- confirmation required: {payload['patch_policy']['confirmation_required']}")
        return

    if payload.get("schema_version") == "nac.gnotkg-cost-review/v0.1":
        print(f"GNotKG-Kostenansicht: {payload['usecase_slug']} ({payload['graph_id']})")
        print(f"- title: {payload['title']}")
        print(f"- renderer: {payload['rendering']['preferred_renderer']}")
        print(f"- nodes: {len(payload['nodes'])}")
        print(f"- edges: {len(payload['edges'])}")
        print("")
        print("Guardrails")
        print(f"- notarielle Prüfung erforderlich: {payload['guardrails']['notarial_review_required']}")
        print(f"- echte Mandatsdaten in Git: {payload['guardrails']['real_mandate_data_in_git']}")
        return

    if payload.get("schema_version") == "nac.workflow-contract-draft/v0.1":
        print(f"Workflow-Vertragsentwurf: {payload['source']['usecase_slug']}")
        print(f"- contract_id: {payload['contract_id']}")
        print(f"- status: {payload['status']}")
        print(f"- required information: {len(payload['intake']['required_information'])}")
        print(f"- documents: {len(payload['intake']['documents'])}")
        print(f"- decisions: {len(payload['intake']['decisions'])}")
        print(f"- gates: {len(payload['gates'])}")
        print(f"- evidence: {len(payload['evidence'])}")
        print("")
        print("Guardrails")
        print(f"- real mandate data in Git: {payload['guardrails']['real_mandate_data_in_git']}")
        print(f"- value fields included: {payload['guardrails']['value_fields_included']}")
        print(f"- protected PR required: {payload['guardrails']['protected_pr_required']}")
        return

    if payload.get("schema_version") == "nac.pilot-intake-checklist/v0.1":
        print(f"Pilot-Checkliste: {payload['pilot_usecase']['slug']}")
        print(f"- workflow: {payload['workflow_binding']['workflow_id']}")
        print(f"- status: {payload['status']}")
        print(f"- items: {payload['summary']['open_items']}/{payload['summary']['total_items']} offen")
        print(f"- nächster Schritt: {payload['summary']['next_step']['label']}")
        print("")
        print("Abschnitte")
        for section in payload["sections"]:
            print(f"- {section['label_de']}: {section['open_count']}/{section['item_count']} offen")
        print("")
        print("Guardrails")
        print(f"- echte Mandatsdaten in Git: {payload['guardrails']['real_mandate_data_in_git']}")
        print(f"- produktive Register-/XNP-Aktion: {payload['guardrails']['productive_register_or_xnp_action']}")
        return

    if payload.get("schema_version") in BUSINESS_CASE_INVENTORY_SCHEMA_VERSIONS:
        summary = payload["summary"]
        print("Notarial business-case inventory")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- business cases: {summary['business_case_count']}")
        print(f"- canonical coverage: {summary['canonical_covered_count']}/{summary['canonical_target_count']}")
        if payload["schema_version"].endswith("/v0.2"):
            print(f"- canonical business-case types: {summary['canonical_business_case_type_count']}")
            print(f"- legacy aliases: {summary['legacy_alias_count']}")
        print(f"- backlog candidates: {summary['backlog_candidate_count']}")
        print(f"- max complexity score: {summary['max_complexity_score']}")
        print("")
        print("Storage strategy")
        for key, value in payload["storage_strategy"].items():
            print(f"- {key}: {value}")
        print("")
        print("Domain counts")
        for domain, count in sorted(summary["domain_counts"].items()):
            print(f"- {domain}: {count}")
        print("")
        print("Recommended deep-process slices")
        for slug in summary["deep_process_slices_recommended"]:
            print(f"- {slug}")
        if payload["schema_version"].endswith("/v0.2"):
            validity = payload["type_validity_dependencies"]
            print("")
            print("Type validity")
            print(f"- Vorgangsartenregister required: {validity['vorgangsartenregister_required']}")
            print(f"- Prozessregister required: {validity['prozessregister_required']}")
            print(f"- viewer required: {validity['viewer_required']}")
        return

    if payload.get("schema_version") == "nac.notarial-ontology-sizing-storage/v0.1":
        evaluation = payload["evaluation"]
        current = evaluation["current_sizing"]
        print("Notarial ontology sizing and storage contract")
        print(f"- status: {payload['status']}")
        print(f"- contract: {payload['contract_path']}")
        print(f"- business cases: {current['business_case_count']}/{current['max_supported_business_cases_without_store_migration']}")
        print(f"- canonical coverage: {current['canonical_covered_count']}/{current['canonical_required']}")
        print(
            "- max complexity score: "
            f"{current['max_complexity_score']}/{current['max_complexity_score_without_architecture_review']}"
        )
        print("")
        print("Derived decision")
        for key, value in evaluation["derived_decision"].items():
            print(f"- {key}: {value}")
        if evaluation["warnings"]:
            print("")
            print("Warnings")
            for warning in evaluation["warnings"]:
                print(f"- {warning}")
        return

    if payload.get("schema_version") in PROCESS_ONTOLOGY_SCHEMA_VERSIONS:
        evaluation = payload["evaluation"]
        summary = evaluation["summary"]
        print("Notarial process ontology contract")
        print(f"- status: {payload['status']}")
        print(f"- contract: {payload['contract_path']}")
        print(f"- business cases: {summary['business_case_count']}")
        print(f"- canonical coverage: {summary['canonical_covered_count']}/{summary['canonical_required']}")
        if payload["schema_version"].endswith("/v2"):
            inventory_summary = payload["inventory_snapshot"]["summary"]
            print(f"- canonical business-case types: {inventory_summary['canonical_business_case_type_count']}")
            print(f"- legacy aliases: {inventory_summary['legacy_alias_count']}")
        print(f"- entity classes: {summary['entity_class_count']}")
        print(f"- relationship templates: {summary['relationship_template_count']}")
        print(f"- process phases: {summary['process_phase_count']}")
        print("")
        print("Derived decision")
        for key, value in evaluation["derived_decision"].items():
            print(f"- {key}: {value}")
        if evaluation["warnings"]:
            print("")
            print("Warnings")
            for warning in evaluation["warnings"]:
                print(f"- {warning}")
        return

    if payload.get("schema_version") in PROCESS_ONTOLOGY_SCHEMA_GAP_VERSIONS:
        summary = payload["summary"]
        print("Process ontology to SharePoint schema gap review")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- business cases: {summary['business_case_count']}")
        print(f"- missing required lists: {summary['missing_required_list_count']}")
        print(f"- optional projection gaps: {summary['optional_projection_gap_count']}")
        print(f"- field gaps: {summary['field_gap_count']}")
        print(f"- choice gaps: {summary['choice_gap_count']}")
        print(f"- total gaps: {summary['total_gap_count']}")
        if payload["schema_version"].endswith("/v0.2"):
            legacy = payload["legacy_column_contract"]
            required_targets = {gap["target"] for gap in payload["required_projection_gaps"]}
            optional_targets = {gap["target"] for gap in payload["optional_projection_gaps"]}
            print(f"- canonical BusinessCaseTypeIds: {len(payload['business_case_type_ids'])}")
            print(f"- Vorgangsartenregister required projection: {'Vorgangsartenregister' in required_targets}")
            print(f"- Prozessregister optional projection: {'Prozessregister' in optional_targets}")
            print(f"- legacy {legacy['target']} protected: {legacy['protected']}")
            print("- legacy Akten.Vorgangstyp patch planned: False")
        return

    if payload.get("schema_version") in PROCESS_ONTOLOGY_SCHEMA_APPLY_PLAN_VERSIONS:
        summary = payload["summary"]
        print("Process ontology SharePoint schema apply plan")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- source gaps: {summary['source_total_gap_count']}")
        print(f"- create list steps: {summary['create_list_step_count']}")
        print(f"- create document library steps: {summary['create_document_library_step_count']}")
        print(f"- create column steps: {summary['create_column_step_count']}")
        print(f"- extend choice steps: {summary['extend_choice_step_count']}")
        print(f"- total steps: {summary['total_step_count']}")
        print(f"- owner gate before apply: {summary['owner_gate_required_before_apply']}")
        if payload["schema_version"].endswith("/v0.2"):
            print(f"- legacy Akten.Vorgangstyp patch planned: {_legacy_vorgangstyp_patch_planned(payload)}")
            print(f"- live execution approval: {summary['live_execution_approval_state']}")
        return

    if payload.get("schema_version") in PROCESS_ONTOLOGY_SCHEMA_APPLY_READINESS_VERSIONS:
        summary = payload["summary"]
        print("Process ontology SharePoint schema apply readiness")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- workspaces: {summary['workspace_count']}")
        print(f"- apply-plan steps: {summary['apply_plan_step_count']}")
        print(f"- workspace apply units: {summary['workspace_apply_unit_count']}")
        print(f"- known site IDs: {summary['known_site_id_count']}")
        print(f"- known required list IDs: {summary['known_required_list_id_count']}")
        print(f"- missing required list IDs: {summary['missing_required_list_id_count']}")
        print(f"- dynamic ID resolutions: {summary['dynamic_resource_resolution_count']}")
        print(f"- live apply readiness: {summary['live_apply_readiness']}")
        if payload["schema_version"].endswith("/v0.2"):
            print(f"- live execution approval: {payload['source']['live_execution_approval_state']}")
        return

    if payload.get("schema_version") in PROCESS_ONTOLOGY_SCHEMA_APPLY_EXECUTION_CONTRACT_VERSIONS:
        summary = payload["summary"]
        print("Process ontology SharePoint schema apply execution contract")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- workspaces: {summary['workspace_count']}")
        print(f"- phases: {summary['execution_phase_count']}")
        print(f"- workspace apply units: {summary['workspace_apply_unit_count']}")
        print(f"- mutating operations: {summary['mutating_operation_count']}")
        print(f"- dynamic resolutions: {summary['dynamic_resolution_count']}")
        print(f"- live apply contract: {summary['live_apply_contract_status']}")
        print(f"- owner gate before live apply: {summary['owner_gate_required_before_live_apply']}")
        return

    if payload.get("schema_version") in PROCESS_ONTOLOGY_SCHEMA_APPLY_RUNNER_DRY_RUN_VERSIONS:
        summary = payload["summary"]
        print("Process ontology SharePoint schema apply runner dry-run")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- workspaces: {summary['workspace_count']}")
        print(f"- dry-run steps: {summary['dry_run_step_count']}")
        print(f"- preflight requests: {summary['preflight_request_count']}")
        print(f"- future mutation requests: {summary['future_mutation_request_count']}")
        print(f"- readback requests: {summary['readback_request_count']}")
        print(f"- owner gate before live apply: {summary['owner_gate_required_before_live_apply']}")
        if payload["schema_version"].endswith("/v0.2"):
            print(f"- executes Graph requests: {summary['executes_graph_requests']}")
            print(f"- writes SharePoint: {summary['writes_sharepoint']}")
            print(f"- live execution approval: {LIVE_EXECUTION_APPROVAL_STATE}")
        return

    if payload.get("schema_version") == PROCESS_ONTOLOGY_SCHEMA_APPLY_RUNNER_DRY_RUN_ARTIFACT_SCHEMA_VERSION:
        summary = payload["summary"]
        print("Process ontology SharePoint schema apply runner dry-run artifact")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- JSON: {payload['artifact_paths']['json']}")
        print(f"- Markdown: {payload['artifact_paths']['markdown']}")
        print(f"- workspaces: {summary['workspace_count']}")
        print(f"- dry-run steps: {summary['dry_run_step_count']}")
        print(f"- future mutation requests: {summary['future_mutation_request_count']}")
        print(f"- owner gate before live apply: {summary['owner_gate_required_before_live_apply']}")
        return

    if payload.get("schema_version") == PROCESS_ONTOLOGY_SCHEMA_APPLY_ARTIFACT_INDEX_SCHEMA_VERSION:
        summary = payload["summary"]
        print("Process ontology SharePoint schema apply artifact index")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- artifact root: {payload['source']['artifact_root']}")
        print(f"- artifacts: {summary['artifact_count']}")
        print(f"- required for live apply readiness: {summary['required_for_live_apply_readiness_count']}")
        print(f"- total dry-run steps: {summary['total_dry_run_step_count']}")
        if payload.get("artifact_paths"):
            print(f"- JSON: {payload['artifact_paths']['json']}")
            print(f"- Markdown: {payload['artifact_paths']['markdown']}")
        return

    if payload.get("schema_version") == PROCESS_ONTOLOGY_SCHEMA_APPLY_LIVE_READINESS_GATE_SCHEMA_VERSION:
        summary = payload["summary"]
        print("Process ontology SharePoint schema apply live readiness gate")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- checks: {summary['passed_check_count']}/{summary['check_count']}")
        print(f"- workspaces: {summary['workspace_count']}")
        print(f"- workspace apply units: {summary['workspace_apply_unit_count']}")
        print(f"- dry-run steps: {summary['dry_run_step_count']}")
        print(f"- indexed artifacts: {summary['artifact_count']}")
        print(f"- owner gate before live apply: {summary['owner_gate_required_before_live_apply']}")
        if payload.get("artifact_paths"):
            print(f"- JSON: {payload['artifact_paths']['json']}")
            print(f"- Markdown: {payload['artifact_paths']['markdown']}")
        return

    if payload.get("schema_version") == PROCESS_ONTOLOGY_SCHEMA_APPLY_OWNER_GATED_LIVE_PLAN_SCHEMA_VERSION:
        summary = payload["summary"]
        print("Process ontology SharePoint schema apply owner-gated live plan")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- workspaces: {summary['workspace_count']}")
        print(f"- planned live steps: {summary['planned_live_step_count']}")
        print(f"- owner gate required now: {summary['owner_gate_required_now']}")
        print(f"- executes Graph requests: {summary['executes_graph_requests']}")
        print(f"- writes SharePoint: {summary['writes_sharepoint']}")
        if payload.get("artifact_paths"):
            print(f"- JSON: {payload['artifact_paths']['json']}")
            print(f"- Markdown: {payload['artifact_paths']['markdown']}")
        return

    if payload.get("schema_version") == PROCESS_ONTOLOGY_SCHEMA_APPLY_OWNER_GATED_RUNNER_CONTRACT_SCHEMA_VERSION:
        summary = payload["summary"]
        print("Process ontology SharePoint schema apply owner-gated runner contract")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- runner command: {payload['runner_interface']['command']}")
        print(f"- runner steps: {summary['runner_step_count']}")
        print(f"- owner gate before execution: {summary['owner_gate_required_before_execution']}")
        print(f"- executes Graph requests: {summary['executes_graph_requests']}")
        print(f"- writes SharePoint: {summary['writes_sharepoint']}")
        if payload.get("artifact_paths"):
            print(f"- JSON: {payload['artifact_paths']['json']}")
            print(f"- Markdown: {payload['artifact_paths']['markdown']}")
        return

    if payload.get("schema_version") == PROCESS_ONTOLOGY_SCHEMA_APPLY_LIVE_RUNNER_SCHEMA_VERSION:
        summary = payload["summary"]
        print("Process ontology SharePoint schema apply live runner")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- correlation ID: {payload['owner_gate']['correlation_id']}")
        print(f"- runner steps: {summary['runner_step_count']}")
        print(f"- owner gate satisfied: {summary['owner_gate_satisfied']}")
        print(f"- ready for Graph REST dispatch: {summary['ready_for_graph_rest_dispatch']}")
        print(f"- executes Graph requests: {summary['executes_graph_requests']}")
        print(f"- writes SharePoint: {summary['writes_sharepoint']}")
        if payload["owner_gate"]["missing_or_blocking"]:
            print("- blockers:")
            for reason in payload["owner_gate"]["missing_or_blocking"]:
                print(f"  - {reason}")
        if payload.get("artifact_paths"):
            print(f"- JSON: {payload['artifact_paths']['json']}")
            print(f"- Markdown: {payload['artifact_paths']['markdown']}")
        return

    if payload.get("schema_version") in PROCESS_ONTOLOGY_SCHEMA_APPLY_GRAPH_DISPATCHER_SCHEMA_VERSIONS:
        summary = payload["summary"]
        print("Process ontology SharePoint schema apply Graph dispatcher")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- correlation ID: {summary['correlation_id']}")
        print(f"- dispatched steps: {summary['dispatched_step_count']}")
        print(f"- mutations executed: {summary['mutation_request_count']}")
        print(f"- executed Graph requests: {summary['executed_graph_requests']}")
        print(f"- executed Graph writes: {summary['executed_graph_writes']}")
        print(f"- stopped on first failure: {summary['stopped_on_first_failure']}")
        if payload.get("artifact_paths"):
            print(f"- JSON: {payload['artifact_paths']['json']}")
            print(f"- Markdown: {payload['artifact_paths']['markdown']}")
        return

    if payload.get("schema_version") == "nac.notarial-deep-process-candidate-routing/v0.1":
        summary = payload["summary"]
        print("Notarial deep-process candidate routing")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- candidates: {summary['candidate_count']}/{summary['business_case_count']}")
        print(f"- first wave: {summary['first_wave_count']}")
        print(f"- max complexity score: {summary['max_complexity_score']}")
        print("")
        print("Lane counts")
        for lane, count in sorted(summary["lane_counts"].items()):
            print(f"- {lane}: {count}")
        print("")
        print("Recommended batch")
        for slug in payload["recommended_batch"]:
            print(f"- {slug}")
        return

    if payload.get("schema_version") == "nac.first-wave-bpmn-outline/v0.1":
        summary = payload["summary"]
        print("First-wave BPMN outline contract")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- first-wave cases: {summary['first_wave_count']}")
        print(f"- total BPMN flow nodes: {summary['total_bpmn_flow_nodes']}")
        print(f"- total required-information nodes: {summary['total_required_information_nodes']}")
        print("")
        print("Outlines")
        for outline in payload["outlines"]:
            print(
                f"- {outline['slug']}: "
                f"{outline['bpmn_outline']['flow_node_count']} BPMN nodes, "
                f"{outline['kg_outline']['required_information_nodes']} KG info nodes"
            )
        return

    if payload.get("schema_version") == "nac.first-wave-process-deep-model/v0.1":
        summary = payload["summary"]
        print("First-wave process deep model contract")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- first-wave cases: {summary['first_wave_count']}")
        print(f"- phase templates: {summary['phase_template_count']}")
        print(f"- BPMN flow-node bindings: {summary['bpmn_flow_node_binding_count']}")
        print(f"- required-information bindings: {summary['required_information_binding_count']}")
        print(f"- evidence bindings: {summary['evidence_binding_count']}")
        print(f"- open gaps carried forward: {summary['open_gap_count']}")
        print("")
        print("Case models")
        for case_model in payload["case_models"]:
            print(
                f"- {case_model['slug']}: "
                f"{len(case_model['phase_plan'])} phases, "
                f"{case_model['bpmn_binding_plan']['flow_node_count']} BPMN nodes, "
                f"{case_model['kg_binding_plan']['required_information_count']} KG info nodes"
            )
        return

    if payload.get("schema_version") == "nac.first-wave-bpmn-outline-gap-review/v0.1":
        summary = payload["summary"]
        print("First-wave BPMN outline gap review")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- first-wave cases: {summary['first_wave_count']}")
        print(f"- SharePoint field gaps: {summary['sharepoint_field_gap_count']}")
        print(f"- BPMN gaps: {summary['bpmn_gap_count']}")
        print(f"- ontology patches: {summary['ontology_patch_count']}")
        print("")
        print("Review items")
        for item in payload["review_items"]:
            print(
                f"- {item['slug']}: "
                f"{len(item['sharepoint_field_gap_plan']['gaps'])} SharePoint gaps, "
                f"{len(item['bpmn_gap_plan']['gaps'])} BPMN gaps, "
                f"{len(item['ontology_projection_patch_plan']['patches'])} ontology patches"
            )
        return

    if payload.get("schema_version") == FIRST_WAVE_GAP_REVIEW_ARTIFACT_SCHEMA_VERSION:
        summary = payload["summary"]
        print("First-wave BPMN outline gap review artifact")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- JSON: {payload['artifact_paths']['json']}")
        print(f"- Markdown: {payload['artifact_paths']['markdown']}")
        print(f"- first-wave cases: {summary['first_wave_count']}")
        print(f"- SharePoint field gaps: {summary['sharepoint_field_gap_count']}")
        print(f"- BPMN gaps: {summary['bpmn_gap_count']}")
        print(f"- ontology patches: {summary['ontology_patch_count']}")
        return

    if payload.get("schema_version") == "nac.notarial-ontology-scale-budget/v0.1":
        summary = payload["summary"]
        print("Notarial ontology scale budget")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- business cases: {summary['business_case_count']}")
        print(f"- BPMN sources: {summary['bpmn_source_count']}")
        print(f"- total BPMN flow nodes: {summary['total_bpmn_flow_nodes']}")
        print(f"- total projection entities estimate: {summary['total_projection_entities_estimate']}")
        print(f"- max projection entities estimate: {summary['max_projection_entities_estimate']}")
        print(f"- total projection edges estimate: {summary['total_projection_edges_estimate']}")
        print(f"- max projection edges estimate: {summary['max_projection_edges_estimate']}")
        print("")
        print("Pressure cases")
        for slug in summary["pressure_cases"]:
            print(f"- {slug}")
        return

    print(f"{payload['slug']} ({payload['catalog_id']})")
    print(f"- title: {payload['title']}")
    print(f"- priority: {payload['priority']}")
    print(f"- status: {payload['status']}")
    print(f"- usecase: {payload['usecase_path']}")
    print(f"- required information: {payload['required_information']}")
    print(f"- open required information: {payload['open_required_information']}")
    print(f"- documents: {payload['documents']}")
    print(f"- decisions: {payload['decisions']}")
    print(f"- gates: {payload['gates']}")
    print(f"- evidence: {payload['evidence']}")
    if payload["first_open_questions"]:
        print("")
        print("First open questions")
        for question in payload["first_open_questions"]:
            print(f"- {question}")


class _FixtureBusinessCaseTypeRegistryReadPort:
    _MAX_FIXTURE_BYTES = 65536
    _ROOT_KEYS = frozenset({"status", "rows", "reason_code", "pages_complete"})
    _ROW_KEYS = frozenset(
        {
            "business_case_type_id",
            "lifecycle_status",
            "selectable",
            "catalog_version",
            "etag",
        }
    )

    def __init__(self, result: RegistryFetchResult) -> None:
        self._result = result

    @classmethod
    def from_path(cls, path: Path) -> "_FixtureBusinessCaseTypeRegistryReadPort":
        if path.stat().st_size > cls._MAX_FIXTURE_BYTES:
            raise ValueError("registry fixture exceeds offline size limit")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not set(raw).issubset(cls._ROOT_KEYS):
            raise ValueError("registry fixture must be a supported object")
        status = raw.get("status")
        rows = raw.get("rows", [])
        if not isinstance(rows, list):
            raise ValueError("registry fixture rows must be a list")
        if status == "OK":
            if raw.get("pages_complete") is not True:
                raise ValueError("OK registry fixture requires pages_complete=true")
            parsed_rows = tuple(cls._parse_row(row) for row in rows)
            return cls(RegistryFetchResult.ok(*parsed_rows, pages_complete=True))
        if rows:
            raise ValueError("non-OK registry fixtures cannot contain rows")
        if status == "NOT_MODIFIED":
            return cls(RegistryFetchResult.not_modified())
        if status == "UNAVAILABLE":
            reason_code = raw.get("reason_code", "fixture_transport_unavailable")
            if not isinstance(reason_code, str) or not reason_code:
                raise ValueError("unavailable fixture requires a reason code")
            return cls(RegistryFetchResult.unavailable(reason_code))
        raise ValueError("unsupported registry fixture status")

    @classmethod
    def _parse_row(cls, raw: object) -> BusinessCaseTypeRegistryRow:
        if not isinstance(raw, dict) or set(raw) != cls._ROW_KEYS:
            raise ValueError("registry fixture row shape mismatch")
        values = (
            raw["business_case_type_id"],
            raw["lifecycle_status"],
            raw["catalog_version"],
            raw["etag"],
        )
        if not all(isinstance(value, str) for value in values):
            raise ValueError("registry fixture text field type mismatch")
        if type(raw["selectable"]) is not bool:
            raise ValueError("registry fixture Selectable must be boolean")
        return BusinessCaseTypeRegistryRow(
            business_case_type_id=raw["business_case_type_id"],
            lifecycle_status=raw["lifecycle_status"],
            selectable=raw["selectable"],
            catalog_version=raw["catalog_version"],
            etag=raw["etag"],
        )

    def fetch_registry(
        self,
        *,
        site_id: str,
        business_case_type_id: str,
        catalog_version: str,
        if_none_match: str | None,
    ) -> RegistryFetchResult:
        del site_id, business_case_type_id, catalog_version, if_none_match
        return self._result


def _print_business_case_type_lookup(payload: dict[str, object], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return
    print("BusinessCaseType runtime lookup")
    print(f"- status: {payload['status']}")
    print(f"- requested identifier: {payload['requested_identifier']}")
    print(f"- canonical BusinessCaseTypeId: {payload['canonical_business_case_type_id']}")
    print(f"- CatalogVersion: {payload['catalog_version']}")
    print(f"- registry ETag: {payload['registry_etag']}")
    print(f"- resolved from alias: {payload['resolved_from_alias']}")
    print(f"- audit required: {payload['audit_required']}")
    print(f"- selectable: {payload['selectable']}")
    print(f"- cache state: {payload['cache_state']}")
    print(f"- reason code: {payload['reason_code']}")


def _print_business_case_type_migration(
    payload: dict[str, object], output_format: str
) -> None:
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return

    print("BusinessCaseType migration S5 offline dry-run")
    print(f"- status: {payload['status']}")
    print(f"- readiness scope: {payload['readiness_scope']}")
    print(f"- live cutover status: {payload['live_cutover_status']}")
    print(f"- allowed live calls: {payload['allowed_live_calls']}")
    print(f"- allowed tenant writes: {payload['allowed_tenant_writes']}")
    reason_codes = payload.get("reason_codes", [])
    print(f"- reason codes: {', '.join(reason_codes) if reason_codes else 'none'}")
    print("- class counts:")
    for name, count in sorted(payload.get("class_counts", {}).items()):
        print(f"  - {name}: {count}")
    print("- evidence hashes:")
    for name, digest in sorted(payload.get("top_level_hashes", {}).items()):
        print(f"  - {name}: {digest}")


if __name__ == "__main__":
    raise SystemExit(main())
