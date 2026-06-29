from __future__ import annotations

import argparse
import json
from pathlib import Path

from nac_gnotkg.views import build_cost_review_view

from .catalog import all_case_summaries, find_case, load_catalogs
from .editor import build_editor_view
from .pilot_checklist import build_pilot_intake_checklist
from .workflow_contract import build_workflow_contract_draft


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
