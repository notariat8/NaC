from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class OnboardingRequestTests(unittest.TestCase):
    def test_build_onboarding_request_creates_stable_non_secret_id(self) -> None:
        from nac_identity.onboarding_requests import build_onboarding_request

        request = build_onboarding_request(
            domain="MYJUR.DE",
            tenant_slug="MyJur",
            admin_email="OFunk@MyJur.DE",
            dns_status="verified",
            now="2026-06-10T00:00:00Z",
        )
        serialized = json.dumps(request, sort_keys=True).lower()

        self.assertEqual(request["schema_version"], "nac.onboarding-request/v0.1")
        self.assertEqual(request["request_id"], "onr_myjur_20260610_000000")
        self.assertEqual(request["domain"], "myjur.de")
        self.assertEqual(request["tenant_slug"], "myjur")
        self.assertEqual(request["admin_email"], "ofunk@myjur.de")
        self.assertEqual(request["dns_status"], "verified")
        self.assertEqual(request["request_status"], "submitted")
        self.assertEqual(request["invitation_status"], "not_sent")
        self.assertEqual(request["created_by_surface"], "app.notariat8.de")
        self.assertNotIn("ofunk", request["request_id"])
        self.assertNotIn("@", request["request_id"])
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("private_key", serialized)

    def test_build_onboarding_request_rejects_unready_dns_status(self) -> None:
        from nac_identity.onboarding_requests import build_onboarding_request

        with self.assertRaises(ValueError) as ctx:
            build_onboarding_request(
                domain="myjur.de",
                tenant_slug="myjur",
                admin_email="ofunk@myjur.de",
                dns_status="pending",
                now="2026-06-10T00:00:00Z",
            )

        self.assertIn("dns_status_not_verified", str(ctx.exception))

    def test_disabled_store_fails_closed_without_writing(self) -> None:
        from nac_identity.onboarding_requests import DisabledOnboardingRequestStore, OnboardingRequestStoreDisabled

        store = DisabledOnboardingRequestStore()

        with self.assertRaises(OnboardingRequestStoreDisabled):
            store.create_request({"request_id": "onr_myjur_20260610_000000"})
        with self.assertRaises(OnboardingRequestStoreDisabled):
            store.get_request("onr_myjur_20260610_000000")
        with self.assertRaises(OnboardingRequestStoreDisabled):
            store.list_requests()

    def test_env_factory_requires_explicit_atp_gate_and_secret_reference(self) -> None:
        from nac_identity.onboarding_requests import DisabledOnboardingRequestStore, build_onboarding_request_store_from_env

        missing_gate = build_onboarding_request_store_from_env(
            {
                "NAC_ATP_DSN": "nacdb_low",
                "NAC_ATP_USER": "nac_app",
                "NAC_ATP_PASSWORD_SECRET_OCID": "ocid1.vaultsecret.oc1.eu-frankfurt-1.example",
            }
        )
        plaintext_password_only = build_onboarding_request_store_from_env(
            {
                "NAC_ONBOARDING_STORE": "atp",
                "NAC_ATP_DSN": "nacdb_low",
                "NAC_ATP_USER": "nac_app",
                "NAC_ATP_PASSWORD": "disabled-fixture-value",
            }
        )

        self.assertIsInstance(missing_gate, DisabledOnboardingRequestStore)
        self.assertIsInstance(plaintext_password_only, DisabledOnboardingRequestStore)

    def test_atp_store_create_request_uses_named_binds_without_secret_leakage(self) -> None:
        from nac_identity.onboarding_requests import AtpOnboardingRequestStore, build_onboarding_request

        connections: list[FakeConnection] = []

        def connect(**kwargs: object) -> "FakeConnection":
            connection = FakeConnection(kwargs)
            connections.append(connection)
            return connection

        request = build_onboarding_request(
            domain="myjur.de",
            tenant_slug="myjur",
            admin_email="ofunk@myjur.de",
            dns_status="verified",
            now="2026-06-10T00:00:00Z",
        )
        store = AtpOnboardingRequestStore(
            user="nac_app",
            dsn="nacdb_low",
            password_provider=lambda: "fixture-db-value",
            connector=connect,
        )

        created = store.create_request(request)

        self.assertEqual(created, request)
        self.assertEqual(connections[0].connect_kwargs["user"], "nac_app")
        self.assertEqual(connections[0].connect_kwargs["dsn"], "nacdb_low")
        self.assertEqual(connections[0].connect_kwargs["password"], "fixture-db-value")
        self.assertTrue(connections[0].committed)
        statement, binds = connections[0].cursor_obj.executions[0]
        self.assertIn("INSERT INTO onboarding_requests", statement)
        self.assertEqual(binds["request_id"], "onr_myjur_20260610_000000")
        self.assertEqual(binds["tenant_id"], "tenant.myjur")
        self.assertEqual(binds["domain"], "myjur.de")
        self.assertNotIn("fixture-db-value", json.dumps(binds, sort_keys=True))

    def test_atp_session_store_creates_multi_tenant_user_session_without_secret_leakage(self) -> None:
        from nac_identity.session_store import AtpSessionStore

        connections: list[FakeConnection] = []

        def connect(**kwargs: object) -> "FakeConnection":
            connection = FakeConnection(kwargs)
            connections.append(connection)
            return connection

        store = AtpSessionStore(
            user="nac_app",
            dsn="nacdb_low",
            password_provider=lambda: "fixture-db-value",
            connector=connect,
        )

        created = store.create_session_record(
            session_id="raw-session-secret",
            tenant_slug="myjur",
            subject_hash="subject-hash-1",
            role_class="nac-tenant-admin",
            usecase_slug="immobilienkaufvertrag",
            purpose="portal-start",
            issued_at=1_800_000_000,
            expires_at=1_800_000_600,
            audit_event_id="audit-session-1",
        )

        self.assertEqual(created["schema_version"], "nac.server-session/v0.1")
        self.assertFalse(created["session_id_exposed"])
        self.assertTrue(created["tenant_bound"])
        self.assertTrue(created["subject_bound"])
        self.assertTrue(created["role_bound"])
        self.assertTrue(created["case_bound"])
        self.assertTrue(created["purpose_bound"])
        self.assertEqual(connections[0].connect_kwargs["user"], "nac_app")
        self.assertEqual(connections[0].connect_kwargs["dsn"], "nacdb_low")
        self.assertEqual(connections[0].connect_kwargs["password"], "fixture-db-value")
        self.assertTrue(connections[0].committed)
        statement, binds = connections[0].cursor_obj.executions[0]
        serialized_binds = json.dumps(binds, sort_keys=True)
        self.assertIn("MERGE INTO nac_sessions", statement)
        self.assertIn("session_id_hash", binds)
        self.assertNotEqual(binds["session_id_hash"], "raw-session-secret")
        self.assertEqual(binds["tenant_slug"], "myjur")
        self.assertEqual(binds["subject_hash"], "subject-hash-1")
        self.assertEqual(binds["role_class"], "nac-tenant-admin")
        self.assertEqual(binds["usecase_slug"], "immobilienkaufvertrag")
        self.assertEqual(binds["purpose"], "portal-start")
        self.assertEqual(binds["contains_credentials"], 0)
        self.assertEqual(binds["tokens_stored"], 0)
        self.assertEqual(binds["claims_stored"], 0)
        self.assertNotIn("raw-session-secret", serialized_binds)
        self.assertNotIn("fixture-db-value", serialized_binds)

    def test_atp_session_store_lookup_returns_redacted_runtime_record(self) -> None:
        from nac_identity.session_store import AtpSessionStore

        connection = FakeConnection({})

        def connect(**kwargs: object) -> FakeConnection:
            connection.connect_kwargs.update(kwargs)
            connection.cursor_obj.description = [
                ("SESSION_ID_HASH",),
                ("TENANT_SLUG",),
                ("SUBJECT_HASH",),
                ("ROLE_CLASS",),
                ("USECASE_SLUG",),
                ("PURPOSE",),
                ("ISSUED_AT",),
                ("EXPIRES_AT",),
                ("REVOKED_AT",),
                ("AUDIT_EVENT_ID",),
                ("CONTAINS_CREDENTIALS",),
                ("TOKENS_STORED",),
                ("CLAIMS_STORED",),
            ]
            connection.cursor_obj.rows = [
                (
                    "stored-session-hash",
                    "myjur",
                    "subject-hash-1",
                    "nac-tenant-admin",
                    "immobilienkaufvertrag",
                    "portal-start",
                    1_800_000_000,
                    1_800_000_600,
                    None,
                    "audit-session-1",
                    0,
                    0,
                    0,
                )
            ]
            return connection

        store = AtpSessionStore(
            user="nac_app",
            dsn="nacdb_low",
            password_provider=lambda: "fixture-db-value",
            connector=connect,
        )

        record = store.get_session_record("raw-session-secret")

        self.assertIsNotNone(record)
        assert record is not None
        serialized = json.dumps(record, sort_keys=True)
        select_statement, select_binds = connection.cursor_obj.executions[0]
        self.assertIn("SELECT", select_statement)
        self.assertIn("FROM nac_sessions", select_statement)
        self.assertNotEqual(select_binds["session_id_hash"], "raw-session-secret")
        self.assertEqual(record["schema_version"], "nac.server-session/v0.1")
        self.assertEqual(record["expires_at"], 1_800_000_600)
        self.assertFalse(record["contains_credentials"])
        self.assertFalse(record["tokens_stored"])
        self.assertFalse(record["claims_stored"])
        self.assertEqual(record["audit_event_id"], "audit-session-1")
        self.assertTrue(record["tenant_bound"])
        self.assertTrue(record["subject_bound"])
        self.assertTrue(record["role_bound"])
        self.assertTrue(record["case_bound"])
        self.assertTrue(record["purpose_bound"])
        self.assertNotIn("raw-session-secret", serialized)
        self.assertNotIn("fixture-db-value", serialized)

    def test_atp_store_review_request_updates_status_without_invitation_send(self) -> None:
        from nac_identity.onboarding_requests import AtpOnboardingRequestStore

        connection = FakeConnection({})

        def connect(**kwargs: object) -> FakeConnection:
            connection.connect_kwargs.update(kwargs)
            connection.cursor_obj.description = [
                ("REQUEST_ID",),
                ("TENANT_ID",),
                ("TENANT_SLUG",),
                ("DOMAIN",),
                ("ADMIN_EMAIL",),
                ("DNS_STATUS",),
                ("REQUEST_STATUS",),
                ("INVITATION_STATUS",),
                ("CREATED_AT",),
                ("UPDATED_AT",),
                ("CREATED_BY_SURFACE",),
            ]
            connection.cursor_obj.rows = [
                (
                    "onr_myjur_20260611_182453",
                    "tenant.myjur",
                    "myjur",
                    "myjur.de",
                    "ofunk@myjur.de",
                    "verified",
                    "approved",
                    "not_sent",
                    "2026-06-11T18:24:53Z",
                    "2026-06-11T18:30:00Z",
                    "app.notariat8.de",
                )
            ]
            return connection

        store = AtpOnboardingRequestStore(
            user="nac_app",
            dsn="nacdb_low",
            password_provider=lambda: "fixture-db-value",
            connector=connect,
        )

        reviewed = store.review_request(
            request_id="onr_myjur_20260611_182453",
            decision="approve",
            now="2026-06-11T18:30:00Z",
        )

        update_statement, update_binds = connection.cursor_obj.executions[0]
        select_statement, select_binds = connection.cursor_obj.executions[1]
        self.assertIn("UPDATE onboarding_requests", update_statement)
        self.assertIn("request_status = :request_status", update_statement)
        self.assertIn("invitation_status = :invitation_status", update_statement)
        self.assertEqual(update_binds["request_id"], "onr_myjur_20260611_182453")
        self.assertEqual(update_binds["request_status"], "approved")
        self.assertEqual(update_binds["invitation_status"], "not_sent")
        self.assertEqual(update_binds["updated_at"], "2026-06-11T18:30:00Z")
        self.assertIn("SELECT", select_statement)
        self.assertEqual(select_binds["request_id"], "onr_myjur_20260611_182453")
        self.assertTrue(connection.committed)
        self.assertEqual(reviewed["request_status"], "approved")
        self.assertEqual(reviewed["invitation_status"], "not_sent")
        self.assertEqual(reviewed["domain"], "myjur.de")
        self.assertEqual(reviewed["review_audit"]["schema_version"], "nac.onboarding-review-audit/v0.1")
        self.assertEqual(reviewed["review_audit"]["decision"], "approve")
        self.assertEqual(reviewed["review_audit"]["reviewed_at"], "2026-06-11T18:30:00Z")
        self.assertEqual(reviewed["review_audit"]["review_surface"], "admin.onboarding.review")
        self.assertFalse(reviewed["review_audit"]["contains_mandate_data"])
        self.assertFalse(reviewed["review_audit"]["customer_mail_dispatched"])
        self.assertFalse(reviewed["review_audit"]["oci_write_executed"])
        self.assertFalse(reviewed["review_audit"]["atp_schema_change_required"])
        self.assertNotIn("fixture-db-value", json.dumps(update_binds, sort_keys=True))
        self.assertNotIn("fixture-db-value", json.dumps(reviewed["review_audit"], sort_keys=True))
        self.assertNotIn("ofunk@myjur.de", json.dumps(reviewed["review_audit"], sort_keys=True))

    def test_build_onboarding_review_audit_metadata_is_redacted(self) -> None:
        from nac_identity.onboarding_requests import build_onboarding_review_audit_metadata

        audit = build_onboarding_review_audit_metadata(
            request_id="onr_myjur_20260611_182453",
            decision="approve",
            reviewed_at="2026-06-11T18:30:00Z",
        )
        serialized = json.dumps(audit, sort_keys=True).lower()

        self.assertEqual(audit["schema_version"], "nac.onboarding-review-audit/v0.1")
        self.assertEqual(audit["review_surface"], "admin.onboarding.review")
        self.assertEqual(audit["request_id"], "onr_myjur_20260611_182453")
        self.assertFalse(audit["contains_mandate_data"])
        self.assertFalse(audit["customer_mail_dispatched"])
        self.assertFalse(audit["oci_write_executed"])
        self.assertFalse(audit["atp_schema_change_required"])
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("private_key", serialized)
        self.assertNotIn("password", serialized)
        self.assertNotIn("urkunde", serialized)
        self.assertNotIn("ausweis", serialized)
        self.assertNotIn("einladung senden", serialized)

    def test_env_factory_builds_atp_store_from_secret_reference(self) -> None:
        from nac_identity.onboarding_requests import AtpOnboardingRequestStore, build_onboarding_request_store_from_env

        secret_ids: list[str] = []

        def secret_text_provider(secret_id: str) -> str:
            secret_ids.append(secret_id)
            return "vault-fixture-value"

        store = build_onboarding_request_store_from_env(
            {
                "NAC_ONBOARDING_STORE": "atp",
                "NAC_ATP_DSN": "nacdb_low",
                "NAC_ATP_USER": "nac_app",
                "NAC_ATP_PASSWORD_SECRET_OCID": "ocid1.vaultsecret.oc1.eu-frankfurt-1.example",
            },
            secret_text_provider=secret_text_provider,
            connector=lambda **kwargs: FakeConnection(kwargs),
        )

        self.assertIsInstance(store, AtpOnboardingRequestStore)
        store.create_request(
            {
                "request_id": "onr_myjur_20260610_000000",
                "tenant_id": "tenant.myjur",
                "tenant_slug": "myjur",
                "domain": "myjur.de",
                "admin_email": "ofunk@myjur.de",
                "dns_status": "verified",
                "request_status": "submitted",
                "invitation_status": "not_sent",
                "created_at": "2026-06-10T00:00:00Z",
                "updated_at": "2026-06-10T00:00:00Z",
                "created_by_surface": "app.notariat8.de",
            }
        )

        self.assertEqual(secret_ids, ["ocid1.vaultsecret.oc1.eu-frankfurt-1.example"])

    def test_env_factory_extracts_vault_wallet_zip_ephemerally_for_mtls(self) -> None:
        from nac_identity.onboarding_requests import AtpOnboardingRequestStore, build_onboarding_request_store_from_env

        connections: list[FakeConnection] = []
        password_secret_ids: list[str] = []
        wallet_secret_ids: list[str] = []
        wallet_zip = _build_wallet_zip()

        def secret_text_provider(secret_id: str) -> str:
            password_secret_ids.append(secret_id)
            return "vault-db-password"

        def secret_bytes_provider(secret_id: str) -> bytes:
            wallet_secret_ids.append(secret_id)
            return wallet_zip

        with tempfile.TemporaryDirectory() as temp_dir:
            store = build_onboarding_request_store_from_env(
                {
                    "NAC_ONBOARDING_STORE": "atp",
                    "NAC_ATP_DSN": "nacdb_low",
                    "NAC_ATP_USER": "nac_app",
                    "NAC_ATP_PASSWORD_SECRET_OCID": "vault-password-secret",
                    "NAC_ATP_WALLET_ZIP_SECRET_OCID": "vault-wallet-secret",
                    "NAC_ATP_WALLET_EXTRACT_DIR": temp_dir,
                },
                secret_text_provider=secret_text_provider,
                secret_bytes_provider=secret_bytes_provider,
                connector=lambda **kwargs: connections.append(FakeConnection(kwargs)) or connections[-1],
            )

            self.assertIsInstance(store, AtpOnboardingRequestStore)
            store.create_request(_request_fixture())

            connect_kwargs = connections[0].connect_kwargs
            config_dir = Path(str(connect_kwargs["config_dir"]))
            wallet_location = Path(str(connect_kwargs["wallet_location"]))
            self.assertEqual(config_dir, wallet_location)
            self.assertEqual(config_dir.parent, Path(temp_dir))
            self.assertTrue((config_dir / "tnsnames.ora").exists())
            self.assertTrue((config_dir / "cwallet.sso").exists())

        self.assertEqual(password_secret_ids, ["vault-password-secret"])
        self.assertEqual(wallet_secret_ids, ["vault-wallet-secret"])
        self.assertEqual(connections[0].connect_kwargs["password"], "vault-db-password")

    def test_env_factory_extracts_object_storage_wallet_zip_with_wallet_password_for_mtls(self) -> None:
        from nac_identity.onboarding_requests import AtpOnboardingRequestStore, build_onboarding_request_store_from_env

        connections: list[FakeConnection] = []
        requested_secret_ids: list[str] = []
        requested_objects: list[tuple[str, str, str]] = []
        wallet_zip = _build_wallet_zip()

        def secret_text_provider(secret_id: str) -> str:
            requested_secret_ids.append(secret_id)
            if secret_id == "wallet-password-secret":
                return "fixture-wallet-password"
            return "vault-db-password"

        def object_bytes_provider(namespace: str, bucket_name: str, object_name: str) -> bytes:
            requested_objects.append((namespace, bucket_name, object_name))
            return wallet_zip

        with tempfile.TemporaryDirectory() as temp_dir:
            store = build_onboarding_request_store_from_env(
                {
                    "NAC_ONBOARDING_STORE": "atp",
                    "NAC_ATP_DSN": "nacdb_low",
                    "NAC_ATP_USER": "nac_app",
                    "NAC_ATP_PASSWORD_SECRET_OCID": "vault-password-secret",
                    "NAC_ATP_WALLET_OBJECT_STORAGE_NAMESPACE": "frnyakqskoer",
                    "NAC_ATP_WALLET_BUCKET_NAME": "nac-dev-atp-wallet",
                    "NAC_ATP_WALLET_OBJECT_NAME": "wallets/nacdev-wallet.zip",
                    "NAC_ATP_WALLET_PASSWORD_SECRET_OCID": "wallet-password-secret",
                    "NAC_ATP_WALLET_EXTRACT_DIR": temp_dir,
                },
                secret_text_provider=secret_text_provider,
                object_bytes_provider=object_bytes_provider,
                connector=lambda **kwargs: connections.append(FakeConnection(kwargs)) or connections[-1],
            )

            self.assertIsInstance(store, AtpOnboardingRequestStore)
            store.create_request(_request_fixture())

            connect_kwargs = connections[0].connect_kwargs
            config_dir = Path(str(connect_kwargs["config_dir"]))
            wallet_location = Path(str(connect_kwargs["wallet_location"]))
            self.assertEqual(config_dir, wallet_location)
            self.assertEqual(config_dir.parent, Path(temp_dir))
            self.assertEqual(connect_kwargs["wallet_password"], "fixture-wallet-password")
            self.assertTrue((config_dir / "tnsnames.ora").exists())
            self.assertTrue((config_dir / "cwallet.sso").exists())

        self.assertEqual(requested_secret_ids, ["vault-password-secret", "wallet-password-secret"])
        self.assertEqual(requested_objects, [("frnyakqskoer", "nac-dev-atp-wallet", "wallets/nacdev-wallet.zip")])
        self.assertEqual(connections[0].connect_kwargs["password"], "vault-db-password")

    def test_object_storage_wallet_failure_logs_safe_stage_without_secret_values(self) -> None:
        from nac_identity.onboarding_requests import (
            OnboardingRequestStoreUnavailable,
            build_onboarding_request_store_from_env,
        )

        def object_bytes_provider(namespace: str, bucket_name: str, object_name: str) -> bytes:
            raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable")

        store = build_onboarding_request_store_from_env(
            {
                "NAC_ONBOARDING_STORE": "atp",
                "NAC_ATP_DSN": "nacdb_low",
                "NAC_ATP_USER": "nac_app",
                "NAC_ATP_PASSWORD_SECRET_OCID": "ocid1.vaultsecret.oc1.eu-frankfurt-1.secret-example",
                "NAC_ATP_WALLET_OBJECT_STORAGE_NAMESPACE": "frnyakqskoer",
                "NAC_ATP_WALLET_BUCKET_NAME": "nac-dev-atp-wallet",
                "NAC_ATP_WALLET_OBJECT_NAME": "wallets/nacdev-wallet.zip",
                "NAC_ATP_WALLET_PASSWORD_SECRET_OCID": "wallet-password-secret",
            },
            secret_text_provider=lambda _secret_id: "vault-db-password",
            object_bytes_provider=object_bytes_provider,
            connector=lambda **_kwargs: FakeConnection({}),
        )

        with self.assertLogs("nac_identity.onboarding_requests", level="WARNING") as logs:
            with self.assertRaises(OnboardingRequestStoreUnavailable):
                store.create_request(_request_fixture())

        rendered_logs = "\n".join(logs.output)
        self.assertIn("stage=wallet_object", rendered_logs)
        self.assertNotIn("ocid1.vaultsecret", rendered_logs)
        self.assertNotIn("wallet-password-secret", rendered_logs)
        self.assertNotIn("vault-db-password", rendered_logs)

    def test_wallet_zip_materializer_rejects_path_traversal_without_secret_leakage(self) -> None:
        from nac_identity.onboarding_requests import AtpWalletZipMaterializer, OnboardingRequestStoreUnavailable

        malicious_zip = _build_wallet_zip({"../secret.txt": b"do-not-write"})
        materializer = AtpWalletZipMaterializer(
            wallet_secret_id="vault-wallet-secret",
            wallet_zip_provider=lambda _secret_id: malicious_zip,
        )

        with self.assertRaises(OnboardingRequestStoreUnavailable) as ctx:
            materializer.materialize()

        self.assertEqual(str(ctx.exception), "onboarding_request_store_unavailable")


def _request_fixture() -> dict[str, str]:
    return {
        "request_id": "onr_myjur_20260610_000000",
        "tenant_id": "tenant.myjur",
        "tenant_slug": "myjur",
        "domain": "myjur.de",
        "admin_email": "ofunk@myjur.de",
        "dns_status": "verified",
        "request_status": "submitted",
        "invitation_status": "not_sent",
        "created_at": "2026-06-10T00:00:00Z",
        "updated_at": "2026-06-10T00:00:00Z",
        "created_by_surface": "app.notariat8.de",
    }


def _build_wallet_zip(entries: dict[str, bytes] | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as wallet:
        for name, content in (
            entries
            or {
                "tnsnames.ora": b"NACDB_LOW=(description=fixture)",
                "sqlnet.ora": b"WALLET_LOCATION=(SOURCE=(METHOD=file))",
                "cwallet.sso": b"fixture-wallet-bytes",
            }
        ).items():
            wallet.writestr(name, content)
    return buffer.getvalue()


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

    def fetchall(self) -> list[tuple[object, ...]]:
        return list(self.rows)


class FakeConnection:
    def __init__(self, connect_kwargs: dict[str, object]) -> None:
        self.connect_kwargs = connect_kwargs
        self.cursor_obj = FakeCursor()
        self.committed = False

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True


if __name__ == "__main__":
    unittest.main()
