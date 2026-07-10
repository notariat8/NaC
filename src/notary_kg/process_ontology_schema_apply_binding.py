from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .process_ontology_schema_apply_plan import build_process_ontology_sharepoint_schema_apply_plan
from .process_ontology_schema_apply_readiness import build_process_ontology_sharepoint_schema_apply_readiness


SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-apply-binding/v0.1"


def build_process_ontology_sharepoint_schema_apply_binding(
    repo_root: Path,
    workspace_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    readiness = build_process_ontology_sharepoint_schema_apply_readiness(repo_root)
    apply_plan = build_process_ontology_sharepoint_schema_apply_plan(repo_root)
    workspaces_by_id = {str(workspace["workspace_id"]): workspace for workspace in readiness["workspaces"]}
    selected_ids = _selected_workspace_ids(workspaces_by_id, workspace_ids)
    selected_workspaces = [workspaces_by_id[workspace_id] for workspace_id in selected_ids]

    apply_plan_sha256 = _payload_sha256(apply_plan)
    workspace_readiness_sha256 = _payload_sha256({**readiness, "workspaces": selected_workspaces})
    workspace_bindings = [
        {
            "workspace_id": workspace["workspace_id"],
            "site_id_sha256": _text_sha256(str(workspace["site_id"])),
            "apply_unit_count": len(workspace["apply_units"]),
        }
        for workspace in selected_workspaces
    ]
    binding_source = {
        "workspace_ids": selected_ids,
        "workspace_bindings": workspace_bindings,
        "apply_plan_sha256": apply_plan_sha256,
        "workspace_readiness_sha256": workspace_readiness_sha256,
        "selected_apply_unit_count": sum(item["apply_unit_count"] for item in workspace_bindings),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        **binding_source,
        "binding_sha256": _payload_sha256(binding_source),
    }


def _selected_workspace_ids(
    workspaces_by_id: dict[str, dict[str, Any]],
    workspace_ids: Iterable[str] | None,
) -> list[str]:
    requested = list(dict.fromkeys(str(value).strip() for value in (workspace_ids or []) if str(value).strip()))
    selected = requested or list(workspaces_by_id)
    unknown = [workspace_id for workspace_id in selected if workspace_id not in workspaces_by_id]
    if unknown:
        raise ValueError(f"unknown process ontology schema apply workspace: {', '.join(unknown)}")
    return selected


def _payload_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _text_sha256(canonical)


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
