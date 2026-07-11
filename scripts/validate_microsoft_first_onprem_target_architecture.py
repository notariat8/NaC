from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "workflows/contracts/microsoft-first-onprem-target-architecture.contract.json"
DOC_DE = REPO_ROOT / "docs/de/architecture/microsoft-first-onprem-target-architecture.md"
DOC_EN = REPO_ROOT / "docs/en/architecture/microsoft-first-onprem-target-architecture.md"
SPEC_DE = REPO_ROOT / "docs/de/superpowers/specs/2026-07-11-microsoft-first-onprem-target-architecture-design.md"
SPEC_EN = REPO_ROOT / "docs/en/superpowers/specs/2026-07-11-microsoft-first-onprem-target-architecture-design.md"
PLAN_DE = REPO_ROOT / "docs/de/superpowers/plans/2026-07-11-microsoft-first-onprem-target-architecture.md"
PLAN_EN = REPO_ROOT / "docs/en/superpowers/plans/2026-07-11-microsoft-first-onprem-target-architecture.md"


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: Microsoft-first edge, on-prem AI core, layer boundaries, storage roles and roadmap are aligned.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    contract = _read_json(CONTRACT, errors)
    documents = _read_documents(errors)
    if not contract or not documents:
        return errors

    _require_equal(contract, "schema_version", "nac.microsoft-first-onprem-target-architecture/v0.2", errors)
    _require_equal(contract, "leading_issue", "https://github.com/notariat8/NaC/issues/613", errors)

    decisions = _mapping(contract.get("decisions"), "decisions", errors)
    pdf_assessment = _mapping(contract.get("pdf_assessment"), "pdf_assessment", errors)
    guardrails = _mapping(contract.get("guardrails"), "guardrails", errors)
    boundaries = _mapping(contract.get("layer_boundaries"), "layer_boundaries", errors)
    storage = _mapping(contract.get("storage_roles"), "storage_roles", errors)
    spike = _mapping(contract.get("durable_workflow_spike"), "durable_workflow_spike", errors)
    roadmap = _mapping(contract.get("roadmap"), "roadmap", errors)
    repository_ownership = _mapping(contract.get("repository_ownership"), "repository_ownership", errors)

    if decisions:
        expected_microsoft_first_edge = [
            "microsoft_teams",
            "sharepoint_online",
            "spfx",
            "entra_id",
            "microsoft_graph_rest_v1",
        ]
        expected_onprem_core = [
            "python_fastapi_bff",
            "deterministic_workflow_control_plane",
            "nvidia_nemo_agent_toolkit",
            "postgresql",
            "outbox_broker",
            "worm_audit",
        ]
        _expect(
            decisions.get("microsoft_first_edge") == expected_microsoft_first_edge,
            "decisions.microsoft_first_edge must match the Microsoft-first edge exactly",
            errors,
        )
        _expect(
            decisions.get("onprem_core") == expected_onprem_core,
            "decisions.onprem_core must match the on-prem core exactly",
            errors,
        )
        _expect(decisions.get("only_agentic_toolkit") == "nvidia_nemo_agent_toolkit", "NeMo Agent Toolkit must be the only agentic toolkit", errors)
        _expect(decisions.get("m365_agents_sdk_role") == "optional_channel_adapter_only", "M365 Agents SDK must remain channel-adapter-only", errors)
        _expect(decisions.get("temporal_status") == "timeboxed_candidate_spike_not_selected", "Temporal must remain an unselected spike candidate", errors)

    expected_pdf_assessment = {
        "teams_as_user_entry": "adopt",
        "spfx_react_typescript": "adopt",
        "spfx_1_22_heft_toolchain": "adopt",
        "app_catalog_sppkg_teams_publishing_admin_approval": "adapt",
        "python_outside_sharepoint": "adopt",
        "sharepoint_as_hosting_platform": "adapt",
        "graph_or_sharepoint_rest": "adapt",
        "entra_sso_aadhttpclient": "adopt",
        "sharepoint_lists_for_process_state": "adapt",
        "bpmn_js": "adapt",
        "bpmn_instance_model_version_pinning": "adopt",
        "bpmn_js_lazy_loading_code_splitting": "adopt",
        "teams_custom_app_policies_early_admin_gate": "adapt",
        "spiffworkflow_as_default": "reject",
        "postgresql": "adapt",
        "microsoft_365_agents_sdk": "adapt",
        "azure_app_service_container_apps": "reject_as_prerequisite",
        "wsl_containers": "adapt",
    }
    _expect(pdf_assessment == expected_pdf_assessment, "pdf_assessment must classify every relevant recommendation exactly", errors)

    required_true = {
        "graph_rest_or_graph_backed_mcp_only",
        "ai_and_models_onprem",
    }
    required_false = {
        "sharepoint_rest_allowed",
        "pnp_allowed",
        "graph_sdk_allowed",
        "graph_beta_allowed",
        "azure_ai_runtime_required",
        "cloud_runtime_required",
        "sharepoint_is_workflow_engine",
        "sharepoint_is_technical_workflow_truth",
        "local_sidecar_is_authoritative",
        "temporal_is_final_decision",
        "live_actions_in_this_contract",
    }
    if guardrails:
        for key in sorted(required_true):
            _expect(guardrails.get(key) is True, f"guardrails.{key} must be true", errors)
        for key in sorted(required_false):
            _expect(guardrails.get(key) is False, f"guardrails.{key} must be false", errors)
        _expect(guardrails.get("graph_base_url") == "https://graph.microsoft.com/v1.0", "Graph base URL must be v1.0", errors)

    for layer in ("ui", "bff_and_access", "workflow", "personal_agent", "m365_adapter", "persistence", "audit"):
        _expect(layer in boundaries, f"layer boundary missing: {layer}", errors)
    persistence = _mapping(boundaries.get("persistence"), "layer_boundaries.persistence", errors)
    audit = _mapping(boundaries.get("audit"), "layer_boundaries.audit", errors)
    expected_persistence = {
        "common_postgresql": ["domain_read_models", "outbox", "human_task_metadata", "projections", "sync_state"],
        "temporal_mode": {
            "authoritative_execution_store": "temporal_service_and_event_history",
            "owns": ["workflow_execution_state", "timers", "retries"],
        },
        "baseline_mode": {
            "authoritative_execution_store": "postgresql",
            "owns": ["workflow_execution_state", "timers", "leases", "retries"],
        },
        "sharepoint": ["documents", "visible_metadata", "task_projections", "matter_projections"],
        "worm_separate_in_all_modes": True,
    }
    _expect(persistence == expected_persistence, "layer_boundaries.persistence must match the conditional workflow modes exactly", errors)
    expected_audit = {
        "required": ["append_only_events", "hash_binding", "worm_retention", "reconciliation"],
        "sharepoint_version_history_is_sufficient": False,
    }
    _expect(
        audit == expected_audit,
        "layer_boundaries.audit must match the required evidence and SharePoint exclusion exactly",
        errors,
    )

    expected_storage = {
        "sharepoint": "documents_and_user_facing_projections",
        "postgresql_common": "domain_read_models_outbox_task_metadata_projections_and_sync_state",
        "temporal_mode": {
            "authoritative_execution_store": "temporal_service_and_event_history",
            "temporal_owns": ["workflow_execution_state", "timers", "retries"],
            "postgresql_owns": ["domain_read_models", "outbox", "human_task_metadata", "projections", "sync_state"],
        },
        "baseline_mode": {
            "authoritative_execution_store": "postgresql",
            "postgresql_owns": ["workflow_execution_state", "timers", "leases", "retries", "domain_read_models", "outbox", "human_task_metadata", "projections", "sync_state"],
        },
        "workflow_history": "selected_engine_execution_history_not_sole_legal_evidence",
        "worm": "immutable_approval_access_delegation_and_mutation_evidence",
        "local_cache": "encrypted_short_lived_non_authoritative",
        "agent_memory": "personal_preferences_without_matter_truth",
    }
    _expect(storage == expected_storage, "storage_roles must match the conditional source-of-truth contract exactly", errors)

    expected_roadmap = {
        "days_0_90": ["s3_runtime", "s4_graph_read_adapter", "entra_fastapi_bff_spec", "spfx_read_only_workspace", "spfx_delivery_governance", "bpmn_instance_version_pinning", "durable_workflow_spike", "synthetic_end_to_end_matter"],
        "days_91_180": ["selected_workflow_control_plane", "mode_specific_persistence", "human_tasks_and_deadlines", "nemo_bounded_activities", "outbox_inbox_reconciliation", "worm_evidence", "local_sidecar_pilot"],
        "days_181_365": ["four_first_wave_cases", "ha_backup_restore", "capacity_and_monitoring", "two_plus_two_office_pilot", "optional_m365_agents_channel_adapter"],
    }
    _expect(roadmap == expected_roadmap, "roadmap must match the accepted 90/180/365 values exactly", errors)

    expected_repository_ownership = {
        "spfx": "spfx/",
        "m365_graph_adapter": "src/nac_m365_graph/",
        "ontology_and_type_runtime": "src/notary_kg/",
        "workflow_control_plane": "src/nac_runtime/",
        "workflow_contracts": "workflows/",
        "onprem_deployment": "deploy/runtime/onprem/",
        "workstation_connectors": "plugins/",
    }
    _expect(
        repository_ownership == expected_repository_ownership,
        "repository_ownership must match the accepted component-to-path mapping exactly",
        errors,
    )

    if spike:
        _expect(spike.get("timebox_weeks_max") == 6, "durable workflow spike must be capped at six weeks", errors)
        _expect(spike.get("requires_separate_adr") is True, "durable workflow selection requires a separate ADR", errors)
        _expect(spike.get("is_agentic_toolkit_selection") is False, "workflow engine spike must not select an agentic toolkit", errors)
        candidates = set(spike.get("candidates", []))
        _expect(candidates == {"temporal_self_hosted_python", "python_postgresql_baseline"}, "spike candidates must remain explicit and outcome-open", errors)

    for path, text in documents.items():
        _validate_document_markers(path, text, errors)

    forbidden_contract_values = {"sharepoint_rest", "pnp", "microsoft_graph_sdk", "graph_beta"}
    adapter = _mapping(boundaries.get("m365_adapter"), "layer_boundaries.m365_adapter", errors)
    if adapter:
        _expect(forbidden_contract_values.issubset(set(adapter.get("forbidden", []))), "M365 adapter forbidden API families are incomplete", errors)

    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read {path.relative_to(REPO_ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} must contain a JSON object")
        return {}
    return value


def _read_documents(errors: list[str]) -> dict[str, str]:
    documents: dict[str, str] = {}
    for path in (DOC_DE, DOC_EN, SPEC_DE, SPEC_EN, PLAN_DE, PLAN_EN):
        try:
            relative = str(path.relative_to(REPO_ROOT))
            text = path.read_text(encoding="utf-8")
            if not text.strip():
                errors.append(f"{relative} must not be empty")
            documents[relative] = text
        except OSError as exc:
            errors.append(f"cannot read {path.relative_to(REPO_ROOT)}: {exc}")
    return documents


def _validate_document_markers(path: str, text: str, errors: list[str]) -> None:
    markers = ["PostgreSQL", "WORM", "Temporal", "SPFx", "FastAPI"]
    is_german = "/de/" in path
    if "/architecture/" in path:
        markers.append("#613")
        markers.extend(
            [
                "NVIDIA NeMo Agent Toolkit",
                "SPFx 1.22+",
                ".sppkg",
                "Lazy Loading" if is_german else "Lazy loading",
                "BPMN-Modellversion" if is_german else "BPMN model version",
                "Teams-Custom-App-Richtlinien" if is_german else "Teams custom-app policies",
                "Temporal-Modus" if is_german else "Temporal mode",
                "Baseline-Modus" if is_german else "Baseline mode",
                "0–90" if is_german else "0–90",
                "91–180" if is_german else "91–180",
                "181–365" if is_german else "181–365",
            ]
        )
        matrix_rows_de = [
            "| Teams als Benutzereinstieg | Übernehmen |",
            "| SPFx + React/TypeScript | Übernehmen |",
            "| SPFx 1.22+ mit Heft-Toolchain | Übernehmen |",
            "| App Catalog, .sppkg, Teams-Publishing und Admin-Freigabe | Anpassen |",
            "| Python außerhalb SharePoint | Übernehmen |",
            "| SharePoint als Hosting-Plattform | Anpassen |",
            "| Graph oder SharePoint REST | Anpassen |",
            "| Entra SSO/AadHttpClient | Übernehmen |",
            "| SharePoint-Listen für Prozesszustand | Anpassen |",
            "| BPMN.js | Anpassen |",
            "| BPMN-Modellversion pro laufender Instanz | Übernehmen |",
            "| Lazy Loading und Code Splitting für bpmn-js | Übernehmen |",
            "| Teams-Custom-App-Richtlinien und frühes Admin-Gate | Anpassen |",
            "| SpiffWorkflow als Default | Verwerfen |",
            "| PostgreSQL | Anpassen |",
            "| Microsoft 365 Agents SDK | Anpassen |",
            "| Azure App Service/Container Apps | Verwerfen als Voraussetzung |",
            "| WSL-Container | Anpassen |",
        ]
        matrix_rows_en = [
            "| Teams as user entry | Adopt |",
            "| SPFx + React/TypeScript | Adopt |",
            "| SPFx 1.22+ with the Heft toolchain | Adopt |",
            "| App Catalog, .sppkg, Teams publishing and admin approval | Adapt |",
            "| Python outside SharePoint | Adopt |",
            "| SharePoint as hosting platform | Adapt |",
            "| Graph or SharePoint REST | Adapt |",
            "| Entra SSO/AadHttpClient | Adopt |",
            "| SharePoint lists for process state | Adapt |",
            "| BPMN.js | Adapt |",
            "| BPMN model version per running instance | Adopt |",
            "| Lazy loading and code splitting for bpmn-js | Adopt |",
            "| Teams custom-app policies and early admin gate | Adapt |",
            "| SpiffWorkflow as default | Reject |",
            "| PostgreSQL | Adapt |",
            "| Microsoft 365 Agents SDK | Adapt |",
            "| Azure App Service/Container Apps | Reject as prerequisite |",
            "| WSL containers | Adapt |",
        ]
        markers.extend(matrix_rows_de if is_german else matrix_rows_en)
    elif "/specs/" in path:
        markers.append("issues/613")
        markers.extend([f"AC-613-0{number}" for number in range(1, 7)])
        markers.append("Ausführungswahrheit" if is_german else "execution truth")
    elif "/plans/" in path:
        markers.append("#613")
        markers.extend([f"Slice {number}" for number in range(1, 8)])
        markers.extend(
            [
                "SPFx 1.22+",
                ".sppkg",
                "Temporal-Modus" if is_german else "Temporal mode",
                "Baseline-Modus" if is_german else "baseline mode",
            ]
        )
    for marker in markers:
        _expect(marker in text, f"{path} marker missing: {marker}", errors)


def _mapping(value: Any, name: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return {}
    return value


def _require_equal(document: dict[str, Any], key: str, expected: Any, errors: list[str]) -> None:
    _expect(document.get(key) == expected, f"{key} must equal {expected!r}", errors)


def _expect(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


if __name__ == "__main__":
    raise SystemExit(main())
