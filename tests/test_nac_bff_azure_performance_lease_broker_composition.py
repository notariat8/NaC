from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
import hashlib
import unittest

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from nac_bff.azure_performance_lease_broker import AzurePerformanceLeaseBroker
from nac_bff.azure_performance_lease_broker_composition import (
    PERFORMANCE_LEASE_APP_ROLE,
    PERFORMANCE_LEASE_TICKET_SCOPE,
    PerformanceLeaseBrokerCompositionError,
    PerformanceLeaseBrokerSettings,
    build_performance_lease_broker,
)


TENANT = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
ACTOR = "11111111-1111-4111-8111-111111111111"
TARGET = "1" * 64
BLOB_PATH = f"locks/{TARGET}.lock"


def _certificate() -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "NaC owner gate")])
    now = datetime.now(UTC)
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
        .public_bytes(serialization.Encoding.PEM)
    )


def _env() -> dict[str, str]:
    cert = _certificate()
    return {
        "NAC_BFF_PERFORMANCE_LEASE_ENABLED": "true",
        "NAC_BFF_PERFORMANCE_LEASE_TENANT_ID": TENANT,
        "NAC_BFF_AUDIENCE": "api://nac-m365-bff",
        "NAC_BFF_PERFORMANCE_LEASE_ACTOR_ID": ACTOR,
        "NAC_BFF_PERFORMANCE_LEASE_OWNER_SUBJECT": ACTOR,
        "NAC_BFF_PERFORMANCE_LEASE_OWNER_BINDING_SHA256": "2" * 64,
        "NAC_BFF_PERFORMANCE_LEASE_COMMIT_SHA": "3" * 40,
        "NAC_BFF_PERFORMANCE_LEASE_TREE_SHA": "4" * 64,
        "NAC_BFF_PERFORMANCE_LEASE_FUNCTION_PACKAGE_SHA256": "5" * 64,
        "NAC_BFF_PERFORMANCE_LEASE_PLAN_SHA256": "6" * 64,
        "NAC_BFF_PERFORMANCE_LEASE_TARGET_BINDING_SHA256": TARGET,
        "NAC_BFF_PERFORMANCE_LEASE_BLOB_PATH": BLOB_PATH,
        "NAC_BFF_PERFORMANCE_LEASE_BLOB_URL": (
            "https://stnacperflease001.blob.core.windows.net/"
            f"nac-bff-performance-leases/{BLOB_PATH}"
        ),
        "NAC_BFF_PERFORMANCE_LEASE_STORAGE_BINDING_ID": "lease-binding-v1",
        "NAC_BFF_PERFORMANCE_LEASE_STORAGE_ATTESTATION_B64": base64.b64encode(
            b"a" * 64
        ).decode("ascii"),
        "NAC_BFF_PERFORMANCE_LEASE_TICKET_ISSUER": "nac-owner-gate",
        "NAC_BFF_PERFORMANCE_LEASE_TICKET_KEY_ID": "owner-key-v1",
        "NAC_BFF_PERFORMANCE_LEASE_TICKET_CERTIFICATE_B64": base64.b64encode(
            cert
        ).decode("ascii"),
        "NAC_BFF_PERFORMANCE_LEASE_TICKET_CERTIFICATE_SHA256": hashlib.sha256(
            cert
        ).hexdigest(),
    }


class _Credential:
    def get_token(self, scope: str):
        raise AssertionError(scope)


class _Opener:
    def open(self, request: object, *, timeout: float):
        raise AssertionError((request, timeout))


class PerformanceLeaseBrokerCompositionTests(unittest.TestCase):
    def test_settings_and_composition_bind_exact_server_side_boundary(self) -> None:
        env = _env()
        settings = PerformanceLeaseBrokerSettings.from_env(env)
        self.assertEqual(settings.blob_path, BLOB_PATH)
        calls: list[str] = []

        def credential_factory():
            calls.append("system-assigned")
            return _Credential()

        broker = build_performance_lease_broker(
            env,
            credential_factory=credential_factory,
            opener=_Opener(),
        )
        self.assertIs(type(broker), AzurePerformanceLeaseBroker)
        self.assertEqual(calls, ["system-assigned"])
        self.assertEqual(PERFORMANCE_LEASE_APP_ROLE, "Performance.Lease")
        self.assertEqual(PERFORMANCE_LEASE_TICKET_SCOPE, "nac.performance.lease")

    def test_disabled_missing_and_noncanonical_values_fail_generically(self) -> None:
        cases = (
            {},
            {**_env(), "NAC_BFF_PERFORMANCE_LEASE_ENABLED": "false"},
            {**_env(), "NAC_BFF_PERFORMANCE_LEASE_BLOB_PATH": "other.lock"},
            {**_env(), "NAC_BFF_PERFORMANCE_LEASE_TICKET_CERTIFICATE_B64": "%%%"},
        )
        for env in cases:
            with self.subTest(keys=len(env)):
                with self.assertRaises(PerformanceLeaseBrokerCompositionError) as error:
                    build_performance_lease_broker(
                        env,
                        credential_factory=lambda **_: _Credential(),
                        opener=_Opener(),
                    )
                self.assertNotIn("CERTIFICATE", str(error.exception))
                self.assertNotIn("BLOB", str(error.exception))


if __name__ == "__main__":
    unittest.main()
