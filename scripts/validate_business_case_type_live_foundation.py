from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from nac_m365_graph.business_case_type_live_foundation import (  # noqa: E402
    CATALOG_VERSION,
    FOUNDATION_PATH,
    WORKSPACE_ID,
    build_business_case_type_live_foundation_plan,
    load_business_case_type_live_foundation,
    validate_business_case_type_live_foundation,
)


DOMAIN_PATH = ROOT / "workflows/contracts/business-case-type-live-foundation.contract.json"
VERIFICATION_PATH = (
    ROOT / "workflows/verification-contracts/business-case-type-live-foundation.verification.json"
)
EXPECTED_ACCEPTANCE_IDS = [f"AC-678-{number:02d}" for number in range(1, 9)]
REQUIRED_CHECKS = {
    "python3 -m unittest tests.test_business_case_type_live_foundation tests.test_business_case_type_live_foundation_cli tests.test_business_case_type_live_foundation_contract",
    "python3 scripts/validate_business_case_type_live_foundation.py",
    "python3 scripts/nac.py m365 teams-sharepoint business-case-type-live-foundation-plan --format json",
    "python3 scripts/nac.py m365 teams-sharepoint business-case-type-live-foundation-apply --help",
    "python3 scripts/quality_gate.py",
    "git diff --check",
}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain an object")
    return payload


def validate() -> list[str]:
    errors: list[str] = []
    try:
        manifest = load_business_case_type_live_foundation(ROOT)
        domain = _load(DOMAIN_PATH)
        verification = _load(VERIFICATION_PATH)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"foundation artifact load failed: {exc}"]

    manifest_validation = validate_business_case_type_live_foundation(ROOT, manifest)
    errors.extend(manifest_validation.errors)
    plan = build_business_case_type_live_foundation_plan(ROOT)
    if plan.get("status") != "PASSED":
        errors.append("foundation offline plan must pass")
    plan_sha256 = plan.get("plan_sha256")
    if not isinstance(plan_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", plan_sha256) is None:
        errors.append("foundation plan must expose a stable SHA-256")
    graph_sha256 = plan.get("binding", {}).get("graph_sha256")
    if not isinstance(graph_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", graph_sha256) is None:
        errors.append("foundation plan must hash-bind the provisioner permission boundary")
    summary = plan.get("summary", {})
    if summary.get("maximum_mutation_count") != 22:
        errors.append("foundation plan must contain at most 22 additive mutations")
    if summary.get("canonical_registry_row_count") != 20 or summary.get("alias_registry_row_count") != 0:
        errors.append("foundation plan canonical/alias row counts mismatch")
    if summary.get("executes_graph_requests") is not False or summary.get("writes_sharepoint") is not False:
        errors.append("foundation plan must remain offline")

    target = manifest.get("target", {})
    if target.get("workspace_id") != WORKSPACE_ID:
        errors.append("foundation target workspace mismatch")
    registry = manifest.get("registry", {})
    rows = registry.get("rows", [])
    if registry.get("catalog_version") != CATALOG_VERSION:
        errors.append("foundation catalog version mismatch")
    if not isinstance(rows, list) or len(rows) != 20:
        errors.append("foundation registry must contain exactly 20 rows")
    elif any(
        row.get("CatalogVersion") != CATALOG_VERSION
        or row.get("LifecycleStatus") != "active"
        or row.get("Selectable") is not True
        for row in rows
        if isinstance(row, dict)
    ):
        errors.append("foundation registry rows must share active/selectable/version state")

    criteria = domain.get("acceptance_criteria", [])
    if [item.get("id") for item in criteria if isinstance(item, dict)] != EXPECTED_ACCEPTANCE_IDS:
        errors.append("domain contract acceptance ID coverage mismatch")
    if verification.get("acceptance_ids") != EXPECTED_ACCEPTANCE_IDS:
        errors.append("verification contract acceptance ID coverage mismatch")
    graph_boundary = domain.get("graph_boundary", {})
    provisioner_binding = graph_boundary.get("provisioner_binding", {})
    if graph_boundary.get("application_permission") != "Sites.FullControl.All":
        errors.append("domain contract must bind the existing Sites.FullControl.All permission")
    if (
        provisioner_binding.get("application_display_name_exact") != "NaC M365 Provisioning"
        or provisioner_binding.get("existing_permission_required") is not True
        or provisioner_binding.get("permission_change_required") is not False
        or provisioner_binding.get("permission_mutation_allowed") is not False
    ):
        errors.append("domain contract existing provisioner no-permission-change binding mismatch")
    if set(verification.get("checks", [])) != REQUIRED_CHECKS:
        errors.append("verification contract checks mismatch")
    thresholds = verification.get("thresholds", {})
    expected_thresholds = {
        "workspace_count": 1,
        "registry_custom_column_count": 4,
        "canonical_registry_row_count": 20,
        "alias_registry_row_count": 0,
        "maximum_first_run_mutations": 22,
        "second_run_mutations": 0,
        "allowed_test_graph_calls": 0,
        "allowed_delete_calls": 0,
        "allowed_rollback_calls": 0,
    }
    if thresholds != expected_thresholds:
        errors.append("verification thresholds mismatch")

    source = (ROOT / "src/nac_m365_graph/business_case_type_live_foundation.py").read_text(
        encoding="utf-8"
    )
    for forbidden_call in ("client.patch(", "client.delete(", "urllib.request", "requests."):
        if forbidden_call in source:
            errors.append(f"foundation runner contains forbidden live/write surface: {forbidden_call}")
    cli = (ROOT / "src/nac_cli/cli.py").read_text(encoding="utf-8")
    for command in (
        "business-case-type-live-foundation-plan",
        "business-case-type-live-foundation-apply",
    ):
        if command not in cli:
            errors.append(f"central CLI missing command: {command}")
    quality_gate = (ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")
    if "validate_business_case_type_live_foundation.py" not in quality_gate:
        errors.append("quality gate missing BusinessCaseType live foundation validator")

    if not (ROOT / FOUNDATION_PATH).is_file():
        errors.append("foundation manifest path is missing")
    return errors


def main() -> int:
    errors = validate()
    print(json.dumps({"status": "PASSED" if not errors else "FAILED", "errors": errors}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
