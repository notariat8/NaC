from __future__ import annotations

import hashlib
import json
from typing import Any


RESOURCE_GROUP_ONLY = "RESOURCE_GROUP_ONLY"
BICEP_BASELINE_EXACT = "BICEP_BASELINE_EXACT"
RESOURCE_GRAPH_VISIBLE_OPERATION_TYPES = frozenset({
    "microsoft.authorization/roleassignments",
})


def compact_sha256_json(value: object) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def newline_sha256_json(value: object) -> str:
    raw = (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        + "\n"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def resource_graph_visible_targets(
    inventory: object,
    operations: object,
) -> list[dict[str, str]] | None:
    if not isinstance(inventory, list) or not isinstance(operations, list):
        return None
    selected: list[object] = list(inventory)
    for operation in operations:
        if not isinstance(operation, dict):
            return None
        resource_type = operation.get("type")
        if not isinstance(resource_type, str):
            return None
        if resource_type.lower() in RESOURCE_GRAPH_VISIBLE_OPERATION_TYPES:
            selected.append(operation)

    targets: dict[str, str] = {}
    for item in selected:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not isinstance(item.get("type"), str)
        ):
            return None
        resource_id = item["id"].lower()
        resource_type = item["type"].lower()
        if not resource_id or not resource_type:
            return None
        if resource_id in targets and targets[resource_id] != resource_type:
            return None
        targets[resource_id] = resource_type
    return sorted(
        ({"id": key, "type": value} for key, value in targets.items()),
        key=lambda item: (item["type"], item["id"]),
    )


def canonical_parameters_from_wrappers(
    value: dict[str, Any],
) -> dict[str, Any]:
    canonical: dict[str, Any] = {}
    for key in sorted(value):
        wrapper = value[key]
        if not isinstance(wrapper, dict) or set(wrapper) not in (
            {"value"},
            {"type", "value"},
        ):
            raise ValueError("deployment parameter wrapper invalid")
        canonical[key] = {"value": wrapper["value"]}
    return canonical
