"""Synthetic, offline-only checks for the private workbench 403 event."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import unittest

from nac_bff.bff_403_diagnostic_event import (
    DENIAL_UNCLASSIFIED,
    REQUEST_SCOPE_REJECTED,
    ACCESS_DECISION_REJECTED,
    ACCESS_DECISION_UNAVAILABLE,
    DenialReasonState,
    InactiveDiagnosticBuffer,
    build_event,
    correlation_binding_from_scope,
    matches_protected_receipt,
    is_bounded_workbench_get,
)
from scripts.validate_m365_bff_403_diagnostic_event import validate_contract, CONTRACT_PATH
from nac_identity.governance_registry import evaluate_approval_mode, satisfies_four_eyes
from scripts.validate_identity_registry import REGISTRY_PATH
from nac_bff.fastapi_adapter import create_fastapi_app
from nac_bff.test_environment import (
    ALLOWED_MATTER_ID,
    ALLOWED_PURPOSE,
    ALLOWED_TENANT_ID,
    ALLOWED_WORKSPACE_ID,
    AccessDecision,
    TestEnvironmentBff,
    ValidatedClaims,
)
from nac_bff.workbench_endpoint import WorkbenchEndpoint


CORRELATION = "spfx-123e4567-e89b-42d3-a456-426614174000"
DIGEST = hashlib.sha256(CORRELATION.encode("ascii")).hexdigest()
PATH = (
    f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/"
    f"{ALLOWED_MATTER_ID}/workbench-snapshot"
)
WIRE_403 = b'{"status":403,"error":{"code":"ACCESS_DENIED"}}'
NOW = datetime(2026, 9, 26, 9, 0, tzinfo=UTC)


class _Access:
    def __init__(self, *, raises: bool = False) -> None:
        self.raises = raises
        self.calls = 0

    def decide(self, **_: object) -> AccessDecision:
        self.calls += 1
        if self.raises:
            raise RuntimeError("sensitive decision failure")
        return AccessDecision.deny()


class _NoGraph:
    def read_synthetic_workspace(self, **_: object) -> None:
        raise AssertionError("Graph must not be called for a denied request")


class _NoBpmn:
    def read_canonical_bpmn(self) -> None:
        raise AssertionError("BPMN must not be called for a denied request")


def _claims() -> ValidatedClaims:
    return ValidatedClaims(
        object_id="actor:synthetic:001",
        tenant_id=ALLOWED_TENANT_ID,
        subject="actor:synthetic:001",
    )


class Bff403DiagnosticEventTests(unittest.TestCase):
    def test_exact_single_header_is_hashed_and_receipt_match_is_separate(self) -> None:
        scope = {"headers": [(b"x-correlation-id", CORRELATION.encode("ascii"))]}
        self.assertEqual(correlation_binding_from_scope(scope), DIGEST)
        self.assertTrue(matches_protected_receipt(DIGEST, DIGEST))
        self.assertFalse(matches_protected_receipt(DIGEST, "0" * 64))
        self.assertFalse(matches_protected_receipt(DIGEST, "not-a-digest"))

    def test_missing_duplicate_combined_or_rewritten_header_is_unbound(self) -> None:
        valid = (b"X-Correlation-ID", CORRELATION.encode("ascii"))
        invalid_sets = (
            [],
            [valid, valid],
            [(b"x-correlation-id", CORRELATION.encode("ascii") + b",other")],
            [(b"x-correlation-id", CORRELATION.upper().encode("ascii"))],
            [(b"x-correlation-id", b"spfx-123e4567-e89b-12d3-a456-426614174000")],
            [(b"x-correlation-id", b"spfx-123e4567-e89b-42d3-1456-426614174000")],
        )
        for headers in invalid_sets:
            with self.subTest(headers=headers):
                self.assertIsNone(correlation_binding_from_scope({"headers": headers}))

    def test_event_is_closed_and_contains_no_request_controlled_text(self) -> None:
        event = build_event(
            reason_class=REQUEST_SCOPE_REJECTED,
            correlation_binding_sha256=DIGEST,
            observed_at=NOW,
        )
        self.assertEqual(
            set(event),
            {
                "schema_version",
                "observed_at_utc",
                "route_class",
                "method",
                "http_class",
                "reason_class",
                "request_correlation_binding_sha256",
            },
        )
        self.assertEqual(event["observed_at_utc"], "2026-09-26T09:00:00Z")
        self.assertNotIn(CORRELATION, repr(event))
        for sensitive in ("actor:synthetic:001", "Bearer secret", "ofunk@example.invalid", PATH):
            self.assertNotIn(sensitive, repr(event))
        with self.assertRaises(ValueError):
            build_event(
                reason_class="sensitive free text",
                correlation_binding_sha256=DIGEST,
                observed_at=NOW,
            )

    def test_inactive_buffer_is_bounded_and_not_a_provider_sink(self) -> None:
        buffer = InactiveDiagnosticBuffer()
        event = build_event(reason_class=DENIAL_UNCLASSIFIED, correlation_binding_sha256=DIGEST, observed_at=NOW)
        self.assertTrue(buffer.record_nowait(event))
        self.assertFalse(buffer.record_nowait(event))
        self.assertEqual(buffer.take_nowait(), event)
        self.assertIsNone(buffer.take_nowait())
        self.assertTrue(is_bounded_workbench_get(path=PATH, method="GET"))
        for path, method in ((PATH, "POST"), (PATH + "/other", "GET"), ("/healthz", "GET")):
            self.assertFalse(is_bounded_workbench_get(path=path, method=method))

    def test_contract_rejects_approval_and_activation_claims(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(validate_contract(contract), [])
        for field, bad_value in (
            ("evidence_status", "APPROVED"),
            ("same_principal_accounts_are_distinct_approvers", True),
            ("solo_four_eyes_satisfied", True),
            ("uncited_two_person_duty", "OWNER_SOLO_APPROVAL"),
            ("cited_two_person_duty_with_one_principal", "FOUR_EYES_APPROVAL"),
        ):
            with self.subTest(field=field):
                changed = json.loads(json.dumps(contract))
                changed["approval_boundary"][field] = bad_value
                self.assertTrue(validate_contract(changed))
        changed = json.loads(json.dumps(contract))
        changed["gates"]["deployment_authorized"] = True
        self.assertTrue(validate_contract(changed))

    def test_contract_approval_cases_follow_principal_policy(self) -> None:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        primary = "github:owner-example-primary"
        alias = "github:owner-example-secondary"
        self.assertFalse(satisfies_four_eyes(registry, primary, alias))
        self.assertEqual(evaluate_approval_mode(registry, operator_account_id=primary)["status"], "OWNER_SOLO_APPROVAL")
        self.assertEqual(evaluate_approval_mode(registry, operator_account_id=primary, external_two_person_required=True, requirement_citation="")["status"], "BLOCKED_REQUIREMENT_CITATION_MISSING")
        self.assertEqual(evaluate_approval_mode(registry, operator_account_id=alias, external_two_person_required=True, requirement_citation="binding-policy:section-4")["status"], "BLOCKED_SINGLE_PRINCIPAL")

    def test_domain_denial_classes_preserve_exact_public_bytes(self) -> None:
        cases = (
            ("wrong-workspace", False, REQUEST_SCOPE_REJECTED),
            (ALLOWED_WORKSPACE_ID, True, ACCESS_DECISION_UNAVAILABLE),
            (ALLOWED_WORKSPACE_ID, False, ACCESS_DECISION_REJECTED),
        )
        for workspace, raises, expected in cases:
            with self.subTest(expected=expected):
                access = _Access(raises=raises)
                endpoint = WorkbenchEndpoint(
                    expected_tenant_id=ALLOWED_TENANT_ID,
                    access_decision_port=access,
                    graph_rest_port=_NoGraph(),
                    bpmn_asset_port=_NoBpmn(),
                )
                state = DenialReasonState()
                response = endpoint.get_snapshot(
                    claims=_claims(),
                    workspace_id=workspace,
                    matter_id=ALLOWED_MATTER_ID,
                    purpose=ALLOWED_PURPOSE,
                    _diagnostic_state=state,
                )
                self.assertEqual(response.body_bytes, WIRE_403)
                self.assertEqual(state.reason_class, expected)
                self.assertEqual(access.calls, 0 if workspace == "wrong-workspace" else 1)

    def test_http_boundary_emits_once_and_keeps_public_response_neutral(self) -> None:
        try:
            from fastapi import HTTPException
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("FastAPI runtime dependencies are not installed")

        access = _Access()
        endpoint = WorkbenchEndpoint(
            expected_tenant_id=ALLOWED_TENANT_ID,
            access_decision_port=access,
            graph_rest_port=_NoGraph(),
            bpmn_asset_port=_NoBpmn(),
        )
        bff = TestEnvironmentBff(
            expected_tenant_id=ALLOWED_TENANT_ID,
            access_decision_port=access,
            graph_rest_port=_NoGraph(),
            bpmn_asset_port=_NoBpmn(),
        )

        async def allowed() -> ValidatedClaims:
            return _claims()

        buffer = InactiveDiagnosticBuffer()
        client = TestClient(create_fastapi_app(
            bff=bff,
            workbench_endpoint=endpoint,
            validated_claims_dependency=allowed,
            diagnostic_buffer=buffer,
        ))
        response = client.get(
            PATH,
            params={"purpose": ALLOWED_PURPOSE},
            headers={"X-Correlation-ID": CORRELATION},
        )
        self.assertEqual((response.status_code, response.content), (403, WIRE_403))
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        event = buffer.take_nowait()
        self.assertIsNotNone(event)
        self.assertEqual(event["reason_class"], ACCESS_DECISION_REJECTED)
        self.assertEqual(event["request_correlation_binding_sha256"], DIGEST)
        self.assertNotIn("reason_class", response.text)

        client.get(PATH, params={"purpose": ALLOWED_PURPOSE}, headers={"X-Correlation-ID": "invalid"})
        self.assertIsNone(buffer.take_nowait())

        async def denied_before_endpoint() -> None:
            raise HTTPException(status_code=403, detail="sensitive auth detail")

        early_buffer = InactiveDiagnosticBuffer()
        early_client = TestClient(create_fastapi_app(
            bff=bff,
            workbench_endpoint=endpoint,
            validated_claims_dependency=denied_before_endpoint,
            diagnostic_buffer=early_buffer,
        ))
        early = early_client.get(PATH, params={"purpose": ALLOWED_PURPOSE}, headers={"X-Correlation-ID": CORRELATION})
        self.assertEqual((early.status_code, early.content), (403, WIRE_403))
        early_event = early_buffer.take_nowait()
        self.assertIsNotNone(early_event)
        self.assertEqual(early_event["reason_class"], DENIAL_UNCLASSIFIED)

    def test_inactive_buffer_never_changes_denial(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("FastAPI runtime dependencies are not installed")

        access = _Access()
        endpoint = WorkbenchEndpoint(
            expected_tenant_id=ALLOWED_TENANT_ID,
            access_decision_port=access,
            graph_rest_port=_NoGraph(),
            bpmn_asset_port=_NoBpmn(),
        )
        bff = TestEnvironmentBff(
            expected_tenant_id=ALLOWED_TENANT_ID,
            access_decision_port=access,
            graph_rest_port=_NoGraph(),
            bpmn_asset_port=_NoBpmn(),
        )

        async def allowed() -> ValidatedClaims:
            return _claims()

        buffer = InactiveDiagnosticBuffer()
        buffer.record_nowait(build_event(reason_class=DENIAL_UNCLASSIFIED, correlation_binding_sha256=DIGEST, observed_at=NOW))
        client = TestClient(create_fastapi_app(
            bff=bff,
            workbench_endpoint=endpoint,
            validated_claims_dependency=allowed,
            diagnostic_buffer=buffer,
        ))
        response = client.get(PATH, params={"purpose": ALLOWED_PURPOSE}, headers={"X-Correlation-ID": CORRELATION})
        self.assertEqual((response.status_code, response.content), (403, WIRE_403))
        self.assertNotIn("reason_class", response.text)
        self.assertIsNotNone(buffer.take_nowait())
        self.assertIsNone(buffer.take_nowait())


if __name__ == "__main__":
    unittest.main()
