from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.azure_performance_lease import (  # noqa: E402
    AttestedAzureStorageAccessToken,
    AzureBlobLeaseBinding,
)
from nac_bff.azure_performance_storage_ports import (  # noqa: E402
    STORAGE_SCOPE,
    AttestedAzureStorageTokenProvider,
    AzurePerformanceStoragePortError,
    DurableLeaseBindingHandoff,
    PerformanceExecutionFence,
)


NOW = 1_775_212_200
TENANT_ID = "11111111-2222-3333-4444-555555555555"
CLIENT_ID = "22222222-3333-4444-5555-666666666666"
SUBJECT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
OWNER_BINDING = "1" * 64
TARGET_BINDING = "2" * 64
READ_BINDING = "3" * 64
WRITE_BINDING = "4" * 64
RESOURCE_ID = (
    "/subscriptions/33333333-4444-5555-6666-777777777777/"
    "resourceGroups/rg-nac/providers/Microsoft.Storage/storageAccounts/stcoord01"
)


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _integer_b64url(value: int) -> str:
    return _b64url(value.to_bytes((value.bit_length() + 7) // 8, "big"))


def _binding(**overrides: str) -> AzureBlobLeaseBinding:
    values = {
        "account_name": "stcoord01",
        "bff_account_name": "stbff01",
        "worm_account_name": "stworm01",
        "coordination_storage_account_resource_id": RESOURCE_ID,
        "owner_approval_body_sha256": OWNER_BINDING,
        "token_subject": SUBJECT_ID,
        "token_tenant_id": TENANT_ID,
        "target_binding_sha256": TARGET_BINDING,
        "expected_etag": '"0x8DABCDEF0123456"',
        "read_identity_binding_sha256": READ_BINDING,
        "write_identity_binding_sha256": WRITE_BINDING,
    }
    values.update(overrides)
    return AzureBlobLeaseBinding(**values)


def _certificate_and_key(
    private_key: rsa.RSAPrivateKey,
) -> tuple[bytes, bytes]:
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "offline-storage-test")])
    now = datetime.fromtimestamp(NOW, tz=timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )
    return (
        certificate.public_bytes(serialization.Encoding.PEM),
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )


def _jwk(private_key: rsa.RSAPrivateKey, kid: str = "signing-key") -> dict[str, str]:
    numbers = private_key.public_key().public_numbers()
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _integer_b64url(numbers.n),
        "e": _integer_b64url(numbers.e),
    }


def _access_token(
    private_key: rsa.RSAPrivateKey,
    *,
    claims: dict[str, object] | None = None,
    algorithm: str = "RS256",
    kid: str = "signing-key",
) -> str:
    payload = {
        "aud": "https://storage.azure.com",
        "iss": f"https://sts.windows.net/{TENANT_ID}/",
        "tid": TENANT_ID,
        "oid": SUBJECT_ID,
        "appid": CLIENT_ID,
        "ver": "1.0",
        "iat": NOW - 10,
        "nbf": NOW - 10,
        "exp": NOW + 300,
    }
    if claims is not None:
        payload.update(claims)
    header = _b64url(
        json.dumps(
            {"alg": algorithm, "kid": kid, "typ": "JWT"},
            separators=(",", ":"),
        ).encode("ascii")
    )
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode("ascii"))
    signing_input = f"{header}.{body}".encode("ascii")
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{header}.{body}.{_b64url(signature)}"


class DurableLeaseBindingHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "handoff" / "lease-binding.json"

    def _store(self, **overrides: str) -> DurableLeaseBindingHandoff:
        values = {
            "expected_owner_approval_body_sha256": OWNER_BINDING,
            "expected_target_binding_sha256": TARGET_BINDING,
            "expected_coordination_storage_account_resource_id": RESOURCE_ID,
        }
        values.update(overrides)
        return DurableLeaseBindingHandoff(self.path, **values)

    def test_commit_is_private_atomic_and_restart_safe(self) -> None:
        committed = self._store().commit_and_load(_binding())

        restarted = self._store()
        self.assertEqual(restarted.load(), committed)
        self.assertEqual(restarted.commit_and_load(_binding()), committed)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.with_name(self.path.name + ".lock").stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)
        self.assertFalse(any(self.path.parent.glob("*.tmp")))
    def test_exact_owner_target_resource_and_etag_are_immutable(self) -> None:
        self._store().commit_and_load(_binding())

        for store, binding in (
            (self._store(expected_owner_approval_body_sha256="9" * 64), _binding()),
            (self._store(expected_target_binding_sha256="9" * 64), _binding()),
            (
                self._store(
                    expected_coordination_storage_account_resource_id=RESOURCE_ID.lower()
                ),
                _binding(),
            ),
            (self._store(), _binding(expected_etag='"0x8D0000000000000"')),
        ):
            with self.subTest(store=store, etag=binding.expected_etag):
                with self.assertRaisesRegex(
                    AzurePerformanceStoragePortError,
                    r"^AZURE_PERFORMANCE_LEASE_HANDOFF_BINDING_MISMATCH$",
                ):
                    store.commit_and_load(binding)

    def test_symlink_and_non_private_regular_files_fail_closed(self) -> None:
        self.path.parent.mkdir(mode=0o700)
        target = self.root / "target.json"
        target.write_text("{}", encoding="ascii")
        target.chmod(0o600)
        self.path.symlink_to(target)
        with self.assertRaises(AzurePerformanceStoragePortError):
            self._store().commit_and_load(_binding())
        self.path.unlink()

        self.path.write_text("{}", encoding="ascii")
        self.path.chmod(0o644)
        with self.assertRaises(AzurePerformanceStoragePortError):
            self._store().load()

    def test_failed_atomic_commit_leaves_no_binding_or_temporary_file(self) -> None:
        with mock.patch(
            "nac_bff.azure_performance_storage_ports.os.link",
            side_effect=OSError("offline failure"),
        ):
            with self.assertRaisesRegex(
                AzurePerformanceStoragePortError,
                r"^AZURE_PERFORMANCE_LEASE_HANDOFF_WRITE_FAILED$",
            ):
                self._store().commit_and_load(_binding())

        self.assertFalse(self.path.exists())
        self.assertFalse(any(self.path.parent.glob("*.tmp")))


class PerformanceExecutionFenceTests(unittest.TestCase):
    def test_second_process_boundary_is_rejected_without_waiting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run" / "composition.lock"
            first = PerformanceExecutionFence(path)
            second = PerformanceExecutionFence(path)

            with first.hold():
                with self.assertRaisesRegex(
                    AzurePerformanceStoragePortError,
                    r"^AZURE_PERFORMANCE_EXECUTION_ALREADY_ACTIVE$",
                ):
                    with second.hold():
                        self.fail("second execution fence must stay closed")

            with second.hold():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)


class AttestedAzureStorageTokenProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.credential_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other_credential_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.token_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        certificate, private_key = _certificate_and_key(self.credential_key)
        self.certificate_path = self.root / "credential.cert.pem"
        self.private_key_path = self.root / "credential.key.pem"
        self.certificate_path.write_bytes(certificate)
        self.private_key_path.write_bytes(private_key)
        self.certificate_path.chmod(0o600)
        self.private_key_path.chmod(0o600)
        self.expected_certificate_sha256 = hashlib.sha256(certificate).hexdigest()
        self.http_calls: list[tuple[str, dict[str, str]]] = []
        self.jwks_calls: list[str] = []

    def _provider(
        self,
        *,
        token: str | None = None,
        certificate_path: Path | None = None,
        private_key_path: Path | None = None,
        expected_certificate_sha256: str | None = None,
        jwks: dict[str, object] | None = None,
    ) -> AttestedAzureStorageTokenProvider:
        selected_token = token or _access_token(self.token_key)

        def post(endpoint: str, form: dict[str, str]) -> dict[str, object]:
            self.http_calls.append((endpoint, dict(form)))
            return {
                "token_type": "Bearer",
                "access_token": selected_token,
                "expires_in": 300,
            }

        def fetch_jwks(url: str) -> dict[str, object]:
            self.jwks_calls.append(url)
            return jwks or {"keys": [_jwk(self.token_key)]}

        return AttestedAzureStorageTokenProvider(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            token_subject=SUBJECT_ID,
            certificate_path=certificate_path or self.certificate_path,
            private_key_path=private_key_path or self.private_key_path,
            expected_certificate_sha256=(
                expected_certificate_sha256 or self.expected_certificate_sha256
            ),
            http_post=post,
            jwks_fetcher=fetch_jwks,
            clock=lambda: float(NOW),
        )

    def test_get_token_uses_only_certificate_credentials_and_returns_sealed_attestation(self) -> None:
        result = self._provider().get_token(
            audience=STORAGE_SCOPE,
            identity_binding_sha256=READ_BINDING,
        )

        self.assertIs(type(result), AttestedAzureStorageAccessToken)
        self.assertEqual(result.scope, STORAGE_SCOPE)
        self.assertEqual(result.identity_binding_sha256, READ_BINDING)
        self.assertEqual(result.source_attestation_sha256, READ_BINDING)
        self.assertEqual(result.subject, SUBJECT_ID)
        self.assertEqual(result.tenant_id, TENANT_ID)
        self.assertEqual(len(self.http_calls), 1)
        endpoint, form = self.http_calls[0]
        self.assertEqual(
            endpoint,
            f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
        )
        self.assertEqual(form["scope"], STORAGE_SCOPE)
        self.assertEqual(form["grant_type"], "client_credentials")
        self.assertNotIn("client_secret", form)
        assertion_header = json.loads(
            base64.urlsafe_b64decode(form["client_assertion"].split(".")[0] + "==")
        )
        self.assertEqual(assertion_header["alg"], "RS256")
        self.assertEqual(
            self.jwks_calls,
            ["https://login.microsoftonline.com/common/discovery/v2.0/keys"],
        )

    def test_local_credential_preflight_is_redacted_and_network_free(self) -> None:
        result = self._provider().validate_local_credentials()

        self.assertEqual(result["status"], "READY")
        self.assertEqual(
            result["certificate_sha256"], self.expected_certificate_sha256
        )
        self.assertEqual(self.http_calls, [])
        self.assertEqual(self.jwks_calls, [])
        encoded = json.dumps(result, sort_keys=True)
        self.assertNotIn(str(self.private_key_path), encoded)
        self.assertNotIn("PRIVATE KEY", encoded)

    def test_scope_and_identity_binding_are_rejected_before_credentials_or_http(self) -> None:
        provider = self._provider()
        for audience, identity in (
            ("https://graph.microsoft.com/.default", READ_BINDING),
            (STORAGE_SCOPE + " ", READ_BINDING),
            (STORAGE_SCOPE, "not-a-digest"),
        ):
            with self.subTest(audience=audience, identity=identity):
                with self.assertRaisesRegex(
                    AzurePerformanceStoragePortError,
                    r"^AZURE_STORAGE_TOKEN_REQUEST_INVALID$",
                ):
                    provider.get_token(
                        audience=audience,
                        identity_binding_sha256=identity,
                    )
        self.assertEqual(self.http_calls, [])
        self.assertEqual(self.jwks_calls, [])

    def test_untrusted_or_mismatched_credentials_fail_before_http(self) -> None:
        original = self.root / "original.cert.pem"
        self.certificate_path.rename(original)
        self.certificate_path.symlink_to(original)
        with self.assertRaisesRegex(
            AzurePerformanceStoragePortError,
            r"^AZURE_STORAGE_CREDENTIAL_UNTRUSTED$",
        ):
            self._provider(certificate_path=self.certificate_path).get_token(
                audience=STORAGE_SCOPE,
                identity_binding_sha256=READ_BINDING,
            )
        self.certificate_path.unlink()
        original.rename(self.certificate_path)

        self.private_key_path.chmod(0o644)
        with self.assertRaises(AzurePerformanceStoragePortError):
            self._provider().get_token(
                audience=STORAGE_SCOPE,
                identity_binding_sha256=READ_BINDING,
            )
        self.private_key_path.chmod(0o600)

        _, other_key = _certificate_and_key(self.other_credential_key)
        self.private_key_path.write_bytes(other_key)
        self.private_key_path.chmod(0o600)
        with self.assertRaisesRegex(
            AzurePerformanceStoragePortError,
            r"^AZURE_STORAGE_CREDENTIAL_INVALID$",
        ):
            self._provider().get_token(
                audience=STORAGE_SCOPE,
                identity_binding_sha256=READ_BINDING,
            )
        self.assertEqual(self.http_calls, [])

    def test_rs256_signature_and_every_security_claim_fail_closed(self) -> None:
        cases = {
            "algorithm": _access_token(self.token_key, algorithm="RS512"),
            "wrong_signature": _access_token(self.other_credential_key),
            "audience": _access_token(self.token_key, claims={"aud": "https://example.invalid"}),
            "issuer": _access_token(self.token_key, claims={"iss": "https://example.invalid"}),
            "tenant": _access_token(self.token_key, claims={"tid": CLIENT_ID}),
            "subject": _access_token(self.token_key, claims={"oid": CLIENT_ID}),
            "client": _access_token(self.token_key, claims={"appid": SUBJECT_ID}),
            "expired": _access_token(self.token_key, claims={"exp": NOW}),
            "future": _access_token(self.token_key, claims={"nbf": NOW + 1}),
        }
        for label, token in cases.items():
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    AzurePerformanceStoragePortError,
                    r"^AZURE_STORAGE_TOKEN_INVALID$",
                ) as caught:
                    self._provider(token=token).get_token(
                        audience=STORAGE_SCOPE,
                        identity_binding_sha256=READ_BINDING,
                    )
                self.assertNotIn(token, str(caught.exception))

    def test_jwks_key_must_be_unique_rs256_signing_key(self) -> None:
        duplicate = _jwk(self.token_key)
        invalid_sets = (
            {"keys": []},
            {"keys": [duplicate, dict(duplicate)]},
            {"keys": [{**duplicate, "kty": "EC"}]},
            {"keys": [{**duplicate, "use": "enc"}]},
            {"keys": [{**duplicate, "alg": "RS512"}]},
        )
        for jwks in invalid_sets:
            with self.subTest(jwks=jwks):
                with self.assertRaisesRegex(
                    AzurePerformanceStoragePortError,
                    r"^AZURE_STORAGE_TOKEN_INVALID$",
                ):
                    self._provider(jwks=jwks).get_token(
                        audience=STORAGE_SCOPE,
                        identity_binding_sha256=READ_BINDING,
                    )


if __name__ == "__main__":
    unittest.main()
