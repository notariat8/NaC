from __future__ import annotations

import json
import unittest

from nac_bff.azure_performance_lease_broker import (
    BrokerRoleScopeClaims,
    LeaseBrokerError,
    LeaseBrokerReceipt,
    RetryDirective,
)
from nac_bff.fastapi_adapter import create_fastapi_app


OWNER = "11111111-1111-4111-8111-111111111111"


class _Bff:
    def get_workspace(self, **kwargs: object) -> None:
        raise AssertionError(kwargs)


class _Broker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, object]] = []

    def _call(self, operation: str, *, ticket: object, claims: object):
        self.calls.append((operation, ticket, claims))
        if ticket == {"deny": True}:
            raise LeaseBrokerError("provider secret must not escape")
        return LeaseBrokerReceipt(
            operation=operation,
            outcome="ACQUIRED" if operation == "acquire" else "HELD",
            retry=RetryDirective.NONE,
            ticket_fingerprint="a" * 64,
            binding_fingerprint="b" * 64,
        )

    def acquire(self, **kwargs: object):
        return self._call("acquire", **kwargs)

    def assert_held(self, **kwargs: object):
        return self._call("assert_held", **kwargs)

    def release(self, **kwargs: object):
        return self._call("release", **kwargs)


class PerformanceLeaseBrokerFastApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            raise unittest.SkipTest("FastAPI runtime dependencies are unavailable")
        cls.TestClient = TestClient

    def _client(self):
        broker = _Broker()
        claims = BrokerRoleScopeClaims(
            owner_subject=OWNER,
            role="Performance.Lease",
            scope="nac.performance.lease",
        )

        async def read_claims():
            return claims

        async def unused_claims():
            return None

        app = create_fastapi_app(
            bff=_Bff(),
            validated_claims_dependency=unused_claims,
            performance_lease_broker=broker,
            performance_lease_claims_dependency=read_claims,
        )
        return self.TestClient(app), broker, claims

    def test_fixed_routes_accept_only_exact_ticket_envelope(self) -> None:
        client, broker, claims = self._client()
        for route, expected in (
            ("acquire", "acquire"),
            ("assert", "assert_held"),
            ("release", "release"),
        ):
            with self.subTest(route=route):
                response = client.post(
                    f"/v1/internal/performance-lease/{route}",
                    content=json.dumps({"ticket": {"value": route}}),
                    headers={"Content-Type": "application/json"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.assertEqual(broker.calls[-1], (expected, {"value": route}, claims))
                self.assertNotIn("lease_id", response.text)

    def test_invalid_shapes_and_provider_errors_are_generic(self) -> None:
        client, broker, _ = self._client()
        for body in ({}, {"ticket": {}, "url": "https://example.invalid"}):
            response = client.post(
                "/v1/internal/performance-lease/acquire",
                content=json.dumps(body),
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json(), {"detail": "request denied"})
        response = client.post(
            "/v1/internal/performance-lease/acquire",
            content=json.dumps({"ticket": {"deny": True}}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("provider", response.text)
        self.assertNotIn("secret", response.text)
        self.assertEqual(broker.calls[-1][0], "acquire")

    def test_unknown_operation_and_oversized_body_are_rejected(self) -> None:
        client, broker, _ = self._client()
        unknown = client.post(
            "/v1/internal/performance-lease/break",
            content=json.dumps({"ticket": {}}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(unknown.status_code, 404)
        oversized = client.post(
            "/v1/internal/performance-lease/acquire",
            content=json.dumps({"ticket": {"padding": "x" * 16_384}}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(oversized.status_code, 400)
        self.assertEqual(broker.calls, [])


if __name__ == "__main__":
    unittest.main()
