from __future__ import annotations

import argparse
import json
from pathlib import Path

from nac_gnotkg.views import build_cost_review_view

from .business_case_inventory import build_business_case_inventory
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
from .process_ontology_schema_apply_readiness import build_process_ontology_sharepoint_schema_apply_readiness
from .process_ontology_schema_gap import build_process_ontology_sharepoint_schema_gap
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

    subparsers.add_parser(
        "business-case-inventory",
        help="Build the thin notarial business-case inventory for ontology sizing.",
    )

    subparsers.add_parser(
        "ontology-storage-contract",
        help="Evaluate the notarial ontology sizing and storage contract.",
    )

    subparsers.add_parser(
        "process-ontology-contract",
        help="Evaluate the notarial process ontology product-model contract.",
    )

    subparsers.add_parser(
        "process-ontology-schema-gap",
        help="Compare the process ontology contract with the current SharePoint MVP schema.",
    )

    subparsers.add_parser(
        "process-ontology-schema-apply-plan",
        help="Build an offline Graph REST apply plan from the process ontology SharePoint schema gaps.",
    )

    subparsers.add_parser(
        "process-ontology-schema-apply-readiness",
        help="Check offline workspace, ID, permission and ordering readiness for a future schema apply.",
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

    if payload.get("schema_version") == "nac.notarial-business-case-inventory/v0.1":
        summary = payload["summary"]
        print("Notarial business-case inventory")
        print(f"- status: {payload['status']}")
        print(f"- mode: {payload['mode']}")
        print(f"- business cases: {summary['business_case_count']}")
        print(f"- canonical coverage: {summary['canonical_covered_count']}/{summary['canonical_target_count']}")
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

    if payload.get("schema_version") == "nac.notarial-process-ontology/v1":
        evaluation = payload["evaluation"]
        summary = evaluation["summary"]
        print("Notarial process ontology contract")
        print(f"- status: {payload['status']}")
        print(f"- contract: {payload['contract_path']}")
        print(f"- business cases: {summary['business_case_count']}")
        print(f"- canonical coverage: {summary['canonical_covered_count']}/{summary['canonical_required']}")
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

    if payload.get("schema_version") == "nac.process-ontology-sharepoint-schema-gap/v0.1":
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
        return

    if payload.get("schema_version") == "nac.process-ontology-sharepoint-schema-apply-plan/v0.1":
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
        return

    if payload.get("schema_version") == "nac.process-ontology-sharepoint-schema-apply-readiness/v0.1":
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


if __name__ == "__main__":
    raise SystemExit(main())
