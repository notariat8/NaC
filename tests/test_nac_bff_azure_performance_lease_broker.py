from __future__ import annotations

import base64
import hashlib
import hmac
import inspect
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from nac_bff.azure_performance_lease_broker import (
    MAX_TICKET_LIFETIME_SECONDS,
    TICKET_VERSION,
    AcquireOutcome,
    AssertOutcome,
    AtomicLeaseStateMachinePort,
    AttestedStorageBinding,
    AzurePerformanceLeaseBroker,
    BrokerRoleScopeClaims,
    LeaseAcquireCommand,
    LeaseBrokerError,
    LeaseCommand,
    ReleaseOutcome,
    RsaCertificateTicketSignatureVerifier,
    RetryDirective,
)


NOW = 1_800_000_000
OWNER = "11111111-1111-4111-8111-111111111111"
OTHER_OWNER = "22222222-2222-4222-8222-222222222222"
TENANT = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
ACTOR = "33333333-3333-4333-8333-333333333333"
ROLE = "nac.performance.lease-broker"
SCOPE = "nac.performance.lease"
ISSUER = "nac-owner-approval-service"
AUDIENCE = "nac-azure-performance-lease-broker"
BINDING = "performance-coordination-v1"
KEY_ID = "owner-signing-key-v1"
KEY = b"unit-test-owner-signing-key-not-a-production-secret"
OWNER_BINDING = "1" * 64
COMMIT = "2" * 40
TREE = "3" * 64
FUNCTION_PACKAGE = "4" * 64
PLAN = "5" * 64
TARGET = "6" * 64
BLOB_PATH = f"locks/{TARGET}.lock"


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


class HmacVerifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, bytes]] = []

    def verify(self, *, key_id: str, payload: bytes, signature: bytes) -> bool:
        self.calls.append((key_id, payload, signature))
        return key_id == KEY_ID and hmac.compare_digest(
            signature, hmac.new(KEY, payload, hashlib.sha256).digest()
        )


class BindingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def load(self) -> AttestedStorageBinding:
        self.calls += 1
        return AttestedStorageBinding(BINDING, b"a" * 64)


class AtomicMemoryStateMachine:
    """Test double implementing the documented atomic/replay contract."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_nonce: dict[str, str] = {}
        self._state: dict[str, Any] | None = None
        self.acquire_commands: list[LeaseAcquireCommand] = []
        self.assert_commands: list[LeaseCommand] = []
        self.release_commands: list[LeaseCommand] = []

    def acquire(self, command: LeaseAcquireCommand, /) -> AcquireOutcome:
        with self._lock:
            self.acquire_commands.append(command)
            prior_operation = self._by_nonce.get(command.nonce_key)
            if prior_operation is not None and prior_operation != command.operation_id:
                return AcquireOutcome.REPLAY_REJECTED
            self._by_nonce[command.nonce_key] = command.operation_id
            if self._state is None:
                self._state = {
                    "operation_id": command.operation_id,
                    "private_lease_id": command.private_lease_id,
                    "state": "HELD",
                }
                return AcquireOutcome.ACQUIRED
            return (
                AcquireOutcome.ALREADY_ACQUIRED
                if self._state["operation_id"] == command.operation_id
                else AcquireOutcome.BUSY
            )

    def assert_held(self, command: LeaseCommand, /) -> AssertOutcome:
        with self._lock:
            self.assert_commands.append(command)
            prior_operation = self._by_nonce.get(command.nonce_key)
            if prior_operation is not None and prior_operation != command.operation_id:
                return AssertOutcome.REPLAY_REJECTED
            self._by_nonce[command.nonce_key] = command.operation_id
            if self._state is None:
                return AssertOutcome.NOT_ACQUIRED
            return (
                AssertOutcome.HELD
                if self._state["state"] == "HELD"
                else AssertOutcome.LOST
            )

    def release(self, command: LeaseCommand, /) -> ReleaseOutcome:
        with self._lock:
            self.release_commands.append(command)
            prior_operation = self._by_nonce.get(command.nonce_key)
            if prior_operation is not None and prior_operation != command.operation_id:
                return ReleaseOutcome.REPLAY_REJECTED
            self._by_nonce[command.nonce_key] = command.operation_id
            if self._state is None:
                return ReleaseOutcome.NOT_ACQUIRED
            if self._state["state"] == "RELEASED":
                return ReleaseOutcome.ALREADY_RELEASED
            self._state["state"] = "RELEASED"
            return ReleaseOutcome.RELEASED


class FixedOutcomeStateMachine:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome

    def acquire(self, command: LeaseAcquireCommand, /) -> Any:
        return self.outcome

    def assert_held(self, command: LeaseCommand, /) -> Any:
        return self.outcome

    def release(self, command: LeaseCommand, /) -> Any:
        return self.outcome


def make_ticket(*, operation: str = "acquire", **changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "actions": [operation],
        "actor_id": ACTOR,
        "audience": AUDIENCE,
        "blob_path": BLOB_PATH,
        "commit_sha": COMMIT,
        "expires_at": NOW + 45,
        "function_package_sha256": FUNCTION_PACKAGE,
        "issued_at": NOW,
        "issuer": ISSUER,
        "nonce": _b64(b"n" * 32),
        "owner_binding_sha256": OWNER_BINDING,
        "owner_subject": OWNER,
        "plan_sha256": PLAN,
        "role": ROLE,
        "scope": SCOPE,
        "storage_binding": BINDING,
        "target_binding_sha256": TARGET,
        "tenant_id": TENANT,
        "tree_sha": TREE,
        "version": TICKET_VERSION,
    }
    payload.update(changes)
    return {
        "key_id": KEY_ID,
        "payload": payload,
        "signature": _b64(hmac.new(KEY, _canonical(payload), hashlib.sha256).digest()),
    }


def make_broker(
    state_machine: object | None = None,
    *,
    verifier: object | None = None,
    provider: object | None = None,
    clock: object = lambda: NOW,
) -> tuple[AzurePerformanceLeaseBroker, Any, Any, Any]:
    selected_state = state_machine or AtomicMemoryStateMachine()
    selected_verifier = verifier or HmacVerifier()
    selected_provider = provider or BindingProvider()
    broker = AzurePerformanceLeaseBroker(
        signature_verifier=selected_verifier,
        binding_provider=selected_provider,
        state_machine=selected_state,
        issuer=ISSUER,
        tenant_id=TENANT,
        audience=AUDIENCE,
        actor_id=ACTOR,
        owner_subject=OWNER,
        owner_binding_sha256=OWNER_BINDING,
        commit_sha=COMMIT,
        tree_sha=TREE,
        function_package_sha256=FUNCTION_PACKAGE,
        plan_sha256=PLAN,
        target_binding_sha256=TARGET,
        blob_path=BLOB_PATH,
        required_role=ROLE,
        required_scope=SCOPE,
        clock=clock,  # type: ignore[arg-type]
    )
    return broker, selected_state, selected_verifier, selected_provider


CLAIMS = BrokerRoleScopeClaims(owner_subject=OWNER, role=ROLE, scope=SCOPE)


class TicketTests(unittest.TestCase):
    def test_pinned_rsa_certificate_verifier_accepts_only_exact_key(self) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "NaC owner gate")])
        now = datetime.now(UTC)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(private_key.public_key())
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
            .sign(private_key, hashes.SHA256())
        )
        encoded = certificate.public_bytes(serialization.Encoding.PEM)
        verifier = RsaCertificateTicketSignatureVerifier(
            key_id=KEY_ID,
            certificate_bytes=encoded,
            certificate_sha256=hashlib.sha256(encoded).hexdigest(),
        )
        payload = b"bound-ticket"
        signature = private_key.sign(payload, padding.PKCS1v15(), hashes.SHA256())
        self.assertTrue(
            verifier.verify(key_id=KEY_ID, payload=payload, signature=signature)
        )
        self.assertFalse(
            verifier.verify(key_id="other-key", payload=payload, signature=signature)
        )
        self.assertFalse(
            verifier.verify(key_id=KEY_ID, payload=b"tampered", signature=signature)
        )

    def test_valid_ticket_is_verified_over_canonical_payload(self) -> None:
        broker, state, verifier, _ = make_broker()
        ticket = make_ticket()

        receipt = broker.acquire(ticket=ticket, claims=CLAIMS)

        self.assertEqual(receipt.outcome, AcquireOutcome.ACQUIRED.value)
        self.assertEqual(verifier.calls[0][0], KEY_ID)
        self.assertEqual(verifier.calls[0][1], _canonical(ticket["payload"]))
        self.assertEqual(len(state.acquire_commands), 1)

    def test_ticket_and_payload_fields_are_exact(self) -> None:
        for path, key in (("ticket", "extra"), ("payload", "trusted_sha256")):
            with self.subTest(path=path):
                ticket = make_ticket()
                target = ticket if path == "ticket" else ticket["payload"]
                target[key] = "0" * 64  # type: ignore[index]
                broker, state, _, _ = make_broker()
                with self.assertRaisesRegex(
                    LeaseBrokerError, "^LEASE_BROKER_TICKET_INVALID$"
                ):
                    broker.acquire(ticket=ticket, claims=CLAIMS)
                self.assertEqual(state.acquire_commands, [])

        for path, key in (("ticket", "signature"), ("payload", "nonce")):
            with self.subTest(path=path, missing=key):
                ticket = make_ticket()
                target = ticket if path == "ticket" else ticket["payload"]
                del target[key]  # type: ignore[index]
                broker, _, _, _ = make_broker()
                with self.assertRaisesRegex(
                    LeaseBrokerError, "^LEASE_BROKER_TICKET_INVALID$"
                ):
                    broker.acquire(ticket=ticket, claims=CLAIMS)

    def test_every_signed_payload_field_is_tamper_evident(self) -> None:
        replacements = {
            "actions": ["release"],
            "actor_id": OTHER_OWNER,
            "audience": "other-audience",
            "blob_path": f"locks/{'7' * 64}.lock",
            "commit_sha": "7" * 40,
            "expires_at": NOW + 44,
            "function_package_sha256": "7" * 64,
            "issued_at": NOW - 1,
            "issuer": "other-issuer",
            "nonce": _b64(b"x" * 32),
            "owner_binding_sha256": "7" * 64,
            "owner_subject": OTHER_OWNER,
            "plan_sha256": "7" * 64,
            "role": "other.role",
            "scope": "other.scope",
            "storage_binding": "other-binding",
            "target_binding_sha256": "7" * 64,
            "tenant_id": OTHER_OWNER,
            "tree_sha": "7" * 64,
            "version": "other/v1",
        }
        original = make_ticket()
        for name, replacement in replacements.items():
            with self.subTest(field=name):
                ticket = deepcopy(original)
                ticket["payload"][name] = replacement  # type: ignore[index]
                broker, state, _, _ = make_broker()
                with self.assertRaisesRegex(
                    LeaseBrokerError, "^LEASE_BROKER_SIGNATURE_INVALID$"
                ):
                    broker.acquire(ticket=ticket, claims=CLAIMS)
                self.assertEqual(state.acquire_commands, [])

    def test_invalid_signature_and_verifier_failure_are_redacted(self) -> None:
        ticket = make_ticket()
        ticket["signature"] = _b64(b"z" * 32)
        broker, _, _, _ = make_broker()
        with self.assertRaisesRegex(
            LeaseBrokerError, "^LEASE_BROKER_SIGNATURE_INVALID$"
        ):
            broker.acquire(ticket=ticket, claims=CLAIMS)

        class FailingVerifier(HmacVerifier):
            def verify(self, **kwargs: object) -> bool:
                raise RuntimeError("secret provider details")

        broker, _, _, _ = make_broker(verifier=FailingVerifier())
        with self.assertRaisesRegex(
            LeaseBrokerError, "^LEASE_BROKER_SIGNATURE_INVALID$"
        ):
            broker.acquire(ticket=make_ticket(), claims=CLAIMS)

    def test_expiry_lifetime_future_skew_and_integer_dates_are_enforced(self) -> None:
        cases = (
            {"expires_at": NOW},
            {"expires_at": NOW + MAX_TICKET_LIFETIME_SECONDS + 1},
            {"issued_at": NOW + 6, "expires_at": NOW + 7},
            {"issued_at": True},
            {"expires_at": float(NOW + 1)},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                broker, state, _, _ = make_broker()
                with self.assertRaisesRegex(
                    LeaseBrokerError, "^LEASE_BROKER_TICKET_INVALID$"
                ):
                    broker.acquire(ticket=make_ticket(**changes), claims=CLAIMS)
                self.assertEqual(state.acquire_commands, [])

    def test_nonce_must_be_canonical_256_bit_base64url(self) -> None:
        for nonce in ("short", _b64(b"x" * 31), _b64(b"x" * 33), _b64(b"x" * 32) + "="):
            with self.subTest(nonce=nonce):
                broker, _, _, _ = make_broker()
                with self.assertRaisesRegex(
                    LeaseBrokerError, "^LEASE_BROKER_TICKET_INVALID$"
                ):
                    broker.acquire(ticket=make_ticket(nonce=nonce), claims=CLAIMS)


class AuthorizationTests(unittest.TestCase):
    def test_owner_role_and_scope_are_bound_on_server_and_in_trusted_claims(self) -> None:
        ticket_changes = (
            {"owner_subject": OTHER_OWNER},
            {"role": "nac.performance.viewer"},
            {"scope": "nac.performance.read"},
        )
        for changes in ticket_changes:
            with self.subTest(ticket=changes):
                broker, state, _, _ = make_broker()
                with self.assertRaisesRegex(
                    LeaseBrokerError,
                    "^LEASE_BROKER_OWNER_AUTHORIZATION_DENIED$",
                ):
                    broker.acquire(ticket=make_ticket(**changes), claims=CLAIMS)
                self.assertEqual(state.acquire_commands, [])

        claim_changes = (
            {"owner_subject": OTHER_OWNER, "role": ROLE, "scope": SCOPE},
            {"owner_subject": OWNER, "role": "other.role", "scope": SCOPE},
            {"owner_subject": OWNER, "role": ROLE, "scope": "other.scope"},
        )
        for changes in claim_changes:
            with self.subTest(claims=changes):
                broker, state, _, _ = make_broker()
                claims = BrokerRoleScopeClaims(**changes)
                with self.assertRaisesRegex(
                    LeaseBrokerError,
                    "^LEASE_BROKER_OWNER_AUTHORIZATION_DENIED$",
                ):
                    broker.acquire(ticket=make_ticket(), claims=claims)
                self.assertEqual(state.acquire_commands, [])

    def test_claim_mapping_rejects_missing_extra_and_generic_claims(self) -> None:
        valid = {"owner_subject": OWNER, "role": ROLE, "scope": SCOPE}
        self.assertEqual(BrokerRoleScopeClaims.from_mapping(valid), CLAIMS)
        for value in (
            {"owner_subject": OWNER, "role": ROLE},
            {**valid, "roles": [ROLE]},
            {**valid, "trusted_sha256": "0" * 64},
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "LEASE_BROKER_CLAIMS_INVALID"):
                    BrokerRoleScopeClaims.from_mapping(value)

    def test_binding_issuer_and_audience_drift_fail_before_state_access(self) -> None:
        for changes in (
            {"storage_binding": "other-binding"},
            {"issuer": "other-issuer"},
            {"audience": "other-audience"},
            {"tenant_id": OTHER_OWNER},
            {"actor_id": OTHER_OWNER},
            {"owner_binding_sha256": "7" * 64},
            {"commit_sha": "7" * 40},
            {"tree_sha": "7" * 64},
            {"function_package_sha256": "7" * 64},
            {"plan_sha256": "7" * 64},
            {"target_binding_sha256": "7" * 64},
        ):
            with self.subTest(changes=changes):
                broker, state, _, _ = make_broker()
                with self.assertRaisesRegex(
                    LeaseBrokerError, "^LEASE_BROKER_TICKET_INVALID$"
                ):
                    broker.acquire(ticket=make_ticket(**changes), claims=CLAIMS)
                self.assertEqual(state.acquire_commands, [])


class StateMachineTests(unittest.TestCase):
    def test_port_surface_has_only_acquire_assert_release_operations(self) -> None:
        methods = {
            name
            for name, value in inspect.getmembers(
                AtomicLeaseStateMachinePort, inspect.isfunction
            )
            if not name.startswith("_")
        }
        self.assertEqual(methods, {"acquire", "assert_held", "release"})
        source = inspect.getsource(AtomicLeaseStateMachinePort)
        for forbidden in ("break_lease", "change", "renew", "overwrite", "delete"):
            self.assertNotIn(f"def {forbidden}", source)

    def test_request_facing_methods_have_no_storage_or_http_controls(self) -> None:
        forbidden = {"url", "account", "container", "blob", "header", "method", "lease_id"}
        for name in ("acquire", "assert_held", "release"):
            parameters = set(
                inspect.signature(getattr(AzurePerformanceLeaseBroker, name)).parameters
            )
            self.assertEqual(parameters, {"self", "ticket", "claims"})
            self.assertTrue(parameters.isdisjoint(forbidden))

    def test_fixed_binding_is_loaded_once_and_pinned(self) -> None:
        provider = BindingProvider()
        broker, state, _, _ = make_broker(provider=provider)
        first = broker.acquire(ticket=make_ticket(), claims=CLAIMS)
        provider.load = lambda: AttestedStorageBinding(  # type: ignore[method-assign]
            "changed", b"b" * 64
        )
        second = broker.assert_held(
            ticket=make_ticket(operation="assert", nonce=_b64(b"a" * 32)),
            claims=CLAIMS,
        )
        self.assertEqual(provider.calls, 1)
        self.assertEqual(first.binding_fingerprint, second.binding_fingerprint)
        self.assertEqual(
            state.acquire_commands[0].binding_fingerprint,
            state.assert_commands[0].binding_fingerprint,
        )

    def test_private_lease_id_is_random_well_formed_and_never_receipted(self) -> None:
        broker, state, _, _ = make_broker()
        receipt = broker.acquire(ticket=make_ticket(), claims=CLAIMS)
        lease_id = state.acquire_commands[0].private_lease_id
        decoded = base64.urlsafe_b64decode(lease_id + "=" * (-len(lease_id) % 4))
        self.assertEqual(len(decoded), 32)
        self.assertNotIn(lease_id, repr(receipt))
        self.assertNotIn(lease_id, json.dumps(receipt.as_dict()))
        self.assertNotIn("lease_id", receipt.as_dict())

    def test_lifecycle_is_idempotent_and_redacted(self) -> None:
        broker, state, _, _ = make_broker()
        acquire_ticket = make_ticket()
        assert_ticket = make_ticket(operation="assert", nonce=_b64(b"a" * 32))
        release_ticket = make_ticket(operation="release", nonce=_b64(b"r" * 32))
        acquired = broker.acquire(ticket=acquire_ticket, claims=CLAIMS)
        repeated = broker.acquire(ticket=acquire_ticket, claims=CLAIMS)
        held = broker.assert_held(ticket=assert_ticket, claims=CLAIMS)
        released = broker.release(ticket=release_ticket, claims=CLAIMS)
        rereleased = broker.release(ticket=release_ticket, claims=CLAIMS)

        self.assertEqual(acquired.outcome, "ACQUIRED")
        self.assertEqual(repeated.outcome, "ALREADY_ACQUIRED")
        self.assertEqual(held.outcome, "HELD")
        self.assertEqual(released.outcome, "RELEASED")
        self.assertEqual(rereleased.outcome, "ALREADY_RELEASED")
        run_fingerprints = {
            state.acquire_commands[0].run_fingerprint,
            state.assert_commands[0].run_fingerprint,
            state.release_commands[0].run_fingerprint,
        }
        self.assertEqual(len(run_fingerprints), 1)
        self.assertTrue(all(len(value) == 64 for value in run_fingerprints))
        self.assertEqual(
            len(
                {
                    state.acquire_commands[0].operation_id,
                    state.assert_commands[0].operation_id,
                    state.release_commands[0].operation_id,
                }
            ),
            3,
        )
        allowed = {
            "binding_fingerprint",
            "operation",
            "outcome",
            "retry",
            "schema_version",
            "ticket_fingerprint",
        }
        for receipt in (acquired, repeated, held, released, rereleased):
            self.assertEqual(set(receipt.as_dict()), allowed)
            serialized = json.dumps(receipt.as_dict())
            for secret in (
                OWNER, ROLE, SCOPE, ISSUER, AUDIENCE, BINDING, ACTOR,
                OWNER_BINDING, COMMIT, TREE, FUNCTION_PACKAGE, PLAN, TARGET,
            ):
                self.assertNotIn(secret, serialized)

    def test_crash_and_retry_outcomes_have_explicit_directives(self) -> None:
        acquire_cases = {
            AcquireOutcome.BUSY: RetryDirective.RETRY_SAME_TICKET,
            AcquireOutcome.RETRYABLE_FAILURE: RetryDirective.RETRY_SAME_TICKET,
            AcquireOutcome.INDETERMINATE_AFTER_CRASH: RetryDirective.ASSERT_BEFORE_RETRY,
            AcquireOutcome.REPLAY_REJECTED: RetryDirective.DO_NOT_RETRY,
        }
        for outcome, expected in acquire_cases.items():
            with self.subTest(acquire=outcome):
                broker, _, _, _ = make_broker(FixedOutcomeStateMachine(outcome))
                self.assertEqual(
                    broker.acquire(ticket=make_ticket(), claims=CLAIMS).retry,
                    expected,
                )

        broker, _, _, _ = make_broker(
            FixedOutcomeStateMachine(AssertOutcome.INDETERMINATE_AFTER_CRASH)
        )
        self.assertEqual(
            broker.assert_held(
                ticket=make_ticket(operation="assert"), claims=CLAIMS
            ).retry,
            RetryDirective.RETRY_SAME_TICKET,
        )
        broker, _, _, _ = make_broker(
            FixedOutcomeStateMachine(ReleaseOutcome.INDETERMINATE_AFTER_CRASH)
        )
        self.assertEqual(
            broker.release(
                ticket=make_ticket(operation="release"), claims=CLAIMS
            ).retry,
            RetryDirective.ASSERT_BEFORE_RETRY,
        )

    def test_state_errors_and_wrong_outcome_types_are_redacted(self) -> None:
        class ExplodingState(FixedOutcomeStateMachine):
            def acquire(self, command: LeaseAcquireCommand, /) -> Any:
                raise RuntimeError("https://account.blob.core.windows.net/private")

        broker, _, _, _ = make_broker(ExplodingState(None))
        with self.assertRaisesRegex(
            LeaseBrokerError, "^LEASE_BROKER_STATE_UNAVAILABLE$"
        ):
            broker.acquire(ticket=make_ticket(), claims=CLAIMS)

        broker, _, _, _ = make_broker(FixedOutcomeStateMachine("ACQUIRED"))
        with self.assertRaisesRegex(
            LeaseBrokerError, "^LEASE_BROKER_STATE_RESPONSE_INVALID$"
        ):
            broker.acquire(ticket=make_ticket(), claims=CLAIMS)


class ReplayAndConcurrencyTests(unittest.TestCase):
    def test_same_nonce_on_a_different_valid_ticket_is_rejected_as_replay(self) -> None:
        broker, state, _, _ = make_broker()
        first = make_ticket()
        second = make_ticket(issued_at=NOW - 1, expires_at=NOW + 44)
        self.assertEqual(broker.acquire(ticket=first, claims=CLAIMS).outcome, "ACQUIRED")
        replay = broker.acquire(ticket=second, claims=CLAIMS)
        self.assertEqual(replay.outcome, "REPLAY_REJECTED")
        self.assertEqual(replay.retry, RetryDirective.DO_NOT_RETRY)
        self.assertEqual(len(state._by_nonce), 1)

    def test_concurrent_replay_creates_exactly_one_lease(self) -> None:
        broker, state, _, _ = make_broker()
        ticket = make_ticket()
        workers = 64
        barrier = threading.Barrier(workers)

        def acquire_once(_: int) -> str:
            barrier.wait()
            return broker.acquire(ticket=ticket, claims=CLAIMS).outcome

        with ThreadPoolExecutor(max_workers=workers) as executor:
            outcomes = list(executor.map(acquire_once, range(workers)))

        self.assertEqual(outcomes.count("ACQUIRED"), 1)
        self.assertEqual(outcomes.count("ALREADY_ACQUIRED"), workers - 1)
        self.assertEqual(len(state._by_nonce), 1)
        private_ids = [command.private_lease_id for command in state.acquire_commands]
        self.assertEqual(len(private_ids), len(set(private_ids)))
        self.assertTrue(
            all(
                len(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))) == 32
                for value in private_ids
            )
        )

    def test_parallel_distinct_nonces_each_acquire_once(self) -> None:
        broker, state, _, _ = make_broker()
        tickets = [make_ticket(nonce=_b64(index.to_bytes(32, "big"))) for index in range(1, 65)]
        with ThreadPoolExecutor(max_workers=16) as executor:
            outcomes = list(
                executor.map(
                    lambda ticket: broker.acquire(ticket=ticket, claims=CLAIMS).outcome,
                    tickets,
                )
            )
        self.assertEqual(outcomes.count("ACQUIRED"), 1)
        self.assertEqual(outcomes.count("BUSY"), len(tickets) - 1)
        self.assertEqual(len(state._by_nonce), len(tickets))


class ModelTests(unittest.TestCase):
    def test_commands_contain_no_storage_transport_fields(self) -> None:
        names = {field.name for field in fields(LeaseAcquireCommand)} | {
            field.name for field in fields(LeaseCommand)
        }
        forbidden_fragments = ("url", "account", "container", "blob", "header", "method")
        self.assertFalse(
            [name for name in names if any(fragment in name for fragment in forbidden_fragments)]
        )

    def test_attested_binding_rejects_unbounded_or_weak_values(self) -> None:
        for binding_id, attestation in (
            ("https://account.blob.core.windows.net/container/blob", b"a" * 64),
            ("valid", b"short"),
            ("", b"a" * 64),
        ):
            with self.subTest(binding_id=binding_id):
                with self.assertRaisesRegex(ValueError, "LEASE_BROKER_BINDING_INVALID"):
                    AttestedStorageBinding(binding_id, attestation)


if __name__ == "__main__":
    unittest.main()
