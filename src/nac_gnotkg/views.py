from __future__ import annotations

from pathlib import Path
from typing import Any

from notary_kg.catalog import load_catalogs


COST_INFORMATION_ID = "cost.business_value"
COST_DECISION_ID = "decision.gnotkg_cost_path"
COST_GATE_ID = "gate.gnotkg_cost_review"
COST_EVIDENCE_ID = "evidence.gnotkg_cost_note"


def build_cost_review_view(repo_root: Path, slug: str) -> dict[str, Any]:
    catalog, case = _find_case(repo_root, slug)
    nodes = [
        _node(
            node_id=str(case.get("id", f"case.{slug}")),
            node_type="case",
            label=str(case.get("title", slug)),
            status=str(case.get("status", "open")),
            owner_role="notary",
            source_ref=f"{case.get('usecase_path', f'usecases/{slug}')}/knowledge-graph.graph.json",
            data_class="mandate_metadata",
            editable=False,
            requires_review=True,
        ),
        _node_from_item(case, "required_information", COST_INFORMATION_ID, "information"),
        _node(
            node_id="cost.value_rule",
            node_type="rule",
            label="Wertvorschrift prüfen",
            status="open",
            owner_role="notary",
            source_ref="GNotKG § 3, §§ 36 ff.",
            data_class="legal_reference",
            editable=False,
            requires_review=True,
        ),
        _node(
            node_id="cost.kv_position",
            node_type="kv_item",
            label="KV-Position aus Anlage 1 bestimmen",
            status="open",
            owner_role="notary",
            source_ref="GNotKG Anlage 1",
            data_class="legal_reference",
            editable=False,
            requires_review=True,
        ),
        _node_from_item(case, "decisions", COST_DECISION_ID, "decision"),
        _node(
            node_id="cost.table_a",
            node_type="fee_table",
            label="Tabelle A",
            status="open",
            owner_role="notary",
            source_ref="GNotKG § 34 und Anlage 2",
            data_class="legal_reference",
            editable=False,
            requires_review=True,
        ),
        _node(
            node_id="cost.table_b",
            node_type="fee_table",
            label="Tabelle B",
            status="open",
            owner_role="notary",
            source_ref="GNotKG § 34 und Anlage 2",
            data_class="legal_reference",
            editable=False,
            requires_review=True,
        ),
        _node_from_item(case, "gates", COST_GATE_ID, "gate"),
        _node_from_item(case, "evidence", COST_EVIDENCE_ID, "evidence"),
    ]
    case_id = str(case.get("id", f"case.{slug}"))
    edges = [
        _edge(case_id, COST_INFORMATION_ID, "requires"),
        _edge(COST_INFORMATION_ID, "cost.value_rule", "informs"),
        _edge("cost.value_rule", "cost.kv_position", "requires"),
        _edge("cost.kv_position", COST_DECISION_ID, "informs"),
        _edge(COST_DECISION_ID, "cost.table_a", "selects"),
        _edge(COST_DECISION_ID, "cost.table_b", "selects"),
        _edge("cost.table_a", COST_GATE_ID, "requires_review"),
        _edge("cost.table_b", COST_GATE_ID, "requires_review"),
        _edge(COST_GATE_ID, COST_EVIDENCE_ID, "evidences"),
    ]

    return {
        "schema_version": "nac.gnotkg-cost-review/v0.1",
        "graph_id": catalog.graph_id,
        "usecase_slug": slug,
        "case_id": case_id,
        "title": f"GNotKG-Kostenprüfung: {case.get('title', slug)}",
        "source_refs": [
            "https://www.gesetze-im-internet.de/gnotkg/__3.html",
            "https://www.gesetze-im-internet.de/gnotkg/__34.html",
            "https://www.gesetze-im-internet.de/gnotkg/__35.html",
            "https://www.gesetze-im-internet.de/gnotkg/anlage_1.html",
            "https://www.gesetze-im-internet.de/gnotkg/anlage_2.html",
        ],
        "rendering": {
            "preferred_renderer": "xyflow",
            "renderer_role": "visual_review_only",
            "contract": "workflows/contracts/gnotkg-cost-review.contract.json",
        },
        "nodes": nodes,
        "edges": edges,
        "actions": [
            {"name": "calculate_draft_quote", "mode": "local_input_only"},
            {"name": "propose_kg_patch", "mode": "pull_request_required"},
            {"name": "create_pull_request", "mode": "protected_pr"},
        ],
        "guardrails": {
            "real_mandate_data_in_git": False,
            "value_fields_editable": False,
            "xyflow_calculates_fees": False,
            "notarial_review_required": True,
            "privacy_boundary": "Produktrepo enthält nur Struktur, Quellen und Reviewstatus.",
        },
    }


def _find_case(repo_root: Path, slug: str):
    for catalog in load_catalogs(repo_root):
        for case in catalog.payload.get("cases", []):
            if isinstance(case, dict) and case.get("slug") == slug:
                return catalog, case
    raise KeyError(f"Unknown KG case slug: {slug}")


def _node_from_item(case: dict[str, Any], source: str, node_id: str, node_type: str) -> dict[str, Any]:
    for item in case.get(source, []):
        if isinstance(item, dict) and item.get("id") == node_id:
            return _node(
                node_id=node_id,
                node_type=node_type,
                label=str(item.get("label", node_id)),
                status=str(item.get("status", "open")),
                owner_role=str(item.get("owner_role", "notary")),
                source_ref=f"{case.get('usecase_path', '')}/knowledge-graph.graph.json#{source}.{node_id}",
                data_class=str(item.get("privacy_class", "mandate_metadata")),
                editable=False,
                requires_review=True,
            )
    raise ValueError(f"{case.get('slug', '<unknown>')}: Pflicht-Kostenknoten fehlt: {node_id}")


def _node(
    node_id: str,
    node_type: str,
    label: str,
    status: str,
    owner_role: str,
    source_ref: str,
    data_class: str,
    editable: bool,
    requires_review: bool,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "label": label,
        "status": status,
        "data_class": data_class,
        "owner_role": owner_role,
        "source_ref": source_ref,
        "editable": editable,
        "requires_review": requires_review,
        "privacy_boundary": "no_mandate_values",
    }


def _edge(source: str, target: str, edge_type: str) -> dict[str, str]:
    return {
        "id": f"{source}->{target}",
        "source": source,
        "target": target,
        "type": edge_type,
    }
