from __future__ import annotations

import hashlib
import json
import unittest

from src.nac_bff.client_http_observation_receipt import (
    ClientHttpObservationError,
    validate_client_http_observation_receipt_bytes,
)


def _raw(value: dict[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _pair(status: str = "403", *, subject_available: bool = True) -> tuple[bytes, bytes]:
    base_core: dict[str, object] = {
        "end_utc": "2026-09-25T08:00:01.000Z",
        "request_correlation_binding_sha256": "a" * 64,
        "spfx_subject_available": subject_available,
        "start_utc": "2026-09-25T08:00:00.000Z",
        "ui_state": "no_access",
    }
    base = _raw({**base_core, "window_binding_sha256": hashlib.sha256(_raw(base_core)).hexdigest()})
    companion_core: dict[str, object] = {
        "base_receipt_sha256": hashlib.sha256(base).hexdigest(),
        "client_http_class": status,
        "schema_version": "nac.client-http-observation/v0.1",
    }
    companion = _raw({
        **companion_core,
        "observation_binding_sha256": hashlib.sha256(_raw(companion_core)).hexdigest(),
    })
    return base, companion


class ClientHttpObservationReceiptTests(unittest.TestCase):
    def test_closed_valid_pairs(self) -> None:
        for status in ("none", "401", "403"):
            with self.subTest(status=status):
                base, companion = _pair(status)
                self.assertEqual(
                    validate_client_http_observation_receipt_bytes(base, companion)["client_http_class"],
                    status,
                )

    def test_rejects_substitution_and_unknown_fields(self) -> None:
        base, companion = _pair()
        other_base, _ = _pair("401")
        # A different valid base receipt must not be paired with the old sidecar.
        other = json.loads(other_base)
        other["request_correlation_binding_sha256"] = "b" * 64
        other_core = {key: value for key, value in other.items() if key != "window_binding_sha256"}
        other["window_binding_sha256"] = hashlib.sha256(_raw(other_core)).hexdigest()
        for candidate_base, candidate_sidecar in (
            (_raw(other), companion),
            (base, _raw({**json.loads(companion), "token": "forbidden"})),
            (base, companion.replace(b'"403"', b'"200"')),
            (base, companion.replace(b'"403"', b'"401"')),
            (base, b'{"client_http_class":"403","client_http_class":"403"}'),
            (base, b"{" + b"x" * 1025 + b"}"),
        ):
            with self.subTest(candidate_sidecar=candidate_sidecar[:30]):
                with self.assertRaises(ClientHttpObservationError):
                    validate_client_http_observation_receipt_bytes(candidate_base, candidate_sidecar)

    def test_rejects_http_response_when_base_has_no_spfx_subject(self) -> None:
        base, companion = _pair("401", subject_available=False)
        with self.assertRaisesRegex(ClientHttpObservationError, "CLIENT_HTTP_SUBJECT_CLASS_CONFLICT"):
            validate_client_http_observation_receipt_bytes(base, companion)
