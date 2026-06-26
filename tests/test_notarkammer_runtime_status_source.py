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
    AtpRuntimeMetadataRowFetcher,
    AtpRuntimeMetadataRowReader,
    PackagedRuntimeMetadataSource,
    RuntimeMetadataSourceUnavailable,
    UnavailableRuntimeMetadataSource,
    build_atp_runtime_metadata_row_fetcher_from_env,
    build_first_matter_runtime_metadata_source_from_env,
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

    def test_env_runtime_source_is_inactive_without_atp_mode(self) -> None:
        source = build_first_matter_runtime_metadata_source_from_env({})

        self.assertIsNone(source)

    def test_env_runtime_source_uses_atp_row_reader_and_configured_object_key(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        requested_keys: list[str] = []

        def fetch_row(object_key: str) -> dict[str, object]:
            requested_keys.append(object_key)
            return {"metadata": json.dumps(fixture, ensure_ascii=False)}

        source = build_first_matter_runtime_metadata_source_from_env(
            {
                "NAC_FIRST_MATTER_RUNTIME_SOURCE": "atp-json",
                "NAC_FIRST_MATTER_RUNTIME_OBJECT_KEY": "runtime/atp/notarkammer-first.json",
                "NAC_FIRST_MATTER_RUNTIME_PAYLOAD_COLUMN": "metadata",
            },
            row_fetcher=fetch_row,
        )

        display = build_first_matter_status_display_from_metadata_source(source=source)

        self.assertEqual(requested_keys, ["runtime/atp/notarkammer-first.json"])
        self.assertEqual(display["title"], "Immobilienkaufvertrag Status")
        self.assertIn("Keine Mandatsdaten geladen.", display["status_items"])
        self.assertFalse(display["mandate_data_loaded"])
        self.assertFalse(display["productive_xnp_action"])

    def test_env_runtime_source_fails_closed_when_atp_mode_lacks_row_fetcher(self) -> None:
        source = build_first_matter_runtime_metadata_source_from_env(
            {"NAC_FIRST_MATTER_RUNTIME_SOURCE": "atp"}
        )

        self.assertIsInstance(source, UnavailableRuntimeMetadataSource)
        with self.assertRaisesRegex(RuntimeMetadataSourceUnavailable, "runtime_metadata_row_fetcher_missing"):
            source.load_first_matter_metadata()

    def test_env_runtime_source_can_use_configured_atp_row_fetcher_without_secret_leakage(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        connection = FakeConnection()

        def connect(**kwargs: object) -> FakeConnection:
            connection.connect_kwargs.update(kwargs)
            connection.cursor_obj.description = [("PAYLOAD_JSON",)]
            connection.cursor_obj.rows = [(json.dumps(fixture, ensure_ascii=False),)]
            return connection

        source = build_first_matter_runtime_metadata_source_from_env(
            {
                "NAC_FIRST_MATTER_RUNTIME_SOURCE": "atp",
                "NAC_FIRST_MATTER_RUNTIME_OBJECT_KEY": "process.notarkammer-first",
                "NAC_FIRST_MATTER_RUNTIME_TABLE": "nac_process_instances",
                "NAC_FIRST_MATTER_RUNTIME_KEY_COLUMN": "process_instance_id",
                "NAC_FIRST_MATTER_RUNTIME_PAYLOAD_COLUMN": "payload_json",
                "NAC_ATP_USER": "nac_app",
                "NAC_ATP_DSN": "nacdb_low",
                "NAC_ATP_PASSWORD_SECRET_OCID": "fixture-atp-password-secret-reference",
            },
            secret_text_provider=lambda _secret_id: "fixture-db-password",
            connector=connect,
        )

        display = build_first_matter_status_display_from_metadata_source(source=source)

        self.assertEqual(display["title"], "Immobilienkaufvertrag Status")
        self.assertEqual(connection.connect_kwargs["user"], "nac_app")
        self.assertEqual(connection.connect_kwargs["dsn"], "nacdb_low")
        self.assertEqual(connection.connect_kwargs["password"], "fixture-db-password")
        statement, binds = connection.cursor_obj.executions[0]
        serialized_binds = json.dumps(binds, sort_keys=True)
        self.assertIn("SELECT payload_json FROM nac_process_instances", statement)
        self.assertIn("WHERE process_instance_id = :object_key", statement)
        self.assertEqual(binds["object_key"], "process.notarkammer-first")
        self.assertNotIn("fixture-db-password", statement)
        self.assertNotIn("fixture-db-password", serialized_binds)
        self.assertNotIn("fixture-atp-password-secret-reference", statement)
        self.assertNotIn("fixture-atp-password-secret-reference", serialized_binds)

    def test_env_runtime_source_defaults_to_process_instance_anchor_lookup(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        connection = FakeConnection()

        def connect(**kwargs: object) -> FakeConnection:
            connection.connect_kwargs.update(kwargs)
            connection.cursor_obj.description = [("PAYLOAD_JSON",)]
            connection.cursor_obj.rows = [(json.dumps(fixture, ensure_ascii=False),)]
            return connection

        source = build_first_matter_runtime_metadata_source_from_env(
            {
                "NAC_FIRST_MATTER_RUNTIME_SOURCE": "atp",
                "NAC_ATP_USER": "nac_app",
                "NAC_ATP_DSN": "nacdb_low",
                "NAC_ATP_PASSWORD_SECRET_OCID": "fixture-atp-password-secret-reference",
            },
            secret_text_provider=lambda _secret_id: "fixture-db-password",
            connector=connect,
        )

        build_first_matter_status_display_from_metadata_source(source=source)

        statement, binds = connection.cursor_obj.executions[0]
        self.assertIn("FROM nac_process_instances", statement)
        self.assertIn("WHERE process_instance_id = :object_key", statement)
        self.assertEqual(binds["object_key"], DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY)
        self.assertEqual(DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY, "DEMO-PROCESS-IMMOBILIENKAUF-01")

    def test_direct_atp_row_fetcher_rejects_unallowlisted_sql_identifiers(self) -> None:
        with self.assertRaisesRegex(ValueError, "runtime_metadata_table_not_allowed"):
            AtpRuntimeMetadataRowFetcher(
                user="nac_app",
                dsn="nacdb_low",
                password_provider=lambda: "fixture-db-password",
                table_name="nac_process_instances where 1=1",
            )
        with self.assertRaisesRegex(ValueError, "runtime_metadata_key_column_not_allowed"):
            AtpRuntimeMetadataRowFetcher(
                user="nac_app",
                dsn="nacdb_low",
                password_provider=lambda: "fixture-db-password",
                table_name="nac_process_instances",
                key_column="payload_json",
            )

    def test_env_runtime_source_fails_closed_for_invalid_atp_identifier_config(self) -> None:
        source = build_first_matter_runtime_metadata_source_from_env(
            {
                "NAC_FIRST_MATTER_RUNTIME_SOURCE": "atp",
                "NAC_FIRST_MATTER_RUNTIME_TABLE": "nac_process_instances where 1=1",
                "NAC_ATP_USER": "nac_app",
                "NAC_ATP_DSN": "nacdb_low",
                "NAC_ATP_PASSWORD_SECRET_OCID": "fixture-atp-password-secret-reference",
            },
            secret_text_provider=lambda _secret_id: "fixture-db-password",
            connector=lambda **_kwargs: FakeConnection(),
        )

        self.assertIsInstance(source, UnavailableRuntimeMetadataSource)
        with self.assertRaisesRegex(RuntimeMetadataSourceUnavailable, "runtime_metadata_row_fetcher_invalid_config"):
            source.load_first_matter_metadata()

    def test_atp_row_fetcher_env_factory_requires_secret_reference_not_plaintext_password(self) -> None:
        source = build_atp_runtime_metadata_row_fetcher_from_env(
            {
                "NAC_ATP_USER": "nac_app",
                "NAC_ATP_DSN": "nacdb_low",
                "NAC_ATP_PASSWORD": "disabled-plaintext-fixture",
            },
            secret_text_provider=lambda _secret_id: "fixture-db-password",
            connector=lambda **_kwargs: FakeConnection(),
        )

        self.assertIsNone(source)

    def test_atp_row_fetcher_unavailable_errors_drop_secret_exception_cause(self) -> None:
        def password_provider() -> str:
            raise RuntimeError("fixture-db-password")

        fetcher = AtpRuntimeMetadataRowFetcher(
            user="nac_app",
            dsn="nacdb_low",
            password_provider=password_provider,
        )

        with self.assertRaisesRegex(RuntimeMetadataSourceUnavailable, "runtime_metadata_row_fetcher_unavailable") as ctx:
            fetcher(DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY)

        self.assertIsNone(ctx.exception.__cause__)
        self.assertNotIn("fixture-db-password", str(ctx.exception))

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


class FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, dict[str, object]]] = []
        self.description: list[tuple[str]] = []
        self.rows: list[tuple[object, ...]] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        return None

    def execute(self, statement: str, binds: dict[str, object] | None = None) -> None:
        self.executions.append((statement, binds or {}))

    def fetchone(self) -> tuple[object, ...] | None:
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self) -> None:
        self.connect_kwargs: dict[str, object] = {}
        self.cursor_obj = FakeCursor()

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self.cursor_obj


if __name__ == "__main__":
    unittest.main()
