from __future__ import annotations

import json
import sys
import unittest
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
