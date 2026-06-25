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
from nac_runtime.status_presenter import present_first_matter_status
from nac_runtime.status_read_model import build_first_matter_status
from nac_runtime.store import InMemoryRuntimeStore

FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "demo"
    / "notarkammer-first-immobilienkaufvertrag.metadata.json"
)
CONTRACT = REPO_ROOT / "workflows" / "contracts" / "notarkammer-runtime-status-presenter.contract.json"


class NotarkammerRuntimeStatusPresenterTests(unittest.TestCase):
    def test_presenter_returns_demo_safe_first_matter_status(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        store = InMemoryRuntimeStore()
        seed = seed_notarkammer_first_matter(store=store, fixture=fixture)
        status = build_first_matter_status(
            store=store,
            process_instance_id=seed["process_instance_id"],
        )

        display = present_first_matter_status(status)
        serialized = json.dumps(display, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(display["schema_version"], "nac.runtime-status-presenter/v0.1")
        self.assertEqual(display["title"], "Immobilienkaufvertrag Status")
        self.assertEqual(display["matter_label"], "Immobilienkaufvertrag")
        self.assertIn("BPMN-Modell vorhanden.", display["status_items"])
        self.assertIn("XNP/SNP-Zielpfad vorbereitet.", display["status_items"])
        self.assertIn("Vollzugspfad sichtbar.", display["status_items"])
        self.assertIn("Kritischer Pfad: externer rücklauf.", display["status_items"])
        self.assertIn("Dauerband: Wochen bis Monate.", display["status_items"])
        self.assertIn("Parallele Arbeitsschritte erkennbar.", display["status_items"])
        self.assertIn("Keine Mandatsdaten geladen.", display["status_items"])
        self.assertFalse(display["mandate_data_loaded"])
        self.assertFalse(display["productive_xnp_action"])
        self.assertFalse(display["full_workspace_open"])
        self.assertNotIn(seed["tenant_id"].lower(), serialized)
        self.assertNotIn(seed["matter_id"].lower(), serialized)
        self.assertNotIn(seed["process_instance_id"].lower(), serialized)
        for forbidden in (
            "claim",
            "provider",
            "oracle",
            "idcs",
            "client_secret",
            "private_key",
            "owner_id",
            "raw_mandate",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_presenter_fails_closed_for_workspace_or_mandate_status(self) -> None:
        safe_status = {
            "schema_version": "nac.runtime-status-read-model/v0.1",
            "matter_label": "Immobilienkaufvertrag",
            "mandate_data_loaded": False,
            "productive_xnp_action": False,
            "full_workspace_open": False,
        }

        for key, message in (
            ("mandate_data_loaded", "runtime_status_mandate_data_not_allowed"),
            ("productive_xnp_action", "runtime_status_productive_xnp_action_not_allowed"),
            ("full_workspace_open", "runtime_status_full_workspace_not_allowed"),
        ):
            unsafe_status = dict(safe_status)
            unsafe_status[key] = True
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, message):
                    present_first_matter_status(unsafe_status)

    def test_contract_documents_public_output_boundary(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

        self.assertEqual(contract["schema_version"], "nac.runtime-status-presenter/v0.1")
        self.assertEqual(contract["source"], "nac.runtime-status-read-model/v0.1")
        self.assertEqual(contract["output"]["title"], "public_demo_label")
        self.assertEqual(contract["output"]["status_items"], "public_safe_strings")
        self.assertFalse(contract["output_guardrails"]["tenant_id"])
        self.assertFalse(contract["output_guardrails"]["matter_id"])
        self.assertFalse(contract["output_guardrails"]["process_instance_id"])
        self.assertFalse(contract["output_guardrails"]["session_id"])
        self.assertFalse(contract["output_guardrails"]["provider_details"])
        self.assertFalse(contract["output_guardrails"]["claims"])
        self.assertFalse(contract["output_guardrails"]["emails"])
        self.assertFalse(contract["output_guardrails"]["mandate_data"])


if __name__ == "__main__":
    unittest.main()
