# Legal Graph Commentary Connectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first reviewable NaC legal graph for inheritance law and secure licensed commentary sources as a separate MCP/API connector track.

**Architecture:** The first slice delivers contracts, validators, a static inheritance-law graph, a Python runtime, a patch/review dry-run pipeline and a central `nac legal-graph` CLI. Automatic source runs only create review patches; professional truth is created only after human review and merge.

**Tech Stack:** Python standard library, `unittest`, JSON contracts, existing NaC CLI, `workflows/legal-graph/` as a mandate-data-free graph artifact area.

---

## File Structure

- Create `workflows/contracts/legal-graph.contract.json`: contract for graph schema, allowed sources, review requirement and no-auto-merge rules.
- Create `workflows/contracts/legal-commentary-connectors.contract.json`: contract for licensed commentary/publisher sources through MCP/API without full-text or credential storage.
- Create `scripts/validate_legal_graph_contracts.py`: deterministic validator for both new contracts.
- Modify `src/nac_cli/cli.py`: `nac contracts validate` calls the new validator; `nac legal-graph ...` is added as the central operating surface.
- Create `src/nac_legal_graph/__init__.py`: package marker and version export.
- Create `src/nac_legal_graph/catalog.py`: loads static legal graph domain files and builds status/review payloads.
- Create `src/nac_legal_graph/patches.py`: creates review patches from source-diff fixtures without graph merge.
- Create `workflows/legal-graph/domains/erbrecht.graph.json`: first mandate-data-free inheritance-law graph.
- Create `workflows/legal-graph/fixtures/erbrecht-source-update.json`: fixture for update dry-run and patch test.
- Create `tests/test_legal_graph_contracts.py`: contract tests and validator execution.
- Create `tests/test_legal_graph.py`: loader, graph, patch and no-mandate-data tests.
- Modify `tests/test_nac_cli.py`: CLI coverage for `nac legal-graph status`, `review` and `update-dry-run`.
- Modify `workflows/contracts/README.md`: link new contracts.
- Modify `docs/de/cli.md` and `docs/en/cli.md`: document new operating surface.
- Modify `docs/de/pruefung-standardisierung-start.md` and `docs/en/pruefung-standardisierung-start.md`: extend the review path with the legal graph and commentary connector boundary.

---

### Task 1: Build Contracts And Validator

**Files:**
- Create: `workflows/contracts/legal-graph.contract.json`
- Create: `workflows/contracts/legal-commentary-connectors.contract.json`
- Create: `scripts/validate_legal_graph_contracts.py`
- Modify: `src/nac_cli/cli.py`
- Test: `tests/test_legal_graph_contracts.py`

- [ ] **Step 1: Write the failing contract tests**

Add `tests/test_legal_graph_contracts.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGAL_GRAPH_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "legal-graph.contract.json"
COMMENTARY_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "legal-commentary-connectors.contract.json"


class LegalGraphContractTests(unittest.TestCase):
    def test_legal_graph_contract_blocks_unreviewed_merges(self) -> None:
        payload = json.loads(LEGAL_GRAPH_CONTRACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["contract_id"], "workflow.legal_graph")
        self.assertEqual(payload["status"], "planned_mvp")
        self.assertFalse(payload["automation_policy"]["auto_merge_allowed"])
        self.assertTrue(payload["automation_policy"]["human_review_required"])
        self.assertIn("erbrecht", payload["domains"][0]["id"])
        self.assertIn("source_document", payload["required_node_types"])
        self.assertIn("graph_patch", payload["required_node_types"])

    def test_commentary_contract_requires_mcp_or_api_and_blocks_full_text(self) -> None:
        payload = json.loads(COMMENTARY_CONTRACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["contract_id"], "workflow.legal_commentary_connectors")
        self.assertFalse(payload["policy"]["credentials_allowed_in_repo"])
        self.assertFalse(payload["policy"]["commentary_full_text_allowed_in_repo"])
        self.assertTrue(payload["policy"]["requires_license_review"])
        self.assertTrue(payload["policy"]["requires_human_notarial_review"])
        self.assertEqual(set(payload["allowed_connection_modes"]), {"mcp", "api"})

    def test_validator_accepts_contracts(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_legal_graph_contracts.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_legal_graph_contracts
```

Expected: `FAILED` because the two contract JSON files and `scripts/validate_legal_graph_contracts.py` do not exist.

- [ ] **Step 3: Add `legal-graph.contract.json`**

Create `workflows/contracts/legal-graph.contract.json`:

```json
{
  "schema_version": "nac.workflow-contract/v0.1",
  "contract_id": "workflow.legal_graph",
  "title": "NaC Legal Graph",
  "status": "planned_mvp",
  "last_update": "2026-06-12",
  "purpose": "Define the mandatsdatenfreie primary-source legal graph for notarial usecases and its review-only update model.",
  "domains": [
    {
      "id": "erbrecht",
      "label_de": "Erbrecht",
      "status": "mvp",
      "graph_path": "workflows/legal-graph/domains/erbrecht.graph.json"
    }
  ],
  "allowed_primary_sources": [
    "gesetze_im_internet",
    "rechtsprechung_im_internet",
    "ris_search_candidate"
  ],
  "required_node_types": [
    "legal_domain",
    "source_document",
    "norm",
    "decision",
    "notarial_usecase",
    "review_point",
    "commentary_connector",
    "graph_patch"
  ],
  "required_edge_types": [
    "cites",
    "amends",
    "valid_from",
    "valid_until",
    "affects_usecase",
    "supports_review_point",
    "needs_commentary_review",
    "approved_by"
  ],
  "automation_policy": {
    "source_update_allowed": true,
    "patch_proposal_allowed": true,
    "auto_merge_allowed": false,
    "human_review_required": true,
    "real_mandate_data_allowed": false,
    "commentary_full_text_allowed": false
  },
  "required_patch_statuses": [
    "proposed",
    "needs_human_mapping",
    "blocked_contract",
    "approved",
    "rejected"
  ]
}
```

- [ ] **Step 4: Add `legal-commentary-connectors.contract.json`**

Create `workflows/contracts/legal-commentary-connectors.contract.json`:

```json
{
  "schema_version": "nac.workflow-contract/v0.1",
  "contract_id": "workflow.legal_commentary_connectors",
  "title": "Licensed Legal Commentary Connectors",
  "status": "candidate_backlog",
  "last_update": "2026-06-12",
  "purpose": "Prepare licensed commentary and publisher sources for MCP/API access without scraping, credentials in repo, full-text storage or mandate-data processing.",
  "allowed_connection_modes": [
    "mcp",
    "api"
  ],
  "policy": {
    "credentials_allowed_in_repo": false,
    "commentary_full_text_allowed_in_repo": false,
    "production_mandate_data_allowed": false,
    "requires_license_review": true,
    "requires_avv_review_for_personal_data": true,
    "requires_professional_secrecy_review": true,
    "requires_ai_sbom_decision": true,
    "requires_source_attribution": true,
    "requires_human_notarial_review": true
  },
  "candidate_providers": [
    {
      "id": "beck-online",
      "display_name": "beck-online",
      "status": "license_review_required"
    },
    {
      "id": "juris",
      "display_name": "juris",
      "status": "license_review_required"
    },
    {
      "id": "wolters-kluwer",
      "display_name": "Wolters Kluwer Online",
      "status": "license_review_required"
    }
  ],
  "allowed_evidence_fields": [
    "provider_id",
    "source_url",
    "citation",
    "checked_at",
    "checked_by",
    "license_status",
    "data_classes",
    "review_note"
  ],
  "blocked_actions": [
    "scrape_protected_portal",
    "store_credentials",
    "store_commentary_full_text",
    "send_mandate_data_without_avv",
    "treat_commentary_as_sole_notarial_truth"
  ]
}
```

- [ ] **Step 5: Add the validator**

Create `scripts/validate_legal_graph_contracts.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGAL_GRAPH_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "legal-graph.contract.json"
COMMENTARY_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "legal-commentary-connectors.contract.json"
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
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"Pflichtvertrag fehlt: {path.relative_to(REPO_ROOT)}")
        return {}
    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(REPO_ROOT)} enthält unzulässigen Marker: {marker}")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)} ist kein gültiges JSON: {exc}")
        return {}
    return payload if isinstance(payload, dict) else {}


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
    for node_type in {"source_document", "norm", "decision", "notarial_usecase", "graph_patch"} - required_nodes:
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


def _strings(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: Legal-Graph- und Kommentar-Connector-Verträge erzwingen Review, Lizenzgrenzen und No-Fulltext-/No-Credential-Regeln.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Wire the validator into `nac contracts validate`**

In `src/nac_cli/cli.py`, extend the `validators` list inside `command_contracts`:

```python
        validators = [
            ("GNotKG Cost Review Contract", "validate_gnotkg_costs.py"),
            ("Secure Document Link Contract", "validate_secure_document_links.py"),
            ("Legal Research Connectors", "validate_legal_research_connectors.py"),
            ("Legal Graph Contracts", "validate_legal_graph_contracts.py"),
            ("OCI Tenant Identity Contract", "validate_oci_tenant_identity.py"),
            ("Spec Traceability Contract", "validate_spec_traceability.py"),
        ]
```

- [ ] **Step 7: Run tests and commit**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_legal_graph_contracts tests.test_nac_cli
```

Expected: `OK`.

Commit:

```bash
git add workflows/contracts/legal-graph.contract.json workflows/contracts/legal-commentary-connectors.contract.json scripts/validate_legal_graph_contracts.py src/nac_cli/cli.py tests/test_legal_graph_contracts.py
git commit -m "feat: add legal graph contracts"
```

---

### Task 2: Build The Inheritance-Law Graph And Loader

**Files:**
- Create: `src/nac_legal_graph/__init__.py`
- Create: `src/nac_legal_graph/catalog.py`
- Create: `workflows/legal-graph/domains/erbrecht.graph.json`
- Test: `tests/test_legal_graph.py`

- [ ] **Step 1: Write the failing loader tests**

Create `tests/test_legal_graph.py`:

```python
from __future__ import annotations

import json
import unittest
from pathlib import Path

from nac_legal_graph.catalog import build_review_payload, load_domain_graph, legal_graph_status


REPO_ROOT = Path(__file__).resolve().parents[1]


class LegalGraphTests(unittest.TestCase):
    def test_erbrecht_graph_loads_without_mandate_values(self) -> None:
        graph = load_domain_graph(REPO_ROOT, "erbrecht")

        self.assertEqual(graph["schema_version"], "nac.legal-graph/v0.1")
        self.assertEqual(graph["domain"]["id"], "erbrecht")
        self.assertGreaterEqual(len(graph["nodes"]), 10)
        self.assertGreaterEqual(len(graph["edges"]), 8)
        self.assertFalse(_contains_key(graph, "value"))
        self.assertFalse(_contains_text(graph, "Max Mustermann"))

    def test_erbrecht_status_counts_nodes_edges_and_review_items(self) -> None:
        status = legal_graph_status(REPO_ROOT)

        self.assertEqual(status["schema_version"], "nac.legal-graph-status/v0.1")
        self.assertEqual(status["domains"], 1)
        self.assertEqual(status["domain_status"][0]["id"], "erbrecht")
        self.assertGreaterEqual(status["domain_status"][0]["nodes"], 10)
        self.assertGreaterEqual(status["domain_status"][0]["review_required"], 1)

    def test_review_payload_exposes_sources_and_commentary_boundary(self) -> None:
        payload = build_review_payload(REPO_ROOT, "erbrecht")

        self.assertEqual(payload["schema_version"], "nac.legal-graph-review/v0.1")
        self.assertEqual(payload["domain"], "erbrecht")
        self.assertIn("commentary_connector", {item["type"] for item in payload["review_items"]})
        self.assertTrue(payload["guardrails"]["human_review_required"])
        self.assertFalse(payload["guardrails"]["commentary_full_text_in_repo"])

    def test_erbrecht_graph_json_is_stable(self) -> None:
        graph_path = REPO_ROOT / "workflows" / "legal-graph" / "domains" / "erbrecht.graph.json"
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
        node_ids = {node["id"] for node in payload["nodes"]}

        self.assertIn("norm.bgb.1945", node_ids)
        self.assertIn("usecase.erbausschlagung", node_ids)
        self.assertIn("connector.beck-online", node_ids)


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def _contains_text(value, text: str) -> bool:
    if isinstance(value, str):
        return text in value
    if isinstance(value, dict):
        return any(_contains_text(item, text) for item in value.values())
    if isinstance(value, list):
        return any(_contains_text(item, text) for item in value)
    return False


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the loader tests and verify failure**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_legal_graph
```

Expected: `ModuleNotFoundError: No module named 'nac_legal_graph'`.

- [ ] **Step 3: Add the inheritance-law graph fixture**

Create `workflows/legal-graph/domains/erbrecht.graph.json` with this minimal MVP graph:

```json
{
  "schema_version": "nac.legal-graph/v0.1",
  "graph_id": "legal.erbrecht",
  "last_update": "2026-06-12",
  "domain": {
    "id": "erbrecht",
    "label_de": "Erbrecht",
    "status": "mvp"
  },
  "guardrails": {
    "real_mandate_data_allowed": false,
    "commentary_full_text_in_repo": false,
    "human_review_required": true
  },
  "nodes": [
    {
      "id": "source.gesetze-im-internet.bgb",
      "type": "source_document",
      "label": "Gesetze im Internet: BGB",
      "url": "https://www.gesetze-im-internet.de/bgb/",
      "usage_status": "primary_source_candidate",
      "content_hash": "metadata-only"
    },
    {
      "id": "source.rechtsprechung-im-internet",
      "type": "source_document",
      "label": "Rechtsprechung im Internet",
      "url": "https://www.rechtsprechung-im-internet.de/jportal/portal/page/bsjrsprod.psml",
      "usage_status": "primary_source_candidate",
      "content_hash": "metadata-only"
    },
    {
      "id": "norm.bgb.1945",
      "type": "norm",
      "label": "BGB § 1945 Form der Ausschlagung",
      "source_ref": "source.gesetze-im-internet.bgb",
      "citation": "§ 1945 BGB",
      "version_status": "current_metadata_only"
    },
    {
      "id": "norm.bgb.2231",
      "type": "norm",
      "label": "BGB § 2231 Ordentliche Testamente",
      "source_ref": "source.gesetze-im-internet.bgb",
      "citation": "§ 2231 BGB",
      "version_status": "current_metadata_only"
    },
    {
      "id": "norm.bgb.2276",
      "type": "norm",
      "label": "BGB § 2276 Form des Erbvertrags",
      "source_ref": "source.gesetze-im-internet.bgb",
      "citation": "§ 2276 BGB",
      "version_status": "current_metadata_only"
    },
    {
      "id": "norm.bgb.2346",
      "type": "norm",
      "label": "BGB § 2346 Wirkung des Erbverzichts",
      "source_ref": "source.gesetze-im-internet.bgb",
      "citation": "§ 2346 BGB",
      "version_status": "current_metadata_only"
    },
    {
      "id": "norm.bgb.2353",
      "type": "norm",
      "label": "BGB § 2353 Zuständigkeit und Antrag",
      "source_ref": "source.gesetze-im-internet.bgb",
      "citation": "§ 2353 BGB",
      "version_status": "current_metadata_only"
    },
    {
      "id": "usecase.testament-erbvertrag",
      "type": "notarial_usecase",
      "label": "Testament / Erbvertrag",
      "usecase_path": "usecases/testament-erbvertrag"
    },
    {
      "id": "usecase.erbausschlagung",
      "type": "notarial_usecase",
      "label": "Erbausschlagung",
      "usecase_path": "usecases/erbausschlagung"
    },
    {
      "id": "usecase.erbscheinsantrag-nachlass",
      "type": "notarial_usecase",
      "label": "Erbscheinsantrag / Nachlass",
      "usecase_path": "usecases/erbscheinsantrag-nachlass"
    },
    {
      "id": "usecase.pflichtteilsverzicht-erbverzicht",
      "type": "notarial_usecase",
      "label": "Pflichtteilsverzicht / Erbverzicht",
      "usecase_path": "usecases/pflichtteilsverzicht-erbverzicht"
    },
    {
      "id": "review.form",
      "type": "review_point",
      "label": "Formprüfung",
      "status": "review_required"
    },
    {
      "id": "review.capacity",
      "type": "review_point",
      "label": "Geschäftsfähigkeit und Testierfähigkeit",
      "status": "review_required"
    },
    {
      "id": "connector.beck-online",
      "type": "commentary_connector",
      "label": "beck-online Kommentarzugriff",
      "provider_id": "beck-online",
      "status": "license_review_required",
      "connection_mode": "mcp_or_api_required",
      "full_text_storage": "blocked"
    }
  ],
  "edges": [
    {"from": "norm.bgb.2231", "to": "usecase.testament-erbvertrag", "type": "affects_usecase"},
    {"from": "norm.bgb.2276", "to": "usecase.testament-erbvertrag", "type": "affects_usecase"},
    {"from": "norm.bgb.1945", "to": "usecase.erbausschlagung", "type": "affects_usecase"},
    {"from": "norm.bgb.2353", "to": "usecase.erbscheinsantrag-nachlass", "type": "affects_usecase"},
    {"from": "norm.bgb.2346", "to": "usecase.pflichtteilsverzicht-erbverzicht", "type": "affects_usecase"},
    {"from": "norm.bgb.2231", "to": "review.form", "type": "supports_review_point"},
    {"from": "norm.bgb.2276", "to": "review.form", "type": "supports_review_point"},
    {"from": "connector.beck-online", "to": "review.form", "type": "needs_commentary_review"}
  ]
}
```

- [ ] **Step 4: Add the package marker**

Create `src/nac_legal_graph/__init__.py`:

```python
from __future__ import annotations

__all__ = ["__version__"]
__version__ = "0.1.0"
```

- [ ] **Step 5: Add the loader and review payload**

Create `src/nac_legal_graph/catalog.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DOMAIN_ROOT = Path("workflows") / "legal-graph" / "domains"
EMPTY_VALUES = (None, "", [], {})


def load_domain_graph(repo_root: Path, domain: str) -> dict[str, Any]:
    path = repo_root / DOMAIN_ROOT / f"{_safe_domain(domain)}.graph.json"
    if not path.is_file():
        raise KeyError(f"Unknown legal graph domain: {domain}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    _assert_no_values(payload)
    return payload


def legal_graph_status(repo_root: Path) -> dict[str, Any]:
    graphs = _load_all_graphs(repo_root)
    return {
        "schema_version": "nac.legal-graph-status/v0.1",
        "domains": len(graphs),
        "domain_status": [_domain_status(graph) for graph in graphs],
    }


def build_review_payload(repo_root: Path, domain: str) -> dict[str, Any]:
    graph = load_domain_graph(repo_root, domain)
    review_items = [
        {
            "id": node["id"],
            "type": node["type"],
            "label": node.get("label", node["id"]),
            "status": node.get("status", node.get("usage_status", "metadata_only")),
        }
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("type") in {"source_document", "review_point", "commentary_connector"}
    ]
    return {
        "schema_version": "nac.legal-graph-review/v0.1",
        "domain": graph["domain"]["id"],
        "graph_id": graph["graph_id"],
        "guardrails": graph["guardrails"],
        "review_items": review_items,
    }


def _load_all_graphs(repo_root: Path) -> list[dict[str, Any]]:
    root = repo_root / DOMAIN_ROOT
    if not root.is_dir():
        return []
    return [load_domain_graph(repo_root, path.name.removesuffix(".graph.json")) for path in sorted(root.glob("*.graph.json"))]


def _domain_status(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    return {
        "id": graph["domain"]["id"],
        "label_de": graph["domain"].get("label_de", graph["domain"]["id"]),
        "status": graph["domain"].get("status", "unknown"),
        "nodes": len(nodes),
        "edges": len([edge for edge in graph.get("edges", []) if isinstance(edge, dict)]),
        "review_required": sum(1 for node in nodes if str(node.get("status", "")).endswith("review_required")),
        "commentary_connectors": sum(1 for node in nodes if node.get("type") == "commentary_connector"),
    }


def _assert_no_values(value: Any) -> None:
    if isinstance(value, dict):
        if "value" in value and value["value"] not in EMPTY_VALUES:
            raise ValueError("Legal graph must not contain mandate values")
        for item in value.values():
            _assert_no_values(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_values(item)


def _safe_domain(domain: str) -> str:
    if not domain.replace("-", "").isalnum():
        raise ValueError(f"Unsafe legal graph domain: {domain}")
    return domain
```

- [ ] **Step 6: Run loader tests and commit**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_legal_graph
```

Expected: `OK`.

Commit:

```bash
git add src/nac_legal_graph workflows/legal-graph/domains/erbrecht.graph.json tests/test_legal_graph.py
git commit -m "feat: add erbrecht legal graph"
```

---

### Task 3: Build Patch/Update Dry-Run

**Files:**
- Create: `src/nac_legal_graph/patches.py`
- Create: `workflows/legal-graph/fixtures/erbrecht-source-update.json`
- Modify: `tests/test_legal_graph.py`

- [ ] **Step 1: Add failing patch tests**

Append these tests to `LegalGraphTests` in `tests/test_legal_graph.py` and add the import:

```python
from nac_legal_graph.patches import build_update_patch
```

```python
    def test_update_patch_is_review_only_and_does_not_merge(self) -> None:
        patch = build_update_patch(REPO_ROOT, "erbrecht")

        self.assertEqual(patch["schema_version"], "nac.legal-graph-patch/v0.1")
        self.assertEqual(patch["domain"], "erbrecht")
        self.assertEqual(patch["status"], "proposed")
        self.assertFalse(patch["auto_merge_allowed"])
        self.assertTrue(patch["human_review_required"])
        self.assertEqual(patch["changes"][0]["action"], "add_node")
        self.assertEqual(patch["changes"][0]["node"]["id"], "norm.bgb.1944")

    def test_update_patch_blocks_commentary_without_contract(self) -> None:
        patch = build_update_patch(REPO_ROOT, "erbrecht")
        commentary_changes = [
            change for change in patch["changes"]
            if change.get("node", {}).get("type") == "commentary_connector"
        ]

        self.assertTrue(commentary_changes)
        self.assertEqual(commentary_changes[0]["status"], "blocked_contract")
```

- [ ] **Step 2: Run patch tests and verify failure**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_legal_graph
```

Expected: `ModuleNotFoundError` for `nac_legal_graph.patches`.

- [ ] **Step 3: Add the update fixture**

Create `workflows/legal-graph/fixtures/erbrecht-source-update.json`:

```json
{
  "schema_version": "nac.legal-graph-source-update/v0.1",
  "domain": "erbrecht",
  "source": {
    "id": "source.gesetze-im-internet.bgb",
    "retrieved_at": "2026-06-12T00:00:00Z"
  },
  "candidate_nodes": [
    {
      "id": "norm.bgb.1944",
      "type": "norm",
      "label": "BGB § 1944 Ausschlagungsfrist",
      "source_ref": "source.gesetze-im-internet.bgb",
      "citation": "§ 1944 BGB",
      "version_status": "current_metadata_only"
    },
    {
      "id": "connector.juris",
      "type": "commentary_connector",
      "label": "juris Kommentarzugriff",
      "provider_id": "juris",
      "status": "license_review_required",
      "connection_mode": "mcp_or_api_required",
      "full_text_storage": "blocked"
    }
  ],
  "candidate_edges": [
    {
      "from": "norm.bgb.1944",
      "to": "usecase.erbausschlagung",
      "type": "affects_usecase"
    }
  ]
}
```

- [ ] **Step 4: Implement patch builder**

Create `src/nac_legal_graph/patches.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .catalog import load_domain_graph


FIXTURE_ROOT = Path("workflows") / "legal-graph" / "fixtures"


def build_update_patch(repo_root: Path, domain: str) -> dict[str, Any]:
    graph = load_domain_graph(repo_root, domain)
    fixture_path = repo_root / FIXTURE_ROOT / f"{domain}-source-update.json"
    if not fixture_path.is_file():
        raise KeyError(f"Unknown legal graph update fixture: {domain}")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    existing_nodes = {node["id"] for node in graph.get("nodes", []) if isinstance(node, dict) and "id" in node}
    existing_edges = {
        (edge.get("from"), edge.get("to"), edge.get("type"))
        for edge in graph.get("edges", [])
        if isinstance(edge, dict)
    }
    changes: list[dict[str, Any]] = []
    for node in fixture.get("candidate_nodes", []):
        if not isinstance(node, dict) or node.get("id") in existing_nodes:
            continue
        changes.append(
            {
                "action": "add_node",
                "status": _change_status(node),
                "node": node,
            }
        )
    for edge in fixture.get("candidate_edges", []):
        edge_key = (edge.get("from"), edge.get("to"), edge.get("type")) if isinstance(edge, dict) else None
        if edge_key and edge_key not in existing_edges:
            changes.append(
                {
                    "action": "add_edge",
                    "status": "proposed",
                    "edge": edge,
                }
            )
    return {
        "schema_version": "nac.legal-graph-patch/v0.1",
        "domain": domain,
        "source": fixture.get("source", {}),
        "status": "proposed",
        "auto_merge_allowed": False,
        "human_review_required": True,
        "changes": changes,
    }


def _change_status(node: dict[str, Any]) -> str:
    if node.get("type") == "commentary_connector":
        return "blocked_contract"
    return "proposed"
```

- [ ] **Step 5: Run patch tests and commit**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_legal_graph
```

Expected: `OK`.

Commit:

```bash
git add src/nac_legal_graph/patches.py workflows/legal-graph/fixtures/erbrecht-source-update.json tests/test_legal_graph.py
git commit -m "feat: add legal graph patch dry run"
```

---

### Task 4: Add `nac legal-graph` CLI

**Files:**
- Modify: `src/nac_cli/cli.py`
- Modify: `tests/test_nac_cli.py`

- [ ] **Step 1: Add failing CLI tests**

Append to `NaCCliTests` in `tests/test_nac_cli.py`:

```python
    def test_legal_graph_status_cli_returns_json(self) -> None:
        rc, output = run_cli("legal-graph", "status", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.legal-graph-status/v0.1")
        self.assertEqual(payload["domain_status"][0]["id"], "erbrecht")

    def test_legal_graph_review_cli_returns_json(self) -> None:
        rc, output = run_cli("legal-graph", "review", "erbrecht", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.legal-graph-review/v0.1")
        self.assertFalse(payload["guardrails"]["commentary_full_text_in_repo"])

    def test_legal_graph_update_dry_run_cli_returns_patch(self) -> None:
        rc, output = run_cli("legal-graph", "update-dry-run", "erbrecht", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.legal-graph-patch/v0.1")
        self.assertFalse(payload["auto_merge_allowed"])
```

- [ ] **Step 2: Run CLI tests and verify failure**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_cli
```

Expected: argparse exits with an invalid choice for `legal-graph`.

- [ ] **Step 3: Add imports**

In `src/nac_cli/cli.py`, add:

```python
from nac_legal_graph.catalog import build_review_payload, legal_graph_status
from nac_legal_graph.patches import build_update_patch
```

- [ ] **Step 4: Add parser branch**

In `build_parser()`, before the `tenant` parser block, add:

```python
    legal_graph = subparsers.add_parser("legal-graph", help="Steuert den NaC-Rechtsgraphen.")
    legal_graph_sub = legal_graph.add_subparsers(dest="legal_graph_command", required=True)
    legal_graph_status_parser = legal_graph_sub.add_parser("status", help="Zeigt Legal-Graph-Domänen und Reviewstatus.")
    legal_graph_status_parser.add_argument("--format", choices=["text", "json"], default="text")
    legal_graph_review = legal_graph_sub.add_parser("review", help="Zeigt eine Review-Ansicht für eine Legal-Graph-Domäne.")
    legal_graph_review.add_argument("domain")
    legal_graph_review.add_argument("--format", choices=["text", "json"], default="text")
    legal_graph_update = legal_graph_sub.add_parser("update-dry-run", help="Erzeugt einen Review-Patch ohne Merge.")
    legal_graph_update.add_argument("domain")
    legal_graph_update.add_argument("--format", choices=["text", "json"], default="text")
    legal_graph.set_defaults(func=command_legal_graph)
```

- [ ] **Step 5: Add command handler**

In `src/nac_cli/cli.py`, near the other command handlers, add:

```python
def command_legal_graph(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    try:
        if args.legal_graph_command == "status":
            payload = legal_graph_status(repo_root)
            if args.format == "json":
                print_json(payload)
                return 0
            print("NaC Legal Graph")
            for item in payload["domain_status"]:
                print(
                    f"- {item['id']}: {item['nodes']} Knoten, "
                    f"{item['edges']} Kanten, {item['review_required']} Reviewpunkte"
                )
            return 0
        if args.legal_graph_command == "review":
            payload = build_review_payload(repo_root, args.domain)
            if args.format == "json":
                print_json(payload)
                return 0
            print(f"NaC Legal Graph Review: {payload['domain']}")
            for item in payload["review_items"]:
                print(f"- {item['id']}: {item['status']}")
            return 0
        if args.legal_graph_command == "update-dry-run":
            payload = build_update_patch(repo_root, args.domain)
            if args.format == "json":
                print_json(payload)
                return 0
            print(f"NaC Legal Graph Update-Dry-run: {payload['domain']}")
            print(f"- Änderungen: {len(payload['changes'])}")
            print(f"- Auto-Merge: {payload['auto_merge_allowed']}")
            return 0
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    raise AssertionError(f"Unknown legal graph command: {args.legal_graph_command}")
```

- [ ] **Step 6: Run CLI tests and commit**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_cli tests.test_legal_graph
```

Expected: `OK`.

Commit:

```bash
git add src/nac_cli/cli.py tests/test_nac_cli.py
git commit -m "feat: expose legal graph cli"
```

---

### Task 5: Add Documentation, Indexes And Review Path

**Files:**
- Modify: `workflows/contracts/README.md`
- Modify: `docs/de/cli.md`
- Modify: `docs/en/cli.md`
- Modify: `docs/de/pruefung-standardisierung-start.md`
- Modify: `docs/en/pruefung-standardisierung-start.md`
- Modify: `roadmap/GANTT.md`

- [ ] **Step 1: Update workflow contract index**

In `workflows/contracts/README.md`, add these bullets under "Implementierte Verträge":

```markdown
- [workflows/contracts/legal-graph.contract.json](legal-graph.contract.json):
  Vertrag für den mandatsdatenfreien NaC-Rechtsgraphen mit Primärquellen,
  Erbrechts-MVP, Review-Patches und No-Auto-Merge-Regel.
- [workflows/contracts/legal-commentary-connectors.contract.json](legal-commentary-connectors.contract.json):
  Vertrag für lizenzierte Kommentar- und Verlagsquellen über MCP/API ohne
  Credentials, Mandatsdaten oder Kommentar-Volltexte im Produktrepo.
```

- [ ] **Step 2: Update German CLI docs**

In `docs/de/cli.md`, add a `legal-graph` section near the other command groups:

````markdown
## `nac legal-graph`

Der Befehl steuert den mandatsdatenfreien NaC-Rechtsgraphen. Der erste MVP ist
Erbrecht. Automatische Quellenläufe erzeugen nur Review-Patches; ein Merge
braucht fachliche Prüfung.

```bash
nac legal-graph status
nac legal-graph review erbrecht --format json
nac legal-graph update-dry-run erbrecht --format json
```

Lizenzierte Kommentare und Verlagsquellen laufen nicht über Scraping oder
Volltextimport, sondern nur über geprüfte MCP-/API-Connectoren mit
Lizenz-, AVV-/DPA-, Berufsgeheimnis-, AI-SBOM- und Review-Gate.
````

- [ ] **Step 3: Update English CLI docs**

In `docs/en/cli.md`, add:

````markdown
## `nac legal-graph`

This command controls the mandate-data-free NaC legal graph. The first MVP is
inheritance law. Automatic source runs only create review patches; a merge
requires professional review.

```bash
nac legal-graph status
nac legal-graph review erbrecht --format json
nac legal-graph update-dry-run erbrecht --format json
```

Licensed commentaries and publisher sources do not use scraping or full-text
imports. They require reviewed MCP/API connectors with license, AVV/DPA,
professional-secrecy, AI-SBOM and review gates.
````

- [ ] **Step 4: Update Prüfung/Standardisierung docs**

In `docs/de/pruefung-standardisierung-start.md`, add a bullet under "Was Bewertbar Ist":

```markdown
- der mandatsdatenfreie Legal Graph für Erbrecht und seine
  Kommentar-Connector-Grenzen,
```

In `docs/en/pruefung-standardisierung-start.md`, add the equivalent:

```markdown
- the mandate-data-free legal graph for inheritance law and its commentary
  connector boundaries,
```

- [ ] **Step 5: Update roadmap**

In `roadmap/GANTT.md`, add one line in section B after the legal-research connector sentence or as a new task after `b1w`:

```mermaid
    Legal-Graph-Erbrechts-MVP planen             :active,  b1z, 2026-06-12, 14d
```

In the progress row B, add one sentence:

```markdown
The legal graph track plans the first inheritance-law MVP with a primary-source
graph, review patches and a separate commentary connector contract for licensed
MCP/API sources without full-text or credential storage in the product repo.
```

- [ ] **Step 6: Run docs and language checks**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/validate_language_parity.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_doc_links.py
```

Expected: both print `STATUS: PASSED`.

- [ ] **Step 7: Commit docs**

Commit:

```bash
git add workflows/contracts/README.md docs/de/cli.md docs/en/cli.md docs/de/pruefung-standardisierung-start.md docs/en/pruefung-standardisierung-start.md roadmap/GANTT.md
git commit -m "docs: document legal graph workflow"
```

---

### Task 6: Final Verification

**Files:**
- Modify only if checks require it.

- [ ] **Step 1: Run unit tests for the new slice**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_legal_graph_contracts tests.test_legal_graph tests.test_nac_cli
```

Expected: `OK`.

- [ ] **Step 2: Run contract validation**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/validate_legal_graph_contracts.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_legal_research_connectors.py
```

Expected: both print `STATUS: PASSED`.

- [ ] **Step 3: Run repo-level checks**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/validate_language_parity.py
/home/ubuntu/.venvs/nac/bin/python scripts/validate_doc_links.py
/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: each command exits 0. `quality_gate.py --profile strict` must pass before claiming the implementation is complete.

- [ ] **Step 4: Check working tree**

Run:

```bash
git status --short
```

Expected: no unstaged or untracked files except intentionally ignored local artifacts.

---

## Self-Review

- Spec coverage: M1 contracts, M2 inheritance-law MVP, M3 update dry-run, CLI, docs, validation and commentary connector boundaries are covered. M4 family/corporate expansion is intentionally not implemented in this first plan.
- Placeholder scan: no placeholder markers in the planned implementation files; tests specify exact expected schema IDs and guardrails.
- Type consistency: graph payloads use `schema_version`, `graph_id`, `domain`, `nodes`, `edges`, `guardrails`; patch payloads use `schema_version`, `domain`, `status`, `auto_merge_allowed`, `human_review_required`, `changes`.
