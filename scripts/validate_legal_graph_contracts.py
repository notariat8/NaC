from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_legal_graph.catalog import assert_no_prohibited_payload  # noqa: E402
from nac_legal_graph.patches import build_update_patch  # noqa: E402


LEGAL_GRAPH_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "legal-graph.contract.json"
COMMENTARY_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "legal-commentary-connectors.contract.json"
LEGAL_GRAPH_DOMAIN_ROOT = REPO_ROOT / "workflows" / "legal-graph" / "domains"
LEGAL_GRAPH_FIXTURE_ROOT = REPO_ROOT / "workflows" / "legal-graph" / "fixtures"
PROHIBITED_MARKERS = {
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
    "password",
    "cookie",
}


def validate() -> list[str]:
    errors: list[str] = []
    legal_graph = _read_json(LEGAL_GRAPH_CONTRACT, errors)
    commentary = _read_json(COMMENTARY_CONTRACT, errors)
    if legal_graph:
        errors.extend(_validate_legal_graph_contract(legal_graph))
    if commentary:
        errors.extend(_validate_commentary_contract(commentary))
    errors.extend(validate_legal_graph_artifacts(REPO_ROOT))
    return errors


def validate_legal_graph_artifacts(repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    domain_root = repo_root / "workflows" / "legal-graph" / "domains"
    fixture_root = repo_root / "workflows" / "legal-graph" / "fixtures"

    for graph_path in sorted(domain_root.glob("*.graph.json")) if domain_root.is_dir() else []:
        payload = _read_json(graph_path, errors, repo_root=repo_root)
        if not payload:
            continue
        errors.extend(_validate_graph_payload(graph_path, payload, repo_root))

    for fixture_path in sorted(fixture_root.glob("*.json")) if fixture_root.is_dir() else []:
        payload = _read_json(fixture_path, errors, repo_root=repo_root)
        if not payload:
            continue
        errors.extend(_validate_fixture_payload(fixture_path, payload, repo_root))

    return errors


def _read_json(path: Path, errors: list[str], repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"Pflichtvertrag fehlt: {path.relative_to(repo_root)}")
        return {}

    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(repo_root)} enthaelt unzulaessigen Marker: {marker}")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(repo_root)} ist kein gueltiges JSON: {exc}")
        return {}

    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(repo_root)} muss ein JSON-Objekt sein")
        return {}
    return payload


def _validate_legal_graph_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "nac.workflow-contract/v0.1":
        errors.append("legal-graph.contract.json: schema_version muss nac.workflow-contract/v0.1 sein")
    if payload.get("contract_id") != "workflow.legal_graph":
        errors.append("legal-graph.contract.json: contract_id muss workflow.legal_graph sein")

    policy = payload.get("automation_policy")
    if not isinstance(policy, dict):
        errors.append("legal-graph.contract.json: automation_policy muss ein Objekt sein")
    else:
        if policy.get("auto_merge_allowed") is not False:
            errors.append("legal-graph.contract.json: auto_merge_allowed muss false sein")
        if policy.get("human_review_required") is not True:
            errors.append("legal-graph.contract.json: human_review_required muss true sein")
        if policy.get("real_mandate_data_allowed") is not False:
            errors.append("legal-graph.contract.json: real_mandate_data_allowed muss false sein")

    required_nodes = set(_strings(payload.get("required_node_types")))
    for node_type in sorted({"source_document", "norm", "decision", "notarial_usecase", "graph_patch"} - required_nodes):
        errors.append(f"legal-graph.contract.json: required_node_types fehlt {node_type}")
    return errors


def _validate_commentary_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "nac.workflow-contract/v0.1":
        errors.append("legal-commentary-connectors.contract.json: schema_version muss nac.workflow-contract/v0.1 sein")
    if payload.get("contract_id") != "workflow.legal_commentary_connectors":
        errors.append("legal-commentary-connectors.contract.json: contract_id muss workflow.legal_commentary_connectors sein")
    if set(_strings(payload.get("allowed_connection_modes"))) != {"mcp", "api"}:
        errors.append("legal-commentary-connectors.contract.json: allowed_connection_modes muss mcp und api enthalten")

    policy = payload.get("policy")
    if not isinstance(policy, dict):
        errors.append("legal-commentary-connectors.contract.json: policy muss ein Objekt sein")
    else:
        false_keys = {
            "credentials_allowed_in_repo",
            "commentary_full_text_allowed_in_repo",
            "production_mandate_data_allowed",
        }
        true_keys = {
            "requires_license_review",
            "requires_avv_review_for_personal_data",
            "requires_professional_secrecy_review",
            "requires_ai_sbom_decision",
            "requires_source_attribution",
            "requires_human_notarial_review",
        }
        for key in sorted(false_keys):
            if policy.get(key) is not False:
                errors.append(f"legal-commentary-connectors.contract.json: policy.{key} muss false sein")
        for key in sorted(true_keys):
            if policy.get(key) is not True:
                errors.append(f"legal-commentary-connectors.contract.json: policy.{key} muss true sein")
    return errors


def _validate_graph_payload(path: Path, payload: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []
    label = path.relative_to(repo_root).as_posix()
    try:
        assert_no_prohibited_payload(payload)
    except ValueError as exc:
        errors.append(f"{label}: {exc}")

    if payload.get("schema_version") != "nac.legal-graph/v0.1":
        errors.append(f"{label}: schema_version muss nac.legal-graph/v0.1 sein")
    domain = payload.get("domain")
    if not isinstance(domain, dict) or not isinstance(domain.get("id"), str):
        errors.append(f"{label}: domain.id muss gesetzt sein")
    elif path.name != f"{domain['id']}.graph.json":
        errors.append(f"{label}: Dateiname muss zur domain.id passen")

    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append(f"{label}: nodes muss eine nicht leere Liste sein")
        return errors
    node_ids: set[str] = set()
    node_types: set[str] = set()
    for index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            errors.append(f"{label}: nodes[{index}] muss ein Objekt sein")
            continue
        node_id = node.get("id")
        node_type = node.get("type")
        if not isinstance(node_id, str) or not node_id:
            errors.append(f"{label}: nodes[{index}].id muss gesetzt sein")
        elif node_id in node_ids:
            errors.append(f"{label}: doppelte Node-ID {node_id}")
        else:
            node_ids.add(node_id)
        if isinstance(node_type, str):
            node_types.add(node_type)

    for node_type in sorted({"source_document", "norm", "notarial_usecase", "review_point", "commentary_connector"} - node_types):
        errors.append(f"{label}: Node-Typ fehlt {node_type}")

    edges = payload.get("edges")
    if not isinstance(edges, list):
        errors.append(f"{label}: edges muss eine Liste sein")
        return errors
    for index, edge in enumerate(edges, start=1):
        if not isinstance(edge, dict):
            errors.append(f"{label}: edges[{index}] muss ein Objekt sein")
            continue
        edge_from = edge.get("from")
        edge_to = edge.get("to")
        edge_type = edge.get("type")
        if not all(isinstance(item, str) and item for item in (edge_from, edge_to, edge_type)):
            errors.append(f"{label}: edges[{index}] braucht from, to und type")
            continue
        if edge_from not in node_ids or edge_to not in node_ids:
            errors.append(f"{label}: edges[{index}] verweist auf unbekannten Knoten")
    return errors


def _validate_fixture_payload(path: Path, payload: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []
    label = path.relative_to(repo_root).as_posix()
    try:
        assert_no_prohibited_payload(payload)
    except ValueError as exc:
        errors.append(f"{label}: {exc}")

    if payload.get("schema_version") != "nac.legal-graph-source-update/v0.1":
        errors.append(f"{label}: schema_version muss nac.legal-graph-source-update/v0.1 sein")
    domain = payload.get("domain")
    if not isinstance(domain, str) or not domain:
        errors.append(f"{label}: domain muss gesetzt sein")
        return errors
    if path.name != f"{domain}-source-update.json":
        errors.append(f"{label}: Dateiname muss zur domain passen")
    try:
        build_update_patch(repo_root, domain)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: {exc}")
    return errors


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print(
        "OK: Legal-Graph- und Kommentar-Connector-Vertraege erzwingen Review, "
        "Lizenzgrenzen und No-Fulltext-/No-Credential-Regeln."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
