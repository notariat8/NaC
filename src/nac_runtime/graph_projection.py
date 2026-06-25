from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from nac_runtime.store import RuntimeRecord


FORBIDDEN_TERMS = ("client_secret", "private_key", "raw_mandate", "mandatsdaten", "owner_id")


def project_process_graph(*, process_instance_id: str, events: Iterable[RuntimeRecord]) -> dict[str, Any]:
    _require_text(process_instance_id, "process_instance_id_missing")
    ordered_events = sorted(list(events), key=lambda event: event.sequence)
    nodes: dict[str, dict[str, Any]] = {
        _node_id("process", process_instance_id): {
            "id": _node_id("process", process_instance_id),
            "type": "process_instance",
            "label": "process_instance",
        }
    }
    edges: dict[str, dict[str, str]] = {}
    duration_bands: list[str] = []
    parallel_groups: list[str] = []
    critical_path: list[dict[str, str]] = []

    for event in ordered_events:
        if event.record_type != "process_event" or event.process_instance_id != process_instance_id:
            raise ValueError("process_event_scope_mismatch")
        _reject_forbidden_payload(event.payload)

        gate = _optional_text(event.payload.get("gate"))
        step = _optional_text(event.payload.get("step"))
        external_system = _optional_text(event.payload.get("external_system"))
        duration_band = _optional_text(event.payload.get("duration_band"))
        parallel_group = _optional_text(event.payload.get("parallel_group"))

        if duration_band and duration_band not in duration_bands:
            duration_bands.append(duration_band)
        if parallel_group and parallel_group not in parallel_groups:
            parallel_groups.append(parallel_group)

        target_node_id = _node_id("process", process_instance_id)
        if gate:
            target_node_id = _node_id("gate", gate)
            nodes[target_node_id] = {
                "id": target_node_id,
                "type": "gate",
                "label": gate,
                "event_type": event.event_type,
                "step": step,
                "duration_band": duration_band,
                "parallel_group": parallel_group,
            }
            edge_id = f"event:{event.record_id}->gate:{gate}"
            edges[edge_id] = {
                "id": edge_id,
                "source": _node_id("process", process_instance_id),
                "target": target_node_id,
                "type": "has_event_gate",
            }

        if external_system and gate:
            external_node_id = _node_id("external", external_system)
            nodes[external_node_id] = {
                "id": external_node_id,
                "type": "external_system",
                "label": external_system,
            }
            edge_id = f"external:{external_system}->gate:{gate}"
            edges[edge_id] = {
                "id": edge_id,
                "source": external_node_id,
                "target": target_node_id,
                "type": "touches_gate",
            }

        for dependency in _text_list(event.payload.get("depends_on")):
            if not gate:
                continue
            edge_id = f"dependency:{dependency}->{gate}"
            edges[edge_id] = {
                "id": edge_id,
                "source": _node_id("gate", dependency),
                "target": target_node_id,
                "type": "depends_on",
            }

        if bool(event.payload.get("critical_path")) and gate:
            critical_path.append(
                {
                    "gate": gate,
                    "duration_band": duration_band or "unspecified",
                }
            )

    return {
        "schema_version": "nac.atp-runtime-graph-projection/v0.1",
        "projection_status": "derived_from_process_events",
        "process_instance_ref": process_instance_id,
        "live_oci_enabled": False,
        "schema_apply_enabled": False,
        "mandate_data_loaded": False,
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
        "critical_path": critical_path,
        "parallel_groups": parallel_groups,
        "duration_bands": duration_bands,
    }


def _node_id(kind: str, value: str) -> str:
    return f"{kind}:{value}"


def _optional_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _reject_forbidden_payload(payload: Mapping[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    for term in FORBIDDEN_TERMS:
        if term in serialized:
            raise ValueError("runtime_graph_payload_forbidden_term: " + term)


def _require_text(value: str, message: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(message)
