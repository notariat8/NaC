from __future__ import annotations

from pathlib import Path
from typing import Any

from .catalog import load_catalogs


ALLOWED_STATUS = ("open", "in_progress", "provided", "blocked", "not_applicable")
EDITOR_ACTIONS = (
    "get_graph",
    "propose_patch",
    "validate_graph_patch",
    "create_pull_request",
)
PATCH_PIPELINE = (
    "natural_language_instruction",
    "structured_patch_proposal",
    "kg_schema_validation",
    "privacy_policy_check",
    "diff_review",
    "user_confirmation",
    "pull_request",
)


TAB_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "open_information",
        "label_de": "Offene Angaben",
        "label_en": "Open Information",
        "render_as": "checklist",
        "source": "required_information",
        "fields": (
            "id",
            "label",
            "question",
            "status",
            "owner_role",
            "privacy_class",
            "required_for",
        ),
        "editable_fields": ("status", "owner_role", "required_for"),
        "blocked_fields": ("value",),
    },
    {
        "id": "documents",
        "label_de": "Dokumente",
        "label_en": "Documents",
        "render_as": "document_status_list",
        "source": "documents",
        "fields": ("id", "label", "status", "source", "contains_personal_data"),
        "editable_fields": ("status", "source"),
        "blocked_fields": ("value",),
    },
    {
        "id": "decisions",
        "label_de": "Entscheidungen",
        "label_en": "Decisions",
        "render_as": "decision_dropdowns",
        "source": "decisions",
        "fields": ("id", "label", "status", "options"),
        "editable_fields": ("status", "options"),
        "blocked_fields": ("value",),
    },
    {
        "id": "gates_evidence",
        "label_de": "Gates/Evidence",
        "label_en": "Gates/Evidence",
        "render_as": "gate_evidence_review",
        "source_groups": (
            {
                "id": "gates",
                "label_de": "Gates",
                "label_en": "Gates",
                "source": "gates",
                "fields": ("id", "label", "status", "owner_role"),
                "editable_fields": ("status", "owner_role"),
            },
            {
                "id": "evidence",
                "label_de": "Evidence",
                "label_en": "Evidence",
                "source": "evidence",
                "fields": ("id", "label", "status"),
                "editable_fields": ("status",),
            },
        ),
        "blocked_fields": ("value",),
    },
)


def build_editor_view(repo_root: Path, slug: str) -> dict[str, Any]:
    """Build the safe, form-oriented view for one usecase-local KG."""

    catalog, case = _find_case_payload(repo_root=repo_root, slug=slug)
    tabs = [_build_tab(case, tab_definition) for tab_definition in TAB_DEFINITIONS]

    return {
        "schema_version": "noc.kg-editor-view/v0.1",
        "graph_id": catalog.graph_id,
        "case_id": str(case.get("id", "")),
        "usecase_slug": str(case.get("slug", "")),
        "title": str(case.get("title", "")),
        "status": str(case.get("status", "unknown")),
        "usecase_path": str(case.get("usecase_path", "")),
        "editor_model": {
            "audience": "fachpersonal_without_programming_knowledge",
            "primary_language": "de",
            "json_role": "static_machine_representation",
            "interaction_model": "chat_first_form_and_checklist_editor",
            "tabs": tabs,
        },
        "actions": [{"name": name} for name in EDITOR_ACTIONS],
        "patch_policy": {
            "mode": "proposal_only",
            "pipeline": list(PATCH_PIPELINE),
            "schema": "schemas/kg-editor-patch.schema.json",
            "forbidden_fields": ["value"],
            "privacy_guardrail": "No real mandate data, personal data, property data, health data, estate data or secrets may be stored in Git.",
            "confirmation_required": True,
        },
    }


def _find_case_payload(
    repo_root: Path,
    slug: str,
) -> tuple[Any, dict[str, Any]]:
    for catalog in load_catalogs(repo_root):
        for case in catalog.payload.get("cases", []):
            if isinstance(case, dict) and case.get("slug") == slug:
                return catalog, case
    raise KeyError(f"Unknown KG case slug: {slug}")


def _build_tab(case: dict[str, Any], definition: dict[str, Any]) -> dict[str, Any]:
    if "source_groups" in definition:
        groups = [_build_group(case, group) for group in definition["source_groups"]]
        item_count = sum(group["item_count"] for group in groups)
        editable_fields = sorted(
            {
                field
                for group in definition["source_groups"]
                for field in group.get("editable_fields", ())
            }
        )
        return {
            "id": definition["id"],
            "label_de": definition["label_de"],
            "label_en": definition["label_en"],
            "render_as": definition["render_as"],
            "item_count": item_count,
            "editable_fields": editable_fields,
            "blocked_fields": list(definition.get("blocked_fields", ())),
            "allowed_status": list(ALLOWED_STATUS),
            "groups": groups,
        }

    source = definition["source"]
    items = [
        _sanitize_item(item, definition["fields"])
        for item in _as_dict_list(case.get(source))
    ]
    return {
        "id": definition["id"],
        "label_de": definition["label_de"],
        "label_en": definition["label_en"],
        "render_as": definition["render_as"],
        "source": source,
        "item_count": len(items),
        "editable_fields": list(definition.get("editable_fields", ())),
        "blocked_fields": list(definition.get("blocked_fields", ())),
        "allowed_status": list(ALLOWED_STATUS),
        "items": items,
    }


def _build_group(case: dict[str, Any], definition: dict[str, Any]) -> dict[str, Any]:
    source = definition["source"]
    items = [
        _sanitize_item(item, definition["fields"])
        for item in _as_dict_list(case.get(source))
    ]
    return {
        "id": definition["id"],
        "label_de": definition["label_de"],
        "label_en": definition["label_en"],
        "source": source,
        "item_count": len(items),
        "editable_fields": list(definition.get("editable_fields", ())),
        "items": items,
    }


def _sanitize_item(item: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: item[field] for field in fields if field in item}


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
