from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

src_root_text = str(SRC_ROOT)
if src_root_text in sys.path:
    sys.path.remove(src_root_text)
sys.path.insert(0, src_root_text)

from nac_gnotkg.costs import calculate_value_fee  # noqa: E402
from nac_gnotkg.views import build_cost_review_view  # noqa: E402
from notary_kg.catalog import all_case_summaries, load_catalogs  # noqa: E402


CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "gnotkg-cost-review.contract.json"
KNOWN_TABLE_VALUES = {
    "A": {
        "500": "40.00",
        "500000": "4138.00",
        "3000000": "14638.00",
        "10000000": "44038.00",
    },
    "B": {
        "500": "15.00",
        "500000": "935.00",
        "3000000": "4935.00",
        "10000000": "11385.00",
    },
}
REQUIRED_NODE_IDS = {
    "cost.business_value",
    "decision.gnotkg_cost_path",
    "gate.gnotkg_cost_review",
    "evidence.gnotkg_cost_note",
}


def main() -> int:
    errors: list[str] = []
    if not CONTRACT_PATH.exists():
        errors.append("Missing workflows/contracts/gnotkg-cost-review.contract.json")
    else:
        _validate_contract(CONTRACT_PATH, errors)

    _validate_table_values(errors)
    _validate_cost_views(errors)

    if errors:
        print("GNotKG cost validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("GNotKG cost validation passed.")
    return 0


def _validate_contract(path: Path, errors: list[str]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("contract_id") != "workflow.gnotkg_cost_review":
        errors.append("GNotKG contract has unexpected contract_id")
    if payload.get("runtime", {}).get("python_module") != "nac_gnotkg":
        errors.append("GNotKG contract must point to nac_gnotkg runtime")
    guardrails = payload.get("guardrails", {})
    if guardrails.get("real_mandate_data_in_git") is not False:
        errors.append("GNotKG contract must block real mandate data in Git")
    if guardrails.get("xyflow_calculates_fees") is not False:
        errors.append("GNotKG contract must keep xyflow out of fee calculation")
    if guardrails.get("notarial_review_required") is not True:
        errors.append("GNotKG contract must require notarial review")
    if payload.get("xyflow_contract", {}).get("preferred_renderer") != "xyflow":
        errors.append("GNotKG contract must document xyflow as preferred renderer")
    if "https://www.gesetze-im-internet.de/gnotkg/__35.html" not in payload.get("source_law", []):
        errors.append("GNotKG contract must include §35 value caps")


def _validate_table_values(errors: list[str]) -> None:
    for table, examples in KNOWN_TABLE_VALUES.items():
        for business_value, expected in examples.items():
            actual = calculate_value_fee(Decimal(business_value), table)
            if actual != Decimal(expected):
                errors.append(f"Table {table} value {business_value}: {actual} != {expected}")


def _validate_cost_views(errors: list[str]) -> None:
    for case in all_case_summaries(load_catalogs(REPO_ROOT)):
        try:
            view = build_cost_review_view(REPO_ROOT, case.slug)
        except (KeyError, ValueError) as exc:
            errors.append(f"{case.slug}: {exc}")
            continue
        node_ids = {node.get("id") for node in view.get("nodes", []) if isinstance(node, dict)}
        missing = REQUIRED_NODE_IDS - node_ids
        if missing:
            errors.append(f"{case.slug}: missing cost nodes {sorted(missing)}")
        if _contains_key(view, "value"):
            errors.append(f"{case.slug}: cost view exposes forbidden value key")
        guardrails = view.get("guardrails", {})
        if guardrails.get("real_mandate_data_in_git") is not False:
            errors.append(f"{case.slug}: cost view must block real mandate data in Git")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


if __name__ == "__main__":
    raise SystemExit(main())
