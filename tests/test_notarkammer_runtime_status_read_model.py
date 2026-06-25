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
from nac_runtime.status_read_model import build_first_matter_status
from nac_runtime.store import InMemoryRuntimeStore

FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "demo"
    / "notarkammer-first-immobilienkaufvertrag.metadata.json"
)
CONTRACT = REPO_ROOT / "workflows" / "contracts" / "notarkammer-runtime-status-read-model.contract.json"


class NotarkammerRuntimeStatusReadModelTests(unittest.TestCase):
    def test_read_model_returns_redacted_metadata_only_status(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        store = InMemoryRuntimeStore()
        seed = seed_notarkammer_first_matter(store=store, fixture=fixture)

        status = build_first_matter_status(
            store=store,
            process_instance_id=seed["process_instance_id"],
        )
        serialized = json.dumps(status, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(status["schema_version"], "nac.runtime-status-read-model/v0.1")
        self.assertEqual(status["status"], "portal_start_metadata_ready")
        self.assertEqual(status["matter_label"], "Immobilienkaufvertrag")
        self.assertTrue(status["bpmn_model_present"])
        self.assertTrue(status["xnp_snp_target_path_prepared"])
        self.assertTrue(status["execution_path_visible"])
        self.assertEqual(status["critical_path_summary"], "Externer Rücklauf")
        self.assertEqual(status["duration_band_summary"], "Wochen bis Monate")
        self.assertFalse(status["mandate_data_loaded"])
        self.assertFalse(status["productive_xnp_action"])
        self.assertFalse(status["full_workspace_open"])
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
            "mandatsdaten",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_read_model_fails_closed_when_runtime_events_are_missing(self) -> None:
        store = InMemoryRuntimeStore()

        with self.assertRaisesRegex(ValueError, "runtime_status_process_events_missing"):
            build_first_matter_status(
                store=store,
                process_instance_id="DEMO-PROCESS-IMMOBILIENKAUF-01",
            )

    def test_contract_keeps_safe_output_boundary_visible(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

        self.assertEqual(contract["schema_version"], "nac.runtime-status-read-model/v0.1")
        self.assertEqual(contract["source"], "ATP runtime store process events")
        self.assertFalse(contract["output_guardrails"]["tenant_id"])
        self.assertFalse(contract["output_guardrails"]["matter_id"])
        self.assertFalse(contract["output_guardrails"]["process_instance_id"])
        self.assertFalse(contract["output_guardrails"]["provider_details"])
        self.assertFalse(contract["output_guardrails"]["claims"])
        self.assertFalse(contract["output_guardrails"]["mandate_data"])
        self.assertFalse(contract["output_guardrails"]["productive_xnp_action"])


if __name__ == "__main__":
    unittest.main()
