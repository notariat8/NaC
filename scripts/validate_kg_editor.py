from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

src_root_text = str(SRC_ROOT)
if src_root_text in sys.path:
    sys.path.remove(src_root_text)
sys.path.insert(0, src_root_text)

from notary_kg.catalog import all_case_summaries, load_catalogs  # noqa: E402
from notary_kg.editor import build_editor_view  # noqa: E402


REQUIRED_TABS = ["open_information", "documents", "decisions", "gates_evidence"]
REQUIRED_ACTIONS = [
    "get_graph",
    "propose_patch",
    "validate_graph_patch",
    "create_pull_request",
]


def main() -> int:
    errors: list[str] = []

    schema_path = REPO_ROOT / "schemas" / "kg-editor-patch.schema.json"
    contract_path = REPO_ROOT / "workflows" / "contracts" / "kg-editor.contract.json"
    if not schema_path.exists():
        errors.append("Missing schemas/kg-editor-patch.schema.json")
    if not contract_path.exists():
        errors.append("Missing workflows/contracts/kg-editor.contract.json")

    for case in all_case_summaries(load_catalogs(REPO_ROOT)):
        try:
            view = build_editor_view(REPO_ROOT, case.slug)
        except KeyError as exc:
            errors.append(str(exc))
            continue

        tab_ids = [tab.get("id") for tab in view.get("editor_model", {}).get("tabs", [])]
        if tab_ids != REQUIRED_TABS:
            errors.append(f"{case.slug}: editor tabs are {tab_ids}, expected {REQUIRED_TABS}")

        action_names = [action.get("name") for action in view.get("actions", [])]
        if action_names != REQUIRED_ACTIONS:
            errors.append(f"{case.slug}: editor actions are {action_names}, expected {REQUIRED_ACTIONS}")

        if _contains_key(view, "value"):
            errors.append(f"{case.slug}: editor view exposes a forbidden value key")

    if schema_path.exists():
        _validate_schema_file(schema_path, errors)
    if contract_path.exists():
        _validate_contract_file(contract_path, errors)

    if errors:
        print("KG editor validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("KG editor validation passed.")
    return 0


def _validate_schema_file(path: Path, errors: list[str]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("$id") != "https://noc.local/schemas/kg-editor-patch.schema.json":
        errors.append("KG editor patch schema has unexpected $id")
    operations = payload.get("properties", {}).get("operations", {})
    item_properties = operations.get("items", {}).get("properties", {})
    field_enum = item_properties.get("field", {}).get("enum", [])
    if "value" in field_enum:
        errors.append("KG editor patch schema allows field=value")


def _validate_contract_file(path: Path, errors: list[str]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("contract_id") != "workflow.kg_editor":
        errors.append("KG editor workflow contract has unexpected contract_id")
    if payload.get("guardrails", {}).get("value_fields_editable") is not False:
        errors.append("KG editor workflow contract must make value fields non-editable")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


if __name__ == "__main__":
    raise SystemExit(main())
