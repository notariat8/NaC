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
    AtpRuntimeMetadataRowReader,
    PackagedRuntimeMetadataSource,
    RuntimeMetadataSourceUnavailable,
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

    def test_atp_runtime_metadata_row_reader_feeds_status_display(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        requested_keys: list[str] = []

        def fetch_row(object_key: str) -> dict[str, object]:
            requested_keys.append(object_key)
            return {"object_key": object_key, "payload_json": json.dumps(fixture, ensure_ascii=False)}

        reader = AtpRuntimeMetadataRowReader(fetch_row)
        display = build_first_matter_status_display_from_metadata_source(
            source=AtpJsonRuntimeMetadataSource(reader),
        )

        self.assertEqual(requested_keys, [DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY])
        self.assertEqual(display["title"], "Immobilienkaufvertrag Status")
        self.assertIn("Keine Mandatsdaten geladen.", display["status_items"])
        self.assertFalse(display["mandate_data_loaded"])
        self.assertFalse(display["productive_xnp_action"])
        self.assertFalse(display["full_workspace_open"])

    def test_atp_runtime_metadata_row_reader_normalizes_bytes_and_mapping_payloads(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cases = (
            {"payload_json": json.dumps(fixture, ensure_ascii=False).encode("utf-8")},
            {"payload_json": dict(fixture)},
            dict(fixture),
            {"payload": dict(fixture)},
        )

        for row in cases:
            with self.subTest(row_keys=sorted(row.keys())):
                reader = AtpRuntimeMetadataRowReader(lambda _object_key, row=row: row)
                payload = reader(DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY)

                self.assertEqual(payload["data_model_slice"], "runtime_graph_metadata_v0")
                self.assertFalse(payload["mandate_data_present"])
                self.assertFalse(payload["raw_mandate_content_loaded"])
                self.assertFalse(payload["secret_material_present"])

    def test_atp_runtime_metadata_row_reader_fails_closed_for_missing_or_malformed_rows(self) -> None:
        error_cases = (
            (
                lambda _object_key: None,
                RuntimeMetadataSourceUnavailable,
                "runtime_metadata_row_missing",
            ),
            (
                lambda _object_key: [],  # type: ignore[return-value]
                ValueError,
                "runtime_metadata_row_not_object",
            ),
            (
                lambda _object_key: {"payload_json": "{"},
                ValueError,
                "runtime_metadata_json_invalid",
            ),
            (
                lambda _object_key: {"payload_json": "[]"},
                ValueError,
                "runtime_metadata_payload_not_object",
            ),
        )

        for fetch_row, error_type, message in error_cases:
            with self.subTest(message=message):
                reader = AtpRuntimeMetadataRowReader(fetch_row)  # type: ignore[arg-type]

                with self.assertRaisesRegex(error_type, message):
                    reader(DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY)

    def test_atp_runtime_metadata_row_reader_rejects_mandate_secret_and_productive_payloads(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cases = (
            ("mandate_data_present", True, "runtime_metadata_mandate_data_not_allowed"),
            ("raw_mandate_content_loaded", True, "runtime_metadata_raw_mandate_not_allowed"),
            ("secret_material_present", True, "runtime_metadata_secret_material_not_allowed"),
            ("contains_credentials", True, "runtime_metadata_credentials_not_allowed"),
            ("productive_xnp_action", True, "runtime_metadata_productive_xnp_action_not_allowed"),
            ("client_secret", "secret-value", "runtime_metadata_forbidden_term: client_secret"),
        )

        for field, value, message in cases:
            with self.subTest(field=field):
                payload = dict(fixture)
                payload[field] = value
                reader = AtpRuntimeMetadataRowReader(lambda _object_key, payload=payload: {"payload_json": payload})

                with self.assertRaisesRegex(ValueError, message):
                    reader(DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY)


if __name__ == "__main__":
    unittest.main()
