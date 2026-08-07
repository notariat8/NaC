from __future__ import annotations

import base64
from contextlib import nullcontext
import inspect
import json
import threading
import unittest
from uuid import UUID

from nac_bff.azure_performance_authorization import (
    BLOB_LEASE_ACQUIRE,
    BLOB_LEASE_ASSERT_HELD,
    BLOB_LEASE_RELEASE,
    PerformanceLiveAuthorizationError,
    _mint_verified_performance_authority,
)
from nac_bff.azure_performance_lease_broker import RECEIPT_VERSION
from nac_bff.azure_performance_lease_broker_client import (
    BrokeredAzureBlobLeaseAdapter,
    BrokeredAzureBlobLeaseError,
    _submitted_ticket_fingerprint,
)


TARGET = "1" * 64
LEASE_BINDING = "2" * 64
BROKER_BINDING = "3" * 64
LOCAL_ID = UUID("11111111-1111-4111-8111-111111111111")


def _capability(*, target: str = TARGET, lease_binding: str = LEASE_BINDING):
    return _mint_verified_performance_authority(
        bindings={},
        target_binding_sha256=target,
        action_bindings={
            BLOB_LEASE_ACQUIRE: (lease_binding, 16),
            BLOB_LEASE_ASSERT_HELD: (lease_binding, 16),
            BLOB_LEASE_RELEASE: (lease_binding, 16),
        },
        usage_ledger=None,
    ).capability


class _Response:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.status = status
        self._body = body

    def read(self, size: int) -> bytes:
        return self._body[:size]


class _Opener:
    def __init__(self) -> None:
        self.requests: list[tuple[object, float]] = []
        self.response = _Response(b"{}")

    def open(self, request: object, *, timeout: float):
        self.requests.append((request, timeout))
        return self.response


def _ticket(operation: str) -> dict:
    return {
        "key_id": "test-key",
        "payload": {
            "actions": [operation],
            "actor_id": "33333333-3333-4333-8333-333333333333",
            "audience": "api://nac-test",
            "blob_path": f"locks/{TARGET}.lock",
            "commit_sha": "a" * 40,
            "expires_at": 2,
            "function_package_sha256": "b" * 64,
            "issued_at": 1,
            "issuer": "nac-test",
            "nonce": "c" * 43,
            "owner_binding_sha256": "d" * 64,
            "owner_subject": "33333333-3333-4333-8333-333333333333",
            "plan_sha256": "e" * 64,
            "role": "Performance.Lease",
            "scope": "nac.performance.lease",
            "storage_binding": "test-storage",
            "target_binding_sha256": TARGET,
            "tenant_id": "22222222-2222-4222-8222-222222222222",
            "tree_sha": "f" * 40,
            "version": "nac.azure-performance-lease-activation-ticket/v1",
        },
        "signature": base64.urlsafe_b64encode(b"s" * 32)
        .rstrip(b"=")
        .decode("ascii"),
    }


def _receipt(
    operation: str,
    outcome: str,
    *,
    retry: str = "NONE",
    ticket_fingerprint: str | None = None,
) -> bytes:
    return json.dumps(
        {
            "binding_fingerprint": BROKER_BINDING,
            "operation": "assert_held" if operation == "assert" else operation,
            "outcome": outcome,
            "retry": retry,
            "schema_version": RECEIPT_VERSION,
            "ticket_fingerprint": (
                ticket_fingerprint
                or _submitted_ticket_fingerprint(_ticket(operation))
            ),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


class BrokeredAzureBlobLeaseAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.opener = _Opener()
        self.ticket_calls: list[str] = []
        self.token_calls = 0
        self.capability = _capability()

        def ticket(operation: str):
            self.ticket_calls.append(operation)
            return _ticket(operation)

        def token():
            self.token_calls += 1
            return "x" * 64

        self.adapter = BrokeredAzureBlobLeaseAdapter(
            broker_base_url="https://fn-nac-bff.example.test",
            token_provider=token,
            ticket_provider=ticket,
            target_binding_sha256=TARGET,
            lease_binding_sha256=LEASE_BINDING,
            infrastructure_safety_evidence_sha256="5" * 64,
            lease_acquisition_safety_evidence_sha256="6" * 64,
            expected_broker_binding_fingerprint=BROKER_BINDING,
            opener=self.opener,
        )

    def test_only_fixed_broker_routes_are_called_and_local_id_is_not_sent(self) -> None:
        for operation, method, outcome, state in (
            ("acquire", self.adapter.acquire, "ACQUIRED", "HELD"),
            ("assert", self.adapter.assert_held, "HELD", "HELD"),
            ("release", self.adapter.release, "RELEASED", "RELEASED"),
        ):
            with self.subTest(operation=operation):
                self.opener.response = _Response(_receipt(operation, outcome))
                receipt = method(LOCAL_ID, self.capability)
                request, timeout = self.opener.requests[-1]
                self.assertEqual(
                    request.full_url,
                    f"https://fn-nac-bff.example.test/v1/internal/performance-lease/{operation}",
                )
                self.assertEqual(request.method, "POST")
                self.assertEqual(timeout, 10.0)
                self.assertNotIn(str(LOCAL_ID), request.data.decode("ascii"))
                self.assertNotIn("blob.core.windows.net", request.full_url)
                self.assertEqual(receipt.lifecycle_state, state)
                self.assertEqual(receipt.target_binding_sha256, TARGET)
        self.assertEqual(self.ticket_calls, ["acquire", "assert", "release"])
        self.assertEqual(self.token_calls, 3)

    def test_request_surface_has_no_storage_controls(self) -> None:
        parameters = set(inspect.signature(BrokeredAzureBlobLeaseAdapter).parameters)
        for forbidden in (
            "storage_url",
            "storage_account",
            "container",
            "blob",
            "lease_id",
            "headers",
            "method",
        ):
            self.assertNotIn(forbidden, parameters)
        source = inspect.getsource(BrokeredAzureBlobLeaseAdapter)
        self.assertNotIn("https://storage.azure.com/.default", source)
        self.assertNotIn("blob.core.windows.net", source)
        self.assertNotIn("x-ms-lease-id", source)
        self.assertNotIn("break", source.lower())

    def test_non_success_and_malformed_responses_fail_closed(self) -> None:
        cases = (
            _Response(_receipt("acquire", "BUSY")),
            _Response(b'{"provider":"secret"}'),
            _Response(_receipt("acquire", "ACQUIRED"), status=500),
            _Response(b"x" * 8_193),
        )
        for response in cases:
            with self.subTest(status=response.status, size=len(response._body)):
                self.opener.response = response
                with self.assertRaises(BrokeredAzureBlobLeaseError) as error:
                    self.adapter.acquire(LOCAL_ID, self.capability)
                self.assertNotIn("provider", str(error.exception))
                self.assertNotIn("secret", str(error.exception))

    def test_receipt_for_different_ticket_fails_closed(self) -> None:
        self.opener.response = _Response(
            _receipt(
                "acquire",
                "ACQUIRED",
                ticket_fingerprint="9" * 64,
            )
        )

        with self.assertRaisesRegex(
            BrokeredAzureBlobLeaseError,
            "^BROKERED_LEASE_TICKET_MISMATCH$",
        ):
            self.adapter.acquire(LOCAL_ID, self.capability)

    def test_execution_fence_rejects_concurrent_local_runs(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        errors: list[str] = []

        def hold() -> None:
            with self.adapter.execution_fence():
                entered.set()
                release.wait(2)

        thread = threading.Thread(target=hold)
        thread.start()
        entered.wait(2)
        with self.assertRaisesRegex(
            BrokeredAzureBlobLeaseError, "^BROKERED_LEASE_RUN_BUSY$"
        ):
            with self.adapter.execution_fence():
                errors.append("entered")
        release.set()
        thread.join(2)
        self.assertEqual(errors, [])
        with self.adapter.execution_fence():
            context = nullcontext()
        self.assertIsNotNone(context)

    def test_retry_reuses_exact_ticket_until_terminal_receipt(self) -> None:
        self.opener.response = _Response(
            _receipt("acquire", "RETRYABLE_FAILURE", retry="RETRY_SAME_TICKET")
        )
        with self.assertRaisesRegex(
            BrokeredAzureBlobLeaseError,
            "^BROKERED_LEASE_NOT_AVAILABLE$",
        ):
            self.adapter.acquire(LOCAL_ID, self.capability)
        first_body = self.opener.requests[-1][0].data

        with self.assertRaisesRegex(
            BrokeredAzureBlobLeaseError,
            "^BROKERED_LEASE_NOT_AVAILABLE$",
        ):
            self.adapter.acquire(LOCAL_ID, self.capability)
        self.assertEqual(self.opener.requests[-1][0].data, first_body)
        self.assertEqual(self.ticket_calls, ["acquire"])

        self.opener.response = _Response(_receipt("acquire", "ACQUIRED"))
        self.adapter.acquire(LOCAL_ID, self.capability)
        self.assertEqual(self.opener.requests[-1][0].data, first_body)
        self.assertEqual(self.ticket_calls, ["acquire"])

        self.adapter.acquire(LOCAL_ID, self.capability)
        self.assertEqual(self.ticket_calls, ["acquire", "acquire"])

    def test_capability_is_required_and_bound_before_ticket_token_or_network(self) -> None:
        for capability in (None, _capability(target="7" * 64)):
            with self.subTest(capability=capability is not None):
                with self.assertRaises(PerformanceLiveAuthorizationError):
                    self.adapter.acquire(LOCAL_ID, capability)
                self.assertEqual(self.ticket_calls, [])
                self.assertEqual(self.token_calls, 0)
                self.assertEqual(self.opener.requests, [])

    def test_configuration_is_https_fixed_root_and_digest_bound(self) -> None:
        for url in (
            "http://fn.example.test",
            "https://fn.example.test/path",
            "https://user@fn.example.test",
            "https://fn.example.test?url=https://storage.invalid",
        ):
            with self.subTest(url=url):
                with self.assertRaisesRegex(
                    ValueError, "^BROKERED_LEASE_CONFIGURATION_INVALID$"
                ):
                    BrokeredAzureBlobLeaseAdapter(
                        broker_base_url=url,
                        token_provider=lambda: "x" * 64,
                        ticket_provider=lambda _: {},
                        target_binding_sha256=TARGET,
                        lease_binding_sha256=LEASE_BINDING,
                        infrastructure_safety_evidence_sha256="5" * 64,
                        lease_acquisition_safety_evidence_sha256="6" * 64,
                        expected_broker_binding_fingerprint=BROKER_BINDING,
                        opener=self.opener,
                    )


if __name__ == "__main__":
    unittest.main()
