from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .business_case_inventory import build_business_case_inventory
from .process_ontology_contract import (
    CONTRACT_RELATIVE_PATH as PROCESS_ONTOLOGY_CONTRACT_PATH,
    build_process_ontology_contract,
)


SHAREPOINT_SCHEMA_PATH = Path("deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json")
BPMN_VIEWER_PROVISIONING_PATH = Path("deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json")
SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-gap/v0.2"
CONTRACT_ID = "notarial.process_ontology_sharepoint_schema_gap"

LEGACY_VORGANGSTYP_BASELINE: dict[str, Any] = {
    "name": "Vorgangstyp",
    "type": "choice",
    "choices": [
        "immobilienkaufvertrag",
        "unterschriftsbeglaubigung",
        "online-gmbh-gruendung",
        "handelsregisteranmeldung",
    ],
    "required": True,
}
LEGACY_VORGANGSTYP_BASELINE_SHA256 = "471a8b1702a8636ac831dd93cf123a587ea14a16fddfe2ccde1d5d66f75f1eeb"


REQUIRED_RUNTIME_PROJECTIONS = {
    "lists": {
        "Vorgangsartenregister": [
            {
                "name": "BusinessCaseTypeId",
                "type": "text",
                "required": True,
                "indexed": True,
                "enforceUniqueValues": True,
                "maxLength": 128,
            },
            {
                "name": "LifecycleStatus",
                "type": "choice",
                "required": True,
                "choices": ["active", "deprecated", "retired"],
                "indexed": False,
            },
            {"name": "Selectable", "type": "boolean", "required": True, "indexed": False},
            {"name": "CatalogVersion", "type": "text", "required": True, "indexed": False},
        ]
    }
}


EXPECTED_PROCESS_COLUMNS: dict[str, list[dict[str, Any]]] = {
    "Akten": [
        {
            "name": "VorgangstypId",
            "type": "text",
            "required": False,
            "indexed": True,
            "maxLength": 128,
            "reason": "Canonical BusinessCaseTypeId; additive to the unchanged legacy Vorgangstyp Choice.",
        },
        {"name": "ProcessInstanceId", "type": "text", "required": True, "reason": "Stable runtime process-instance identifier."},
        {"name": "CurrentPhase", "type": "choice", "required": True, "reason": "Current canonical process phase from the process ontology contract."},
        {"name": "CurrentBpmnStepCode", "type": "text", "required": False, "reason": "Current BPMN step pointer for task and evidence routing."},
        {"name": "BpmnModelRef", "type": "text", "required": False, "reason": "Approved BPMN model pointer for the matter's business-case type."},
        {"name": "LastProcessEventId", "type": "text", "required": False, "reason": "Last redacted event pointer for idempotent agent/runtime updates."},
    ],
    "Beteiligte": [
        {"name": "RoleBindingId", "type": "text", "required": True, "reason": "Stable role-binding identifier separate from the party identifier."},
        {"name": "RoleTemplate", "type": "choice", "required": True, "reason": "Canonical role template from the process ontology contract."},
        {"name": "AccessPurpose", "type": "choice", "required": False, "reason": "Purpose-bound participant access and delegation context."},
        {"name": "AuthorizedUntil", "type": "dateTime", "required": False, "reason": "Time-boxed participant access boundary when needed."},
    ],
    "AufgabenFristen": [
        {"name": "ProcessInstanceId", "type": "text", "required": True, "reason": "Stable process-instance join key."},
        {"name": "ProcessPhase", "type": "choice", "required": True, "reason": "Canonical phase for process dashboards and bounded agent tools."},
        {"name": "TaskType", "type": "choice", "required": True, "reason": "Typed task shape for repeatable workflow execution."},
        {"name": "GateType", "type": "choice", "required": False, "reason": "Gate and decision-point shape from the process ontology contract."},
        {"name": "EvidenceRequired", "type": "boolean", "required": True, "reason": "Machine-readable evidence obligation before completion."},
        {"name": "CompletedAt", "type": "dateTime", "required": False, "reason": "Completion timestamp for process state and audit correlation."},
    ],
    "DokumentRegister": [
        {"name": "ProcessInstanceId", "type": "text", "required": True, "reason": "Stable process-instance join key."},
        {"name": "BpmnStepCode", "type": "text", "required": False, "reason": "Document pointer to the process step that produced or requires it."},
        {"name": "EvidencePointerId", "type": "text", "required": False, "reason": "Evidence pointer join key without storing document content."},
        {"name": "DocumentVersionLabel", "type": "text", "required": False, "reason": "Version label for document lifecycle without raw document payload."},
        {"name": "ReviewStatus", "type": "choice", "required": False, "reason": "Review and approval status separate from draft status."},
    ],
    "Vertretungsfreigaben": [
        {"name": "ProcessInstanceId", "type": "text", "required": True, "reason": "Stable process-instance join key for deputy grants."},
        {"name": "AccessPurpose", "type": "choice", "required": True, "reason": "Purpose-bound delegation as required by the access model."},
        {"name": "ValidityWindowId", "type": "text", "required": False, "reason": "Explicit validity-window pointer for replay and audit."},
        {"name": "RevokedAt", "type": "dateTime", "required": False, "reason": "Revocation timestamp for time-boxed delegation history."},
    ],
    "AuditJournalLite": [
        {"name": "ProcessInstanceId", "type": "text", "required": True, "reason": "Stable process-instance join key for audit events."},
        {"name": "ProcessPhase", "type": "choice", "required": False, "reason": "Phase context for redacted process event evidence."},
        {"name": "BpmnStepCode", "type": "text", "required": False, "reason": "Step context for redacted process event evidence."},
        {"name": "EvidencePointerId", "type": "text", "required": False, "reason": "Evidence pointer without raw file or payload content."},
    ],
}


@dataclass(frozen=True, slots=True)
class ProcessOntologySchemaGapValidation:
    status: str
    errors: tuple[str, ...]


def build_process_ontology_sharepoint_schema_gap(repo_root: Path) -> dict[str, Any]:
    process_contract = build_process_ontology_contract(repo_root)
    inventory = build_business_case_inventory(repo_root)
    sharepoint_schema = json.loads((repo_root / SHAREPOINT_SCHEMA_PATH).read_text(encoding="utf-8"))
    viewer_provisioning = json.loads((repo_root / BPMN_VIEWER_PROVISIONING_PATH).read_text(encoding="utf-8"))
    optional_process_projections = _optional_process_projections(viewer_provisioning)
    list_index = _sharepoint_list_index(sharepoint_schema)
    library_index = _sharepoint_library_index(sharepoint_schema)
    required_lists = process_contract["contract"]["sharepoint_projection_rules"]["required_lists_or_libraries"]
    process_phases = process_contract["contract"]["required_process_phases"]
    role_templates = process_contract["contract"]["required_role_templates"]
    legacy_vorgangstyp = list_index.get("Akten", {}).get("raw_columns_by_name", {}).get("Vorgangstyp")
    all_case_slugs = [item["slug"] for item in inventory["business_cases"]]
    business_case_type_ids = [
        str(item.get("business_case_type_id", item["slug"]))
        for item in inventory["business_cases"]
        if item.get("inventory_scope") == "canonical_top10_or_next10"
    ]

    missing_required_lists = [
        list_name
        for list_name in required_lists
        if list_name not in list_index
        and list_name not in REQUIRED_RUNTIME_PROJECTIONS["lists"]
    ]
    required_projection_gaps = _required_projection_gaps(list_index)
    optional_projection_gaps = _optional_projection_gaps(list_index, library_index, optional_process_projections)
    field_gaps = _field_gaps(list_index)
    choice_gaps = _choice_gaps(list_index, all_case_slugs, process_phases, role_templates)
    shape_mismatch_gaps = [
        gap
        for gap in [*required_projection_gaps, *field_gaps]
        if gap["gap_type"].endswith("shape_mismatch") or gap["gap_type"] == "field_shape_mismatch"
    ]
    observed_legacy_fingerprint = _payload_sha256(legacy_vorgangstyp) if legacy_vorgangstyp is not None else None
    legacy_matches_baseline = legacy_vorgangstyp == LEGACY_VORGANGSTYP_BASELINE
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "PASSED",
        "mode": "offline_schema_gap_review",
        "source": {
            "process_ontology_contract": str(PROCESS_ONTOLOGY_CONTRACT_PATH),
            "process_ontology_contract_status": process_contract["status"],
            "sharepoint_schema": str(SHAREPOINT_SCHEMA_PATH),
            "sharepoint_schema_version": sharepoint_schema["schema_version"],
            "bpmn_viewer_provisioning": str(BPMN_VIEWER_PROVISIONING_PATH),
            "bpmn_viewer_provisioning_version": viewer_provisioning["schema_version"],
            "business_case_inventory_schema": inventory["schema_version"],
            "business_case_inventory_status": inventory["status"],
            "graph_rest_only": sharepoint_schema["graph"]["rest_only"],
            "legacy_sharepoint_api_allowed": sharepoint_schema["graph"]["legacy_sharepoint_api_allowed"],
        },
        "summary": {
            "business_case_count": len(all_case_slugs),
            "required_list_count": len(required_lists),
            "missing_required_list_count": len(missing_required_lists),
            "required_projection_gap_count": len(required_projection_gaps),
            "optional_projection_gap_count": len(optional_projection_gaps),
            "field_gap_count": len(field_gaps),
            "choice_gap_count": len(choice_gaps),
            "blocking_shape_mismatch_count": len(shape_mismatch_gaps),
            "optional_shape_mismatch_count": sum(
                1 for gap in optional_projection_gaps if gap["gap_type"].endswith("shape_mismatch")
            ),
            "total_gap_count": (
                len(missing_required_lists)
                + len(required_projection_gaps)
                + len(optional_projection_gaps)
                + len(field_gaps)
                + len(choice_gaps)
            ),
            "owner_gate_required_now": False,
        },
        "business_case_type_ids": business_case_type_ids,
        "legacy_column_contract": {
            "target": "Akten.Vorgangstyp",
            "protected": True,
            "expected_type": "choice",
            "baseline_definition": LEGACY_VORGANGSTYP_BASELINE,
            "baseline_fingerprint_sha256": LEGACY_VORGANGSTYP_BASELINE_SHA256,
            "observed_fingerprint_sha256": observed_legacy_fingerprint,
            "matches_pinned_baseline": legacy_matches_baseline,
        },
        "missing_required_lists": _missing_required_list_gaps(missing_required_lists),
        "required_projection_gaps": required_projection_gaps,
        "optional_projection_gaps": optional_projection_gaps,
        "field_gaps": field_gaps,
        "choice_gaps": choice_gaps,
        "apply_boundary": {
            "mode": "plan_only",
            "owner_gate_required_before_apply": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "rest_endpoint_family": "microsoft_graph_v1_lists_columns_future_apply",
        },
        "guardrails": {
            "offline_only": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "stores_tokens_or_secrets": False,
            "creates_central_knowledge_graph_folder": False,
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
        },
        "next_batch": {
            "recommended_slice": "process_ontology_sharepoint_schema_apply_plan",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "sharepoint_schema_apply",
                "graph_live_write",
                "provision_optional_process_register",
                "provision_bpmn_models_library",
            ],
        },
        "errors": [],
    }
    validation = validate_process_ontology_sharepoint_schema_gap(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def validate_process_ontology_sharepoint_schema_gap(payload: dict[str, Any]) -> ProcessOntologySchemaGapValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected contract_id")
    if payload.get("mode") != "offline_schema_gap_review":
        errors.append("schema gap review must remain offline")
    source = payload.get("source", {})
    if source.get("process_ontology_contract_status") != "PASSED":
        errors.append("process ontology contract must pass before schema gap review")
    if source.get("business_case_inventory_status") != "PASSED":
        errors.append("business-case inventory must pass before schema gap review")
    if source.get("graph_rest_only") is not True:
        errors.append("SharePoint schema must remain Graph REST only")
    if source.get("legacy_sharepoint_api_allowed") is not False:
        errors.append("legacy SharePoint API must remain blocked")

    legacy = payload.get("legacy_column_contract", {})
    if legacy.get("target") != "Akten.Vorgangstyp" or legacy.get("protected") is not True:
        errors.append("legacy Akten.Vorgangstyp must remain protected")
    if legacy.get("expected_type") != "choice":
        errors.append("legacy Akten.Vorgangstyp must remain Choice")
    if legacy.get("baseline_definition") != LEGACY_VORGANGSTYP_BASELINE:
        errors.append("legacy Akten.Vorgangstyp baseline definition must remain pinned")
    if legacy.get("baseline_fingerprint_sha256") != LEGACY_VORGANGSTYP_BASELINE_SHA256:
        errors.append("legacy Akten.Vorgangstyp baseline fingerprint must remain pinned")
    if legacy.get("observed_fingerprint_sha256") != LEGACY_VORGANGSTYP_BASELINE_SHA256:
        errors.append("legacy Akten.Vorgangstyp is missing or drifted from the pinned baseline")
    if legacy.get("matches_pinned_baseline") is not True:
        errors.append("legacy Akten.Vorgangstyp must exactly match the pinned baseline")

    business_case_type_ids = payload.get("business_case_type_ids", [])
    if len(business_case_type_ids) != len(set(business_case_type_ids)) or len(business_case_type_ids) < 20:
        errors.append("canonical BusinessCaseTypeId values must be unique and complete")

    summary = payload.get("summary", {})
    if summary.get("business_case_count", 0) < 20:
        errors.append("schema gap review must cover all canonical business cases")
    if summary.get("missing_required_list_count") != 0:
        errors.append("MVP required SharePoint lists must exist before field gap review")
    gap_sections = {
        "required_projection_gap_count": payload.get("required_projection_gaps", []),
        "optional_projection_gap_count": payload.get("optional_projection_gaps", []),
        "field_gap_count": payload.get("field_gaps", []),
        "choice_gap_count": payload.get("choice_gaps", []),
    }
    for count_key, gaps in gap_sections.items():
        if summary.get(count_key) != len(gaps):
            errors.append(f"{count_key} must match its gap section")
    if summary.get("blocking_shape_mismatch_count") != 0:
        errors.append("existing SharePoint fields must match their complete expected shape")

    for gap in [
        *payload.get("required_projection_gaps", []),
        *payload.get("field_gaps", []),
        *payload.get("choice_gaps", []),
        *payload.get("optional_projection_gaps", []),
    ]:
        if gap.get("mode") != "plan_only":
            errors.append(f"{gap.get('id', '<unknown>')}: gap must be plan_only")
        if gap.get("owner_gate_required_before_apply") is not True:
            errors.append(f"{gap.get('id', '<unknown>')}: owner gate must be required before apply")
        if gap.get("executes_graph_requests") is not False:
            errors.append(f"{gap.get('id', '<unknown>')}: must not execute Graph requests")
        if gap.get("writes_sharepoint") is not False:
            errors.append(f"{gap.get('id', '<unknown>')}: must not write SharePoint")

    apply_boundary = payload.get("apply_boundary", {})
    if apply_boundary.get("mode") != "plan_only":
        errors.append("apply boundary must remain plan_only")
    for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
        if apply_boundary.get(key) is not False:
            errors.append(f"apply boundary must keep {key} false")

    guardrails = payload.get("guardrails", {})
    for key in ("offline_only",):
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
        "legacy_sharepoint_api_allowed",
        "graph_sdk_allowed",
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")
    return ProcessOntologySchemaGapValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _payload_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sharepoint_list_index(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in schema.get("sharepoint", {}).get("lists", []):
        indexed_columns = set(item.get("indexed_columns", []))
        columns = {
            column["name"]: _normalized_column_shape(column, column["name"] in indexed_columns)
            for column in item.get("columns", [])
        }
        result[item["display_name"]] = {**item, "columns_by_name": columns, "raw_columns_by_name": {column["name"]: column for column in item.get("columns", [])}}
    return result


def _sharepoint_library_index(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in schema.get("sharepoint", {}).get("document_libraries", []):
        indexed_columns = set(item.get("indexed_columns", []))
        columns = {
            column["name"]: _normalized_column_shape(column, column["name"] in indexed_columns)
            for column in item.get("columns", [])
        }
        result[item["display_name"]] = {**item, "columns_by_name": columns, "raw_columns_by_name": {column["name"]: column for column in item.get("columns", [])}}
    return result


def _normalized_column_shape(column: dict[str, Any], indexed_by_parent: bool = False) -> dict[str, Any]:
    normalized = dict(column)
    normalized["indexed"] = bool(column.get("indexed", indexed_by_parent))
    if "enforce_unique_values" in column:
        normalized["enforceUniqueValues"] = column["enforce_unique_values"]
    text = column.get("text", {})
    if "max_length" in column:
        normalized["maxLength"] = column["max_length"]
    elif isinstance(text, dict) and "maxLength" in text:
        normalized["maxLength"] = text["maxLength"]
    choice = column.get("choice", {})
    if isinstance(choice, dict) and "choices" in choice:
        normalized["choices"] = choice["choices"]
    return normalized


def _column_shape_mismatches(existing: dict[str, Any], expected: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mismatches: dict[str, dict[str, Any]] = {}
    for key in ("type", "required", "indexed", "enforceUniqueValues", "maxLength"):
        if key in expected and existing.get(key) != expected[key]:
            mismatches[key] = {"expected": expected[key], "observed": existing.get(key)}
    if "choices" in expected and existing.get("choices") != expected["choices"]:
        mismatches["choices"] = {"expected": expected["choices"], "observed": existing.get("choices")}
    return mismatches


def _missing_required_list_gaps(missing_required_lists: list[str]) -> list[dict[str, Any]]:
    return [
        _gap(
            gap_id=f"missing-required-list.{list_name}",
            target=list_name,
            gap_type="missing_required_list",
            required_for_mvp=True,
            reason="Required by the process ontology contract SharePoint projection rules.",
        )
        for list_name in missing_required_lists
    ]


def _optional_process_projections(provisioning: dict[str, Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    sharepoint = provisioning.get("sharepoint", {})
    projections: dict[str, dict[str, list[dict[str, Any]]]] = {
        "lists": {},
        "document_libraries": {},
    }
    for source_key, target_key in (("lists", "lists"), ("document_libraries", "document_libraries")):
        for resource in sharepoint.get(source_key, []):
            indexed_columns = set(resource.get("indexed_columns", []))
            expected_columns: list[dict[str, Any]] = []
            for column in resource.get("columns", []):
                expected = {
                    "name": column["name"],
                    "type": column["type"],
                    "required": bool(column.get("required", False)),
                    "indexed": column["name"] in indexed_columns,
                }
                if "choices" in column:
                    expected["choices"] = list(column["choices"])
                if column.get("enforce_unique_values") is True:
                    expected["enforceUniqueValues"] = True
                if column["name"] == "ProcessKey":
                    expected["maxLength"] = 128
                expected_columns.append(expected)
            projections[target_key][resource["display_name"]] = expected_columns
    return projections


def _optional_projection_gaps(
    list_index: dict[str, dict[str, Any]],
    library_index: dict[str, dict[str, Any]],
    optional_process_projections: dict[str, dict[str, list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    gaps.extend(
        _projection_gaps(
            list_index,
            optional_process_projections["lists"],
            required_for_mvp=False,
            missing_gap_type="missing_optional_process_projection_list",
            mismatch_gap_type="optional_process_projection_shape_mismatch",
            reason="Optional process model registry for BPMN/SPFx viewer and process template selection.",
        )
    )
    gaps.extend(
        _projection_gaps(
            library_index,
            optional_process_projections["document_libraries"],
            required_for_mvp=False,
            missing_gap_type="missing_optional_bpmn_model_library",
            mismatch_gap_type="optional_bpmn_model_library_shape_mismatch",
            reason="Optional SharePoint document library for approved BPMN model files.",
        )
    )
    return gaps


def _required_projection_gaps(list_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return _projection_gaps(
        list_index,
        REQUIRED_RUNTIME_PROJECTIONS["lists"],
        required_for_mvp=True,
        missing_gap_type="missing_required_runtime_projection_list",
        mismatch_gap_type="required_runtime_projection_shape_mismatch",
        reason="Required viewer-independent runtime projection for canonical business-case type validation.",
    )


def _projection_gaps(
    resource_index: dict[str, dict[str, Any]],
    expected_resources: dict[str, list[dict[str, Any]]],
    *,
    required_for_mvp: bool,
    missing_gap_type: str,
    mismatch_gap_type: str,
    reason: str,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for resource_name, expected_columns in expected_resources.items():
        resource = resource_index.get(resource_name)
        if resource is None:
            gaps.append(
                _gap(
                    gap_id=f"{'required' if required_for_mvp else 'optional'}-resource.{resource_name}",
                    target=resource_name,
                    gap_type=missing_gap_type,
                    required_for_mvp=required_for_mvp,
                    reason=reason,
                    planned_columns=expected_columns,
                )
            )
            continue
        existing_columns = resource.get("columns_by_name", {})
        mismatches = {
            expected["name"]: (
                {"missing": {"expected": expected, "observed": None}}
                if expected["name"] not in existing_columns
                else _column_shape_mismatches(existing_columns[expected["name"]], expected)
            )
            for expected in expected_columns
        }
        mismatches = {name: values for name, values in mismatches.items() if values}
        if mismatches:
            gaps.append(
                _gap(
                    gap_id=f"{'required' if required_for_mvp else 'optional'}-resource.{resource_name}.shape",
                    target=resource_name,
                    gap_type=mismatch_gap_type,
                    required_for_mvp=required_for_mvp,
                    reason=reason,
                    planned_columns=expected_columns,
                    shape_mismatches=mismatches,
                )
            )
    return gaps


def _field_gaps(list_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for list_name, expected_columns in EXPECTED_PROCESS_COLUMNS.items():
        existing_columns = list_index.get(list_name, {}).get("columns_by_name", {})
        for expected in expected_columns:
            existing = existing_columns.get(expected["name"])
            if existing is None:
                gaps.append(
                    _gap(
                        gap_id=f"{list_name}.{expected['name']}.missing",
                        target=list_name,
                        gap_type="missing_process_field",
                        field=expected,
                        required_for_mvp=bool(expected["required"]),
                        reason=expected["reason"],
                    )
                )
                continue
            mismatches = _column_shape_mismatches(existing, expected)
            if mismatches:
                gaps.append(
                    _gap(
                        gap_id=f"{list_name}.{expected['name']}.shape",
                        target=list_name,
                        gap_type="field_shape_mismatch",
                        field=expected,
                        required_for_mvp=bool(expected["required"]),
                        reason=expected["reason"],
                        shape_mismatches=mismatches,
                    )
                )
    return gaps


def _choice_gaps(
    list_index: dict[str, dict[str, Any]],
    all_case_slugs: list[str],
    process_phases: list[str],
    role_templates: list[str],
) -> list[dict[str, Any]]:
    checks = [
        {
            "list": "Akten",
            "field": "CurrentPhase",
            "required_choices": process_phases,
            "gap_type": "process_phase_choice_extension_plan",
            "required_for_mvp": True,
        },
        {
            "list": "AufgabenFristen",
            "field": "ProcessPhase",
            "required_choices": process_phases,
            "gap_type": "process_phase_choice_extension_plan",
            "required_for_mvp": True,
        },
        {
            "list": "Beteiligte",
            "field": "RoleTemplate",
            "required_choices": role_templates,
            "gap_type": "role_template_choice_extension_plan",
            "required_for_mvp": True,
        },
    ]
    gaps: list[dict[str, Any]] = []
    for check in checks:
        columns = list_index.get(str(check["list"]), {}).get("columns_by_name", {})
        column = columns.get(str(check["field"]))
        existing_choices = set(column.get("choices", [])) if column else set()
        missing_choices = [choice for choice in check["required_choices"] if choice not in existing_choices]
        if not missing_choices:
            continue
        gaps.append(
            _gap(
                gap_id=f"{check['list']}.{check['field']}.choices",
                target=str(check["list"]),
                gap_type=str(check["gap_type"]),
                field={"name": check["field"], "type": "choice", "required": check["required_for_mvp"]},
                required_for_mvp=bool(check["required_for_mvp"]),
                reason="Choice values are incomplete for the process ontology contract.",
                missing_choice_count=len(missing_choices),
                missing_choices=missing_choices,
            )
        )
    return gaps


def _gap(
    *,
    gap_id: str,
    target: str,
    gap_type: str,
    required_for_mvp: bool,
    reason: str,
    field: dict[str, Any] | None = None,
    planned_columns: list[dict[str, Any]] | None = None,
    existing_type: str | None = None,
    missing_choice_count: int | None = None,
    missing_choices: list[str] | None = None,
    shape_mismatches: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gap = {
        "id": gap_id,
        "target": target,
        "gap_type": gap_type,
        "mode": "plan_only",
        "required_for_mvp_process_instances": required_for_mvp,
        "reason": reason,
        "owner_gate_required_before_apply": True,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "changes_sharepoint_schema": False,
    }
    if field is not None:
        gap["field"] = field
    if planned_columns is not None:
        gap["planned_columns"] = planned_columns
    if existing_type is not None:
        gap["existing_type"] = existing_type
    if missing_choice_count is not None:
        gap["missing_choice_count"] = missing_choice_count
    if missing_choices is not None:
        gap["missing_choices"] = missing_choices
    if shape_mismatches is not None:
        gap["shape_mismatches"] = shape_mismatches
    return gap
