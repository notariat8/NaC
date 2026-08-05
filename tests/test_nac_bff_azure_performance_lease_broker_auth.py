from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from nac_bff.azure_performance_lease_broker import (
    RsaCertificateTicketSignatureVerifier,
    SignedActivationTicket,
)
from nac_bff.azure_performance_lease_broker_auth import (
    BFF_API_AUDIENCE,
    BFF_APP_TOKEN_SCOPE,
    CertificateBffAppTokenProvider,
    PerformanceLeaseBrokerAuthError,
    RsaActivationTicketSigner,
    broker_binding_fingerprint,
    broker_storage_attestation,
)


TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
CLIENT_ID = "11111111-2222-4333-8444-555555555555"
TARGET = "1" * 64
OWNER = "2" * 64
TREE = "3" * 64
PACKAGE = "4" * 64
PLAN = "5" * 64
COMMIT = "6" * 40


class _Token:
    token = "x" * 64


class _Credential:
    def __init__(self) -> None:
        self.scopes: list[str] = []

    def get_token(self, scope: str) -> _Token:
        self.scopes.append(scope)
        return _Token()


class PerformanceLeaseBrokerAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "NaC test")])
        now = datetime.now(timezone.utc)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=1))
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
        )
        self.key = key
        self.cert_bytes = certificate.public_bytes(serialization.Encoding.PEM)
        self.key_bytes = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        self.cert = root / "broker.crt"
        self.private_key = root / "broker.key"
        self.cert.write_bytes(self.cert_bytes)
        self.private_key.write_bytes(self.key_bytes)
        self.cert.chmod(0o644)
        self.private_key.chmod(0o600)
        self.cert_sha = hashlib.sha256(self.cert_bytes).hexdigest()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _provider(self, credential: _Credential) -> CertificateBffAppTokenProvider:
        factory = Mock(return_value=credential)
        provider = CertificateBffAppTokenProvider(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            service_principal_id=CLIENT_ID,
            certificate_path=self.cert,
            private_key_path=self.private_key,
            expected_certificate_sha256=self.cert_sha,
            credential_factory=factory,
        )
        provider._test_factory = factory  # type: ignore[attr-defined]
        return provider

    def test_token_provider_requests_only_fixed_bff_scope(self) -> None:
        credential = _Credential()
        provider = self._provider(credential)
        self.assertEqual(provider(), "x" * 64)
        self.assertEqual(credential.scopes, [BFF_APP_TOKEN_SCOPE])
        self.assertEqual(BFF_API_AUDIENCE, "api://funktion8.de/nac-bff")
        self.assertNotIn("storage.azure.com", BFF_APP_TOKEN_SCOPE)
        kwargs = provider._test_factory.call_args.kwargs  # type: ignore[attr-defined]
        self.assertEqual(kwargs["tenant_id"], TENANT_ID)
        self.assertEqual(kwargs["client_id"], CLIENT_ID)
        self.assertNotIn("scope", kwargs)

    def test_local_credential_validation_is_redacted(self) -> None:
        result = self._provider(_Credential()).validate_local_credentials()
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["certificate_sha256"], self.cert_sha)
        self.assertNotIn(str(self.private_key), json.dumps(result))
        self.assertNotIn(CLIENT_ID, json.dumps(result))

    def test_private_key_must_not_be_group_or_world_readable(self) -> None:
        self.private_key.chmod(0o644)
        with self.assertRaisesRegex(
            PerformanceLeaseBrokerAuthError, "BFF_APP_CREDENTIAL_INVALID"
        ):
            self._provider(_Credential()).validate_local_credentials()

    def test_ticket_is_single_operation_short_lived_and_verifiable(self) -> None:
        signer = RsaActivationTicketSigner(
            key_id="test-key",
            certificate_path=self.cert,
            private_key_path=self.private_key,
            expected_certificate_sha256=self.cert_sha,
            issuer="nac-performance-owner-gate",
            tenant_id=TENANT_ID,
            actor_id=CLIENT_ID,
            owner_binding_sha256=OWNER,
            commit_sha=COMMIT,
            tree_sha=TREE,
            function_package_sha256=PACKAGE,
            plan_sha256=PLAN,
            target_binding_sha256=TARGET,
            storage_binding="coordination-v1",
            clock=lambda: 1000.0,
            nonce_factory=lambda: "nonce-1234567890",
        )
        ticket = signer("assert")
        parsed = SignedActivationTicket.from_mapping(ticket)
        self.assertEqual(parsed.payload.actions, ("assert",))
        self.assertEqual(parsed.payload.expires_at - parsed.payload.issued_at, 60)
        self.assertEqual(parsed.payload.audience, BFF_API_AUDIENCE)
        self.assertEqual(parsed.payload.blob_path, f"locks/{TARGET}.lock")
        verifier = RsaCertificateTicketSignatureVerifier(
            key_id="test-key",
            certificate_bytes=self.cert_bytes,
            certificate_sha256=self.cert_sha,
        )
        signature = base64.urlsafe_b64decode(
            ticket["signature"] + "=" * (-len(ticket["signature"]) % 4)
        )
        self.assertTrue(
            verifier.verify(
                key_id="test-key",
                payload=parsed.payload.canonical_bytes(),
                signature=signature,
            )
        )

    def test_ticket_tampering_breaks_signature(self) -> None:
        signer = RsaActivationTicketSigner(
            key_id="test-key",
            certificate_path=self.cert,
            private_key_path=self.private_key,
            expected_certificate_sha256=self.cert_sha,
            issuer="nac-performance-owner-gate",
            tenant_id=TENANT_ID,
            actor_id=CLIENT_ID,
            owner_binding_sha256=OWNER,
            commit_sha=COMMIT,
            tree_sha=TREE,
            function_package_sha256=PACKAGE,
            plan_sha256=PLAN,
            target_binding_sha256=TARGET,
            storage_binding="coordination-v1",
            clock=lambda: 1000.0,
        )
        ticket = signer("acquire")
        ticket["payload"]["actions"] = ["release"]
        parsed = SignedActivationTicket.from_mapping(ticket)
        signature = base64.urlsafe_b64decode(
            ticket["signature"] + "=" * (-len(ticket["signature"]) % 4)
        )
        with self.assertRaises(Exception):
            self.key.public_key().verify(
                signature,
                parsed.payload.canonical_bytes(),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )

    def test_storage_attestation_and_fingerprint_are_deterministic(self) -> None:
        arguments = {
            "owner_binding_sha256": OWNER,
            "target_binding_sha256": TARGET,
            "coordination_storage_account_resource_id": (
                "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
                "resourceGroups/rg-nac-bff-test/providers/Microsoft.Storage/"
                "storageAccounts/stnacperflease001"
            ),
            "broker_principal_id": CLIENT_ID,
            "broker_function_package_sha256": PACKAGE,
            "broker_ticket_certificate_sha256": self.cert_sha,
        }
        first = broker_storage_attestation(**arguments)
        second = broker_storage_attestation(**arguments)
        self.assertEqual(first, second)
        self.assertEqual(
            broker_binding_fingerprint("coordination-v1", first),
            broker_binding_fingerprint("coordination-v1", second),
        )
        self.assertNotIn(b"token", first.lower())
        self.assertNotIn(b"private", first.lower())


if __name__ == "__main__":
    unittest.main()
