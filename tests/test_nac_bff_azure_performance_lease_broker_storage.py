from __future__ import annotations

import base64
import inspect
import json
import threading
import unittest
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.request import Request
from uuid import UUID

from nac_bff.azure_performance_lease_broker import (
    AcquireOutcome,
    AssertOutcome,
    AtomicLeaseStateMachinePort,
    LeaseAcquireCommand,
    LeaseCommand,
    ReleaseOutcome,
)
from nac_bff.azure_performance_lease_broker_storage import (
    AZURE_BLOB_API_VERSION,
    AZURE_STORAGE_SCOPE,
    AzureBlobAtomicLeaseStateMachine,
    AzureBlobLeaseStateMachineError,
)


BLOB_URL = "https://naccoord.blob.core.windows.net/leases/exact.lock"
BLOB_PATH = "/leases/exact.lock"
NOW = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
OPERATION = "1" * 64
NONCE = "2" * 64
BINDING = "3" * 64
OTHER_OPERATION = "4" * 64
OTHER_NONCE = "5" * 64
PRIVATE_ID = base64.urlsafe_b64encode(bytes(range(32))).rstrip(b"=").decode("ascii")
OTHER_PRIVATE_ID = base64.urlsafe_b64encode(bytes(range(32, 64))).rstrip(b"=").decode(
    "ascii"
)
AZURE_LEASE_ID = str(UUID(bytes=bytes(range(16))))


def acquire_command(
    *,
    operation_id: str = OPERATION,
    nonce_key: str = NONCE,
    binding_fingerprint: str = BINDING,
    private_lease_id: str = PRIVATE_ID,
) -> LeaseAcquireCommand:
    return LeaseAcquireCommand(
        operation_id=operation_id,
        nonce_key=nonce_key,
        binding_fingerprint=binding_fingerprint,
        private_lease_id=private_lease_id,
    )


def command(
    *,
    operation_id: str = OPERATION,
    nonce_key: str = NONCE,
    binding_fingerprint: str = BINDING,
) -> LeaseCommand:
    return LeaseCommand(
        operation_id=operation_id,
        nonce_key=nonce_key,
        binding_fingerprint=binding_fingerprint,
    )


class TokenProvider:
    def __init__(self, token: object = "managed-identity-token") -> None:
        self.token = token
        self.calls: list[str] = []

    def get_token(self, scope: str) -> object:
        self.calls.append(scope)
        if isinstance(self.token, BaseException):
            raise self.token
        if isinstance(self.token, str):
            return type("AccessToken", (), {"token": self.token})()
        return self.token


class HeaderBag:
    def __init__(self, values: Mapping[str, str] | list[tuple[str, str]]) -> None:
        self._values = list(values.items()) if isinstance(values, Mapping) else values

    def items(self) -> list[tuple[str, str]]:
        return list(self._values)


class Response:
    def __init__(
        self,
        status: int,
        headers: Mapping[str, str] | list[tuple[str, str]],
        url: str,
        body: bytes = b"",
    ) -> None:
        self.status = status
        self.headers = HeaderBag(headers)
        self._url = url
        self._body = body

    def geturl(self) -> str:
        return self._url

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None


@dataclass(frozen=True)
class CapturedRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes | None


class FakeBlobOpener:
    """Small, locked Blob REST model with post-commit crash injection."""

    def __init__(self) -> None:
        self.requests: list[CapturedRequest] = []
        self.metadata: dict[str, str] | None = None
        self.etag_generation = 0
        self.lease_id: str | None = None
        self.after_failures: set[int] = set()
        self.before_failures: set[int] = set()
        self.response_body = b""
        self.extra_headers: list[tuple[str, str]] = []
        self.response_url: str | None = None
        self._lock = threading.Lock()

    @property
    def etag(self) -> str:
        return f'"etag-{self.etag_generation}"'

    def open(self, request: Request, timeout: float) -> Response:
        self.assert_timeout(timeout)
        captured = CapturedRequest(
            method=request.get_method(),
            url=request.full_url,
            headers={name.lower(): value for name, value in request.header_items()},
            body=request.data,
        )
        with self._lock:
            self.requests.append(captured)
            number = len(self.requests)
            if number in self.before_failures:
                raise RuntimeError(f"before transport secret {BLOB_URL}")
            result = self._handle(captured)
            if number in self.after_failures:
                raise RuntimeError(f"after transport token managed-identity-token")
            return result

    @staticmethod
    def assert_timeout(timeout: float) -> None:
        if timeout != 10:
            raise AssertionError(timeout)

    def _handle(self, request: CapturedRequest) -> Response:
        parsed = urllib.parse.urlsplit(request.url)
        query = urllib.parse.parse_qs(parsed.query)
        headers = request.headers
        if parsed.path != BLOB_PATH:
            return self._response(404, {}, request.url)
        if request.method == "PUT" and not query:
            if self.metadata is not None:
                return self._response(
                    412, {"x-ms-error-code": "ConditionNotMet"}, request.url
                )
            self._assert_common(request)
            if (
                headers.get("if-none-match") != "*"
                or headers.get("x-ms-blob-type") != "BlockBlob"
                or headers.get("content-length") != "0"
                or request.body != b""
            ):
                raise AssertionError("invalid conditional BlockBlob create")
            self.metadata = self._request_metadata(headers)
            self.etag_generation += 1
            return self._response(201, {"etag": self.etag}, request.url)
        if request.method == "PUT" and query == {"comp": ["metadata"]}:
            self._assert_common(request)
            if self.metadata is None:
                return self._response(404, {}, request.url)
            if headers.get("if-match") != self.etag:
                return self._response(
                    412, {"x-ms-error-code": "ConditionNotMet"}, request.url
                )
            supplied_lease = headers.get("x-ms-lease-id")
            if self.lease_id is not None and supplied_lease != self.lease_id:
                return self._response(
                    412,
                    {"x-ms-error-code": "LeaseIdMismatchWithBlobOperation"},
                    request.url,
                )
            if request.body != b"" or headers.get("content-length") != "0":
                raise AssertionError("metadata body must be empty")
            self.metadata = self._request_metadata(headers)
            self.etag_generation += 1
            return self._response(200, {"etag": self.etag}, request.url)
        if request.method == "PUT" and query == {"comp": ["lease"]}:
            self._assert_common(request)
            if request.body != b"" or headers.get("content-length") != "0":
                raise AssertionError("lease body must be empty")
            action = headers.get("x-ms-lease-action")
            if action == "acquire":
                if self.lease_id is not None:
                    return self._response(
                        409,
                        {"x-ms-error-code": "LeaseAlreadyPresent"},
                        request.url,
                    )
                if headers.get("x-ms-lease-duration") != "-1":
                    raise AssertionError("lease must be infinite")
                self.lease_id = headers.get("x-ms-proposed-lease-id")
                return self._response(
                    201,
                    {"etag": self.etag, "x-ms-lease-id": self.lease_id or ""},
                    request.url,
                )
            if action == "release":
                if self.lease_id is None:
                    return self._response(
                        412,
                        {"x-ms-error-code": "LeaseNotPresentWithLeaseOperation"},
                        request.url,
                    )
                if headers.get("x-ms-lease-id") != self.lease_id:
                    return self._response(
                        412,
                        {"x-ms-error-code": "LeaseIdMismatchWithLeaseOperation"},
                        request.url,
                    )
                self.lease_id = None
                return self._response(200, {"etag": self.etag}, request.url)
            raise AssertionError(f"forbidden lease action: {action}")
        if request.method == "HEAD" and not query:
            self._assert_common(request)
            if request.body is not None:
                raise AssertionError("HEAD has a body")
            if self.metadata is None:
                return self._response(404, {}, request.url)
            if headers.get("if-match") not in {None, self.etag}:
                return self._response(
                    412, {"x-ms-error-code": "ConditionNotMet"}, request.url
                )
            supplied = headers.get("x-ms-lease-id")
            if supplied is not None:
                if self.lease_id is None:
                    return self._response(
                        412,
                        {"x-ms-error-code": "LeaseNotPresentWithBlobOperation"},
                        request.url,
                    )
                if supplied != self.lease_id:
                    return self._response(
                        412,
                        {"x-ms-error-code": "LeaseIdMismatchWithBlobOperation"},
                        request.url,
                    )
            properties = {"etag": self.etag, **self.metadata}
            if self.lease_id is not None:
                properties.update(
                    {
                        "x-ms-lease-state": "leased",
                        "x-ms-lease-status": "locked",
                        "x-ms-lease-duration": "infinite",
                    }
                )
            else:
                properties.update(
                    {
                        "x-ms-lease-state": "available",
                        "x-ms-lease-status": "unlocked",
                    }
                )
            return self._response(200, properties, request.url)
        raise AssertionError(f"forbidden request: {request}")

    def _response(
        self, status: int, headers: Mapping[str, str], url: str
    ) -> Response:
        values = [("x-ms-version", AZURE_BLOB_API_VERSION), *headers.items()]
        values.extend(self.extra_headers)
        return Response(
            status,
            values,
            self.response_url or url,
            body=self.response_body,
        )

    @staticmethod
    def _request_metadata(headers: Mapping[str, str]) -> dict[str, str]:
        return {
            name: value
            for name, value in headers.items()
            if name.startswith("x-ms-meta-")
        }

    @staticmethod
    def _assert_common(request: CapturedRequest) -> None:
        headers = request.headers
        if headers.get("authorization") != "Bearer managed-identity-token":
            raise AssertionError("wrong authorization")
        if headers.get("x-ms-version") != AZURE_BLOB_API_VERSION:
            raise AssertionError("wrong API version")
        if "x-ms-date" not in headers:
            raise AssertionError("missing date")


def adapter(
    opener: FakeBlobOpener | None = None,
    provider: TokenProvider | None = None,
) -> tuple[AzureBlobAtomicLeaseStateMachine, FakeBlobOpener, TokenProvider]:
    selected_opener = opener or FakeBlobOpener()
    selected_provider = provider or TokenProvider()
    return (
        AzureBlobAtomicLeaseStateMachine(
            blob_url=BLOB_URL,
            expected_blob_path=BLOB_PATH,
            token_provider=selected_provider,
            opener=selected_opener,
            clock=lambda: NOW,
        ),
        selected_opener,
        selected_provider,
    )


class ConfigurationTests(unittest.TestCase):
    def test_adapter_implements_port_and_exposes_only_broker_commands(self) -> None:
        state_machine, _, _ = adapter()
        self.assertIsInstance(state_machine, AtomicLeaseStateMachinePort)
        for method in ("acquire", "assert_held", "release"):
            signature = inspect.signature(getattr(state_machine, method))
            parameters = list(signature.parameters.values())
            self.assertEqual([parameter.name for parameter in parameters], ["command"])
            self.assertEqual(parameters[0].kind, inspect.Parameter.POSITIONAL_ONLY)
            self.assertNotIn("url", str(signature))

    def test_target_is_exact_https_blob_host_and_expected_path(self) -> None:
        invalid = (
            ("http://naccoord.blob.core.windows.net/leases/exact.lock", BLOB_PATH),
            ("https://blob.core.windows.net/leases/exact.lock", BLOB_PATH),
            (
                "https://naccoord.blob.core.windows.net.evil.test/leases/exact.lock",
                BLOB_PATH,
            ),
            (
                "https://user@naccoord.blob.core.windows.net/leases/exact.lock",
                BLOB_PATH,
            ),
            ("https://naccoord.blob.core.windows.net:443/leases/exact.lock", BLOB_PATH),
            (BLOB_URL + "?comp=lease", BLOB_PATH),
            (BLOB_URL + "#fragment", BLOB_PATH),
            (BLOB_URL, "/leases/other.lock"),
            ("https://NACCOORD.blob.core.windows.net/leases/exact.lock", BLOB_PATH),
            (
                "https://naccoord.blob.core.windows.net/leases/../exact.lock",
                "/leases/../exact.lock",
            ),
        )
        for url, path in invalid:
            with self.subTest(url=url, path=path):
                with self.assertRaisesRegex(
                    AzureBlobLeaseStateMachineError,
                    "^AZURE_BLOB_BROKER_TARGET_INVALID$",
                ):
                    AzureBlobAtomicLeaseStateMachine(
                        blob_url=url,
                        expected_blob_path=path,
                        token_provider=TokenProvider(),
                        opener=FakeBlobOpener(),
                    )

    def test_invalid_commands_fail_without_token_or_http_access(self) -> None:
        state_machine, opener, provider = adapter()
        invalid = acquire_command(operation_id="not-a-digest")
        with self.assertRaisesRegex(
            AzureBlobLeaseStateMachineError,
            "^AZURE_BLOB_BROKER_COMMAND_INVALID$",
        ):
            state_machine.acquire(invalid)
        with self.assertRaisesRegex(
            AzureBlobLeaseStateMachineError,
            "^AZURE_BLOB_BROKER_COMMAND_INVALID$",
        ):
            state_machine.acquire(acquire_command(private_lease_id="not-private"))
        self.assertEqual(opener.requests, [])
        self.assertEqual(provider.calls, [])


class RequestSequenceTests(unittest.TestCase):
    def test_acquire_persists_exact_intent_before_one_lease_acquire(self) -> None:
        state_machine, opener, provider = adapter()

        outcome = state_machine.acquire(acquire_command())

        self.assertEqual(outcome, AcquireOutcome.ACQUIRED)
        self.assertEqual(
            [(item.method, item.url) for item in opener.requests],
            [
                ("PUT", BLOB_URL),
                ("PUT", BLOB_URL + "?comp=metadata"),
                ("PUT", BLOB_URL + "?comp=lease"),
                ("PUT", BLOB_URL + "?comp=metadata"),
            ],
        )
        initial = opener.requests[0]
        self.assertEqual(initial.headers["if-none-match"], "*")
        self.assertEqual(initial.headers["x-ms-blob-type"], "BlockBlob")
        self.assertEqual(initial.headers["content-length"], "0")
        self.assertEqual(initial.body, b"")
        self.assertEqual(
            {
                key: value
                for key, value in initial.headers.items()
                if key.startswith("x-ms-meta-")
            },
            {
                "x-ms-meta-schema_version": (
                    "nac.azure-performance-lease-broker-blob-state/v1"
                ),
                "x-ms-meta-lifecycle_state": "ACQUIRE_INTENT",
                "x-ms-meta-operation_id": OPERATION,
                "x-ms-meta-nonce_key": NONCE,
                "x-ms-meta-binding_fingerprint": BINDING,
                "x-ms-meta-private_lease_id": PRIVATE_ID,
            },
        )
        acquire = opener.requests[2]
        self.assertEqual(acquire.headers["x-ms-lease-action"], "acquire")
        self.assertEqual(acquire.headers["x-ms-lease-duration"], "-1")
        self.assertEqual(acquire.headers["x-ms-proposed-lease-id"], AZURE_LEASE_ID)
        self.assertNotIn("x-ms-lease-id", acquire.headers)
        self.assertEqual(opener.metadata["x-ms-meta-lifecycle_state"], "HELD")
        self.assertEqual(opener.metadata["x-ms-meta-private_lease_id"], PRIVATE_ID)
        self.assertEqual(provider.calls, [AZURE_STORAGE_SCOPE] * 4)
        self.assertNotIn(PRIVATE_ID, repr(outcome))

    def test_assert_and_release_use_only_the_persisted_private_lease(self) -> None:
        state_machine, opener, _ = adapter()
        self.assertEqual(
            state_machine.acquire(acquire_command()), AcquireOutcome.ACQUIRED
        )
        opener.requests.clear()

        self.assertEqual(state_machine.assert_held(command()), AssertOutcome.HELD)
        self.assertEqual(
            [(request.method, request.url) for request in opener.requests],
            [("HEAD", BLOB_URL), ("HEAD", BLOB_URL)],
        )
        self.assertNotIn("x-ms-lease-id", opener.requests[0].headers)
        self.assertEqual(opener.requests[1].headers["x-ms-lease-id"], AZURE_LEASE_ID)
        opener.requests.clear()

        self.assertEqual(state_machine.release(command()), ReleaseOutcome.RELEASED)
        self.assertEqual(
            [(request.method, request.url) for request in opener.requests],
            [
                ("HEAD", BLOB_URL),
                ("HEAD", BLOB_URL),
                ("PUT", BLOB_URL + "?comp=metadata"),
                ("PUT", BLOB_URL + "?comp=lease"),
                ("PUT", BLOB_URL + "?comp=metadata"),
            ],
        )
        release = opener.requests[3]
        self.assertEqual(release.headers["x-ms-lease-action"], "release")
        self.assertEqual(release.headers["x-ms-lease-id"], AZURE_LEASE_ID)
        self.assertNotIn("x-ms-proposed-lease-id", release.headers)
        self.assertIsNone(opener.lease_id)
        self.assertEqual(opener.metadata["x-ms-meta-lifecycle_state"], "RELEASED")

    def test_no_forbidden_transport_action_or_nonempty_body_is_sent(self) -> None:
        state_machine, opener, _ = adapter()
        state_machine.acquire(acquire_command())
        state_machine.assert_held(command())
        state_machine.release(command())
        state_machine.release(command())

        self.assertTrue(
            all(request.method in {"PUT", "HEAD"} for request in opener.requests)
        )
        self.assertTrue(all(request.body in {None, b""} for request in opener.requests))
        lease_actions = {
            request.headers.get("x-ms-lease-action")
            for request in opener.requests
            if "x-ms-lease-action" in request.headers
        }
        self.assertEqual(lease_actions, {"acquire", "release"})
        serialized = json.dumps([dict(request.headers) for request in opener.requests])
        for forbidden in ("break", "change", "renew", "delete"):
            self.assertNotIn(f'"x-ms-lease-action": "{forbidden}"', serialized)
        creates = [
            request
            for request in opener.requests
            if request.method == "PUT" and request.url == BLOB_URL
        ]
        self.assertEqual(len(creates), 1)
        self.assertEqual(creates[0].headers.get("if-none-match"), "*")


class ReplayAndConcurrencyTests(unittest.TestCase):
    def test_exact_retries_and_completed_release_are_idempotent(self) -> None:
        state_machine, _, _ = adapter()
        self.assertEqual(
            state_machine.acquire(acquire_command()), AcquireOutcome.ACQUIRED
        )
        self.assertEqual(
            state_machine.acquire(acquire_command(private_lease_id=OTHER_PRIVATE_ID)),
            AcquireOutcome.ALREADY_ACQUIRED,
        )
        self.assertEqual(state_machine.assert_held(command()), AssertOutcome.HELD)
        self.assertEqual(state_machine.release(command()), ReleaseOutcome.RELEASED)
        self.assertEqual(
            state_machine.release(command()), ReleaseOutcome.ALREADY_RELEASED
        )
        self.assertEqual(state_machine.assert_held(command()), AssertOutcome.LOST)

    def test_same_nonce_replays_and_other_nonce_is_busy(self) -> None:
        state_machine, opener, _ = adapter()
        self.assertEqual(
            state_machine.acquire(acquire_command()), AcquireOutcome.ACQUIRED
        )
        request_count = len(opener.requests)

        replay = state_machine.acquire(
            acquire_command(
                operation_id=OTHER_OPERATION,
                private_lease_id=OTHER_PRIVATE_ID,
            )
        )
        other = state_machine.acquire(
            acquire_command(nonce_key=OTHER_NONCE, private_lease_id=OTHER_PRIVATE_ID)
        )
        self.assertEqual(replay, AcquireOutcome.REPLAY_REJECTED)
        self.assertEqual(other, AcquireOutcome.BUSY)
        self.assertEqual(
            state_machine.assert_held(command(operation_id=OTHER_OPERATION)),
            AssertOutcome.REPLAY_REJECTED,
        )
        self.assertEqual(
            state_machine.release(command(operation_id=OTHER_OPERATION)),
            ReleaseOutcome.REPLAY_REJECTED,
        )
        self.assertGreater(len(opener.requests), request_count)
        lease_acquires = [
            request
            for request in opener.requests
            if request.headers.get("x-ms-lease-action") == "acquire"
        ]
        self.assertEqual(len(lease_acquires), 1)

    def test_concurrency_creates_exactly_one_remote_lease(self) -> None:
        opener = FakeBlobOpener()
        first, _, _ = adapter(opener)
        second, _, _ = adapter(opener)
        barrier = threading.Barrier(2)

        def run(
            machine: AzureBlobAtomicLeaseStateMachine,
            value: LeaseAcquireCommand,
        ) -> AcquireOutcome:
            barrier.wait()
            return machine.acquire(value)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(run, first, acquire_command()),
                executor.submit(
                    run,
                    second,
                    acquire_command(
                        operation_id=OTHER_OPERATION,
                        nonce_key=OTHER_NONCE,
                        private_lease_id=OTHER_PRIVATE_ID,
                    ),
                ),
            )
            outcomes = {future.result() for future in futures}
        self.assertIn(AcquireOutcome.ACQUIRED, outcomes)
        self.assertTrue(
            outcomes
            <= {
                AcquireOutcome.ACQUIRED,
                AcquireOutcome.BUSY,
                AcquireOutcome.INDETERMINATE_AFTER_CRASH,
            }
        )
        self.assertEqual(
            sum(
                request.headers.get("x-ms-lease-action") == "acquire"
                for request in opener.requests
            ),
            1,
        )


class CrashClassificationTests(unittest.TestCase):
    def test_acquire_crash_points_are_conservative_and_reconcilable(self) -> None:
        expected_retry = {
            1: AcquireOutcome.ALREADY_ACQUIRED,
            2: AcquireOutcome.INDETERMINATE_AFTER_CRASH,
            3: AcquireOutcome.ALREADY_ACQUIRED,
            4: AcquireOutcome.ALREADY_ACQUIRED,
        }
        for crash_after_request, retry_outcome in expected_retry.items():
            with self.subTest(crash_after_request=crash_after_request):
                opener = FakeBlobOpener()
                opener.after_failures.add(crash_after_request)
                state_machine, _, _ = adapter(opener)
                first = state_machine.acquire(acquire_command())
                self.assertEqual(first, AcquireOutcome.INDETERMINATE_AFTER_CRASH)
                opener.after_failures.clear()
                retry = state_machine.acquire(
                    acquire_command(private_lease_id=OTHER_PRIVATE_ID)
                )
                self.assertEqual(retry, retry_outcome)
                self.assertLessEqual(
                    sum(
                        request.headers.get("x-ms-lease-action") == "acquire"
                        for request in opener.requests
                    ),
                    1,
                )

    def test_assert_classifies_inflight_crash_and_read_failure(self) -> None:
        opener = FakeBlobOpener()
        opener.after_failures.add(2)
        state_machine, _, _ = adapter(opener)
        self.assertEqual(
            state_machine.acquire(acquire_command()),
            AcquireOutcome.INDETERMINATE_AFTER_CRASH,
        )
        opener.after_failures.clear()
        self.assertEqual(
            state_machine.assert_held(command()),
            AssertOutcome.INDETERMINATE_AFTER_CRASH,
        )
        opener.before_failures.add(len(opener.requests) + 1)
        self.assertEqual(
            state_machine.assert_held(command()), AssertOutcome.RETRYABLE_FAILURE
        )

    def test_release_crash_points_reconcile_without_unknown_lease_ids(self) -> None:
        # Release starts five requests after the four-request acquire sequence.
        cases = (
            (3, ReleaseOutcome.RELEASED),
            (4, ReleaseOutcome.ALREADY_RELEASED),
            (5, ReleaseOutcome.ALREADY_RELEASED),
        )
        for release_offset, expected in cases:
            with self.subTest(release_offset=release_offset):
                state_machine, opener, _ = adapter()
                self.assertEqual(
                    state_machine.acquire(acquire_command()),
                    AcquireOutcome.ACQUIRED,
                )
                opener.after_failures.add(len(opener.requests) + release_offset)
                self.assertEqual(
                    state_machine.release(command()),
                    ReleaseOutcome.INDETERMINATE_AFTER_CRASH,
                )
                opener.after_failures.clear()
                self.assertEqual(state_machine.release(command()), expected)
                release_ids = [
                    request.headers.get("x-ms-lease-id")
                    for request in opener.requests
                    if request.headers.get("x-ms-lease-action") == "release"
                ]
                self.assertTrue(release_ids)
                self.assertEqual(set(release_ids), {AZURE_LEASE_ID})


class BoundaryFailureTests(unittest.TestCase):
    def test_token_scope_is_fixed_and_failures_are_redacted(self) -> None:
        secret = "provider-secret-value"
        provider = TokenProvider(RuntimeError(secret + BLOB_URL))
        state_machine, opener, _ = adapter(provider=provider)

        outcome = state_machine.acquire(acquire_command())

        self.assertEqual(outcome, AcquireOutcome.RETRYABLE_FAILURE)
        self.assertEqual(provider.calls, [AZURE_STORAGE_SCOPE])
        self.assertEqual(opener.requests, [])
        self.assertNotIn(secret, repr(outcome))
        self.assertNotIn(BLOB_URL, repr(outcome))

    def test_token_appears_only_in_authorization_and_not_metadata_or_url(self) -> None:
        state_machine, opener, _ = adapter()
        state_machine.acquire(acquire_command())
        for request in opener.requests:
            token_headers = [
                name
                for name, value in request.headers.items()
                if "managed-identity-token" in value
            ]
            self.assertEqual(token_headers, ["authorization"])
            self.assertNotIn("managed-identity-token", request.url)
        self.assertNotIn("managed-identity-token", json.dumps(opener.metadata))

    def test_redirects_oversized_bodies_and_headers_are_stable_errors(self) -> None:
        cases: list[tuple[str, Any]] = [
            (
                "redirect",
                lambda opener: setattr(
                    opener, "response_url", "https://evil.test/"
                ),
            ),
            (
                "body",
                lambda opener: setattr(
                    opener, "response_body", b"x" * (16 * 1024 + 1)
                ),
            ),
            (
                "headers",
                lambda opener: opener.extra_headers.extend(
                    [(f"x-extra-{index}", "v") for index in range(65)]
                ),
            ),
            (
                "duplicate",
                lambda opener: opener.extra_headers.extend(
                    [("ETag", '"one"'), ("etag", '"two"')]
                ),
            ),
            (
                "location",
                lambda opener: opener.extra_headers.append(
                    ("Location", "https://evil.test/")
                ),
            ),
        ]
        for name, configure in cases:
            with self.subTest(name=name):
                opener = FakeBlobOpener()
                configure(opener)
                state_machine, _, _ = adapter(opener)
                with self.assertRaisesRegex(
                    AzureBlobLeaseStateMachineError,
                    "^AZURE_BLOB_BROKER_RESPONSE_INVALID$",
                ):
                    state_machine.acquire(acquire_command())

    def test_corrupt_metadata_is_rejected_without_echoing_private_values(self) -> None:
        state_machine, opener, _ = adapter()
        self.assertEqual(
            state_machine.acquire(acquire_command()), AcquireOutcome.ACQUIRED
        )
        opener.metadata["x-ms-meta-private_lease_id"] = "sensitive-corrupt-value"
        with self.assertRaisesRegex(
            AzureBlobLeaseStateMachineError,
            "^AZURE_BLOB_BROKER_STATE_INVALID$",
        ) as captured:
            state_machine.assert_held(command())
        self.assertNotIn("sensitive-corrupt-value", str(captured.exception))
        self.assertNotIn(PRIVATE_ID, str(captured.exception))


if __name__ == "__main__":
    unittest.main()
