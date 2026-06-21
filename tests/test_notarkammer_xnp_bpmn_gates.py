from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_bpmn_models.py"
BPMN_ROOT = REPO_ROOT / "bpmn"
PROFILE_PATH = BPMN_ROOT / "nac-bpmn-profile.md"
DE_BUSINESS_LAYER = REPO_ROOT / "docs" / "de" / "bpmn-js-business-layer.md"
EN_BUSINESS_LAYER = REPO_ROOT / "docs" / "en" / "bpmn-js-business-layer.md"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("validate_bpmn_models", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_validator_module()


def node_channels(path: Path, node_id: str) -> set[str]:
    root = validator.parse_xml(path)
    if root is None:
        raise AssertionError(f"{path} could not be parsed")
    for process in validator.children_by_tag(root, "process"):
        for node in validator.flow_nodes(process, path):
            if node.element_id == node_id:
                return set(validator.split_channel_tokens(node.nac_attr("channel")))
    raise AssertionError(f"{node_id} not found in {path}")


class NotarkammerXnpBpmnGateTests(unittest.TestCase):
    def test_xnotar_xjustiz_is_a_valid_bpmn_channel(self) -> None:
        self.assertIn("xnotar_xjustiz", validator.ALLOWED_CHANNELS)

    def test_profile_documents_xnp_and_xnotar_as_distinct_boundaries(self) -> None:
        profile = PROFILE_PATH.read_text(encoding="utf-8")

        self.assertIn("`xnp_local`", profile)
        self.assertIn("`xnotar_xjustiz`", profile)
        self.assertIn("XNP liefert keine Grundbuchdaten an NaC", profile)

    def test_business_layer_docs_name_the_same_public_boundary(self) -> None:
        de_text = DE_BUSINESS_LAYER.read_text(encoding="utf-8")
        en_text = EN_BUSINESS_LAYER.read_text(encoding="utf-8")

        self.assertIn("XNotar/XJustiz-Austauschordner", de_text)
        self.assertIn("XNotar/XJustiz exchange-folder", en_text)
        self.assertIn("keine Grundbuchdaten", de_text)
        self.assertIn("does not deliver", en_text)
        self.assertIn("land-register data", en_text)

    def test_register_filing_uses_xnotar_xjustiz_not_only_xnp_local(self) -> None:
        channels = node_channels(
            BPMN_ROOT / "usecases" / "handelsregisteranmeldung.bpmn",
            "Task_EinreichungVersand",
        )

        self.assertIn("xnotar_xjustiz", channels)
        self.assertIn("register_portal", channels)

    def test_land_register_filing_uses_xnotar_xjustiz_with_land_register_portal(self) -> None:
        filing_nodes = {
            BPMN_ROOT / "usecases" / "grundschuld-hypothekenbestellung.bpmn": "Task_GrundbuchEinreichungVorbereiten",
            BPMN_ROOT / "usecases" / "grundstueckskaufvertrag.bpmn": "Task_VormerkungBeantragen",
        }
        for model, node_id in filing_nodes.items():
            with self.subTest(model=model.name):
                channels = node_channels(model, node_id)
                self.assertIn("xnotar_xjustiz", channels)
                self.assertIn("land_register_portal", channels)

    def test_xnp_local_remains_limited_to_local_readiness_or_signature_path(self) -> None:
        for model in [
            BPMN_ROOT / "usecases" / "handelsregisteranmeldung.bpmn",
            BPMN_ROOT / "usecases" / "grundschuld-hypothekenbestellung.bpmn",
        ]:
            root = validator.parse_xml(model)
            self.assertIsNotNone(root)
            for process in validator.children_by_tag(root, "process"):
                for node in validator.flow_nodes(process, model):
                    channels = set(validator.split_channel_tokens(node.nac_attr("channel")))
                    if "xnp_local" not in channels:
                        continue
                    allowed = (
                        node.tag_name == "serviceTask"
                        or "Signatur" in node.name
                        or "Identität" in node.name
                        or "Beurkundung" in node.name
                        or "Beglaubigung" in node.name
                    )
                    self.assertTrue(allowed, f"{node.location()} misuses xnp_local")


if __name__ == "__main__":
    unittest.main()
