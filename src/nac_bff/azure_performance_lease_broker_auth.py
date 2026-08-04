from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import stat
import time
from typing import Any, Callable, Mapping
from uuid import UUID

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .azure_performance_lease_broker import (
    MAX_TICKET_LIFETIME_SECONDS,
    TICKET_VERSION,
    ActivationTicketPayload,
)


BFF_API_AUDIENCE = "api://funktion8.de/nac-bff"
BFF_APP_TOKEN_SCOPE = f"{BFF_API_AUDIENCE}/.default"
PERFORMANCE_LEASE_APP_ROLE = "Performance.Lease"
PERFORMANCE_LEASE_TICKET_SCOPE = "nac.performance.lease"

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
_KEY_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_MAX_CREDENTIAL_BYTES = 1024 * 1024


class PerformanceLeaseBrokerAuthError(RuntimeError):
    """Stable failure that never includes credentials, tokens or ticket data."""


class CertificateBffAppTokenProvider:
    """Acquire an app-only token for the fixed BFF API, never Azure Storage."""

    def __init__(
        self,
        *,
        tenant_id: str,
        client_id: str,
        service_principal_id: str,
        certificate_path: Path,
        private_key_path: Path,
        expected_certificate_sha256: str,
        credential_factory: Callable[..., Any] | None = None,
    ) -> None:
        try:
            UUID(tenant_id)
            UUID(client_id)
            UUID(service_principal_id)
        except (TypeError, ValueError):
            raise ValueError("BFF_APP_TOKEN_CONFIGURATION_INVALID") from None
        if (
            not isinstance(certificate_path, Path)
            or not isinstance(private_key_path, Path)
            or _SHA256_RE.fullmatch(expected_certificate_sha256) is None
        ):
            raise ValueError("BFF_APP_TOKEN_CONFIGURATION_INVALID")
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._service_principal_id = service_principal_id
        self._certificate_path = certificate_path
        self._private_key_path = private_key_path
        self._expected_certificate_sha256 = expected_certificate_sha256
        self._credential_factory = credential_factory

    @property
    def service_principal_id(self) -> str:
        return self._service_principal_id

    def validate_local_credentials(self) -> dict[str, str]:
        certificate_bytes, _, certificate, private_key = self._credential_pair()
        return {
            "status": "READY",
            "audience_sha256": _sha256_text(BFF_API_AUDIENCE),
            "scope_sha256": _sha256_text(BFF_APP_TOKEN_SCOPE),
            "certificate_sha256": hashlib.sha256(certificate_bytes).hexdigest(),
            "credential_pair_sha256": _credential_pair_sha256(
                certificate, private_key
            ),
            "service_principal_sha256": _sha256_text(
                self._service_principal_id
            ),
        }

    def __call__(self) -> str:
        certificate_bytes, private_key_bytes, _, _ = self._credential_pair()
        factory = self._credential_factory
        if factory is None:
            try:
                from azure.identity import CertificateCredential
            except ImportError:
                raise PerformanceLeaseBrokerAuthError(
                    "BFF_APP_TOKEN_RUNTIME_UNAVAILABLE"
                ) from None
            factory = CertificateCredential
        try:
            credential = factory(
                tenant_id=self._tenant_id,
                client_id=self._client_id,
                certificate_data=certificate_bytes + b"\n" + private_key_bytes,
                send_certificate_chain=False,
            )
            token = credential.get_token(BFF_APP_TOKEN_SCOPE).token
        except Exception:
            raise PerformanceLeaseBrokerAuthError(
                "BFF_APP_TOKEN_UNAVAILABLE"
            ) from None
        if (
            type(token) is not str
            or not 32 <= len(token) <= 16 * 1024
            or token != token.strip()
            or any(character in token for character in "\r\n\x00")
        ):
            raise PerformanceLeaseBrokerAuthError("BFF_APP_TOKEN_INVALID")
        return token

    def _credential_pair(
        self,
    ) -> tuple[bytes, bytes, x509.Certificate, rsa.RSAPrivateKey]:
        certificate_bytes = _read_credential(self._certificate_path, private=False)
        if not secrets.compare_digest(
            hashlib.sha256(certificate_bytes).hexdigest(),
            self._expected_certificate_sha256,
        ):
            raise PerformanceLeaseBrokerAuthError("BFF_APP_CREDENTIAL_INVALID")
        private_key_bytes = _read_credential(self._private_key_path, private=True)
        certificate, private_key = _load_pair(
            certificate_bytes, private_key_bytes
        )
        return certificate_bytes, private_key_bytes, certificate, private_key


class RsaActivationTicketSigner:
    """Issue one-operation, short-lived tickets bound to the approved run."""

    def __init__(
        self,
        *,
        key_id: str,
        certificate_path: Path,
        private_key_path: Path,
        expected_certificate_sha256: str,
        issuer: str,
        tenant_id: str,
        actor_id: str,
        owner_binding_sha256: str,
        commit_sha: str,
        tree_sha: str,
        function_package_sha256: str,
        plan_sha256: str,
        target_binding_sha256: str,
        storage_binding: str,
        clock: Callable[[], float] = time.time,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        try:
            UUID(tenant_id)
            UUID(actor_id)
        except (TypeError, ValueError):
            raise ValueError("LEASE_TICKET_SIGNER_CONFIGURATION_INVALID") from None
        digests = (
            owner_binding_sha256,
            tree_sha,
            function_package_sha256,
            plan_sha256,
            target_binding_sha256,
        )
        if (
            _KEY_ID_RE.fullmatch(key_id) is None
            or not issuer
            or any(_SHA256_RE.fullmatch(value) is None for value in digests)
            or _GIT_SHA_RE.fullmatch(commit_sha) is None
            or not storage_binding
            or not callable(clock)
        ):
            raise ValueError("LEASE_TICKET_SIGNER_CONFIGURATION_INVALID")
        self._key_id = key_id
        self._certificate_path = certificate_path
        self._private_key_path = private_key_path
        self._expected_certificate_sha256 = expected_certificate_sha256
        self._issuer = issuer
        self._tenant_id = tenant_id
        self._actor_id = actor_id
        self._owner_binding_sha256 = owner_binding_sha256
        self._commit_sha = commit_sha
        self._tree_sha = tree_sha
        self._function_package_sha256 = function_package_sha256
        self._plan_sha256 = plan_sha256
        self._target_binding_sha256 = target_binding_sha256
        self._storage_binding = storage_binding
        self._clock = clock
        self._nonce_factory = nonce_factory or (
            lambda: _base64url(secrets.token_bytes(32))
        )

    def __call__(self, operation: str) -> dict[str, Any]:
        if operation not in {"acquire", "assert", "release"}:
            raise PerformanceLeaseBrokerAuthError("LEASE_TICKET_OPERATION_INVALID")
        now = int(self._clock())
        payload = ActivationTicketPayload(
            version=TICKET_VERSION,
            issuer=self._issuer,
            tenant_id=self._tenant_id,
            audience=BFF_API_AUDIENCE,
            actor_id=self._actor_id,
            owner_subject=self._actor_id,
            owner_binding_sha256=self._owner_binding_sha256,
            commit_sha=self._commit_sha,
            tree_sha=self._tree_sha,
            function_package_sha256=self._function_package_sha256,
            plan_sha256=self._plan_sha256,
            target_binding_sha256=self._target_binding_sha256,
            blob_path=f"locks/{self._target_binding_sha256}.lock",
            actions=(operation,),
            role=PERFORMANCE_LEASE_APP_ROLE,
            scope=PERFORMANCE_LEASE_TICKET_SCOPE,
            storage_binding=self._storage_binding,
            issued_at=now,
            expires_at=now + MAX_TICKET_LIFETIME_SECONDS,
            nonce=self._nonce_factory(),
        )
        _, _, _, private_key = self._credential_pair()
        try:
            signature = private_key.sign(
                payload.canonical_bytes(), padding.PKCS1v15(), hashes.SHA256()
            )
        except Exception:
            raise PerformanceLeaseBrokerAuthError(
                "LEASE_TICKET_SIGNING_FAILED"
            ) from None
        return {
            "key_id": self._key_id,
            "payload": json.loads(payload.canonical_bytes()),
            "signature": _base64url(signature),
        }

    def _credential_pair(
        self,
    ) -> tuple[bytes, bytes, x509.Certificate, rsa.RSAPrivateKey]:
        certificate_bytes = _read_credential(
            self._certificate_path, private=False
        )
        if not secrets.compare_digest(
            hashlib.sha256(certificate_bytes).hexdigest(),
            self._expected_certificate_sha256,
        ):
            raise PerformanceLeaseBrokerAuthError(
                "BFF_APP_CREDENTIAL_INVALID"
            )
        private_key_bytes = _read_credential(
            self._private_key_path, private=True
        )
        certificate, private_key = _load_pair(
            certificate_bytes, private_key_bytes
        )
        return certificate_bytes, private_key_bytes, certificate, private_key


def broker_storage_attestation(
    *,
    owner_binding_sha256: str,
    target_binding_sha256: str,
    coordination_storage_account_resource_id: str,
    broker_principal_id: str,
    broker_function_package_sha256: str,
    broker_ticket_certificate_sha256: str,
) -> bytes:
    payload = {
        "broker_function_package_sha256": broker_function_package_sha256,
        "broker_principal_id": str(UUID(broker_principal_id)),
        "broker_ticket_certificate_sha256": broker_ticket_certificate_sha256,
        "coordination_storage_account_resource_id": (
            coordination_storage_account_resource_id
        ),
        "owner_binding_sha256": owner_binding_sha256,
        "target_binding_sha256": target_binding_sha256,
    }
    if any(
        _SHA256_RE.fullmatch(payload[key]) is None
        for key in (
            "broker_function_package_sha256",
            "broker_ticket_certificate_sha256",
            "owner_binding_sha256",
            "target_binding_sha256",
        )
    ):
        raise ValueError("BROKER_STORAGE_ATTESTATION_INVALID")
    return _canonical_json(payload)


def broker_binding_fingerprint(binding_id: str, attestation: bytes) -> str:
    return hashlib.sha256(
        _canonical_json(
            {
                "attestation": _base64url(attestation),
                "binding_id": binding_id,
            }
        )
    ).hexdigest()


def _read_credential(path: Path, *, private: bool) -> bytes:
    try:
        metadata = path.stat(follow_symlinks=False)
        mode = stat.S_IMODE(metadata.st_mode)
        if (
            path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or not 1 <= metadata.st_size <= _MAX_CREDENTIAL_BYTES
            or (private and mode & 0o077)
            or (not private and mode & 0o022)
        ):
            raise OSError
        value = path.read_bytes()
        after = path.stat(follow_symlinks=False)
        if (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mtime_ns,
        ) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise OSError
        return value
    except OSError:
        raise PerformanceLeaseBrokerAuthError("BFF_APP_CREDENTIAL_INVALID") from None


def _load_pair(
    certificate_bytes: bytes, private_key_bytes: bytes
) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    try:
        certificate = (
            x509.load_pem_x509_certificate(certificate_bytes)
            if certificate_bytes.startswith(b"-----BEGIN CERTIFICATE-----")
            else x509.load_der_x509_certificate(certificate_bytes)
        )
        private_key = serialization.load_pem_private_key(
            private_key_bytes, password=None
        )
        public_key = certificate.public_key()
        now = datetime.now(timezone.utc)
        not_before = getattr(certificate, "not_valid_before_utc", None)
        not_after = getattr(certificate, "not_valid_after_utc", None)
        if not_before is None:
            not_before = certificate.not_valid_before.replace(tzinfo=timezone.utc)
        if not_after is None:
            not_after = certificate.not_valid_after.replace(tzinfo=timezone.utc)
        if (
            not isinstance(private_key, rsa.RSAPrivateKey)
            or not isinstance(public_key, rsa.RSAPublicKey)
            or not 2048 <= private_key.key_size <= 4096
            or private_key.public_key().public_numbers()
            != public_key.public_numbers()
            or not_before > now
            or now >= not_after
        ):
            raise ValueError
        return certificate, private_key
    except Exception:
        raise PerformanceLeaseBrokerAuthError("BFF_APP_CREDENTIAL_INVALID") from None


def _credential_pair_sha256(
    certificate: x509.Certificate, private_key: rsa.RSAPrivateKey
) -> str:
    numbers = private_key.public_key().public_numbers()
    return hashlib.sha256(
        certificate.fingerprint(hashes.SHA256())
        + numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
        + numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
    ).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "BFF_API_AUDIENCE",
    "BFF_APP_TOKEN_SCOPE",
    "PERFORMANCE_LEASE_APP_ROLE",
    "PERFORMANCE_LEASE_TICKET_SCOPE",
    "CertificateBffAppTokenProvider",
    "PerformanceLeaseBrokerAuthError",
    "RsaActivationTicketSigner",
    "broker_binding_fingerprint",
    "broker_storage_attestation",
]
