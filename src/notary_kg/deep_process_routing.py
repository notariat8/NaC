from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .business_case_inventory import build_business_case_inventory
from .ontology_storage_contract import build_ontology_storage_contract


SCHEMA_VERSION = "nac.notarial-deep-process-candidate-routing/v0.1"
EXPLICIT_FIRST_WAVE = {
    "immobilienkaufvertrag",
    "handelsregisteranmeldung",
    "vorsorgevollmacht-patientenverfuegung",
}
ARCHETYPE_CASES = {
    "online-gmbh-gruendung",
    "bautraegervertrag",
    "geschaeftsanteilsuebertragung-gmbh",
    "testament-erbvertrag",
}


@dataclass(frozen=True, slots=True)
class DeepProcessRoutingValidation:
    status: str
    errors: tuple[str, ...]


def build_deep_process_candidate_routing(repo_root: Path) -> dict[str, Any]:
    inventory = build_business_case_inventory(repo_root)
    storage = build_ontology_storage_contract(repo_root)
    contract = storage["contract"]
    thresholds = contract["sizing_thresholds"]
    candidate_bands = set(thresholds["deep_process_candidate_complexity_bands"])
    cases = inventory["business_cases"]
    routes = [_route_case(case, candidate_bands) for case in cases]
    routes.sort(key=_route_sort_key)
    lane_counts: dict[str, int] = {}
    for route in routes:
        lane = str(route["routing_lane"])
        lane_counts[lane] = lane_counts.get(lane, 0) + 1

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASSED" if storage["status"] == "PASSED" and inventory["status"] == "PASSED" else "FAILED",
        "mode": "offline_candidate_routing",
        "source": {
            "business_case_inventory_schema": inventory["schema_version"],
            "ontology_storage_contract_schema": storage["schema_version"],
            "ontology_storage_contract_path": storage["contract_path"],
            "usecase_local_knowledge_graphs_remain_authoritative": True,
            "central_knowledge_graph_folder_allowed": False,
        },
        "routing_policy": {
            "candidate_complexity_bands": sorted(candidate_bands),
            "explicit_first_wave": sorted(EXPLICIT_FIRST_WAVE),
            "archetype_cases": sorted(ARCHETYPE_CASES),
            "max_first_wave_cases": 4,
            "deep_modeling_required_for_all_candidates": False,
            "manual_architecture_review_threshold": thresholds["max_complexity_score_without_architecture_review"],
        },
        "summary": {
            "business_case_count": len(cases),
            "candidate_count": sum(1 for route in routes if route["deep_process_candidate"]),
            "first_wave_count": sum(1 for route in routes if route["routing_lane"] == "first_wave_deep_process"),
            "lane_counts": lane_counts,
            "max_complexity_score": inventory["summary"]["max_complexity_score"],
        },
        "routes": routes,
        "recommended_batch": [
            route["slug"] for route in routes if route["routing_lane"] == "first_wave_deep_process"
        ],
        "guardrails": {
            "offline_only": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "sharepoint_remains_mvp_store": True,
            "ontology_remains_projection_contract": True,
            "bpmn_remains_process_model_not_runtime_engine": True,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "stores_tokens_or_secrets": False,
        },
        "next_artifacts": {
            "first_wave": [
                "bpmn_process_outline",
                "ontology_projection_patch_plan",
                "sharepoint_field_gap_plan",
                "verification_contract",
            ],
            "review_queue": [
                "archetype_similarity_check",
                "duplicate_or_legacy_alias_review",
                "domain_batching_decision",
            ],
        },
    }
    validation = validate_deep_process_candidate_routing(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    else:
        payload["errors"] = []
    return payload


def validate_deep_process_candidate_routing(payload: dict[str, Any]) -> DeepProcessRoutingValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("mode") != "offline_candidate_routing":
        errors.append("routing must remain offline")
    source = payload.get("source", {})
    if source.get("usecase_local_knowledge_graphs_remain_authoritative") is not True:
        errors.append("usecase-local knowledge graphs must remain authoritative")
    if source.get("central_knowledge_graph_folder_allowed") is not False:
        errors.append("central knowledge-graph folder must remain blocked")
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
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")
    routes = payload.get("routes", [])
    if not routes:
        errors.append("routing must include at least one route")
    if payload.get("summary", {}).get("first_wave_count", 0) > payload.get("routing_policy", {}).get("max_first_wave_cases", 0):
        errors.append("first wave exceeds routing policy")
    if "online-gmbh-gruendung" not in payload.get("recommended_batch", []):
        errors.append("high-complexity online-gmbh-gruendung must be in the first wave")
    for route in routes:
        if route.get("deep_process_candidate") and not route.get("routing_reasons"):
            errors.append(f"{route.get('slug', '<missing>')}: candidate missing routing reasons")
        if route.get("routing_lane") == "legacy_alias_dedupe" and route.get("next_action") != "deduplicate_before_deep_modeling":
            errors.append(f"{route.get('slug', '<missing>')}: legacy alias must deduplicate first")
    return DeepProcessRoutingValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _route_case(case: dict[str, Any], candidate_bands: set[str]) -> dict[str, Any]:
    slug = str(case["slug"])
    sizing = case["sizing"]
    band = str(sizing["complexity_band"])
    score = int(sizing["complexity_score"])
    is_candidate = band in candidate_bands
    reasons = _routing_reasons(case, candidate_bands)
    lane = _routing_lane(case, is_candidate)
    return {
        "slug": slug,
        "title": case["title"],
        "domain": case["domain"],
        "inventory_scope": case["inventory_scope"],
        "complexity_score": score,
        "complexity_band": band,
        "deep_process_candidate": is_candidate,
        "routing_lane": lane,
        "routing_reasons": reasons,
        "next_action": _next_action(lane),
        "recommended_artifacts": _recommended_artifacts(lane),
        "blocked_live_actions": [
            "sharepoint_live_apply",
            "sharepoint_schema_change",
            "document_content_read",
            "matter_payload_storage",
            "runtime_ontology_reasoning",
        ],
    }


def _routing_reasons(case: dict[str, Any], candidate_bands: set[str]) -> list[str]:
    reasons: list[str] = []
    slug = str(case["slug"])
    band = str(case["sizing"]["complexity_band"])
    if band in candidate_bands:
        reasons.append(f"complexity_band:{band}")
    if slug in EXPLICIT_FIRST_WAVE:
        reasons.append("explicit_first_wave_recommendation")
    if slug in ARCHETYPE_CASES:
        reasons.append("archetype_coverage")
    if case["inventory_scope"] == "legacy_alias":
        reasons.append("legacy_alias_requires_deduplication")
    return reasons


def _routing_lane(case: dict[str, Any], is_candidate: bool) -> str:
    slug = str(case["slug"])
    if case["inventory_scope"] == "legacy_alias":
        return "legacy_alias_dedupe"
    if slug in EXPLICIT_FIRST_WAVE or case["sizing"]["complexity_band"] == "high":
        return "first_wave_deep_process"
    if is_candidate and slug in ARCHETYPE_CASES:
        return "archetype_review"
    if is_candidate:
        return "candidate_backlog"
    return "thin_catalog_only"


def _next_action(lane: str) -> str:
    return {
        "first_wave_deep_process": "prepare_bpmn_and_ontology_projection_slice",
        "archetype_review": "compare_against_first_wave_before_deep_modeling",
        "candidate_backlog": "batch_by_domain_after_first_wave",
        "legacy_alias_dedupe": "deduplicate_before_deep_modeling",
        "thin_catalog_only": "keep_thin_catalog_until_triggered",
    }[lane]


def _recommended_artifacts(lane: str) -> list[str]:
    if lane == "first_wave_deep_process":
        return ["bpmn_process_outline", "ontology_projection_patch_plan", "verification_contract"]
    if lane == "archetype_review":
        return ["archetype_gap_review", "domain_batching_decision"]
    if lane == "candidate_backlog":
        return ["domain_batching_decision"]
    if lane == "legacy_alias_dedupe":
        return ["canonical_slug_mapping"]
    return ["thin_catalog_status"]


def _route_sort_key(route: dict[str, Any]) -> tuple[int, int, str]:
    lane_priority = {
        "first_wave_deep_process": 0,
        "archetype_review": 1,
        "candidate_backlog": 2,
        "legacy_alias_dedupe": 3,
        "thin_catalog_only": 4,
    }
    return (lane_priority.get(str(route["routing_lane"]), 99), -int(route["complexity_score"]), str(route["slug"]))
