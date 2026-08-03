from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from nac_bff.azure_performance_lease import (
    AzureBlobLeaseAdapter,
    AzureBlobLeaseBinding,
    AzureBlobLeaseError,
)


TARGET_SHA256 = "1" * 64
READ_IDENTITY_SHA256 = "2" * 64
WRITE_IDENTITY_SHA256 = "3" * 64
EXPECTED_ETAG = '"0x8DBABCDEF012345"'
LEASE_ID = UUID("12345678-1234-4abc-8def-1234567890ab")
OTHER_LEASE_ID = UUID("87654321-4321-4abc-8def-ba0987654321")
API_VERSION = "2023-11-03"
BASE_URL = (
    "https://nacperflease001.blob.core.windows.net/"
    f"nac-bff-performance-leases/locks/{TARGET_SHA256}.lock"
)
LEASE_URL = f"{BASE_URL}?comp=lease"
FIXED_DATE = "Mon, 03 Aug 2026 12:00:00 GMT"
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class _Response:
    def __init__(
        self,
        status: int,
        url: str,
        headers: dict[str, str],
        body: bytes = b"",
    ) -> None:
        self.status = status
        self._url = url
        self.headers = headers
        self._body = body
        self.closed = False

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return self._url

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            result, self._body = self._body, b""
            return result
        result, self._body = self._body[:size], self._body[size:]
        return result

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class _Opener:
    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[tuple[object, int]] = []

    def open(self, request: object, *, timeout: int) -> _Response:
        self.calls.append((request, timeout))
        if not self.outcomes:
            raise AssertionError("unexpected network call")
        outcome = self.outcomes.pop(0)
        if callable(outcome):
            outcome = outcome(request)
        if isinstance(outcome, BaseException):
            raise outcome
        assert isinstance(outcome, _Response)
        return outcome


class _TokenProvider:
    def __init__(self, token: str = "opaque-storage-token") -> None:
        self.token = token
        self.calls: list[dict[str, str]] = []

    def __call__(self, **kwargs: str) -> str:
        self.calls.append(kwargs)
        return self.token


def _binding(**updates: str) -> AzureBlobLeaseBinding:
    values = {
        "account_name": "nacperflease001",
        "bff_account_name": "nacbffdeploy001",
        "worm_account_name": "nacwormevidence001",
        "target_binding_sha256": TARGET_SHA256,
        "expected_etag": EXPECTED_ETAG,
        "read_identity_binding_sha256": READ_IDENTITY_SHA256,
        "write_identity_binding_sha256": WRITE_IDENTITY_SHA256,
    }
    values.update(updates)
    return AzureBlobLeaseBinding(**values)


def _success_headers(**updates: str) -> dict[str, str]:
    values = {"ETag": EXPECTED_ETAG, "x-ms-version": API_VERSION}
    values.update(updates)
    return values


def _head_held() -> _Response:
    return _Response(
        200,
        BASE_URL,
        _success_headers(
            **{
                "x-ms-lease-duration": "infinite",
                "x-ms-lease-state": "leased",
                "x-ms-lease-status": "locked",
            }
        ),
    )


def _head_not_present() -> _Response:
    return _Response(
        412,
        BASE_URL,
        {"x-ms-error-code": "LeaseNotPresentWithBlobOperation"},
    )


def _acquired() -> _Response:
    return _Response(
        201,
        LEASE_URL,
        _success_headers(**{"x-ms-lease-id": str(LEASE_ID)}),
    )


def _released() -> _Response:
    return _Response(200, LEASE_URL, _success_headers())


def _request_headers(request: object) -> dict[str, str]:
    return {
        name.lower(): value
        for name, value in getattr(request, "header_items")()
    }


class AzurePerformanceLeaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state_path = Path(self.temporary.name) / "lease-state.json"
        self.clock = lambda: datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)

    def adapter(
        self,
        opener: _Opener,
        *,
        token_provider: object | None = None,
        binding: AzureBlobLeaseBinding | None = None,
    ) -> tuple[AzureBlobLeaseAdapter, object]:
        provider = token_provider or _TokenProvider()
        return (
            AzureBlobLeaseAdapter(
                binding=binding or _binding(),
                state_path=self.state_path,
                token_provider=provider,
                opener=opener,
                clock=self.clock,
            ),
            provider,
        )

    def acquire_held(self) -> None:
        adapter, _ = self.adapter(_Opener(_acquired()))
        adapter.acquire(LEASE_ID)

    def state_payload(self) -> dict[str, object]:
        document = json.loads(self.state_path.read_text(encoding="ascii"))
        return document["payload"]

    def test_binding_is_fixed_to_dedicated_account_and_safe_values(self) -> None:
        binding = _binding()
        self.assertEqual(binding.api_version, API_VERSION)
        self.assertEqual(binding.container_name, "nac-bff-performance-leases")
        self.assertEqual(binding.token_audience, "https://storage.azure.com/")

        for field, value in (
            ("account_name", "nacbffdeploy001"),
            ("account_name", "nacwormevidence001"),
            ("account_name", "Bad-Account"),
            ("target_binding_sha256", "not-a-hash"),
            ("read_identity_binding_sha256", "not-a-hash"),
            ("write_identity_binding_sha256", "not-a-hash"),
            ("expected_etag", "*"),
            ("expected_etag", 'W/"weak"'),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(
                    ValueError, r"^AZURE_BLOB_LEASE_BINDING_INVALID$"
                ):
                    _binding(**{field: value})

    def test_acquire_is_exact_conditional_put_and_persists_held(self) -> None:
        opener = _Opener(_acquired())
        adapter, provider = self.adapter(opener)

        receipt = adapter.acquire(LEASE_ID)

        self.assertEqual(len(opener.calls), 1)
        request, timeout = opener.calls[0]
        self.assertEqual(getattr(request, "method"), "PUT")
        self.assertEqual(getattr(request, "full_url"), LEASE_URL)
        self.assertEqual(getattr(request, "data"), b"")
        self.assertEqual(timeout, 30)
        self.assertEqual(
            _request_headers(request),
            {
                "authorization": "Bearer opaque-storage-token",
                "content-length": "0",
                "if-match": EXPECTED_ETAG,
                "x-ms-client-request-id": str(LEASE_ID),
                "x-ms-date": FIXED_DATE,
                "x-ms-lease-action": "acquire",
                "x-ms-lease-duration": "-1",
                "x-ms-proposed-lease-id": str(LEASE_ID),
                "x-ms-version": API_VERSION,
            },
        )
        self.assertEqual(
            getattr(provider, "calls"),
            [
                {
                    "audience": "https://storage.azure.com/",
                    "identity_binding_sha256": WRITE_IDENTITY_SHA256,
                }
            ],
        )
        self.assertEqual(self.state_payload()["lifecycle_state"], "HELD")
        self.assertEqual(self.state_path.stat().st_mode & 0o777, 0o600)
        lock_path = self.state_path.with_name(f".{self.state_path.name}.lock")
        self.assertEqual(lock_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(set(asdict(receipt)), {
            "lease_binding_sha256",
            "target_binding_sha256",
            "lease_id_sha256",
            "read_identity_binding_sha256",
            "write_identity_binding_sha256",
            "lifecycle_state_sha256",
        })
        self.assertTrue(all(SHA256_RE.fullmatch(value) for value in asdict(receipt).values()))
        serialized = json.dumps(asdict(receipt), sort_keys=True)
        for secret in (
            str(LEASE_ID),
            "nacperflease001",
            EXPECTED_ETAG,
            "opaque-storage-token",
        ):
            self.assertNotIn(secret, serialized)

    def test_assert_held_is_exact_conditional_head_with_read_identity(self) -> None:
        self.acquire_held()
        opener = _Opener(_head_held())
        adapter, provider = self.adapter(opener)

        adapter.assert_held(LEASE_ID)

        self.assertEqual(len(opener.calls), 1)
        request, timeout = opener.calls[0]
        self.assertEqual(getattr(request, "method"), "HEAD")
        self.assertEqual(getattr(request, "full_url"), BASE_URL)
        self.assertIsNone(getattr(request, "data"))
        self.assertEqual(timeout, 30)
        self.assertEqual(
            _request_headers(request),
            {
                "authorization": "Bearer opaque-storage-token",
                "if-match": EXPECTED_ETAG,
                "x-ms-client-request-id": str(LEASE_ID),
                "x-ms-date": FIXED_DATE,
                "x-ms-lease-id": str(LEASE_ID),
                "x-ms-version": API_VERSION,
            },
        )
        self.assertEqual(
            getattr(provider, "calls"),
            [
                {
                    "audience": "https://storage.azure.com/",
                    "identity_binding_sha256": READ_IDENTITY_SHA256,
                }
            ],
        )

    def test_release_is_exact_put_then_conditional_head_and_durable(self) -> None:
        self.acquire_held()
        opener = _Opener(_released(), _head_not_present())
        adapter, provider = self.adapter(opener)

        receipt = adapter.release(LEASE_ID)

        self.assertEqual(len(opener.calls), 2)
        release_request = opener.calls[0][0]
        self.assertEqual(getattr(release_request, "method"), "PUT")
        self.assertEqual(getattr(release_request, "full_url"), LEASE_URL)
        self.assertEqual(
            _request_headers(release_request),
            {
                "authorization": "Bearer opaque-storage-token",
                "content-length": "0",
                "if-match": EXPECTED_ETAG,
                "x-ms-client-request-id": str(LEASE_ID),
                "x-ms-date": FIXED_DATE,
                "x-ms-lease-action": "release",
                "x-ms-lease-id": str(LEASE_ID),
                "x-ms-version": API_VERSION,
            },
        )
        head_request = opener.calls[1][0]
        self.assertEqual(getattr(head_request, "method"), "HEAD")
        self.assertEqual(getattr(head_request, "full_url"), BASE_URL)
        self.assertEqual(
            [call["identity_binding_sha256"] for call in getattr(provider, "calls")],
            [WRITE_IDENTITY_SHA256, READ_IDENTITY_SHA256],
        )
        self.assertEqual(self.state_payload()["lifecycle_state"], "RELEASED")
        self.assertTrue(all(SHA256_RE.fullmatch(value) for value in asdict(receipt).values()))

        adapter.release(LEASE_ID)
        self.assertEqual(len(opener.calls), 2)

    def test_crash_after_remote_acquire_resumes_by_head_without_reacquire(self) -> None:
        def acquired_then_crash(_: object) -> object:
            raise OSError("remote acquired; process lost response")

        first, _ = self.adapter(_Opener(acquired_then_crash))
        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_TRANSPORT_UNAVAILABLE$",
        ):
            first.acquire(LEASE_ID)
        self.assertEqual(
            self.state_payload()["lifecycle_state"], "ACQUIRE_INTENT"
        )

        opener = _Opener(_head_held())
        resumed, _ = self.adapter(opener)
        resumed.acquire(LEASE_ID)
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(getattr(opener.calls[0][0], "method"), "HEAD")
        self.assertEqual(self.state_payload()["lifecycle_state"], "HELD")

    def test_acquire_intent_never_reacquires_when_same_id_is_not_held(self) -> None:
        first, _ = self.adapter(_Opener(OSError("uncertain")))
        with self.assertRaises(AzureBlobLeaseError):
            first.acquire(LEASE_ID)

        opener = _Opener(_head_not_present())
        resumed, _ = self.adapter(opener)
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_NOT_HELD$"
        ):
            resumed.acquire(LEASE_ID)
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(getattr(opener.calls[0][0], "method"), "HEAD")

    def test_resume_requires_same_lease_id_before_network(self) -> None:
        self.acquire_held()
        opener = _Opener()
        adapter, _ = self.adapter(opener)
        for operation in (adapter.acquire, adapter.assert_held, adapter.release):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(
                    AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_ID_MISMATCH$"
                ):
                    operation(OTHER_LEASE_ID)
        self.assertEqual(opener.calls, [])

    def test_uncertain_release_that_is_already_absent_persists_released(self) -> None:
        self.acquire_held()
        first, _ = self.adapter(_Opener(OSError("release response lost")))
        with self.assertRaises(AzureBlobLeaseError):
            first.release(LEASE_ID)
        self.assertEqual(
            self.state_payload()["lifecycle_state"], "RELEASE_INTENT"
        )

        opener = _Opener(_head_not_present())
        resumed, _ = self.adapter(opener)
        resumed.release(LEASE_ID)
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(getattr(opener.calls[0][0], "method"), "HEAD")
        self.assertEqual(self.state_payload()["lifecycle_state"], "RELEASED")

    def test_uncertain_release_allows_one_reconciled_same_id_release(self) -> None:
        self.acquire_held()
        first, _ = self.adapter(_Opener(OSError("first release uncertain")))
        with self.assertRaises(AzureBlobLeaseError):
            first.release(LEASE_ID)

        opener = _Opener(_head_held(), _released(), _head_not_present())
        resumed, _ = self.adapter(opener)
        resumed.release(LEASE_ID)
        self.assertEqual(
            [getattr(call[0], "method") for call in opener.calls],
            ["HEAD", "PUT", "HEAD"],
        )
        self.assertEqual(self.state_payload()["release_attempts"], 2)
        self.assertEqual(self.state_payload()["lifecycle_state"], "RELEASED")

    def test_second_uncertain_release_cannot_issue_a_third_release(self) -> None:
        self.acquire_held()
        first, _ = self.adapter(_Opener(OSError("first release uncertain")))
        with self.assertRaises(AzureBlobLeaseError):
            first.release(LEASE_ID)

        second_opener = _Opener(_head_held(), OSError("second release uncertain"))
        second, _ = self.adapter(second_opener)
        with self.assertRaises(AzureBlobLeaseError):
            second.release(LEASE_ID)
        self.assertEqual(self.state_payload()["release_attempts"], 2)

        third_opener = _Opener(_head_held())
        third, _ = self.adapter(third_opener)
        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_RELEASE_RECONCILIATION_EXHAUSTED$",
        ):
            third.release(LEASE_ID)
        self.assertEqual(len(third_opener.calls), 1)
        self.assertEqual(getattr(third_opener.calls[0][0], "method"), "HEAD")

    def test_release_has_no_success_receipt_until_released_is_persisted(self) -> None:
        self.acquire_held()
        adapter, _ = self.adapter(_Opener(_released(), _head_not_present()))
        real_save = adapter._store.save

        def fail_released(payload: dict[str, object]) -> None:
            if payload["lifecycle_state"] == "RELEASED":
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_UNAVAILABLE")
            real_save(payload)

        adapter._store.save = fail_released
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_UNAVAILABLE$"
        ):
            adapter.release(LEASE_ID)
        self.assertEqual(
            self.state_payload()["lifecycle_state"], "RELEASE_INTENT"
        )

        resumed, _ = self.adapter(_Opener(_head_not_present()))
        receipt = resumed.release(LEASE_ID)
        self.assertTrue(SHA256_RE.fullmatch(receipt.lifecycle_state_sha256))
        self.assertEqual(self.state_payload()["lifecycle_state"], "RELEASED")

    def test_foreign_lost_and_binding_drift_heads_fail_closed(self) -> None:
        self.acquire_held()
        cases = (
            (
                _Response(
                    412,
                    BASE_URL,
                    {"x-ms-error-code": "LeaseIdMismatchWithBlobOperation"},
                ),
                "AZURE_BLOB_LEASE_FOREIGN",
            ),
            (_head_not_present(), "AZURE_BLOB_LEASE_NOT_HELD"),
            (
                _Response(
                    412,
                    BASE_URL,
                    {"x-ms-error-code": "ConditionNotMet"},
                ),
                "AZURE_BLOB_LEASE_BINDING_DRIFT",
            ),
            (_Response(404, BASE_URL, {}), "AZURE_BLOB_LEASE_BINDING_DRIFT"),
        )
        for response, code in cases:
            with self.subTest(code=code):
                adapter, _ = self.adapter(_Opener(response))
                with self.assertRaisesRegex(AzureBlobLeaseError, f"^{code}$"):
                    adapter.assert_held(LEASE_ID)

    def test_responses_require_exact_status_etag_version_lease_and_no_redirect(self) -> None:
        invalid = (
            _Response(200, LEASE_URL, _success_headers()),
            _Response(
                201,
                LEASE_URL,
                _success_headers(**{"x-ms-lease-id": str(OTHER_LEASE_ID)}),
            ),
            _Response(
                201,
                LEASE_URL,
                {"ETag": '"changed"', "x-ms-version": API_VERSION,
                 "x-ms-lease-id": str(LEASE_ID)},
            ),
            _Response(
                201,
                LEASE_URL,
                {"ETag": EXPECTED_ETAG, "x-ms-version": "2021-01-01",
                 "x-ms-lease-id": str(LEASE_ID)},
            ),
            _Response(
                201,
                "https://evil.invalid/redirected",
                _success_headers(**{"x-ms-lease-id": str(LEASE_ID)}),
            ),
            _Response(
                201,
                LEASE_URL,
                _success_headers(
                    **{
                        "Location": "https://evil.invalid",
                        "x-ms-lease-id": str(LEASE_ID),
                    }
                ),
            ),
            _Response(
                201,
                LEASE_URL,
                _success_headers(**{"x-ms-lease-id": str(LEASE_ID)}),
                b"unexpected",
            ),
        )
        for index, response in enumerate(invalid):
            with self.subTest(index=index):
                path = Path(self.temporary.name) / f"state-{index}" / "lease.json"
                opener = _Opener(response)
                adapter = AzureBlobLeaseAdapter(
                    binding=_binding(),
                    state_path=path,
                    token_provider=_TokenProvider(),
                    opener=opener,
                    clock=self.clock,
                )
                with self.assertRaisesRegex(
                    AzureBlobLeaseError,
                    r"^AZURE_BLOB_LEASE_RESPONSE_INVALID$",
                ):
                    adapter.acquire(LEASE_ID)
                self.assertEqual(len(opener.calls), 1)

    def test_errors_are_stable_redacted_and_requests_are_not_retried(self) -> None:
        secret = (
            f"token=secret account=nacperflease001 lease={LEASE_ID} "
            f"etag={EXPECTED_ETAG}"
        )
        opener = _Opener(RuntimeError(secret))
        adapter, _ = self.adapter(opener)
        with self.assertRaises(AzureBlobLeaseError) as raised:
            adapter.acquire(LEASE_ID)
        self.assertEqual(
            str(raised.exception), "AZURE_BLOB_LEASE_TRANSPORT_UNAVAILABLE"
        )
        self.assertEqual(len(opener.calls), 1)
        self.assertNotIn(secret, str(raised.exception))
        self.assertNotIn(str(LEASE_ID), str(raised.exception))

        token_path = Path(self.temporary.name) / "token-failure" / "lease.json"

        def token_failure(**_: str) -> str:
            raise RuntimeError(secret)

        token_adapter = AzureBlobLeaseAdapter(
            binding=_binding(),
            state_path=token_path,
            token_provider=token_failure,
            opener=_Opener(),
            clock=self.clock,
        )
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_TOKEN_UNAVAILABLE$"
        ):
            token_adapter.acquire(LEASE_ID)

    def test_private_state_rejects_tampering_permissions_and_binding_change(self) -> None:
        self.acquire_held()
        document = json.loads(self.state_path.read_text(encoding="ascii"))
        document["payload"]["lifecycle_state"] = "RELEASED"
        self.state_path.write_text(json.dumps(document), encoding="ascii")
        os.chmod(self.state_path, 0o600)
        adapter, _ = self.adapter(_Opener())
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_INVALID$"
        ):
            adapter.assert_held(LEASE_ID)

        self.state_path.unlink()
        self.acquire_held()
        os.chmod(self.state_path, 0o644)
        adapter, _ = self.adapter(_Opener())
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_INVALID$"
        ):
            adapter.assert_held(LEASE_ID)
        os.chmod(self.state_path, 0o600)

        adapter, _ = self.adapter(
            _Opener(), binding=_binding(expected_etag='"different"')
        )
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_CONFLICT$"
        ):
            adapter.assert_held(LEASE_ID)

        adapter, _ = self.adapter(
            _Opener(), binding=_binding(bff_account_name="otherbffaccount01")
        )
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_CONFLICT$"
        ):
            adapter.assert_held(LEASE_ID)

    def test_non_string_lifecycle_is_a_stable_redacted_state_error(self) -> None:
        self.acquire_held()
        document = json.loads(self.state_path.read_text(encoding="ascii"))
        document["payload"]["lifecycle_state"] = ["HELD", str(LEASE_ID)]
        document["payload_sha256"] = "0" * 64
        self.state_path.write_text(json.dumps(document), encoding="ascii")
        os.chmod(self.state_path, 0o600)
        adapter, _ = self.adapter(_Opener())
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_INVALID$"
        ) as raised:
            adapter.assert_held(LEASE_ID)
        self.assertNotIn(str(LEASE_ID), str(raised.exception))

    def test_adapter_has_no_disallowed_lease_or_blob_operations(self) -> None:
        adapter, _ = self.adapter(_Opener())
        for name in (
            "break_lease",
            "break",
            "delete",
            "change",
            "renew",
            "reacquire",
            "create",
            "put_blob",
        ):
            self.assertFalse(hasattr(adapter, name), name)
        public_callables = {
            name
            for name in dir(adapter)
            if not name.startswith("_") and callable(getattr(adapter, name))
        }
        self.assertEqual(public_callables, {"acquire", "assert_held", "release"})

    def test_public_methods_require_uuid_objects(self) -> None:
        adapter, _ = self.adapter(_Opener())
        for operation in (adapter.acquire, adapter.assert_held, adapter.release):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(TypeError, r"^lease_id$"):
                    operation(str(LEASE_ID))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
