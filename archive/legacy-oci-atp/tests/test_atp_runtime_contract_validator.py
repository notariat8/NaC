from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
STORAGE_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "atp-runtime-storage.contract.json"
ADAPTER_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "atp-runtime-store-adapter.contract.json"
GRAPH_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "atp-runtime-graph-projection.contract.json"


class AtpRuntimeContractValidatorTests(unittest.TestCase):
    def test_validator_accepts_atp_runtime_contracts(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_atp_runtime_contracts.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)

    def test_strict_quality_gate_no_longer_runs_archived_atp_runtime_validator(self) -> None:
        from scripts import quality_gate

        checks = {
            check_id: command
            for check_id, _title, command in quality_gate.build_checks("strict")
        }

        self.assertNotIn("atp_runtime_contracts", checks)
        self.assertIn("teams_sharepoint_graph_data_plane", checks)

    def test_adapter_scope_matches_storage_contract_and_externalizes_sessions(self) -> None:
        storage = json.loads(STORAGE_CONTRACT.read_text(encoding="utf-8"))
        adapter = json.loads(ADAPTER_CONTRACT.read_text(encoding="utf-8"))
        scope = storage["implementation_scope_v0"]
        deferred = {
            item["id"]: item
            for item in scope["externalized_or_deferred_entities"]
        }

        self.assertEqual(scope["runtime_graph_adapter_entities"], adapter["runtime_entities"])
        self.assertEqual(adapter["adapter_scope_v0"]["implemented_entities"], adapter["runtime_entities"])
        self.assertNotIn("sessions", adapter["runtime_entities"])
        self.assertNotIn("process_templates", adapter["runtime_entities"])
        self.assertEqual(deferred["sessions"]["runtime_boundary"], "nac_identity.session_store.AtpSessionStore")
        self.assertEqual(deferred["sessions"]["schema_artifact"], "deploy/database/atp-onboarding-request-store.sql")
        self.assertEqual(deferred["process_templates"]["runtime_boundary"], "process_instances.payload.template_ref")

    def test_graph_runtime_vocabulary_matches_projection_output(self) -> None:
        from nac_runtime.graph_projection import project_process_graph
        from nac_runtime.store import InMemoryRuntimeStore

        graph_contract = json.loads(GRAPH_CONTRACT.read_text(encoding="utf-8"))
        storage_contract = json.loads(STORAGE_CONTRACT.read_text(encoding="utf-8"))
        vocabulary = graph_contract["runtime_vocabulary"]

        self.assertEqual(
            vocabulary,
            storage_contract["graph_projection"]["runtime_projection_vocabulary"],
        )

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
                "critical_path": True,
            },
        )
        projection = project_process_graph(
            process_instance_id="process.validator",
            events=store.list_process_events("process.validator"),
        )

        self.assertLessEqual({node["type"] for node in projection["nodes"]}, set(vocabulary["node_types"]))
        self.assertLessEqual({edge["type"] for edge in projection["edges"]}, set(vocabulary["edge_types"]))
        self.assertFalse(projection["live_oci_enabled"])
        self.assertFalse(projection["schema_apply_enabled"])
        self.assertFalse(projection["mandate_data_loaded"])

    def test_notarsoftware_data_model_points_productive_runtime_to_m365(self) -> None:
        german = (REPO_ROOT / "docs" / "de" / "notarsoftware-datenmodell.md").read_text(encoding="utf-8")
        english = (REPO_ROOT / "docs" / "en" / "notarsoftware-datenmodell.md").read_text(encoding="utf-8")

        self.assertIn("SaaS-Laufzeitmetadaten gehören nach der M365-MVP-Entscheidung", german)
        self.assertIn("Productive SaaS runtime metadata belongs in Teams", english)
        self.assertNotIn("Produktive Daten brauchen\neinen geprüften Sovereign-/DSGVO-Git-Anbieter", german)
        self.assertNotIn("Production data needs\na reviewed sovereign/GDPR Git provider", english)


if __name__ == "__main__":
    unittest.main()
