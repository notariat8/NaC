from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_bpmn_models.py"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("validate_bpmn_models", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_validator_module()


class BpmnModelValidationTests(unittest.TestCase):
    def test_repository_bpmn_models_are_valid(self) -> None:
        self.assertEqual(validator.validate(), [])

    def test_unknown_sequence_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "broken.bpmn"
            path.write_text(
                """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_Broken" name="Broken">
    <bpmn:startEvent id="Start" name="Start">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:endEvent id="End" name="End"/>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start" targetRef="Missing"/>
  </bpmn:process>
</bpmn:definitions>
""",
                encoding="utf-8",
            )

            errors = validator.validate_file(path)

        self.assertTrue(any("targetRef" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
