#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.auth import GraphConfig, GraphConfigError, runtime_token_provider_from_env, token_provider_from_env  # noqa: E402
from nac_m365_graph.bpmn_viewer_provisioning import (  # noqa: E402
    DEFAULT_BPMN_VIEWER_PROVISIONING,
    build_bpmn_viewer_provisioning_plan,
    load_bpmn_viewer_provisioning_config,
    summarize_bpmn_viewer_provisioning_plan,
    validate_bpmn_viewer_provisioning_config,
)
from nac_m365_graph.graph_client import GraphHttpError, GraphRestClient  # noqa: E402
from nac_m365_graph.matter_access_delegation import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT,
    build_matter_access_plan,
    load_matter_access_delegation_contract,
    summarize_matter_access_plan,
    validate_matter_access_delegation_contract,
)
from nac_m365_graph.matter_access_delegation_smoke import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_DELEGATION_SMOKE_OUTPUT,
    run_matter_access_delegation_smoke_from_paths,
    write_matter_access_delegation_smoke_artifact,
)
from nac_m365_graph.matter_access_decision_replay import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_DECISION_REPLAY_OUTPUT,
    DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT,
    replay_matter_access_decisions_from_path as run_matter_access_decision_replay,
    write_matter_access_decision_replay_artifact,
)
from nac_m365_graph.matter_access_apply_readiness import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_APPLY_READINESS_OUTPUT,
    build_matter_access_apply_readiness_from_paths,
    write_matter_access_apply_readiness_artifact,
)
from nac_m365_graph.matter_access_apply_request import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_APPLY_REQUEST_OUTPUT,
    build_matter_access_apply_request_plan_from_paths,
    write_matter_access_apply_request_plan_artifact,
)
from nac_m365_graph.matter_access_apply_policy_smoke import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_APPLY_POLICY_SMOKE_OUTPUT,
    run_matter_access_apply_policy_smoke_from_paths,
    write_matter_access_apply_policy_smoke_artifact,
)
from nac_m365_graph.matter_access_apply_smoke import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_APPLY_SMOKE_OUTPUT,
    run_matter_access_apply_smoke_from_paths,
    write_matter_access_apply_smoke_artifact,
)
from nac_m365_graph.matter_access_apply_live_smoke_retention import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_APPLY_LIVE_SMOKE_RETENTION_ROOT,
    retain_matter_access_apply_live_smoke_artifact,
)
from nac_m365_graph.privileged_apply import apply_privileged_change_path  # noqa: E402
from nac_m365_graph.privileged_change import (  # noqa: E402
    DEFAULT_PRIVILEGED_APPLIED_STATE,
    DEFAULT_PRIVILEGED_CHANGE_CONFIG,
    DEFAULT_PROVISIONED_STATE,
    build_application_owner_readiness,
    build_privileged_change_plan,
    load_privileged_applied_state,
    load_privileged_change_config,
    load_provisioned_state,
    summarize_privileged_change_plan,
    validate_privileged_change_config,
)
from nac_m365_graph.provisioner import build_plan, summarize_plan  # noqa: E402
from nac_m365_graph.mcp_runtime import (  # noqa: E402
    DEFAULT_MCP_CONTRACT,
    build_tool_manifest,
    load_mcp_contract,
    validate_mcp_contract,
)
from nac_m365_graph.mcp_live_read_smoke import (  # noqa: E402
    DEFAULT_MCP_LIVE_READ_SMOKE_OUTPUT,
    run_mcp_live_read_smoke_from_paths,
    write_mcp_live_read_smoke_artifact,
)
from nac_m365_graph.mcp_inventory_smoke import (  # noqa: E402
    DEFAULT_MCP_INVENTORY_SMOKE_OUTPUT,
    run_mcp_inventory_smoke_from_paths,
    write_mcp_inventory_smoke_artifact,
)
from nac_m365_graph.mcp_positive_write_read_smoke import (  # noqa: E402
    DEFAULT_MCP_POSITIVE_WRITE_READ_SMOKE_OUTPUT,
    run_mcp_positive_write_read_smoke_from_paths,
    write_mcp_positive_write_read_smoke_artifact,
)
from nac_m365_graph.mcp_smoke_cleanup import (  # noqa: E402
    DEFAULT_MCP_SMOKE_CLEANUP_OUTPUT,
    run_mcp_smoke_cleanup_from_paths,
    write_mcp_smoke_cleanup_artifact,
)
from nac_m365_graph.mcp_smoke_leftover_cleanup import (  # noqa: E402
    DEFAULT_MCP_SMOKE_LEFTOVER_CLEANUP_OUTPUT,
    run_mcp_smoke_leftover_cleanup_from_paths,
    write_mcp_smoke_leftover_cleanup_artifact,
)
from nac_m365_graph.mcp_smoke_suite import (  # noqa: E402
    DEFAULT_MCP_SMOKE_SUITE_OUTPUT,
    run_mcp_smoke_suite_from_paths,
    write_mcp_smoke_suite_artifact,
)
from nac_m365_graph.runtime_metadata import (  # noqa: E402
    DEFAULT_RUNTIME_METADATA_OUTPUT,
    build_runtime_metadata_snapshot,
    write_runtime_metadata_artifact,
)
from nac_m365_graph.runtime_certificate_readiness import (  # noqa: E402
    DEFAULT_CERTIFICATE_EXPIRY_CRITICAL_DAYS,
    DEFAULT_CERTIFICATE_EXPIRY_WARNING_DAYS,
    DEFAULT_RUNTIME_CERTIFICATE_EXPIRY_MONITOR_OUTPUT,
    DEFAULT_RUNTIME_METADATA_STATE,
    DEFAULT_RUNTIME_SMOKE_STATE,
    build_runtime_certificate_expiry_monitor,
    build_runtime_certificate_readiness,
    load_runtime_certificate_state,
    write_runtime_certificate_expiry_monitor_artifact,
)
from nac_m365_graph.runtime_smoke import (  # noqa: E402
    DEFAULT_RUNTIME_SMOKE_OUTPUT,
    run_runtime_site_smoke,
    write_runtime_site_smoke_artifact,
)
from nac_m365_graph.schema import DEFAULT_SCHEMA, load_schema, validate_schema  # noqa: E402
from nac_m365_graph.spfx_bpmn_viewer_skeleton import (  # noqa: E402
    DEFAULT_SPFX_BPMN_VIEWER_SKELETON,
    build_spfx_bpmn_viewer_process_selection_result,
    build_spfx_bpmn_viewer_skeleton_result,
    load_spfx_bpmn_viewer_skeleton,
)
from nac_m365_graph.spfx_bpmn_viewer_runtime_readiness import (  # noqa: E402
    DEFAULT_BPMN_VIEWER_RUNTIME_READINESS,
    build_bpmn_viewer_runtime_readiness_result,
    load_bpmn_viewer_runtime_readiness,
)


MCP_SMOKE_CORRELATION_DEFAULTS = {
    "matter-access-apply-smoke": "matter-access-apply-smoke",
    "matter-access-decision-replay": "matter-access-decision-replay",
    "matter-access-apply-request-plan": "matter-access-apply-request-plan",
    "matter-access-apply-readiness": "matter-access-apply-readiness",
    "matter-access-smoke": "matter-access-delegation-smoke",
    "mcp-inventory-smoke": "mcp-inventory-smoke",
    "mcp-live-read-smoke": "mcp-live-read-smoke",
    "mcp-positive-write-read-smoke": "mcp-positive-write-read-smoke",
    "mcp-smoke-cleanup": "mcp-smoke-cleanup",
    "mcp-smoke-leftover-cleanup": "mcp-smoke-leftover-cleanup",
    "mcp-smoke-suite": "mcp-smoke-suite",
}


def resolve_mcp_smoke_correlation_id(command: str, explicit_correlation_id: str | None) -> str:
    if explicit_correlation_id:
        return explicit_correlation_id
    return MCP_SMOKE_CORRELATION_DEFAULTS.get(command, command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Teams/SharePoint MVP data-plane provisioner using Microsoft Graph REST only."
    )
    parser.add_argument(
        "command",
        choices=[
            "validate",
            "plan",
            "application-owner-readiness",
            "bpmn-viewer-plan",
            "matter-access-plan",
            "matter-access-decision-replay",
            "matter-access-apply-policy-smoke",
            "matter-access-apply-smoke",
            "matter-access-apply-request-plan",
            "matter-access-apply-readiness",
            "matter-access-smoke",
            "bpmn-viewer-runtime-readiness",
            "spfx-bpmn-viewer-skeleton",
            "spfx-bpmn-viewer-process-selection",
            "privileged-plan",
            "privileged-apply",
            "runtime-certificate-expiry-monitor",
            "runtime-certificate-readiness",
            "runtime-smoke",
            "runtime-metadata",
            "mcp-manifest",
            "mcp-stdio",
            "mcp-inventory-smoke",
            "mcp-live-read-smoke",
            "mcp-positive-write-read-smoke",
            "mcp-smoke-cleanup",
            "mcp-smoke-leftover-cleanup",
            "mcp-smoke-suite",
            "apply",
            "drift",
            "export",
        ],
        help=(
            "Provisioning command. validate, plan and privileged-plan run without Microsoft 365 credentials; "
            "application-owner-readiness is offline evidence for the technical-owner path; "
            "bpmn-viewer-plan prepares the optional read-only BPMN viewer SharePoint surface without live apply; "
            "matter-access-plan renders the offline matter visibility and deputy delegation request plan; "
            "matter-access-decision-replay replays synthetic SharePoint list snapshots offline; "
            "matter-access-apply-policy-smoke runs negative offline apply policy checks without Graph; "
            "matter-access-apply-smoke executes an owner-gated synthetic grant_request plus audit_append write/read/cleanup; "
            "matter-access-apply-request-plan renders a concrete redacted future grant request bundle without live apply; "
            "matter-access-apply-readiness validates the future owner-gated write boundary without live apply; "
            "matter-access-smoke writes redacted offline evidence for that request-plan boundary; "
            "bpmn-viewer-runtime-readiness validates offline package/App Catalog/Graph content-read gates; "
            "spfx-bpmn-viewer-skeleton renders the offline SPFx/bpmn-js viewer source skeleton and request plans; "
            "spfx-bpmn-viewer-process-selection checks the metadata-only Prozessregister to BPMN Models selection; "
            "runtime-certificate-expiry-monitor is an offline expiry gate for the runtime certificate; "
            "runtime-certificate-readiness is offline evidence for the runtime certificate path; "
            "privileged-apply, runtime-smoke and runtime-metadata are owner-gated and use Graph REST only. "
            "mcp-stdio starts the local MCP adapter. mcp-inventory-smoke is offline metadata-only evidence."
        ),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="Path to the declarative Teams/SharePoint schema.",
    )
    parser.add_argument(
        "--bpmn-viewer-config",
        type=Path,
        default=DEFAULT_BPMN_VIEWER_PROVISIONING,
        help="Path to the optional BPMN viewer SharePoint provisioning plan.",
    )
    parser.add_argument(
        "--matter-access-contract",
        type=Path,
        default=DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT,
        help="Path to the offline M365 matter access delegation contract.",
    )
    parser.add_argument(
        "--spfx-bpmn-viewer-skeleton",
        type=Path,
        default=DEFAULT_SPFX_BPMN_VIEWER_SKELETON,
        help="Path to the offline SPFx BPMN viewer skeleton artifact.",
    )
    parser.add_argument(
        "--bpmn-viewer-runtime-readiness",
        type=Path,
        default=DEFAULT_BPMN_VIEWER_RUNTIME_READINESS,
        help="Path to the offline BPMN viewer runtime-readiness artifact.",
    )
    parser.add_argument(
        "--owner-approved",
        action="store_true",
        help="Required for live-affecting commands. Does not bypass missing credentials.",
    )
    parser.add_argument(
        "--privileged-config",
        type=Path,
        default=DEFAULT_PRIVILEGED_CHANGE_CONFIG,
        help="Path to the application-owned privileged change path config.",
    )
    parser.add_argument(
        "--provisioned-state",
        type=Path,
        default=DEFAULT_PROVISIONED_STATE,
        help="Path to the non-secret provisioned Teams/SharePoint state export.",
    )
    parser.add_argument(
        "--privileged-applied-state",
        type=Path,
        default=DEFAULT_PRIVILEGED_APPLIED_STATE,
        help="Path to the non-secret privileged-change applied-state evidence export.",
    )
    parser.add_argument(
        "--mcp-contract",
        type=Path,
        default=DEFAULT_MCP_CONTRACT,
        help="Path to the teams-sharepoint-data-mcp contract.",
    )
    parser.add_argument(
        "--runtime-smoke-output",
        type=Path,
        default=DEFAULT_RUNTIME_SMOKE_OUTPUT,
        help="Path for the redacted runtime-smoke artifact under out/.",
    )
    parser.add_argument(
        "--runtime-smoke-state",
        type=Path,
        default=DEFAULT_RUNTIME_SMOKE_STATE,
        help="Path to the non-secret runtime-smoke evidence state.",
    )
    parser.add_argument(
        "--runtime-metadata-output",
        type=Path,
        default=DEFAULT_RUNTIME_METADATA_OUTPUT,
        help="Path for the redacted runtime-metadata artifact under out/.",
    )
    parser.add_argument(
        "--runtime-metadata-state",
        type=Path,
        default=DEFAULT_RUNTIME_METADATA_STATE,
        help="Path to the non-secret runtime-metadata evidence state.",
    )
    parser.add_argument(
        "--runtime-certificate-expiry-output",
        type=Path,
        default=DEFAULT_RUNTIME_CERTIFICATE_EXPIRY_MONITOR_OUTPUT,
        help="Path for the redacted runtime certificate expiry monitor artifact under out/.",
    )
    parser.add_argument(
        "--runtime-certificate-warning-days",
        type=int,
        default=DEFAULT_CERTIFICATE_EXPIRY_WARNING_DAYS,
        help="Warning threshold in days for runtime certificate expiry.",
    )
    parser.add_argument(
        "--runtime-certificate-critical-days",
        type=int,
        default=DEFAULT_CERTIFICATE_EXPIRY_CRITICAL_DAYS,
        help="Critical threshold in days for runtime certificate expiry.",
    )
    parser.add_argument(
        "--mcp-live-read",
        action="store_true",
        help=(
            "Enable owner-gated live Graph REST reads for MCP tools case_get and document_list. "
            "Requires --owner-approved and M365 runtime credentials."
        ),
    )
    parser.add_argument(
        "--mcp-smoke-tool",
        choices=["case_get", "document_list"],
        default="case_get",
        help="MCP live-read smoke tool. Only case_get and document_list are allowed.",
    )
    parser.add_argument(
        "--mcp-smoke-workspace-id",
        default="notary_team_01",
        help="Provisioned workspace id for the MCP live-read smoke.",
    )
    parser.add_argument(
        "--mcp-smoke-case-id",
        help=(
            "Case id used to build the live-read filter. Required for mcp-smoke-cleanup. "
            "For mcp-positive-write-read-smoke and mcp-smoke-suite it is optional; "
            "these commands generate a synthetic case id when omitted. Redacted artifacts store only its SHA-256 hash."
        ),
    )
    parser.add_argument(
        "--mcp-smoke-correlation-id",
        help="Non-secret correlation id for redacted MCP smoke and cleanup artifacts.",
    )
    parser.add_argument(
        "--mcp-smoke-output",
        type=Path,
        default=DEFAULT_MCP_LIVE_READ_SMOKE_OUTPUT,
        help="Path for the redacted MCP live-read smoke artifact under out/.",
    )
    parser.add_argument(
        "--mcp-inventory-smoke-output",
        type=Path,
        default=DEFAULT_MCP_INVENTORY_SMOKE_OUTPUT,
        help="Path for the redacted MCP inventory smoke artifact under out/.",
    )
    parser.add_argument(
        "--matter-access-smoke-output",
        type=Path,
        default=DEFAULT_MATTER_ACCESS_DELEGATION_SMOKE_OUTPUT,
        help="Path for the redacted matter access delegation smoke artifact under out/.",
    )
    parser.add_argument(
        "--matter-access-decision-snapshot",
        type=Path,
        default=DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT,
        help="Path to the synthetic SharePoint list snapshot for offline matter access decision replay.",
    )
    parser.add_argument(
        "--matter-access-decision-replay-output",
        type=Path,
        default=DEFAULT_MATTER_ACCESS_DECISION_REPLAY_OUTPUT,
        help="Path for the redacted matter access decision replay artifact under out/.",
    )
    parser.add_argument(
        "--matter-access-decision-reference-time",
        help="Optional ISO-8601 timestamp for replaying timeboxed deputy grants.",
    )
    parser.add_argument(
        "--matter-access-apply-readiness-output",
        type=Path,
        default=DEFAULT_MATTER_ACCESS_APPLY_READINESS_OUTPUT,
        help="Path for the redacted matter access apply-readiness artifact under out/.",
    )
    parser.add_argument(
        "--matter-access-apply-request-output",
        type=Path,
        default=DEFAULT_MATTER_ACCESS_APPLY_REQUEST_OUTPUT,
        help="Path for the redacted matter access apply request plan artifact under out/.",
    )
    parser.add_argument(
        "--matter-access-apply-policy-smoke-output",
        type=Path,
        default=DEFAULT_MATTER_ACCESS_APPLY_POLICY_SMOKE_OUTPUT,
        help="Path for the redacted offline matter access apply policy smoke artifact under out/.",
    )
    parser.add_argument(
        "--matter-access-apply-smoke-output",
        type=Path,
        default=DEFAULT_MATTER_ACCESS_APPLY_SMOKE_OUTPUT,
        help="Path for the redacted owner-gated matter access apply smoke artifact under out/.",
    )
    parser.add_argument(
        "--matter-access-apply-live-smoke-retention-root",
        type=Path,
        default=DEFAULT_MATTER_ACCESS_APPLY_LIVE_SMOKE_RETENTION_ROOT,
        help="Root for correlation-based retention of redacted matter-access apply live-smoke artifacts.",
    )
    parser.add_argument("--matter-access-grant-id", help="Synthetic grant id seed; redacted artifacts store only a hash.")
    parser.add_argument(
        "--matter-access-from-user",
        help="Synthetic source user seed; redacted artifacts store only a hash.",
    )
    parser.add_argument(
        "--matter-access-to-user",
        help="Synthetic deputy user seed; redacted artifacts store only a hash.",
    )
    parser.add_argument("--matter-access-granted-role", default="SachbearbeitungVertretung")
    parser.add_argument("--matter-access-reason", default="Synthetischer Offline-Vertretungsfreigabeplan")
    parser.add_argument("--matter-access-valid-from", default="2026-07-08T09:00:00Z")
    parser.add_argument("--matter-access-valid-until", default="2026-07-15T09:00:00Z")
    parser.add_argument(
        "--matter-access-approved-by",
        help="Synthetic approver seed; redacted artifacts store only a hash.",
    )
    parser.add_argument("--matter-access-status", default="Aktiv")
    parser.add_argument(
        "--mcp-positive-smoke-output",
        type=Path,
        default=DEFAULT_MCP_POSITIVE_WRITE_READ_SMOKE_OUTPUT,
        help="Path for the redacted MCP positive write-read smoke artifact under out/.",
    )
    parser.add_argument(
        "--mcp-cleanup-output",
        type=Path,
        default=DEFAULT_MCP_SMOKE_CLEANUP_OUTPUT,
        help="Path for the redacted MCP smoke cleanup artifact under out/.",
    )
    parser.add_argument(
        "--mcp-leftover-output",
        type=Path,
        default=DEFAULT_MCP_SMOKE_LEFTOVER_CLEANUP_OUTPUT,
        help="Path for the redacted MCP smoke leftover cleanup artifact under out/.",
    )
    parser.add_argument(
        "--mcp-leftover-dry-run",
        action="store_true",
        help="Only read and report synthetic smoke leftovers; do not delete.",
    )
    parser.add_argument(
        "--mcp-suite-output",
        type=Path,
        default=DEFAULT_MCP_SMOKE_SUITE_OUTPUT,
        help="Path for the redacted MCP smoke suite artifact under out/.",
    )
    parser.add_argument(
        "--mcp-suite-cleanup",
        action="store_true",
        help="Run positive write-read smoke and then clean up the same synthetic item in one owner-gated suite.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mcp_smoke_correlation_id = resolve_mcp_smoke_correlation_id(
        args.command,
        args.mcp_smoke_correlation_id,
    )
    if args.command == "mcp-smoke-leftover-cleanup":
        if not args.owner_approved:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": ["mcp-smoke-leftover-cleanup requires --owner-approved"],
                },
                args.json,
                return_code=2,
            )
        try:
            client = GraphRestClient(runtime_token_provider_from_env())
            result = run_mcp_smoke_leftover_cleanup_from_paths(
                client,
                provisioned_state_path=args.provisioned_state,
                workspace_id=args.mcp_smoke_workspace_id,
                correlation_id=mcp_smoke_correlation_id,
                delete_after=not args.mcp_leftover_dry_run,
            )
            write_mcp_smoke_leftover_cleanup_artifact(result, args.mcp_leftover_output)
        except GraphConfigError as exc:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=2,
            )
        except GraphHttpError as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": ["Microsoft Graph request failed during smoke leftover cleanup"],
                    "summary": {
                        "graph_http_status": exc.status,
                        "graph_error_code": _graph_error_code(exc.body),
                    },
                },
                args.json,
                return_code=1,
            )
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.mcp_leftover_output)
        return _emit(
            {
                "status": result["status"],
                "summary": summary,
                "result": result,
            },
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "mcp-inventory-smoke":
        try:
            result = run_mcp_inventory_smoke_from_paths(
                contract_path=args.mcp_contract,
                provisioned_state_path=args.provisioned_state,
                workspace_id=args.mcp_smoke_workspace_id,
                correlation_id=mcp_smoke_correlation_id,
            )
            write_mcp_inventory_smoke_artifact(result, args.mcp_inventory_smoke_output)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.mcp_inventory_smoke_output)
        return _emit(
            {
                "status": result["status"],
                "summary": summary,
                "result": result,
            },
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "matter-access-smoke":
        try:
            result = run_matter_access_delegation_smoke_from_paths(
                contract_path=args.matter_access_contract,
                schema_path=args.schema,
                workspace_id=args.mcp_smoke_workspace_id,
                correlation_id=mcp_smoke_correlation_id,
            )
            write_matter_access_delegation_smoke_artifact(result, args.matter_access_smoke_output)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.matter_access_smoke_output)
        return _emit(
            {
                "status": result["status"],
                "summary": summary,
                "result": result,
            },
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "matter-access-decision-replay":
        try:
            result = run_matter_access_decision_replay(
                snapshot_path=args.matter_access_decision_snapshot,
                reference_time=args.matter_access_decision_reference_time,
                correlation_id=mcp_smoke_correlation_id,
            )
            write_matter_access_decision_replay_artifact(result, args.matter_access_decision_replay_output)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.matter_access_decision_replay_output)
        return _emit(
            {
                "status": result["status"],
                "summary": summary,
                "result": result,
            },
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "matter-access-apply-readiness":
        try:
            result = build_matter_access_apply_readiness_from_paths(
                contract_path=args.matter_access_contract,
                schema_path=args.schema,
                mcp_contract_path=args.mcp_contract,
                workspace_id=args.mcp_smoke_workspace_id,
                correlation_id=mcp_smoke_correlation_id,
            )
            write_matter_access_apply_readiness_artifact(result, args.matter_access_apply_readiness_output)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.matter_access_apply_readiness_output)
        return _emit(
            {
                "status": result["status"],
                "summary": summary,
                "result": result,
            },
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "matter-access-apply-request-plan":
        try:
            result = build_matter_access_apply_request_plan_from_paths(
                contract_path=args.matter_access_contract,
                schema_path=args.schema,
                mcp_contract_path=args.mcp_contract,
                provisioned_state_path=args.provisioned_state,
                workspace_id=args.mcp_smoke_workspace_id,
                correlation_id=mcp_smoke_correlation_id,
                grant_id=args.matter_access_grant_id,
                case_id=args.mcp_smoke_case_id,
                from_user=args.matter_access_from_user,
                to_user=args.matter_access_to_user,
                granted_role=args.matter_access_granted_role,
                reason=args.matter_access_reason,
                valid_from=args.matter_access_valid_from,
                valid_until=args.matter_access_valid_until,
                approved_by=args.matter_access_approved_by,
                status=args.matter_access_status,
            )
            write_matter_access_apply_request_plan_artifact(result, args.matter_access_apply_request_output)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.matter_access_apply_request_output)
        return _emit(
            {
                "status": result["status"],
                "summary": summary,
                "result": result,
            },
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "matter-access-apply-policy-smoke":
        try:
            result = run_matter_access_apply_policy_smoke_from_paths(
                contract_path=args.mcp_contract,
                provisioned_state_path=args.provisioned_state,
                workspace_id=args.mcp_smoke_workspace_id,
                correlation_id=mcp_smoke_correlation_id,
            )
            write_matter_access_apply_policy_smoke_artifact(result, args.matter_access_apply_policy_smoke_output)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.matter_access_apply_policy_smoke_output)
        return _emit(
            {
                "status": result["status"],
                "summary": summary,
                "result": result,
            },
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "matter-access-apply-smoke":
        if not args.owner_approved:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": ["matter-access-apply-smoke requires --owner-approved"],
                },
                args.json,
                return_code=2,
            )
        try:
            client = GraphRestClient(runtime_token_provider_from_env())
            smoke_valid_from = args.matter_access_valid_from
            smoke_valid_until = args.matter_access_valid_until
            if (
                smoke_valid_from == "2026-07-08T09:00:00Z"
                and smoke_valid_until == "2026-07-15T09:00:00Z"
            ):
                smoke_valid_from = None
                smoke_valid_until = None
            result = run_matter_access_apply_smoke_from_paths(
                client,
                contract_path=args.mcp_contract,
                provisioned_state_path=args.provisioned_state,
                workspace_id=args.mcp_smoke_workspace_id,
                correlation_id=mcp_smoke_correlation_id,
                grant_id=args.matter_access_grant_id,
                case_id=args.mcp_smoke_case_id,
                from_user=args.matter_access_from_user,
                to_user=args.matter_access_to_user,
                granted_role=args.matter_access_granted_role,
                reason=args.matter_access_reason,
                valid_from=smoke_valid_from,
                valid_until=smoke_valid_until,
                approved_by=args.matter_access_approved_by,
                status=args.matter_access_status,
                cleanup_after=True,
            )
            write_matter_access_apply_smoke_artifact(result, args.matter_access_apply_smoke_output)
            retention = retain_matter_access_apply_live_smoke_artifact(
                args.matter_access_apply_smoke_output,
                retention_root=args.matter_access_apply_live_smoke_retention_root,
            )
        except GraphConfigError as exc:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=2,
            )
        except GraphHttpError as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": ["Microsoft Graph request failed during matter access apply smoke"],
                    "summary": {
                        "graph_http_status": exc.status,
                        "graph_error_code": _graph_error_code(exc.body),
                    },
                },
                args.json,
                return_code=1,
            )
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.matter_access_apply_smoke_output)
        summary["retention_status"] = retention["status"]
        summary["retention_artifact_dir"] = retention["summary"].get("artifact_dir")
        summary["retention_json_path"] = retention["summary"].get("retention_json_path")
        summary["retention_report_path"] = retention["summary"].get("retention_report_path")
        summary["retention_index_path"] = retention["summary"].get("retention_json_path")
        summary["retention_root_index_path"] = retention["summary"].get("retention_index_json_path")
        summary["retention_root_index_report_path"] = retention["summary"].get("retention_index_report_path")
        command_status = "PASSED" if result["status"] == "PASSED" and retention["status"] == "PASSED" else "FAILED"
        return _emit(
            {
                "status": command_status,
                "summary": summary,
                "result": result,
                "retention": retention,
            },
            args.json,
            return_code=0 if command_status == "PASSED" else 1,
        )

    if args.command == "mcp-smoke-suite":
        if not args.owner_approved:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": ["mcp-smoke-suite requires --owner-approved"],
                },
                args.json,
                return_code=2,
            )
        try:
            client = GraphRestClient(runtime_token_provider_from_env())
            result = run_mcp_smoke_suite_from_paths(
                client,
                contract_path=args.mcp_contract,
                provisioned_state_path=args.provisioned_state,
                workspace_id=args.mcp_smoke_workspace_id,
                case_id=args.mcp_smoke_case_id,
                correlation_id=mcp_smoke_correlation_id,
                cleanup_after=args.mcp_suite_cleanup,
            )
            write_mcp_smoke_suite_artifact(result, args.mcp_suite_output)
        except GraphConfigError as exc:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=2,
            )
        except GraphHttpError as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": ["Microsoft Graph request failed during smoke suite"],
                    "summary": {
                        "graph_http_status": exc.status,
                        "graph_error_code": _graph_error_code(exc.body),
                    },
                },
                args.json,
                return_code=1,
            )
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.mcp_suite_output)
        return _emit(
            {
                "status": result["status"],
                "summary": summary,
                "result": result,
            },
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "mcp-smoke-cleanup":
        if not args.owner_approved:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": ["mcp-smoke-cleanup requires --owner-approved"],
                },
                args.json,
                return_code=2,
            )
        if not args.mcp_smoke_case_id:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": ["mcp-smoke-cleanup requires --mcp-smoke-case-id"],
                },
                args.json,
                return_code=2,
            )
        try:
            client = GraphRestClient(runtime_token_provider_from_env())
            result = run_mcp_smoke_cleanup_from_paths(
                client,
                contract_path=args.mcp_contract,
                provisioned_state_path=args.provisioned_state,
                workspace_id=args.mcp_smoke_workspace_id,
                case_id=args.mcp_smoke_case_id,
                correlation_id=mcp_smoke_correlation_id,
            )
            write_mcp_smoke_cleanup_artifact(result, args.mcp_cleanup_output)
        except GraphConfigError as exc:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=2,
            )
        except GraphHttpError as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": ["Microsoft Graph request failed during smoke cleanup"],
                    "summary": {
                        "graph_http_status": exc.status,
                        "graph_error_code": _graph_error_code(exc.body),
                    },
                },
                args.json,
                return_code=1,
            )
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.mcp_cleanup_output)
        return _emit(
            {
                "status": result["status"],
                "summary": summary,
                "result": result,
            },
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "mcp-positive-write-read-smoke":
        if not args.owner_approved:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": ["mcp-positive-write-read-smoke requires --owner-approved"],
                },
                args.json,
                return_code=2,
            )
        try:
            client = GraphRestClient(runtime_token_provider_from_env())
            result = run_mcp_positive_write_read_smoke_from_paths(
                client,
                contract_path=args.mcp_contract,
                provisioned_state_path=args.provisioned_state,
                workspace_id=args.mcp_smoke_workspace_id,
                case_id=args.mcp_smoke_case_id,
                correlation_id=mcp_smoke_correlation_id,
            )
            write_mcp_positive_write_read_smoke_artifact(result, args.mcp_positive_smoke_output)
        except GraphConfigError as exc:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=2,
            )
        except GraphHttpError as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": ["Microsoft Graph request failed during positive write-read smoke"],
                    "summary": {
                        "graph_http_status": exc.status,
                        "graph_error_code": _graph_error_code(exc.body),
                    },
                },
                args.json,
                return_code=1,
            )
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.mcp_positive_smoke_output)
        return _emit(
            {
                "status": result["status"],
                "summary": summary,
                "result": result,
            },
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "mcp-live-read-smoke":
        if not args.owner_approved:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": ["mcp-live-read-smoke requires --owner-approved"],
                },
                args.json,
                return_code=2,
            )
        if not args.mcp_smoke_case_id:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": ["mcp-live-read-smoke requires --mcp-smoke-case-id"],
                },
                args.json,
                return_code=2,
            )
        try:
            client = GraphRestClient(runtime_token_provider_from_env())
            result = run_mcp_live_read_smoke_from_paths(
                client,
                contract_path=args.mcp_contract,
                provisioned_state_path=args.provisioned_state,
                tool_name=args.mcp_smoke_tool,
                workspace_id=args.mcp_smoke_workspace_id,
                case_id=args.mcp_smoke_case_id,
                correlation_id=mcp_smoke_correlation_id,
            )
            write_mcp_live_read_smoke_artifact(result, args.mcp_smoke_output)
        except GraphConfigError as exc:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=2,
            )
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(result["summary"])
        summary["artifact_path"] = str(args.mcp_smoke_output)
        return _emit(
            {
                "status": result["status"],
                "summary": summary,
                "result": result,
            },
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "mcp-stdio":
        from nac_m365_graph.mcp_stdio import run_stdio_server

        graph_client = None
        if args.mcp_live_read:
            if not args.owner_approved:
                print("ERROR: mcp-stdio --mcp-live-read requires --owner-approved", file=sys.stderr)
                return 2
            try:
                graph_client = GraphRestClient(runtime_token_provider_from_env())
            except GraphConfigError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 2
        return run_stdio_server(
            contract_path=args.mcp_contract,
            provisioned_state_path=args.provisioned_state,
            live_read_enabled=args.mcp_live_read,
            graph_client=graph_client,
        )

    if args.command == "mcp-manifest":
        contract = load_mcp_contract(args.mcp_contract)
        errors = validate_mcp_contract(contract)
        if errors:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": errors,
                },
                as_json=args.json,
                return_code=1,
            )
        return _emit(
            {
                "status": "PASSED",
                "summary": {
                    "server_id": contract["server_id"],
                    "tool_count": len(contract["tools"]),
                    "executes_graph_requests": contract["runtime_boundary"]["executes_graph_requests"],
                },
                "result": build_tool_manifest(contract),
            },
            args.json,
        )

    if args.command in {"runtime-smoke", "runtime-metadata"}:
        state = load_provisioned_state(args.provisioned_state)
        schema = load_schema(args.schema)
        errors = validate_schema(schema)
        if errors:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": errors,
                },
                as_json=args.json,
                return_code=1,
            )
        if not args.owner_approved:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": [f"{args.command} requires --owner-approved"],
                },
                args.json,
                return_code=2,
            )
        try:
            client = GraphRestClient(runtime_token_provider_from_env())
            if args.command == "runtime-smoke":
                result = run_runtime_site_smoke(client, state, schema)
                redacted_result = write_runtime_site_smoke_artifact(result, args.runtime_smoke_output)
                artifact_path = args.runtime_smoke_output
            else:
                result = build_runtime_metadata_snapshot(client, state, schema)
                redacted_result = write_runtime_metadata_artifact(result, args.runtime_metadata_output)
                artifact_path = args.runtime_metadata_output
        except GraphConfigError as exc:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=2,
            )
        except (GraphHttpError, RuntimeError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        summary = dict(redacted_result["summary"])
        summary["artifact_path"] = str(artifact_path)
        return _emit(
            {
                "status": redacted_result["status"],
                "summary": summary,
                "result": redacted_result,
            },
            args.json,
        )

    if args.command == "application-owner-readiness":
        config = load_privileged_change_config(args.privileged_config)
        applied_state = (
            load_privileged_applied_state(args.privileged_applied_state)
            if args.privileged_applied_state.exists()
            else None
        )
        readiness = build_application_owner_readiness(config, applied_state)
        return _emit(
            readiness,
            args.json,
            return_code=0 if readiness["status"] == "PASSED" else 1,
        )

    if args.command == "runtime-certificate-readiness":
        runtime_smoke_state = (
            load_runtime_certificate_state(args.runtime_smoke_state)
            if args.runtime_smoke_state.exists()
            else None
        )
        runtime_metadata_state = (
            load_runtime_certificate_state(args.runtime_metadata_state)
            if args.runtime_metadata_state.exists()
            else None
        )
        readiness = build_runtime_certificate_readiness(runtime_smoke_state, runtime_metadata_state)
        return _emit(
            readiness,
            args.json,
            return_code=0 if readiness["status"] == "PASSED" else 1,
        )

    if args.command == "runtime-certificate-expiry-monitor":
        runtime_smoke_state = (
            load_runtime_certificate_state(args.runtime_smoke_state)
            if args.runtime_smoke_state.exists()
            else None
        )
        runtime_metadata_state = (
            load_runtime_certificate_state(args.runtime_metadata_state)
            if args.runtime_metadata_state.exists()
            else None
        )
        monitor = build_runtime_certificate_expiry_monitor(
            runtime_smoke_state,
            runtime_metadata_state,
            warning_days=args.runtime_certificate_warning_days,
            critical_days=args.runtime_certificate_critical_days,
        )
        write_runtime_certificate_expiry_monitor_artifact(monitor, args.runtime_certificate_expiry_output)
        return _emit(
            monitor,
            args.json,
            return_code=0 if monitor["status"] == "PASSED" else 1,
        )

    if args.command in {"privileged-plan", "privileged-apply"}:
        config = load_privileged_change_config(args.privileged_config)
        state = load_provisioned_state(args.provisioned_state)
        errors = validate_privileged_change_config(config)
        if errors:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": errors,
                },
                as_json=args.json,
                return_code=1,
            )
        if args.command == "privileged-apply":
            if not args.owner_approved:
                return _emit(
                    {
                        "status": "BLOCKED",
                        "errors": ["privileged-apply requires --owner-approved"],
                    },
                    args.json,
                    return_code=2,
                )
            try:
                client = GraphRestClient(token_provider_from_env())
                result = apply_privileged_change_path(client, config, state)
            except (GraphConfigError, GraphHttpError, RuntimeError, KeyError) as exc:
                return _emit(
                    {
                        "status": "FAILED",
                        "errors": [str(exc)],
                    },
                    args.json,
                    return_code=1,
                )
            return _emit(
                {
                    "status": result["status"],
                    "summary": {
                        "applications": len(result["applications"]),
                        "team_owner_checks": len(result["teamOwnerChecks"]),
                        "site_permissions": len(result["sitePermissions"]),
                    },
                    "result": result,
                },
                args.json,
            )
        plan = build_privileged_change_plan(config, state)
        return _emit(
            {
                "status": "PASSED",
                "summary": summarize_privileged_change_plan(plan),
                "operations": [operation.to_dict() for operation in plan],
            },
            args.json,
        )

    schema = load_schema(args.schema)
    errors = validate_schema(schema)
    if errors:
        return _emit(
            {
                "status": "FAILED",
                "errors": errors,
            },
            as_json=args.json,
            return_code=1,
        )

    if args.command == "validate":
        return _emit({"status": "PASSED", "message": "schema is valid"}, args.json)

    if args.command == "plan":
        plan = build_plan(schema)
        return _emit(
            {
                "status": "PASSED",
                "summary": summarize_plan(plan),
                "operations": [operation.to_dict() for operation in plan],
            },
            args.json,
        )

    if args.command == "bpmn-viewer-plan":
        config = load_bpmn_viewer_provisioning_config(args.bpmn_viewer_config)
        errors = validate_bpmn_viewer_provisioning_config(config)
        if errors:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": errors,
                },
                args.json,
                return_code=1,
            )
        try:
            operations = build_bpmn_viewer_provisioning_plan(config, schema)
        except ValueError as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        return _emit(
            {
                "status": "PASSED",
                "summary": summarize_bpmn_viewer_provisioning_plan(operations),
                "operations": [operation.to_dict() for operation in operations],
                "guardrails": {
                    "mutates_tenant_now": False,
                    "live_apply_implemented": False,
                    "owner_gate_required_before_future_apply": True,
                    "graph_rest_only": True,
                    "legacy_sharepoint_api_allowed": False,
                    "mcp_tools_request_plan_only": True,
                },
            },
            args.json,
        )

    if args.command == "matter-access-plan":
        contract = load_matter_access_delegation_contract(args.matter_access_contract)
        errors = validate_matter_access_delegation_contract(contract, schema)
        if errors:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": errors,
                },
                args.json,
                return_code=1,
            )
        try:
            operations = build_matter_access_plan(contract, schema)
        except ValueError as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        return _emit(
            {
                "status": "PASSED",
                "summary": summarize_matter_access_plan(operations, contract),
                "operations": [operation.to_dict() for operation in operations],
                "guardrails": {
                    "offline_plan_only": True,
                    "executes_graph_requests_now": False,
                    "tenant_mutation_allowed_now": False,
                    "team_membership_mutation_allowed_now": False,
                    "reads_sharepoint_file_content": False,
                    "stores_tokens_or_secrets": False,
                    "stores_matter_payloads": False,
                    "owner_gate_required_before_future_apply": True,
                    "graph_rest_only": True,
                    "legacy_sharepoint_api_allowed": False,
                },
            },
            args.json,
        )

    if args.command == "spfx-bpmn-viewer-skeleton":
        skeleton = load_spfx_bpmn_viewer_skeleton(args.spfx_bpmn_viewer_skeleton)
        mcp_contract = load_mcp_contract(args.mcp_contract)
        provisioned_state = load_provisioned_state(args.provisioned_state)
        result = build_spfx_bpmn_viewer_skeleton_result(
            skeleton,
            mcp_contract=mcp_contract,
            provisioned_state=provisioned_state,
        )
        return _emit(
            result,
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "spfx-bpmn-viewer-process-selection":
        skeleton = load_spfx_bpmn_viewer_skeleton(args.spfx_bpmn_viewer_skeleton)
        mcp_contract = load_mcp_contract(args.mcp_contract)
        result = build_spfx_bpmn_viewer_process_selection_result(
            skeleton,
            mcp_contract=mcp_contract,
        )
        return _emit(
            result,
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if args.command == "bpmn-viewer-runtime-readiness":
        readiness = load_bpmn_viewer_runtime_readiness(args.bpmn_viewer_runtime_readiness)
        skeleton = load_spfx_bpmn_viewer_skeleton(args.spfx_bpmn_viewer_skeleton)
        provisioning = load_bpmn_viewer_provisioning_config(args.bpmn_viewer_config)
        mcp_contract = load_mcp_contract(args.mcp_contract)
        result = build_bpmn_viewer_runtime_readiness_result(
            readiness,
            skeleton=skeleton,
            provisioning=provisioning,
            mcp_contract=mcp_contract,
        )
        return _emit(
            result,
            args.json,
            return_code=0 if result["status"] == "PASSED" else 1,
        )

    if not args.owner_approved:
        return _emit(
            {
                "status": "BLOCKED",
                "errors": [f"{args.command} requires --owner-approved"],
            },
            args.json,
            return_code=2,
        )

    try:
        GraphConfig.from_env()
    except GraphConfigError as exc:
        return _emit(
            {
                "status": "BLOCKED",
                "errors": [str(exc)],
            },
            args.json,
            return_code=2,
        )

    return _emit(
        {
            "status": "BLOCKED",
            "errors": [
                f"{args.command} is intentionally blocked in the MVP skeleton until the first owner-gated live Graph REST smoke is approved."
            ],
            "planned_operations": summarize_plan(plan),
        },
        args.json,
        return_code=2,
    )


def _emit(payload: dict, as_json: bool, return_code: int = 0) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return return_code

    print(f"STATUS: {payload['status']}")
    if payload.get("message"):
        print(payload["message"])
    if payload.get("summary"):
        print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    if payload.get("result"):
        print(json.dumps(payload["result"], indent=2, ensure_ascii=False))
    for error in payload.get("errors", []):
        print(f"ERROR: {error}")
    return return_code


def _graph_error_code(body: str) -> str | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return code if isinstance(code, str) else None


if __name__ == "__main__":
    raise SystemExit(main())
