from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nac_runtime.store import RuntimeStoreAdapter


def seed_notarkammer_first_matter(*, store: RuntimeStoreAdapter, fixture: Mapping[str, Any]) -> dict[str, Any]:
    _validate_demo_fixture(fixture)

    tenant_id = _required_text(fixture.get("tenant_demo_id"), "tenant_demo_id_missing")
    matter_id = _required_text(fixture.get("matter_demo_id"), "matter_demo_id_missing")
    usecase_slug = _required_text(fixture.get("usecase_slug"), "usecase_slug_missing")
    process_instance_id = "DEMO-PROCESS-IMMOBILIENKAUF-01"

    store.put_tenant(
        tenant_id=tenant_id,
        payload={
            "demo_context": fixture.get("demo_context"),
            "scope": "metadata_only",
            "target_systems": _text_list(fixture.get("target_systems")),
        },
    )
    store.put_matter(
        matter_id=matter_id,
        tenant_id=tenant_id,
        payload={
            "usecase_slug": usecase_slug,
            "primary_matter_type": fixture.get("primary_matter_type"),
            "bpmn_model": fixture.get("bpmn_model"),
            "kg_ref": fixture.get("kg_ref"),
            "scope": "metadata_only",
        },
    )
    store.put_process_instance(
        process_instance_id=process_instance_id,
        tenant_id=tenant_id,
        matter_id=matter_id,
        payload={
            "entry_contract": fixture.get("entry_contract"),
            "data_model_slice": _optional_text(fixture.get("data_model_slice")) or "runtime_graph_metadata_v0",
            "graph_projection_contract": "nac.atp-runtime-graph-projection/v0.1",
            "status": "portal_start_metadata_ready",
            "full_workspace_open": False,
            "mandate_data_loaded": False,
        },
    )

    _append_gate_events(
        store=store,
        tenant_id=tenant_id,
        process_instance_id=process_instance_id,
        fixture=fixture,
    )
    store.append_audit_event(
        audit_event_id="DEMO-AUDIT-IMMOBILIENKAUF-SEED-01",
        tenant_id=tenant_id,
        subject_ref="demo_subject_redacted",
        action="demo_runtime_seed_created",
        payload={
            "scope": "metadata_only",
            "mandate_data_loaded": False,
            "productive_xnp_action": False,
        },
    )

    return {
        "schema_version": "nac.demo-runtime-seed/v0.1",
        "tenant_id": tenant_id,
        "matter_id": matter_id,
        "process_instance_id": process_instance_id,
        "usecase_slug": usecase_slug,
        "data_model_slice": _optional_text(fixture.get("data_model_slice")) or "runtime_graph_metadata_v0",
        "runtime_event_profile": "structured" if fixture.get("runtime_event_profile") else "legacy_lists",
        "mandate_data_loaded": False,
        "productive_xnp_action": False,
        "oci_apply_enabled": False,
    }


def _append_gate_events(
    *,
    store: RuntimeStoreAdapter,
    tenant_id: str,
    process_instance_id: str,
    fixture: Mapping[str, Any],
) -> None:
    profile = fixture.get("runtime_event_profile")
    if isinstance(profile, list) and profile:
        _append_profile_events(
            store=store,
            tenant_id=tenant_id,
            process_instance_id=process_instance_id,
            profile=profile,
        )
        return

    duration_bands = fixture.get("duration_bands") if isinstance(fixture.get("duration_bands"), Mapping) else {}
    gates = _text_list(fixture.get("gates"))
    external_boundaries = _text_list(fixture.get("external_boundaries"))
    critical_path = _text_list(fixture.get("critical_path"))
    parallel_groups = _text_list(fixture.get("parallel_groups"))

    for index, gate in enumerate(gates, start=1):
        store.append_process_event(
            event_id=f"DEMO-PROCESS-EVENT-GATE-{index:02d}",
            tenant_id=tenant_id,
            process_instance_id=process_instance_id,
            event_type="demo_gate_ready",
            payload={
                "gate": gate,
                "step": gate,
                "duration_band": _duration_for_gate(gate, duration_bands),
                "parallel_group": parallel_groups[0] if gate.startswith("xnp_") and parallel_groups else "",
            },
        )

    for index, boundary in enumerate(external_boundaries, start=1):
        store.append_process_event(
            event_id=f"DEMO-PROCESS-EVENT-BOUNDARY-{index:02d}",
            tenant_id=tenant_id,
            process_instance_id=process_instance_id,
            event_type="demo_external_boundary_visible",
            payload={
                "gate": boundary,
                "step": boundary,
                "external_system": _external_system(boundary),
                "duration_band": str(duration_bands.get("external_responses", "weeks")),
                "parallel_group": parallel_groups[-1] if parallel_groups else "",
                "depends_on": ["xnp_snp_target_metadata_only"],
            },
        )

    for index, gate in enumerate(critical_path, start=1):
        depends_on = [critical_path[index - 2]] if index > 1 else ["xnp_snp_target_metadata_only"]
        store.append_process_event(
            event_id=f"DEMO-PROCESS-EVENT-CRITICAL-{index:02d}",
            tenant_id=tenant_id,
            process_instance_id=process_instance_id,
            event_type="demo_critical_path_step",
            payload={
                "gate": gate,
                "step": gate,
                "duration_band": _duration_for_critical_path(index, duration_bands),
                "critical_path": True,
                "depends_on": depends_on,
            },
        )


def _append_profile_events(
    *,
    store: RuntimeStoreAdapter,
    tenant_id: str,
    process_instance_id: str,
    profile: list[Any],
) -> None:
    for index, event in enumerate(profile, start=1):
        if not isinstance(event, Mapping):
            raise ValueError("runtime_event_profile_entry_invalid")
        gate = _required_text(event.get("gate"), "runtime_event_profile_gate_missing")
        payload: dict[str, Any] = {
            "gate": gate,
            "step": _optional_text(event.get("step")) or gate,
        }
        for key in ("duration_band", "parallel_group", "external_system"):
            value = _optional_text(event.get(key))
            if value:
                payload[key] = value
        depends_on = _text_list(event.get("depends_on"))
        if depends_on:
            payload["depends_on"] = depends_on
        if event.get("critical_path") is True:
            payload["critical_path"] = True

        store.append_process_event(
            event_id=f"DEMO-PROCESS-EVENT-PROFILE-{index:02d}",
            tenant_id=tenant_id,
            process_instance_id=process_instance_id,
            event_type=_optional_text(event.get("event_type")) or "runtime_metadata_event",
            payload=payload,
        )


def _validate_demo_fixture(fixture: Mapping[str, Any]) -> None:
    if fixture.get("scope") != "metadata_only":
        raise ValueError("demo_fixture_not_metadata_only")
    if fixture.get("productive_xnp_action") is not False:
        raise ValueError("productive_xnp_action_not_allowed")
    if fixture.get("data_model_slice") not in (None, "runtime_graph_metadata_v0"):
        raise ValueError("demo_fixture_data_model_slice_unsupported")
    _validate_runtime_event_profile(fixture.get("runtime_event_profile"))
    for key in (
        "mandate_data_present",
        "real_register_data_present",
        "oci_apply_permitted",
        "secret_material_present",
        "raw_mandate_content_loaded",
        "contains_credentials",
    ):
        if fixture.get(key) is not False:
            raise ValueError(f"demo_fixture_guardrail_failed:{key}")


def _validate_runtime_event_profile(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, list) or not value:
        raise ValueError("runtime_event_profile_invalid")
    for event in value:
        if not isinstance(event, Mapping):
            raise ValueError("runtime_event_profile_entry_invalid")
        _required_text(event.get("gate"), "runtime_event_profile_gate_missing")
        if "depends_on" in event and not isinstance(event.get("depends_on"), list):
            raise ValueError("runtime_event_profile_depends_on_invalid")
        if "critical_path" in event and not isinstance(event.get("critical_path"), bool):
            raise ValueError("runtime_event_profile_critical_path_invalid")


def _duration_for_gate(gate: str, duration_bands: Mapping[str, Any]) -> str:
    if gate in {"tenant_admin_review_required", "gnotkg_review_required", "human_review_required"}:
        return str(duration_bands.get("internal_review", "hours_to_days"))
    if gate.startswith("xnp_"):
        return str(duration_bands.get("external_responses", "weeks"))
    return "hours_to_days"


def _duration_for_critical_path(index: int, duration_bands: Mapping[str, Any]) -> str:
    if index <= 2:
        return str(duration_bands.get("external_responses", "weeks"))
    return str(duration_bands.get("complex_completion", "weeks_to_months"))


def _external_system(boundary: str) -> str:
    if boundary.startswith("grundbuch"):
        return "grundbuch_external_boundary"
    if boundary.startswith("register"):
        return "register_external_boundary"
    if boundary.startswith("tax"):
        return "tax_office_external_boundary"
    if boundary.startswith("municipality"):
        return "municipality_external_boundary"
    return boundary


def _required_text(value: Any, message: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(message)
    return value


def _optional_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]
