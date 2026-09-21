from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_workbench_live_read_binding",
    ROOT / "scripts/validate_workbench_live_read_binding.py",
)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class WorkbenchLiveReadBindingValidatorTests(unittest.TestCase):
    def test_repository_binding_is_valid(self) -> None:
        self.assertEqual(validator.validate(), [])

    def test_quality_gate_transfers_all_live_host_build_evidence(self) -> None:
        workflow = (ROOT / ".github/workflows/quality-gate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "spfx/nac-bpmn-viewer/lib-commonjs/webparts/nacBpmnViewer/services/ClientObservationReceipt.js",
            workflow,
        )
        self.assertIn(
            "path: spfx/nac-bpmn-viewer/lib-commonjs/webparts/nacBpmnViewer\n",
            workflow,
        )

    def test_number_detection_excludes_json_booleans(self) -> None:
        self.assertFalse(validator._contains_number({"flag": True, "value": None}))
        self.assertTrue(validator._contains_number({"value": 1}))


if __name__ == "__main__":
    unittest.main()
