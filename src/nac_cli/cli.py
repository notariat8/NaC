from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from business_os.engine import BusinessProcessEngine
from nac_ai_sbom.export_mapping import ai_sbom_export_mapping_status
from nac_gnotkg.costs import quote_fee
from nac_identity.customer_onboarding import build_customer_tenant_plan, build_live_dns_check_result
from nac_identity.tenant_readiness import check_domain_ready
from nac_legal_graph.ai_sbom import legal_ai_sbom_delta_proposal_status
from nac_legal_graph.catalog import build_review_payload, legal_graph_status
from nac_legal_graph.model_card import legal_model_card_proposal_status
from nac_legal_graph.patches import build_update_patch
from nac_legal_graph.sources import legal_graph_source_status, legal_source_inventory_status
from nac_m365_graph.mcp_smoke_leftover_cleanup import DEFAULT_MCP_SMOKE_LEFTOVER_CLEANUP_OUTPUT
from nac_m365_graph.mcp_smoke_suite import DEFAULT_MCP_SMOKE_SUITE_OUTPUT
from nac_m365_graph.matter_access_apply_readiness import DEFAULT_MATTER_ACCESS_APPLY_READINESS_OUTPUT
from nac_m365_graph.release_gate_evidence import (
    DEFAULT_ARTIFACT_INDEX_OUTPUT,
    DEFAULT_EVIDENCE_JSON_OUTPUT,
    DEFAULT_EVIDENCE_OUTPUT,
    attach_release_gate_artifact_index,
    attach_release_gate_retention_reference,
    build_release_gate_evidence,
    DEFAULT_RUNTIME_ENV_BOOTSTRAP_ARTIFACT,
    write_release_gate_artifact_index,
    write_release_gate_evidence_json,
    write_release_gate_evidence_report,
)
from nac_m365_graph.runtime_metadata import DEFAULT_RUNTIME_METADATA_OUTPUT
from nac_m365_graph.runtime_certificate_readiness import (
    DEFAULT_CERTIFICATE_EXPIRY_CRITICAL_DAYS,
    DEFAULT_CERTIFICATE_EXPIRY_WARNING_DAYS,
    DEFAULT_RUNTIME_CERTIFICATE_EXPIRY_MONITOR_OUTPUT,
    DEFAULT_RUNTIME_SMOKE_STATE,
)
from nac_m365_graph.runtime_env_bootstrap import (
    DEFAULT_RUNTIME_CERTIFICATE_PATH,
    DEFAULT_RUNTIME_ENV_BOOTSTRAP_OUTPUT,
    DEFAULT_RUNTIME_PRIVATE_KEY_PATH,
    build_runtime_env_bootstrap,
    load_runtime_env_state,
    write_runtime_env_bootstrap_artifact,
)
from nac_m365_graph.runtime_smoke import DEFAULT_RUNTIME_SMOKE_OUTPUT
from nac_observability.time_ledger import (
    CATEGORY_CHOICES,
    append_entry,
    build_entry,
    format_summary_text,
    load_entries,
    parse_timestamp,
    run_timed_command,
    summarize_entries,
)
from nac_web.bpmn import bpmn_model_json, find_bpmn_model, list_bpmn_models, render_bpmn_svg
from nac_web.server import run_server
from notary_kg.catalog import all_case_summaries, load_catalogs
from notary_kg.cli import main as notary_kg_main

from . import __version__
from .import_jobs import apply_import_job_result, create_import_job, import_job_status, process_import_job
from .qms import qms_status, read_qms_text
from .tenant import (
    describe_matter,
    init_tenant_repo,
    list_matter_summaries,
    tenant_status,
    write_demo_case,
    write_sample_matter,
)


DEFAULT_PORT = 8765
DEFAULT_RELEASE_GATE_RUN_ARTIFACT_ROOT = Path("out/m365/teams-sharepoint/release-gates")
DEFAULT_RELEASE_GATE_COMPARE_ARTIFACT_ROOT = Path("out/m365/teams-sharepoint/release-gate-comparisons")
DEFAULT_RELEASE_GATE_COMPARE_INDEX_ARTIFACT_ROOT = Path("out/m365/teams-sharepoint/release-gate-comparison-indexes")
DEFAULT_RELEASE_GATE_AUDIT_PACK_ROOT = Path("out/m365/teams-sharepoint/release-gate-audit-packs")
DEFAULT_RELEASE_GATE_POST_RUN_REPORT_ROOT = Path("out/m365/teams-sharepoint/release-gate-post-run-reports")
DEFAULT_RELEASE_GATE_POST_RUN_REPORT_INDEX_ROOT = Path(
    "out/m365/teams-sharepoint/release-gate-post-run-report-indexes"
)
DEFAULT_RELEASE_GATE_INVENTORY_ARTIFACT = Path("out/m365/teams-sharepoint/mcp-inventory-smoke.redacted.json")
DEFAULT_RELEASE_GATE_MATTER_ACCESS_ARTIFACT = Path(
    "out/m365/teams-sharepoint/matter-access-delegation-smoke.redacted.json"
)
DEFAULT_RELEASE_GATE_MATTER_ACCESS_APPLY_READINESS_ARTIFACT = Path(
    "out/m365/teams-sharepoint/matter-access-apply-readiness.redacted.json"
)
DEFAULT_RELEASE_GATE_MATTER_ACCESS_APPLY_REQUEST_ARTIFACT = Path(
    "out/m365/teams-sharepoint/matter-access-apply-request-plan.redacted.json"
)
DEFAULT_RELEASE_READINESS_OUTPUT = Path("out/m365/teams-sharepoint/release-readiness.redacted.json")
M365_RELEASE_READINESS_REQUIRED_ARTIFACTS = (
    "runtime_certificate_expiry",
    "runtime_env_bootstrap",
    "runtime_smoke",
    "runtime_metadata",
    "mcp_inventory_smoke",
    "matter_access_delegation_smoke",
    "matter_access_apply_readiness",
    "matter_access_apply_request_plan",
    "mcp_smoke_suite",
    "mcp_leftover_dry_run",
    "release_gate_evidence_report",
    "release_gate_evidence_json",
    "release_gate_artifact_index",
)
M365_RELEASE_READINESS_REQUIRED_EVIDENCE_STEPS = (
    "runtime_certificate_expiry",
    "runtime_env_bootstrap",
    "runtime_smoke",
    "runtime_metadata",
    "mcp_inventory_smoke",
    "matter_access_delegation_smoke",
    "matter_access_apply_readiness",
    "matter_access_apply_request_plan",
    "mcp_smoke_suite",
    "mcp_leftover_dry_run",
)

PLUGIN_CLI_ROLES = {
    "cli_role": "kanonische Bedienkante der NaC-CLI für Prüfung, Automatisierung und Dokumentation.",
    "plugin_role": "Sichtbarkeit als Codex-Plugin, geführte Bedienung und Installationsmetadaten.",
}

EXECUTABLE_PLUGIN_COMMANDS = {
    "nac-cyberjack-rfid": {
        "command": "nac plugins card-readiness",
        "description": "Kartenleser-, SAK-/XNP- und lokale Readiness-Metadaten prüfen.",
    },
    "nac-bnotk-xnp": {
        "command": "nac plugins xnp-reader-prompt",
        "description": "XNP-Reader-Prompt mit vorgeschaltetem Karten-Gate erzeugen.",
    },
    "nac-pkcs7-certbundle": {
        "command": "nac plugins pkcs7-inspect",
        "description": "Lokales PKCS7/P7B/P7C-Zertifikatsbündel metadata-only prüfen.",
    },
}

EXTRA_PLUGIN_ACTIONS = [
    {
        "plugin": "nac-bnotk-xnp",
        "command": "nac plugins xnp-workflow-gate",
        "description": "XNP-Reader-Prompt-Nachweis als Workflow-Gate auswerten.",
        "cli_status": "executable",
    },
]


@dataclass(frozen=True, slots=True)
class ConfigEntry:
    id: str
    path: str
    group: str
    description: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nac",
        description="Zentrale CLI für Notariat as Code.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Pfad zum NaC-Repository. Standard: aktuelles Verzeichnis.",
    )
    parser.add_argument("--version", action="version", version=f"nac {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Zeigt den lokalen NaC-Überblick.")
    status.add_argument("--format", choices=["text", "json"], default="text")
    status.set_defaults(func=command_status)

    doctor = subparsers.add_parser("doctor", help="Führt das NaC Quality Gate aus.")
    doctor.add_argument("--profile", choices=["minimal", "standard", "strict"], default="strict")
    doctor.add_argument("--json-output", type=Path, default=Path("out/quality/status.json"))
    doctor.add_argument("--md-output", type=Path, default=Path("out/quality/report.md"))
    doctor.set_defaults(func=command_doctor)

    web = subparsers.add_parser("web", help="Startet den lokalen NaC-Webserver.")
    add_web_args(web, default_port=DEFAULT_PORT)
    web.set_defaults(func=command_web)

    preview = subparsers.add_parser("preview", help="Alias für `nac web`.")
    add_web_args(preview, default_port=DEFAULT_PORT)
    preview.set_defaults(func=command_web)

    operator = subparsers.add_parser("operator", help="Startet die lokale Operator-Webapp mit Hardware-Bridge.")
    add_web_args(operator, default_port=8766)
    operator.set_defaults(func=command_operator)

    kg = subparsers.add_parser("kg", help="Steuert usecase-lokale Knowledge Graphs.")
    kg.add_argument("--format", choices=["text", "json"], default="text")
    kg_sub = kg.add_subparsers(dest="kg_command", required=True)
    kg_sub.add_parser("status", help="Zeigt KG-Status und Entwicklungskandidaten.")
    kg_case = kg_sub.add_parser("case", help="Zeigt einen KG-Usecase.")
    kg_case.add_argument("slug")
    kg_editor = kg_sub.add_parser("editor-view", help="Zeigt die sichere KG-Editor-Ansicht.")
    kg_editor.add_argument("slug")
    kg_cost = kg_sub.add_parser("cost-view", help="Zeigt die sichere GNotKG-Kostenansicht.")
    kg_cost.add_argument("slug")
    kg_workflow_contract = kg_sub.add_parser(
        "workflow-contract",
        help="Erzeugt einen sicheren Workflow-Vertragsentwurf aus einem KG-Usecase.",
    )
    kg_workflow_contract.add_argument("slug")
    kg_pilot_checklist = kg_sub.add_parser(
        "pilot-checklist",
        help="Erzeugt eine deterministische Pilot-Aufnahmecheckliste aus einem KG-Usecase.",
    )
    kg_pilot_checklist.add_argument("slug")
    kg.set_defaults(func=command_kg)

    gnotkg = subparsers.add_parser("gnotkg", help="Berechnet technische GNotKG-Kostenentwürfe.")
    gnotkg_sub = gnotkg.add_subparsers(dest="gnotkg_command", required=True)
    gnotkg_quote = gnotkg_sub.add_parser("quote", help="Berechnet eine lokale Wertgebühr ohne Speicherung.")
    gnotkg_quote.add_argument("--business-value", required=True, help="Geschäftswert, z.B. 500000.")
    gnotkg_quote.add_argument("--table", choices=["A", "B"], required=True, help="GNotKG-Tabelle.")
    gnotkg_quote.add_argument("--fee-rate", default="1.0", help="Gebührensatz, z.B. 2.0.")
    gnotkg_quote.add_argument("--kv-number", default="", help="Optionale KV-Nummer aus Anlage 1.")
    gnotkg_quote.add_argument("--usecase-slug", default="", help="Optionaler NaC-Usecase-Slug.")
    gnotkg_quote.add_argument("--format", choices=["text", "json"], default="text")
    gnotkg.set_defaults(func=command_gnotkg)

    ai_sbom = subparsers.add_parser("ai-sbom", help="Steuert AI-SBOM-Governance-Artefakte.")
    ai_sbom_sub = ai_sbom.add_subparsers(dest="ai_sbom_command", required=True)
    ai_sbom_export_mapping = ai_sbom_sub.add_parser(
        "export-mapping",
        help="Zeigt das gewählte CycloneDX/SPDX-Mapping ohne Release-Export.",
    )
    ai_sbom_export_mapping.add_argument("--format", choices=["text", "json"], default="text")
    ai_sbom.set_defaults(func=command_ai_sbom)

    bpmn = subparsers.add_parser("bpmn", help="Steuert BPMN-Prozessmodelle.")
    bpmn_sub = bpmn.add_subparsers(dest="bpmn_command", required=True)
    bpmn_list = bpmn_sub.add_parser("list", help="Listet vorhandene BPMN-Modelle.")
    bpmn_list.add_argument("--format", choices=["text", "json"], default="text")
    bpmn_show = bpmn_sub.add_parser("show", help="Zeigt ein BPMN-Modell.")
    bpmn_show.add_argument("stem")
    bpmn_show.add_argument("--format", choices=["text", "json", "svg"], default="text")
    bpmn_sub.add_parser("validate", help="Validiert alle BPMN-Modelle.")
    bpmn.set_defaults(func=command_bpmn)

    process = subparsers.add_parser("process", help="Steuert deterministische Prozessanträge.")
    process_sub = process.add_subparsers(dest="process_command", required=True)
    process_validate = process_sub.add_parser("validate", help="Validiert einen Prozessantrag.")
    process_validate.add_argument("path", type=Path)
    process_sub.add_parser("validate-all", help="Validiert alle Prozessanträge.")
    process_summary = process_sub.add_parser("render-summary", help="Erzeugt eine Kurzfassung.")
    process_summary.add_argument("path", type=Path)
    process_close = process_sub.add_parser("monthly-close", help="Erstellt Monatsabschluss-JSON.")
    process_close.add_argument("--year", required=True, type=int)
    process_close.add_argument("--month", required=True, type=int)
    process.set_defaults(func=command_process)

    contracts = subparsers.add_parser("contracts", help="Prüft NaC-Workflow-Verträge.")
    contracts_sub = contracts.add_subparsers(dest="contracts_command", required=True)
    contracts_sub.add_parser("validate", help="Validiert Workflow-Verträge, Secure-Link- und Connector-Grenzen.")
    contracts.set_defaults(func=command_contracts)

    batch_approval = subparsers.add_parser("batch-approval", help="Rendert kopierbare Batch-Freigaben.")
    batch_approval_sub = batch_approval.add_subparsers(dest="batch_approval_command", required=True)
    batch_m365 = batch_approval_sub.add_parser(
        "m365",
        help="Rendert M365-MCP-Batch-Freigaben ohne GitHub- oder Graph-Schreibaktion.",
    )
    batch_m365.add_argument(
        "--batch-mode",
        choices=[
            "merge",
            "live-smoke",
            "merge-and-live-smoke",
            "release-gate",
            "runtime-certificate-rotation",
        ],
        default="merge",
        help="Batch-Freigabetext, der gerendert werden soll.",
    )
    batch_m365.add_argument(
        "--batch-pr",
        action="append",
        default=[],
        help="Pull-Request-Nummer fuer Batch-Merge-Freigaben. Wiederholbar oder kommasepariert.",
    )
    batch_m365.add_argument("--workspace-id", default="notary_team_01", help="Workspace-ID fuer Live-Smoke-Text.")
    batch_m365.add_argument(
        "--synthetic-case-id",
        help=(
            "Optionale synthetische Case-ID fuer Live-Smoke-Freigabetext. "
            "Ohne Wert erzeugt die Smoke Suite die ID nur im Prozessspeicher."
        ),
    )
    batch_m365.add_argument(
        "--correlation-id",
        default="m365-mcp-batch-approval",
        help="Nicht-geheime Correlation-ID fuer Live-Smoke-Befehle.",
    )
    batch_m365.add_argument(
        "--release-gate-write-audit-pack",
        action="store_true",
        help=(
            "Ergaenzt Release-Gate-Freigabetexte um das direkte redigierte Offline-Audit-Pack. "
            "Bei release-gate und runtime-certificate-rotation ist dies als MVP-Standard impliziert."
        ),
    )
    batch_m365.add_argument(
        "--release-gate-write-readiness",
        action="store_true",
        help=(
            "Ergaenzt Release-Gate-Freigabetexte um den direkten redigierten MVP-Readiness-Status. "
            "Bei release-gate und runtime-certificate-rotation ist dies als MVP-Standard impliziert."
        ),
    )
    batch_m365.add_argument(
        "--release-gate-readiness-require-audit-pack",
        action="store_true",
        help=(
            "Blockiert den direkten MVP-Readiness-Status, wenn kein passendes Audit-Pack mit PASSED vorliegt. "
            "Bei release-gate und runtime-certificate-rotation ist dies als MVP-Standard impliziert."
        ),
    )
    batch_m365.add_argument(
        "--release-gate-compare-left",
        help="Optionale Baseline-Correlation-ID fuer das Audit-Pack im Release-Gate-Batch-Approval.",
    )
    batch_m365.add_argument(
        "--release-gate-audit-pack-dir",
        help="Optionaler Zielordner fuer das Audit-Pack im Release-Gate-Batch-Approval.",
    )
    batch_m365.add_argument("--format", choices=["text", "json"], default="text")
    batch_approval.set_defaults(func=command_batch_approval)

    m365 = subparsers.add_parser("m365", help="Steuert Microsoft-365-Graph-REST-Bedienkanten.")
    m365_sub = m365.add_subparsers(dest="m365_command", required=True)
    teams_sharepoint = m365_sub.add_parser(
        "teams-sharepoint",
        help="Plant und steuert die Teams/SharePoint-MVP-Datenebene.",
    )
    teams_sharepoint.add_argument(
        "teams_sharepoint_command",
        choices=[
            "validate",
            "plan",
            "application-owner-readiness",
            "bpmn-viewer-plan",
            "matter-access-plan",
            "matter-access-apply-request-plan",
            "matter-access-apply-readiness",
            "matter-access-smoke",
            "bpmn-viewer-runtime-readiness",
            "spfx-bpmn-viewer-skeleton",
            "privileged-plan",
            "privileged-apply",
            "runtime-certificate-expiry-monitor",
            "runtime-certificate-readiness",
            "runtime-env-bootstrap",
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
            "release-gate-evidence",
            "release-gate-retention-audit-pack",
            "release-gate-retention-compare",
            "release-gate-retention-compare-artifact",
            "release-gate-retention-compare-index",
            "release-gate-retention-compare-index-artifact",
            "release-gate-retention-list",
            "release-gate-post-run-report",
            "release-gate-post-run-report-index",
            "release-gate-post-run-report-index-artifact",
            "release-readiness",
            "release-gate-run",
            "apply",
            "drift",
            "export",
        ],
    )
    teams_sharepoint.add_argument("--schema", type=Path, help="Optionales Teams/SharePoint-Schema.")
    teams_sharepoint.add_argument(
        "--bpmn-viewer-config",
        type=Path,
        help="Optionaler BPMN-Viewer-Provisioning-Plan ohne Live-Apply.",
    )
    teams_sharepoint.add_argument(
        "--matter-access-contract",
        type=Path,
        help="Optionaler M365-Mandatszugriffsdelegationsvertrag ohne Live-Apply.",
    )
    teams_sharepoint.add_argument(
        "--bpmn-viewer-runtime-readiness",
        type=Path,
        help="Optionales BPMN-Viewer-Runtime-Readiness-Artefakt ohne Paketierung, App-Catalog-Deploy oder Live-Content-Read.",
    )
    teams_sharepoint.add_argument(
        "--spfx-bpmn-viewer-skeleton",
        type=Path,
        help="Optionales SPFx-BPMN-Viewer-Skeleton ohne Paketierung oder App-Catalog-Deploy.",
    )
    teams_sharepoint.add_argument(
        "--privileged-config",
        type=Path,
        help="Optionaler privilegierter M365-Change-Path.",
    )
    teams_sharepoint.add_argument(
        "--provisioned-state",
        type=Path,
        help="Optionaler nicht-geheimer provisionierter Teams/SharePoint-State.",
    )
    teams_sharepoint.add_argument(
        "--privileged-applied-state",
        type=Path,
        help="Optionaler nicht-geheimer angewendeter Privileged-Change-State.",
    )
    teams_sharepoint.add_argument("--mcp-contract", type=Path, help="Optionaler Teams/SharePoint-Data-MCP-Vertrag.")
    teams_sharepoint.add_argument(
        "--runtime-smoke-output",
        type=Path,
        help="Pfad fuer das redigierte Runtime-Smoke-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--runtime-smoke-state",
        type=Path,
        help="Optionaler nicht-geheimer Runtime-Smoke-Evidence-State.",
    )
    teams_sharepoint.add_argument(
        "--runtime-metadata-output",
        type=Path,
        help="Pfad fuer das redigierte Runtime-Metadata-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--runtime-metadata-state",
        type=Path,
        help="Optionaler nicht-geheimer Runtime-Metadata-Evidence-State.",
    )
    teams_sharepoint.add_argument(
        "--runtime-certificate-expiry-output",
        type=Path,
        help="Pfad fuer das redigierte Runtime-Certificate-Expiry-Monitor-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--runtime-env-bootstrap-output",
        type=Path,
        help="Pfad fuer das redigierte Runtime-Env-Bootstrap-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--runtime-certificate-path",
        type=Path,
        help="Lokaler Runtime-Certificate-Pfad fuer das nicht-geheime Env-Bootstrap.",
    )
    teams_sharepoint.add_argument(
        "--runtime-private-key-path",
        type=Path,
        help="Lokaler Runtime-Private-Key-Pfad fuer das nicht-geheime Env-Bootstrap; Inhalt wird nicht gelesen.",
    )
    teams_sharepoint.add_argument(
        "--runtime-certificate-warning-days",
        type=int,
        default=DEFAULT_CERTIFICATE_EXPIRY_WARNING_DAYS,
        help="Warnschwelle in Tagen fuer den Runtime-Zertifikatsablauf.",
    )
    teams_sharepoint.add_argument(
        "--runtime-certificate-critical-days",
        type=int,
        default=DEFAULT_CERTIFICATE_EXPIRY_CRITICAL_DAYS,
        help="Kritische Schwelle in Tagen fuer den Runtime-Zertifikatsablauf.",
    )
    teams_sharepoint.add_argument(
        "--mcp-live-read",
        action="store_true",
        help="Aktiviert owner-gated Live-Reads fuer case_get und document_list im MCP-stdio-Adapter.",
    )
    teams_sharepoint.add_argument(
        "--mcp-smoke-tool",
        choices=["case_get", "document_list"],
        help="Optionales Tool fuer den MCP-Live-Read-Smoke.",
    )
    teams_sharepoint.add_argument("--mcp-smoke-workspace-id", help="Workspace-ID fuer den MCP-Live-Read-Smoke.")
    teams_sharepoint.add_argument(
        "--mcp-smoke-case-id",
        help=(
            "Case-ID fuer den MCP-Live-Read-Smoke, Pflicht fuer Smoke-Cleanup "
            "oder optional fuer Positive-Write-Read-Smoke und Smoke-Suite."
        ),
    )
    teams_sharepoint.add_argument(
        "--mcp-smoke-correlation-id",
        help="Correlation-ID fuer MCP-Smoke- und Cleanup-Artefakte.",
    )
    teams_sharepoint.add_argument(
        "--mcp-smoke-output",
        type=Path,
        help="Pfad fuer das redigierte MCP-Live-Read-Smoke-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--mcp-inventory-smoke-output",
        type=Path,
        help="Pfad fuer das redigierte MCP-Inventory-Smoke-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--matter-access-smoke-output",
        type=Path,
        help="Pfad fuer das redigierte Matter-Access-Delegation-Smoke-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--matter-access-apply-readiness-output",
        type=Path,
        help="Pfad fuer das redigierte Matter-Access-Apply-Readiness-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--matter-access-apply-request-output",
        type=Path,
        help="Pfad fuer das redigierte Matter-Access-Apply-Request-Plan-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--matter-access-grant-id",
        help="Synthetischer Grant-ID-Seed; redigierte Artefakte speichern nur einen Hash.",
    )
    teams_sharepoint.add_argument(
        "--matter-access-from-user",
        help="Synthetischer FromUser-Seed; redigierte Artefakte speichern nur einen Hash.",
    )
    teams_sharepoint.add_argument(
        "--matter-access-to-user",
        help="Synthetischer ToUser-Seed; redigierte Artefakte speichern nur einen Hash.",
    )
    teams_sharepoint.add_argument("--matter-access-granted-role", default="SachbearbeitungVertretung")
    teams_sharepoint.add_argument("--matter-access-reason", default="Synthetischer Offline-Vertretungsfreigabeplan")
    teams_sharepoint.add_argument("--matter-access-valid-from", default="2026-07-08T09:00:00Z")
    teams_sharepoint.add_argument("--matter-access-valid-until", default="2026-07-15T09:00:00Z")
    teams_sharepoint.add_argument(
        "--matter-access-approved-by",
        help="Synthetischer ApprovedBy-Seed; redigierte Artefakte speichern nur einen Hash.",
    )
    teams_sharepoint.add_argument("--matter-access-status", default="Aktiv")
    teams_sharepoint.add_argument(
        "--mcp-positive-smoke-output",
        type=Path,
        help="Pfad fuer das redigierte MCP-Positive-Write-Read-Smoke-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--mcp-cleanup-output",
        type=Path,
        help="Pfad fuer das redigierte MCP-Smoke-Cleanup-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--mcp-leftover-output",
        type=Path,
        help="Pfad fuer das redigierte MCP-Smoke-Leftover-Cleanup-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--mcp-leftover-dry-run",
        action="store_true",
        help="Liest synthetische Smoke-Reste nur owner-gated, ohne zu löschen.",
    )
    teams_sharepoint.add_argument(
        "--mcp-suite-output",
        type=Path,
        help="Pfad fuer das redigierte MCP-Smoke-Suite-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--mcp-suite-cleanup",
        action="store_true",
        help="Fuehrt Write-Read-Smoke und Cleanup derselben synthetischen Akte in einem owner-gated Lauf aus.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-evidence-output",
        type=Path,
        help="Pfad fuer den redigierten M365-Release-Gate-Abschlussbericht.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-evidence-json-output",
        type=Path,
        help="Pfad fuer das redigierte maschinenlesbare M365-Release-Gate-Evidence-JSON.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-artifact-index-output",
        type=Path,
        help="Pfad fuer den redigierten M365-Release-Gate-Artefaktindex.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-run-artifact-dir",
        type=Path,
        help=(
            "Optionaler Laufordner fuer redigierte Release-Gate-Artefaktkopien; "
            "standardmaessig out/m365/teams-sharepoint/release-gates/<correlation-id>/."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-retention-root",
        type=Path,
        help=(
            "Optionaler Root-Ordner fuer release-gate-retention-list und release-gate-retention-compare; "
            "standardmaessig out/m365/teams-sharepoint/release-gates/."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-compare-left",
        help=(
            "Linker Release-Gate-Lauf fuer release-gate-retention-compare oder Filter fuer compare-index; "
            "akzeptiert Correlation-ID, Laufordner oder Retention-Index-Pfad."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-compare-right",
        help=(
            "Rechter Release-Gate-Lauf fuer release-gate-retention-compare oder Filter fuer compare-index; "
            "akzeptiert Correlation-ID, Laufordner oder Retention-Index-Pfad."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-compare-output",
        type=Path,
        help="Optionaler Markdown-Pfad fuer das redigierte Release-Gate-Retention-Compare-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-compare-json-output",
        type=Path,
        help="Optionaler JSON-Pfad fuer das redigierte Release-Gate-Retention-Compare-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-compare-index-root",
        type=Path,
        help=(
            "Optionaler Root-Ordner fuer release-gate-retention-compare-index; "
            "standardmaessig out/m365/teams-sharepoint/release-gate-comparisons/."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-compare-query",
        help=(
            "Optionaler Suchtext fuer release-gate-retention-compare-index; "
            "sucht in Left/Right-Correlation-ID, Status, Timestamp, Report- und JSON-Pfad."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-compare-status",
        help="Optionaler Statusfilter fuer release-gate-retention-compare-index.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-compare-index-output",
        type=Path,
        help="Optionaler Markdown-Pfad fuer das redigierte Release-Gate-Retention-Compare-Index-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-compare-index-json-output",
        type=Path,
        help="Optionaler JSON-Pfad fuer das redigierte Release-Gate-Retention-Compare-Index-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-audit-pack-dir",
        type=Path,
        help=(
            "Optionaler Zielordner fuer release-gate-retention-audit-pack; "
            "standardmaessig out/m365/teams-sharepoint/release-gate-audit-packs/<filter>/."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-readiness-correlation-id",
        help=(
            "Optionaler Release-Gate-Lauf fuer release-readiness; ohne Wert wird der neueste "
            "lokale Retention-Lauf verwendet."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-readiness-output",
        type=Path,
        help="Optionaler JSON-Pfad fuer den redigierten release-readiness-Status.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-readiness-require-audit-pack",
        action="store_true",
        help="Blockiert release-readiness, wenn kein passendes redigiertes Audit-Pack mit Status PASSED vorliegt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-post-run-report-output",
        type=Path,
        help="Optionaler Markdown-Pfad fuer den redigierten Offline-Post-Gate-Report.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-post-run-report-json-output",
        type=Path,
        help="Optionaler JSON-Pfad fuer den redigierten Offline-Post-Gate-Report.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-github-comment-output",
        type=Path,
        help="Optionaler Markdown-Pfad fuer den redigierten GitHub-Nachweiskommentarentwurf.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-post-run-report-root",
        type=Path,
        help=(
            "Optionaler Root-Ordner fuer release-gate-post-run-report-index; "
            "standardmaessig out/m365/teams-sharepoint/release-gate-post-run-reports/."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-post-run-report-correlation-id",
        help="Optionaler Correlation-ID-Filter fuer release-gate-post-run-report-index.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-post-run-report-baseline",
        help="Optionaler Baseline-Correlation-ID-Filter fuer release-gate-post-run-report-index.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-post-run-report-status",
        help="Optionaler Statusfilter fuer release-gate-post-run-report-index.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-post-run-report-query",
        help=(
            "Optionaler Suchtext fuer release-gate-post-run-report-index; sucht in Correlation-ID, "
            "Baseline, Status, Workspace, Readiness, Report-, JSON- und Kommentar-Pfad."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-post-run-report-index-output",
        type=Path,
        help="Optionaler Markdown-Pfad fuer das redigierte Post-Gate-Report-Index-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-post-run-report-index-json-output",
        type=Path,
        help="Optionaler JSON-Pfad fuer das redigierte Post-Gate-Report-Index-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-write-audit-pack",
        action="store_true",
        help=(
            "Schreibt nach erfolgreichem release-gate-run direkt ein redigiertes Offline-Audit-Pack; "
            "rechts ist standardmaessig die aktuelle Correlation-ID."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-write-readiness",
        action="store_true",
        help=(
            "Schreibt nach erfolgreichem release-gate-run direkt den redigierten MVP-Readiness-Status "
            "des aktuellen Laufs und blockiert bei NOT_READY."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-write-post-run-report",
        action="store_true",
        help=(
            "Schreibt nach erfolgreichem release-gate-run direkt den redigierten Offline-Post-Gate-Report "
            "und einen lokalen GitHub-Nachweiskommentarentwurf; impliziert Audit-Pack, Readiness und "
            "Audit-Pack-Pflicht fuer Readiness."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-write-post-run-report-index",
        action="store_true",
        help=(
            "Schreibt nach erfolgreichem release-gate-run direkt ein redigiertes Offline-Index-Artefakt "
            "der Post-Gate-Reports; impliziert --release-gate-write-post-run-report."
        ),
    )
    teams_sharepoint.add_argument(
        "--release-gate-suite-artifact",
        type=Path,
        help="Optionaler Pfad zum redigierten MCP-Smoke-Suite-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-leftover-artifact",
        type=Path,
        help="Optionaler Pfad zum redigierten MCP-Smoke-Leftover-Dry-Run-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-inventory-artifact",
        type=Path,
        help="Optionaler Pfad zum redigierten MCP-Inventory-Smoke-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-matter-access-artifact",
        type=Path,
        help="Optionaler Pfad zum redigierten Matter-Access-Delegation-Smoke-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-matter-access-apply-readiness-artifact",
        type=Path,
        help="Optionaler Pfad zum redigierten Matter-Access-Apply-Readiness-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-matter-access-apply-request-artifact",
        type=Path,
        help="Optionaler Pfad zum redigierten Matter-Access-Apply-Request-Plan-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-runtime-smoke-artifact",
        type=Path,
        help="Optionaler Pfad zu einem redigierten Runtime-Smoke-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-runtime-certificate-expiry-artifact",
        type=Path,
        help="Optionaler Pfad zu einem redigierten Runtime-Certificate-Expiry-Monitor-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-runtime-env-bootstrap-artifact",
        type=Path,
        help="Optionaler Pfad zu einem redigierten Runtime-Env-Bootstrap-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-runtime-metadata-artifact",
        type=Path,
        help="Optionaler Pfad zu einem redigierten Runtime-Metadata-Artefakt.",
    )
    teams_sharepoint.add_argument(
        "--release-gate-require-runtime-artifacts",
        action="store_true",
        help="Blockiert den Evidence-Export, wenn Runtime-Smoke- oder Runtime-Metadata-Artefakte fehlen.",
    )
    teams_sharepoint.add_argument("--owner-approved", action="store_true", help="Pflicht für Live-Apply.")
    teams_sharepoint.add_argument("--format", choices=["text", "json"], default="text")
    m365.set_defaults(func=command_m365)

    import_parser = subparsers.add_parser("import", help="Steuert Eingang, OCR-/Extraktionsjobs und Import-Vorschläge.")
    import_sub = import_parser.add_subparsers(dest="import_command", required=True)
    import_jobs = import_sub.add_parser("jobs", help="Steuert begrenzte Import-Jobs für Codex.")
    import_jobs_sub = import_jobs.add_subparsers(dest="jobs_command", required=True)
    import_jobs_create = import_jobs_sub.add_parser("create", help="Legt einen Import-Job für einen Vorschlag an.")
    import_jobs_create.add_argument("--repo", type=Path, required=True, help="Pfad zum getrennten NaC-Datenrepo.")
    import_jobs_create.add_argument("--proposal-id", required=True, help="Import-Vorschlag, der verarbeitet werden soll.")
    import_jobs_create.add_argument("--requested-by", default="codex", help="Anfordernde lokale Bedienkante.")
    import_jobs_create.add_argument("--action", default="ocr_metadata_extract", choices=["ocr_metadata_extract"])
    import_jobs_create.add_argument("--format", choices=["text", "json"], default="text")
    import_jobs_status = import_jobs_sub.add_parser("status", help="Listet Import-Jobs und Extraktionsstände.")
    import_jobs_status.add_argument("--repo", type=Path, required=True, help="Pfad zum getrennten NaC-Datenrepo.")
    import_jobs_status.add_argument("--job-id", help="Optionaler einzelner Import-Job.")
    import_jobs_status.add_argument("--format", choices=["text", "json"], default="text")
    import_jobs_process = import_jobs_sub.add_parser("process", help="Verarbeitet einen Import-Job metadata-only.")
    import_jobs_process.add_argument("--repo", type=Path, required=True, help="Pfad zum getrennten NaC-Datenrepo.")
    import_jobs_process.add_argument("--job-id", required=True, help="Import-Job-ID.")
    import_jobs_process.add_argument("--processed-by", default="codex", help="Lokaler Ausführer.")
    import_jobs_process.add_argument("--format", choices=["text", "json"], default="text")
    import_jobs_apply = import_jobs_sub.add_parser("apply-result", help="Übernimmt ein Extraktionsergebnis in den Import-Vorschlag.")
    import_jobs_apply.add_argument("--repo", type=Path, required=True, help="Pfad zum getrennten NaC-Datenrepo.")
    import_jobs_apply.add_argument("--job-id", required=True, help="Import-Job-ID.")
    import_jobs_apply.add_argument("--applied-by", default="nac-local-operator-webapp", help="Lokale Bedienkante für die Übernahme.")
    import_jobs_apply.add_argument("--format", choices=["text", "json"], default="text")
    import_parser.set_defaults(func=command_import)

    plugins = subparsers.add_parser("plugins", help="Steuert lokale NaC-Plugins.")
    plugins_sub = plugins.add_subparsers(dest="plugins_command", required=True)
    plugins_actions = plugins_sub.add_parser("actions", help="Listet fachliche Plugin-Befehle.")
    plugins_actions.add_argument("--format", choices=["text", "json"], default="text")
    plugins_status = plugins_sub.add_parser("status", help="Zeigt CLI-Status aller NaC-Anbindungen.")
    plugins_status.add_argument("plugin", nargs="?", help="Optionaler Plugin-Name, z.B. nac-grundbuch-portal.")
    plugins_status.add_argument("--format", choices=["text", "json"], default="text")
    plugins_install = plugins_sub.add_parser("install", help="Spiegelt repo-lokale Plugins.")
    plugins_install.add_argument("--mode", choices=["dry-run", "link", "copy"], default="dry-run")
    plugins_install.add_argument("--target-root", type=Path)
    plugins_install.add_argument("--force", action="store_true")
    plugins_sub.add_parser("validate", help="Validiert Plugin-Manifeste.")
    plugins_card = plugins_sub.add_parser("card-readiness", help="Prüft Karten-/SAK-Bereitschaft lokal.")
    add_card_readiness_args(plugins_card)
    plugins_xnp = plugins_sub.add_parser("xnp-reader-prompt", help="Erzeugt XNP-Reader-Prompt und Card-Gate-Nachweis.")
    add_xnp_reader_prompt_args(plugins_xnp)
    plugins_xnp_gate = plugins_sub.add_parser(
        "xnp-workflow-gate",
        help="Wertet XNP-Reader-Prompt-Nachweis als Workflow-Gate aus.",
    )
    add_xnp_workflow_gate_args(plugins_xnp_gate)
    plugins_pkcs7 = plugins_sub.add_parser("pkcs7-inspect", help="Prüft PKCS7/P7B/P7C-Zertifikatsbündel lokal.")
    add_pkcs7_inspect_args(plugins_pkcs7)
    plugins.set_defaults(func=command_plugins)

    config = subparsers.add_parser("config", help="Zeigt und prüft NaC-Konfigurationen.")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    config_list = config_sub.add_parser("list", help="Listet steuernde Konfigurationsdateien.")
    config_list.add_argument("--format", choices=["text", "json"], default="text")
    config_show = config_sub.add_parser("show", help="Gibt eine Konfiguration aus.")
    config_show.add_argument("id_or_path")
    config_sub.add_parser("validate", help="Prüft die wichtigsten Konfigurationsregeln.")
    config.set_defaults(func=command_config)

    qms = subparsers.add_parser("qms", help="Steuert die NaC-QMS- und ISO-9001-Schicht.")
    qms_sub = qms.add_subparsers(dest="qms_command", required=True)
    qms_status_parser = qms_sub.add_parser("status", help="Zeigt QMS-Artefakte und Bereitschaft.")
    qms_status_parser.add_argument("--format", choices=["text", "json"], default="text")
    qms_status_parser.add_argument("--repo", type=Path, help="Optionales Datenrepo für Nachweiszählung.")
    qms_sub.add_parser("iso9001-map", help="Gibt das ISO-9001-Mapping aus.")
    qms_sub.add_parser("audit-plan", help="Gibt das interne Auditprogramm aus.")
    qms_evidence = qms_sub.add_parser("evidence", help="Zeigt QMS-Nachweiszahlen aus einem Datenrepo.")
    qms_evidence.add_argument("--repo", type=Path, required=True, help="Pfad zum NaC-Datenrepo.")
    qms_evidence.add_argument("--format", choices=["text", "json"], default="text")
    qms.set_defaults(func=command_qms)

    time_ledger = subparsers.add_parser(
        "time-ledger",
        help="Protokolliert und summiert Codex-Arbeitszeiten.",
    )
    time_ledger_sub = time_ledger.add_subparsers(dest="time_ledger_command", required=True)
    time_ledger_add = time_ledger_sub.add_parser("add", help="Schreibt einen abgeschlossenen Zeitblock.")
    add_time_ledger_common_args(time_ledger_add)
    time_ledger_add.add_argument("--started-at", required=True, help="Startzeit als ISO-8601, z.B. 2026-06-15T10:00:00Z.")
    time_ledger_add.add_argument("--ended-at", required=True, help="Endzeit als ISO-8601, z.B. 2026-06-15T10:05:00Z.")
    time_ledger_add.add_argument("--outcome", choices=["completed", "failed", "interrupted"], default="completed")
    time_ledger_add.add_argument("--command", default="", help="Optionaler Command-String ohne Secrets.")
    time_ledger_add.add_argument("--format", choices=["text", "json"], default="text")
    time_ledger_run = time_ledger_sub.add_parser("run", help="Führt ein Kindkommando aus und misst die Dauer.")
    add_time_ledger_common_args(time_ledger_run)
    time_ledger_run.add_argument("--format", choices=["text", "json"], default="text")
    time_ledger_run.add_argument("child_command", nargs=argparse.REMAINDER)
    time_ledger_summary = time_ledger_sub.add_parser("summary", help="Summiert ein Codex-Time-Ledger.")
    time_ledger_summary.add_argument("--log", type=Path, default=Path("out/observability/codex-time-ledger.jsonl"))
    time_ledger_summary.add_argument("--session-id", help="Optional nur eine Session auswerten.")
    time_ledger_summary.add_argument("--format", choices=["text", "json"], default="text")
    time_ledger.set_defaults(func=command_time_ledger)

    legal_graph = subparsers.add_parser("legal-graph", help="Steuert den NaC-Rechtsgraphen.")
    legal_graph_sub = legal_graph.add_subparsers(dest="legal_graph_command", required=True)
    legal_graph_status_parser = legal_graph_sub.add_parser(
        "status",
        help="Zeigt Legal-Graph-Domänen und Reviewstatus.",
    )
    legal_graph_status_parser.add_argument("--format", choices=["text", "json"], default="text")
    legal_graph_sources = legal_graph_sub.add_parser(
        "sources",
        help="Zeigt Primärquellen-Manifeste und Zugriffspolitik.",
    )
    legal_graph_sources.add_argument("--format", choices=["text", "json"], default="text")
    legal_graph_source_inventory = legal_graph_sub.add_parser(
        "source-inventory",
        help="Zeigt Quelleninventar-, Lizenz- und TDM-Gates ohne Ingestion.",
    )
    legal_graph_source_inventory.add_argument("--format", choices=["text", "json"], default="text")
    legal_graph_model_card = legal_graph_sub.add_parser(
        "model-card-proposal",
        help="Zeigt den metadata-only Model-Card-Vorschlag ohne Checkpoint.",
    )
    legal_graph_model_card.add_argument("--format", choices=["text", "json"], default="text")
    legal_graph_ai_sbom_delta = legal_graph_sub.add_parser(
        "ai-sbom-delta-proposal",
        help="Zeigt den metadata-only AI-SBOM-Delta-Vorschlag ohne Runtime.",
    )
    legal_graph_ai_sbom_delta.add_argument("--format", choices=["text", "json"], default="text")
    legal_graph_review = legal_graph_sub.add_parser(
        "review",
        help="Zeigt eine Review-Ansicht für eine Legal-Graph-Domäne.",
    )
    legal_graph_review.add_argument("domain")
    legal_graph_review.add_argument("--format", choices=["text", "json"], default="text")
    legal_graph_update = legal_graph_sub.add_parser("update-dry-run", help="Erzeugt einen Review-Patch ohne Merge.")
    legal_graph_update.add_argument("domain")
    legal_graph_update.add_argument("--format", choices=["text", "json"], default="text")
    legal_graph.set_defaults(func=command_legal_graph)

    tenant = subparsers.add_parser("tenant", help="Steuert getrennte NaC-Datenrepositories.")
    tenant_sub = tenant.add_subparsers(dest="tenant_command", required=True)
    tenant_init = tenant_sub.add_parser("init", help="Initialisiert ein getrenntes NaC-Datenrepo.")
    tenant_init.add_argument("--repo", type=Path, required=True, help="Pfad zum Datenrepo, getrennt vom NaC-Repo.")
    tenant_init.add_argument("--name", help="Anzeigename des Datenrepos. Standard: Ordnername.")
    tenant_init.add_argument("--mode", choices=["demo", "production"], default="demo")
    tenant_init.add_argument("--remote-url", help="Optionaler Git-Remote für das Datenrepo.")
    tenant_init.add_argument("--force", action="store_true", help="Manifest und Standarddateien überschreiben.")
    tenant_status_parser = tenant_sub.add_parser("status", help="Prüft ein NaC-Datenrepo.")
    tenant_status_parser.add_argument("--repo", type=Path, required=True, help="Pfad zum Datenrepo.")
    tenant_status_parser.add_argument("--format", choices=["text", "json"], default="text")
    tenant_list = tenant_sub.add_parser("list-akten", help="Listet Akten aus dem Datenrepo.")
    tenant_list.add_argument("--repo", type=Path, required=True, help="Pfad zum Datenrepo.")
    tenant_list.add_argument("--format", choices=["text", "json"], default="text")
    tenant_show = tenant_sub.add_parser("show-akte", help="Zeigt eine Akte mit aufgelösten ID-Pointern.")
    tenant_show.add_argument("--repo", type=Path, required=True, help="Pfad zum Datenrepo.")
    tenant_show.add_argument("--akten-id", required=True, help="Akte oder Aktenzeichen, z.B. UVZ-2026-0001.")
    tenant_show.add_argument("--format", choices=["text", "json"], default="text")
    tenant_write_demo = tenant_sub.add_parser("write-demo", help="Schreibt synthetische Demo-Vorgangsdaten.")
    tenant_write_demo.add_argument("slug", help="NaC-Usecase-Slug, zum Beispiel immobilienkaufvertrag.")
    tenant_write_demo.add_argument("--repo", type=Path, required=True, help="Pfad zum Datenrepo.")
    tenant_write_demo.add_argument("--case-id", help="Optionale Demo-Vorgangs-ID.")
    tenant_write_demo.add_argument("--force", action="store_true", help="Bestehenden Demo-Vorgang überschreiben.")
    tenant_write_demo.add_argument("--format", choices=["text", "json"], default="text")
    tenant_sample = tenant_sub.add_parser("write-sample-akte", help="Schreibt eine synthetische Musterakte im ID-Pointer-Modell.")
    tenant_sample.add_argument("--repo", type=Path, required=True, help="Pfad zum Datenrepo.")
    tenant_sample.add_argument("--akten-id", help="Optionale technische Akten-ID. Standard: UVZ-2026-0001.")
    tenant_sample.add_argument("--force", action="store_true", help="Bestehende Musterakte überschreiben.")
    tenant_sample.add_argument("--format", choices=["text", "json"], default="text")
    tenant_domain = tenant_sub.add_parser("domain-check", help="Prüft Domain-Readiness für NaC-SaaS-Tenant-Onboarding.")
    tenant_domain.add_argument("--domain", required=True, help="Kundendomain, z.B. kanzlei-notariat.example.")
    tenant_domain.add_argument("--tenant-slug", required=True, help="Stabiler Tenant-Slug, keine Secrets.")
    tenant_domain.add_argument("--admin-email", required=True, help="Initiale Admin-E-Mail zur Kundendomain.")
    tenant_domain.add_argument("--format", choices=["text", "json"], default="text")
    tenant_customer_plan = tenant_sub.add_parser("customer-plan", help="Erzeugt einen Customer-Tenant-Onboarding-Plan.")
    tenant_customer_plan.add_argument("--domain", required=True, help="Kundendomain.")
    tenant_customer_plan.add_argument("--tenant-slug", required=True, help="Stabiler Tenant-Slug.")
    tenant_customer_plan.add_argument("--admin-email", required=True, help="Initiale Admin-E-Mail zur Kundendomain.")
    tenant_customer_plan.add_argument("--saas-admin-email", required=True, help="SaaS-Owner für Owner-Apply-Review.")
    tenant_customer_plan.add_argument("--format", choices=["text", "json"], default="text")
    tenant_dns = tenant_sub.add_parser("dns-check", help="Prüft den DNS-TXT-Record live über DNS.")
    tenant_dns.add_argument("--domain", required=True, help="Kundendomain.")
    tenant_dns.add_argument("--tenant-slug", required=True, help="Stabiler Tenant-Slug.")
    tenant_dns.add_argument("--admin-email", required=True, help="Initiale Admin-E-Mail zur Kundendomain.")
    tenant_dns.add_argument("--format", choices=["text", "json"], default="text")
    tenant.set_defaults(func=command_tenant)

    return parser


def add_web_args(parser: argparse.ArgumentParser, default_port: int) -> None:
    parser.add_argument("--host", default="127.0.0.1", help="Bind-Adresse. Standard: 127.0.0.1.")
    parser.add_argument("--port", type=int, default=default_port, help=f"Port. Standard: {default_port}.")
    parser.add_argument("--open", action="store_true", help="Browser nach Serverstart öffnen.")


def add_card_readiness_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manual-card-present", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument("--manual-rfid-off", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument("--output", type=Path, help="Optionaler JSON-Nachweispfad.")
    parser.add_argument("--json", action="store_true", help="Vollen JSON-Nachweis ausgeben.")
    parser.add_argument(
        "--probe-morris-api",
        action="store_true",
        help="Lokale morris-Loopback-API ohne Karten- oder PIN-Daten aktiv prüfen.",
    )
    parser.add_argument("--strict", action="store_true", help="Nur bei vollständiger Bereitschaft mit 0 beenden.")


def add_xnp_reader_prompt_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt", help="Optionaler lokaler Bedienhinweis. Keine Secrets eintragen.")
    parser.add_argument(
        "--intent",
        choices=["reader_function_check", "xnp_login_preflight", "online_hra_preflight"],
        default="reader_function_check",
    )
    parser.add_argument("--manual-card-present", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument("--manual-rfid-off", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument("--output", type=Path, help="Optionaler JSON-Nachweispfad.")
    parser.add_argument("--json", action="store_true", help="Vollen JSON-Nachweis ausgeben.")
    parser.add_argument(
        "--probe-morris-api",
        action="store_true",
        help="Karten-Gate soll die lokale morris-Loopback-API aktiv prüfen.",
    )
    parser.add_argument("--strict", action="store_true", help="Nur bei promptfähigem Stand mit 0 beenden.")


def add_xnp_workflow_gate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--evidence", type=Path, help="Vorhandener XNP-Reader-Prompt-Nachweis.")
    parser.add_argument("--usecase", default="online-gmbh-gruendung", help="Usecase-Slug für das Workflow-Gate.")
    parser.add_argument("--prompt", help="Optionaler lokaler Bedienhinweis, falls der Nachweis inline erzeugt wird.")
    parser.add_argument(
        "--intent",
        choices=["reader_function_check", "xnp_login_preflight", "online_hra_preflight"],
        default="reader_function_check",
    )
    parser.add_argument("--manual-card-present", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument("--manual-rfid-off", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument("--output", type=Path, help="Optionaler JSON-Gate-Nachweispfad.")
    parser.add_argument("--json", action="store_true", help="Vollen JSON-Gate-Nachweis ausgeben.")
    parser.add_argument(
        "--probe-morris-api",
        action="store_true",
        help="Karten-Gate soll die lokale morris-Loopback-API aktiv prüfen.",
    )
    parser.add_argument("--strict", action="store_true", help="Nur bei vorbereitbarem Workflow-Gate mit 0 beenden.")


def add_pkcs7_inspect_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input",
        type=Path,
        help="Lokaler PKCS7/P7B/P7C-Zertifikatsbündelpfad. Keine PFX/P12/Key-Dateien übergeben.",
    )
    parser.add_argument("--max-bytes", type=int, default=5 * 1024 * 1024)
    parser.add_argument("--output", type=Path, help="Optionaler JSON-Nachweispfad.")
    parser.add_argument("--json", action="store_true", help="Vollen JSON-Nachweis ausgeben.")
    parser.add_argument("--strict", action="store_true", help="Nur bei bereitem Zertifikatsbündel-Gate mit 0 beenden.")


def add_time_ledger_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--log", type=Path, default=Path("out/observability/codex-time-ledger.jsonl"))
    parser.add_argument("--session-id", required=True, help="Stabile Session-ID, z.B. 2026-06-15-nac.")
    parser.add_argument("--task", required=True, help="Kurzer Arbeitsauftrag oder Issue-/Plan-Bezug.")
    parser.add_argument("--phase", required=True, help="Messphase, z.B. context-read, tests oder approval.")
    parser.add_argument("--category", choices=CATEGORY_CHOICES, required=True)
    parser.add_argument("--actor", default="codex", help="Ausführer des Zeitblocks, Standard: codex.")
    parser.add_argument("--notes", default="", help="Optionale knappe Notiz ohne Mandatsdaten oder Secrets.")


def command_status(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    catalogs = load_catalogs(repo_root)
    cases = all_case_summaries(catalogs)
    bpmn_models = list_bpmn_models(repo_root)
    configs = discover_config_entries(repo_root)
    payload = {
        "schema_version": "nac.status/v0.1",
        "repo_root": str(repo_root),
        "usecases": len(cases),
        "p0_usecases": sum(1 for case in cases if case.priority == "P0"),
        "open_required_information": sum(case.open_required_information for case in cases),
        "bpmn_models": len(bpmn_models),
        "configs": len(configs),
        "commands": {
            "quality_gate": "nac doctor --profile strict",
            "local_web": "nac web",
            "local_operator": "nac operator --open",
            "kg_status": "nac kg status",
            "legal_graph_status": "nac legal-graph status",
            "legal_graph_sources": "nac legal-graph sources",
            "ai_sbom_export_mapping": "nac ai-sbom export-mapping",
            "bpmn_validate": "nac bpmn validate",
            "contracts_validate": "nac contracts validate",
            "m365_teams_sharepoint_plan": "nac m365 teams-sharepoint plan",
            "config_validate": "nac config validate",
            "plugin_actions": "nac plugins actions",
            "tenant_status": "nac tenant status --repo ../demo8notariat",
            "time_ledger_summary": "nac time-ledger summary",
        },
    }
    if args.format == "json":
        print_json(payload)
        return 0

    print("NaC Status")
    print(f"- Repository: {repo_root}")
    print(f"- Usecases mit KG: {payload['usecases']} ({payload['p0_usecases']} P0)")
    print(f"- Offene Pflichtangaben: {payload['open_required_information']}")
    print(f"- BPMN-Modelle: {payload['bpmn_models']}")
    print(f"- Steuernde Konfigurationen: {payload['configs']}")
    print("")
    print("Nächste Befehle")
    for command in payload["commands"].values():
        print(f"- {command}")
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    return run_script(
        repo_root,
        "scripts/quality_gate.py",
        [
            "--profile",
            args.profile,
            "--json-output",
            str(args.json_output),
            "--md-output",
            str(args.md_output),
        ],
    )


def command_web(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    run_server(repo_root, args.host, args.port, open_browser=args.open)
    return 0


def command_operator(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    return run_script(
        repo_root,
        "scripts/nac_hw_bridge.py",
        [
            "--host",
            args.host,
            "--port",
            str(args.port),
            *optional_flag(args.open, "--open"),
        ],
    )


def command_kg(args: argparse.Namespace) -> int:
    argv = ["--repo-root", str(resolve_repo_root(args.repo_root)), "--format", args.format, args.kg_command]
    if getattr(args, "slug", None):
        argv.append(args.slug)
    return notary_kg_main(argv)


def command_gnotkg(args: argparse.Namespace) -> int:
    if args.gnotkg_command == "quote":
        try:
            quote = quote_fee(
                business_value=Decimal(args.business_value),
                table=args.table,
                fee_rate=Decimal(args.fee_rate),
                kv_number=args.kv_number,
                usecase_slug=args.usecase_slug,
            )
        except (ValueError, ArithmeticError) as exc:
            print(f"ERROR: {exc}")
            return 1
        if args.format == "json":
            print(quote.to_json())
            return 0
        print("GNotKG-Kostenentwurf")
        print(f"- Geschäftswert: {quote.to_dict()['business_value']}")
        print(f"- Tabelle: {quote.table}")
        print(f"- Gebührensatz: {quote.to_dict()['fee_rate']}")
        print(f"- Basisgebühr: {quote.to_dict()['base_fee']}")
        print(f"- Gebühr: {quote.to_dict()['fee_amount']}")
        print("- Hinweis: finale notarielle Kostenprüfung bleibt erforderlich.")
        return 0

    raise AssertionError(f"Unknown GNotKG command: {args.gnotkg_command}")


def command_ai_sbom(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    try:
        if args.ai_sbom_command == "export-mapping":
            payload = ai_sbom_export_mapping_status(repo_root)
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC AI-SBOM Export Mapping")
            print(f"- Status: {payload['status']}")
            print(f"- Release-Export aktiv: {payload['release_export_enabled']}")
            print(f"- Externe Toolausführung aktiv: {payload['external_tool_execution_enabled']}")
            print(f"- Mandatsdaten erlaubt: {payload['mandate_data_allowed']}")
            print(f"- Secrets erlaubt: {payload['secret_material_allowed']}")
            print(
                "- Owner-Apply vor Release-Bindung: "
                f"{payload['owner_apply_required_before_release_binding']}"
            )
            for item in payload["target_profiles"]:
                print(f"- {item['id']}: {item['format']}, Release-Bindung: {item['release_binding']}")
            return 0
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        message = str(exc.args[0]) if isinstance(exc, KeyError) and exc.args else str(exc)
        if args.format == "json":
            print_json(
                {
                    "schema_version": "nac.error/v0.1",
                    "command": "ai-sbom",
                    "error": message,
                }
            )
            return 1
        print(f"ERROR: {message}")
        return 1

    raise AssertionError(f"Unknown AI-SBOM command: {args.ai_sbom_command}")


def command_legal_graph(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    try:
        if args.legal_graph_command == "status":
            payload = legal_graph_status(repo_root)
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC Legal Graph")
            for item in payload["domain_status"]:
                print(
                    f"- {item['id']}: {item['nodes']} Knoten, "
                    f"{item['edges']} Kanten, {item['review_required']} Reviewpunkte"
                )
            return 0

        if args.legal_graph_command == "sources":
            payload = legal_graph_source_status(repo_root)
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC Legal Graph Sources")
            for item in payload["source_status"]:
                print(
                    f"- {item['domain']}: {item['source_id']}, "
                    f"{item['retrieval_mode']}, Kommentarzugriff: {item['commentary_access_allowed']}"
                )
            return 0

        if args.legal_graph_command == "source-inventory":
            payload = legal_source_inventory_status(repo_root)
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC Legal Source Inventory")
            print(f"- Status: {payload['status']}")
            print(f"- Quellen: {payload['sources']}")
            print(f"- Planung ohne Ingestion: {payload['planning_only']}")
            print(f"- Owner-Apply vor Ingestion: {payload['owner_apply_required_before_ingestion']}")
            for item in payload["source_status"]:
                print(
                    f"- {item['source_id']}: {item['source_class']}, "
                    f"Lizenz: {item['license_status']}, TDM: {item['tdm_status']}"
                )
            return 0

        if args.legal_graph_command == "model-card-proposal":
            payload = legal_model_card_proposal_status(repo_root)
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC Legal Model Card Proposal")
            print(f"- Status: {payload['status']}")
            print(f"- Abschnitte: {payload['sections']}")
            print(f"- Keine Mandatsdaten: {payload['no_mandate_data']}")
            print(f"- Kein Checkpoint: {payload['no_checkpoint_published']}")
            print(f"- Owner-Apply vor Nutzung: {payload['owner_apply_required_before_use']}")
            for item in payload["candidate_references"]:
                print(f"- {item['id']}: {item['status']}")
            return 0

        if args.legal_graph_command == "ai-sbom-delta-proposal":
            payload = legal_ai_sbom_delta_proposal_status(repo_root)
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC Legal AI-SBOM Delta Proposal")
            print(f"- Status: {payload['status']}")
            print(f"- Delta-Komponenten: {len(payload['delta_components'])}")
            print(f"- Keine Mandatsdaten: {payload['no_mandate_data']}")
            print(f"- Kein Checkpoint: {payload['no_checkpoint_published']}")
            print(f"- Keine Runtime: {payload['no_runtime_enabled']}")
            print(
                "- Owner-Apply vor Runtime oder Checkpoint: "
                f"{payload['owner_apply_required_before_runtime_or_checkpoint']}"
            )
            for item in payload["candidate_components"]:
                print(f"- {item['id']}: {item['status']}")
            return 0

        if args.legal_graph_command == "review":
            payload = build_review_payload(repo_root, args.domain)
            if args.format == "json":
                print_json(payload)
                return 0
            print(f"NaC Legal Graph Review: {payload['domain']}")
            for item in payload["review_items"]:
                print(f"- {item['id']}: {item['status']}")
            return 0

        if args.legal_graph_command == "update-dry-run":
            payload = build_update_patch(repo_root, args.domain)
            if args.format == "json":
                print_json(payload)
                return 0
            print(f"NaC Legal Graph Update-Dry-run: {payload['domain']}")
            print(f"- Änderungen: {len(payload['changes'])}")
            print(f"- Auto-Merge: {payload['auto_merge_allowed']}")
            return 0
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        message = str(exc.args[0]) if isinstance(exc, KeyError) and exc.args else str(exc)
        if args.format == "json":
            print_json(
                {
                    "schema_version": "nac.error/v0.1",
                    "command": "legal-graph",
                    "error": message,
                }
            )
            return 1
        print(f"ERROR: {message}")
        return 1

    raise AssertionError(f"Unknown legal graph command: {args.legal_graph_command}")


def command_bpmn(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    if args.bpmn_command == "validate":
        return run_script(repo_root, "scripts/validate_bpmn_models.py", [])

    if args.bpmn_command == "list":
        models = list_bpmn_models(repo_root)
        if args.format == "json":
            print_json({"models": [model.to_dict() for model in models]})
            return 0
        print("BPMN-Modelle")
        for model in models:
            marker = "mit Diagramm" if model.has_diagram else "ohne Diagramm"
            print(f"- {model.stem}: {model.name} ({marker})")
        return 0

    if args.bpmn_command == "show":
        try:
            model = find_bpmn_model(repo_root, args.stem)
        except KeyError as exc:
            print(f"ERROR: {exc}")
            return 1
        if args.format == "json":
            print(bpmn_model_json(model))
            return 0
        if args.format == "svg":
            print(render_bpmn_svg(model))
            return 0
        print(f"{model.stem}: {model.name}")
        print(f"- Datei: {model.path}")
        print(f"- Prozess-ID: {model.process_id}")
        print(f"- Diagrammfläche: {'ja' if model.has_diagram else 'nein'}")
        print(f"- Knoten: {len(model.nodes)}")
        print(f"- Sequenzflüsse: {len(model.flows)}")
        return 0

    raise AssertionError(f"Unknown BPMN command: {args.bpmn_command}")


def command_process(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    engine = BusinessProcessEngine(repo_root=repo_root)

    if args.process_command == "validate":
        result = engine.validate_document(args.path)
        print_validation(result.errors, result.warnings)
        return 0 if result.ok else 1

    if args.process_command == "validate-all":
        overall_ok = True
        for result in engine.validate_all_processes():
            relative_path = result.document.path.relative_to(engine.repo_root)
            print(f"[{relative_path}]")
            print_validation(result.errors, result.warnings)
            if not result.ok:
                overall_ok = False
        return 0 if overall_ok else 1

    if args.process_command == "render-summary":
        print(engine.render_summary(args.path))
        return 0

    if args.process_command == "monthly-close":
        print(engine.monthly_close(year=args.year, month=args.month).to_json())
        return 0

    raise AssertionError(f"Unknown process command: {args.process_command}")


def command_contracts(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    if args.contracts_command == "validate":
        validators = [
            ("GNotKG Cost Review Contract", "validate_gnotkg_costs.py"),
            ("Secure Document Link Contract", "validate_secure_document_links.py"),
            ("Legal Research Connectors", "validate_legal_research_connectors.py"),
            ("Legal Graph Contracts", "validate_legal_graph_contracts.py"),
            ("Teams SharePoint Graph Data Plane", "validate_teams_sharepoint_graph_data_plane.py"),
            ("M365 Matter Access Delegation", "validate_m365_matter_access_delegation.py"),
            ("Spec Traceability Contract", "validate_spec_traceability.py"),
        ]
        overall_rc = 0
        for title, script_name in validators:
            print(title)
            result = subprocess.run(
                [sys.executable, str(repo_root / "scripts" / script_name)],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(result.stderr.rstrip())
            if result.returncode != 0:
                overall_rc = result.returncode
        return overall_rc

    raise AssertionError(f"Unknown contracts command: {args.contracts_command}")


def command_batch_approval(args: argparse.Namespace) -> int:
    if args.batch_approval_command != "m365":
        raise AssertionError(f"Unknown batch approval command: {args.batch_approval_command}")

    try:
        payload = _build_m365_batch_approval_payload(
            mode=args.batch_mode,
            batch_prs=args.batch_pr,
            workspace_id=args.workspace_id,
            synthetic_case_id=args.synthetic_case_id,
            correlation_id=args.correlation_id,
            release_gate_write_audit_pack=args.release_gate_write_audit_pack,
            release_gate_write_readiness=args.release_gate_write_readiness,
            release_gate_readiness_require_audit_pack=args.release_gate_readiness_require_audit_pack,
            release_gate_compare_left=args.release_gate_compare_left,
            release_gate_audit_pack_dir=args.release_gate_audit_pack_dir,
        )
    except ValueError as exc:
        payload = {"status": "BLOCKED", "errors": [str(exc)]}
        _print_batch_approval_payload(payload, args.format)
        return 2

    _print_batch_approval_payload(payload, args.format)
    return 0


def _build_m365_batch_approval_payload(
    *,
    mode: str,
    batch_prs: list[str],
    workspace_id: str,
    synthetic_case_id: str | None,
    correlation_id: str,
    release_gate_write_audit_pack: bool = False,
    release_gate_write_readiness: bool = False,
    release_gate_readiness_require_audit_pack: bool = False,
    release_gate_compare_left: str | None = None,
    release_gate_audit_pack_dir: str | None = None,
) -> dict:
    prs = _normalize_batch_prs(batch_prs)
    (
        release_gate_write_audit_pack,
        release_gate_write_readiness,
        release_gate_readiness_require_audit_pack,
    ) = _apply_m365_release_gate_mvp_defaults(
        mode=mode,
        release_gate_write_audit_pack=release_gate_write_audit_pack,
        release_gate_write_readiness=release_gate_write_readiness,
        release_gate_readiness_require_audit_pack=release_gate_readiness_require_audit_pack,
    )
    if mode in {"merge", "merge-and-live-smoke"} and not prs:
        raise ValueError("batch-approval m365 merge mode requires at least one --batch-pr")
    if not release_gate_write_audit_pack and (release_gate_compare_left or release_gate_audit_pack_dir):
        raise ValueError(
            "--release-gate-compare-left and --release-gate-audit-pack-dir "
            "require --release-gate-write-audit-pack"
        )

    approvals: dict[str, dict] = {}
    if mode in {"merge", "merge-and-live-smoke"}:
        approvals["merge"] = {
            "approval_text": f"Freigabe: PRs {', '.join(prs)} mergen und Branches nach Merge aufräumen.",
            "owner_gate": "merge_to_main_and_branch_cleanup",
            "prs": prs,
        }

    if mode in {"live-smoke", "merge-and-live-smoke"}:
        suite_command, leftover_dry_run_command = _build_m365_mcp_smoke_suite_commands(
            workspace_id=workspace_id,
            synthetic_case_id=synthetic_case_id,
            correlation_id=correlation_id,
        )
        approvals["live_smoke"] = {
            "approval_text": (
                "Freigabe: M365 MCP Smoke Suite live mit synthetischer Testakte "
                f"im Workspace {workspace_id} ausführen, positive write-read und Cleanup "
                "im gleichen Lauf."
            ),
            "owner_gate": "m365_tenant_write_and_delete",
            "workspace_id": workspace_id,
            "synthetic_case_id": synthetic_case_id or "generated_in_process_memory",
            "commands": [
                suite_command,
                leftover_dry_run_command,
            ],
            "operator_sequence": [
                {
                    "step": "mcp_smoke_suite",
                    "owner_gate": "m365_tenant_write_and_delete",
                    "command": suite_command,
                },
                {
                    "step": "mcp_smoke_leftover_cleanup_dry_run",
                    "owner_gate": "m365_tenant_read_only",
                    "command": leftover_dry_run_command,
                },
            ],
        }

    if mode == "release-gate":
        release_gate_run_command = _build_m365_release_gate_run_command(
            workspace_id=workspace_id,
            correlation_id=correlation_id,
            synthetic_case_id=synthetic_case_id,
            write_audit_pack=release_gate_write_audit_pack,
            write_readiness=release_gate_write_readiness,
            readiness_require_audit_pack=release_gate_readiness_require_audit_pack,
            compare_left=release_gate_compare_left,
            audit_pack_dir=release_gate_audit_pack_dir,
        )
        release_gate_covers_steps = [
            "mcp_inventory_smoke",
            "matter_access_delegation_smoke",
            "matter_access_apply_readiness",
            "matter_access_apply_request_plan",
            "runtime_certificate_expiry_monitor",
            "runtime_smoke",
            "runtime_metadata",
            "mcp_smoke_suite",
            "mcp_smoke_leftover_cleanup_dry_run",
            "release_gate_evidence_export",
        ]
        post_step_suffixes: list[str] = []
        if release_gate_write_audit_pack:
            release_gate_covers_steps.append("release_gate_audit_pack")
            audit_pack_suffix = "direktem redigiertem Release-Gate-Audit-Pack"
            if release_gate_compare_left:
                audit_pack_suffix += f" gegen Baseline {release_gate_compare_left}"
            else:
                audit_pack_suffix += " als Self-Compare des aktuellen Laufs"
            post_step_suffixes.append(audit_pack_suffix)
        if release_gate_write_readiness:
            release_gate_covers_steps.append("release_gate_readiness")
            post_step_suffixes.append("direktem redigiertem MVP-Readiness-Status")
        post_step_suffix = f" sowie {' und '.join(post_step_suffixes)}" if post_step_suffixes else ""
        approvals["release_gate"] = {
            "approval_text": (
                "Freigabe: M365 Runtime Release-Gate live über den One-Shot-Runner "
                f"im Workspace {workspace_id} ausführen, inklusive "
                "runtime-certificate-expiry-monitor, runtime-smoke, "
                "runtime-metadata, Matter-Access-Smoke, Matter-Access-Apply-Readiness, "
                "Matter-Access-Apply-Request-Plan, "
                "MCP Smoke Suite mit Cleanup, Leftover-Dry-Run "
                f"und release-gate-evidence Export{post_step_suffix}."
            ),
            "owner_gate": "m365_runtime_release_gate",
            "workspace_id": workspace_id,
            "synthetic_case_id": synthetic_case_id or "generated_in_process_memory",
            "release_gate_write_audit_pack": release_gate_write_audit_pack,
            "release_gate_write_readiness": release_gate_write_readiness,
            "release_gate_readiness_require_audit_pack": release_gate_readiness_require_audit_pack,
            "release_gate_compare_left": release_gate_compare_left,
            "release_gate_audit_pack_dir": release_gate_audit_pack_dir,
            "commands": [release_gate_run_command],
            "operator_sequence": [
                {
                    "step": "release_gate_run",
                    "owner_gate": "m365_runtime_release_gate",
                    "command": release_gate_run_command,
                    "covers_steps": release_gate_covers_steps,
                },
            ],
        }

    if mode == "runtime-certificate-rotation":
        readiness_command = (
            "python3 scripts/nac.py m365 teams-sharepoint "
            "runtime-certificate-readiness --format json"
        )
        release_gate_run_command = _build_m365_release_gate_run_command(
            workspace_id=workspace_id,
            correlation_id=correlation_id,
            synthetic_case_id=synthetic_case_id,
            write_audit_pack=release_gate_write_audit_pack,
            write_readiness=release_gate_write_readiness,
            readiness_require_audit_pack=release_gate_readiness_require_audit_pack,
            compare_left=release_gate_compare_left,
            audit_pack_dir=release_gate_audit_pack_dir,
        )
        rotation_release_gate_covers_steps = [
            "mcp_inventory_smoke",
            "matter_access_delegation_smoke",
            "matter_access_apply_readiness",
            "matter_access_apply_request_plan",
            "runtime_certificate_expiry_monitor",
            "runtime_smoke",
            "runtime_metadata",
            "mcp_smoke_suite",
            "mcp_smoke_leftover_cleanup_dry_run",
            "release_gate_evidence_export",
        ]
        rotation_post_step_suffixes: list[str] = []
        if release_gate_write_audit_pack:
            rotation_release_gate_covers_steps.append("release_gate_audit_pack")
            rotation_audit_pack_suffix = "direktem redigiertem Release-Gate-Audit-Pack"
            if release_gate_compare_left:
                rotation_audit_pack_suffix += f" gegen Baseline {release_gate_compare_left}"
            else:
                rotation_audit_pack_suffix += " als Self-Compare des aktuellen Laufs"
            rotation_post_step_suffixes.append(rotation_audit_pack_suffix)
        if release_gate_write_readiness:
            rotation_release_gate_covers_steps.append("release_gate_readiness")
            rotation_post_step_suffixes.append("direktem redigiertem MVP-Readiness-Status")
        rotation_post_step_suffix = (
            f" mit {' und '.join(rotation_post_step_suffixes)}" if rotation_post_step_suffixes else ""
        )
        approvals["runtime_certificate_rotation"] = {
            "approval_text": (
                "Freigabe: M365 Runtime-Zertifikat rotieren als gebündelten Owner-gated "
                "Lifecycle: neues lokales Runtime-Zertifikat erzeugen, Public Certificate "
                "in Entra für die Runtime-App hochladen, lokale Runtime-Credential-Grenzen "
                f"aktualisieren, M365 Runtime Release-Gate live im Workspace {workspace_id} "
                f"ausführen{rotation_post_step_suffix}, "
                "nicht-geheime Runtime-Evidence refreshen, altes Runtime-Zertifikat "
                "aus Entra entfernen, lokales Archiv des alten Zertifikats löschen und lokale "
                "M365-CLI-Session abmelden."
            ),
            "owner_gate": "m365_runtime_certificate_rotation_lifecycle",
            "workspace_id": workspace_id,
            "synthetic_case_id": synthetic_case_id or "generated_in_process_memory",
            "release_gate_write_audit_pack": release_gate_write_audit_pack,
            "release_gate_write_readiness": release_gate_write_readiness,
            "release_gate_readiness_require_audit_pack": release_gate_readiness_require_audit_pack,
            "release_gate_compare_left": release_gate_compare_left,
            "release_gate_audit_pack_dir": release_gate_audit_pack_dir,
            "commands": [
                readiness_command,
                release_gate_run_command,
            ],
            "operator_sequence": [
                {
                    "step": "runtime_certificate_readiness",
                    "owner_gate": "none",
                    "command": readiness_command,
                    "executes_graph_requests": False,
                    "reads_certificate_files": False,
                    "reads_private_key_files": False,
                },
                {
                    "step": "generate_local_runtime_certificate",
                    "owner_gate": "local_certificate_material",
                    "stores_in_repo": False,
                    "expected_location": "/tmp or approved local secret storage",
                },
                {
                    "step": "upload_public_certificate_to_entra_runtime_app",
                    "owner_gate": "entra_app_credential_change",
                    "graph_boundary": "Microsoft Graph REST v1.0 only",
                    "private_key_uploaded": False,
                },
                {
                    "step": "update_local_runtime_credential_boundary",
                    "owner_gate": "local_secret_boundary_change",
                    "stores_in_repo": False,
                },
                {
                    "step": "release_gate_run",
                    "owner_gate": "m365_runtime_release_gate",
                    "command": release_gate_run_command,
                    "covers_steps": rotation_release_gate_covers_steps,
                },
                {
                    "step": "refresh_non_secret_runtime_evidence_pr",
                    "owner_gate": "merge_to_main_and_branch_cleanup",
                    "stores_secret_material": False,
                },
                {
                    "step": "remove_stale_entra_runtime_certificate",
                    "owner_gate": "entra_app_credential_delete",
                    "requires_successful_new_certificate_gate": True,
                },
                {
                    "step": "delete_local_old_certificate_archive",
                    "owner_gate": "local_destructive_secret_cleanup",
                    "requires_stale_entra_credential_removed": True,
                },
                {
                    "step": "logout_local_delegated_m365_cli_session",
                    "owner_gate": "local_session_cleanup",
                },
            ],
        }

    return {
        "status": "PASSED",
        "summary": {
            "batch_mode": mode,
            "executes_github_writes": False,
            "executes_graph_requests": False,
            "reads_certificate_files": False,
            "reads_private_key_files": False,
            "reads_secret_values": False,
            "release_gate_write_audit_pack": release_gate_write_audit_pack,
            "release_gate_write_readiness": release_gate_write_readiness,
            "release_gate_readiness_require_audit_pack": release_gate_readiness_require_audit_pack,
            "owner_gates": [approval["owner_gate"] for approval in approvals.values()],
        },
        "result": approvals,
    }


def _apply_m365_release_gate_mvp_defaults(
    *,
    mode: str,
    release_gate_write_audit_pack: bool,
    release_gate_write_readiness: bool,
    release_gate_readiness_require_audit_pack: bool,
) -> tuple[bool, bool, bool]:
    if mode not in {"release-gate", "runtime-certificate-rotation"}:
        return (
            release_gate_write_audit_pack,
            release_gate_write_readiness,
            release_gate_readiness_require_audit_pack,
        )

    return (True, True, True)


def _build_m365_release_gate_run_command(
    *,
    workspace_id: str,
    correlation_id: str,
    synthetic_case_id: str | None,
    write_audit_pack: bool,
    write_readiness: bool,
    readiness_require_audit_pack: bool,
    compare_left: str | None,
    audit_pack_dir: str | None,
) -> str:
    command = [
        "python3",
        "scripts/nac.py",
        "m365",
        "teams-sharepoint",
        "release-gate-run",
        "--owner-approved",
        "--mcp-smoke-workspace-id",
        workspace_id,
    ]
    if synthetic_case_id:
        command.extend(["--mcp-smoke-case-id", synthetic_case_id])
    command.extend(["--mcp-smoke-correlation-id", correlation_id])
    if write_audit_pack:
        command.append("--release-gate-write-audit-pack")
        if compare_left:
            command.extend(["--release-gate-compare-left", compare_left])
        if audit_pack_dir:
            command.extend(["--release-gate-audit-pack-dir", audit_pack_dir])
    if write_readiness:
        command.append("--release-gate-write-readiness")
        if readiness_require_audit_pack:
            command.append("--release-gate-readiness-require-audit-pack")
    command.extend(["--format", "json"])
    return shlex.join(command)


def _build_m365_mcp_smoke_suite_commands(
    *,
    workspace_id: str,
    synthetic_case_id: str | None,
    correlation_id: str,
) -> tuple[str, str]:
    suite_case_id_arg = f"--mcp-smoke-case-id {synthetic_case_id} " if synthetic_case_id else ""
    suite_command = (
        "python3 scripts/nac.py m365 teams-sharepoint "
        "mcp-smoke-suite --owner-approved --mcp-suite-cleanup "
        f"--mcp-smoke-workspace-id {workspace_id} "
        f"{suite_case_id_arg}"
        f"--mcp-smoke-correlation-id {correlation_id} "
        "--format json"
    )
    leftover_dry_run_command = (
        "python3 scripts/nac.py m365 teams-sharepoint "
        "mcp-smoke-leftover-cleanup --owner-approved --mcp-leftover-dry-run "
        f"--mcp-smoke-workspace-id {workspace_id} "
        f"--mcp-smoke-correlation-id {correlation_id} "
        "--format json"
    )
    return suite_command, leftover_dry_run_command


def _normalize_batch_prs(values: list[str]) -> list[str]:
    prs: list[str] = []
    for value in values:
        for part in value.split(","):
            raw = part.strip()
            if not raw:
                continue
            if raw.startswith("#"):
                raw = raw[1:]
            if not raw.isdigit():
                raise ValueError(f"invalid pull request number for --batch-pr: {part.strip()}")
            prs.append(f"#{int(raw)}")
    return prs


def _print_batch_approval_payload(payload: dict, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    print(f"STATUS: {payload['status']}")
    for approval in payload.get("result", {}).values():
        print(approval["approval_text"])
    for error in payload.get("errors", []):
        print(f"ERROR: {error}")


def command_m365(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    if args.m365_command == "teams-sharepoint":
        if args.teams_sharepoint_command == "runtime-env-bootstrap":
            runtime_state_path = _resolve_m365_release_gate_path(
                repo_root,
                args.runtime_smoke_state,
                DEFAULT_RUNTIME_SMOKE_STATE,
            )
            output_path = _resolve_m365_release_gate_path(
                repo_root,
                args.runtime_env_bootstrap_output,
                DEFAULT_RUNTIME_ENV_BOOTSTRAP_OUTPUT,
            )
            certificate_path = args.runtime_certificate_path or DEFAULT_RUNTIME_CERTIFICATE_PATH
            private_key_path = args.runtime_private_key_path or DEFAULT_RUNTIME_PRIVATE_KEY_PATH
            try:
                runtime_state = load_runtime_env_state(runtime_state_path)
                bootstrap = build_runtime_env_bootstrap(
                    runtime_state,
                    certificate_path=certificate_path,
                    private_key_path=private_key_path,
                )
                bootstrap.readiness["summary"]["artifact_path"] = str(output_path)
                write_runtime_env_bootstrap_artifact(bootstrap.readiness, output_path)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                payload = {
                    "status": "BLOCKED",
                    "summary": {
                        "runtime_state_path": str(runtime_state_path),
                        "artifact_path": str(output_path),
                        "executes_graph_requests": False,
                        "executes_graph_writes": False,
                    },
                    "errors": [str(exc)],
                }
                print_json(payload) if args.format == "json" else print(f"STATUS: {payload['status']}")
                return 2
            if args.format == "json":
                print_json(bootstrap.readiness)
            else:
                print(f"STATUS: {bootstrap.readiness['status']}")
                print(f"Artifact: {output_path}")
            return 0 if bootstrap.readiness["status"] == "PASSED" else 2

        if args.teams_sharepoint_command == "release-gate-run":
            payload, return_code = _run_m365_release_gate(repo_root, args)
            if args.format == "json":
                print_json(payload)
            else:
                _print_m365_release_gate_run(payload)
            return return_code

        if args.teams_sharepoint_command == "release-gate-retention-list":
            payload = _list_m365_release_gate_retention(repo_root, args)
            if args.format == "json":
                print_json(payload)
            else:
                _print_m365_release_gate_retention_list(payload)
            return 0 if payload["status"] == "PASSED" else 1

        if args.teams_sharepoint_command == "release-readiness":
            payload = _build_m365_release_readiness(repo_root, args)
            if args.release_gate_readiness_output:
                output_path = _resolve_m365_release_gate_path(
                    repo_root,
                    args.release_gate_readiness_output,
                    DEFAULT_RELEASE_READINESS_OUTPUT,
                )
                payload["summary"]["json_path"] = str(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            if args.format == "json":
                print_json(payload)
            else:
                _print_m365_release_readiness(payload)
            if payload["status"] == "PASSED":
                return 0
            return 2 if payload["status"] == "BLOCKED" else 1

        if args.teams_sharepoint_command == "release-gate-post-run-report":
            payload = _write_m365_release_gate_post_run_report(repo_root, args)
            if args.format == "json":
                print_json(payload)
            else:
                _print_m365_release_gate_post_run_report(payload)
            return _m365_release_gate_post_run_report_return_code(payload)

        if args.teams_sharepoint_command == "release-gate-post-run-report-index":
            payload = _list_m365_release_gate_post_run_reports(repo_root, args)
            if args.format == "json":
                print_json(payload)
            else:
                _print_m365_release_gate_post_run_report_index(payload)
            return 0 if payload["status"] == "PASSED" else 1

        if args.teams_sharepoint_command == "release-gate-post-run-report-index-artifact":
            payload = _write_m365_release_gate_post_run_report_index_artifact(repo_root, args)
            if args.format == "json":
                print_json(payload)
            else:
                _print_m365_release_gate_post_run_report_index_artifact(payload)
            return 0 if payload["status"] == "PASSED" else 2

        if args.teams_sharepoint_command == "release-gate-retention-audit-pack":
            payload = _write_m365_release_gate_retention_audit_pack(repo_root, args)
            if args.format == "json":
                print_json(payload)
            else:
                _print_m365_release_gate_retention_audit_pack(payload)
            return 0 if payload["status"] == "PASSED" else 2

        if args.teams_sharepoint_command == "release-gate-retention-compare":
            payload = _compare_m365_release_gate_retention(repo_root, args)
            if args.format == "json":
                print_json(payload)
            else:
                _print_m365_release_gate_retention_compare(payload)
            return 0 if payload["status"] == "PASSED" else 2

        if args.teams_sharepoint_command == "release-gate-retention-compare-artifact":
            payload = _write_m365_release_gate_retention_compare_artifact(repo_root, args)
            if args.format == "json":
                print_json(payload)
            else:
                _print_m365_release_gate_retention_compare_artifact(payload)
            return 0 if payload["status"] == "PASSED" else 2

        if args.teams_sharepoint_command == "release-gate-retention-compare-index":
            payload = _list_m365_release_gate_retention_compare_artifacts(repo_root, args)
            if args.format == "json":
                print_json(payload)
            else:
                _print_m365_release_gate_retention_compare_index(payload)
            return 0 if payload["status"] == "PASSED" else 1

        if args.teams_sharepoint_command == "release-gate-retention-compare-index-artifact":
            payload = _write_m365_release_gate_retention_compare_index_artifact(repo_root, args)
            if args.format == "json":
                print_json(payload)
            else:
                _print_m365_release_gate_retention_compare_index_artifact(payload)
            return 0 if payload["status"] == "PASSED" else 2

        if args.teams_sharepoint_command == "release-gate-evidence":
            output_path = _resolve_m365_release_gate_path(
                repo_root,
                args.release_gate_evidence_output,
                DEFAULT_EVIDENCE_OUTPUT,
            )
            json_output_path = _resolve_m365_release_gate_path(
                repo_root,
                args.release_gate_evidence_json_output,
                DEFAULT_EVIDENCE_JSON_OUTPUT,
            )
            artifact_index_path = _resolve_m365_release_gate_path(
                repo_root,
                args.release_gate_artifact_index_output,
                DEFAULT_ARTIFACT_INDEX_OUTPUT,
            )
            evidence = build_release_gate_evidence(
                repo_root=repo_root,
                mcp_inventory_artifact=args.release_gate_inventory_artifact,
                matter_access_artifact=args.release_gate_matter_access_artifact,
                matter_access_apply_readiness_artifact=args.release_gate_matter_access_apply_readiness_artifact,
                matter_access_apply_request_artifact=args.release_gate_matter_access_apply_request_artifact,
                mcp_suite_artifact=args.release_gate_suite_artifact,
                mcp_leftover_artifact=args.release_gate_leftover_artifact,
                runtime_smoke_artifact=args.release_gate_runtime_smoke_artifact,
                runtime_certificate_expiry_artifact=args.release_gate_runtime_certificate_expiry_artifact,
                runtime_env_bootstrap_artifact=args.release_gate_runtime_env_bootstrap_artifact,
                runtime_metadata_artifact=args.release_gate_runtime_metadata_artifact,
                expected_workspace_id=args.mcp_smoke_workspace_id,
                expected_correlation_id=args.mcp_smoke_correlation_id,
                require_runtime_artifacts=args.release_gate_require_runtime_artifacts,
            )
            evidence["summary"]["report_path"] = str(output_path)
            evidence["summary"]["json_path"] = str(json_output_path)
            evidence["summary"]["artifact_index_path"] = str(artifact_index_path)
            attach_release_gate_artifact_index(evidence)
            write_release_gate_evidence_report(evidence, output_path)
            write_release_gate_evidence_json(evidence, json_output_path)
            write_release_gate_artifact_index(evidence["artifact_index"], artifact_index_path)
            if args.format == "json":
                print_json(evidence)
            else:
                _print_release_gate_evidence(evidence)
            if evidence["status"] == "PASSED":
                return 0
            return 2 if evidence["status"] == "BLOCKED" else 1

        script_args = [args.teams_sharepoint_command]
        if args.schema:
            script_args.extend(["--schema", str(args.schema)])
        if args.bpmn_viewer_config:
            script_args.extend(["--bpmn-viewer-config", str(args.bpmn_viewer_config)])
        if args.matter_access_contract:
            script_args.extend(["--matter-access-contract", str(args.matter_access_contract)])
        if args.bpmn_viewer_runtime_readiness:
            script_args.extend(["--bpmn-viewer-runtime-readiness", str(args.bpmn_viewer_runtime_readiness)])
        if args.spfx_bpmn_viewer_skeleton:
            script_args.extend(["--spfx-bpmn-viewer-skeleton", str(args.spfx_bpmn_viewer_skeleton)])
        if args.privileged_config:
            script_args.extend(["--privileged-config", str(args.privileged_config)])
        if args.provisioned_state:
            script_args.extend(["--provisioned-state", str(args.provisioned_state)])
        if args.privileged_applied_state:
            script_args.extend(["--privileged-applied-state", str(args.privileged_applied_state)])
        if args.mcp_contract:
            script_args.extend(["--mcp-contract", str(args.mcp_contract)])
        if args.runtime_smoke_output:
            script_args.extend(["--runtime-smoke-output", str(args.runtime_smoke_output)])
        if args.runtime_smoke_state:
            script_args.extend(["--runtime-smoke-state", str(args.runtime_smoke_state)])
        if args.runtime_metadata_output:
            script_args.extend(["--runtime-metadata-output", str(args.runtime_metadata_output)])
        if args.runtime_metadata_state:
            script_args.extend(["--runtime-metadata-state", str(args.runtime_metadata_state)])
        if args.runtime_certificate_expiry_output:
            script_args.extend(["--runtime-certificate-expiry-output", str(args.runtime_certificate_expiry_output)])
        script_args.extend(["--runtime-certificate-warning-days", str(args.runtime_certificate_warning_days)])
        script_args.extend(["--runtime-certificate-critical-days", str(args.runtime_certificate_critical_days)])
        if args.mcp_live_read:
            script_args.append("--mcp-live-read")
        if args.mcp_smoke_tool:
            script_args.extend(["--mcp-smoke-tool", args.mcp_smoke_tool])
        if args.mcp_smoke_workspace_id:
            script_args.extend(["--mcp-smoke-workspace-id", args.mcp_smoke_workspace_id])
        if args.mcp_smoke_case_id:
            script_args.extend(["--mcp-smoke-case-id", args.mcp_smoke_case_id])
        if args.mcp_smoke_correlation_id:
            script_args.extend(["--mcp-smoke-correlation-id", args.mcp_smoke_correlation_id])
        if args.mcp_smoke_output:
            script_args.extend(["--mcp-smoke-output", str(args.mcp_smoke_output)])
        if args.mcp_inventory_smoke_output:
            script_args.extend(["--mcp-inventory-smoke-output", str(args.mcp_inventory_smoke_output)])
        if args.matter_access_smoke_output:
            script_args.extend(["--matter-access-smoke-output", str(args.matter_access_smoke_output)])
        if args.matter_access_apply_readiness_output:
            script_args.extend(
                ["--matter-access-apply-readiness-output", str(args.matter_access_apply_readiness_output)]
            )
        if args.matter_access_apply_request_output:
            script_args.extend(["--matter-access-apply-request-output", str(args.matter_access_apply_request_output)])
        if args.matter_access_grant_id:
            script_args.extend(["--matter-access-grant-id", args.matter_access_grant_id])
        if args.matter_access_from_user:
            script_args.extend(["--matter-access-from-user", args.matter_access_from_user])
        if args.matter_access_to_user:
            script_args.extend(["--matter-access-to-user", args.matter_access_to_user])
        if args.matter_access_granted_role:
            script_args.extend(["--matter-access-granted-role", args.matter_access_granted_role])
        if args.matter_access_reason:
            script_args.extend(["--matter-access-reason", args.matter_access_reason])
        if args.matter_access_valid_from:
            script_args.extend(["--matter-access-valid-from", args.matter_access_valid_from])
        if args.matter_access_valid_until:
            script_args.extend(["--matter-access-valid-until", args.matter_access_valid_until])
        if args.matter_access_approved_by:
            script_args.extend(["--matter-access-approved-by", args.matter_access_approved_by])
        if args.matter_access_status:
            script_args.extend(["--matter-access-status", args.matter_access_status])
        if args.mcp_positive_smoke_output:
            script_args.extend(["--mcp-positive-smoke-output", str(args.mcp_positive_smoke_output)])
        if args.mcp_cleanup_output:
            script_args.extend(["--mcp-cleanup-output", str(args.mcp_cleanup_output)])
        if args.mcp_leftover_output:
            script_args.extend(["--mcp-leftover-output", str(args.mcp_leftover_output)])
        if args.mcp_leftover_dry_run:
            script_args.append("--mcp-leftover-dry-run")
        if args.mcp_suite_output:
            script_args.extend(["--mcp-suite-output", str(args.mcp_suite_output)])
        if args.mcp_suite_cleanup:
            script_args.append("--mcp-suite-cleanup")
        if args.owner_approved:
            script_args.append("--owner-approved")
        if args.format == "json":
            script_args.append("--json")
        if args.teams_sharepoint_command == "mcp-stdio":
            result = subprocess.run(
                [sys.executable, str(repo_root / "scripts" / "provision_teams_sharepoint_graph.py"), *script_args],
                cwd=repo_root,
                check=False,
            )
            return result.returncode
        result = subprocess.run(
            [sys.executable, str(repo_root / "scripts" / "provision_teams_sharepoint_graph.py"), *script_args],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip())
        return result.returncode

    raise AssertionError(f"Unknown Microsoft 365 command: {args.m365_command}")


def _run_m365_release_gate(repo_root: Path, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    if not args.owner_approved:
        return (
            {
                "status": "BLOCKED",
                "errors": ["release-gate-run requires --owner-approved"],
                "summary": {
                    "workspace_id": args.mcp_smoke_workspace_id or "notary_team_01",
                    "correlation_id": args.mcp_smoke_correlation_id,
                    "owner_gate": "m365_runtime_release_gate",
                },
                "steps": [],
            },
            2,
        )

    args = _m365_release_gate_run_effective_args(args)
    workspace_id = args.mcp_smoke_workspace_id or "notary_team_01"
    correlation_id = args.mcp_smoke_correlation_id or "m365-runtime-release-gate"
    runtime_smoke_output = _resolve_m365_release_gate_path(
        repo_root,
        args.runtime_smoke_output,
        DEFAULT_RUNTIME_SMOKE_OUTPUT,
    )
    runtime_certificate_expiry_output = _resolve_m365_release_gate_path(
        repo_root,
        args.runtime_certificate_expiry_output,
        DEFAULT_RUNTIME_CERTIFICATE_EXPIRY_MONITOR_OUTPUT,
    )
    runtime_env_bootstrap_output = _resolve_m365_release_gate_path(
        repo_root,
        args.runtime_env_bootstrap_output,
        DEFAULT_RUNTIME_ENV_BOOTSTRAP_ARTIFACT,
    )
    runtime_metadata_output = _resolve_m365_release_gate_path(
        repo_root,
        args.runtime_metadata_output,
        DEFAULT_RUNTIME_METADATA_OUTPUT,
    )
    mcp_suite_output = _resolve_m365_release_gate_path(
        repo_root,
        args.mcp_suite_output,
        DEFAULT_MCP_SMOKE_SUITE_OUTPUT,
    )
    mcp_leftover_output = _resolve_m365_release_gate_path(
        repo_root,
        args.mcp_leftover_output,
        DEFAULT_MCP_SMOKE_LEFTOVER_CLEANUP_OUTPUT,
    )
    release_gate_inventory_artifact = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_inventory_artifact,
        DEFAULT_RELEASE_GATE_INVENTORY_ARTIFACT,
    )
    release_gate_matter_access_artifact = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_matter_access_artifact,
        DEFAULT_RELEASE_GATE_MATTER_ACCESS_ARTIFACT,
    )
    release_gate_matter_access_apply_readiness_artifact = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_matter_access_apply_readiness_artifact,
        DEFAULT_RELEASE_GATE_MATTER_ACCESS_APPLY_READINESS_ARTIFACT,
    )
    release_gate_matter_access_apply_request_artifact = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_matter_access_apply_request_artifact,
        DEFAULT_RELEASE_GATE_MATTER_ACCESS_APPLY_REQUEST_ARTIFACT,
    )
    evidence_output = _resolve_m365_release_gate_path(repo_root, args.release_gate_evidence_output, DEFAULT_EVIDENCE_OUTPUT)
    evidence_json_output = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_evidence_json_output,
        DEFAULT_EVIDENCE_JSON_OUTPUT,
    )
    artifact_index_output = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_artifact_index_output,
        DEFAULT_ARTIFACT_INDEX_OUTPUT,
    )
    release_gate_run_artifact_dir = _resolve_m365_release_gate_run_artifact_dir(
        repo_root,
        args.release_gate_run_artifact_dir,
        correlation_id,
    )

    steps = [
        (
            "mcp_inventory_smoke",
            [
                "m365",
                "teams-sharepoint",
                "mcp-inventory-smoke",
                "--mcp-smoke-workspace-id",
                workspace_id,
                "--mcp-smoke-correlation-id",
                correlation_id,
                "--mcp-inventory-smoke-output",
                str(release_gate_inventory_artifact),
                "--format",
                "json",
            ],
        ),
        (
            "matter_access_delegation_smoke",
            [
                "m365",
                "teams-sharepoint",
                "matter-access-smoke",
                "--mcp-smoke-workspace-id",
                workspace_id,
                "--mcp-smoke-correlation-id",
                correlation_id,
                "--matter-access-smoke-output",
                str(release_gate_matter_access_artifact),
                "--format",
                "json",
            ],
        ),
        (
            "matter_access_apply_readiness",
            [
                "m365",
                "teams-sharepoint",
                "matter-access-apply-readiness",
                "--mcp-smoke-workspace-id",
                workspace_id,
                "--mcp-smoke-correlation-id",
                correlation_id,
                "--matter-access-apply-readiness-output",
                str(release_gate_matter_access_apply_readiness_artifact),
                "--format",
                "json",
            ],
        ),
        (
            "matter_access_apply_request_plan",
            [
                "m365",
                "teams-sharepoint",
                "matter-access-apply-request-plan",
                "--mcp-smoke-workspace-id",
                workspace_id,
                "--mcp-smoke-correlation-id",
                correlation_id,
                "--matter-access-apply-request-output",
                str(release_gate_matter_access_apply_request_artifact),
                "--format",
                "json",
            ],
        ),
        (
            "runtime_certificate_expiry",
            [
                "m365",
                "teams-sharepoint",
                "runtime-certificate-expiry-monitor",
                "--runtime-certificate-expiry-output",
                str(runtime_certificate_expiry_output),
                "--runtime-certificate-warning-days",
                str(args.runtime_certificate_warning_days),
                "--runtime-certificate-critical-days",
                str(args.runtime_certificate_critical_days),
                "--format",
                "json",
            ],
        ),
        (
            "runtime_smoke",
            [
                "m365",
                "teams-sharepoint",
                "runtime-smoke",
                "--owner-approved",
                "--runtime-smoke-output",
                str(runtime_smoke_output),
                "--format",
                "json",
            ],
        ),
        (
            "runtime_metadata",
            [
                "m365",
                "teams-sharepoint",
                "runtime-metadata",
                "--owner-approved",
                "--runtime-metadata-output",
                str(runtime_metadata_output),
                "--format",
                "json",
            ],
        ),
        (
            "mcp_smoke_suite",
            [
                "m365",
                "teams-sharepoint",
                "mcp-smoke-suite",
                "--owner-approved",
                "--mcp-suite-cleanup",
                "--mcp-smoke-workspace-id",
                workspace_id,
                "--mcp-smoke-correlation-id",
                correlation_id,
                "--mcp-suite-output",
                str(mcp_suite_output),
                "--format",
                "json",
            ],
        ),
        (
            "mcp_leftover_dry_run",
            [
                "m365",
                "teams-sharepoint",
                "mcp-smoke-leftover-cleanup",
                "--owner-approved",
                "--mcp-leftover-dry-run",
                "--mcp-smoke-workspace-id",
                workspace_id,
                "--mcp-smoke-correlation-id",
                correlation_id,
                "--mcp-leftover-output",
                str(mcp_leftover_output),
                "--format",
                "json",
            ],
        ),
        (
            "release_gate_evidence",
            [
                "m365",
                "teams-sharepoint",
                "release-gate-evidence",
                "--mcp-smoke-workspace-id",
                workspace_id,
                "--mcp-smoke-correlation-id",
                correlation_id,
                "--release-gate-require-runtime-artifacts",
                "--release-gate-inventory-artifact",
                str(release_gate_inventory_artifact),
                "--release-gate-matter-access-artifact",
                str(release_gate_matter_access_artifact),
                "--release-gate-matter-access-apply-readiness-artifact",
                str(release_gate_matter_access_apply_readiness_artifact),
                "--release-gate-matter-access-apply-request-artifact",
                str(release_gate_matter_access_apply_request_artifact),
                "--release-gate-runtime-certificate-expiry-artifact",
                str(runtime_certificate_expiry_output),
                "--release-gate-runtime-env-bootstrap-artifact",
                str(runtime_env_bootstrap_output),
                "--release-gate-runtime-smoke-artifact",
                str(runtime_smoke_output),
                "--release-gate-runtime-metadata-artifact",
                str(runtime_metadata_output),
                "--release-gate-suite-artifact",
                str(mcp_suite_output),
                "--release-gate-leftover-artifact",
                str(mcp_leftover_output),
                "--release-gate-evidence-output",
                str(evidence_output),
                "--release-gate-evidence-json-output",
                str(evidence_json_output),
                "--release-gate-artifact-index-output",
                str(artifact_index_output),
                "--format",
                "json",
            ],
        ),
    ]
    if args.schema:
        for command in _m365_release_gate_step_commands(
            steps,
            {
                "matter_access_delegation_smoke",
                "matter_access_apply_readiness",
                "matter_access_apply_request_plan",
                "runtime_smoke",
                "runtime_metadata",
            },
        ):
            command[3:3] = ["--schema", str(args.schema)]
    if args.matter_access_contract:
        for command in _m365_release_gate_step_commands(
            steps,
            {"matter_access_delegation_smoke", "matter_access_apply_readiness", "matter_access_apply_request_plan"},
        ):
            command[3:3] = ["--matter-access-contract", str(args.matter_access_contract)]
    if args.runtime_smoke_state:
        _m365_release_gate_step_command(steps, "runtime_certificate_expiry")[3:3] = [
            "--runtime-smoke-state",
            str(args.runtime_smoke_state),
        ]
    if args.runtime_metadata_state:
        _m365_release_gate_step_command(steps, "runtime_certificate_expiry")[3:3] = [
            "--runtime-metadata-state",
            str(args.runtime_metadata_state),
        ]
    if args.provisioned_state:
        for command in _m365_release_gate_step_commands(
            steps,
            {
                "mcp_inventory_smoke",
                "matter_access_apply_request_plan",
                "runtime_smoke",
                "runtime_metadata",
                "mcp_smoke_suite",
                "mcp_leftover_dry_run",
            },
        ):
            command[3:3] = ["--provisioned-state", str(args.provisioned_state)]
    if args.mcp_contract:
        for command in _m365_release_gate_step_commands(
            steps,
            {
                "mcp_inventory_smoke",
                "matter_access_apply_readiness",
                "matter_access_apply_request_plan",
                "mcp_smoke_suite",
                "mcp_leftover_dry_run",
            },
        ):
            command[3:3] = ["--mcp-contract", str(args.mcp_contract)]
    if args.mcp_smoke_case_id:
        _m365_release_gate_step_command(steps, "mcp_smoke_suite")[3:3] = [
            "--mcp-smoke-case-id",
            args.mcp_smoke_case_id,
        ]

    runtime_env_overlay, runtime_env_summary = _m365_runtime_env_overlay(
        repo_root,
        args,
        output_path=runtime_env_bootstrap_output,
    )
    if runtime_env_summary["status"] != "PASSED":
        return (
            {
                "status": "FAILED",
                "summary": {
                    "workspace_id": workspace_id,
                    "correlation_id": correlation_id,
                    "failed_step": "runtime_env_bootstrap",
                    "steps_completed": 0,
                    "runtime_env_bootstrap_status": runtime_env_summary["status"],
                    "runtime_env_bootstrap_artifact": runtime_env_summary["artifact_path"],
                    "runtime_env_overlay_variable_names": runtime_env_summary["env_overlay_variable_names"],
                },
                "steps": [],
                "errors": runtime_env_summary["errors"],
            },
            2,
        )
    step_results: list[dict[str, Any]] = []
    for step_id, command in steps:
        env_overlay = runtime_env_overlay if step_id in _M365_RELEASE_GATE_RUNTIME_ENV_STEPS else None
        result = _run_nac_json_step(repo_root, command, env_overlay=env_overlay)
        step_results.append(
            {
                "step": step_id,
                "return_code": result.returncode,
                "status": _payload_status(result.stdout),
                "command": "python3 scripts/nac.py " + " ".join(command),
            }
        )
        if result.returncode != 0:
            return (
                {
                    "status": "FAILED",
                    "summary": {
                        "workspace_id": workspace_id,
                        "correlation_id": correlation_id,
                        "failed_step": step_id,
                        "steps_completed": len(step_results) - 1,
                        "runtime_env_bootstrap_status": runtime_env_summary["status"],
                        "runtime_env_bootstrap_artifact": runtime_env_summary["artifact_path"],
                        "runtime_env_overlay_variable_names": runtime_env_summary["env_overlay_variable_names"],
                    },
                    "steps": step_results,
                    "errors": [_step_error_message(result)],
                },
                result.returncode,
            )

    retention_index = _retain_m365_release_gate_artifacts(
        artifact_dir=release_gate_run_artifact_dir,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        status="PASSED",
        artifacts={
            "runtime_certificate_expiry": runtime_certificate_expiry_output,
            "runtime_env_bootstrap": runtime_env_bootstrap_output,
            "runtime_smoke": runtime_smoke_output,
            "runtime_metadata": runtime_metadata_output,
            "mcp_inventory_smoke": release_gate_inventory_artifact,
            "matter_access_delegation_smoke": release_gate_matter_access_artifact,
            "matter_access_apply_readiness": release_gate_matter_access_apply_readiness_artifact,
            "matter_access_apply_request_plan": release_gate_matter_access_apply_request_artifact,
            "mcp_smoke_suite": mcp_suite_output,
            "mcp_leftover_dry_run": mcp_leftover_output,
            "release_gate_evidence_report": evidence_output,
            "release_gate_evidence_json": evidence_json_output,
            "release_gate_artifact_index": artifact_index_output,
        },
    )
    _refresh_m365_release_gate_evidence_with_retention(
        evidence_output=evidence_output,
        evidence_json_output=evidence_json_output,
        artifact_index_output=artifact_index_output,
        retention_index=retention_index,
    )
    retention_index = _retain_m365_release_gate_artifacts(
        artifact_dir=release_gate_run_artifact_dir,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        status="PASSED",
        artifacts={
            "runtime_certificate_expiry": runtime_certificate_expiry_output,
            "runtime_env_bootstrap": runtime_env_bootstrap_output,
            "runtime_smoke": runtime_smoke_output,
            "runtime_metadata": runtime_metadata_output,
            "mcp_inventory_smoke": release_gate_inventory_artifact,
            "matter_access_delegation_smoke": release_gate_matter_access_artifact,
            "matter_access_apply_readiness": release_gate_matter_access_apply_readiness_artifact,
            "matter_access_apply_request_plan": release_gate_matter_access_apply_request_artifact,
            "mcp_smoke_suite": mcp_suite_output,
            "mcp_leftover_dry_run": mcp_leftover_output,
            "release_gate_evidence_report": evidence_output,
            "release_gate_evidence_json": evidence_json_output,
            "release_gate_artifact_index": artifact_index_output,
        },
    )
    post_run_baseline_reference = _m365_release_gate_run_post_run_baseline_reference(
        repo_root,
        args,
        correlation_id=correlation_id,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
    )
    audit_pack_payload: dict[str, Any] | None = None
    if args.release_gate_write_audit_pack:
        audit_pack_payload = _write_m365_release_gate_run_audit_pack(
            repo_root,
            args,
            correlation_id=correlation_id,
            release_gate_run_artifact_dir=release_gate_run_artifact_dir,
            baseline_reference=post_run_baseline_reference,
        )
        step_results.append(
            {
                "step": "release_gate_audit_pack",
                "return_code": 0 if audit_pack_payload["status"] == "PASSED" else 2,
                "status": audit_pack_payload["status"],
                "command": _m365_release_gate_run_audit_pack_command(
                    args,
                    correlation_id=correlation_id,
                    release_gate_run_artifact_dir=release_gate_run_artifact_dir,
                    baseline_reference=post_run_baseline_reference,
                ),
            }
        )
        if audit_pack_payload["status"] != "PASSED":
            return (
                {
                    "status": "FAILED",
                    "summary": {
                        "workspace_id": workspace_id,
                        "correlation_id": correlation_id,
                        "failed_step": "release_gate_audit_pack",
                        "steps_completed": len(step_results) - 1,
                        "runtime_env_bootstrap_status": runtime_env_summary["status"],
                        "runtime_env_bootstrap_artifact": runtime_env_summary["artifact_path"],
                        "runtime_env_overlay_variable_names": runtime_env_summary["env_overlay_variable_names"],
                        "release_gate_run_artifact_dir": str(release_gate_run_artifact_dir),
                        "release_gate_retention_index": retention_index["index_path"],
                        "release_gate_audit_pack_status": audit_pack_payload["status"],
                        "release_gate_audit_pack_dir": audit_pack_payload.get("summary", {}).get("pack_dir"),
                        "release_gate_audit_pack_manifest": audit_pack_payload.get("summary", {}).get("json_path"),
                    },
                    "steps": step_results,
                    "errors": audit_pack_payload.get("errors", []),
                },
                2,
            )

    readiness_payload: dict[str, Any] | None = None
    if args.release_gate_write_readiness:
        readiness_payload = _write_m365_release_gate_run_readiness(
            repo_root,
            args,
            correlation_id=correlation_id,
            release_gate_run_artifact_dir=release_gate_run_artifact_dir,
            baseline_reference=post_run_baseline_reference,
        )
        readiness_return_code = _m365_release_readiness_return_code(readiness_payload)
        step_results.append(
            {
                "step": "release_gate_readiness",
                "return_code": readiness_return_code,
                "status": readiness_payload["status"],
                "command": _m365_release_gate_run_readiness_command(
                    repo_root,
                    args,
                    correlation_id=correlation_id,
                    release_gate_run_artifact_dir=release_gate_run_artifact_dir,
                    baseline_reference=post_run_baseline_reference,
                ),
            }
        )
        if readiness_payload["status"] != "PASSED":
            readiness_summary = readiness_payload.get("summary", {})
            return (
                {
                    "status": "BLOCKED" if readiness_payload["status"] == "BLOCKED" else "FAILED",
                    "summary": {
                        "workspace_id": workspace_id,
                        "correlation_id": correlation_id,
                        "failed_step": "release_gate_readiness",
                        "steps_completed": len(step_results) - 1,
                        "runtime_env_bootstrap_status": runtime_env_summary["status"],
                        "runtime_env_bootstrap_artifact": runtime_env_summary["artifact_path"],
                        "runtime_env_overlay_variable_names": runtime_env_summary["env_overlay_variable_names"],
                        "release_gate_run_artifact_dir": str(release_gate_run_artifact_dir),
                        "release_gate_retention_index": retention_index["index_path"],
                        "release_gate_audit_pack_status": audit_pack_payload["status"] if audit_pack_payload else None,
                        "release_gate_audit_pack_dir": (
                            audit_pack_payload.get("summary", {}).get("pack_dir") if audit_pack_payload else None
                        ),
                        "release_gate_audit_pack_manifest": (
                            audit_pack_payload.get("summary", {}).get("json_path") if audit_pack_payload else None
                        ),
                        "release_gate_readiness_status": readiness_payload["status"],
                        "release_gate_readiness": readiness_summary.get("mvp_release_readiness"),
                        "release_gate_readiness_artifact": readiness_summary.get("json_path"),
                        "release_gate_readiness_require_audit_pack": args.release_gate_readiness_require_audit_pack,
                    },
                    "steps": step_results,
                    "errors": readiness_payload.get("errors", []),
                },
                readiness_return_code,
            )

    post_run_report_payload: dict[str, Any] | None = None
    if args.release_gate_write_post_run_report:
        post_run_report_payload = _write_m365_release_gate_run_post_run_report(
            repo_root,
            args,
            correlation_id=correlation_id,
            release_gate_run_artifact_dir=release_gate_run_artifact_dir,
            baseline_reference=post_run_baseline_reference,
        )
        post_run_report_return_code = _m365_release_gate_post_run_report_return_code(post_run_report_payload)
        step_results.append(
            {
                "step": "release_gate_post_run_report",
                "return_code": post_run_report_return_code,
                "status": post_run_report_payload["status"],
                "command": _m365_release_gate_run_post_run_report_command(
                    repo_root,
                    args,
                    correlation_id=correlation_id,
                    release_gate_run_artifact_dir=release_gate_run_artifact_dir,
                    baseline_reference=post_run_baseline_reference,
                ),
            }
        )
        if post_run_report_payload["status"] != "PASSED":
            post_run_report_summary = post_run_report_payload.get("summary", {})
            return (
                {
                    "status": "BLOCKED" if post_run_report_payload["status"] == "BLOCKED" else "FAILED",
                    "summary": {
                        "workspace_id": workspace_id,
                        "correlation_id": correlation_id,
                        "failed_step": "release_gate_post_run_report",
                        "steps_completed": len(step_results) - 1,
                        "runtime_env_bootstrap_status": runtime_env_summary["status"],
                        "runtime_env_bootstrap_artifact": runtime_env_summary["artifact_path"],
                        "runtime_env_overlay_variable_names": runtime_env_summary["env_overlay_variable_names"],
                        "release_gate_run_artifact_dir": str(release_gate_run_artifact_dir),
                        "release_gate_retention_index": retention_index["index_path"],
                        "release_gate_audit_pack_status": audit_pack_payload["status"] if audit_pack_payload else None,
                        "release_gate_audit_pack_dir": (
                            audit_pack_payload.get("summary", {}).get("pack_dir") if audit_pack_payload else None
                        ),
                        "release_gate_audit_pack_manifest": (
                            audit_pack_payload.get("summary", {}).get("json_path") if audit_pack_payload else None
                        ),
                        "release_gate_readiness_status": readiness_payload["status"] if readiness_payload else None,
                        "release_gate_readiness": (
                            readiness_payload.get("summary", {}).get("mvp_release_readiness")
                            if readiness_payload
                            else None
                        ),
                        "release_gate_post_run_report_status": post_run_report_payload["status"],
                        "release_gate_post_run_report": post_run_report_summary.get("report_path"),
                        "release_gate_post_run_report_json": post_run_report_summary.get("json_path"),
                        "release_gate_github_comment_draft": post_run_report_summary.get("github_comment_path"),
                    },
                    "steps": step_results,
                    "errors": post_run_report_payload.get("errors", []),
                },
                post_run_report_return_code,
            )

    post_run_report_index_payload: dict[str, Any] | None = None
    if args.release_gate_write_post_run_report_index:
        post_run_report_index_payload = _write_m365_release_gate_run_post_run_report_index(
            repo_root,
            args,
            release_gate_run_artifact_dir=release_gate_run_artifact_dir,
        )
        post_run_report_index_return_code = 0 if post_run_report_index_payload["status"] == "PASSED" else 2
        step_results.append(
            {
                "step": "release_gate_post_run_report_index",
                "return_code": post_run_report_index_return_code,
                "status": post_run_report_index_payload["status"],
                "command": _m365_release_gate_run_post_run_report_index_command(
                    repo_root,
                    args,
                    release_gate_run_artifact_dir=release_gate_run_artifact_dir,
                ),
            }
        )
        if post_run_report_index_payload["status"] != "PASSED":
            post_run_report_index_summary = post_run_report_index_payload.get("summary", {})
            post_run_report_summary = post_run_report_payload.get("summary", {}) if post_run_report_payload else {}
            return (
                {
                    "status": "FAILED",
                    "summary": {
                        "workspace_id": workspace_id,
                        "correlation_id": correlation_id,
                        "failed_step": "release_gate_post_run_report_index",
                        "steps_completed": len(step_results) - 1,
                        "runtime_env_bootstrap_status": runtime_env_summary["status"],
                        "runtime_env_bootstrap_artifact": runtime_env_summary["artifact_path"],
                        "runtime_env_overlay_variable_names": runtime_env_summary["env_overlay_variable_names"],
                        "release_gate_run_artifact_dir": str(release_gate_run_artifact_dir),
                        "release_gate_retention_index": retention_index["index_path"],
                        "release_gate_audit_pack_status": audit_pack_payload["status"] if audit_pack_payload else None,
                        "release_gate_audit_pack_dir": (
                            audit_pack_payload.get("summary", {}).get("pack_dir") if audit_pack_payload else None
                        ),
                        "release_gate_audit_pack_manifest": (
                            audit_pack_payload.get("summary", {}).get("json_path") if audit_pack_payload else None
                        ),
                        "release_gate_readiness_status": readiness_payload["status"] if readiness_payload else None,
                        "release_gate_readiness": (
                            readiness_payload.get("summary", {}).get("mvp_release_readiness")
                            if readiness_payload
                            else None
                        ),
                        "release_gate_post_run_report_status": (
                            post_run_report_payload["status"] if post_run_report_payload else None
                        ),
                        "release_gate_post_run_report": post_run_report_summary.get("report_path"),
                        "release_gate_post_run_report_json": post_run_report_summary.get("json_path"),
                        "release_gate_github_comment_draft": post_run_report_summary.get("github_comment_path"),
                        "release_gate_post_run_report_index_status": post_run_report_index_payload["status"],
                        "release_gate_post_run_report_index": post_run_report_index_summary.get("report_path"),
                        "release_gate_post_run_report_index_json": post_run_report_index_summary.get("json_path"),
                    },
                    "steps": step_results,
                    "errors": post_run_report_index_payload.get("errors", []),
                },
                post_run_report_index_return_code,
            )

    readiness_summary = readiness_payload.get("summary", {}) if readiness_payload else {}
    post_run_report_summary = post_run_report_payload.get("summary", {}) if post_run_report_payload else {}
    post_run_report_index_summary = (
        post_run_report_index_payload.get("summary", {}) if post_run_report_index_payload else {}
    )
    return (
        {
            "status": "PASSED",
            "summary": {
                "workspace_id": workspace_id,
                "correlation_id": correlation_id,
                "steps_completed": len(step_results),
                "runtime_env_bootstrap_status": runtime_env_summary["status"],
                "runtime_env_bootstrap_artifact": runtime_env_summary["artifact_path"],
                "runtime_env_overlay_variable_names": runtime_env_summary["env_overlay_variable_names"],
                "evidence_output": str(evidence_output),
                "evidence_json_output": str(evidence_json_output),
                "artifact_index_output": str(artifact_index_output),
                "release_gate_run_artifact_dir": str(release_gate_run_artifact_dir),
                "release_gate_retention_index": retention_index["index_path"],
                "retained_artifact_count": retention_index["copied_artifact_count"],
                "release_gate_audit_pack_status": audit_pack_payload["status"] if audit_pack_payload else None,
                "release_gate_audit_pack_dir": (
                    audit_pack_payload.get("summary", {}).get("pack_dir") if audit_pack_payload else None
                ),
                "release_gate_audit_pack_manifest": (
                    audit_pack_payload.get("summary", {}).get("json_path") if audit_pack_payload else None
                ),
                "release_gate_readiness_status": readiness_payload["status"] if readiness_payload else None,
                "release_gate_readiness": readiness_summary.get("mvp_release_readiness"),
                "release_gate_readiness_artifact": readiness_summary.get("json_path"),
                "release_gate_readiness_require_audit_pack": (
                    args.release_gate_readiness_require_audit_pack if readiness_payload else False
                ),
                "release_gate_post_run_report_status": (
                    post_run_report_payload["status"] if post_run_report_payload else None
                ),
                "release_gate_post_run_report": post_run_report_summary.get("report_path"),
                "release_gate_post_run_report_json": post_run_report_summary.get("json_path"),
                "release_gate_github_comment_draft": post_run_report_summary.get("github_comment_path"),
                "release_gate_post_run_report_index_status": (
                    post_run_report_index_payload["status"] if post_run_report_index_payload else None
                ),
                "release_gate_post_run_report_index": post_run_report_index_summary.get("report_path"),
                "release_gate_post_run_report_index_json": post_run_report_index_summary.get("json_path"),
            },
            "steps": step_results,
            "errors": [],
        },
        0,
    )


def _m365_release_gate_run_effective_args(args: argparse.Namespace) -> argparse.Namespace:
    if not args.release_gate_write_post_run_report and not args.release_gate_write_post_run_report_index:
        return args
    return _m365_release_gate_audit_pack_args(
        args,
        release_gate_write_audit_pack=True,
        release_gate_write_readiness=True,
        release_gate_readiness_require_audit_pack=True,
        release_gate_write_post_run_report=args.release_gate_write_post_run_report
        or args.release_gate_write_post_run_report_index,
    )


_M365_RELEASE_GATE_RUNTIME_ENV_STEPS = {
    "runtime_smoke",
    "runtime_metadata",
    "mcp_smoke_suite",
    "mcp_leftover_dry_run",
}


def _m365_release_gate_step_command(steps: list[tuple[str, list[str]]], step_id: str) -> list[str]:
    for candidate_step_id, command in steps:
        if candidate_step_id == step_id:
            return command
    raise AssertionError(f"release-gate step not found: {step_id}")


def _m365_release_gate_step_commands(steps: list[tuple[str, list[str]]], step_ids: set[str]) -> list[list[str]]:
    return [command for candidate_step_id, command in steps if candidate_step_id in step_ids]


def _list_m365_release_gate_retention(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    retention_root = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_retention_root,
        DEFAULT_RELEASE_GATE_RUN_ARTIFACT_ROOT,
    )
    runs: list[dict[str, Any]] = []
    errors: list[str] = []
    if retention_root.exists():
        for index_path in sorted(retention_root.glob("*/release-gate-retention-index.redacted.json")):
            try:
                payload = json.loads(index_path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("retention index root must be an object")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                errors.append(f"invalid retention index {index_path}: {exc}")
                continue
            runs.append(_m365_release_gate_retention_row(index_path, payload))
    runs.sort(key=lambda run: (str(run.get("timestamp") or ""), str(run.get("correlation_id") or "")), reverse=True)
    return {
        "schema_version": "nac.m365-release-gate-retention-list/v0.1",
        "status": "FAILED" if errors else "PASSED",
        "summary": {
            "retention_root": str(retention_root),
            "run_count": len(runs),
            "invalid_run_count": len(errors),
            "latest_timestamp": runs[0]["timestamp"] if runs else None,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "runs": runs,
        "errors": errors,
    }


def _write_m365_release_gate_retention_list_artifact(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    report_path: Path,
    json_path: Path,
) -> dict[str, Any]:
    payload = _list_m365_release_gate_retention(repo_root, args)
    payload = {
        **payload,
        "schema_version": "nac.m365-release-gate-retention-list-artifact/v0.1",
        "generated_at": _now_utc(),
    }
    payload["summary"] = {
        **payload["summary"],
        "artifact_directory": str(report_path.parent),
        "report_path": str(report_path),
        "json_path": str(json_path),
        "source_artifacts_must_be_redacted": True,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.write_text(_render_m365_release_gate_retention_list_report(payload), encoding="utf-8")
    return payload


def _build_m365_release_readiness(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    retention_root = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_retention_root,
        DEFAULT_RELEASE_GATE_RUN_ARTIFACT_ROOT,
    )
    errors: list[str] = []
    selected_by = "correlation_id" if args.release_gate_readiness_correlation_id else "latest_retention_run"
    try:
        index_path = _select_m365_release_readiness_index(repo_root, retention_root, args)
        retention_index = _load_json_object(index_path, "release gate retention index")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(str(exc))
        return _m365_release_readiness_payload(
            status="BLOCKED",
            retention_root=retention_root,
            selected_by=selected_by,
            run=None,
            evidence=None,
            audit_pack=None,
            checks=[_m365_release_readiness_check("retention_index", "BLOCKED", str(exc))],
            errors=errors,
        )

    run = _m365_release_gate_retention_row(index_path, retention_index)
    evidence_path = Path(str(run.get("evidence_json_path") or index_path.parent / "release-gate-evidence.redacted.json"))
    evidence: dict[str, Any] | None = None
    try:
        evidence = _load_json_object(evidence_path, "release gate evidence")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(str(exc))

    audit_pack = _load_m365_release_readiness_audit_pack(repo_root, args, run)
    checks = _m365_release_readiness_checks(
        retention_index=retention_index,
        run=run,
        evidence=evidence,
        evidence_path=evidence_path,
        audit_pack=audit_pack,
        require_audit_pack=args.release_gate_readiness_require_audit_pack,
        load_errors=errors,
    )
    status = _m365_release_readiness_status(checks)
    readiness_errors = [check["message"] for check in checks if check["status"] != "PASSED" and check.get("required")]
    return _m365_release_readiness_payload(
        status=status,
        retention_root=retention_root,
        selected_by=selected_by,
        run=run,
        evidence=evidence,
        audit_pack=audit_pack,
        checks=checks,
        errors=readiness_errors,
    )


def _select_m365_release_readiness_index(repo_root: Path, retention_root: Path, args: argparse.Namespace) -> Path:
    if args.release_gate_readiness_correlation_id:
        return _resolve_m365_release_gate_retention_reference(
            repo_root,
            retention_root,
            args.release_gate_readiness_correlation_id,
        )
    retention_payload = _list_m365_release_gate_retention(repo_root, args)
    if retention_payload["status"] != "PASSED":
        raise ValueError("; ".join(retention_payload.get("errors") or ["release gate retention list failed"]))
    runs = retention_payload.get("runs") if isinstance(retention_payload.get("runs"), list) else []
    if not runs:
        raise FileNotFoundError(f"no release gate retention runs found under {retention_root}")
    return Path(str(runs[0]["retention_index_path"]))


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _load_m365_release_readiness_audit_pack(
    repo_root: Path,
    args: argparse.Namespace,
    run: dict[str, Any],
) -> dict[str, Any] | None:
    correlation_id = str(run.get("correlation_id") or "")
    for candidate in _m365_release_readiness_audit_pack_candidates(repo_root, args, correlation_id):
        if not candidate.exists():
            continue
        try:
            payload = _load_json_object(candidate, "release gate audit pack")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return {
                "status": "FAILED",
                "path": str(candidate),
                "errors": [str(exc)],
            }
        payload["path"] = str(candidate)
        return payload
    return None


def _m365_release_readiness_audit_pack_candidates(
    repo_root: Path,
    args: argparse.Namespace,
    correlation_id: str,
) -> list[Path]:
    candidates: list[Path] = []
    if args.release_gate_audit_pack_dir:
        explicit = _resolve_m365_release_gate_path(
            repo_root,
            args.release_gate_audit_pack_dir,
            DEFAULT_RELEASE_GATE_AUDIT_PACK_ROOT,
        )
        candidates.append(explicit / "release-gate-retention-audit-pack.redacted.json" if explicit.is_dir() else explicit)
    if not correlation_id:
        return candidates

    audit_pack_root = repo_root / DEFAULT_RELEASE_GATE_AUDIT_PACK_ROOT
    right_slug = f"right-{_safe_release_gate_slug(correlation_id, 72)}"
    if audit_pack_root.exists():
        candidates.extend(
            path
            for path in sorted(audit_pack_root.glob("*/release-gate-retention-audit-pack.redacted.json"), reverse=True)
            if right_slug in path.parent.name
        )
    self_slug = (
        f"left-{_safe_release_gate_slug(correlation_id, 72)}__"
        f"right-{_safe_release_gate_slug(correlation_id, 72)}"
    )
    candidates.append(audit_pack_root / self_slug / "release-gate-retention-audit-pack.redacted.json")

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_candidates.append(candidate)
    return unique_candidates


def _m365_release_readiness_checks(
    *,
    retention_index: dict[str, Any],
    run: dict[str, Any],
    evidence: dict[str, Any] | None,
    evidence_path: Path,
    audit_pack: dict[str, Any] | None,
    require_audit_pack: bool,
    load_errors: list[str],
) -> list[dict[str, Any]]:
    artifacts = _m365_release_gate_retention_artifacts_by_id(retention_index)
    checks = [
        _m365_release_readiness_check(
            "retention_status",
            "PASSED" if retention_index.get("status") == "PASSED" else "FAILED",
            f"retention status is {retention_index.get('status')}",
        ),
        _m365_release_readiness_check(
            "retention_artifacts",
            "PASSED" if _m365_release_readiness_missing_artifacts(artifacts) == [] else "BLOCKED",
            _m365_release_readiness_artifact_message(artifacts),
        ),
        _m365_release_readiness_check(
            "retention_copied_count",
            "PASSED"
            if isinstance(run.get("copied_artifact_count"), int)
            and run.get("copied_artifact_count") >= len(M365_RELEASE_READINESS_REQUIRED_ARTIFACTS)
            else "BLOCKED",
            f"retained copied artifact count is {run.get('copied_artifact_count')}",
        ),
        _m365_release_readiness_check(
            "evidence_present",
            "PASSED" if evidence is not None else "BLOCKED",
            f"release gate evidence JSON is readable at {evidence_path}",
        ),
    ]
    if evidence is not None:
        summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
        checks.extend(
            [
                _m365_release_readiness_check(
                    "evidence_status",
                    "PASSED" if evidence.get("status") == "PASSED" else "FAILED",
                    f"release gate evidence status is {evidence.get('status')}",
                ),
                _m365_release_readiness_check(
                    "evidence_completeness",
                    "PASSED" if summary.get("evidence_completeness") == "complete_release_gate_artifacts" else "BLOCKED",
                    f"evidence completeness is {summary.get('evidence_completeness')}",
                ),
                _m365_release_readiness_check(
                    "evidence_retention_reference",
                    "PASSED" if summary.get("retention_index_attached") is True else "BLOCKED",
                    "release gate evidence references its retention index",
                ),
                _m365_release_readiness_check(
                    "evidence_step_statuses",
                    "PASSED" if _m365_release_readiness_bad_step_statuses(evidence) == [] else "FAILED",
                    _m365_release_readiness_step_message(evidence),
                ),
                _m365_release_readiness_check(
                    "evidence_privacy",
                    "PASSED" if _m365_release_readiness_privacy_ok(summary) else "FAILED",
                    "evidence privacy flags confirm no tokens, raw Graph responses, raw case IDs or SharePoint content reads",
                ),
            ]
        )
    if load_errors:
        checks.append(_m365_release_readiness_check("local_artifact_load", "BLOCKED", "; ".join(load_errors)))
    if require_audit_pack:
        checks.append(
            _m365_release_readiness_check(
                "audit_pack",
                "PASSED" if isinstance(audit_pack, dict) and audit_pack.get("status") == "PASSED" else "BLOCKED",
                _m365_release_readiness_audit_message(audit_pack),
            )
        )
    elif isinstance(audit_pack, dict):
        checks.append(
            _m365_release_readiness_check(
                "audit_pack",
                "PASSED" if audit_pack.get("status") == "PASSED" else "FAILED",
                _m365_release_readiness_audit_message(audit_pack),
                required=False,
            )
        )
    return checks


def _m365_release_readiness_missing_artifacts(artifacts: dict[str, dict[str, Any]]) -> list[str]:
    missing = []
    for artifact_id in M365_RELEASE_READINESS_REQUIRED_ARTIFACTS:
        artifact = artifacts.get(artifact_id)
        if artifact is None or artifact.get("status") != "COPIED" or not artifact.get("artifact_sha256"):
            missing.append(artifact_id)
    return missing


def _m365_release_readiness_artifact_message(artifacts: dict[str, dict[str, Any]]) -> str:
    missing = _m365_release_readiness_missing_artifacts(artifacts)
    if not missing:
        return "all required release gate artifacts are copied and hashed"
    return "missing or not copied required artifacts: " + ", ".join(missing)


def _m365_release_readiness_bad_step_statuses(evidence: dict[str, Any]) -> list[str]:
    by_id = {
        step.get("id"): step
        for step in evidence.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("id"), str)
    }
    bad = []
    for step_id in M365_RELEASE_READINESS_REQUIRED_EVIDENCE_STEPS:
        step = by_id.get(step_id)
        if step is None or step.get("status") != "PASSED":
            bad.append(step_id)
    return bad


def _m365_release_readiness_step_message(evidence: dict[str, Any]) -> str:
    bad = _m365_release_readiness_bad_step_statuses(evidence)
    if not bad:
        return "all required release gate evidence steps passed"
    return "required release gate evidence steps did not pass: " + ", ".join(bad)


def _m365_release_readiness_privacy_ok(summary: dict[str, Any]) -> bool:
    return (
        summary.get("stores_tokens_or_secrets") is False
        and summary.get("stores_raw_graph_response") is False
        and summary.get("stores_raw_case_id") is False
        and summary.get("reads_sharepoint_file_content") is False
    )


def _m365_release_readiness_audit_message(audit_pack: dict[str, Any] | None) -> str:
    if audit_pack is None:
        return "release gate audit pack is not attached"
    return f"release gate audit pack status is {audit_pack.get('status')} at {audit_pack.get('path')}"


def _m365_release_readiness_check(
    check_id: str,
    status: str,
    message: str,
    *,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": status,
        "required": required,
        "message": message,
    }


def _m365_release_readiness_status(checks: list[dict[str, Any]]) -> str:
    required_statuses = [check.get("status") for check in checks if check.get("required")]
    if "FAILED" in required_statuses:
        return "FAILED"
    if "BLOCKED" in required_statuses:
        return "BLOCKED"
    return "PASSED"


def _m365_release_readiness_payload(
    *,
    status: str,
    retention_root: Path,
    selected_by: str,
    run: dict[str, Any] | None,
    evidence: dict[str, Any] | None,
    audit_pack: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    summary = evidence.get("summary") if isinstance(evidence, dict) and isinstance(evidence.get("summary"), dict) else {}
    run = run or {}
    return {
        "schema_version": "nac.m365-release-readiness/v0.1",
        "status": status,
        "generated_at": _now_utc(),
        "summary": {
            "mvp_release_readiness": "READY" if status == "PASSED" else "NOT_READY",
            "selected_by": selected_by,
            "retention_root": str(retention_root),
            "workspace_id": run.get("workspace_id") or summary.get("workspace_id"),
            "correlation_id": run.get("correlation_id") or summary.get("correlation_id"),
            "release_gate_status": run.get("status"),
            "evidence_status": evidence.get("status") if isinstance(evidence, dict) else None,
            "evidence_completeness": summary.get("evidence_completeness"),
            "matter_access_delegation_smoke_status": summary.get("matter_access_delegation_smoke_status"),
            "matter_access_apply_readiness_status": summary.get("matter_access_apply_readiness_status"),
            "matter_access_apply_request_plan_status": summary.get("matter_access_apply_request_plan_status"),
            "retained_artifact_count": run.get("copied_artifact_count") or summary.get("retained_artifact_count"),
            "required_artifact_count": len(M365_RELEASE_READINESS_REQUIRED_ARTIFACTS),
            "retention_index_path": run.get("retention_index_path"),
            "evidence_json_path": run.get("evidence_json_path"),
            "report_path": run.get("report_path"),
            "artifact_index_path": run.get("artifact_index_path"),
            "audit_pack_status": audit_pack.get("status") if isinstance(audit_pack, dict) else None,
            "audit_pack_path": audit_pack.get("path") if isinstance(audit_pack, dict) else None,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "checks": checks,
        "errors": errors,
        "privacy": {
            "source_artifacts_must_be_redacted": True,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }


def _write_m365_release_gate_post_run_report(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    payload = _build_m365_release_gate_post_run_report(repo_root, args)
    report_path, json_path, comment_path = _m365_release_gate_post_run_report_paths(repo_root, args, payload)
    payload["summary"] = {
        **payload["summary"],
        "artifact_directory": str(report_path.parent),
        "report_path": str(report_path),
        "json_path": str(json_path),
        "github_comment_path": str(comment_path),
    }
    payload["artifacts"] = [
        _m365_release_gate_post_run_artifact("post_run_report", payload.get("status"), report_path, json_path),
        _m365_release_gate_post_run_artifact("github_comment_draft", payload.get("status"), comment_path, None),
    ]
    payload["github_comment_draft"] = _render_m365_release_gate_github_comment(payload)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    comment_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.write_text(_render_m365_release_gate_post_run_report(payload), encoding="utf-8")
    comment_path.write_text(payload["github_comment_draft"], encoding="utf-8")
    return payload


def _build_m365_release_gate_post_run_report(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    retention_root = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_retention_root,
        DEFAULT_RELEASE_GATE_RUN_ARTIFACT_ROOT,
    )
    target_reference = _m365_release_gate_post_run_target_reference(args)
    if not target_reference:
        return _m365_release_gate_post_run_payload(
            status="BLOCKED",
            retention_root=retention_root,
            target_reference=None,
            target_run=None,
            baseline_reference=None,
            baseline_selection="not_requested",
            readiness_payload=None,
            compare_payload=None,
            checks=[
                _m365_release_gate_post_run_check(
                    "target_correlation_id",
                    "BLOCKED",
                    "requires --release-gate-readiness-correlation-id or --release-gate-compare-right",
                )
            ],
            errors=["requires --release-gate-readiness-correlation-id or --release-gate-compare-right"],
        )

    errors: list[str] = []
    try:
        target_index_path = _resolve_m365_release_gate_retention_reference(repo_root, retention_root, target_reference)
        target_index = _load_json_object(target_index_path, "release gate retention index")
        target_run = _m365_release_gate_retention_row(target_index_path, target_index)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(str(exc))
        return _m365_release_gate_post_run_payload(
            status="BLOCKED",
            retention_root=retention_root,
            target_reference=target_reference,
            target_run=None,
            baseline_reference=args.release_gate_compare_left,
            baseline_selection="explicit" if args.release_gate_compare_left else "not_available",
            readiness_payload=None,
            compare_payload=None,
            checks=[
                _m365_release_gate_post_run_check("target_retention_index", "BLOCKED", str(exc)),
            ],
            errors=errors,
        )

    retention_payload = _list_m365_release_gate_retention(repo_root, args)
    errors.extend(retention_payload.get("errors", []))
    baseline_reference = args.release_gate_compare_left
    baseline_selection = "explicit" if baseline_reference else "previous_retained_run"
    baseline_run: dict[str, Any] | None = None
    if not baseline_reference:
        baseline_run = _m365_release_gate_post_run_previous_baseline(retention_payload.get("runs", []), target_run)
        if baseline_run is None:
            baseline_selection = "not_available"
            errors.append("no previous retained PASSED release-gate run found for the target workspace")
        else:
            baseline_reference = str(baseline_run.get("correlation_id"))

    target_correlation_id = str(target_run.get("correlation_id") or target_reference)
    compare_payload: dict[str, Any] | None = None
    if baseline_reference:
        compare_args = _m365_release_gate_audit_pack_args(
            args,
            release_gate_compare_left=baseline_reference,
            release_gate_compare_right=target_reference,
        )
        compare_payload = _compare_m365_release_gate_retention(repo_root, compare_args)
        errors.extend(compare_payload.get("errors", []))
        if compare_payload.get("status") == "PASSED":
            summary = compare_payload.get("summary", {})
            baseline_reference = summary.get("left_correlation_id") or baseline_reference
    else:
        compare_payload = _m365_release_gate_post_run_blocked_compare(retention_root, target_correlation_id)
        errors.extend(compare_payload.get("errors", []))

    audit_pack_dir = _m365_release_gate_post_run_readiness_audit_pack_dir(
        repo_root,
        args,
        baseline_reference=baseline_reference,
        target_correlation_id=target_correlation_id,
    )
    readiness_args = _m365_release_gate_audit_pack_args(
        args,
        release_gate_readiness_correlation_id=target_reference,
        release_gate_readiness_output=None,
        release_gate_audit_pack_dir=audit_pack_dir,
        release_gate_readiness_require_audit_pack=True,
    )
    readiness_payload = _build_m365_release_readiness(repo_root, readiness_args)
    errors.extend(readiness_payload.get("errors", []))

    checks = [
        _m365_release_gate_post_run_check(
            "target_retention_index",
            "PASSED",
            f"target retention index is readable for {target_correlation_id}",
        ),
        _m365_release_gate_post_run_check(
            "baseline_selection",
            "PASSED" if baseline_reference else "BLOCKED",
            _m365_release_gate_post_run_baseline_message(baseline_selection, baseline_reference),
        ),
        _m365_release_gate_post_run_check(
            "release_readiness",
            str(readiness_payload.get("status") or "BLOCKED"),
            f"release-readiness status is {readiness_payload.get('status')}",
        ),
        _m365_release_gate_post_run_check(
            "retention_compare",
            str(compare_payload.get("status") or "BLOCKED"),
            f"release-gate-retention-compare status is {compare_payload.get('status')}",
        ),
        _m365_release_gate_post_run_check(
            "offline_only",
            "PASSED",
            "post-gate reporter writes local redacted artifacts and performs no Graph or GitHub writes",
        ),
    ]
    status = _m365_release_gate_post_run_status(checks)
    return _m365_release_gate_post_run_payload(
        status=status,
        retention_root=retention_root,
        target_reference=target_reference,
        target_run=target_run,
        baseline_reference=baseline_reference,
        baseline_selection=baseline_selection,
        readiness_payload=readiness_payload,
        compare_payload=compare_payload,
        checks=checks,
        errors=errors,
    )


def _m365_release_gate_post_run_target_reference(args: argparse.Namespace) -> str | None:
    return args.release_gate_readiness_correlation_id or args.release_gate_compare_right


def _m365_release_gate_post_run_previous_baseline(
    runs: list[dict[str, Any]],
    target_run: dict[str, Any],
) -> dict[str, Any] | None:
    target_correlation_id = str(target_run.get("correlation_id") or "")
    target_timestamp = str(target_run.get("timestamp") or "")
    target_workspace_id = target_run.get("workspace_id")
    candidates: list[dict[str, Any]] = []
    for run in runs:
        if str(run.get("correlation_id") or "") == target_correlation_id:
            continue
        if target_workspace_id and run.get("workspace_id") != target_workspace_id:
            continue
        if run.get("status") != "PASSED":
            continue
        if not isinstance(run.get("copied_artifact_count"), int) or run.get("copied_artifact_count") <= 0:
            continue
        if run.get("not_attached_artifact_count") not in (0, None):
            continue
        run_timestamp = str(run.get("timestamp") or "")
        if target_timestamp and run_timestamp and run_timestamp >= target_timestamp:
            continue
        candidates.append(run)
    if not candidates:
        return None
    candidates.sort(key=lambda run: (str(run.get("timestamp") or ""), str(run.get("correlation_id") or "")), reverse=True)
    return candidates[0]


def _m365_release_gate_post_run_readiness_audit_pack_dir(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    baseline_reference: str | None,
    target_correlation_id: str,
) -> Path | None:
    if args.release_gate_audit_pack_dir is not None:
        return args.release_gate_audit_pack_dir
    if not baseline_reference:
        return None
    audit_args = _m365_release_gate_audit_pack_args(
        args,
        release_gate_compare_left=baseline_reference,
        release_gate_compare_right=target_correlation_id,
    )
    pack_dir = _m365_release_gate_retention_audit_pack_dir(repo_root, audit_args)
    return _m365_release_gate_path_for_command(repo_root, pack_dir)


def _m365_release_gate_post_run_blocked_compare(retention_root: Path, target_correlation_id: str) -> dict[str, Any]:
    return {
        "schema_version": "nac.m365-release-gate-retention-compare/v0.1",
        "status": "BLOCKED",
        "summary": {
            "retention_root": str(retention_root),
            "right_correlation_id": target_correlation_id,
            "baseline_selection": "not_available",
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "left": None,
        "right": None,
        "comparison": {},
        "errors": ["no previous retained PASSED release-gate run found for the target workspace"],
    }


def _m365_release_gate_post_run_baseline_message(
    baseline_selection: str,
    baseline_reference: str | None,
) -> str:
    if baseline_reference:
        return f"baseline selected by {baseline_selection}: {baseline_reference}"
    return "no previous retained PASSED release-gate baseline is available"


def _m365_release_gate_post_run_payload(
    *,
    status: str,
    retention_root: Path,
    target_reference: str | None,
    target_run: dict[str, Any] | None,
    baseline_reference: str | None,
    baseline_selection: str,
    readiness_payload: dict[str, Any] | None,
    compare_payload: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    target_run = target_run or {}
    readiness_summary = readiness_payload.get("summary", {}) if isinstance(readiness_payload, dict) else {}
    compare_summary = compare_payload.get("summary", {}) if isinstance(compare_payload, dict) else {}
    return {
        "schema_version": "nac.m365-release-gate-post-run-report/v0.1",
        "status": status,
        "generated_at": _now_utc(),
        "summary": {
            "correlation_id": target_run.get("correlation_id") or readiness_summary.get("correlation_id") or target_reference,
            "target_reference": target_reference,
            "baseline_correlation_id": compare_summary.get("left_correlation_id") or baseline_reference,
            "baseline_selection": baseline_selection,
            "retention_root": str(retention_root),
            "workspace_id": target_run.get("workspace_id") or readiness_summary.get("workspace_id"),
            "mvp_release_readiness": readiness_summary.get("mvp_release_readiness"),
            "release_readiness_status": readiness_payload.get("status") if isinstance(readiness_payload, dict) else None,
            "release_gate_status": readiness_summary.get("release_gate_status") or target_run.get("status"),
            "audit_pack_status": readiness_summary.get("audit_pack_status"),
            "audit_pack_path": readiness_summary.get("audit_pack_path"),
            "retention_compare_status": compare_payload.get("status") if isinstance(compare_payload, dict) else None,
            "difference_count": compare_summary.get("difference_count"),
            "artifact_difference_count": compare_summary.get("artifact_difference_count"),
            "missing_attachment_difference_count": compare_summary.get("missing_attachment_difference_count"),
            "github_comment_draft_only": True,
            "github_comment_posted": False,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "stores_tokens_or_secrets": False,
            "stores_raw_graph_response": False,
            "stores_raw_case_id": False,
            "reads_sharepoint_file_content": False,
            "source_artifacts_must_be_redacted": True,
        },
        "checks": checks,
        "readiness": readiness_payload,
        "retention_compare": compare_payload,
        "errors": errors,
        "privacy": {
            "source_artifacts_must_be_redacted": True,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "github_comment_posted": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }


def _m365_release_gate_post_run_report_paths(
    repo_root: Path,
    args: argparse.Namespace,
    payload: dict[str, Any],
) -> tuple[Path, Path, Path]:
    summary = payload.get("summary", {})
    slug = _safe_release_gate_slug(str(summary.get("correlation_id") or "missing-correlation-id"), 96)
    default_dir = DEFAULT_RELEASE_GATE_POST_RUN_REPORT_ROOT / slug
    report_path = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_post_run_report_output,
        default_dir / "release-gate-post-run-report.redacted.md",
    )
    json_path = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_post_run_report_json_output,
        default_dir / "release-gate-post-run-report.redacted.json",
    )
    comment_path = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_github_comment_output,
        default_dir / "github-evidence-comment.redacted.md",
    )
    return report_path, json_path, comment_path


def _m365_release_gate_post_run_artifact(
    artifact_id: str,
    status: str | None,
    report_path: Path,
    json_path: Path | None,
) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "status": status,
        "report_path": str(report_path),
        "json_path": str(json_path) if json_path is not None else None,
        "privacy": {
            "source_artifacts_must_be_redacted": True,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "github_comment_posted": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }


def _m365_release_gate_post_run_check(check_id: str, status: str, message: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": status,
        "required": True,
        "message": message,
    }


def _m365_release_gate_post_run_status(checks: list[dict[str, Any]]) -> str:
    statuses = [check.get("status") for check in checks if check.get("required")]
    if "FAILED" in statuses:
        return "FAILED"
    if "BLOCKED" in statuses:
        return "BLOCKED"
    return "PASSED"


def _m365_release_gate_post_run_report_return_code(payload: dict[str, Any]) -> int:
    if payload["status"] == "PASSED":
        return 0
    return 2 if payload["status"] == "BLOCKED" else 1


def _render_m365_release_gate_post_run_report(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    lines = [
        "# M365 Release Gate Post-Run Report",
        "",
        f"Status: {payload.get('status')}",
        f"Generated at: {payload.get('generated_at')}",
        f"Correlation ID: {summary.get('correlation_id')}",
        f"Baseline correlation ID: {summary.get('baseline_correlation_id') or 'none'}",
        f"Baseline selection: {summary.get('baseline_selection')}",
        f"Workspace ID: {summary.get('workspace_id')}",
        f"MVP release readiness: {summary.get('mvp_release_readiness')}",
        f"Release readiness status: {summary.get('release_readiness_status')}",
        f"Retention compare status: {summary.get('retention_compare_status')}",
        f"Difference count: {summary.get('difference_count')}",
        f"Audit pack status: {summary.get('audit_pack_status')}",
        f"Audit pack path: {summary.get('audit_pack_path')}",
        "",
        "## Local Artifacts",
        "",
        f"- Report: `{_md_cell(summary.get('report_path'))}`",
        f"- JSON: `{_md_cell(summary.get('json_path'))}`",
        f"- GitHub comment draft: `{_md_cell(summary.get('github_comment_path'))}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Message |",
        "| --- | --- | --- |",
    ]
    for check in payload.get("checks", []):
        lines.append(
            f"| {_md_cell(check.get('id'))} | {_md_cell(check.get('status'))} | {_md_cell(check.get('message'))} |"
        )
    lines.extend(
        [
            "",
            "## Privacy",
            "",
            "- Graph requests executed: false",
            "- Tenant writes executed: false",
            "- Tenant deletes executed: false",
            "- GitHub comment posted: false",
            "- Stores tokens or secrets: false",
            "- Stores raw Graph response: false",
            "- Stores raw case ID: false",
            "- Reads SharePoint file content: false",
        ]
    )
    errors = payload.get("errors", [])
    if errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {_md_cell(error)}" for error in errors)
    lines.append("")
    return "\n".join(lines)


def _render_m365_release_gate_github_comment(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    lines = [
        "## M365 Release-Gate Evidence",
        "",
        "Draft only. This command writes local redacted evidence and does not post to GitHub.",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Correlation ID: `{_md_cell(summary.get('correlation_id'))}`",
        f"- Baseline: `{_md_cell(summary.get('baseline_correlation_id')) or 'none'}`",
        f"- Baseline selection: `{_md_cell(summary.get('baseline_selection'))}`",
        f"- MVP readiness: `{_md_cell(summary.get('mvp_release_readiness'))}`",
        f"- Release readiness: `{_md_cell(summary.get('release_readiness_status'))}`",
        f"- Audit pack: `{_md_cell(summary.get('audit_pack_status'))}`",
        f"- Retention compare: `{_md_cell(summary.get('retention_compare_status'))}`",
        f"- Difference count: `{_md_cell(summary.get('difference_count'))}`",
        f"- Missing attachment differences: `{_md_cell(summary.get('missing_attachment_difference_count'))}`",
        f"- Report: `{_md_cell(summary.get('report_path'))}`",
        f"- JSON: `{_md_cell(summary.get('json_path'))}`",
        "",
        "Privacy: no Graph requests, no tenant writes/deletes, no GitHub write, no tokens/secrets, no raw Graph response, no raw case ID, no SharePoint file content reads.",
    ]
    errors = payload.get("errors", [])
    if errors:
        lines.extend(["", "Blocking notes:"])
        lines.extend(f"- {_md_cell(error)}" for error in errors)
    lines.append("")
    return "\n".join(lines)


def _print_m365_release_gate_post_run_report(payload: dict[str, Any]) -> None:
    summary = payload.get("summary", {})
    print(f"STATUS: {payload.get('status')}")
    print(f"Correlation ID: {summary.get('correlation_id')}")
    print(f"Baseline: {summary.get('baseline_correlation_id') or 'none'}")
    print(f"MVP readiness: {summary.get('mvp_release_readiness')}")
    print(f"Report: {summary.get('report_path')}")
    print(f"GitHub comment draft: {summary.get('github_comment_path')}")


def _list_m365_release_gate_post_run_reports(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    report_root = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_post_run_report_root,
        DEFAULT_RELEASE_GATE_POST_RUN_REPORT_ROOT,
    )
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if report_root.exists():
        for json_path in sorted(report_root.glob("*/release-gate-post-run-report.redacted.json")):
            try:
                payload = _load_json_object(json_path, "release gate post-run report")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                errors.append(f"invalid post-gate report artifact {json_path}: {exc}")
                continue
            row = _m365_release_gate_post_run_report_index_row(json_path, payload)
            if _m365_release_gate_post_run_report_index_matches(row, args):
                rows.append(row)
    rows.sort(
        key=lambda row: (
            str(row.get("generated_at") or ""),
            str(row.get("correlation_id") or ""),
        ),
        reverse=True,
    )
    return {
        "schema_version": "nac.m365-release-gate-post-run-report-index/v0.1",
        "status": "FAILED" if errors else "PASSED",
        "summary": {
            "post_run_report_root": str(report_root),
            "post_run_report_count": len(rows),
            "invalid_artifact_count": len(errors),
            "correlation_id": args.release_gate_post_run_report_correlation_id,
            "baseline_correlation_id": args.release_gate_post_run_report_baseline,
            "status_filter": args.release_gate_post_run_report_status,
            "query": args.release_gate_post_run_report_query,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "github_writes_executed": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "post_run_reports": rows,
        "errors": errors,
    }


def _write_m365_release_gate_post_run_report_index_artifact(
    repo_root: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    payload = _list_m365_release_gate_post_run_reports(repo_root, args)
    if payload["status"] != "PASSED":
        return {
            **payload,
            "schema_version": "nac.m365-release-gate-post-run-report-index-artifact/v0.1",
        }
    report_path, json_path = _m365_release_gate_post_run_report_index_artifact_paths(repo_root, args, payload)
    payload = {
        **payload,
        "schema_version": "nac.m365-release-gate-post-run-report-index-artifact/v0.1",
        "generated_at": _now_utc(),
    }
    payload["summary"] = {
        **payload["summary"],
        "artifact_directory": str(report_path.parent),
        "report_path": str(report_path),
        "json_path": str(json_path),
        "source_artifacts_must_be_redacted": True,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.write_text(_render_m365_release_gate_post_run_report_index_report(payload), encoding="utf-8")
    return payload


def _m365_release_gate_post_run_report_index_row(json_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    report_path = summary.get("report_path") or str(json_path.parent / "release-gate-post-run-report.redacted.md")
    json_output_path = summary.get("json_path") or str(json_path)
    github_comment_path = summary.get("github_comment_path") or str(json_path.parent / "github-evidence-comment.redacted.md")
    row = {
        "status": payload.get("status"),
        "generated_at": payload.get("generated_at"),
        "correlation_id": summary.get("correlation_id"),
        "baseline_correlation_id": summary.get("baseline_correlation_id"),
        "baseline_selection": summary.get("baseline_selection"),
        "workspace_id": summary.get("workspace_id"),
        "mvp_release_readiness": summary.get("mvp_release_readiness"),
        "release_readiness_status": summary.get("release_readiness_status"),
        "release_gate_status": summary.get("release_gate_status"),
        "audit_pack_status": summary.get("audit_pack_status"),
        "retention_compare_status": summary.get("retention_compare_status"),
        "difference_count": summary.get("difference_count"),
        "artifact_directory": summary.get("artifact_directory") or str(json_path.parent),
        "report_path": report_path,
        "json_path": json_output_path,
        "github_comment_path": github_comment_path,
        "source_json_path": str(json_path),
        "search_fields": {
            "correlation_id": summary.get("correlation_id"),
            "baseline_correlation_id": summary.get("baseline_correlation_id"),
            "baseline_selection": summary.get("baseline_selection"),
            "workspace_id": summary.get("workspace_id"),
            "mvp_release_readiness": summary.get("mvp_release_readiness"),
            "release_readiness_status": summary.get("release_readiness_status"),
            "status": payload.get("status"),
            "generated_at": payload.get("generated_at"),
            "report_path": report_path,
            "json_path": json_output_path,
            "github_comment_path": github_comment_path,
        },
        "privacy": {
            "source_artifacts_must_be_redacted": True,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "github_writes_executed": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }
    return row


def _m365_release_gate_post_run_report_index_matches(row: dict[str, Any], args: argparse.Namespace) -> bool:
    if (
        args.release_gate_post_run_report_correlation_id
        and row.get("correlation_id") != args.release_gate_post_run_report_correlation_id
    ):
        return False
    if (
        args.release_gate_post_run_report_baseline
        and row.get("baseline_correlation_id") != args.release_gate_post_run_report_baseline
    ):
        return False
    if args.release_gate_post_run_report_status and row.get("status") != args.release_gate_post_run_report_status:
        return False
    query = args.release_gate_post_run_report_query
    if query:
        haystack = " ".join(str(value or "") for value in row.get("search_fields", {}).values()).lower()
        return query.lower() in haystack
    return True


def _m365_release_gate_post_run_report_index_artifact_paths(
    repo_root: Path,
    args: argparse.Namespace,
    payload: dict[str, Any],
) -> tuple[Path, Path]:
    summary = payload.get("summary", {})
    slug = _m365_release_gate_post_run_report_index_artifact_slug(summary)
    default_dir = DEFAULT_RELEASE_GATE_POST_RUN_REPORT_INDEX_ROOT / slug
    default_report = default_dir / "release-gate-post-run-report-index.redacted.md"
    default_json = default_dir / "release-gate-post-run-report-index.redacted.json"
    report_path = _resolve_m365_release_gate_path(repo_root, args.release_gate_post_run_report_index_output, default_report)
    json_path = _resolve_m365_release_gate_path(repo_root, args.release_gate_post_run_report_index_json_output, default_json)
    return report_path, json_path


def _m365_release_gate_post_run_report_index_artifact_slug(summary: dict[str, Any]) -> str:
    parts: list[str] = []
    filters = [
        ("correlation", summary.get("correlation_id")),
        ("baseline", summary.get("baseline_correlation_id")),
        ("status", summary.get("status_filter")),
        ("query", summary.get("query")),
    ]
    for label, value in filters:
        if value:
            parts.append(f"{label}-{_safe_release_gate_slug(str(value), 72)}")
    return "__".join(parts) if parts else "all"


def _render_m365_release_gate_post_run_report_index_report(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    lines = [
        "# M365 Release Gate Post-Run Report Index",
        "",
        f"Status: {payload.get('status')}",
        f"Generated at: {payload.get('generated_at')}",
        f"Post-run report root: {summary.get('post_run_report_root')}",
        f"Post-run report count: {summary.get('post_run_report_count')}",
        f"Invalid artifact count: {summary.get('invalid_artifact_count')}",
        "",
        "## Filters",
        "",
        f"- Correlation ID: {_md_cell(summary.get('correlation_id')) or 'none'}",
        f"- Baseline correlation ID: {_md_cell(summary.get('baseline_correlation_id')) or 'none'}",
        f"- Status: {_md_cell(summary.get('status_filter')) or 'none'}",
        f"- Query: {_md_cell(summary.get('query')) or 'none'}",
        "",
        "## Privacy",
        "",
        "- Graph requests executed: false",
        "- Tenant writes executed: false",
        "- Tenant deletes executed: false",
        "- GitHub writes executed: false",
        "- Stores tokens or secrets: false",
        "- Reads SharePoint file content: false",
        "",
        "## Post-Run Reports",
        "",
    ]
    reports = payload.get("post_run_reports", [])
    if reports:
        lines.extend(
            [
                "| Generated at | Correlation ID | Baseline | Status | MVP readiness | Report | JSON | Comment |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        lines.extend(_m365_release_gate_post_run_report_index_markdown_row(row) for row in reports)
    else:
        lines.append("No post-gate report artifacts matched the selected filters.")
    errors = payload.get("errors", [])
    if errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {_md_cell(error)}" for error in errors)
    lines.append("")
    return "\n".join(lines)


def _m365_release_gate_post_run_report_index_markdown_row(row: dict[str, Any]) -> str:
    return (
        f"| {_md_cell(row.get('generated_at'))} | {_md_cell(row.get('correlation_id'))} | "
        f"{_md_cell(row.get('baseline_correlation_id')) or 'none'} | {_md_cell(row.get('status'))} | "
        f"{_md_cell(row.get('mvp_release_readiness'))} | `{_md_cell(row.get('report_path'))}` | "
        f"`{_md_cell(row.get('json_path'))}` | `{_md_cell(row.get('github_comment_path'))}` |"
    )


def _print_m365_release_gate_post_run_report_index(payload: dict[str, Any]) -> None:
    summary = payload.get("summary", {})
    print(f"STATUS: {payload.get('status')}")
    print(f"Post-run report root: {summary.get('post_run_report_root')}")
    print(f"Post-run report count: {summary.get('post_run_report_count')}")
    print(f"Invalid artifact count: {summary.get('invalid_artifact_count')}")
    for row in payload.get("post_run_reports", []):
        print(
            f"- {row.get('generated_at')}: {row.get('correlation_id')} "
            f"baseline={row.get('baseline_correlation_id') or 'none'} status={row.get('status')} "
            f"readiness={row.get('mvp_release_readiness')} report={row.get('report_path')}"
        )
    for error in payload.get("errors", []):
        print(f"ERROR: {error}", file=sys.stderr)


def _print_m365_release_gate_post_run_report_index_artifact(payload: dict[str, Any]) -> None:
    _print_m365_release_gate_post_run_report_index(payload)
    summary = payload.get("summary", {})
    if summary.get("report_path"):
        print(f"Index report: {summary.get('report_path')}")
    if summary.get("json_path"):
        print(f"Index JSON: {summary.get('json_path')}")


def _write_m365_release_gate_retention_audit_pack(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    pack_dir = _m365_release_gate_retention_audit_pack_dir(repo_root, args)
    pack_dir.mkdir(parents=True, exist_ok=True)
    retention_payload = _write_m365_release_gate_retention_list_artifact(
        repo_root,
        args,
        report_path=pack_dir / "release-gate-retention-list.redacted.md",
        json_path=pack_dir / "release-gate-retention-list.redacted.json",
    )
    artifacts = [
        _m365_release_gate_audit_pack_artifact("retention_list", retention_payload),
    ]
    errors = list(retention_payload.get("errors", []))
    compare_args = _m365_release_gate_audit_pack_args(
        args,
        release_gate_compare_output=_m365_release_gate_audit_pack_compare_dir(pack_dir, args)
        / "release-gate-retention-compare.redacted.md",
        release_gate_compare_json_output=_m365_release_gate_audit_pack_compare_dir(pack_dir, args)
        / "release-gate-retention-compare.redacted.json",
    )
    compare_payload = _write_m365_release_gate_retention_compare_artifact(repo_root, compare_args)
    artifacts.append(_m365_release_gate_audit_pack_artifact("retention_compare", compare_payload))
    errors.extend(compare_payload.get("errors", []))

    compare_index_payload: dict[str, Any] | None = None
    if compare_payload["status"] == "PASSED":
        compare_index_root = args.release_gate_compare_index_root or (pack_dir / "comparisons")
        compare_index_args = _m365_release_gate_audit_pack_args(
            args,
            release_gate_compare_index_root=compare_index_root,
            release_gate_compare_index_output=pack_dir / "release-gate-retention-compare-index.redacted.md",
            release_gate_compare_index_json_output=pack_dir / "release-gate-retention-compare-index.redacted.json",
        )
        compare_index_payload = _write_m365_release_gate_retention_compare_index_artifact(repo_root, compare_index_args)
        artifacts.append(_m365_release_gate_audit_pack_artifact("retention_compare_index", compare_index_payload))
        errors.extend(compare_index_payload.get("errors", []))
    else:
        artifacts.append(
            {
                "id": "retention_compare_index",
                "status": "NOT_WRITTEN",
                "reason": "retention_compare did not pass",
            }
        )

    status = _m365_release_gate_audit_pack_status(retention_payload, compare_payload, compare_index_payload)
    manifest_report_path = pack_dir / "release-gate-retention-audit-pack.redacted.md"
    manifest_json_path = pack_dir / "release-gate-retention-audit-pack.redacted.json"
    payload = {
        "schema_version": "nac.m365-release-gate-retention-audit-pack/v0.1",
        "status": status,
        "generated_at": _now_utc(),
        "summary": {
            "pack_dir": str(pack_dir),
            "retention_root": retention_payload.get("summary", {}).get("retention_root"),
            "compare_root": (
                compare_index_payload.get("summary", {}).get("compare_root")
                if isinstance(compare_index_payload, dict)
                else str(pack_dir / "comparisons")
            ),
            "left_correlation_id": args.release_gate_compare_left,
            "right_correlation_id": args.release_gate_compare_right,
            "status_filter": args.release_gate_compare_status,
            "query": args.release_gate_compare_query,
            "artifact_count": len(artifacts),
            "report_path": str(manifest_report_path),
            "json_path": str(manifest_json_path),
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
            "source_artifacts_must_be_redacted": True,
        },
        "artifacts": artifacts,
        "steps": [
            _m365_release_gate_audit_pack_step("retention_list", retention_payload),
            _m365_release_gate_audit_pack_step("retention_compare", compare_payload),
            _m365_release_gate_audit_pack_step("retention_compare_index", compare_index_payload),
        ],
        "errors": errors,
        "privacy": {
            "source_artifacts_must_be_redacted": True,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }
    manifest_json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest_report_path.write_text(_render_m365_release_gate_retention_audit_pack_report(payload), encoding="utf-8")
    return payload


def _write_m365_release_gate_run_audit_pack(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
    baseline_reference: str | None = None,
) -> dict[str, Any]:
    audit_args = _m365_release_gate_run_audit_pack_args(
        args,
        correlation_id=correlation_id,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
        baseline_reference=baseline_reference,
    )
    return _write_m365_release_gate_retention_audit_pack(repo_root, audit_args)


def _m365_release_gate_run_audit_pack_args(
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
    baseline_reference: str | None = None,
) -> argparse.Namespace:
    return _m365_release_gate_audit_pack_args(
        args,
        release_gate_retention_root=args.release_gate_retention_root or release_gate_run_artifact_dir.parent,
        release_gate_compare_left=args.release_gate_compare_left or baseline_reference or correlation_id,
        release_gate_compare_right=args.release_gate_compare_right or correlation_id,
    )


def _m365_release_gate_run_audit_pack_command(
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
    baseline_reference: str | None = None,
) -> str:
    audit_args = _m365_release_gate_run_audit_pack_args(
        args,
        correlation_id=correlation_id,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
        baseline_reference=baseline_reference,
    )
    command = [
        "python3",
        "scripts/nac.py",
        "m365",
        "teams-sharepoint",
        "release-gate-retention-audit-pack",
        "--release-gate-retention-root",
        str(audit_args.release_gate_retention_root),
        "--release-gate-compare-left",
        str(audit_args.release_gate_compare_left),
        "--release-gate-compare-right",
        str(audit_args.release_gate_compare_right),
    ]
    if audit_args.release_gate_audit_pack_dir is not None:
        command.extend(["--release-gate-audit-pack-dir", str(audit_args.release_gate_audit_pack_dir)])
    if audit_args.release_gate_compare_status:
        command.extend(["--release-gate-compare-status", str(audit_args.release_gate_compare_status)])
    if audit_args.release_gate_compare_query:
        command.extend(["--release-gate-compare-query", str(audit_args.release_gate_compare_query)])
    command.extend(["--format", "json"])
    return " ".join(command)


def _write_m365_release_gate_run_readiness(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
    baseline_reference: str | None = None,
) -> dict[str, Any]:
    output_path = _m365_release_gate_run_readiness_output_path(repo_root, args, release_gate_run_artifact_dir)
    readiness_args = _m365_release_gate_run_readiness_args(
        repo_root,
        args,
        correlation_id=correlation_id,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
        output_path=output_path,
        baseline_reference=baseline_reference,
    )
    payload = _build_m365_release_readiness(repo_root, readiness_args)
    payload["summary"]["json_path"] = str(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def _m365_release_gate_run_readiness_args(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
    output_path: Path,
    baseline_reference: str | None = None,
) -> argparse.Namespace:
    audit_pack_dir = _m365_release_gate_run_readiness_audit_pack_dir(
        repo_root,
        args,
        correlation_id=correlation_id,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
        baseline_reference=baseline_reference,
    )
    return _m365_release_gate_audit_pack_args(
        args,
        release_gate_retention_root=args.release_gate_retention_root or release_gate_run_artifact_dir.parent,
        release_gate_readiness_correlation_id=correlation_id,
        release_gate_readiness_output=output_path,
        release_gate_audit_pack_dir=audit_pack_dir,
    )


def _m365_release_gate_run_readiness_audit_pack_dir(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
    baseline_reference: str | None = None,
) -> Path | None:
    if not args.release_gate_write_audit_pack:
        return args.release_gate_audit_pack_dir

    audit_args = _m365_release_gate_run_audit_pack_args(
        args,
        correlation_id=correlation_id,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
        baseline_reference=baseline_reference,
    )
    pack_dir = _m365_release_gate_retention_audit_pack_dir(repo_root, audit_args)
    return _m365_release_gate_path_for_command(repo_root, pack_dir)


def _m365_release_gate_path_for_command(repo_root: Path, path: Path) -> Path:
    try:
        return path.relative_to(repo_root)
    except ValueError:
        return path


def _m365_release_gate_run_readiness_output_path(
    repo_root: Path,
    args: argparse.Namespace,
    release_gate_run_artifact_dir: Path,
) -> Path:
    if args.release_gate_readiness_output:
        return _resolve_m365_release_gate_path(repo_root, args.release_gate_readiness_output, DEFAULT_RELEASE_READINESS_OUTPUT)
    return release_gate_run_artifact_dir / "release-readiness.redacted.json"


def _m365_release_gate_run_readiness_command(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
    baseline_reference: str | None = None,
) -> str:
    audit_pack_dir = _m365_release_gate_run_readiness_audit_pack_dir(
        repo_root,
        args,
        correlation_id=correlation_id,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
        baseline_reference=baseline_reference,
    )
    output_path = args.release_gate_readiness_output or release_gate_run_artifact_dir / "release-readiness.redacted.json"
    retention_root = args.release_gate_retention_root or release_gate_run_artifact_dir.parent
    command = [
        "python3",
        "scripts/nac.py",
        "m365",
        "teams-sharepoint",
        "release-readiness",
        "--release-gate-retention-root",
        str(retention_root),
        "--release-gate-readiness-correlation-id",
        correlation_id,
        "--release-gate-readiness-output",
        str(output_path),
    ]
    if audit_pack_dir is not None:
        command.extend(["--release-gate-audit-pack-dir", str(audit_pack_dir)])
    if args.release_gate_readiness_require_audit_pack:
        command.append("--release-gate-readiness-require-audit-pack")
    command.extend(["--format", "json"])
    return shlex.join(command)


def _m365_release_gate_run_post_run_baseline_reference(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
) -> str | None:
    if args.release_gate_compare_left:
        return args.release_gate_compare_left
    if not args.release_gate_write_post_run_report:
        return None
    retention_args = _m365_release_gate_audit_pack_args(
        args,
        release_gate_retention_root=args.release_gate_retention_root or release_gate_run_artifact_dir.parent,
    )
    retention_payload = _list_m365_release_gate_retention(repo_root, retention_args)
    runs = retention_payload.get("runs") if isinstance(retention_payload.get("runs"), list) else []
    target_run = next((run for run in runs if run.get("correlation_id") == correlation_id), None)
    if target_run is None:
        return None
    baseline_run = _m365_release_gate_post_run_previous_baseline(runs, target_run)
    if baseline_run is None:
        return None
    baseline_correlation_id = baseline_run.get("correlation_id")
    return str(baseline_correlation_id) if baseline_correlation_id else None


def _write_m365_release_gate_run_post_run_report(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
    baseline_reference: str | None,
) -> dict[str, Any]:
    post_run_args = _m365_release_gate_run_post_run_report_args(
        repo_root,
        args,
        correlation_id=correlation_id,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
        baseline_reference=baseline_reference,
    )
    return _write_m365_release_gate_post_run_report(repo_root, post_run_args)


def _m365_release_gate_run_post_run_report_args(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
    baseline_reference: str | None,
) -> argparse.Namespace:
    audit_pack_dir = _m365_release_gate_run_post_run_report_audit_pack_dir(
        repo_root,
        args,
        correlation_id=correlation_id,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
        baseline_reference=baseline_reference,
    )
    return _m365_release_gate_audit_pack_args(
        args,
        release_gate_retention_root=args.release_gate_retention_root or release_gate_run_artifact_dir.parent,
        release_gate_readiness_correlation_id=correlation_id,
        release_gate_compare_left=args.release_gate_compare_left,
        release_gate_compare_right=correlation_id,
        release_gate_audit_pack_dir=audit_pack_dir,
    )


def _m365_release_gate_run_post_run_report_audit_pack_dir(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
    baseline_reference: str | None,
) -> Path | None:
    if args.release_gate_audit_pack_dir is not None:
        return args.release_gate_audit_pack_dir
    if not baseline_reference:
        return None
    audit_args = _m365_release_gate_run_audit_pack_args(
        args,
        correlation_id=correlation_id,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
        baseline_reference=baseline_reference,
    )
    pack_dir = _m365_release_gate_retention_audit_pack_dir(repo_root, audit_args)
    return _m365_release_gate_path_for_command(repo_root, pack_dir)


def _m365_release_gate_run_post_run_report_command(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    correlation_id: str,
    release_gate_run_artifact_dir: Path,
    baseline_reference: str | None,
) -> str:
    post_run_args = _m365_release_gate_run_post_run_report_args(
        repo_root,
        args,
        correlation_id=correlation_id,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
        baseline_reference=baseline_reference,
    )
    command = [
        "python3",
        "scripts/nac.py",
        "m365",
        "teams-sharepoint",
        "release-gate-post-run-report",
        "--release-gate-retention-root",
        str(post_run_args.release_gate_retention_root),
        "--release-gate-readiness-correlation-id",
        correlation_id,
    ]
    if args.release_gate_compare_left:
        command.extend(["--release-gate-compare-left", str(post_run_args.release_gate_compare_left)])
    if post_run_args.release_gate_audit_pack_dir is not None:
        command.extend(["--release-gate-audit-pack-dir", str(post_run_args.release_gate_audit_pack_dir)])
    if post_run_args.release_gate_post_run_report_output is not None:
        command.extend(["--release-gate-post-run-report-output", str(post_run_args.release_gate_post_run_report_output)])
    if post_run_args.release_gate_post_run_report_json_output is not None:
        command.extend(
            ["--release-gate-post-run-report-json-output", str(post_run_args.release_gate_post_run_report_json_output)]
        )
    if post_run_args.release_gate_github_comment_output is not None:
        command.extend(["--release-gate-github-comment-output", str(post_run_args.release_gate_github_comment_output)])
    command.extend(["--format", "json"])
    return shlex.join(command)


def _write_m365_release_gate_run_post_run_report_index(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    release_gate_run_artifact_dir: Path,
) -> dict[str, Any]:
    index_args = _m365_release_gate_run_post_run_report_index_args(
        args,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
    )
    return _write_m365_release_gate_post_run_report_index_artifact(repo_root, index_args)


def _m365_release_gate_run_post_run_report_index_args(
    args: argparse.Namespace,
    *,
    release_gate_run_artifact_dir: Path,
) -> argparse.Namespace:
    return _m365_release_gate_audit_pack_args(
        args,
        release_gate_post_run_report_root=args.release_gate_post_run_report_root
        or DEFAULT_RELEASE_GATE_POST_RUN_REPORT_ROOT,
        release_gate_retention_root=args.release_gate_retention_root or release_gate_run_artifact_dir.parent,
    )


def _m365_release_gate_run_post_run_report_index_command(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    release_gate_run_artifact_dir: Path,
) -> str:
    index_args = _m365_release_gate_run_post_run_report_index_args(
        args,
        release_gate_run_artifact_dir=release_gate_run_artifact_dir,
    )
    command = [
        "python3",
        "scripts/nac.py",
        "m365",
        "teams-sharepoint",
        "release-gate-post-run-report-index-artifact",
        "--release-gate-post-run-report-root",
        str(_resolve_m365_release_gate_path(repo_root, index_args.release_gate_post_run_report_root, DEFAULT_RELEASE_GATE_POST_RUN_REPORT_ROOT)),
    ]
    if index_args.release_gate_post_run_report_correlation_id:
        command.extend(
            [
                "--release-gate-post-run-report-correlation-id",
                str(index_args.release_gate_post_run_report_correlation_id),
            ]
        )
    if index_args.release_gate_post_run_report_baseline:
        command.extend(["--release-gate-post-run-report-baseline", str(index_args.release_gate_post_run_report_baseline)])
    if index_args.release_gate_post_run_report_status:
        command.extend(["--release-gate-post-run-report-status", str(index_args.release_gate_post_run_report_status)])
    if index_args.release_gate_post_run_report_query:
        command.extend(["--release-gate-post-run-report-query", str(index_args.release_gate_post_run_report_query)])
    if index_args.release_gate_post_run_report_index_output is not None:
        command.extend(
            ["--release-gate-post-run-report-index-output", str(index_args.release_gate_post_run_report_index_output)]
        )
    if index_args.release_gate_post_run_report_index_json_output is not None:
        command.extend(
            [
                "--release-gate-post-run-report-index-json-output",
                str(index_args.release_gate_post_run_report_index_json_output),
            ]
        )
    command.extend(["--format", "json"])
    return shlex.join(command)


def _m365_release_readiness_return_code(payload: dict[str, Any]) -> int:
    if payload["status"] == "PASSED":
        return 0
    return 2 if payload["status"] == "BLOCKED" else 1


def _m365_release_gate_audit_pack_args(args: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    values = vars(args).copy()
    values.update(overrides)
    return argparse.Namespace(**values)


def _m365_release_gate_audit_pack_status(
    retention_payload: dict[str, Any],
    compare_payload: dict[str, Any],
    compare_index_payload: dict[str, Any] | None,
) -> str:
    statuses = [retention_payload.get("status"), compare_payload.get("status")]
    if compare_index_payload is not None:
        statuses.append(compare_index_payload.get("status"))
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if any(status != "PASSED" for status in statuses):
        return "FAILED"
    return "PASSED"


def _m365_release_gate_audit_pack_artifact(artifact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    return {
        "id": artifact_id,
        "status": payload.get("status"),
        "schema_version": payload.get("schema_version"),
        "report_path": summary.get("report_path"),
        "json_path": summary.get("json_path"),
        "artifact_directory": summary.get("artifact_directory"),
        "privacy": {
            "source_artifacts_must_be_redacted": True,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }


def _m365_release_gate_audit_pack_step(step_id: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {"id": step_id, "status": "NOT_WRITTEN"}
    return {
        "id": step_id,
        "status": payload.get("status"),
        "errors": payload.get("errors", []),
    }


def _m365_release_gate_retention_audit_pack_dir(repo_root: Path, args: argparse.Namespace) -> Path:
    if args.release_gate_audit_pack_dir is not None:
        return _resolve_m365_release_gate_path(repo_root, args.release_gate_audit_pack_dir, DEFAULT_RELEASE_GATE_AUDIT_PACK_ROOT)
    slug = _m365_release_gate_retention_audit_pack_slug(args)
    return repo_root / DEFAULT_RELEASE_GATE_AUDIT_PACK_ROOT / slug


def _m365_release_gate_retention_audit_pack_slug(args: argparse.Namespace) -> str:
    parts = [
        f"left-{_safe_release_gate_slug(str(args.release_gate_compare_left or 'missing'), 72)}",
        f"right-{_safe_release_gate_slug(str(args.release_gate_compare_right or 'missing'), 72)}",
    ]
    if args.release_gate_compare_status:
        parts.append(f"status-{_safe_release_gate_slug(str(args.release_gate_compare_status), 48)}")
    if args.release_gate_compare_query:
        parts.append(f"query-{_safe_release_gate_slug(str(args.release_gate_compare_query), 72)}")
    return "__".join(parts)


def _m365_release_gate_audit_pack_compare_dir(pack_dir: Path, args: argparse.Namespace) -> Path:
    left = _safe_release_gate_slug(str(args.release_gate_compare_left or "left"), 72)
    right = _safe_release_gate_slug(str(args.release_gate_compare_right or "right"), 72)
    return pack_dir / "comparisons" / f"{left}__{right}"


def _m365_release_gate_retention_row(index_path: Path, retention_index: dict[str, Any]) -> dict[str, Any]:
    run_dir = index_path.parent
    evidence_path = run_dir / "release-gate-evidence.redacted.json"
    evidence_generated_at = _m365_release_gate_evidence_generated_at(evidence_path)
    artifacts = retention_index.get("artifacts") if isinstance(retention_index.get("artifacts"), list) else []
    copied_artifact_count = retention_index.get("copied_artifact_count")
    if not isinstance(copied_artifact_count, int):
        copied_artifact_count = sum(1 for artifact in artifacts if isinstance(artifact, dict) and artifact.get("status") == "COPIED")
    not_attached_artifact_count = sum(
        1 for artifact in artifacts if isinstance(artifact, dict) and artifact.get("status") == "NOT_ATTACHED"
    )
    return {
        "status": retention_index.get("status"),
        "workspace_id": retention_index.get("workspace_id"),
        "correlation_id": retention_index.get("correlation_id") or run_dir.name,
        "timestamp": evidence_generated_at or _mtime_utc(index_path),
        "evidence_generated_at": evidence_generated_at,
        "artifact_dir": retention_index.get("artifact_dir") or str(run_dir),
        "retention_index_path": str(index_path),
        "copied_artifact_count": copied_artifact_count,
        "not_attached_artifact_count": not_attached_artifact_count,
        "artifact_count": len(artifacts),
        "report_path": str(run_dir / "release-gate-evidence.redacted.md"),
        "evidence_json_path": str(evidence_path),
        "artifact_index_path": str(run_dir / "release-gate-artifact-index.redacted.json"),
        "privacy": {
            "source_artifacts_must_be_redacted": True,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }


def _m365_release_gate_evidence_generated_at(evidence_path: Path) -> str | None:
    if not evidence_path.exists():
        return None
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(evidence, dict):
        return None
    generated_at = evidence.get("generated_at")
    return generated_at if isinstance(generated_at, str) else None


def _compare_m365_release_gate_retention(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    retention_root = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_retention_root,
        DEFAULT_RELEASE_GATE_RUN_ARTIFACT_ROOT,
    )
    errors: list[str] = []
    try:
        left = _load_m365_release_gate_retention_compare_side(
            repo_root,
            retention_root,
            "left",
            args.release_gate_compare_left,
        )
        right = _load_m365_release_gate_retention_compare_side(
            repo_root,
            retention_root,
            "right",
            args.release_gate_compare_right,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(str(exc))
        return {
            "schema_version": "nac.m365-release-gate-retention-compare/v0.1",
            "status": "BLOCKED",
            "summary": {
                "retention_root": str(retention_root),
                "graph_requests_executed": False,
                "tenant_writes_executed": False,
                "tenant_deletes_executed": False,
                "stores_tokens_or_secrets": False,
                "reads_sharepoint_file_content": False,
            },
            "left": None,
            "right": None,
            "comparison": {},
            "errors": errors,
        }

    comparison = _m365_release_gate_retention_diff(left, right)
    return {
        "schema_version": "nac.m365-release-gate-retention-compare/v0.1",
        "status": "PASSED",
        "summary": {
            "retention_root": str(retention_root),
            "left_correlation_id": left["run"].get("correlation_id"),
            "right_correlation_id": right["run"].get("correlation_id"),
            "differences_found": comparison["difference_count"] > 0,
            "difference_count": comparison["difference_count"],
            "artifact_difference_count": comparison["artifacts"]["difference_count"],
            "missing_attachment_difference_count": comparison["missing_attachments"]["difference_count"],
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "left": left["run"],
        "right": right["run"],
        "comparison": comparison,
        "errors": [],
    }


def _write_m365_release_gate_retention_compare_artifact(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    payload = _compare_m365_release_gate_retention(repo_root, args)
    if payload["status"] != "PASSED":
        return {
            **payload,
            "schema_version": "nac.m365-release-gate-retention-compare-artifact/v0.1",
        }
    report_path, json_path = _m365_release_gate_retention_compare_artifact_paths(repo_root, args, payload)
    payload = {
        **payload,
        "schema_version": "nac.m365-release-gate-retention-compare-artifact/v0.1",
        "generated_at": _now_utc(),
    }
    payload["summary"] = {
        **payload["summary"],
        "artifact_directory": str(report_path.parent),
        "report_path": str(report_path),
        "json_path": str(json_path),
        "source_artifacts_must_be_redacted": True,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.write_text(_render_m365_release_gate_retention_compare_report(payload), encoding="utf-8")
    return payload


def _list_m365_release_gate_retention_compare_artifacts(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    compare_root = _resolve_m365_release_gate_path(
        repo_root,
        args.release_gate_compare_index_root,
        DEFAULT_RELEASE_GATE_COMPARE_ARTIFACT_ROOT,
    )
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if compare_root.exists():
        for json_path in sorted(compare_root.glob("*/release-gate-retention-compare.redacted.json")):
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("compare artifact root must be an object")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                errors.append(f"invalid compare artifact {json_path}: {exc}")
                continue
            row = _m365_release_gate_retention_compare_index_row(json_path, payload)
            if _m365_release_gate_retention_compare_index_matches(row, args):
                rows.append(row)
    rows.sort(
        key=lambda row: (
            str(row.get("generated_at") or ""),
            str(row.get("left_correlation_id") or ""),
            str(row.get("right_correlation_id") or ""),
        ),
        reverse=True,
    )
    return {
        "schema_version": "nac.m365-release-gate-retention-compare-index/v0.1",
        "status": "FAILED" if errors else "PASSED",
        "summary": {
            "compare_root": str(compare_root),
            "comparison_count": len(rows),
            "invalid_artifact_count": len(errors),
            "left_correlation_id": args.release_gate_compare_left,
            "right_correlation_id": args.release_gate_compare_right,
            "status_filter": args.release_gate_compare_status,
            "query": args.release_gate_compare_query,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "comparisons": rows,
        "errors": errors,
    }


def _write_m365_release_gate_retention_compare_index_artifact(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    payload = _list_m365_release_gate_retention_compare_artifacts(repo_root, args)
    if payload["status"] != "PASSED":
        return {
            **payload,
            "schema_version": "nac.m365-release-gate-retention-compare-index-artifact/v0.1",
        }
    report_path, json_path = _m365_release_gate_retention_compare_index_artifact_paths(repo_root, args, payload)
    payload = {
        **payload,
        "schema_version": "nac.m365-release-gate-retention-compare-index-artifact/v0.1",
        "generated_at": _now_utc(),
    }
    payload["summary"] = {
        **payload["summary"],
        "artifact_directory": str(report_path.parent),
        "report_path": str(report_path),
        "json_path": str(json_path),
        "source_artifacts_must_be_redacted": True,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.write_text(_render_m365_release_gate_retention_compare_index_report(payload), encoding="utf-8")
    return payload


def _m365_release_gate_retention_compare_index_row(json_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    report_path = summary.get("report_path") or str(json_path.parent / "release-gate-retention-compare.redacted.md")
    json_output_path = summary.get("json_path") or str(json_path)
    row = {
        "status": payload.get("status"),
        "generated_at": payload.get("generated_at"),
        "left_correlation_id": summary.get("left_correlation_id"),
        "right_correlation_id": summary.get("right_correlation_id"),
        "differences_found": summary.get("differences_found"),
        "difference_count": summary.get("difference_count"),
        "artifact_difference_count": summary.get("artifact_difference_count"),
        "missing_attachment_difference_count": summary.get("missing_attachment_difference_count"),
        "artifact_directory": summary.get("artifact_directory") or str(json_path.parent),
        "report_path": report_path,
        "json_path": json_output_path,
        "source_json_path": str(json_path),
        "search_fields": {
            "left_correlation_id": summary.get("left_correlation_id"),
            "right_correlation_id": summary.get("right_correlation_id"),
            "generated_at": payload.get("generated_at"),
            "status": payload.get("status"),
            "report_path": report_path,
            "json_path": json_output_path,
        },
        "privacy": {
            "source_artifacts_must_be_redacted": True,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }
    return row


def _m365_release_gate_retention_compare_index_matches(row: dict[str, Any], args: argparse.Namespace) -> bool:
    if args.release_gate_compare_left and row.get("left_correlation_id") != args.release_gate_compare_left:
        return False
    if args.release_gate_compare_right and row.get("right_correlation_id") != args.release_gate_compare_right:
        return False
    if args.release_gate_compare_status and row.get("status") != args.release_gate_compare_status:
        return False
    query = args.release_gate_compare_query
    if query:
        haystack = " ".join(str(value or "") for value in row.get("search_fields", {}).values()).lower()
        return query.lower() in haystack
    return True


def _m365_release_gate_retention_compare_index_artifact_paths(
    repo_root: Path,
    args: argparse.Namespace,
    payload: dict[str, Any],
) -> tuple[Path, Path]:
    summary = payload.get("summary", {})
    slug = _m365_release_gate_retention_compare_index_artifact_slug(summary)
    default_dir = DEFAULT_RELEASE_GATE_COMPARE_INDEX_ARTIFACT_ROOT / slug
    default_report = default_dir / "release-gate-retention-compare-index.redacted.md"
    default_json = default_dir / "release-gate-retention-compare-index.redacted.json"
    report_path = _resolve_m365_release_gate_path(repo_root, args.release_gate_compare_index_output, default_report)
    json_path = _resolve_m365_release_gate_path(repo_root, args.release_gate_compare_index_json_output, default_json)
    return report_path, json_path


def _m365_release_gate_retention_compare_index_artifact_slug(summary: dict[str, Any]) -> str:
    parts: list[str] = []
    filters = [
        ("left", summary.get("left_correlation_id")),
        ("right", summary.get("right_correlation_id")),
        ("status", summary.get("status_filter")),
        ("query", summary.get("query")),
    ]
    for label, value in filters:
        if value:
            parts.append(f"{label}-{_safe_release_gate_slug(str(value), 72)}")
    return "__".join(parts) if parts else "all"


def _render_m365_release_gate_retention_compare_index_report(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    lines = [
        "# M365 Release Gate Retention Compare Index",
        "",
        f"Status: {payload.get('status')}",
        f"Generated at: {payload.get('generated_at')}",
        f"Compare root: {summary.get('compare_root')}",
        f"Comparison count: {summary.get('comparison_count')}",
        f"Invalid artifact count: {summary.get('invalid_artifact_count')}",
        "",
        "## Filters",
        "",
        f"- Left correlation ID: {_md_cell(summary.get('left_correlation_id')) or 'none'}",
        f"- Right correlation ID: {_md_cell(summary.get('right_correlation_id')) or 'none'}",
        f"- Status: {_md_cell(summary.get('status_filter')) or 'none'}",
        f"- Query: {_md_cell(summary.get('query')) or 'none'}",
        "",
        "## Privacy",
        "",
        "- Graph requests executed: false",
        "- Tenant writes executed: false",
        "- Tenant deletes executed: false",
        "- Stores tokens or secrets: false",
        "- Reads SharePoint file content: false",
        "",
        "## Comparisons",
        "",
    ]
    comparisons = payload.get("comparisons", [])
    if comparisons:
        lines.extend(
            [
                "| Generated at | Left | Right | Status | Differences | Report | JSON |",
                "| --- | --- | --- | --- | ---: | --- | --- |",
            ]
        )
        lines.extend(_m365_release_gate_retention_compare_index_markdown_row(row) for row in comparisons)
    else:
        lines.append("No comparison evidence artifacts matched the selected filters.")
    errors = payload.get("errors", [])
    if errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {_md_cell(error)}" for error in errors)
    lines.append("")
    return "\n".join(lines)


def _m365_release_gate_retention_compare_index_markdown_row(row: dict[str, Any]) -> str:
    return (
        f"| {_md_cell(row.get('generated_at'))} | {_md_cell(row.get('left_correlation_id'))} | "
        f"{_md_cell(row.get('right_correlation_id'))} | {_md_cell(row.get('status'))} | "
        f"{_md_cell(row.get('difference_count'))} | `{_md_cell(row.get('report_path'))}` | "
        f"`{_md_cell(row.get('json_path'))}` |"
    )


def _render_m365_release_gate_retention_list_report(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    lines = [
        "# M365 Release Gate Retention List",
        "",
        f"Status: {payload.get('status')}",
        f"Generated at: {payload.get('generated_at')}",
        f"Retention root: {summary.get('retention_root')}",
        f"Run count: {summary.get('run_count')}",
        f"Invalid run count: {summary.get('invalid_run_count')}",
        f"Latest timestamp: {summary.get('latest_timestamp')}",
        "",
        "## Privacy",
        "",
        "- Graph requests executed: false",
        "- Tenant writes executed: false",
        "- Tenant deletes executed: false",
        "- Stores tokens or secrets: false",
        "- Reads SharePoint file content: false",
        "",
        "## Runs",
        "",
    ]
    runs = payload.get("runs", [])
    if runs:
        lines.extend(
            [
                "| Timestamp | Correlation ID | Status | Workspace | Retained | Missing attachments | Retention index |",
                "| --- | --- | --- | --- | ---: | ---: | --- |",
            ]
        )
        lines.extend(_m365_release_gate_retention_list_markdown_row(run) for run in runs)
    else:
        lines.append("No release-gate retention runs were found.")
    errors = payload.get("errors", [])
    if errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {_md_cell(error)}" for error in errors)
    lines.append("")
    return "\n".join(lines)


def _m365_release_gate_retention_list_markdown_row(run: dict[str, Any]) -> str:
    return (
        f"| {_md_cell(run.get('timestamp'))} | {_md_cell(run.get('correlation_id'))} | "
        f"{_md_cell(run.get('status'))} | {_md_cell(run.get('workspace_id'))} | "
        f"{_md_cell(run.get('copied_artifact_count'))} | {_md_cell(run.get('not_attached_artifact_count'))} | "
        f"`{_md_cell(run.get('retention_index_path'))}` |"
    )


def _render_m365_release_gate_retention_audit_pack_report(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    lines = [
        "# M365 Release Gate Retention Audit Pack",
        "",
        f"Status: {payload.get('status')}",
        f"Generated at: {payload.get('generated_at')}",
        f"Pack directory: {summary.get('pack_dir')}",
        f"Retention root: {summary.get('retention_root')}",
        f"Compare root: {summary.get('compare_root')}",
        "",
        "## Scope",
        "",
        f"- Left correlation ID: {_md_cell(summary.get('left_correlation_id')) or 'none'}",
        f"- Right correlation ID: {_md_cell(summary.get('right_correlation_id')) or 'none'}",
        f"- Status filter: {_md_cell(summary.get('status_filter')) or 'none'}",
        f"- Query: {_md_cell(summary.get('query')) or 'none'}",
        "",
        "## Privacy",
        "",
        "- Graph requests executed: false",
        "- Tenant writes executed: false",
        "- Tenant deletes executed: false",
        "- Stores tokens or secrets: false",
        "- Reads SharePoint file content: false",
        "",
        "## Artifacts",
        "",
        "| Artifact | Status | Report | JSON |",
        "| --- | --- | --- | --- |",
    ]
    for artifact in payload.get("artifacts", []):
        lines.append(
            f"| {_md_cell(artifact.get('id'))} | {_md_cell(artifact.get('status'))} | "
            f"`{_md_cell(artifact.get('report_path'))}` | `{_md_cell(artifact.get('json_path'))}` |"
        )
    lines.extend(["", "## Steps", "", "| Step | Status | Errors |", "| --- | --- | --- |"])
    for step in payload.get("steps", []):
        lines.append(
            f"| {_md_cell(step.get('id'))} | {_md_cell(step.get('status'))} | "
            f"{_md_cell(', '.join(step.get('errors') or []))} |"
        )
    errors = payload.get("errors", [])
    if errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {_md_cell(error)}" for error in errors)
    lines.append("")
    return "\n".join(lines)


def _m365_release_gate_retention_compare_artifact_paths(
    repo_root: Path,
    args: argparse.Namespace,
    payload: dict[str, Any],
) -> tuple[Path, Path]:
    summary = payload.get("summary", {})
    left = _safe_release_gate_correlation_id(str(summary.get("left_correlation_id") or "left"))
    right = _safe_release_gate_correlation_id(str(summary.get("right_correlation_id") or "right"))
    default_dir = DEFAULT_RELEASE_GATE_COMPARE_ARTIFACT_ROOT / f"{left}__{right}"
    default_report = default_dir / "release-gate-retention-compare.redacted.md"
    default_json = default_dir / "release-gate-retention-compare.redacted.json"
    report_path = _resolve_m365_release_gate_path(repo_root, args.release_gate_compare_output, default_report)
    json_path = _resolve_m365_release_gate_path(repo_root, args.release_gate_compare_json_output, default_json)
    return report_path, json_path


def _render_m365_release_gate_retention_compare_report(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    comparison = payload.get("comparison", {})
    artifacts = comparison.get("artifacts", {})
    missing = comparison.get("missing_attachments", {})
    lines = [
        "# M365 Release Gate Retention Compare",
        "",
        f"Status: {payload.get('status')}",
        f"Generated at: {payload.get('generated_at')}",
        f"Left correlation ID: {summary.get('left_correlation_id')}",
        f"Right correlation ID: {summary.get('right_correlation_id')}",
        f"Differences found: {summary.get('differences_found')}",
        f"Difference count: {summary.get('difference_count')}",
        "",
        "## Privacy",
        "",
        "- Graph requests executed: false",
        "- Tenant writes executed: false",
        "- Tenant deletes executed: false",
        "- Stores tokens or secrets: false",
        "- Reads SharePoint file content: false",
        "",
        "## Runs",
        "",
        "| Side | Status | Workspace | Timestamp | Retained | Missing attachments |",
        "| --- | --- | --- | --- | ---: | ---: |",
        _m365_release_gate_retention_run_markdown_row("Left", payload.get("left") or {}),
        _m365_release_gate_retention_run_markdown_row("Right", payload.get("right") or {}),
        "",
        "## Field Differences",
        "",
    ]
    field_diffs = comparison.get("fields", [])
    if field_diffs:
        lines.extend(["| Field | Left | Right |", "| --- | --- | --- |"])
        lines.extend(
            f"| {item.get('field')} | {_md_cell(item.get('left'))} | {_md_cell(item.get('right'))} |"
            for item in field_diffs
        )
    else:
        lines.append("No field differences.")
    lines.extend(["", "## Artifact Differences", ""])
    lines.append(f"Added in right: {', '.join(artifacts.get('added_in_right') or []) or 'none'}")
    lines.append(f"Removed in right: {', '.join(artifacts.get('removed_in_right') or []) or 'none'}")
    changed = artifacts.get("changed", [])
    if changed:
        lines.extend(["", "| Artifact | Changed fields |", "| --- | --- |"])
        lines.extend(
            f"| {item.get('id')} | {', '.join(item.get('changed_fields') or [])} |"
            for item in changed
        )
    else:
        lines.append("Changed artifacts: none")
    lines.extend(
        [
            "",
            "## Missing Attachments",
            "",
            f"Left missing: {', '.join(missing.get('left_missing') or []) or 'none'}",
            f"Right missing: {', '.join(missing.get('right_missing') or []) or 'none'}",
            f"Resolved in right: {', '.join(missing.get('resolved_in_right') or []) or 'none'}",
            f"Newly missing in right: {', '.join(missing.get('newly_missing_in_right') or []) or 'none'}",
            "",
            "## Evidence Paths",
            "",
        ]
    )
    path_diffs = comparison.get("evidence_paths", {}).get("differences", [])
    if path_diffs:
        lines.extend(["| Field | Left | Right |", "| --- | --- | --- |"])
        lines.extend(
            f"| {item.get('field')} | `{_md_cell(item.get('left'))}` | `{_md_cell(item.get('right'))}` |"
            for item in path_diffs
        )
    else:
        lines.append("No evidence path differences.")
    lines.append("")
    return "\n".join(lines)


def _m365_release_gate_retention_run_markdown_row(side: str, run: dict[str, Any]) -> str:
    return (
        f"| {side} | {_md_cell(run.get('status'))} | {_md_cell(run.get('workspace_id'))} | "
        f"{_md_cell(run.get('timestamp'))} | {_md_cell(run.get('copied_artifact_count'))} | "
        f"{_md_cell(run.get('not_attached_artifact_count'))} |"
    )


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|") if value is not None else ""


def _now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_m365_release_gate_retention_compare_side(
    repo_root: Path,
    retention_root: Path,
    label: str,
    reference: str | None,
) -> dict[str, Any]:
    if not reference:
        raise ValueError(f"{label} release gate reference is required")
    index_path = _resolve_m365_release_gate_retention_reference(repo_root, retention_root, reference)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} retention index root must be an object: {index_path}")
    return {
        "index_path": index_path,
        "run": _m365_release_gate_retention_row(index_path, payload),
        "artifacts": _m365_release_gate_retention_artifacts_by_id(payload),
    }


def _resolve_m365_release_gate_retention_reference(repo_root: Path, retention_root: Path, reference: str) -> Path:
    ref_path = Path(reference)
    candidates: list[Path] = []
    if ref_path.is_absolute():
        candidates.append(ref_path)
    else:
        candidates.append(repo_root / ref_path)
        candidates.append(retention_root / _safe_release_gate_correlation_id(reference))
    for candidate in candidates:
        index_path = candidate / "release-gate-retention-index.redacted.json" if candidate.is_dir() else candidate
        if index_path.exists():
            return index_path
    fallback = retention_root / _safe_release_gate_correlation_id(reference) / "release-gate-retention-index.redacted.json"
    raise FileNotFoundError(f"release gate retention index not found for {reference!r}: {fallback}")


def _m365_release_gate_retention_artifacts_by_id(retention_index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = retention_index.get("artifacts") if isinstance(retention_index.get("artifacts"), list) else []
    result: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        artifact_id = artifact.get("id")
        if isinstance(artifact_id, str):
            result[artifact_id] = {
                "id": artifact_id,
                "status": artifact.get("status"),
                "artifact_sha256": artifact.get("artifact_sha256"),
                "source_path": artifact.get("source_path"),
                "retained_path": artifact.get("retained_path"),
            }
    return result


def _m365_release_gate_retention_diff(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_run = left["run"]
    right_run = right["run"]
    fields = _m365_release_gate_retention_field_diffs(left_run, right_run)
    paths = _m365_release_gate_retention_path_diffs(left_run, right_run)
    artifacts = _m365_release_gate_retention_artifact_diffs(left["artifacts"], right["artifacts"])
    missing = _m365_release_gate_retention_missing_attachment_diffs(left["artifacts"], right["artifacts"])
    difference_count = len(fields) + len(paths) + artifacts["difference_count"] + missing["difference_count"]
    return {
        "difference_count": difference_count,
        "fields": fields,
        "evidence_paths": {
            "difference_count": len(paths),
            "differences": paths,
        },
        "artifacts": artifacts,
        "missing_attachments": missing,
        "privacy": {
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }


def _m365_release_gate_retention_field_diffs(left_run: dict[str, Any], right_run: dict[str, Any]) -> list[dict[str, Any]]:
    fields = [
        "status",
        "workspace_id",
        "timestamp",
        "copied_artifact_count",
        "not_attached_artifact_count",
        "artifact_count",
    ]
    return [
        {"field": field, "left": left_run.get(field), "right": right_run.get(field)}
        for field in fields
        if left_run.get(field) != right_run.get(field)
    ]


def _m365_release_gate_retention_path_diffs(left_run: dict[str, Any], right_run: dict[str, Any]) -> list[dict[str, Any]]:
    fields = ["retention_index_path", "report_path", "evidence_json_path", "artifact_index_path"]
    return [
        {"field": field, "left": left_run.get(field), "right": right_run.get(field)}
        for field in fields
        if left_run.get(field) != right_run.get(field)
    ]


def _m365_release_gate_retention_artifact_diffs(
    left_artifacts: dict[str, dict[str, Any]],
    right_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    left_ids = set(left_artifacts)
    right_ids = set(right_artifacts)
    changed: list[dict[str, Any]] = []
    for artifact_id in sorted(left_ids & right_ids):
        left = left_artifacts[artifact_id]
        right = right_artifacts[artifact_id]
        changed_fields = [
            field for field in ("status", "artifact_sha256") if left.get(field) != right.get(field)
        ]
        if changed_fields:
            changed.append(
                {
                    "id": artifact_id,
                    "changed_fields": changed_fields,
                    "left": {field: left.get(field) for field in changed_fields},
                    "right": {field: right.get(field) for field in changed_fields},
                }
            )
    return {
        "difference_count": len(left_ids - right_ids) + len(right_ids - left_ids) + len(changed),
        "added_in_right": sorted(right_ids - left_ids),
        "removed_in_right": sorted(left_ids - right_ids),
        "changed": changed,
    }


def _m365_release_gate_retention_missing_attachment_diffs(
    left_artifacts: dict[str, dict[str, Any]],
    right_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    left_missing = {artifact_id for artifact_id, artifact in left_artifacts.items() if artifact.get("status") == "NOT_ATTACHED"}
    right_missing = {artifact_id for artifact_id, artifact in right_artifacts.items() if artifact.get("status") == "NOT_ATTACHED"}
    return {
        "difference_count": len(left_missing ^ right_missing),
        "left_missing": sorted(left_missing),
        "right_missing": sorted(right_missing),
        "resolved_in_right": sorted(left_missing - right_missing),
        "newly_missing_in_right": sorted(right_missing - left_missing),
    }


def _print_m365_release_gate_retention_compare(payload: dict[str, Any]) -> None:
    print(f"STATUS: {payload['status']}")
    if payload["status"] != "PASSED":
        for error in payload.get("errors", []):
            print(f"ERROR: {error}")
        return
    summary = payload.get("summary", {})
    print(f"Left: {summary.get('left_correlation_id')}")
    print(f"Right: {summary.get('right_correlation_id')}")
    print(f"Differences: {summary.get('difference_count')}")
    comparison = payload.get("comparison", {})
    for field in comparison.get("fields", []):
        print(f"- field {field['field']}: {field.get('left')} -> {field.get('right')}")
    artifacts = comparison.get("artifacts", {})
    for artifact_id in artifacts.get("added_in_right", []):
        print(f"- artifact added in right: {artifact_id}")
    for artifact_id in artifacts.get("removed_in_right", []):
        print(f"- artifact removed in right: {artifact_id}")
    for artifact in artifacts.get("changed", []):
        print(f"- artifact changed: {artifact['id']} fields={','.join(artifact.get('changed_fields', []))}")
    missing = comparison.get("missing_attachments", {})
    for artifact_id in missing.get("resolved_in_right", []):
        print(f"- missing attachment resolved in right: {artifact_id}")
    for artifact_id in missing.get("newly_missing_in_right", []):
        print(f"- missing attachment new in right: {artifact_id}")


def _print_m365_release_gate_retention_compare_artifact(payload: dict[str, Any]) -> None:
    _print_m365_release_gate_retention_compare(payload)
    summary = payload.get("summary", {})
    if payload["status"] == "PASSED":
        print(f"Report: {summary.get('report_path')}")
        print(f"JSON: {summary.get('json_path')}")


def _print_m365_release_gate_retention_compare_index(payload: dict[str, Any]) -> None:
    summary = payload.get("summary", {})
    print(f"STATUS: {payload['status']}")
    print(f"Compare root: {summary.get('compare_root')}")
    print(f"Comparisons: {summary.get('comparison_count')}")
    for row in payload.get("comparisons", []):
        print(
            "- "
            f"{row.get('generated_at') or 'unknown'} "
            f"{row.get('left_correlation_id') or 'unknown'} -> "
            f"{row.get('right_correlation_id') or 'unknown'} "
            f"status={row.get('status') or 'UNKNOWN'} "
            f"diffs={row.get('difference_count')} "
            f"report={row.get('report_path')}"
        )
    for error in payload.get("errors", []):
        print(f"ERROR: {error}")


def _print_m365_release_gate_retention_compare_index_artifact(payload: dict[str, Any]) -> None:
    _print_m365_release_gate_retention_compare_index(payload)
    summary = payload.get("summary", {})
    if payload["status"] == "PASSED":
        print(f"Report: {summary.get('report_path')}")
        print(f"JSON: {summary.get('json_path')}")


def _print_m365_release_gate_retention_audit_pack(payload: dict[str, Any]) -> None:
    summary = payload.get("summary", {})
    print(f"STATUS: {payload['status']}")
    print(f"Pack: {summary.get('pack_dir')}")
    print(f"Artifacts: {summary.get('artifact_count')}")
    for artifact in payload.get("artifacts", []):
        print(
            "- "
            f"{artifact.get('id')}: {artifact.get('status')} "
            f"report={artifact.get('report_path')} json={artifact.get('json_path')}"
        )
    for error in payload.get("errors", []):
        print(f"ERROR: {error}")


def _mtime_utc(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except OSError:
        return None


def _print_m365_release_gate_retention_list(payload: dict[str, Any]) -> None:
    summary = payload.get("summary", {})
    print(f"STATUS: {payload['status']}")
    print(f"Retention root: {summary.get('retention_root')}")
    print(f"Runs: {summary.get('run_count')}")
    for run in payload.get("runs", []):
        print(
            "- "
            f"{run.get('timestamp') or 'unknown'} "
            f"{run.get('correlation_id') or 'unknown'} "
            f"status={run.get('status') or 'UNKNOWN'} "
            f"retained={run.get('copied_artifact_count')} "
            f"index={run.get('retention_index_path')}"
        )
    for error in payload.get("errors", []):
        print(f"ERROR: {error}")


def _print_m365_release_readiness(payload: dict[str, Any]) -> None:
    summary = payload.get("summary", {})
    print(f"STATUS: {payload['status']}")
    print(f"MVP release readiness: {summary.get('mvp_release_readiness')}")
    print(f"Correlation: {summary.get('correlation_id')}")
    print(f"Workspace: {summary.get('workspace_id')}")
    print(f"Retained artifacts: {summary.get('retained_artifact_count')}/{summary.get('required_artifact_count')}")
    print(f"Evidence completeness: {summary.get('evidence_completeness')}")
    print(f"Retention index: {summary.get('retention_index_path')}")
    print(f"Evidence JSON: {summary.get('evidence_json_path')}")
    if summary.get("audit_pack_path"):
        print(f"Audit pack: {summary.get('audit_pack_status')} {summary.get('audit_pack_path')}")
    for check in payload.get("checks", []):
        if check.get("status") != "PASSED":
            print(f"- {check.get('id')}: {check.get('status')} {check.get('message')}")
    for error in payload.get("errors", []):
        print(f"ERROR: {error}")


def _refresh_m365_release_gate_evidence_with_retention(
    *,
    evidence_output: Path,
    evidence_json_output: Path,
    artifact_index_output: Path,
    retention_index: dict[str, Any],
) -> None:
    evidence = json.loads(evidence_json_output.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict):
        raise ValueError(f"invalid release gate evidence JSON: {evidence_json_output}")
    attach_release_gate_retention_reference(
        evidence,
        artifact_dir=str(retention_index["artifact_dir"]),
        retention_index_path=str(retention_index["index_path"]),
        copied_artifact_count=int(retention_index["copied_artifact_count"]),
    )
    write_release_gate_evidence_report(evidence, evidence_output)
    write_release_gate_evidence_json(evidence, evidence_json_output)
    write_release_gate_artifact_index(evidence["artifact_index"], artifact_index_output)


def _resolve_m365_release_gate_run_artifact_dir(
    repo_root: Path,
    artifact_dir: Path | None,
    correlation_id: str,
) -> Path:
    if artifact_dir is not None:
        return artifact_dir if artifact_dir.is_absolute() else repo_root / artifact_dir
    return repo_root / DEFAULT_RELEASE_GATE_RUN_ARTIFACT_ROOT / _safe_release_gate_correlation_id(correlation_id)


def _safe_release_gate_correlation_id(correlation_id: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_", "."} else "-" for char in correlation_id)
    cleaned = cleaned.strip("-_.")
    return cleaned or "m365-runtime-release-gate"


def _safe_release_gate_slug(value: str, max_length: int) -> str:
    cleaned = _safe_release_gate_correlation_id(value)
    shortened = cleaned[:max_length].rstrip("-_.")
    return shortened or "value"


def _retain_m365_release_gate_artifacts(
    *,
    artifact_dir: Path,
    workspace_id: str,
    correlation_id: str,
    status: str,
    artifacts: dict[str, Path],
) -> dict[str, Any]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    retained_artifacts: list[dict[str, Any]] = []
    for artifact_id, source_path in artifacts.items():
        retained_path = artifact_dir / source_path.name
        if source_path.exists():
            shutil.copy2(source_path, retained_path)
            retained_artifacts.append(
                {
                    "id": artifact_id,
                    "status": "COPIED",
                    "source_path": str(source_path),
                    "retained_path": str(retained_path),
                    "artifact_sha256": _sha256_file(retained_path),
                }
            )
        else:
            retained_artifacts.append(
                {
                    "id": artifact_id,
                    "status": "NOT_ATTACHED",
                    "source_path": str(source_path),
                    "retained_path": str(retained_path),
                    "artifact_sha256": None,
                }
            )
    copied_artifact_count = sum(1 for artifact in retained_artifacts if artifact["status"] == "COPIED")
    index = {
        "schema_version": "nac.m365-release-gate-retention-index/v0.1",
        "status": status,
        "workspace_id": workspace_id,
        "correlation_id": correlation_id,
        "artifact_dir": str(artifact_dir),
        "copied_artifact_count": copied_artifact_count,
        "artifacts": retained_artifacts,
        "privacy": {
            "source_artifacts_must_be_redacted": True,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }
    index_path = artifact_dir / "release-gate-retention-index.redacted.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "index_path": str(index_path),
        "artifact_dir": str(artifact_dir),
        "copied_artifact_count": copied_artifact_count,
    }


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _m365_runtime_env_overlay(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    output_path: Path,
) -> tuple[dict[str, str], dict[str, Any]]:
    runtime_state_path = _resolve_m365_release_gate_path(repo_root, args.runtime_smoke_state, DEFAULT_RUNTIME_SMOKE_STATE)
    certificate_path = args.runtime_certificate_path or DEFAULT_RUNTIME_CERTIFICATE_PATH
    private_key_path = args.runtime_private_key_path or DEFAULT_RUNTIME_PRIVATE_KEY_PATH
    try:
        runtime_state = load_runtime_env_state(runtime_state_path)
        bootstrap = build_runtime_env_bootstrap(
            runtime_state,
            certificate_path=certificate_path,
            private_key_path=private_key_path,
        )
        bootstrap.readiness["summary"]["artifact_path"] = str(output_path)
        write_runtime_env_bootstrap_artifact(bootstrap.readiness, output_path)
        return bootstrap.env_overlay, {
            "status": bootstrap.readiness["status"],
            "artifact_path": str(output_path),
            "env_overlay_variable_names": bootstrap.readiness["summary"]["env_overlay_variable_names"],
            "errors": _runtime_env_bootstrap_messages(bootstrap.readiness),
        }
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {}, {
            "status": "BLOCKED",
            "artifact_path": str(output_path),
            "env_overlay_variable_names": [],
            "errors": [str(exc)],
        }


def _runtime_env_bootstrap_messages(readiness: dict[str, Any]) -> list[str]:
    errors = readiness.get("errors")
    if isinstance(errors, list) and errors:
        return [str(error) for error in errors]
    messages: list[str] = []
    for check in readiness.get("checks", []):
        if isinstance(check, dict) and check.get("status") == "REVIEW_REQUIRED":
            messages.append(str(check.get("message", "runtime env bootstrap requires review")))
    return messages or ["runtime env bootstrap did not pass"]


def _run_nac_json_step(
    repo_root: Path,
    command: list[str],
    *,
    env_overlay: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = None
    if env_overlay:
        env = dict(os.environ)
        env.update(env_overlay)
    return subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "nac.py"), "--repo-root", str(repo_root), *command],
        cwd=repo_root,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def _payload_status(stdout: str) -> str | None:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    status = payload.get("status") if isinstance(payload, dict) else None
    return status if isinstance(status, str) else None


def _step_error_message(result: subprocess.CompletedProcess[str]) -> str:
    if result.stdout:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                return str(errors[0])
    if result.stderr:
        return result.stderr.strip()
    return f"release-gate step failed with return code {result.returncode}"


def _resolve_m365_release_gate_path(repo_root: Path, path: Path | None, default: Path) -> Path:
    raw = path or default
    return raw if raw.is_absolute() else repo_root / raw


def _print_m365_release_gate_run(payload: dict[str, Any]) -> None:
    summary = payload.get("summary", {})
    print(f"STATUS: {payload['status']}")
    print(f"Workspace: {summary.get('workspace_id')}")
    print(f"Correlation: {summary.get('correlation_id')}")
    for step in payload.get("steps", []):
        print(f"- {step['step']}: {step.get('status')} ({step.get('return_code')})")
    for error in payload.get("errors", []):
        print(f"ERROR: {error}")


def _print_release_gate_evidence(evidence: dict[str, Any]) -> None:
    summary = evidence.get("summary", {})
    print(f"STATUS: {evidence['status']}")
    print(f"Report: {summary.get('report_path')}")
    print(f"JSON: {summary.get('json_path')}")
    print(f"Artifact index: {summary.get('artifact_index_path')}")
    print(f"Evidence completeness: {summary.get('evidence_completeness')}")
    for step in evidence.get("steps", []):
        print(f"- {step['label']}: {step['status']}")
    for error in evidence.get("errors", []):
        print(f"ERROR: {error}")


def command_import(args: argparse.Namespace) -> int:
    try:
        if args.import_command == "jobs":
            if args.jobs_command == "create":
                payload = create_import_job(
                    args.repo,
                    proposal_id=args.proposal_id,
                    requested_by=args.requested_by,
                    action=args.action,
                )
                if args.format == "json":
                    print_json(payload)
                    return 0
                print("NaC-Import-Job angelegt")
                print(f"- Job: {payload['job_id']}")
                print(f"- Vorschlag: {payload['proposal_id']}")
                print(f"- Status: {payload['status']}")
                return 0

            if args.jobs_command == "status":
                payload = import_job_status(args.repo, job_id=args.job_id)
                if args.format == "json":
                    print_json(payload)
                    return 0
                print("NaC-Import-Jobs")
                print(f"- Repo: {payload['repo']}")
                print(f"- Gesamt: {payload['counts']['total']}")
                for job in payload["jobs"]:
                    extraction = job.get("extraction") if isinstance(job.get("extraction"), dict) else {}
                    suffix = f" · Extraktion: {extraction.get('status')}" if extraction else ""
                    print(f"- {job['job_id']}: {job['status']} ({job['proposal_id']}){suffix}")
                return 0

            if args.jobs_command == "process":
                payload = process_import_job(args.repo, job_id=args.job_id, processed_by=args.processed_by)
                if args.format == "json":
                    print_json(payload)
                    return 0
                print("NaC-Import-Job verarbeitet")
                print(f"- Job: {payload['job']['job_id']}")
                print(f"- Status: {payload['job']['status']}")
                print(f"- Extraktion: {payload['extraction']['status']}")
                return 0

            if args.jobs_command == "apply-result":
                payload = apply_import_job_result(args.repo, job_id=args.job_id, applied_by=args.applied_by)
                if args.format == "json":
                    print_json(payload)
                    return 0
                print("NaC-Import-Extraktion übernommen")
                print(f"- Job: {payload['job']['job_id']}")
                print(f"- Vorschlag: {payload['proposal']['proposal_id']}")
                print(f"- Status: {payload['job']['status']}")
                return 0
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    raise AssertionError(f"Unknown import command: {args.import_command}")


def command_plugins(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    if args.plugins_command == "validate":
        return run_script(repo_root, "scripts/validate_plugins.py", [])

    if args.plugins_command == "install":
        script_args = ["--mode", args.mode]
        if args.target_root:
            script_args.extend(["--target-root", str(args.target_root)])
        if args.force:
            script_args.append("--force")
        return run_script(repo_root, "scripts/install_local_plugins.py", script_args)

    if args.plugins_command == "actions":
        actions = plugin_actions(repo_root)
        if args.format == "json":
            print_json({"schema_version": "nac.plugin-actions/v1", "actions": actions})
            return 0
        print("NaC-Plugin-Befehle")
        for action in actions:
            status = "ausführbar" if action["cli_status"] == "executable" else "geplant"
            print(f"- {action['command']}: {action['description']} ({status})")
        return 0

    if args.plugins_command == "status":
        plugins = plugin_status_entries(repo_root)
        if args.plugin:
            plugin = next((candidate for candidate in plugins if candidate["name"] == args.plugin), None)
            if plugin is None:
                print(f"Unbekannte NaC-Anbindung: {args.plugin}")
                print("Verfügbare Anbindungen:")
                for candidate in plugins:
                    print(f"- {candidate['name']}")
                return 1
            if args.format == "json":
                print_json({"schema_version": "nac.plugin-status/v1", "plugin": plugin})
                return 0
            print_plugin_status(plugin)
            return 0
        if args.format == "json":
            print_json({"schema_version": "nac.plugin-status/v1", "plugins": plugins})
            return 0
        print("NaC-Anbindungen")
        for plugin in plugins:
            print_plugin_status(plugin, prefix="- ")
        return 0

    if args.plugins_command == "card-readiness":
        return run_plugin_main(
            repo_root,
            "plugins/nac-cyberjack-rfid/scripts/check_readiness.py",
            [
                "--manual-card-present",
                args.manual_card_present,
                "--manual-rfid-off",
                args.manual_rfid_off,
                *optional_flag(args.json, "--json"),
                *optional_flag(args.probe_morris_api, "--probe-morris-api"),
                *optional_flag(args.strict, "--strict"),
                *optional_path("--output", args.output),
            ],
        )

    if args.plugins_command == "xnp-reader-prompt":
        return run_plugin_main(
            repo_root,
            "plugins/nac-bnotk-xnp/scripts/reader_prompt.py",
            [
                "--intent",
                args.intent,
                "--manual-card-present",
                args.manual_card_present,
                "--manual-rfid-off",
                args.manual_rfid_off,
                *optional_value("--prompt", args.prompt),
                *optional_flag(args.json, "--json"),
                *optional_flag(args.probe_morris_api, "--probe-morris-api"),
                *optional_flag(args.strict, "--strict"),
                *optional_path("--output", args.output),
            ],
        )

    if args.plugins_command == "xnp-workflow-gate":
        return run_plugin_main(
            repo_root,
            "plugins/nac-bnotk-xnp/scripts/workflow_gate.py",
            [
                "--usecase",
                args.usecase,
                "--intent",
                args.intent,
                "--manual-card-present",
                args.manual_card_present,
                "--manual-rfid-off",
                args.manual_rfid_off,
                *optional_path("--evidence", args.evidence),
                *optional_value("--prompt", args.prompt),
                *optional_flag(args.json, "--json"),
                *optional_flag(args.probe_morris_api, "--probe-morris-api"),
                *optional_flag(args.strict, "--strict"),
                *optional_path("--output", args.output),
            ],
        )

    if args.plugins_command == "pkcs7-inspect":
        return run_plugin_main(
            repo_root,
            "plugins/nac-pkcs7-certbundle/scripts/inspect_certbundle.py",
            [
                "--max-bytes",
                str(args.max_bytes),
                *optional_path("--input", args.input),
                *optional_flag(args.json, "--json"),
                *optional_flag(args.strict, "--strict"),
                *optional_path("--output", args.output),
            ],
        )

    raise AssertionError(f"Unknown plugin command: {args.plugins_command}")


def command_config(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    entries = discover_config_entries(repo_root)
    if args.config_command == "list":
        if args.format == "json":
            print_json({"configs": [asdict(entry) for entry in entries]})
            return 0
        print("NaC-Konfigurationen")
        current_group = ""
        for entry in entries:
            if entry.group != current_group:
                current_group = entry.group
                print(f"\n{current_group}")
            print(f"- {entry.id}: {entry.path} - {entry.description}")
        return 0

    if args.config_command == "show":
        entry = find_config_entry(repo_root, entries, args.id_or_path)
        if entry is None:
            print(f"ERROR: Konfiguration nicht gefunden: {args.id_or_path}")
            return 1
        print((repo_root / entry.path).read_text(encoding="utf-8"))
        return 0

    if args.config_command == "validate":
        checks = [
            "scripts/validate_governance_sync.py",
            "scripts/validate_language_parity.py",
            "scripts/validate_plugins.py",
            "scripts/validate_bpmn_models.py",
            "scripts/validate_kg_editor.py",
            "scripts/validate_gnotkg_costs.py",
            "scripts/validate_secure_document_links.py",
            "scripts/validate_legal_research_connectors.py",
        ]
        failed = False
        for script in checks:
            result = run_script(repo_root, script, [])
            if result != 0:
                failed = True
        return 1 if failed else 0

    raise AssertionError(f"Unknown config command: {args.config_command}")


def command_qms(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    try:
        if args.qms_command == "status":
            status = qms_status(repo_root, evidence_repo=args.repo)
            if args.format == "json":
                print_json(status.to_dict())
                return 0 if status.ok else 1
            print("NaC-QMS Status")
            print(f"- QMS-Artefakte: {sum(status.files_present.values())}/{len(status.files_present)}")
            print(f"- Qualitätsziele: {status.quality_objectives}")
            print(f"- Rollen: {status.raci_roles}")
            print(f"- ISO-9001-Mappingzeilen: {status.iso_mapping_rows}")
            if status.evidence_repo:
                print(f"- Nachweisrepo: {status.evidence_repo}")
                for key, value in status.evidence_counts.items():
                    print(f"- {key}: {value}")
            missing = [name for name, present in status.files_present.items() if not present]
            if missing:
                print("Fehlende Dateien")
                for name in missing:
                    print(f"- qms/{name}")
                return 1
            return 0

        if args.qms_command == "iso9001-map":
            print(read_qms_text(repo_root, "iso9001-mapping.md"))
            return 0

        if args.qms_command == "audit-plan":
            print(read_qms_text(repo_root, "audit-program.md"))
            return 0

        if args.qms_command == "evidence":
            status = qms_status(repo_root, evidence_repo=args.repo)
            if args.format == "json":
                print_json(status.to_dict())
                return 0 if status.ok else 1
            print("NaC-QMS Nachweisbild")
            print(f"- Datenrepo: {status.evidence_repo}")
            print(f"- Akten: {status.evidence_counts.get('matters', 0)}")
            print(f"- Personen: {status.evidence_counts.get('persons', 0)}")
            print(f"- Dokumente: {status.evidence_counts.get('documents', 0)}")
            print(f"- Legacy-Demo-Vorgänge: {status.evidence_counts.get('demo_cases', 0)}")
            return 0 if status.ok else 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    raise AssertionError(f"Unknown QMS command: {args.qms_command}")


def command_time_ledger(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    log_path = resolve_repo_path(repo_root, args.log)
    try:
        if args.time_ledger_command == "add":
            entry = build_entry(
                session_id=args.session_id,
                task=args.task,
                phase=args.phase,
                category=args.category,
                started_at=parse_timestamp(args.started_at),
                ended_at=parse_timestamp(args.ended_at),
                actor=args.actor,
                outcome=args.outcome,
                command=args.command,
                notes=args.notes,
            )
            append_entry(log_path, entry)
            if args.format == "json":
                print_json(entry)
                return 0
            print("NaC Codex Time Ledger")
            print(f"- Log: {log_path}")
            print(f"- Session: {entry['session_id']}")
            print(f"- Phase: {entry['phase']}")
            print(f"- Kategorie: {entry['category']}")
            print(f"- Dauer: {entry['duration_ms']} ms")
            return 0

        if args.time_ledger_command == "run":
            rc, entry = run_timed_command(
                log_path=log_path,
                session_id=args.session_id,
                task=args.task,
                phase=args.phase,
                category=args.category,
                command=args.child_command,
                cwd=repo_root,
                actor=args.actor,
                notes=args.notes,
            )
            payload = {**entry, "child_return_code": rc}
            if args.format == "json":
                print_json(payload)
            else:
                print("NaC Codex Time Ledger")
                print(f"- Log: {log_path}")
                print(f"- Session: {entry['session_id']}")
                print(f"- Phase: {entry['phase']}")
                print(f"- Kategorie: {entry['category']}")
                print(f"- Dauer: {entry['duration_ms']} ms")
                print(f"- Kindprozess: {rc}")
            return rc

        if args.time_ledger_command == "summary":
            summary = summarize_entries(load_entries(log_path), session_id=args.session_id)
            if args.format == "json":
                print_json(summary)
                return 0
            print(format_summary_text(summary))
            return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    raise AssertionError(f"Unknown time-ledger command: {args.time_ledger_command}")


def command_tenant(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    try:
        if args.tenant_command == "init":
            payload = init_tenant_repo(
                args.repo,
                name=args.name,
                mode=args.mode,
                remote_url=args.remote_url,
                force=args.force,
            )
            print("NaC-Datenrepo initialisiert")
            print(f"- Repo: {payload['repo']}")
            print(f"- Manifest: {payload['manifest']}")
            print(f"- Modus: {payload['mode']}")
            if payload["remote_origin"]:
                print(f"- Remote: {payload['remote_origin']}")
            return 0

        if args.tenant_command == "domain-check":
            payload = check_domain_ready(
                domain=args.domain,
                tenant_slug=args.tenant_slug,
                admin_email=args.admin_email,
            )
            if args.format == "json":
                print_json(payload)
                return 0 if payload["ready"] else 1
            print("NaC Tenant-Domain-Readiness")
            print(f"- Domain: {payload['domain']}")
            print(f"- Tenant: {payload['tenant_slug']}")
            print(f"- Status: {'bereit' if payload['ready'] else 'blockiert'}")
            print(f"- DNS-TXT: {payload['verification']['dns_record_name']}")
            print(f"- Wert: {payload['verification']['dns_record_value']}")
            for finding in payload["blocking_findings"]:
                print(f"- Blocker: {finding}")
            return 0 if payload["ready"] else 1

        if args.tenant_command == "customer-plan":
            payload = build_customer_tenant_plan(
                domain=args.domain,
                tenant_slug=args.tenant_slug,
                admin_email=args.admin_email,
                saas_admin_email=args.saas_admin_email,
            )
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC Customer-Tenant-Onboarding-Plan")
            print(f"- Tenant: {payload['tenant']['slug']}")
            print(f"- Domain: {payload['tenant']['domain']}")
            print(f"- Admin: {payload['admin_user']['email']}")
            print(f"- SaaS-Owner: {payload['saas_admin']['email']}")
            print(f"- Identity: {payload['m365']['identity']['provider']}")
            print(f"- Workspace: {payload['m365']['workspace']['strategy']}")
            print(f"- Datenhaltung: {payload['m365']['data_plane']['strategy']}")
            print("- Owner-Gate vor privilegierter Graph-Änderung: erforderlich")
            return 0

        if args.tenant_command == "dns-check":
            readiness = check_domain_ready(
                domain=args.domain,
                tenant_slug=args.tenant_slug,
                admin_email=args.admin_email,
            )
            verification = readiness["verification"]
            payload = build_live_dns_check_result(
                expected_name=verification["dns_record_name"],
                expected_value=verification["dns_record_value"],
            )
            if args.format == "json":
                print_json(payload)
                return 0 if payload["status"] == "verified" else 1
            print("NaC Live-DNS-Readiness")
            print(f"- DNS-TXT: {payload['expected']['name']}")
            print(f"- Erwarteter Wert: {payload['expected']['value']}")
            print(f"- Status: {payload['status']}")
            print(f"- Hinweis: {payload['customer_guidance']}")
            for finding in payload["findings"]:
                print(f"- Diagnose: {finding}")
            return 0 if payload["status"] == "verified" else 1

        if args.tenant_command == "status":
            status = tenant_status(args.repo)
            if args.format == "json":
                print_json(status.to_dict())
                return 0
            print("NaC-Datenrepo Status")
            print(f"- Repo: {status.repo}")
            print(f"- Manifest: {'ja' if status.manifest else 'nein'}")
            if status.manifest:
                print(f"- Name: {status.manifest.get('name')}")
                print(f"- Modus: {status.manifest.get('mode')}")
            print(f"- Git: {'ja' if status.git_present else 'nein'}")
            print(f"- Remote: {status.remote_origin or 'nicht gesetzt'}")
            print(f"- Demo-Vorgänge: {status.demo_cases}")
            print(f"- Akten: {status.matters}")
            print(f"- Personen: {status.persons}")
            print(f"- Dokumente: {status.documents}")
            return 0

        if args.tenant_command == "list-akten":
            summaries = list_matter_summaries(args.repo)
            if args.format == "json":
                print_json({"schema_version": "nac.tenant-matter-list/v1", "matters": summaries})
                return 0
            print("NaC-Aktenliste")
            if not summaries:
                print("- Keine Akten gefunden.")
                return 0
            for summary in summaries:
                next_task = summary["next_task"] or "kein offener Schritt"
                print(
                    f"- {summary['matter_id']} | {summary['aktenzeichen']} | "
                    f"{summary['title']} | Status: {summary['status']} | Nächster Schritt: {next_task}"
                )
            return 0

        if args.tenant_command == "show-akte":
            description = describe_matter(args.repo, args.akten_id)
            if args.format == "json":
                print_json({"schema_version": "nac.tenant-matter-description/v1", **description})
                return 0
            matter = description["matter"]
            side_file = matter.get("electronic_side_file") if isinstance(matter.get("electronic_side_file"), dict) else {}
            print("NaC-Akte")
            print(f"- Akte: {matter.get('matter_id')}")
            print(f"- Aktenzeichen: {matter.get('aktenzeichen')}")
            print(f"- Titel: {matter.get('title')}")
            print(f"- Status: {matter.get('status')}")
            print(f"- Beteiligte: {len(description['participants'])}")
            print(f"- Dokumente: {len(description['documents'])}")
            print(f"- Aufgaben: {len(description['tasks'])}")
            print(f"- Nachweise: {len(description['evidence'])}")
            if side_file.get("label"):
                print(f"- {side_file['label']}")
            return 0

        if args.tenant_command == "write-demo":
            payload = write_demo_case(
                nac_repo_root=repo_root,
                tenant_repo=args.repo,
                slug=args.slug,
                case_id=args.case_id,
                force=args.force,
            )
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC-Demo-Vorgang geschrieben")
            print(f"- Repo: {payload['repo']}")
            print(f"- Vorgang: {payload['case_id']}")
            print(f"- Datei: {payload['path']}")
            print(f"- Datenklasse: {payload['data_classification']}")
            return 0

        if args.tenant_command == "write-sample-akte":
            payload = write_sample_matter(
                tenant_repo=args.repo,
                matter_id=args.akten_id,
                force=args.force,
            )
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC-Musterakte geschrieben")
            print(f"- Repo: {payload['repo']}")
            print(f"- Akte: {payload['matter_id']}")
            print(f"- Datei: {payload['path']}")
            print(f"- Personen: {payload['person_count']}")
            print(f"- Dokumente: {payload['document_count']}")
            print(f"- Datenklasse: {payload['data_classification']}")
            return 0
    except (KeyError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}")
        return 1

    raise AssertionError(f"Unknown tenant command: {args.tenant_command}")


def resolve_repo_root(path: Path) -> Path:
    repo_root = path.expanduser().resolve()
    if not (repo_root / "pyproject.toml").is_file():
        raise SystemExit(f"ERROR: Kein NaC-Repository gefunden: {repo_root}")
    return repo_root


def resolve_repo_path(repo_root: Path, path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded
    return repo_root / expanded


def discover_config_entries(repo_root: Path) -> list[ConfigEntry]:
    entries: list[ConfigEntry] = []
    for path in sorted((repo_root / "policies").glob("*")):
        if path.suffix in {".yaml", ".yml", ".json"}:
            entries.append(
                ConfigEntry(
                    id=path.stem,
                    path=display_path(repo_root, path),
                    group="Policies",
                    description="Verbindliche Governance- oder Betriebsregel.",
                )
            )

    fixed = [
        (
            ".agents/plugins/marketplace.json",
            "Plugins",
            "Lokaler Plugin-Marktplatz für Codex-Erkennung.",
        ),
        ("bpmn/nac-moddle.json", "BPMN", "NaC-Erweiterungen für bpmn-js und BPMN-Modelle."),
        ("pyproject.toml", "Runtime", "Python-Paket, Einstiegspunkte und CLI-Befehle."),
    ]
    for rel_path, group, description in fixed:
        if (repo_root / rel_path).is_file():
            entries.append(ConfigEntry(id=Path(rel_path).stem, path=rel_path, group=group, description=description))

    for path in sorted((repo_root / "workflows" / "contracts").glob("*.json")):
        entries.append(
            ConfigEntry(
                id=path.stem,
                path=display_path(repo_root, path),
                group="Workflow-Verträge",
                description="Maschinenlesbarer Vertrag für Bedienung, Eingaben und Nachweise.",
            )
        )
    return sorted(entries, key=lambda item: (item.group, item.path))


def find_config_entry(repo_root: Path, entries: list[ConfigEntry], value: str) -> ConfigEntry | None:
    normalized = value.strip()
    for entry in entries:
        if normalized in {entry.id, entry.path}:
            return entry
    candidate = (repo_root / normalized).resolve()
    for entry in entries:
        if (repo_root / entry.path).resolve() == candidate:
            return entry
    return None


def run_script(repo_root: Path, script_path: str, args: list[str]) -> int:
    env = os.environ.copy()
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    return subprocess.call([sys.executable, str(repo_root / script_path), *args], cwd=repo_root, env=env)


def run_plugin_main(repo_root: Path, script_path: str, args: list[str]) -> int:
    absolute = repo_root / script_path
    spec = importlib.util.spec_from_file_location(f"nac_plugin_{absolute.stem}", absolute)
    if spec is None or spec.loader is None:
        print(f"ERROR: Plugin-Skript kann nicht geladen werden: {script_path}")
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    main = getattr(module, "main", None)
    if not callable(main):
        print(f"ERROR: Plugin-Skript hat keinen main(argv)-Einstieg: {script_path}")
        return 1
    previous_cwd = Path.cwd()
    try:
        os.chdir(repo_root)
        return int(main(args))
    finally:
        os.chdir(previous_cwd)


def optional_flag(enabled: bool, flag: str) -> list[str]:
    return [flag] if enabled else []


def optional_value(flag: str, value: str | None) -> list[str]:
    return [flag, value] if value is not None else []


def optional_path(flag: str, value: Path | None) -> list[str]:
    return [flag, str(value)] if value is not None else []


def plugin_actions(repo_root: Path) -> list[dict[str, str]]:
    actions = [
        {
            "plugin": plugin["name"],
            "command": plugin["command"],
            "description": plugin["description"],
            "cli_status": plugin["cli_status"],
        }
        for plugin in plugin_status_entries(repo_root)
    ]
    actions.extend(EXTRA_PLUGIN_ACTIONS)
    return actions


def plugin_status_entries(repo_root: Path) -> list[dict[str, Any]]:
    marketplace_path = repo_root / ".agents" / "plugins" / "marketplace.json"
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = []
    for entry in marketplace.get("plugins", []):
        name = str(entry.get("name", ""))
        source_path = str(entry.get("source", {}).get("path", f"./plugins/{name}"))
        plugin_root = repo_root / source_path.removeprefix("./")
        manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        interface = manifest.get("interface", {})
        executable = EXECUTABLE_PLUGIN_COMMANDS.get(name)
        command = executable["command"] if executable else f"nac plugins status {name}"
        description = executable["description"] if executable else str(interface.get("shortDescription") or manifest.get("description") or "")
        entries.append(
            {
                "name": name,
                "display_name": str(interface.get("displayName") or name),
                "description": description,
                "category": str(interface.get("category") or entry.get("category") or ""),
                "cli_status": "executable" if executable else "planned",
                "command": command,
                "plugin_role": PLUGIN_CLI_ROLES["plugin_role"],
                "cli_role": PLUGIN_CLI_ROLES["cli_role"],
                "plugin_path": source_path,
                "manifest_path": manifest_path.relative_to(repo_root).as_posix(),
            }
        )
    return entries


def print_plugin_status(plugin: dict[str, Any], prefix: str = "") -> None:
    status = "ausführbar" if plugin["cli_status"] == "executable" else "geplant"
    print(f"{prefix}NaC-Anbindung: {plugin['display_name']} ({plugin['name']})")
    print(f"{prefix}  CLI-Status: {status}")
    print(f"{prefix}  CLI-Befehl: {plugin['command']}")
    print(f"{prefix}  Plugin-Rolle: {plugin['plugin_role']}")
    print(f"{prefix}  CLI-Rolle: {plugin['cli_role']}")


def display_path(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def print_validation(errors: list[str], warnings: list[str]) -> None:
    if not errors and not warnings:
        print("OK")
        return
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
