from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .first_wave_outline import build_first_wave_bpmn_outline


SCHEMA_VERSION = "nac.first-wave-bpmn-outline-gap-review/v0.1"
ARTIFACT_SCHEMA_VERSION = "nac.first-wave-bpmn-outline-gap-review-artifact/v0.1"
SHAREPOINT_SCHEMA_PATH = Path("deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json")
ONTOLOGY_CONTRACT_PATH = Path("workflows/contracts/notarial-ontology-sizing-storage.contract.json")
DEFAULT_GAP_REVIEW_ARTIFACT_JSON = Path("out/notary-kg/first-wave-gap-review.redacted.json")
DEFAULT_GAP_REVIEW_ARTIFACT_MARKDOWN = Path("out/notary-kg/first-wave-gap-review.redacted.md")


@dataclass(frozen=True, slots=True)
class FirstWaveGapReviewValidation:
    status: str
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FirstWaveGapReviewArtifactValidation:
    status: str
    errors: tuple[str, ...]


def build_first_wave_bpmn_outline_gap_review(repo_root: Path) -> dict[str, Any]:
    outline = build_first_wave_bpmn_outline(repo_root)
    sharepoint_schema = json.loads((repo_root / SHAREPOINT_SCHEMA_PATH).read_text(encoding="utf-8"))
    ontology_contract = json.loads((repo_root / ONTOLOGY_CONTRACT_PATH).read_text(encoding="utf-8"))
    sharepoint_lists = _sharepoint_lists(sharepoint_schema)
    review_items = [
        _review_item(case_outline, sharepoint_lists, ontology_contract)
        for case_outline in outline["outlines"]
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASSED",
        "mode": "offline_gap_review",
        "source": {
            "first_wave_outline_schema": outline["schema_version"],
            "first_wave_outline_status": outline["status"],
            "sharepoint_schema": str(SHAREPOINT_SCHEMA_PATH),
            "ontology_storage_contract": str(ONTOLOGY_CONTRACT_PATH),
            "central_knowledge_graph_folder_allowed": False,
            "usecase_local_knowledge_graphs_remain_authoritative": True,
        },
        "summary": {
            "first_wave_count": len(review_items),
            "review_slugs": [item["slug"] for item in review_items],
            "sharepoint_field_gap_count": sum(
                len(item["sharepoint_field_gap_plan"]["gaps"])
                for item in review_items
            ),
            "bpmn_gap_count": sum(len(item["bpmn_gap_plan"]["gaps"]) for item in review_items),
            "ontology_patch_count": sum(
                len(item["ontology_projection_patch_plan"]["patches"])
                for item in review_items
            ),
            "owner_gate_required_now": False,
        },
        "review_items": review_items,
        "guardrails": {
            "offline_only": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "stores_tokens_or_secrets": False,
            "creates_central_knowledge_graph_folder": False,
            "sharepoint_remains_mvp_store": True,
            "ontology_remains_projection_contract": True,
            "bpmn_remains_process_model_not_runtime_engine": True,
        },
        "next_batch": {
            "recommended_slice": "first_wave_bpmn_outline_gap_review_artifact",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "sharepoint_schema_apply",
                "graph_live_write",
                "bpmn_model_mutation",
                "ontology_projection_patch_apply",
            ],
        },
        "errors": [],
    }
    validation = validate_first_wave_bpmn_outline_gap_review(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def write_first_wave_bpmn_outline_gap_review_artifact(
    repo_root: Path,
    json_output: Path | None = None,
    markdown_output: Path | None = None,
) -> dict[str, Any]:
    review = build_first_wave_bpmn_outline_gap_review(repo_root)
    json_path = json_output or DEFAULT_GAP_REVIEW_ARTIFACT_JSON
    markdown_path = markdown_output or DEFAULT_GAP_REVIEW_ARTIFACT_MARKDOWN
    json_path = _resolve_output_path(repo_root, json_path)
    markdown_path = _resolve_output_path(repo_root, markdown_path)

    payload = _artifact_payload(repo_root, review, json_path, markdown_path)
    validation = validate_first_wave_bpmn_outline_gap_review_artifact(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_artifact_markdown(payload), encoding="utf-8")
    return payload


def validate_first_wave_bpmn_outline_gap_review_artifact(payload: dict[str, Any]) -> FirstWaveGapReviewArtifactValidation:
    errors: list[str] = []
    if payload.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        errors.append("unexpected artifact schema_version")
    if payload.get("mode") != "redacted_offline_artifact":
        errors.append("artifact must remain a redacted offline artifact")
    if payload.get("source", {}).get("gap_review_schema_version") != SCHEMA_VERSION:
        errors.append("artifact must reference the first-wave gap review schema")

    artifact_paths = payload.get("artifact_paths", {})
    for key, suffix in (("json", ".redacted.json"), ("markdown", ".redacted.md")):
        path = artifact_paths.get(key, "")
        if not str(path).endswith(suffix):
            errors.append(f"{key} artifact path must end with {suffix}")

    summary = payload.get("summary", {})
    if summary.get("first_wave_count") != 4:
        errors.append("artifact must summarize exactly four first-wave cases")
    if summary.get("sharepoint_field_gap_count", 0) <= 0:
        errors.append("artifact must include SharePoint field gap count")
    if summary.get("bpmn_gap_count", 0) <= 0:
        errors.append("artifact must include BPMN gap count")
    if summary.get("ontology_patch_count", 0) <= 0:
        errors.append("artifact must include ontology patch count")

    redaction = payload.get("redaction", {})
    for key in (
        "redacted",
        "contains_real_matter_data",
        "contains_document_full_text",
        "contains_tokens_or_secrets",
        "contains_raw_graph_response",
    ):
        expected = key == "redacted"
        if redaction.get(key) is not expected:
            errors.append(f"redaction flag mismatch: {key}")

    guardrails = payload.get("guardrails", {})
    for key in ("offline_only", "sharepoint_remains_mvp_store", "redacted_artifact", "release_readiness_attachable"):
        if guardrails.get(key) is not True:
            errors.append(f"guardrail must be true: {key}")
    for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema", "stores_tokens_or_secrets"):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")

    review_index = payload.get("review_index", [])
    if len(review_index) != 4:
        errors.append("artifact review index must include exactly four entries")
    for item in review_index:
        slug = item.get("slug", "<missing>")
        if "planned_value" in item:
            errors.append(f"{slug}: artifact index must not expose planned values")
        if item.get("sharepoint_field_gap_count", 0) <= 0:
            errors.append(f"{slug}: expected at least one SharePoint gap")
        if item.get("ontology_patch_count", 0) <= 0:
            errors.append(f"{slug}: expected at least one ontology patch")

    attachments = payload.get("evidence_attachments", [])
    if len(attachments) != 2:
        errors.append("artifact must expose json and markdown evidence attachments")
    for attachment in attachments:
        if attachment.get("redacted") is not True:
            errors.append("evidence attachment must be marked redacted")
        if attachment.get("required_for_release_readiness") is not False:
            errors.append("first-wave gap review artifact must remain optional release-readiness evidence")

    return FirstWaveGapReviewArtifactValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def validate_first_wave_bpmn_outline_gap_review(payload: dict[str, Any]) -> FirstWaveGapReviewValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("mode") != "offline_gap_review":
        errors.append("gap review must remain offline")
    source = payload.get("source", {})
    if source.get("first_wave_outline_status") != "PASSED":
        errors.append("first-wave outline must pass before gap review")
    if source.get("central_knowledge_graph_folder_allowed") is not False:
        errors.append("central knowledge-graph folder must remain blocked")
    if source.get("usecase_local_knowledge_graphs_remain_authoritative") is not True:
        errors.append("usecase-local knowledge graphs must remain authoritative")

    review_items = payload.get("review_items", [])
    if len(review_items) != 4:
        errors.append("gap review must include exactly four first-wave cases")
    if payload.get("summary", {}).get("sharepoint_field_gap_count", 0) <= 0:
        errors.append("gap review must surface at least one SharePoint field gap")
    if payload.get("summary", {}).get("bpmn_gap_count", 0) <= 0:
        errors.append("gap review must surface at least one BPMN gap")
    for item in review_items:
        slug = item.get("slug", "<missing>")
        for plan_name in ("sharepoint_field_gap_plan", "bpmn_gap_plan", "ontology_projection_patch_plan"):
            plan = item.get(plan_name, {})
            if plan.get("mode") != "plan_only":
                errors.append(f"{slug}: {plan_name} must be plan_only")
            if plan.get("owner_gate_required_before_apply") is not True:
                errors.append(f"{slug}: {plan_name} must require owner gate before apply")
            if plan.get("writes_sharepoint") is not False:
                errors.append(f"{slug}: {plan_name} must not write SharePoint")
            if plan.get("executes_graph_requests") is not False:
                errors.append(f"{slug}: {plan_name} must not execute Graph requests")
        if item.get("sharepoint_field_gap_plan", {}).get("stores_matter_values") is not False:
            errors.append(f"{slug}: SharePoint gap plan must not store matter values")
        if item.get("ontology_projection_patch_plan", {}).get("stores_document_full_text") is not False:
            errors.append(f"{slug}: ontology patch plan must not store document full text")

    guardrails = payload.get("guardrails", {})
    for key in (
        "offline_only",
        "sharepoint_remains_mvp_store",
        "ontology_remains_projection_contract",
        "bpmn_remains_process_model_not_runtime_engine",
    ):
        if guardrails.get(key) is not True:
            errors.append(f"guardrail must be true: {key}")
    for key in (
        "executes_graph_requests",
        "writes_sharepoint",
        "changes_sharepoint_schema",
        "stores_matter_instance_values",
        "stores_document_full_text",
        "stores_tokens_or_secrets",
        "creates_central_knowledge_graph_folder",
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")
    return FirstWaveGapReviewValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _artifact_payload(
    repo_root: Path,
    review: dict[str, Any],
    json_path: Path,
    markdown_path: Path,
) -> dict[str, Any]:
    review_index = [_redacted_review_index_item(item) for item in review["review_items"]]
    artifact_paths = {
        "json": _relative_path(repo_root, json_path),
        "markdown": _relative_path(repo_root, markdown_path),
    }
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "status": "PASSED" if review.get("status") == "PASSED" else "FAILED",
        "mode": "redacted_offline_artifact",
        "source": {
            "gap_review_schema_version": review["schema_version"],
            "gap_review_status": review["status"],
            "first_wave_outline_schema": review["source"]["first_wave_outline_schema"],
            "sharepoint_schema": review["source"]["sharepoint_schema"],
            "ontology_storage_contract": review["source"]["ontology_storage_contract"],
        },
        "artifact_paths": artifact_paths,
        "summary": review["summary"],
        "review_index": review_index,
        "evidence_attachments": [
            {
                "id": "first_wave_gap_review_json",
                "path": artifact_paths["json"],
                "status": "PASSED",
                "redacted": True,
                "required_for_release_readiness": False,
            },
            {
                "id": "first_wave_gap_review_markdown",
                "path": artifact_paths["markdown"],
                "status": "PASSED",
                "redacted": True,
                "required_for_release_readiness": False,
            },
        ],
        "redaction": {
            "redacted": True,
            "contains_real_matter_data": False,
            "contains_document_full_text": False,
            "contains_tokens_or_secrets": False,
            "contains_raw_graph_response": False,
            "omits_sharepoint_choice_values": True,
            "omits_raw_review_items": True,
        },
        "guardrails": {
            **review["guardrails"],
            "redacted_artifact": True,
            "release_readiness_attachable": True,
        },
        "next_batch": {
            "recommended_slice": "first_wave_gap_review_release_readiness_attachment",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "making_this_artifact_release_readiness_required",
                "sharepoint_schema_apply",
                "graph_live_write",
            ],
        },
        "errors": [],
    }


def _redacted_review_index_item(item: dict[str, Any]) -> dict[str, Any]:
    sharepoint_gaps = item["sharepoint_field_gap_plan"]["gaps"]
    bpmn_gaps = item["bpmn_gap_plan"]["gaps"]
    ontology_patches = item["ontology_projection_patch_plan"]["patches"]
    return {
        "slug": item["slug"],
        "domain": item["domain"],
        "source_refs": {
            "bpmn": item["sources"]["bpmn"],
            "knowledge_graph": item["sources"]["knowledge_graph"],
        },
        "sharepoint_field_gap_count": len(sharepoint_gaps),
        "sharepoint_gap_types": sorted({gap["gap_type"] for gap in sharepoint_gaps}),
        "bpmn_gap_count": len(bpmn_gaps),
        "bpmn_gap_types": sorted({gap["gap_type"] for gap in bpmn_gaps}),
        "ontology_patch_count": len(ontology_patches),
        "ontology_patch_types": sorted({patch["patch_type"] for patch in ontology_patches}),
        "owner_gate_required_before_apply": True,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "stores_matter_values": False,
        "stores_document_full_text": False,
    }


def _artifact_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# First-Wave BPMN Outline Gap Review Artifact",
        "",
        f"- Status: `{payload['status']}`",
        f"- Schema: `{payload['schema_version']}`",
        "- Mode: `redacted_offline_artifact`",
        f"- First-wave cases: {summary['first_wave_count']}",
        f"- SharePoint field gaps: {summary['sharepoint_field_gap_count']}",
        f"- BPMN gaps: {summary['bpmn_gap_count']}",
        f"- Ontology projection patches: {summary['ontology_patch_count']}",
        "- Owner gate required now: `false`",
        "",
        "## Case Index",
        "",
        "| Case | SharePoint gaps | BPMN gaps | Ontology patches |",
        "| --- | ---: | ---: | ---: |",
    ]
    for item in payload["review_index"]:
        lines.append(
            "| "
            f"`{item['slug']}` | "
            f"{item['sharepoint_field_gap_count']} | "
            f"{item['bpmn_gap_count']} | "
            f"{item['ontology_patch_count']} |"
        )
    lines.extend(
        [
            "",
            "## Redaction",
            "",
            "- Contains real matter data: `false`",
            "- Contains document full text: `false`",
            "- Contains tokens or secrets: `false`",
            "- Contains raw Graph responses: `false`",
            "- Omits raw planned SharePoint values: `true`",
            "",
            "## Release Evidence",
            "",
            "This artifact is optional release/readiness evidence. Making it mandatory requires a separate owner-gated decision.",
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_output_path(repo_root: Path, output_path: Path) -> Path:
    if output_path.is_absolute():
        return output_path
    return repo_root / output_path


def _relative_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _review_item(
    case_outline: dict[str, Any],
    sharepoint_lists: dict[str, dict[str, Any]],
    ontology_contract: dict[str, Any],
) -> dict[str, Any]:
    return {
        "slug": case_outline["slug"],
        "title": case_outline["title"],
        "domain": case_outline["domain"],
        "sources": case_outline["sources"],
        "sharepoint_field_gap_plan": _sharepoint_gap_plan(case_outline, sharepoint_lists),
        "bpmn_gap_plan": _bpmn_gap_plan(case_outline),
        "ontology_projection_patch_plan": _ontology_patch_plan(case_outline, ontology_contract),
        "verification_contract_plan": {
            "mode": "plan_only",
            "required_checks": [
                "first_wave_outline_still_passes",
                "sharepoint_gap_plan_contains_no_values",
                "bpmn_patch_is_non_executable",
                "ontology_patch_is_shape_only",
            ],
            "owner_gate_required_before_apply": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
        },
    }


def _sharepoint_gap_plan(case_outline: dict[str, Any], sharepoint_lists: dict[str, dict[str, Any]]) -> dict[str, Any]:
    slug = case_outline["slug"]
    gaps: list[dict[str, Any]] = []
    akten_columns = sharepoint_lists.get("Akten", {}).get("columns_by_name", {})
    vorgangstyp = akten_columns.get("Vorgangstyp", {})
    if slug not in set(vorgangstyp.get("choices", [])):
        gaps.append(
            {
                "id": f"{slug}.akten.vorgangstyp.choice",
                "list": "Akten",
                "field": "Vorgangstyp",
                "gap_type": "choice_extension_plan",
                "planned_value": slug,
                "reason": "First-wave case type is not selectable in the MVP matter metadata list.",
            }
        )
    if case_outline["kg_outline"]["document_types"] > 0:
        gaps.append(
            {
                "id": f"{slug}.dokumentregister.documenttype.taxonomy",
                "list": "DokumentRegister",
                "field": "DocumentType",
                "gap_type": "case_document_type_taxonomy_review",
                "planned_value_count": case_outline["kg_outline"]["document_types"],
                "reason": "Usecase-local document types need a metadata-only taxonomy mapping before schema apply.",
            }
        )
    if case_outline["kg_outline"]["decision_points"] > 0:
        gaps.append(
            {
                "id": f"{slug}.aufgabenfristen.decision-gate-mapping",
                "list": "AufgabenFristen",
                "field": "BpmnStepCode",
                "gap_type": "decision_and_gate_step_mapping_review",
                "planned_value_count": case_outline["kg_outline"]["decision_points"] + case_outline["kg_outline"]["gates"],
                "reason": "Decision and gate shapes need stable BPMN step codes before task-state materialization.",
            }
        )
    return {
        "mode": "plan_only",
        "source_schema": str(SHAREPOINT_SCHEMA_PATH),
        "gaps": gaps,
        "stores_matter_values": False,
        "stores_document_full_text": False,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "owner_gate_required_before_apply": True,
    }


def _bpmn_gap_plan(case_outline: dict[str, Any]) -> dict[str, Any]:
    bpmn = case_outline["bpmn_outline"]
    kg = case_outline["kg_outline"]
    gaps: list[dict[str, Any]] = []
    if bpmn["critical_path_node_count"] == 0:
        gaps.append(
            {
                "id": f"{case_outline['slug']}.bpmn.critical-path",
                "gap_type": "missing_critical_path_annotations",
                "recommended_action": "Add non-executable critical-path annotations to the BPMN source.",
            }
        )
    gateway_count = bpmn["node_type_counts"].get("exclusiveGateway", 0) + bpmn["node_type_counts"].get("parallelGateway", 0)
    if kg["decision_points"] > 0 and gateway_count == 0:
        gaps.append(
            {
                "id": f"{case_outline['slug']}.bpmn.decision-gateways",
                "gap_type": "decision_points_not_represented_as_gateways",
                "recommended_action": "Review whether KG decision points need explicit BPMN gateway shapes.",
            }
        )
    if bpmn["evidence_required_node_count"] < max(1, bpmn["flow_node_count"] - 1):
        gaps.append(
            {
                "id": f"{case_outline['slug']}.bpmn.evidence-coverage",
                "gap_type": "partial_evidence_annotation_coverage",
                "recommended_action": "Review evidence-required annotations before runtime evidence checks.",
            }
        )
    if kg["gates"] > gateway_count + bpmn["node_type_counts"].get("businessRuleTask", 0):
        gaps.append(
            {
                "id": f"{case_outline['slug']}.bpmn.gate-coverage",
                "gap_type": "kg_gates_exceed_bpmn_gate_shapes",
                "recommended_action": "Map KG gates to BPMN gateway or business-rule shapes before deep modeling apply.",
            }
        )
    return {
        "mode": "plan_only",
        "source_bpmn": case_outline["sources"]["bpmn"],
        "gaps": gaps,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "owner_gate_required_before_apply": True,
    }


def _ontology_patch_plan(case_outline: dict[str, Any], ontology_contract: dict[str, Any]) -> dict[str, Any]:
    kg = case_outline["kg_outline"]
    patches = [
        {
            "id": f"{case_outline['slug']}.business-case-type",
            "patch_type": "business_case_type_shape",
            "entities": ["BusinessCaseType"],
            "source": case_outline["sources"]["knowledge_graph"],
        },
        {
            "id": f"{case_outline['slug']}.process-pointer",
            "patch_type": "process_model_pointer",
            "entities": ["ProcessStep", "Gate"],
            "source": case_outline["sources"]["bpmn"],
        },
        {
            "id": f"{case_outline['slug']}.document-evidence-shapes",
            "patch_type": "document_and_evidence_shape",
            "entities": ["DocumentType", "EvidencePointer"],
            "document_type_count": kg["document_types"],
            "evidence_point_count": kg["evidence_points"],
        },
    ]
    mapping_lists = [
        item["list_or_library"]
        for item in ontology_contract.get("sharepoint_projection_mapping", [])
    ]
    return {
        "mode": "plan_only",
        "projection_mode": ontology_contract["projection_rules"]["projection_mode"],
        "source_of_truth": ontology_contract["projection_rules"]["source_of_truth"],
        "target_sharepoint_lists": mapping_lists,
        "patches": patches,
        "stores_matter_values": False,
        "stores_document_full_text": False,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "owner_gate_required_before_apply": True,
    }


def _sharepoint_lists(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lists: dict[str, dict[str, Any]] = {}
    for item in schema.get("sharepoint", {}).get("lists", []):
        columns = item.get("columns", [])
        lists[item["display_name"]] = {
            **item,
            "columns_by_name": {column["name"]: column for column in columns},
        }
    return lists
