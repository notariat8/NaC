from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
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

    def test_generated_visual_comparison_rejects_case_matrix_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / "workbench-live-read-binding"
            shutil.copytree(validator.VISUAL_ROOT, generated)
            errors: list[str] = []
            validator._compare_generated_visual_evidence(generated, errors)
            self.assertEqual(errors, [])
            manifest_path = generated / validator.VISUAL_MANIFEST_PATH.name
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["cases"][0]["layout"] = "drifted"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            errors = []
            validator._compare_generated_visual_evidence(generated, errors)
            self.assertIn("generated live host visual case matrix drift", errors)


if __name__ == "__main__":
    unittest.main()
