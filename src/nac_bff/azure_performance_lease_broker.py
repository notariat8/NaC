from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import math
import re
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Protocol, runtime_checkable
from uuid import UUID

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


TICKET_VERSION = "nac.azure-performance-lease-activation-ticket/v1"
RECEIPT_VERSION = "nac.azure-performance-lease-broker-receipt/v1"
MAX_TICKET_LIFETIME_SECONDS = 60
MAX_FUTURE_SKEW_SECONDS = 5


def lease_broker_policy() -> dict[str, Any]:
    """Return the fixed server-side lease and state-machine boundary."""

    return {
        "api_version": "2023-11-03",
        "allowed_operations": ["acquire", "assert_held", "release"],
        "broker_routes": [
            "POST /v1/internal/performance-lease/acquire",
            "POST /v1/internal/performance-lease/assert",
            "POST /v1/internal/performance-lease/release",
        ],
        "client_retries": 0,
        "forbidden_lease_actions": ["break", "change", "renew"],
        "lifecycle_states": [
            "ACQUIRE_INTENT",
            "ACQUIRE_IN_FLIGHT",
            "HELD",
            "RELEASE_INTENT",
            "RELEASED",
            "LOST",
        ],
        "local_runner_storage_access": False,
        "private_lease_id_owner": "broker_only",
        "redirects_followed": 0,
        "fresh_same_run_ticket_may_reconcile_persisted_intent": True,
        "same_ticket_retry_reuses_persisted_private_lease_id": True,
        "storage_token_holder": "broker_uami_only",
    }


def lease_broker_policy_sha256() -> str:
    return _sha256(_canonical_json(lease_broker_policy()))


def lease_broker_state_bootstrap_policy() -> dict[str, Any]:
    """Return the exact conditional-create policy for broker state metadata."""

    return {
        "allowed_operations": ["put_blob_if_absent", "head_blob"],
        "blob_type": "BlockBlob",
        "content_length": 0,
        "forbidden_operations": ["delete", "overwrite"],
        "owner_and_target_binding_required": True,
        "put_precondition": "If-None-Match:*",
        "runtime_creator": "broker_uami_only",
        "strong_etag_readback_required": True,
    }


def lease_broker_state_bootstrap_policy_sha256() -> str:
    return _sha256(_canonical_json(lease_broker_state_bootstrap_policy()))

_TICKET_FIELDS = frozenset({"key_id", "payload", "signature"})
_PAYLOAD_FIELDS = frozenset(
    {
        "actions",
        "actor_id",
        "audience",
        "blob_path",
        "commit_sha",
        "expires_at",
        "function_package_sha256",
        "issued_at",
        "issuer",
        "nonce",
        "owner_binding_sha256",
        "owner_subject",
        "plan_sha256",
        "role",
        "scope",
        "storage_binding",
        "target_binding_sha256",
        "tenant_id",
        "tree_sha",
        "version",
    }
)
_CLAIM_FIELDS = frozenset({"owner_subject", "role", "scope"})
_IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}\Z")
_KEY_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_BINDING_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class LeaseBrokerError(RuntimeError):
    """Stable error whose text contains no provider or identity details."""


class AcquireOutcome(str, Enum):
    ACQUIRED = "ACQUIRED"
    ALREADY_ACQUIRED = "ALREADY_ACQUIRED"
    BUSY = "BUSY"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    INDETERMINATE_AFTER_CRASH = "INDETERMINATE_AFTER_CRASH"
    REPLAY_REJECTED = "REPLAY_REJECTED"


class AssertOutcome(str, Enum):
    HELD = "HELD"
    LOST = "LOST"
    NOT_ACQUIRED = "NOT_ACQUIRED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    INDETERMINATE_AFTER_CRASH = "INDETERMINATE_AFTER_CRASH"
    REPLAY_REJECTED = "REPLAY_REJECTED"


class ReleaseOutcome(str, Enum):
    RELEASED = "RELEASED"
    ALREADY_RELEASED = "ALREADY_RELEASED"
    LOST = "LOST"
    NOT_ACQUIRED = "NOT_ACQUIRED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    INDETERMINATE_AFTER_CRASH = "INDETERMINATE_AFTER_CRASH"
    REPLAY_REJECTED = "REPLAY_REJECTED"


class RetryDirective(str, Enum):
    NONE = "NONE"
    RETRY_SAME_TICKET = "RETRY_SAME_TICKET"
    ASSERT_BEFORE_RETRY = "ASSERT_BEFORE_RETRY"
    DO_NOT_RETRY = "DO_NOT_RETRY"


@runtime_checkable
class TicketSignatureVerifier(Protocol):
    """Verifies server signatures; callers cannot substitute digest claims."""

    def verify(
        self,
        *,
        key_id: str,
        payload: bytes,
        signature: bytes,
    ) -> bool: ...


class RsaCertificateTicketSignatureVerifier:
    """Verify one pinned RS256 ticket-signing certificate."""

    def __init__(
        self,
        *,
        key_id: str,
        certificate_bytes: bytes,
        certificate_sha256: str,
    ) -> None:
        if (
            type(key_id) is not str
            or _KEY_ID_RE.fullmatch(key_id) is None
            or type(certificate_bytes) is not bytes
            or not _canonical_sha256(certificate_sha256)
            or not hmac.compare_digest(
                hashlib.sha256(certificate_bytes).hexdigest(), certificate_sha256
            )
        ):
            raise ValueError("LEASE_BROKER_CERTIFICATE_INVALID")
        try:
            certificate = (
                x509.load_pem_x509_certificate(certificate_bytes)
                if certificate_bytes.startswith(b"-----BEGIN CERTIFICATE-----")
                else x509.load_der_x509_certificate(certificate_bytes)
            )
            public_key = certificate.public_key()
            key_usage = certificate.extensions.get_extension_for_class(
                x509.KeyUsage
            ).value
        except Exception:
            raise ValueError("LEASE_BROKER_CERTIFICATE_INVALID") from None
        if (
            not isinstance(public_key, rsa.RSAPublicKey)
            or not 2048 <= public_key.key_size <= 4096
            or key_usage.digital_signature is not True
        ):
            raise ValueError("LEASE_BROKER_CERTIFICATE_INVALID")
        self._key_id = key_id
        self._public_key = public_key

    def verify(self, *, key_id: str, payload: bytes, signature: bytes) -> bool:
        if not hmac.compare_digest(key_id, self._key_id):
            return False
        try:
            self._public_key.verify(
                signature,
                payload,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except (InvalidSignature, TypeError, ValueError):
            return False
        return True


@dataclass(frozen=True, slots=True)
class AttestedStorageBinding:
    """Opaque deployment attestation, loaded and pinned outside request input."""

    binding_id: str
    attestation: bytes

    def __post_init__(self) -> None:
        if (
            type(self.binding_id) is not str
            or _BINDING_ID_RE.fullmatch(self.binding_id) is None
            or type(self.attestation) is not bytes
            or not 32 <= len(self.attestation) <= 4096
        ):
            raise ValueError("LEASE_BROKER_BINDING_INVALID")


@runtime_checkable
class FixedStorageBindingProvider(Protocol):
    """Returns one server-configured storage attestation at composition time."""

    def load(self) -> AttestedStorageBinding: ...


@dataclass(frozen=True, slots=True)
class BrokerRoleScopeClaims:
    """Trusted identity-middleware output dedicated to the broker boundary."""

    owner_subject: str
    role: str
    scope: str

    def __post_init__(self) -> None:
        if (
            _canonical_uuid(self.owner_subject) is None
            or not _valid_identifier(self.role)
            or not _valid_identifier(self.scope)
        ):
            raise ValueError("LEASE_BROKER_CLAIMS_INVALID")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> BrokerRoleScopeClaims:
        if type(value) is not dict or set(value) != _CLAIM_FIELDS:
            raise ValueError("LEASE_BROKER_CLAIMS_INVALID")
        try:
            return cls(
                owner_subject=value["owner_subject"],
                role=value["role"],
                scope=value["scope"],
            )
        except (KeyError, TypeError, ValueError):
            raise ValueError("LEASE_BROKER_CLAIMS_INVALID") from None


@dataclass(frozen=True, slots=True)
class ActivationTicketPayload:
    version: str
    issuer: str
    tenant_id: str
    audience: str
    actor_id: str
    owner_subject: str
    owner_binding_sha256: str
    commit_sha: str
    tree_sha: str
    function_package_sha256: str
    plan_sha256: str
    target_binding_sha256: str
    blob_path: str
    actions: tuple[str, ...]
    role: str
    scope: str
    storage_binding: str
    issued_at: int
    expires_at: int
    nonce: str

    def canonical_bytes(self) -> bytes:
        return _canonical_json(
            {
                "actions": list(self.actions),
                "actor_id": self.actor_id,
                "audience": self.audience,
                "blob_path": self.blob_path,
                "commit_sha": self.commit_sha,
                "expires_at": self.expires_at,
                "function_package_sha256": self.function_package_sha256,
                "issued_at": self.issued_at,
                "issuer": self.issuer,
                "nonce": self.nonce,
                "owner_binding_sha256": self.owner_binding_sha256,
                "owner_subject": self.owner_subject,
                "plan_sha256": self.plan_sha256,
                "role": self.role,
                "scope": self.scope,
                "storage_binding": self.storage_binding,
                "target_binding_sha256": self.target_binding_sha256,
                "tenant_id": self.tenant_id,
                "tree_sha": self.tree_sha,
                "version": self.version,
            }
        )


@dataclass(frozen=True, slots=True)
class SignedActivationTicket:
    key_id: str
    payload: ActivationTicketPayload
    signature: bytes

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> SignedActivationTicket:
        if type(value) is not dict or set(value) != _TICKET_FIELDS:
            raise LeaseBrokerError("LEASE_BROKER_TICKET_INVALID")
        raw_payload = value.get("payload")
        if type(raw_payload) is not dict or set(raw_payload) != _PAYLOAD_FIELDS:
            raise LeaseBrokerError("LEASE_BROKER_TICKET_INVALID")
        try:
            key_id = value["key_id"]
            signature = _decode_base64url(
                value["signature"], minimum=32, maximum=1024
            )
            payload = ActivationTicketPayload(
                version=raw_payload["version"],
                issuer=raw_payload["issuer"],
                tenant_id=raw_payload["tenant_id"],
                audience=raw_payload["audience"],
                actor_id=raw_payload["actor_id"],
                owner_subject=raw_payload["owner_subject"],
                owner_binding_sha256=raw_payload["owner_binding_sha256"],
                commit_sha=raw_payload["commit_sha"],
                tree_sha=raw_payload["tree_sha"],
                function_package_sha256=raw_payload["function_package_sha256"],
                plan_sha256=raw_payload["plan_sha256"],
                target_binding_sha256=raw_payload["target_binding_sha256"],
                blob_path=raw_payload["blob_path"],
                actions=tuple(raw_payload["actions"]),
                role=raw_payload["role"],
                scope=raw_payload["scope"],
                storage_binding=raw_payload["storage_binding"],
                issued_at=raw_payload["issued_at"],
                expires_at=raw_payload["expires_at"],
                nonce=raw_payload["nonce"],
            )
        except (KeyError, TypeError, ValueError):
            raise LeaseBrokerError("LEASE_BROKER_TICKET_INVALID") from None
        if type(key_id) is not str or _KEY_ID_RE.fullmatch(key_id) is None:
            raise LeaseBrokerError("LEASE_BROKER_TICKET_INVALID")
        return cls(key_id=key_id, payload=payload, signature=signature)


@dataclass(frozen=True, slots=True)
class LeaseAcquireCommand:
    run_fingerprint: str
    operation_id: str
    nonce_key: str
    binding_fingerprint: str
    private_lease_id: str


@dataclass(frozen=True, slots=True)
class LeaseCommand:
    run_fingerprint: str
    operation_id: str
    nonce_key: str
    binding_fingerprint: str


@runtime_checkable
class AtomicLeaseStateMachinePort(Protocol):
    """Atomic, durable port for one fixed target.

    Implementations must reserve ``nonce_key`` and persist transition intent in
    the same critical section used to classify the result. Exact retries use
    ``operation_id``; a nonce attached to another operation is a replay. An
    Azure adapter keeps ``private_lease_id`` server-side and exposes no lease
    mutation surface beyond these three methods.
    """

    def acquire(self, command: LeaseAcquireCommand, /) -> AcquireOutcome: ...

    def assert_held(self, command: LeaseCommand, /) -> AssertOutcome: ...

    def release(self, command: LeaseCommand, /) -> ReleaseOutcome: ...


@dataclass(frozen=True, slots=True)
class LeaseBrokerReceipt:
    operation: str
    outcome: str
    retry: RetryDirective
    ticket_fingerprint: str
    binding_fingerprint: str
    schema_version: str = RECEIPT_VERSION

    def as_dict(self) -> dict[str, str]:
        return {
            "binding_fingerprint": self.binding_fingerprint,
            "operation": self.operation,
            "outcome": self.outcome,
            "retry": self.retry.value,
            "schema_version": self.schema_version,
            "ticket_fingerprint": self.ticket_fingerprint,
        }


class AzurePerformanceLeaseBroker:
    """Owner-bound lease broker core with no network or Azure dependency."""

    def __init__(
        self,
        *,
        signature_verifier: TicketSignatureVerifier,
        binding_provider: FixedStorageBindingProvider,
        state_machine: AtomicLeaseStateMachinePort,
        issuer: str,
        tenant_id: str,
        audience: str,
        actor_id: str,
        owner_subject: str,
        owner_binding_sha256: str,
        commit_sha: str,
        tree_sha: str,
        function_package_sha256: str,
        plan_sha256: str,
        target_binding_sha256: str,
        blob_path: str,
        required_role: str,
        required_scope: str,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if (
            not isinstance(signature_verifier, TicketSignatureVerifier)
            or not isinstance(binding_provider, FixedStorageBindingProvider)
            or not isinstance(state_machine, AtomicLeaseStateMachinePort)
            or not _valid_identifier(issuer)
            or _canonical_uuid(tenant_id) is None
            or not _valid_identifier(audience)
            or _canonical_uuid(actor_id) is None
            or _canonical_uuid(owner_subject) is None
            or not all(
                _canonical_sha256(value)
                for value in (
                    owner_binding_sha256,
                    tree_sha,
                    function_package_sha256,
                    plan_sha256,
                    target_binding_sha256,
                )
            )
            or not _canonical_git_sha(commit_sha)
            or not _valid_blob_path(blob_path, target_binding_sha256)
            or not _valid_identifier(required_role)
            or not _valid_identifier(required_scope)
            or not callable(clock)
        ):
            raise ValueError("LEASE_BROKER_CONFIGURATION_INVALID")
        try:
            binding = binding_provider.load()
        except Exception:
            raise ValueError("LEASE_BROKER_BINDING_INVALID") from None
        if type(binding) is not AttestedStorageBinding:
            raise ValueError("LEASE_BROKER_BINDING_INVALID")
        self._signature_verifier = signature_verifier
        self._state_machine = state_machine
        self._issuer = issuer
        self._tenant_id = tenant_id
        self._audience = audience
        self._actor_id = actor_id
        self._owner_subject = owner_subject
        self._owner_binding_sha256 = owner_binding_sha256
        self._commit_sha = commit_sha
        self._tree_sha = tree_sha
        self._function_package_sha256 = function_package_sha256
        self._plan_sha256 = plan_sha256
        self._target_binding_sha256 = target_binding_sha256
        self._blob_path = blob_path
        self._required_role = required_role
        self._required_scope = required_scope
        self._clock = clock
        self._binding_id = binding.binding_id
        self._binding_fingerprint = _sha256(
            _canonical_json(
                {
                    "attestation": _encode_base64url(binding.attestation),
                    "binding_id": binding.binding_id,
                }
            )
        )
        self._run_fingerprint = _sha256(
            _canonical_json(
                {
                    "blob_path": self._blob_path,
                    "commit_sha": self._commit_sha,
                    "function_package_sha256": self._function_package_sha256,
                    "owner_binding_sha256": self._owner_binding_sha256,
                    "plan_sha256": self._plan_sha256,
                    "storage_binding_fingerprint": self._binding_fingerprint,
                    "target_binding_sha256": self._target_binding_sha256,
                    "tree_sha": self._tree_sha,
                }
            )
        )

    def acquire(
        self,
        *,
        ticket: Mapping[str, Any],
        claims: BrokerRoleScopeClaims,
    ) -> LeaseBrokerReceipt:
        verified = self._verify(ticket, claims, operation="acquire")
        command = LeaseAcquireCommand(
            run_fingerprint=self._run_fingerprint,
            operation_id=verified.operation_id,
            nonce_key=verified.nonce_key,
            binding_fingerprint=self._binding_fingerprint,
            private_lease_id=_encode_base64url(secrets.token_bytes(32)),
        )
        outcome = self._call_state("acquire", command, AcquireOutcome)
        retry = {
            AcquireOutcome.ACQUIRED: RetryDirective.NONE,
            AcquireOutcome.ALREADY_ACQUIRED: RetryDirective.NONE,
            AcquireOutcome.BUSY: RetryDirective.RETRY_SAME_TICKET,
            AcquireOutcome.RETRYABLE_FAILURE: RetryDirective.RETRY_SAME_TICKET,
            AcquireOutcome.INDETERMINATE_AFTER_CRASH: (
                RetryDirective.ASSERT_BEFORE_RETRY
            ),
            AcquireOutcome.REPLAY_REJECTED: RetryDirective.DO_NOT_RETRY,
        }[outcome]
        return self._receipt("acquire", outcome.value, retry, verified)

    def assert_held(
        self,
        *,
        ticket: Mapping[str, Any],
        claims: BrokerRoleScopeClaims,
    ) -> LeaseBrokerReceipt:
        verified = self._verify(ticket, claims, operation="assert")
        outcome = self._call_state(
            "assert_held", self._command(verified), AssertOutcome
        )
        retry = {
            AssertOutcome.HELD: RetryDirective.NONE,
            AssertOutcome.LOST: RetryDirective.DO_NOT_RETRY,
            AssertOutcome.NOT_ACQUIRED: RetryDirective.DO_NOT_RETRY,
            AssertOutcome.RETRYABLE_FAILURE: RetryDirective.RETRY_SAME_TICKET,
            AssertOutcome.INDETERMINATE_AFTER_CRASH: (
                RetryDirective.RETRY_SAME_TICKET
            ),
            AssertOutcome.REPLAY_REJECTED: RetryDirective.DO_NOT_RETRY,
        }[outcome]
        return self._receipt("assert_held", outcome.value, retry, verified)

    def release(
        self,
        *,
        ticket: Mapping[str, Any],
        claims: BrokerRoleScopeClaims,
    ) -> LeaseBrokerReceipt:
        verified = self._verify(ticket, claims, operation="release")
        outcome = self._call_state(
            "release", self._command(verified), ReleaseOutcome
        )
        retry = {
            ReleaseOutcome.RELEASED: RetryDirective.NONE,
            ReleaseOutcome.ALREADY_RELEASED: RetryDirective.NONE,
            ReleaseOutcome.LOST: RetryDirective.DO_NOT_RETRY,
            ReleaseOutcome.NOT_ACQUIRED: RetryDirective.DO_NOT_RETRY,
            ReleaseOutcome.RETRYABLE_FAILURE: RetryDirective.RETRY_SAME_TICKET,
            ReleaseOutcome.INDETERMINATE_AFTER_CRASH: (
                RetryDirective.ASSERT_BEFORE_RETRY
            ),
            ReleaseOutcome.REPLAY_REJECTED: RetryDirective.DO_NOT_RETRY,
        }[outcome]
        return self._receipt("release", outcome.value, retry, verified)

    def _verify(
        self,
        ticket_value: Mapping[str, Any],
        claims: BrokerRoleScopeClaims,
        *,
        operation: str,
    ) -> _VerifiedTicket:
        if type(claims) is not BrokerRoleScopeClaims:
            raise LeaseBrokerError("LEASE_BROKER_CLAIMS_INVALID")
        ticket = SignedActivationTicket.from_mapping(ticket_value)
        payload_bytes = ticket.payload.canonical_bytes()
        try:
            signature_valid = self._signature_verifier.verify(
                key_id=ticket.key_id,
                payload=payload_bytes,
                signature=ticket.signature,
            )
        except Exception:
            raise LeaseBrokerError("LEASE_BROKER_SIGNATURE_INVALID") from None
        if signature_valid is not True:
            raise LeaseBrokerError("LEASE_BROKER_SIGNATURE_INVALID")
        now = self._clock_value()
        payload = ticket.payload
        if not _valid_payload_shape(payload):
            raise LeaseBrokerError("LEASE_BROKER_TICKET_INVALID")
        if (
            payload.version != TICKET_VERSION
            or not hmac.compare_digest(payload.issuer, self._issuer)
            or not hmac.compare_digest(payload.tenant_id, self._tenant_id)
            or not hmac.compare_digest(payload.audience, self._audience)
            or not hmac.compare_digest(payload.actor_id, self._actor_id)
            or not hmac.compare_digest(payload.storage_binding, self._binding_id)
            or not hmac.compare_digest(
                payload.owner_binding_sha256, self._owner_binding_sha256
            )
            or not hmac.compare_digest(payload.commit_sha, self._commit_sha)
            or not hmac.compare_digest(payload.tree_sha, self._tree_sha)
            or not hmac.compare_digest(
                payload.function_package_sha256, self._function_package_sha256
            )
            or not hmac.compare_digest(payload.plan_sha256, self._plan_sha256)
            or not hmac.compare_digest(
                payload.target_binding_sha256, self._target_binding_sha256
            )
            or not hmac.compare_digest(payload.blob_path, self._blob_path)
            or payload.actions != (operation,)
            or payload.expires_at <= now
            or payload.issued_at > now + MAX_FUTURE_SKEW_SECONDS
            or payload.expires_at - payload.issued_at
            > MAX_TICKET_LIFETIME_SECONDS
        ):
            raise LeaseBrokerError("LEASE_BROKER_TICKET_INVALID")
        if not (
            hmac.compare_digest(payload.owner_subject, self._owner_subject)
            and hmac.compare_digest(claims.owner_subject, self._owner_subject)
            and hmac.compare_digest(payload.owner_subject, claims.owner_subject)
            and hmac.compare_digest(payload.role, self._required_role)
            and hmac.compare_digest(claims.role, self._required_role)
            and hmac.compare_digest(payload.scope, self._required_scope)
            and hmac.compare_digest(claims.scope, self._required_scope)
        ):
            raise LeaseBrokerError("LEASE_BROKER_OWNER_AUTHORIZATION_DENIED")
        ticket_fingerprint = _sha256(
            payload_bytes
            + b"\x00"
            + ticket.key_id.encode("ascii")
            + b"\x00"
            + ticket.signature
        )
        return _VerifiedTicket(
            operation_id=ticket_fingerprint,
            nonce_key=_sha256(
                payload.issuer.encode("utf-8")
                + b"\x00"
                + _decode_base64url(payload.nonce, minimum=32, maximum=32)
            ),
            ticket_fingerprint=ticket_fingerprint,
        )

    def _command(self, ticket: _VerifiedTicket) -> LeaseCommand:
        return LeaseCommand(
            run_fingerprint=self._run_fingerprint,
            operation_id=ticket.operation_id,
            nonce_key=ticket.nonce_key,
            binding_fingerprint=self._binding_fingerprint,
        )

    def _call_state(self, method: str, command: object, expected: type[Enum]) -> Any:
        try:
            result = getattr(self._state_machine, method)(command)
        except Exception:
            raise LeaseBrokerError("LEASE_BROKER_STATE_UNAVAILABLE") from None
        if type(result) is not expected:
            raise LeaseBrokerError("LEASE_BROKER_STATE_RESPONSE_INVALID")
        return result

    def _receipt(
        self,
        operation: str,
        outcome: str,
        retry: RetryDirective,
        ticket: _VerifiedTicket,
    ) -> LeaseBrokerReceipt:
        return LeaseBrokerReceipt(
            operation=operation,
            outcome=outcome,
            retry=retry,
            ticket_fingerprint=ticket.ticket_fingerprint,
            binding_fingerprint=self._binding_fingerprint,
        )

    def _clock_value(self) -> int:
        try:
            value = self._clock()
        except Exception:
            raise LeaseBrokerError("LEASE_BROKER_CLOCK_INVALID") from None
        if type(value) not in {int, float} or not math.isfinite(value):
            raise LeaseBrokerError("LEASE_BROKER_CLOCK_INVALID")
        return math.floor(value)


@dataclass(frozen=True, slots=True)
class _VerifiedTicket:
    operation_id: str
    nonce_key: str
    ticket_fingerprint: str


def _valid_payload_shape(value: ActivationTicketPayload) -> bool:
    return (
        type(value.version) is str
        and _valid_identifier(value.issuer)
        and _canonical_uuid(value.tenant_id) is not None
        and _valid_identifier(value.audience)
        and _canonical_uuid(value.actor_id) is not None
        and _canonical_uuid(value.owner_subject) is not None
        and _canonical_sha256(value.owner_binding_sha256)
        and _canonical_git_sha(value.commit_sha)
        and _canonical_sha256(value.tree_sha)
        and _canonical_sha256(value.function_package_sha256)
        and _canonical_sha256(value.plan_sha256)
        and _canonical_sha256(value.target_binding_sha256)
        and _valid_blob_path(value.blob_path, value.target_binding_sha256)
        and type(value.actions) is tuple
        and len(value.actions) == 1
        and value.actions[0] in {"acquire", "assert", "release"}
        and _valid_identifier(value.role)
        and _valid_identifier(value.scope)
        and type(value.storage_binding) is str
        and _BINDING_ID_RE.fullmatch(value.storage_binding) is not None
        and type(value.issued_at) is int
        and type(value.expires_at) is int
        and 0 <= value.issued_at < value.expires_at <= 2**63 - 1
        and _canonical_base64url(value.nonce, size=32)
    )


def _valid_identifier(value: object) -> bool:
    return type(value) is str and _IDENTIFIER_RE.fullmatch(value) is not None


def _canonical_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _canonical_git_sha(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 40
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_blob_path(value: object, target_binding_sha256: object) -> bool:
    return (
        _canonical_sha256(target_binding_sha256)
        and value == f"locks/{target_binding_sha256}.lock"
    )


def _canonical_uuid(value: object) -> str | None:
    if type(value) is not str:
        return None
    try:
        canonical = str(UUID(value))
    except (AttributeError, TypeError, ValueError):
        return None
    return canonical if canonical == value else None


def _canonical_base64url(value: object, *, size: int) -> bool:
    try:
        return len(_decode_base64url(value, minimum=size, maximum=size)) == size
    except (TypeError, ValueError):
        return False


def _decode_base64url(value: object, *, minimum: int, maximum: int) -> bytes:
    if (
        type(value) is not str
        or not value
        or "=" in value
        or any(character not in _BASE64URL_ALPHABET for character in value)
    ):
        raise ValueError
    try:
        decoded = base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
        )
    except (ValueError, binascii.Error):
        raise ValueError from None
    if not minimum <= len(decoded) <= maximum or _encode_base64url(decoded) != value:
        raise ValueError
    return decoded


_BASE64URL_ALPHABET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)


def _encode_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError):
        raise LeaseBrokerError("LEASE_BROKER_TICKET_INVALID") from None


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
