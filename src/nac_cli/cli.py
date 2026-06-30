from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from business_os.engine import BusinessProcessEngine
from nac_gnotkg.costs import quote_fee
from nac_identity.customer_onboarding import build_customer_tenant_plan, build_live_dns_check_result
from nac_identity.oci_tenant import build_admin_provisioning_plan, build_apply_request, check_domain_ready
from nac_legal_graph.catalog import build_review_payload, legal_graph_status
from nac_legal_graph.patches import build_update_patch
from nac_legal_graph.sources import legal_graph_source_status, legal_source_inventory_status
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
    tenant_admin = tenant_sub.add_parser("provision-admin", help="Erzeugt einen OCI-Identity-Admin-Dry-run-Plan.")
    tenant_admin.add_argument("--tenant-slug", required=True, help="Stabiler Tenant-Slug.")
    tenant_admin.add_argument("--domain", required=True, help="Kundendomain.")
    tenant_admin.add_argument("--admin-email", required=True, help="Initiale Admin-E-Mail zur Kundendomain.")
    tenant_admin.add_argument("--admin-display-name", required=True, help="Anzeigename des initialen Tenant-Admins.")
    tenant_admin.add_argument("--identity-domain-url", required=True, help="OCI Identity Domain URL ohne /admin/v1.")
    tenant_admin.add_argument("--identity-domain-id", required=True, help="OCI Identity Domain OCID.")
    tenant_admin.add_argument("--dry-run", action="store_true", help="Pflicht: Nur Plan erzeugen, keine OCI-Schreiboperation.")
    tenant_admin.add_argument("--format", choices=["text", "json"], default="text")
    tenant_apply = tenant_sub.add_parser("apply-request", help="Erzeugt einen OCI-Identity-Apply-Readiness-Request.")
    tenant_apply.add_argument("--tenant-slug", required=True, help="Stabiler Tenant-Slug.")
    tenant_apply.add_argument("--domain", required=True, help="Kundendomain.")
    tenant_apply.add_argument("--admin-email", required=True, help="Initiale Admin-E-Mail zur Kundendomain.")
    tenant_apply.add_argument("--admin-display-name", required=True, help="Anzeigename des initialen Tenant-Admins.")
    tenant_apply.add_argument("--identity-domain-url", required=True, help="OCI Identity Domain URL ohne /admin/v1.")
    tenant_apply.add_argument("--identity-domain-id", required=True, help="OCI Identity Domain OCID.")
    tenant_apply.add_argument("--dns-verified", action="store_true", help="DNS-TXT-Domainverifikation wurde extern geprüft.")
    tenant_apply.add_argument("--owner-approval-id", default="", help="Owner-Apply-Freigabe-ID.")
    tenant_apply.add_argument("--audit-event-id", default="", help="Audit-Event-ID für die Apply-Absicht.")
    tenant_apply.add_argument("--rollback-plan-id", default="", help="Rollback-Plan-ID für späteren Connector-Apply.")
    tenant_apply.add_argument("--dry-run", action="store_true", help="Pflicht: Nur Review-Artefakt erzeugen.")
    tenant_apply.add_argument("--format", choices=["text", "json"], default="text")
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
            "bpmn_validate": "nac bpmn validate",
            "contracts_validate": "nac contracts validate",
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
            ("OCI Tenant Identity Contract", "validate_oci_tenant_identity.py"),
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

        if args.tenant_command == "provision-admin":
            if not args.dry_run:
                print("ERROR: OCI-Admin-Provisioning ist in diesem Track nur mit --dry-run zulässig.")
                return 1
            payload = build_admin_provisioning_plan(
                tenant_slug=args.tenant_slug,
                domain=args.domain,
                admin_email=args.admin_email,
                admin_display_name=args.admin_display_name,
                identity_domain_url=args.identity_domain_url,
                identity_domain_id=args.identity_domain_id,
            )
            if args.format == "json":
                print_json(payload)
                return 0
            print("OCI-Identity-Admin-Provisioning-Plan")
            print("- Modus: dry_run")
            print(f"- Tenant: {payload['tenant_slug']}")
            print(f"- Admin: {payload['admin_user']['user_name']}")
            print(f"- Benutzer-Endpunkt: {payload['target']['users_endpoint']}")
            print(f"- Gruppen-Endpunkt: {payload['target']['groups_endpoint']}")
            print("- Owner-Freigabe vor Apply: erforderlich")
            return 0

        if args.tenant_command == "apply-request":
            if not args.dry_run:
                print("ERROR: OCI-Apply-Requests sind in diesem Track nur mit --dry-run zulässig.")
                return 1
            plan = build_admin_provisioning_plan(
                tenant_slug=args.tenant_slug,
                domain=args.domain,
                admin_email=args.admin_email,
                admin_display_name=args.admin_display_name,
                identity_domain_url=args.identity_domain_url,
                identity_domain_id=args.identity_domain_id,
            )
            payload = build_apply_request(
                plan,
                dns_verified=args.dns_verified,
                owner_approval_id=args.owner_approval_id,
                audit_event_id=args.audit_event_id,
                rollback_plan_id=args.rollback_plan_id,
            )
            if args.format == "json":
                print_json(payload)
                return 0 if payload["ready_to_apply"] else 1
            print("OCI-Identity-Apply-Readiness")
            print("- Modus: review_artifact_only")
            print(f"- Tenant: {payload['tenant_slug']}")
            print(f"- Status: {'bereit' if payload['ready_to_apply'] else 'blockiert'}")
            print(f"- Owner-Approval: {payload['approval']['owner_approval_id'] or 'fehlt'}")
            print(f"- Audit-Event: {payload['audit']['audit_event_id'] or 'fehlt'}")
            print(f"- Rollback-Plan: {payload['rollback']['rollback_plan_id'] or 'fehlt'}")
            for finding in payload["blocking_findings"]:
                print(f"- Blocker: {finding}")
            return 0 if payload["ready_to_apply"] else 1

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
            print(f"- Identity: {payload['oci']['identity']['customer_domain_strategy']}")
            print(f"- Compartment: {payload['oci']['resource_isolation']['compartment_strategy']}")
            print(f"- ATP: {payload['atp']['strategy']}")
            print("- Owner-Apply vor OCI-Schreiboperation: erforderlich")
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
