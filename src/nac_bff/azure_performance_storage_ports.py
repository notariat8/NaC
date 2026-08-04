from __future__ import annotations

import base64
import binascii
import fcntl
import hashlib
import json
import math
import os
import re
import secrets
import stat
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping
from uuid import UUID, uuid4

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .azure_performance_authorization import (
    SecurePerformancePathError,
    _open_root_anchored_private_parent,
)
from .azure_performance_lease import (
    AttestedAzureStorageAccessToken,
    AzureBlobLeaseBinding,
    _issue_attested_azure_storage_access_token as _lease_token_issuer,
)


__all__ = (
    "STORAGE_SCOPE",
    "AttestedAzureStorageTokenProvider",
    "AzurePerformanceStoragePortError",
    "DurableLeaseBindingHandoff",
    "PerformanceExecutionFence",
)


STORAGE_SCOPE = "https://storage.azure.com/.default"
_STORAGE_AUDIENCE = "https://storage.azure.com"
_JWKS_URI = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
_HANDOFF_SCHEMA = "nac.azure-performance-lease-binding-handoff/v1"
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_BASE64URL_RE = re.compile(r"[A-Za-z0-9_-]+\Z")
_BINDING_FIELDS = (
    "account_name",
    "bff_account_name",
    "worm_account_name",
    "coordination_storage_account_resource_id",
    "owner_approval_body_sha256",
    "token_subject",
    "token_tenant_id",
    "target_binding_sha256",
    "expected_etag",
    "read_identity_binding_sha256",
    "write_identity_binding_sha256",
)
_MAX_HANDOFF_BYTES = 16 * 1024
_MAX_CREDENTIAL_BYTES = 1024 * 1024
_MAX_TOKEN_BYTES = 16 * 1024
_MAX_JSON_SEGMENT_BYTES = 16 * 1024
_MAX_RESPONSE_BYTES = 256 * 1024
_MAX_JWKS_KEYS = 100
_MIN_RSA_BITS = 2048
_MAX_RSA_BITS = 8192
_MAX_TOKEN_LIFETIME_SECONDS = 2 * 60 * 60
_ASSERTION_LIFETIME_SECONDS = 10 * 60
_CLOCK_SKEW_SECONDS = 60
_HTTP_TIMEOUT_SECONDS = 30.0

HttpPost = Callable[[str, dict[str, str]], Mapping[str, Any]]
JwksFetcher = Callable[[str], Mapping[str, Any]]
Clock = Callable[[], float]


class AzurePerformanceStoragePortError(RuntimeError):
    """Stable, redacted failure at a production storage-port boundary."""


class _Rejected(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class PerformanceExecutionFence:
    """Reject a second process before any owner or provider interaction."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path) or path.name in {"", ".", ".."}:
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_EXECUTION_FENCE_CONFIGURATION_INVALID"
            )
        self._path = Path(os.path.abspath(path.expanduser()))

    @contextmanager
    def hold(self) -> Iterator[None]:
        try:
            parent_fd = _open_root_anchored_private_parent(
                self._path, create=True
            )
        except SecurePerformancePathError:
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_EXECUTION_FENCE_PATH_UNTRUSTED"
            ) from None
        if parent_fd is None:
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_EXECUTION_FENCE_PATH_UNTRUSTED"
            )
        lock_fd: int | None = None
        try:
            lock_fd = _open_private_file_at(
                parent_fd, self._path.name, create=True
            )
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise AzurePerformanceStoragePortError(
                    "AZURE_PERFORMANCE_EXECUTION_ALREADY_ACTIVE"
                ) from None
            yield
        except AzurePerformanceStoragePortError:
            raise
        except OSError:
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_EXECUTION_FENCE_PATH_UNTRUSTED"
            ) from None
        finally:
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                finally:
                    os.close(lock_fd)
            os.close(parent_fd)


class DurableLeaseBindingHandoff:
    """Persist one exact post-bootstrap lease binding across process restarts."""

    def __init__(
        self,
        path: Path,
        *,
        expected_owner_approval_body_sha256: str,
        expected_target_binding_sha256: str,
        expected_coordination_storage_account_resource_id: str,
    ) -> None:
        if (
            not isinstance(path, Path)
            or path.name in {"", ".", ".."}
            or not _is_sha256(expected_owner_approval_body_sha256)
            or not _is_sha256(expected_target_binding_sha256)
            or not isinstance(expected_coordination_storage_account_resource_id, str)
            or not expected_coordination_storage_account_resource_id
            or expected_coordination_storage_account_resource_id.strip()
            != expected_coordination_storage_account_resource_id
            or len(expected_coordination_storage_account_resource_id) > 2048
        ):
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_LEASE_HANDOFF_CONFIGURATION_INVALID"
            )
        self._path = Path(os.path.abspath(path.expanduser()))
        self._expected_owner = expected_owner_approval_body_sha256
        self._expected_target = expected_target_binding_sha256
        self._expected_resource = expected_coordination_storage_account_resource_id

    @property
    def path(self) -> Path:
        return self._path

    def commit_and_load(
        self, binding: AzureBlobLeaseBinding
    ) -> AzureBlobLeaseBinding:
        self._validate_expected_binding(binding)
        with self._locked_parent(create=True) as parent_fd:
            persisted = self._read_binding(parent_fd)
            if persisted is None:
                self._atomic_commit(parent_fd, self._record(binding))
                persisted = self._read_binding(parent_fd)
            if persisted != binding:
                raise AzurePerformanceStoragePortError(
                    "AZURE_PERFORMANCE_LEASE_HANDOFF_BINDING_MISMATCH"
                )
            self._validate_expected_binding(persisted)
            return persisted

    def load(self) -> AzureBlobLeaseBinding:
        with self._locked_parent(create=False) as parent_fd:
            binding = self._read_binding(parent_fd)
            if binding is None:
                raise AzurePerformanceStoragePortError(
                    "AZURE_PERFORMANCE_LEASE_HANDOFF_MISSING"
                )
            self._validate_expected_binding(binding)
            return binding

    def _validate_expected_binding(self, binding: object) -> None:
        if (
            type(binding) is not AzureBlobLeaseBinding
            or binding.owner_approval_body_sha256 != self._expected_owner
            or binding.target_binding_sha256 != self._expected_target
            or binding.coordination_storage_account_resource_id
            != self._expected_resource
        ):
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_LEASE_HANDOFF_BINDING_MISMATCH"
            )

    @contextmanager
    def _locked_parent(self, *, create: bool) -> Iterator[int]:
        try:
            parent_fd = _open_root_anchored_private_parent(
                self._path, create=create
            )
        except SecurePerformancePathError:
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_LEASE_HANDOFF_PATH_UNTRUSTED"
            ) from None
        if parent_fd is None:
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_LEASE_HANDOFF_MISSING"
            )
        lock_fd: int | None = None
        try:
            lock_fd = _open_private_file_at(
                parent_fd, self._path.name + ".lock", create=True
            )
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            yield parent_fd
        except AzurePerformanceStoragePortError:
            raise
        except OSError:
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_LEASE_HANDOFF_PATH_UNTRUSTED"
            ) from None
        finally:
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                finally:
                    os.close(lock_fd)
            os.close(parent_fd)

    def _read_binding(self, parent_fd: int) -> AzureBlobLeaseBinding | None:
        try:
            metadata = os.stat(
                self._path.name, dir_fd=parent_fd, follow_symlinks=False
            )
        except FileNotFoundError:
            return None
        except OSError:
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_LEASE_HANDOFF_INVALID"
            ) from None
        if not _private_regular_file(metadata):
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_LEASE_HANDOFF_INVALID"
            )
        descriptor = _open_private_file_at(
            parent_fd, self._path.name, create=False
        )
        try:
            raw = _read_stable_fd(descriptor, _MAX_HANDOFF_BYTES)
        except OSError:
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_LEASE_HANDOFF_INVALID"
            ) from None
        finally:
            os.close(descriptor)
        try:
            record = json.loads(
                raw.decode("ascii"), object_pairs_hook=_unique_json_object
            )
            if (
                not isinstance(record, dict)
                or set(record) != {"schema_version", "binding", "binding_sha256"}
                or record["schema_version"] != _HANDOFF_SCHEMA
                or not isinstance(record["binding"], dict)
                or set(record["binding"]) != set(_BINDING_FIELDS)
                or record["binding_sha256"]
                != _sha256_json(record["binding"])
            ):
                raise _Rejected
            return AzureBlobLeaseBinding(**record["binding"])
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
            _Rejected,
        ):
            raise AzurePerformanceStoragePortError(
                "AZURE_PERFORMANCE_LEASE_HANDOFF_INVALID"
            ) from None

    def _record(self, binding: AzureBlobLeaseBinding) -> dict[str, Any]:
        payload = {field: getattr(binding, field) for field in _BINDING_FIELDS}
        return {
            "schema_version": _HANDOFF_SCHEMA,
            "binding": payload,
            "binding_sha256": _sha256_json(payload),
        }

    def _atomic_commit(self, parent_fd: int, record: Mapping[str, Any]) -> None:
        raw = _canonical_json(record).encode("ascii")
        temporary = f".{self._path.name}.{secrets.token_hex(16)}.tmp"
        descriptor: int | None = None
        linked = False
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=parent_fd,
            )
            _write_all(descriptor, raw)
            os.fsync(descriptor)
            metadata = os.fstat(descriptor)
            if not _private_regular_file(metadata):
                raise OSError
            os.close(descriptor)
            descriptor = None
            os.link(
                temporary,
                self._path.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
            linked = True
            os.unlink(temporary, dir_fd=parent_fd)
            os.fsync(parent_fd)
            metadata = os.stat(
                self._path.name, dir_fd=parent_fd, follow_symlinks=False
            )
            if not _private_regular_file(metadata):
                raise OSError
        except (OSError, TypeError, ValueError):
            code = (
                "AZURE_PERFORMANCE_LEASE_HANDOFF_BINDING_MISMATCH"
                if linked
                else "AZURE_PERFORMANCE_LEASE_HANDOFF_WRITE_FAILED"
            )
            raise AzurePerformanceStoragePortError(code) from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            except OSError:
                pass


class AttestedAzureStorageTokenProvider:
    """Acquire and attest one certificate-backed Azure Storage access token."""

    def __init__(
        self,
        *,
        tenant_id: str,
        client_id: str,
        token_subject: str,
        certificate_path: Path,
        private_key_path: Path,
        expected_certificate_sha256: str,
        private_key_password: str | bytes | None = None,
        http_post: HttpPost | None = None,
        jwks_fetcher: JwksFetcher | None = None,
        clock: Clock | None = None,
    ) -> None:
        if (
            _canonical_uuid(tenant_id) is None
            or _canonical_uuid(client_id) is None
            or _canonical_uuid(token_subject) is None
            or not isinstance(certificate_path, Path)
            or not isinstance(private_key_path, Path)
            or not _is_sha256(expected_certificate_sha256)
            or http_post is not None
            and not callable(http_post)
            or jwks_fetcher is not None
            and not callable(jwks_fetcher)
            or clock is not None
            and not callable(clock)
        ):
            raise AzurePerformanceStoragePortError(
                "AZURE_STORAGE_TOKEN_CONFIGURATION_INVALID"
            )
        if isinstance(private_key_password, str):
            password = private_key_password.encode("utf-8")
        elif isinstance(private_key_password, bytes) or private_key_password is None:
            password = private_key_password
        else:
            raise AzurePerformanceStoragePortError(
                "AZURE_STORAGE_TOKEN_CONFIGURATION_INVALID"
            )
        if password is not None and not 1 <= len(password) <= 4096:
            raise AzurePerformanceStoragePortError(
                "AZURE_STORAGE_TOKEN_CONFIGURATION_INVALID"
            )
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._token_subject = token_subject
        self._certificate_path = certificate_path
        self._private_key_path = private_key_path
        self._expected_certificate_sha256 = expected_certificate_sha256
        self._private_key_password = password
        self._http_post = http_post or _post_token_form
        self._jwks_fetcher = jwks_fetcher or _fetch_jwks
        self._clock = clock or _system_clock
        self._token_endpoint = (
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        )

    def __call__(
        self, *, audience: str, identity_binding_sha256: str
    ) -> AttestedAzureStorageAccessToken:
        return self.get_token(
            audience=audience,
            identity_binding_sha256=identity_binding_sha256,
        )

    def get_token(
        self, *, audience: str, identity_binding_sha256: str
    ) -> AttestedAzureStorageAccessToken:
        if audience != STORAGE_SCOPE or not _is_sha256(identity_binding_sha256):
            raise AzurePerformanceStoragePortError(
                "AZURE_STORAGE_TOKEN_REQUEST_INVALID"
            )
        try:
            return self._get_token(identity_binding_sha256)
        except AzurePerformanceStoragePortError:
            raise
        except Exception:
            raise AzurePerformanceStoragePortError(
                "AZURE_STORAGE_TOKEN_UNAVAILABLE"
            ) from None

    def validate_local_credentials(self) -> dict[str, str]:
        """Validate the exact certificate/key pair without network access."""

        now = _clock_value(self._clock)
        certificate_bytes = _read_trusted_credential(
            self._certificate_path,
            expected_sha256=self._expected_certificate_sha256,
        )
        private_key_bytes = _read_trusted_credential(self._private_key_path)
        certificate, private_key = _load_credential_pair(
            certificate_bytes,
            private_key_bytes,
            password=self._private_key_password,
            now=now,
        )
        public_numbers = private_key.public_key().public_numbers()
        certificate_numbers = certificate.public_key().public_numbers()
        if public_numbers != certificate_numbers:
            raise AzurePerformanceStoragePortError(
                "AZURE_STORAGE_CREDENTIAL_INVALID"
            )
        return {
            "status": "READY",
            "tenant_id_sha256": hashlib.sha256(
                self._tenant_id.encode("ascii")
            ).hexdigest(),
            "client_id_sha256": hashlib.sha256(
                self._client_id.encode("ascii")
            ).hexdigest(),
            "token_subject_sha256": hashlib.sha256(
                self._token_subject.encode("ascii")
            ).hexdigest(),
            "certificate_sha256": hashlib.sha256(
                certificate_bytes
            ).hexdigest(),
            "credential_pair_sha256": hashlib.sha256(
                certificate.fingerprint(hashes.SHA256())
                + public_numbers.n.to_bytes(
                    (public_numbers.n.bit_length() + 7) // 8, "big"
                )
                + public_numbers.e.to_bytes(
                    (public_numbers.e.bit_length() + 7) // 8, "big"
                )
            ).hexdigest(),
        }

    def _get_token(
        self, identity_binding_sha256: str
    ) -> AttestedAzureStorageAccessToken:
        now = _clock_value(self._clock)
        certificate_bytes = _read_trusted_credential(
            self._certificate_path,
            expected_sha256=self._expected_certificate_sha256,
        )
        private_key_bytes = _read_trusted_credential(self._private_key_path)
        certificate, private_key = _load_credential_pair(
            certificate_bytes,
            private_key_bytes,
            password=self._private_key_password,
            now=now,
        )
        assertion = _build_client_assertion(
            certificate=certificate,
            private_key=private_key,
            client_id=self._client_id,
            token_endpoint=self._token_endpoint,
            now=now,
        )
        try:
            response = self._http_post(
                self._token_endpoint,
                {
                    "client_id": self._client_id,
                    "scope": STORAGE_SCOPE,
                    "grant_type": "client_credentials",
                    "client_assertion_type": _ASSERTION_TYPE,
                    "client_assertion": assertion,
                },
            )
        except Exception:
            raise AzurePerformanceStoragePortError(
                "AZURE_STORAGE_TOKEN_UNAVAILABLE"
            ) from None
        token = _token_from_response(response)
        try:
            jwks = self._jwks_fetcher(_JWKS_URI)
        except Exception:
            raise AzurePerformanceStoragePortError(
                "AZURE_STORAGE_TOKEN_UNAVAILABLE"
            ) from None
        validated_at = _clock_value(self._clock)
        not_before, expires_at = _validate_access_token(
            token,
            jwks=jwks,
            tenant_id=self._tenant_id,
            client_id=self._client_id,
            token_subject=self._token_subject,
            now=validated_at,
        )
        return _lease_token_issuer(
            token,
            scope=STORAGE_SCOPE,
            identity_binding_sha256=identity_binding_sha256,
            subject=self._token_subject,
            tenant_id=self._tenant_id,
            not_before=not_before,
            expires_at=expires_at,
            source_attestation_sha256=identity_binding_sha256,
        )


def _open_private_file_at(parent_fd: int, name: str, *, create: bool) -> int:
    if (
        not isinstance(name, str)
        or name in {"", ".", ".."}
        or "/" in name
        or "\\" in name
        or not hasattr(os, "O_NOFOLLOW")
    ):
        raise AzurePerformanceStoragePortError(
            "AZURE_PERFORMANCE_LEASE_HANDOFF_INVALID"
        )
    flags = os.O_RDWR | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    if create:
        flags |= os.O_CREAT
    try:
        descriptor = os.open(name, flags, 0o600, dir_fd=parent_fd)
    except OSError:
        raise AzurePerformanceStoragePortError(
            "AZURE_PERFORMANCE_LEASE_HANDOFF_INVALID"
        ) from None
    if not _private_regular_file(os.fstat(descriptor)):
        os.close(descriptor)
        raise AzurePerformanceStoragePortError(
            "AZURE_PERFORMANCE_LEASE_HANDOFF_INVALID"
        )
    return descriptor


def _private_regular_file(metadata: os.stat_result) -> bool:
    return (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid == os.geteuid()
        and stat.S_IMODE(metadata.st_mode) == 0o600
        and metadata.st_nlink == 1
    )


def _read_stable_fd(descriptor: int, maximum: int) -> bytes:
    before = os.fstat(descriptor)
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, min(64 * 1024, maximum + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > maximum:
            raise OSError
    after = os.fstat(descriptor)
    if (
        not _same_file_snapshot(before, after)
        or total != after.st_size
        or not _private_regular_file(after)
    ):
        raise OSError
    return b"".join(chunks)


def _same_file_snapshot(before: os.stat_result, after: os.stat_result) -> bool:
    return (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_uid,
        before.st_nlink,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) == (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_uid,
        after.st_nlink,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError
        offset += written


def _read_trusted_credential(
    path: Path, *, expected_sha256: str | None = None
) -> bytes:
    if (
        not isinstance(path, Path)
        or not path.is_absolute()
        or not _trusted_parent_chain(path.parent)
        or expected_sha256 is not None
        and not _is_sha256(expected_sha256)
        or not hasattr(os, "O_NOFOLLOW")
    ):
        raise AzurePerformanceStoragePortError(
            "AZURE_STORAGE_CREDENTIAL_UNTRUSTED"
        )
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or stat.S_IMODE(before.st_mode) not in {0o400, 0o600}
            or before.st_nlink != 1
        ):
            raise OSError
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(
                descriptor,
                min(64 * 1024, _MAX_CREDENTIAL_BYTES + 1 - total),
            )
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > _MAX_CREDENTIAL_BYTES:
                raise OSError
        after = os.fstat(descriptor)
        if not _same_credential_snapshot(before, after) or total != after.st_size:
            raise OSError
        payload = b"".join(chunks)
        if not payload or (
            expected_sha256 is not None
            and hashlib.sha256(payload).hexdigest() != expected_sha256
        ):
            raise OSError
        return payload
    except OSError:
        raise AzurePerformanceStoragePortError(
            "AZURE_STORAGE_CREDENTIAL_UNTRUSTED"
        ) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _same_credential_snapshot(
    before: os.stat_result, after: os.stat_result
) -> bool:
    return (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_uid,
        before.st_nlink,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) == (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_uid,
        after.st_nlink,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )


def _trusted_parent_chain(path: Path) -> bool:
    current = path
    try:
        filesystem_root_uid = Path("/").lstat().st_uid
        trusted_system_uids = {0, filesystem_root_uid}
        while True:
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                return False
            writable_by_others = bool(
                metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            )
            trusted_sticky_root = bool(
                metadata.st_uid in trusted_system_uids
                and metadata.st_mode & stat.S_ISVTX
                and stat.S_ISDIR(metadata.st_mode)
            )
            if metadata.st_uid not in {*trusted_system_uids, os.geteuid()} or (
                writable_by_others and not trusted_sticky_root
            ):
                return False
            if current == current.parent:
                return True
            current = current.parent
    except OSError:
        return False


def _load_credential_pair(
    certificate_bytes: bytes,
    private_key_bytes: bytes,
    *,
    password: bytes | None,
    now: float,
) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    try:
        try:
            certificate = x509.load_pem_x509_certificate(certificate_bytes)
        except ValueError:
            certificate = x509.load_der_x509_certificate(certificate_bytes)
        private_key = serialization.load_pem_private_key(
            private_key_bytes, password=password
        )
        public_key = certificate.public_key()
        if (
            not isinstance(private_key, rsa.RSAPrivateKey)
            or not isinstance(public_key, rsa.RSAPublicKey)
            or not _MIN_RSA_BITS <= private_key.key_size <= _MAX_RSA_BITS
            or private_key.public_key().public_numbers()
            != public_key.public_numbers()
        ):
            raise ValueError
        moment = datetime.fromtimestamp(now, tz=timezone.utc)
        not_before = getattr(certificate, "not_valid_before_utc", None)
        not_after = getattr(certificate, "not_valid_after_utc", None)
        if not_before is None:
            not_before = certificate.not_valid_before.replace(tzinfo=timezone.utc)
        if not_after is None:
            not_after = certificate.not_valid_after.replace(tzinfo=timezone.utc)
        if moment < not_before or moment >= not_after:
            raise ValueError
        try:
            key_usage = certificate.extensions.get_extension_for_class(
                x509.KeyUsage
            ).value
            if not key_usage.digital_signature:
                raise ValueError
        except x509.ExtensionNotFound:
            pass
        return certificate, private_key
    except (TypeError, ValueError, OverflowError):
        raise AzurePerformanceStoragePortError(
            "AZURE_STORAGE_CREDENTIAL_INVALID"
        ) from None


def _build_client_assertion(
    *,
    certificate: x509.Certificate,
    private_key: rsa.RSAPrivateKey,
    client_id: str,
    token_endpoint: str,
    now: float,
) -> str:
    issued_at = int(now)
    header = {
        "alg": "RS256",
        "typ": "JWT",
        "x5t": _b64url(certificate.fingerprint(hashes.SHA1())),  # nosec B303
    }
    claims = {
        "aud": token_endpoint,
        "iss": client_id,
        "sub": client_id,
        "jti": str(uuid4()),
        "nbf": issued_at - _CLOCK_SKEW_SECONDS,
        "exp": issued_at + _ASSERTION_LIFETIME_SECONDS,
    }
    signing_input = (
        _b64url(_canonical_json(header).encode("ascii"))
        + "."
        + _b64url(_canonical_json(claims).encode("ascii"))
    )
    try:
        signature = private_key.sign(
            signing_input.encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except (TypeError, ValueError):
        raise AzurePerformanceStoragePortError(
            "AZURE_STORAGE_CREDENTIAL_INVALID"
        ) from None
    return signing_input + "." + _b64url(signature)


def _token_from_response(value: object) -> str:
    if not isinstance(value, Mapping):
        raise AzurePerformanceStoragePortError("AZURE_STORAGE_TOKEN_INVALID")
    token = value.get("access_token")
    if (
        value.get("token_type") != "Bearer"
        or not isinstance(token, str)
        or not 1 <= len(token) <= _MAX_TOKEN_BYTES
        or token.strip() != token
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in token)
    ):
        raise AzurePerformanceStoragePortError("AZURE_STORAGE_TOKEN_INVALID")
    return token


def _validate_access_token(
    token: str,
    *,
    jwks: object,
    tenant_id: str,
    client_id: str,
    token_subject: str,
    now: float,
) -> tuple[float, float]:
    try:
        header_segment, claims_segment, signature_segment = _split_jwt(token)
        header = _decode_json_segment(header_segment)
        claims = _decode_json_segment(claims_segment)
        if (
            header.get("alg") != "RS256"
            or header.get("typ") != "JWT"
            or _bounded_string(header.get("kid")) is None
        ):
            raise _Rejected
        key = _select_jwk(jwks, header["kid"])
        signature = _b64url_decode(signature_segment)
        signing_input = f"{header_segment}.{claims_segment}".encode("ascii")
        _verify_rs256(signing_input, signature, key)
        return _validate_storage_claims(
            claims,
            tenant_id=tenant_id,
            client_id=client_id,
            token_subject=token_subject,
            now=now,
        )
    except (
        _Rejected,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
        TypeError,
        ValueError,
        InvalidSignature,
    ):
        raise AzurePerformanceStoragePortError(
            "AZURE_STORAGE_TOKEN_INVALID"
        ) from None


def _validate_storage_claims(
    claims: Mapping[str, Any],
    *,
    tenant_id: str,
    client_id: str,
    token_subject: str,
    now: float,
) -> tuple[float, float]:
    version = claims.get("ver")
    if version == "1.0":
        issuer = f"https://sts.windows.net/{tenant_id}/"
        application_claim = claims.get("appid")
    elif version == "2.0":
        issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        application_claim = claims.get("azp")
    else:
        raise _Rejected
    issued_at = _numeric_date(claims.get("iat"))
    not_before = _numeric_date(claims.get("nbf"))
    expires_at = _numeric_date(claims.get("exp"))
    if (
        claims.get("aud") != _STORAGE_AUDIENCE
        or claims.get("iss") != issuer
        or claims.get("tid") != tenant_id
        or claims.get("oid") != token_subject
        or application_claim != client_id
        or issued_at is None
        or not_before is None
        or expires_at is None
        or not not_before <= issued_at <= expires_at
        or expires_at - not_before > _MAX_TOKEN_LIFETIME_SECONDS
        or issued_at > now + _CLOCK_SKEW_SECONDS
        or now < not_before
        or now >= expires_at
    ):
        raise _Rejected
    return not_before, expires_at


def _select_jwk(value: object, kid: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _Rejected
    keys = value.get("keys")
    if (
        not isinstance(keys, list)
        or not 1 <= len(keys) <= _MAX_JWKS_KEYS
        or not all(isinstance(key, Mapping) for key in keys)
    ):
        raise _Rejected
    matches = [key for key in keys if key.get("kid") == kid]
    if len(matches) != 1:
        raise _Rejected
    return matches[0]


def _verify_rs256(
    signing_input: bytes, signature: bytes, jwk: Mapping[str, Any]
) -> None:
    if (
        jwk.get("kty") != "RSA"
        or jwk.get("use") not in (None, "sig")
        or jwk.get("alg") not in (None, "RS256")
    ):
        raise _Rejected
    modulus = _b64url_integer(jwk.get("n"))
    exponent = _b64url_integer(jwk.get("e"))
    try:
        key = rsa.RSAPublicNumbers(exponent, modulus).public_key()
    except ValueError:
        raise _Rejected from None
    if not _MIN_RSA_BITS <= key.key_size <= _MAX_RSA_BITS:
        raise _Rejected
    key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())


def _split_jwt(token: str) -> tuple[str, str, str]:
    parts = token.split(".")
    if len(parts) != 3 or not all(parts):
        raise _Rejected
    return parts[0], parts[1], parts[2]


def _decode_json_segment(segment: str) -> Mapping[str, Any]:
    raw = _b64url_decode(segment)
    if len(raw) > _MAX_JSON_SEGMENT_BYTES:
        raise _Rejected
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
    if not isinstance(value, Mapping):
        raise _Rejected
    return value


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _Rejected
        result[key] = value
    return result


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: object) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or _BASE64URL_RE.fullmatch(value) is None
    ):
        raise _Rejected
    encoded = value.encode("ascii")
    try:
        return base64.b64decode(
            encoded + b"=" * (-len(encoded) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError):
        raise _Rejected from None


def _b64url_integer(value: object) -> int:
    raw = _b64url_decode(value)
    if not raw:
        raise _Rejected
    return int.from_bytes(raw, "big")


def _post_token_form(endpoint: str, form: dict[str, str]) -> Mapping[str, Any]:
    if not endpoint.startswith("https://login.microsoftonline.com/"):
        raise _Rejected
    request = urllib.request.Request(
        endpoint,
        data=urllib.parse.urlencode(form).encode("ascii"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    return _open_json(request)


def _fetch_jwks(url: str) -> Mapping[str, Any]:
    if url != _JWKS_URI:
        raise _Rejected
    request = urllib.request.Request(
        url, headers={"Accept": "application/json"}, method="GET"
    )
    return _open_json(request)


def _open_json(request: urllib.request.Request) -> Mapping[str, Any]:
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            length = response.headers.get("Content-Length")
            if length is not None:
                try:
                    parsed_length = int(length)
                except (TypeError, ValueError):
                    raise _Rejected from None
                if parsed_length < 0 or parsed_length > _MAX_RESPONSE_BYTES:
                    raise _Rejected
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise _Rejected
    except urllib.error.HTTPError as error:
        error.close()
        raise _Rejected from None
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
    if not isinstance(value, Mapping):
        raise _Rejected
    return value


def _clock_value(clock: Clock) -> float:
    try:
        value = clock()
    except Exception:
        raise AzurePerformanceStoragePortError(
            "AZURE_STORAGE_TOKEN_CLOCK_INVALID"
        ) from None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AzurePerformanceStoragePortError(
            "AZURE_STORAGE_TOKEN_CLOCK_INVALID"
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise AzurePerformanceStoragePortError(
            "AZURE_STORAGE_TOKEN_CLOCK_INVALID"
        )
    return numeric


def _system_clock() -> float:
    return datetime.now(timezone.utc).timestamp()


def _numeric_date(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _canonical_uuid(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        canonical = str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        return None
    return canonical if canonical == value else None


def _bounded_string(value: object) -> str | None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 256
    ):
        return None
    return value


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()
