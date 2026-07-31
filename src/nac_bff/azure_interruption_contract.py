from __future__ import annotations

import hashlib
import json
from typing import Any


RESOURCE_GROUP_ONLY = "RESOURCE_GROUP_ONLY"
BICEP_BASELINE_EXACT = "BICEP_BASELINE_EXACT"


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
