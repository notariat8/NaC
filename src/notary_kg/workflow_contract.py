from __future__ import annotations

from pathlib import Path
from typing import Any

from .catalog import load_catalogs


WORKFLOW_CONTRACT_ACTIONS = (
    "review_generated_contract",
    "fill_contract_guardrails_without_mandate_data",
    "validate_contract",
    "create_pull_request",
)


def build_workflow_contract_draft(repo_root: Path, slug: str) -> dict[str, Any]:
    """Build a safe workflow-contract draft from one usecase-local KG."""

    catalog, case = _find_case_payload(repo_root=repo_root, slug=slug)
    return {
        "schema_version": "nac.workflow-contract-draft/v0.1",
        "contract_id": "workflow." + str(case.get("slug", "")).replace("-", "_"),
        "status": "draft_from_knowledge_graph",
        "title": str(case.get("title", "")),
        "source": {
            "graph_id": catalog.graph_id,
            "case_id": str(case.get("id", "")),
            "usecase_slug": str(case.get("slug", "")),
            "usecase_path": str(case.get("usecase_path", "")),
            "catalog_source": _catalog_source(repo_root, catalog.source_path),
        },
        "purpose": _purpose(case),
        "intake": {
            "required_information": [
                _sanitize_required_information(item)
                for item in _as_dict_list(case.get("required_information"))
            ],
            "documents": [
                _sanitize_item(item, ("id", "label", "status", "source", "contains_personal_data"))
                for item in _as_dict_list(case.get("documents"))
            ],
            "decisions": [
                _sanitize_item(item, ("id", "label", "status", "options"))
                for item in _as_dict_list(case.get("decisions"))
            ],
        },
        "gates": [
            _sanitize_item(item, ("id", "label", "status", "owner_role"))
            for item in _as_dict_list(case.get("gates"))
        ],
        "evidence": [
            _sanitize_item(item, ("id", "label", "status"))
            for item in _as_dict_list(case.get("evidence"))
        ],
        "dependencies": {
            "plugins": _text_list(case.get("plugin_dependencies")),
            "workflows": _text_list(case.get("workflow_dependencies")),
            "legal_anchors": _text_list(case.get("legal_anchors")),
        },
        "guardrails": {
            "real_mandate_data_in_git": False,
            "value_fields_included": False,
            "secrets_included": False,
            "productive_external_action": False,
            "owner_review_required_before_use": True,
            "protected_pr_required": True,
        },
        "proposal_policy": {
            "mode": "proposal_only",
            "actions": [{"name": name} for name in WORKFLOW_CONTRACT_ACTIONS],
            "forbidden_fields": ["value"],
            "storage_boundary": (
                "Generated draft contains workflow metadata only; "
                "real mandate data stays outside the product repository."
            ),
        },
        "validation_commands": [
            "python scripts/validate_knowledge_graph.py",
            f"python scripts/notary_kg.py --repo-root . --format json workflow-contract {case.get('slug', '')}",
        ],
    }


def _find_case_payload(repo_root: Path, slug: str) -> tuple[Any, dict[str, Any]]:
    for catalog in load_catalogs(repo_root):
        for case in catalog.payload.get("cases", []):
            if isinstance(case, dict) and case.get("slug") == slug:
                return catalog, case
    raise KeyError(f"Unknown KG case slug: {slug}")


def _purpose(case: dict[str, Any]) -> str:
    summary = case.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    return "Draft workflow contract generated from the usecase-local knowledge graph."


def _sanitize_required_information(item: dict[str, Any]) -> dict[str, Any]:
    return _sanitize_item(
        item,
        (
            "id",
            "label",
            "question",
            "status",
            "owner_role",
            "privacy_class",
            "required_for",
        ),
    )


def _sanitize_item(item: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: item[field] for field in fields if field in item}


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _text_list(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def _catalog_source(repo_root: Path, source_path: Path) -> str:
    try:
        return str(source_path.relative_to(repo_root))
    except ValueError:
        return str(source_path)
