from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_runtime.status_source import (
    DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY,
    AtpJsonRuntimeMetadataSource,
    PackagedRuntimeMetadataSource,
    build_first_matter_status_display_from_metadata_source,
    resolve_first_matter_runtime_metadata_source,
)

FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "demo"
    / "notarkammer-first-immobilienkaufvertrag.metadata.json"
)


class NotarkammerRuntimeStatusSourceTests(unittest.TestCase):
    def test_first_matter_source_resolver_defaults_to_packaged_source(self) -> None:
        source = resolve_first_matter_runtime_metadata_source()

        self.assertIsInstance(source, PackagedRuntimeMetadataSource)

    def test_first_matter_source_resolver_keeps_injected_source(self) -> None:
        injected = AtpJsonRuntimeMetadataSource(lambda _object_key: {})

        source = resolve_first_matter_runtime_metadata_source(injected)

        self.assertIs(source, injected)

    def test_packaged_runtime_source_loads_metadata_only_json_without_test_fixture_path(self) -> None:
        payload = PackagedRuntimeMetadataSource().load_first_matter_metadata()
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        self.assertEqual(payload["data_model_slice"], "runtime_graph_metadata_v0")
        self.assertIsInstance(payload["runtime_event_profile"], list)
        self.assertFalse(payload["mandate_data_present"])
        self.assertFalse(payload["productive_xnp_action"])
        self.assertNotIn("tests/fixtures", serialized)

    def test_atp_json_source_can_back_same_status_display_contract(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        requested_keys: list[str] = []

        def read_atp_json(object_key: str) -> dict[str, object]:
            requested_keys.append(object_key)
            return dict(fixture)

        display = build_first_matter_status_display_from_metadata_source(
            source=AtpJsonRuntimeMetadataSource(read_atp_json),
        )

        self.assertEqual(requested_keys, [DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY])
        self.assertEqual(display["title"], "Immobilienkaufvertrag Status")
        self.assertIn("BPMN-Modell vorhanden.", display["status_items"])
        self.assertFalse(display["mandate_data_loaded"])
        self.assertFalse(display["productive_xnp_action"])
        self.assertFalse(display["full_workspace_open"])

    def test_atp_json_source_rejects_invalid_reader_payload(self) -> None:
        source = AtpJsonRuntimeMetadataSource(lambda _object_key: [])  # type: ignore[arg-type]

        with self.assertRaisesRegex(ValueError, "runtime_metadata_source_not_object"):
            source.load_first_matter_metadata()


if __name__ == "__main__":
    unittest.main()
