from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_runtime.graph_projection import project_process_graph  # noqa: E402
from nac_runtime.store import InMemoryRuntimeStore  # noqa: E402


STORAGE_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "atp-runtime-storage.contract.json"
ADAPTER_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "atp-runtime-store-adapter.contract.json"
GRAPH_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "atp-runtime-graph-projection.contract.json"
RUNTIME_SCHEMA = REPO_ROOT / "deploy" / "database" / "atp-runtime-anchor-schema.sql"
SESSION_SCHEMA = REPO_ROOT / "deploy" / "database" / "atp-onboarding-request-store.sql"
SESSION_STORE = REPO_ROOT / "src" / "nac_identity" / "session_store.py"
PROHIBITED_MARKERS = {
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
    "oci_session_token",
    "password=",
}


def main() -> int:
    errors = validate()
    if errors:
        print("ATP runtime contract validation failed:")
        for error in errors:
            print(f"- {error}")
        print("STATUS: FAILED")
        return 1
    print("ATP runtime contract validation passed.")
    print("STATUS: PASSED")
    return 0


def validate(repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    storage = _read_json(repo_root / STORAGE_CONTRACT.relative_to(REPO_ROOT), errors, repo_root)
    adapter = _read_json(repo_root / ADAPTER_CONTRACT.relative_to(REPO_ROOT), errors, repo_root)
    graph = _read_json(repo_root / GRAPH_CONTRACT.relative_to(REPO_ROOT), errors, repo_root)
    if not storage or not adapter or not graph:
        return errors

    errors.extend(_validate_storage_adapter_parity(storage, adapter))
    errors.extend(_validate_schema_parity(storage, repo_root))
    errors.extend(_validate_graph_vocabulary(storage, graph))
    errors.extend(_validate_runtime_projection_matches_contract(graph))
    errors.extend(_validate_documentation_boundary(repo_root))
    return errors


def _read_json(path: Path, errors: list[str], repo_root: Path) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing JSON artifact: {path.relative_to(repo_root)}")
        return {}
    text = path.read_text(encoding="utf-8")
    _reject_prohibited_text(path, text, errors, repo_root)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON {path.relative_to(repo_root)}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(repo_root)} must be a JSON object")
        return {}
    return payload


def _validate_storage_adapter_parity(storage: dict[str, Any], adapter: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    implementation_scope = storage.get("implementation_scope_v0")
    if not isinstance(implementation_scope, dict):
        return ["atp-runtime-storage.contract.json missing implementation_scope_v0"]

    adapter_entities = adapter.get("runtime_entities")
    storage_adapter_entities = implementation_scope.get("runtime_graph_adapter_entities")
    if storage_adapter_entities != adapter_entities:
        errors.append("storage implementation_scope_v0.runtime_graph_adapter_entities must match adapter runtime_entities")

    adapter_scope = adapter.get("adapter_scope_v0")
    if not isinstance(adapter_scope, dict):
        errors.append("atp-runtime-store-adapter.contract.json missing adapter_scope_v0")
    elif adapter_scope.get("implemented_entities") != adapter_entities:
        errors.append("adapter_scope_v0.implemented_entities must match runtime_entities")

    deferred = _scope_by_id(implementation_scope.get("externalized_or_deferred_entities"))
    if "sessions" not in deferred:
        errors.append("sessions must be explicitly externalized/deferred from the runtime graph adapter")
    else:
        session = deferred["sessions"]
        if session.get("runtime_boundary") != "nac_identity.session_store.AtpSessionStore":
            errors.append("sessions deferred boundary must point to nac_identity.session_store.AtpSessionStore")
        if session.get("schema_artifact") != "deploy/database/atp-onboarding-request-store.sql":
            errors.append("sessions deferred schema artifact must point to atp-onboarding-request-store.sql")

    if "process_templates" not in deferred:
        errors.append("process_templates must be explicitly schema-anchor/template-ref scoped")
    elif deferred["process_templates"].get("runtime_boundary") != "process_instances.payload.template_ref":
        errors.append("process_templates runtime boundary must be process_instances.payload.template_ref")

    if isinstance(adapter_entities, list):
        for forbidden in ("sessions", "process_templates"):
            if forbidden in adapter_entities:
                errors.append(f"{forbidden} must not be a RuntimeStoreAdapter implemented entity in v0.1")
    return errors


def _validate_schema_parity(storage: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []
    schema_text = _read_text(repo_root / RUNTIME_SCHEMA.relative_to(REPO_ROOT), errors, repo_root)
    session_schema = _read_text(repo_root / SESSION_SCHEMA.relative_to(REPO_ROOT), errors, repo_root)
    session_store = _read_text(repo_root / SESSION_STORE.relative_to(REPO_ROOT), errors, repo_root)
    normalized = " ".join(schema_text.lower().split())

    for table in storage.get("anchor_schema", {}).get("tables", []):
        if not isinstance(table, dict):
            errors.append("anchor_schema.tables entries must be objects")
            continue
        name = table.get("name")
        if not isinstance(name, str):
            errors.append("anchor_schema table entry missing name")
            continue
        if f"create table {name.lower()}" not in normalized:
            errors.append(f"runtime anchor schema missing table {name}")

    if "create table nac_sessions" not in session_schema.lower():
        errors.append("session schema artifact must define nac_sessions")
    if "class AtpSessionStore" not in session_store:
        errors.append("nac_identity.session_store must expose AtpSessionStore")
    if "nac_sessions" in normalized:
        errors.append("runtime graph anchor schema must not duplicate nac_sessions")
    return errors


def _validate_graph_vocabulary(storage: dict[str, Any], graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    storage_vocab = storage.get("graph_projection", {}).get("runtime_projection_vocabulary")
    graph_vocab = graph.get("runtime_vocabulary")
    if not isinstance(storage_vocab, dict):
        errors.append("storage graph_projection missing runtime_projection_vocabulary")
    if not isinstance(graph_vocab, dict):
        errors.append("graph contract missing runtime_vocabulary")
    if not isinstance(storage_vocab, dict) or not isinstance(graph_vocab, dict):
        return errors

    for key in ("node_types", "edge_types", "canonical_mapping"):
        if storage_vocab.get(key) != graph_vocab.get(key):
            errors.append(f"graph runtime vocabulary mismatch for {key}")
    if graph.get("oracle_graph_studio_boundary", {}).get("runtime_ui_dependency") is not False:
        errors.append("Graph Studio must not be a runtime UI dependency")
    return errors


def _validate_runtime_projection_matches_contract(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    vocab = graph.get("runtime_vocabulary") if isinstance(graph.get("runtime_vocabulary"), dict) else {}
    allowed_node_types = set(_strings(vocab.get("node_types")))
    allowed_edge_types = set(_strings(vocab.get("edge_types")))
    projection = _sample_projection()
    emitted_node_types = {str(node.get("type")) for node in projection.get("nodes", [])}
    emitted_edge_types = {str(edge.get("type")) for edge in projection.get("edges", [])}
    if not emitted_node_types <= allowed_node_types:
        errors.append(f"runtime projection emits undocumented node types: {sorted(emitted_node_types - allowed_node_types)}")
    if not emitted_edge_types <= allowed_edge_types:
        errors.append(f"runtime projection emits undocumented edge types: {sorted(emitted_edge_types - allowed_edge_types)}")
    if projection.get("live_oci_enabled") is not False or projection.get("schema_apply_enabled") is not False:
        errors.append("runtime projection must remain owner-free and no-apply")
    if projection.get("mandate_data_loaded") is not False:
        errors.append("runtime projection must not load mandate data")
    return errors


def _sample_projection() -> dict[str, Any]:
    store = InMemoryRuntimeStore()
    store.put_tenant(tenant_id="tenant.validator", payload={"schema_version": "nac.runtime.tenant/v0.1"})
    store.put_matter(
        matter_id="matter.validator",
        tenant_id="tenant.validator",
        payload={"schema_version": "nac.runtime.matter/v0.1", "matter_type": "immobilienkaufvertrag"},
    )
    store.put_process_instance(
        process_instance_id="process.validator",
        tenant_id="tenant.validator",
        matter_id="matter.validator",
        payload={"schema_version": "nac.runtime.process-instance/v0.1", "template_ref": "bpmn:validator"},
    )
    store.append_process_event(
        event_id="event.validator.1",
        tenant_id="tenant.validator",
        process_instance_id="process.validator",
        event_type="gate_ready",
        payload={
            "schema_version": "nac.runtime.process-event/v0.1",
            "gate": "xnp_readiness",
            "external_system": "XNP/SNP",
            "duration_band": "hours_to_days",
        },
    )
    store.append_process_event(
        event_id="event.validator.2",
        tenant_id="tenant.validator",
        process_instance_id="process.validator",
        event_type="external_wait",
        payload={
            "schema_version": "nac.runtime.process-event/v0.1",
            "gate": "grundbuch_ruecklauf",
            "depends_on": ["xnp_readiness"],
            "duration_band": "weeks_to_months",
            "critical_path": True,
        },
    )
    return project_process_graph(
        process_instance_id="process.validator",
        events=store.list_process_events("process.validator"),
    )


def _validate_documentation_boundary(repo_root: Path) -> list[str]:
    errors: list[str] = []
    german = _read_text(repo_root / "docs" / "de" / "notarsoftware-datenmodell.md", errors, repo_root)
    english = _read_text(repo_root / "docs" / "en" / "notarsoftware-datenmodell.md", errors, repo_root)
    required = {
        "docs/de/notarsoftware-datenmodell.md": "SaaS-Laufzeitmetadaten gehören nach der ATP-Zielarchitektur in ATP",
        "docs/en/notarsoftware-datenmodell.md": "SaaS runtime metadata belongs in ATP according to the ATP target",
    }
    for rel, term in required.items():
        text = german if rel.startswith("docs/de/") else english
        if term not in text:
            errors.append(f"{rel} missing ATP runtime metadata boundary")
    old_phrases = (
        "Produktive Daten brauchen\neinen geprüften Sovereign-/DSGVO-Git-Anbieter",
        "Production data needs\na reviewed sovereign/GDPR Git provider",
    )
    combined = german + "\n" + english
    for phrase in old_phrases:
        if phrase in combined:
            errors.append("notarsoftware data model still frames Git provider as productive runtime target")
    return errors


def _read_text(path: Path, errors: list[str], repo_root: Path) -> str:
    if not path.is_file():
        errors.append(f"missing text artifact: {path.relative_to(repo_root)}")
        return ""
    text = path.read_text(encoding="utf-8")
    _reject_prohibited_text(path, text, errors, repo_root)
    return text


def _reject_prohibited_text(path: Path, text: str, errors: list[str], repo_root: Path) -> None:
    lowered = text.lower()
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"{path.relative_to(repo_root)} contains prohibited marker: {marker}")


def _scope_by_id(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        return {}
    return {str(item.get("id")): item for item in value if isinstance(item, dict) and item.get("id")}


def _strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
