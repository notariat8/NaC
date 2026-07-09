from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
src_root_text = str(SRC_ROOT)
if src_root_text in sys.path:
    sys.path.remove(src_root_text)
sys.path.insert(0, src_root_text)

from notary_kg.process_ontology_schema_apply_readiness import (  # noqa: E402
    build_process_ontology_sharepoint_schema_apply_readiness,
    validate_process_ontology_sharepoint_schema_apply_readiness,
)


PROHIBITED_MARKERS = {
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "Authorization",
    "Bearer ",
    "ghp_",
    "gho_",
    "raw_mandate",
    "mandatsdaten",
}


def main() -> int:
    errors: list[str] = []
    payload = build_process_ontology_sharepoint_schema_apply_readiness(REPO_ROOT)
    validation = validate_process_ontology_sharepoint_schema_apply_readiness(payload)
    errors.extend(validation.errors)

    summary = payload.get("summary", {})
    if summary.get("workspace_count") != 2:
        errors.append("expected two provisioned notary workspaces")
    if summary.get("apply_plan_step_count") != 34:
        errors.append("expected 34 source apply-plan steps")
    if summary.get("workspace_apply_unit_count") != 68:
        errors.append("expected 68 workspace apply units")
    if summary.get("known_site_id_count") != 2:
        errors.append("expected known site IDs for both workspaces")
    if summary.get("missing_required_list_id_count") != 0:
        errors.append("expected no missing required list IDs")
    if summary.get("dynamic_resource_resolution_count") != 12:
        errors.append("expected 12 dynamic ID resolutions across both workspaces")
    if summary.get("live_apply_readiness") != "OWNER_GATE_REQUIRED":
        errors.append("live apply must remain owner-gated")

    permission = payload.get("permission_readiness", {})
    if permission.get("required_application_permission") != "Sites.Manage.All":
        errors.append("expected Sites.Manage.All as required application permission")
    if permission.get("permission_present_in_provisioned_state") is not True:
        errors.append("Sites.Manage.All must be visible in provisioned state")
    if permission.get("delegated_user_context_allowed_for_live_apply") is not False:
        errors.append("delegated user context must stay blocked for live schema apply")

    for workspace in payload.get("workspaces", []):
        if workspace.get("summary", {}).get("workspace_apply_unit_count") != 34:
            errors.append(f"{workspace.get('workspace_id')}: expected 34 apply units")
        if workspace.get("summary", {}).get("dynamic_resource_resolution_count") != 6:
            errors.append(f"{workspace.get('workspace_id')}: expected six dynamic ID resolutions")
        if workspace.get("summary", {}).get("missing_required_list_id_count") != 0:
            errors.append(f"{workspace.get('workspace_id')}: missing required list IDs")

    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    lowered = serialized.lower()
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"prohibited marker found: {marker}")

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print(
        "OK: Process ontology SharePoint schema apply readiness is offline, "
        "workspace-expanded and owner-gated before live apply."
    )
    print(
        "READINESS: "
        f"{summary['workspace_count']} workspaces, "
        f"{summary['workspace_apply_unit_count']} workspace apply units, "
        f"{summary['dynamic_resource_resolution_count']} dynamic ID resolutions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
