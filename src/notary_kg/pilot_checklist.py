from __future__ import annotations

from pathlib import Path
from typing import Any

from .catalog import load_catalogs


PILOT_ACTIONS = (
    "review_intake_checklist",
    "confirm_open_questions",
    "bind_workflow_version",
    "create_pull_request",
)


def build_pilot_intake_checklist(repo_root: Path, slug: str) -> dict[str, Any]:
    """Build a deterministic, mandate-data-free pilot intake checklist."""

    catalog, case = _find_case_payload(repo_root=repo_root, slug=slug)
    required_information = _as_dict_list(case.get("required_information"))
    documents = _as_dict_list(case.get("documents"))
    decisions = _as_dict_list(case.get("decisions"))
    gates = _as_dict_list(case.get("gates"))
    evidence = _as_dict_list(case.get("evidence"))

    return {
        "schema_version": "nac.pilot-intake-checklist/v0.1",
        "status": "draft_from_knowledge_graph",
        "pilot_usecase": {
            "graph_id": catalog.graph_id,
            "case_id": str(case.get("id", "")),
            "slug": str(case.get("slug", "")),
            "title": str(case.get("title", "")),
            "usecase_path": str(case.get("usecase_path", "")),
            "catalog_source": _catalog_source(repo_root, catalog.source_path),
        },
        "workflow_binding": {
            "workflow_id": f"{case.get('slug', '')}:pilot-intake",
            "workflow_version": "v0.1",
            "source": "usecase-local knowledge graph",
            "approval_state": "draft_requires_notarial_review",
        },
        "sections": [
            _section(
                "required_information",
                "Offene Angaben",
                [_required_information_item(item, index) for index, item in enumerate(required_information, start=1)],
            ),
            _section(
                "documents",
                "Dokumente",
                [_simple_item(item, index) for index, item in enumerate(documents, start=1)],
            ),
            _section(
                "decisions",
                "Entscheidungen",
                [_decision_item(item, index) for index, item in enumerate(decisions, start=1)],
            ),
            _section(
                "gates",
                "Prüfgates",
                [_simple_item(item, index) for index, item in enumerate(gates, start=1)],
            ),
            _section(
                "evidence",
                "Nachweise",
                [_simple_item(item, index) for index, item in enumerate(evidence, start=1)],
            ),
        ],
        "summary": {
            "total_items": len(required_information) + len(documents) + len(decisions) + len(gates) + len(evidence),
            "open_items": (
                _open_count(required_information)
                + _open_count(documents)
                + _open_count(decisions)
                + _open_count(gates)
                + _open_count(evidence)
            ),
            "plugin_dependencies": _text_list(case.get("plugin_dependencies")),
            "workflow_dependencies": _text_list(case.get("workflow_dependencies")),
            "legal_anchors": _text_list(case.get("legal_anchors")),
            "next_step": _next_step(required_information, documents, decisions, gates, evidence),
        },
        "guardrails": {
            "real_mandate_data_in_git": False,
            "value_fields_included": False,
            "secrets_included": False,
            "productive_register_or_xnp_action": False,
            "notarial_review_required_before_use": True,
            "protected_pr_required": True,
        },
        "actions": [{"name": name} for name in PILOT_ACTIONS],
    }


def _find_case_payload(repo_root: Path, slug: str) -> tuple[Any, dict[str, Any]]:
    for catalog in load_catalogs(repo_root):
        for case in catalog.payload.get("cases", []):
            if isinstance(case, dict) and case.get("slug") == slug:
                return catalog, case
    raise KeyError(f"Unknown KG case slug: {slug}")


def _section(section_id: str, label_de: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": section_id,
        "label_de": label_de,
        "item_count": len(items),
        "open_count": _open_count(items),
        "items": items,
    }


def _required_information_item(item: dict[str, Any], order: int) -> dict[str, Any]:
    payload = _simple_item(item, order)
    for key in ("question", "owner_role", "privacy_class", "required_for"):
        if key in item:
            payload[key] = item[key]
    return payload


def _decision_item(item: dict[str, Any], order: int) -> dict[str, Any]:
    payload = _simple_item(item, order)
    if "options" in item:
        payload["options"] = item["options"]
    return payload


def _simple_item(item: dict[str, Any], order: int) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")),
        "label": str(item.get("label", "")),
        "status": str(item.get("status", "open")),
        "order": order,
    }


def _next_step(*groups: list[dict[str, Any]]) -> dict[str, Any]:
    for group in groups:
        for item in group:
            if item.get("status") == "open":
                return {
                    "id": str(item.get("id", "")),
                    "label": str(item.get("label", "")),
                    "status": "open",
                }
    return {"id": "", "label": "", "status": "complete"}


def _open_count(items: list[dict[str, Any]]) -> int:
    return sum(1 for item in items if item.get("status") == "open")


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _text_list(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def _catalog_source(repo_root: Path, source_path: Path) -> str:
    try:
        return str(source_path.relative_to(repo_root))
    except ValueError:
        return str(source_path)
