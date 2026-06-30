from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_ai_sbom.export_mapping import ai_sbom_export_mapping_status, load_export_mapping  # noqa: E402
from scripts.validate_ai_sbom_export_mapping import validate  # noqa: E402


class AiSbomExportMappingTests(unittest.TestCase):
    def test_export_mapping_loads_without_release_export(self) -> None:
        mapping = load_export_mapping(REPO_ROOT)
        target_ids = {item["id"] for item in mapping["target_profiles"]}

        self.assertEqual(mapping["schema_version"], "nac.ai-sbom-export-mapping/v0.1")
        self.assertEqual(mapping["status"], "mapping_selected_no_release_export")
        self.assertFalse(mapping["scope"]["release_export_enabled"])
        self.assertFalse(mapping["scope"]["external_tool_execution_enabled"])
        self.assertFalse(mapping["scope"]["mandate_data_allowed"])
        self.assertFalse(mapping["scope"]["secret_material_allowed"])
        self.assertTrue(mapping["scope"]["owner_apply_required_before_release_binding"])
        self.assertEqual(target_ids, {"cyclonedx-json", "spdx-json"})

    def test_export_mapping_status_reports_selected_profiles(self) -> None:
        status = ai_sbom_export_mapping_status(REPO_ROOT)
        profile_ids = {item["id"] for item in status["target_profiles"]}

        self.assertEqual(status["schema_version"], "nac.ai-sbom-export-mapping-status/v0.1")
        self.assertEqual(status["status"], "mapping_selected_no_release_export")
        self.assertEqual(profile_ids, {"cyclonedx-json", "spdx-json"})
        self.assertIn("models", status["mapped_clusters"])
        self.assertFalse(status["release_export_enabled"])
        self.assertFalse(status["external_tool_execution_enabled"])
        self.assertFalse(status["mandate_data_allowed"])
        self.assertTrue(status["owner_apply_required_before_release_binding"])
        self.assertIn("attach_ai_sbom_to_release_without_owner_apply", status["blocked_actions"])

    def test_export_mapping_validator_accepts_repository_artifact(self) -> None:
        self.assertEqual(validate(), [])

    def test_export_mapping_artifact_contains_no_prohibited_payload_keys(self) -> None:
        path = REPO_ROOT / "sbom" / "ai" / "nac-ai-sbom-export-mapping.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertFalse(_contains_key(payload, "value"))
        self.assertFalse(_contains_text(payload, "Max Mustermann"))


def _contains_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def _contains_text(value: object, text: str) -> bool:
    if isinstance(value, str):
        return text in value
    if isinstance(value, dict):
        return any(_contains_text(item, text) for item in value.values())
    if isinstance(value, list):
        return any(_contains_text(item, text) for item in value)
    return False


if __name__ == "__main__":
    unittest.main()
