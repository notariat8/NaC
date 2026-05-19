from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from business_os.engine import BusinessProcessEngine
from nac_web.bpmn import bpmn_model_json, find_bpmn_model, list_bpmn_models, render_bpmn_svg
from nac_web.server import run_server
from notary_kg.catalog import all_case_summaries, load_catalogs
from notary_kg.cli import main as notary_kg_main

from . import __version__
from .tenant import init_tenant_repo, tenant_status, write_demo_case, write_sample_matter


DEFAULT_PORT = 8765


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
    kg.set_defaults(func=command_kg)

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

    plugins = subparsers.add_parser("plugins", help="Steuert lokale NaC-Plugins.")
    plugins_sub = plugins.add_subparsers(dest="plugins_command", required=True)
    plugins_actions = plugins_sub.add_parser("actions", help="Listet fachliche Plugin-Befehle.")
    plugins_actions.add_argument("--format", choices=["text", "json"], default="text")
    plugins_install = plugins_sub.add_parser("install", help="Spiegelt repo-lokale Plugins.")
    plugins_install.add_argument("--mode", choices=["dry-run", "link", "copy"], default="dry-run")
    plugins_install.add_argument("--target-root", type=Path)
    plugins_install.add_argument("--force", action="store_true")
    plugins_sub.add_parser("validate", help="Validiert Plugin-Manifeste.")
    plugins_card = plugins_sub.add_parser("card-readiness", help="Prüft Karten-/SAK-Bereitschaft lokal.")
    add_card_readiness_args(plugins_card)
    plugins_xnp = plugins_sub.add_parser("xnp-reader-prompt", help="Erzeugt XNP-Reader-Prompt und Card-Gate-Nachweis.")
    add_xnp_reader_prompt_args(plugins_xnp)
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
            "bpmn_validate": "nac bpmn validate",
            "config_validate": "nac config validate",
            "plugin_actions": "nac plugins actions",
            "tenant_status": "nac tenant status --repo ../demo8notariat",
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
        actions = plugin_actions()
        if args.format == "json":
            print_json({"actions": actions})
            return 0
        print("NaC-Plugin-Befehle")
        for action in actions:
            print(f"- {action['command']}: {action['description']}")
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
        ]
        failed = False
        for script in checks:
            result = run_script(repo_root, script, [])
            if result != 0:
                failed = True
        return 1 if failed else 0

    raise AssertionError(f"Unknown config command: {args.config_command}")


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


def plugin_actions() -> list[dict[str, str]]:
    return [
        {
            "command": "nac plugins card-readiness",
            "plugin": "nac-cyberjack-rfid",
            "description": "Kartenleser-, SAK-/XNP- und lokale Readiness-Metadaten prüfen.",
        },
        {
            "command": "nac plugins xnp-reader-prompt",
            "plugin": "nac-bnotk-xnp",
            "description": "XNP-Reader-Prompt mit vorgeschaltetem Karten-Gate erzeugen.",
        },
        {
            "command": "nac plugins pkcs7-inspect",
            "plugin": "nac-pkcs7-certbundle",
            "description": "Lokales PKCS7/P7B/P7C-Zertifikatsbündel metadata-only prüfen.",
        },
    ]


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
