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
from nac_runtime.status_display import build_first_matter_status_display
from nac_runtime.store import InMemoryRuntimeStore

FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "demo"
    / "notarkammer-first-immobilienkaufvertrag.metadata.json"
)


class NotarkammerRuntimeStatusDisplayTests(unittest.TestCase):
    def test_display_bridge_builds_safe_status_from_runtime_events(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        store = InMemoryRuntimeStore()
        seed = seed_notarkammer_first_matter(store=store, fixture=fixture)

        display = build_first_matter_status_display(
            store=store,
            process_instance_id=seed["process_instance_id"],
        )
        serialized = json.dumps(display, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(display["schema_version"], "nac.runtime-status-presenter/v0.1")
        self.assertEqual(display["title"], "Immobilienkaufvertrag Status")
        self.assertIn("BPMN-Modell vorhanden.", display["status_items"])
        self.assertIn("XNP/SNP-Zielpfad vorbereitet.", display["status_items"])
        self.assertIn("Kritischer Pfad: externer rücklauf.", display["status_items"])
        self.assertIn("Dauerband: Wochen bis Monate.", display["status_items"])
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

    def test_display_bridge_fails_closed_when_runtime_events_are_missing(self) -> None:
        store = InMemoryRuntimeStore()

        with self.assertRaisesRegex(ValueError, "runtime_status_process_events_missing"):
            build_first_matter_status_display(
                store=store,
                process_instance_id="DEMO-PROCESS-IMMOBILIENKAUF-01",
            )


if __name__ == "__main__":
    unittest.main()
