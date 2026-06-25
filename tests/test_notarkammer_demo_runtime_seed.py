from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_runtime.demo_seed import seed_notarkammer_first_matter
from nac_runtime.graph_projection import project_process_graph
from nac_runtime.store import InMemoryRuntimeStore

FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "demo"
    / "notarkammer-first-immobilienkaufvertrag.metadata.json"
)
CONTRACT = REPO_ROOT / "workflows" / "contracts" / "notarkammer-demo-runtime-seed.contract.json"
DE_DOC = REPO_ROOT / "docs" / "de" / "architecture" / "notarkammer-demo-runtime-seed.md"
EN_DOC = REPO_ROOT / "docs" / "en" / "architecture" / "notarkammer-demo-runtime-seed.md"


class NotarkammerDemoRuntimeSeedTests(unittest.TestCase):
    def test_seed_writes_metadata_only_runtime_records_and_projectable_events(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        store = InMemoryRuntimeStore()

        result = seed_notarkammer_first_matter(store=store, fixture=fixture)
        exported = store.export_json()

        self.assertEqual(result["schema_version"], "nac.demo-runtime-seed/v0.1")
        self.assertEqual(result["tenant_id"], "DEMO-TENANT-NOTARIAT-01")
        self.assertEqual(result["matter_id"], "DEMO-MATTER-IMMOBILIENKAUF-01")
        self.assertEqual(result["process_instance_id"], "DEMO-PROCESS-IMMOBILIENKAUF-01")
        self.assertFalse(result["mandate_data_loaded"])
        self.assertFalse(result["productive_xnp_action"])
        self.assertFalse(result["oci_apply_enabled"])

        self.assertEqual(len(exported["records"]["tenants"]), 1)
        self.assertEqual(len(exported["records"]["matters"]), 1)
        self.assertEqual(len(exported["records"]["process_instances"]), 1)
        self.assertGreaterEqual(len(exported["records"]["process_events"]), 6)
        self.assertGreaterEqual(len(exported["records"]["audit_events"]), 1)

        events = store.list_process_events(result["process_instance_id"])
        graph = project_process_graph(process_instance_id=result["process_instance_id"], events=events)
        labels = {node["label"] for node in graph["nodes"]}
        edge_types = {edge["type"] for edge in graph["edges"]}

        self.assertIn("xnp_local_readiness_only", labels)
        self.assertIn("xnp_snp_target_metadata_only", labels)
        self.assertIn("grundbuch_external_boundary", labels)
        self.assertIn("kaufpreisfaelligkeit", labels)
        self.assertIn("touches_gate", edge_types)
        self.assertIn("depends_on", edge_types)
        self.assertIn("post_beurkundung_parallel", graph["parallel_groups"])
        self.assertIn("weeks_to_months", graph["duration_bands"])
        self.assertTrue(graph["critical_path"])
        self.assertFalse(graph["mandate_data_loaded"])

    def test_seed_rejects_non_metadata_or_productive_fixture(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        store = InMemoryRuntimeStore()

        fixture["scope"] = "mandate_data"
        with self.assertRaisesRegex(ValueError, "demo_fixture_not_metadata_only"):
            seed_notarkammer_first_matter(store=store, fixture=fixture)

        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        fixture["productive_xnp_action"] = True
        with self.assertRaisesRegex(ValueError, "productive_xnp_action_not_allowed"):
            seed_notarkammer_first_matter(store=store, fixture=fixture)

    def test_seed_contract_and_docs_keep_guardrails_visible(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        german = DE_DOC.read_text(encoding="utf-8")
        english = EN_DOC.read_text(encoding="utf-8")
        combined = "\n".join([json.dumps(contract, sort_keys=True), german, english])

        self.assertEqual(contract["schema_version"], "nac.demo-runtime-seed/v0.1")
        self.assertEqual(contract["source_fixture"], str(FIXTURE.relative_to(REPO_ROOT)))
        self.assertTrue(contract["writes"]["process_events"])
        self.assertEqual(contract["graph_projection"]["contract"], "nac.atp-runtime-graph-projection/v0.1")
        self.assertFalse(contract["guardrails"]["mandate_data"])
        self.assertFalse(contract["guardrails"]["productive_xnp_action"])
        self.assertFalse(contract["guardrails"]["live_oci"])
        self.assertFalse(contract["guardrails"]["schema_apply"])
        for term in (
            "ATP Runtime Store Adapter",
            "Runtime Graph Projection",
            "XNP/SNP",
            "Dauerbändern",
            "critical path",
            "No mandate data",
            "Keine Mandatsdaten",
        ):
            self.assertIn(term, combined)


if __name__ == "__main__":
    unittest.main()
