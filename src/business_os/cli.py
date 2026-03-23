from __future__ import annotations

import argparse
from pathlib import Path

from .engine import BusinessProcessEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="business-os",
        description="Git-driven reference runtime for business processes.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validiert einen Prozessantrag.")
    validate.add_argument("path", type=Path)

    validate_all = subparsers.add_parser("validate-all", help="Validiert alle Prozessantraege.")
    validate_all.add_argument(
        "--repo-root", type=Path, default=Path.cwd(), help="Pfad zum Repository."
    )

    render_summary = subparsers.add_parser(
        "render-summary", help="Erzeugt eine fachliche Kurzzusammenfassung."
    )
    render_summary.add_argument("path", type=Path)

    monthly_close = subparsers.add_parser(
        "monthly-close", help="Erstellt einen einfachen Monatsabschlussbericht."
    )
    monthly_close.add_argument("--year", required=True, type=int)
    monthly_close.add_argument("--month", required=True, type=int)
    monthly_close.add_argument(
        "--repo-root", type=Path, default=Path.cwd(), help="Pfad zum Repository."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = getattr(args, "repo_root", Path.cwd())
    engine = BusinessProcessEngine(repo_root=repo_root.resolve())

    if args.command == "validate":
        result = engine.validate_document(args.path)
        _print_validation(result.errors, result.warnings)
        return 0 if result.ok else 1

    if args.command == "validate-all":
        return _validate_all(engine)

    if args.command == "render-summary":
        print(engine.render_summary(args.path))
        return 0

    if args.command == "monthly-close":
        report = engine.monthly_close(year=args.year, month=args.month)
        print(report.to_json())
        return 0

    parser.error(f"Unbekannter Befehl: {args.command}")
    return 2


def _validate_all(engine: BusinessProcessEngine) -> int:
    overall_ok = True
    for result in engine.validate_all_processes():
        relative_path = result.document.path.relative_to(engine.repo_root)
        print(f"[{relative_path}]")
        _print_validation(result.errors, result.warnings)
        if not result.ok:
            overall_ok = False
    return 0 if overall_ok else 1


def _print_validation(errors: list[str], warnings: list[str]) -> None:
    if not errors and not warnings:
        print("OK")
        return
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
