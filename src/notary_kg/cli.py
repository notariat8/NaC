from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import all_case_summaries, find_case, load_catalogs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notary-kg",
        description="Executable status tooling for NoC notarial knowledge graphs.",
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

    parser.error(f"Unknown command: {args.command}")
    return 2


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
        print("NoC KG development status")
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


if __name__ == "__main__":
    raise SystemExit(main())

