from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_bpmn_models.py"
USECASES_ROOT = REPO_ROOT / "usecases"
BPMN_ROOT = REPO_ROOT / "bpmn"


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

    def test_moddle_declares_duration_parallel_and_critical_path_metadata(self) -> None:
        errors = validator.validate_moddle_descriptor()

        self.assertEqual(errors, [])
        payload = validator.json.loads(validator.NAC_MODDLE.read_text(encoding="utf-8"))
        properties = {
            prop["name"]
            for entry in payload["types"]
            for prop in entry.get("properties", [])
            if prop.get("isAttr")
        }

        self.assertIn("durationBand", properties)
        self.assertIn("parallelGroup", properties)
        self.assertIn("criticalPath", properties)

    def test_real_estate_model_marks_duration_parallel_and_critical_path(self) -> None:
        path = BPMN_ROOT / "immobilienkaufvertrag.bpmn"
        root = validator.parse_xml(path)
        self.assertIsNotNone(root)

        nodes = [
            validator.BpmnElement(path, child)
            for process in validator.children_by_tag(root, "process")
            for child in validator.all_process_children(process)
            if child.tag.rsplit("}", maxsplit=1)[-1] in validator.FLOW_NODE_NAMES
        ]

        self.assertTrue(any(node.nac_attr("durationBand") == "standard_external" for node in nodes))
        self.assertTrue(any(node.nac_attr("parallelGroup") == "post_notarization" for node in nodes))
        self.assertTrue(any(node.nac_attr("criticalPath") == "true" for node in nodes))

    def test_every_usecase_has_a_bpmn_model(self) -> None:
        usecase_slugs = {
            path.name
            for path in USECASES_ROOT.iterdir()
            if path.is_dir() and (path / "knowledge-graph.graph.json").is_file()
        }
        model_stems = {path.stem for path in BPMN_ROOT.rglob("*.bpmn")}

        self.assertTrue(usecase_slugs)
        self.assertEqual(sorted(usecase_slugs - model_stems), [])

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

    def test_invalid_duration_band_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "broken-duration.bpmn"
            path.write_text(
                f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:nac="{validator.NAC_NS}">
  <bpmn:process id="Process_Broken"
                name="Broken"
                nac:profile="{validator.NAC_PROFILE}"
                nac:owner="notariat8"
                nac:binding="Git Pull Request">
    <bpmn:startEvent id="Start"
                     name="Start"
                     nac:role="Notariat"
                     nac:channel="internal"
                     nac:dataClass="metadata"
                     nac:approval="none"
                     nac:evidence="none"
                     nac:durationBand="instant"
                     nac:kgRef="immobilienkaufvertrag">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:endEvent id="End"
                   name="End"
                   nac:role="Notariat"
                   nac:channel="internal"
                   nac:dataClass="metadata"
                   nac:approval="none"
                   nac:evidence="none"
                   nac:kgRef="immobilienkaufvertrag">
      <bpmn:incoming>Flow_1</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start" targetRef="End"/>
  </bpmn:process>
</bpmn:definitions>
""",
                encoding="utf-8",
            )

            errors = validator.validate_file(path)

        self.assertTrue(any("nac:durationBand" in error for error in errors), errors)

    def test_real_estate_purchase_usecase_has_demo_external_gates(self) -> None:
        path = BPMN_ROOT / "usecases" / "grundstueckskaufvertrag.bpmn"
        root = validator.parse_xml(path)
        self.assertIsNotNone(root)

        nodes = {
            node.element_id: node
            for process in validator.children_by_tag(root, "process")
            for node in validator.flow_nodes(process, path)
        }

        expected = {
            "Task_VormerkungBeantragen": ("post_notarization", "standard_external", "true"),
            "Task_LoeschungsunterlagenNachhalten": ("post_notarization", "standard_external", "true"),
            "Task_VorkaufsrechtKlaeren": ("post_notarization", "standard_external", "true"),
            "Task_UnbedenklichkeitNachhalten": ("ownership_transfer", "extended_external", "true"),
            "Task_EigentumsumschreibungEinreichen": ("ownership_transfer", "extended_external", "true"),
        }
        for node_id, (parallel_group, duration_band, critical_path) in expected.items():
            with self.subTest(node_id=node_id):
                node = nodes[node_id]
                self.assertEqual(node.nac_attr("parallelGroup"), parallel_group)
                self.assertEqual(node.nac_attr("durationBand"), duration_band)
                self.assertEqual(node.nac_attr("criticalPath"), critical_path)
                self.assertNotEqual(node.nac_attr("dataClass"), "confidential_placeholder")

        self.assertIn("xnotar_xjustiz", validator.split_channel_tokens(nodes["Task_VormerkungBeantragen"].nac_attr("channel")))
        self.assertNotIn("xnp_local", validator.split_channel_tokens(nodes["Task_VormerkungBeantragen"].nac_attr("channel")))

    def test_mortgage_usecase_keeps_xnp_local_as_readiness_not_land_register_feed(self) -> None:
        path = BPMN_ROOT / "usecases" / "grundschuld-hypothekenbestellung.bpmn"
        root = validator.parse_xml(path)
        self.assertIsNotNone(root)

        nodes = {
            node.element_id: node
            for process in validator.children_by_tag(root, "process")
            for node in validator.flow_nodes(process, path)
        }

        readiness = nodes["Task_XnpArbeitsplatzPruefen"]
        self.assertEqual(readiness.nac_attr("durationBand"), "same_day_or_internal")
        self.assertEqual(readiness.nac_attr("parallelGroup"), "local_readiness")
        self.assertEqual(readiness.nac_attr("criticalPath"), "false")
        self.assertIn("xnp_local", validator.split_channel_tokens(readiness.nac_attr("channel")))

        filing = nodes["Task_GrundbuchEinreichungVorbereiten"]
        self.assertEqual(filing.nac_attr("durationBand"), "standard_external")
        self.assertEqual(filing.nac_attr("parallelGroup"), "land_register_filing")
        self.assertEqual(filing.nac_attr("criticalPath"), "true")
        self.assertIn("xnotar_xjustiz", validator.split_channel_tokens(filing.nac_attr("channel")))
        self.assertNotIn("xnp_local", validator.split_channel_tokens(filing.nac_attr("channel")))


if __name__ == "__main__":
    unittest.main()
