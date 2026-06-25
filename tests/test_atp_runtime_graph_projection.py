from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def read_json(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class AtpRuntimeGraphProjectionTests(unittest.TestCase):
    def test_projects_process_events_to_metadata_graph_with_parallel_and_critical_path(self) -> None:
        from nac_runtime.graph_projection import project_process_graph
        from nac_runtime.store import InMemoryRuntimeStore

        store = InMemoryRuntimeStore()
        store.put_tenant(
            tenant_id="tenant.myjur",
            payload={"schema_version": "nac.runtime.tenant/v0.1", "tenant_slug": "myjur"},
        )
        store.put_matter(
            matter_id="matter.synthetic.001",
            tenant_id="tenant.myjur",
            payload={"schema_version": "nac.runtime.matter/v0.1", "matter_type": "immobilienkaufvertrag"},
        )
        store.put_process_instance(
            process_instance_id="process.synthetic.001",
            tenant_id="tenant.myjur",
            matter_id="matter.synthetic.001",
            payload={
                "schema_version": "nac.runtime.process-instance/v0.1",
                "template_ref": "bpmn:immobilienkaufvertrag:xnp-demo",
            },
        )
        store.append_process_event(
            event_id="event.001",
            tenant_id="tenant.myjur",
            process_instance_id="process.synthetic.001",
            event_type="gate_reached",
            payload={
                "schema_version": "nac.runtime.process-event/v0.1",
                "step": "Beurkundung vorbereiten",
                "gate": "xnp_readiness",
                "external_system": "XNP/SNP",
                "parallel_group": "vorbereitung",
                "duration_band": "hours_to_days",
                "critical_path": False,
            },
        )
        store.append_process_event(
            event_id="event.002",
            tenant_id="tenant.myjur",
            process_instance_id="process.synthetic.001",
            event_type="external_wait",
            payload={
                "schema_version": "nac.runtime.process-event/v0.1",
                "step": "Grundbuchruecklauf pruefen",
                "gate": "grundbuch_ruecklauf",
                "external_system": "Grundbuch",
                "depends_on": ["xnp_readiness"],
                "duration_band": "weeks_to_months",
                "critical_path": True,
            },
        )

        projection = project_process_graph(
            process_instance_id="process.synthetic.001",
            events=store.list_process_events("process.synthetic.001"),
        )

        self.assertEqual(projection["schema_version"], "nac.atp-runtime-graph-projection/v0.1")
        self.assertEqual(projection["projection_status"], "derived_from_process_events")
        self.assertFalse(projection["live_oci_enabled"])
        self.assertFalse(projection["schema_apply_enabled"])
        self.assertFalse(projection["mandate_data_loaded"])
        self.assertEqual(projection["process_instance_ref"], "process.synthetic.001")
        self.assertEqual(projection["duration_bands"], ["hours_to_days", "weeks_to_months"])
        self.assertEqual(projection["parallel_groups"], ["vorbereitung"])
        self.assertEqual(
            projection["critical_path"],
            [{"gate": "grundbuch_ruecklauf", "duration_band": "weeks_to_months"}],
        )
        node_ids = {node["id"] for node in projection["nodes"]}
        self.assertIn("process:process.synthetic.001", node_ids)
        self.assertIn("gate:xnp_readiness", node_ids)
        self.assertIn("gate:grundbuch_ruecklauf", node_ids)
        self.assertIn("external:XNP/SNP", node_ids)
        self.assertIn("external:Grundbuch", node_ids)
        self.assertIn(
            {
                "id": "dependency:xnp_readiness->grundbuch_ruecklauf",
                "source": "gate:xnp_readiness",
                "target": "gate:grundbuch_ruecklauf",
                "type": "depends_on",
            },
            projection["edges"],
        )
        serialized = json.dumps(projection, ensure_ascii=False, sort_keys=True).lower()
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten", "owner_id"):
            self.assertNotIn(forbidden, serialized)

    def test_projection_fails_closed_for_mismatched_process_events(self) -> None:
        from nac_runtime.graph_projection import project_process_graph
        from nac_runtime.store import RuntimeRecord

        with self.assertRaisesRegex(ValueError, "process_event_scope_mismatch"):
            project_process_graph(
                process_instance_id="process.expected",
                events=[
                    RuntimeRecord(
                        record_type="process_event",
                        record_id="event.other",
                        tenant_id="tenant.myjur",
                        process_instance_id="process.other",
                        event_type="gate_reached",
                        payload={"gate": "xnp_readiness"},
                    )
                ],
            )

    def test_projection_contract_documents_deferred_graph_guardrails(self) -> None:
        contract = read_json("workflows/contracts/atp-runtime-graph-projection.contract.json")
        german = read_text("docs/de/architecture/atp-runtime-graph-projection.md")
        english = read_text("docs/en/architecture/atp-runtime-graph-projection.md")
        combined = "\n".join([json.dumps(contract, sort_keys=True), german, english])

        self.assertEqual(contract["schema_version"], "nac.atp-runtime-graph-projection/v0.1")
        self.assertEqual(contract["projection_source"], "process_events")
        self.assertTrue(contract["outputs"]["critical_path"])
        self.assertTrue(contract["outputs"]["parallel_groups"])
        self.assertTrue(contract["outputs"]["duration_bands"])
        self.assertFalse(contract["guardrails"]["live_oci"])
        self.assertFalse(contract["guardrails"]["schema_apply"])
        self.assertFalse(contract["guardrails"]["mandate_data"])
        self.assertFalse(contract["guardrails"]["secret_material"])
        for term in (
            "process_events",
            "critical path",
            "kritischer Pfad",
            "parallel",
            "duration bands",
            "Dauerbänder",
            "No live OCI",
            "Kein Live-OCI",
        ):
            self.assertIn(term, combined)


if __name__ == "__main__":
    unittest.main()
