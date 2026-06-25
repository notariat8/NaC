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


class AtpRuntimeStoreAdapterTests(unittest.TestCase):
    def test_in_memory_adapter_persists_runtime_json_without_owner_or_mandate_data(self) -> None:
        from nac_runtime.store import InMemoryRuntimeStore

        store = InMemoryRuntimeStore()

        tenant = store.put_tenant(
            tenant_id="tenant.myjur",
            payload={
                "schema_version": "nac.runtime.tenant/v0.1",
                "tenant_slug": "myjur",
                "status": "active",
            },
        )
        user = store.put_user_binding(
            user_binding_id="user-binding.myjur.admin",
            tenant_id="tenant.myjur",
            payload={
                "schema_version": "nac.runtime.user-binding/v0.1",
                "subject_hash": "sha256:subject-fixture",
                "role_class": "nac-tenant-admin",
            },
        )
        matter = store.put_matter(
            matter_id="matter.synthetic.001",
            tenant_id="tenant.myjur",
            payload={
                "schema_version": "nac.runtime.matter/v0.1",
                "matter_type": "synthetic_immobilienkauf",
                "status": "open",
            },
        )
        instance = store.put_process_instance(
            process_instance_id="process.synthetic.001",
            tenant_id="tenant.myjur",
            matter_id="matter.synthetic.001",
            payload={
                "schema_version": "nac.runtime.process-instance/v0.1",
                "template_ref": "bpmn:immobilienkauf:v1",
                "state": "started",
            },
        )
        event = store.append_process_event(
            event_id="event.synthetic.001",
            tenant_id="tenant.myjur",
            process_instance_id="process.synthetic.001",
            event_type="gate_reached",
            payload={
                "schema_version": "nac.runtime.process-event/v0.1",
                "gate": "identity_check",
                "status": "waiting",
            },
        )
        audit = store.append_audit_event(
            audit_event_id="audit.synthetic.001",
            tenant_id="tenant.myjur",
            subject_ref="user-binding.myjur.admin",
            action="process_event_appended",
            payload={
                "schema_version": "nac.runtime.audit-event/v0.1",
                "reason": "synthetic_fixture",
                "process_event_id": "event.synthetic.001",
            },
        )

        self.assertEqual(tenant.record_type, "tenant")
        self.assertEqual(user.record_type, "user_binding")
        self.assertEqual(user.tenant_id, "tenant.myjur")
        self.assertEqual(matter.payload["matter_type"], "synthetic_immobilienkauf")
        self.assertEqual(instance.matter_id, "matter.synthetic.001")
        self.assertEqual(event.sequence, 1)
        self.assertEqual(audit.sequence, 1)
        self.assertEqual(store.get_tenant("tenant.myjur"), tenant)
        self.assertEqual(store.list_process_events("process.synthetic.001"), [event])
        self.assertEqual(store.list_audit_events("tenant.myjur"), [audit])

        serialized = store.export_json()
        self.assertFalse(serialized["requires_owner_approval"])
        self.assertFalse(serialized["live_oci_enabled"])
        self.assertFalse(serialized["schema_apply_enabled"])
        self.assertEqual(serialized["graph_projection"]["mode"], "deferred_projection_from_events")
        self.assertIn("user_bindings", serialized["records"])
        self.assertNotIn("users", serialized["records"])
        self.assertIn("process.synthetic.001", json.dumps(serialized, sort_keys=True))
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten", "owner_id"):
            self.assertNotIn(forbidden, json.dumps(serialized, sort_keys=True).lower())

    def test_runtime_store_contract_documents_entities_and_guardrails(self) -> None:
        contract = read_json("workflows/contracts/atp-runtime-store-adapter.contract.json")
        german = read_text("docs/de/architecture/atp-runtime-store-adapter.md")
        english = read_text("docs/en/architecture/atp-runtime-store-adapter.md")
        combined = "\n".join([json.dumps(contract, sort_keys=True), german, english])

        self.assertEqual(contract["schema_version"], "nac.atp-runtime-store-adapter/v0.1")
        self.assertEqual(contract["interface_status"], "owner_free_contract_first")
        self.assertEqual(contract["implementation_scope"], "testable_adapter_interface")
        self.assertEqual(
            contract["runtime_entities"],
            [
                "tenants",
                "user_bindings",
                "matters",
                "process_instances",
                "process_events",
                "audit_events",
            ],
        )
        self.assertTrue(contract["payload_model"]["json_payloads"])
        self.assertEqual(contract["graph_projection"]["status"], "deferred")
        self.assertFalse(contract["guardrails"]["live_oci"])
        self.assertFalse(contract["guardrails"]["schema_apply"])
        self.assertFalse(contract["guardrails"]["secrets"])
        self.assertFalse(contract["guardrails"]["mandate_data"])

        for term in (
            "RuntimeStoreAdapter",
            "InMemoryRuntimeStore",
            "owner-free",
            "owner-frei",
            "JSON payloads",
            "JSON-Payloads",
            "deferred graph projection",
            "spätere Graph-Projektion",
            "No live OCI",
            "Kein Live-OCI",
            "No schema apply",
            "Kein Schema-Apply",
        ):
            self.assertIn(term, combined)


if __name__ == "__main__":
    unittest.main()
