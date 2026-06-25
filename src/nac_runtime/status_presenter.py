from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


FORBIDDEN_PUBLIC_TERMS = (
    "client_secret",
    "private_key",
    "oracle",
    "idcs",
    "claim",
    "provider",
    "tenant_id",
    "matter_id",
    "process_instance_id",
    "session_id",
    "email",
    "owner_id",
    "raw_mandate",
)


def present_first_matter_status(status: Mapping[str, Any]) -> dict[str, Any]:
    """Convert the runtime read model into a browser-safe display model."""
    _require_schema(status)

    display = {
        "schema_version": "nac.runtime-status-presenter/v0.1",
        "title": "Immobilienkaufvertrag Status",
        "status_label": "Vorgang vorbereitet",
        "summary": (
            "Vorgangsstatus ohne Mandatsdaten: notariat8 zeigt hier nur Prozessmetadaten, "
            "Sicherheitsgrenzen und vorbereitete Integrationspunkte."
        ),
        "matter_label": _public_matter_label(status),
        "status_items": _status_items(status),
        "next_steps": (
            "Vorgang als Statusansicht öffnen.",
            "Vollständiger Arbeitsbereich und Mandatsinhalte bleiben geschlossen.",
        ),
        "mandate_data_loaded": False,
        "productive_xnp_action": False,
        "full_workspace_open": False,
    }
    _reject_public_leakage(display)
    return display


def _status_items(status: Mapping[str, Any]) -> tuple[str, ...]:
    items: list[str] = [
        "Aufnahme und Beteiligte: vorbereitet.",
        "Entwurf und Abstimmung: vorbereitet.",
        "Beurkundung: vorbereitet.",
        "Vollzug: vorbereitet.",
    ]
    if status.get("bpmn_model_present") is True:
        items.append("BPMN-Modell vorhanden.")
    if status.get("xnp_snp_target_path_prepared") is True:
        items.append("XNP/SNP-Zielpfad vorbereitet.")
    if status.get("execution_path_visible") is True:
        items.append("Vollzugspfad sichtbar.")
    critical_path = _optional_text(status.get("critical_path_summary"))
    if critical_path:
        items.append(f"Kritischer Pfad: {critical_path.lower()}.")
    duration_band = _optional_text(status.get("duration_band_summary"))
    if duration_band:
        items.append(f"Dauerband: {duration_band}.")
    if status.get("parallel_work_visible") is True:
        items.append("Parallele Arbeitsschritte erkennbar.")
    items.append("Keine Mandatsdaten geladen.")
    return tuple(items)


def _public_matter_label(status: Mapping[str, Any]) -> str:
    label = _optional_text(status.get("matter_label"))
    return label if label == "Immobilienkaufvertrag" else "Erster Vorgang"


def _require_schema(status: Mapping[str, Any]) -> None:
    if status.get("schema_version") != "nac.runtime-status-read-model/v0.1":
        raise ValueError("runtime_status_schema_unsupported")
    if status.get("mandate_data_loaded") is not False:
        raise ValueError("runtime_status_mandate_data_not_allowed")
    if status.get("productive_xnp_action") is not False:
        raise ValueError("runtime_status_productive_xnp_action_not_allowed")
    if status.get("full_workspace_open") is not False:
        raise ValueError("runtime_status_full_workspace_not_allowed")


def _reject_public_leakage(display: Mapping[str, Any]) -> None:
    serialized = json.dumps(display, ensure_ascii=False, sort_keys=True).lower()
    for term in FORBIDDEN_PUBLIC_TERMS:
        if term in serialized:
            raise ValueError("runtime_status_presenter_forbidden_term: " + term)


def _optional_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""
