from __future__ import annotations

from typing import Any, Protocol

from nac_runtime.graph_projection import project_process_graph
from nac_runtime.store import RuntimeRecord


class ProcessEventReader(Protocol):
    def list_process_events(self, process_instance_id: str) -> list[RuntimeRecord]:
        """Return process events for a runtime process instance."""


def build_first_matter_status(*, store: ProcessEventReader, process_instance_id: str) -> dict[str, Any]:
    _require_text(process_instance_id, "process_instance_id_missing")
    events = store.list_process_events(process_instance_id)
    if not events:
        raise ValueError("runtime_status_process_events_missing")

    graph = project_process_graph(process_instance_id=process_instance_id, events=events)
    labels = {str(node.get("label", "")) for node in graph["nodes"]}

    return {
        "schema_version": "nac.runtime-status-read-model/v0.1",
        "status": "portal_start_metadata_ready",
        "matter_label": "Immobilienkaufvertrag",
        "bpmn_model_present": "xnp_local_readiness_only" in labels,
        "xnp_snp_target_path_prepared": "xnp_snp_target_metadata_only" in labels,
        "execution_path_visible": bool(graph["nodes"]) and bool(graph["edges"]),
        "critical_path_summary": _critical_path_summary(graph),
        "duration_band_summary": _duration_band_summary(graph),
        "parallel_work_visible": bool(graph["parallel_groups"]),
        "mandate_data_loaded": False,
        "productive_xnp_action": False,
        "full_workspace_open": False,
    }


def _critical_path_summary(graph: dict[str, Any]) -> str:
    critical_path = graph.get("critical_path")
    if isinstance(critical_path, list) and critical_path:
        return "Externer Rücklauf"
    return "Nicht bestimmt"


def _duration_band_summary(graph: dict[str, Any]) -> str:
    duration_bands = graph.get("duration_bands")
    if isinstance(duration_bands, list) and "weeks_to_months" in duration_bands:
        return "Wochen bis Monate"
    if isinstance(duration_bands, list) and "weeks" in duration_bands:
        return "Wochen"
    return "Stunden bis Tage"


def _require_text(value: str, message: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(message)
