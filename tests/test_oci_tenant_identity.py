from __future__ import annotations

import base64
import json
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


_TEST_RSA_N = 60290864802346228052373842506010458173966209336683677551090586324542057079549228854349222820208753926620218796263542965581242407526149580695574568271645442151543746443266285352844502009509804166840559101498386186628283747338680995712921543972624707983532965790736363470772309180782392068865075054488348654111
_TEST_RSA_E = 65537
_TEST_RSA_D = 44044520410484617246189213080553926880921925086781580330402124013306987912134800644821669300748195854933796409794614440135086176436661175747471254484361018752788764680484856240334993542981039820309435002130903876692383392605366887582127376452577112987587644549766431208915510460186709613716948053911309728473
_TEST_RSA_KID = "nac-test-key"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _int_b64url(value: int) -> str:
    length = max(1, (value.bit_length() + 7) // 8)
    return _b64url(value.to_bytes(length, "big"))


def _json_segment(payload: dict[str, object]) -> str:
    return _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _rs256_test_signature(signing_input: str) -> str:
    key_length = (_TEST_RSA_N.bit_length() + 7) // 8
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(
        signing_input.encode("ascii")
    ).digest()
    padding_length = key_length - len(digest_info) - 3
    encoded = b"\x00\x01" + (b"\xff" * padding_length) + b"\x00" + digest_info
    signature = pow(int.from_bytes(encoded, "big"), _TEST_RSA_D, _TEST_RSA_N).to_bytes(key_length, "big")
    return _b64url(signature)


def _signed_test_id_token(claims: dict[str, object], *, kid: str = _TEST_RSA_KID) -> str:
    header = {"alg": "RS256", "kid": kid, "typ": "JWT"}
    signing_input = f"{_json_segment(header)}.{_json_segment(claims)}"
    return f"{signing_input}.{_rs256_test_signature(signing_input)}"


def _session_cookie_payload(cookie_header: str) -> dict[str, object]:
    cookie_value = cookie_header.split("=", 1)[1]
    payload_part = cookie_value.split(".", 1)[0]
    padding = "=" * (-len(payload_part) % 4)
    return json.loads(base64.urlsafe_b64decode(f"{payload_part}{padding}".encode("ascii")).decode("utf-8"))


def _test_jwk(*, kid: str = _TEST_RSA_KID) -> dict[str, str]:
    return {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": _int_b64url(_TEST_RSA_N),
        "e": _int_b64url(_TEST_RSA_E),
    }


class NaCOciTenantIdentityTests(unittest.TestCase):
    def test_contract_declares_dry_run_only_boundary(self) -> None:
        contract = json.loads(
            (REPO_ROOT / "workflows/contracts/oci-tenant-identity.contract.json").read_text(encoding="utf-8")
        )

        self.assertEqual(contract["schema_version"], "nac.oci-tenant-identity-contract/v0.1")
        self.assertFalse(contract["productive_identity_writes_allowed"])
        self.assertIn("domain_ready", contract["required_gates"])
        self.assertIn("owner_apply_approval", contract["required_gates"])
        self.assertIn("/admin/v1/Users", contract["oci_identity_domain_endpoints"])
        self.assertIn("/admin/v1/Groups", contract["oci_identity_domain_endpoints"])
        self.assertIn("/oauth2/v1/authorize", contract["oci_identity_domain_endpoints"])
        self.assertEqual(contract["login_intent_schema"]["schema_version"], "nac.oci-login-intent/v0.1")
        self.assertEqual(
            contract["callback_session_contract_schema"]["schema_version"],
            "nac.oidc-session-boundary/v0.2",
        )
        self.assertEqual(
            contract["token_exchange_contract_schema"]["schema_version"],
            "nac.oidc-token-exchange/v0.1",
        )
        self.assertTrue(contract["token_exchange_contract_schema"]["server_side_live_adapter_available"])
        self.assertFalse(contract["token_exchange_contract_schema"]["live_token_exchange_performed_by_default"])
        self.assertTrue(contract["token_exchange_contract_schema"]["id_token_verifier_uses_oidc_discovery_jwks"])
        self.assertTrue(
            contract["token_exchange_contract_schema"]["id_token_verifier_validates_rs256_issuer_audience_and_expiry"]
        )
        self.assertTrue(contract["token_exchange_contract_schema"]["vault_secret_read_in_contract_slice"])
        self.assertTrue(
            contract["token_exchange_contract_schema"][
                "vault_secret_read_requires_valid_state_code_metadata_and_id_token_verifier"
            ]
        )
        self.assertTrue(contract["callback_session_contract_schema"]["live_token_exchange_in_contract_slice"])
        self.assertTrue(contract["callback_session_contract_schema"]["live_token_exchange_requires_valid_state"])
        self.assertTrue(contract["callback_session_contract_schema"]["verified_id_token_required_before_role_gate"])
        self.assertFalse(contract["callback_session_contract_schema"]["verified_id_token_claims_exposed_in_public_result"])
        self.assertTrue(contract["callback_session_contract_schema"]["session_cookie_issued_in_contract_slice"])
        self.assertTrue(contract["callback_session_contract_schema"]["session_cookie_requires_positive_role_gate"])
        self.assertFalse(contract["callback_session_contract_schema"]["session_cookie_contains_tokens_or_claims"])
        self.assertEqual(contract["callback_session_contract_schema"]["session_cookie_max_ttl_seconds"], 3600)
        self.assertFalse(contract["callback_session_contract_schema"]["workspace_opened_in_contract_slice"])
        self.assertTrue(contract["callback_session_contract_schema"]["server_session_store_in_contract_slice"])
        self.assertTrue(contract["callback_session_contract_schema"]["server_session_store_required_before_full_workspace"])
        self.assertTrue(contract["callback_session_contract_schema"]["server_session_revocation_fails_closed"])
        self.assertFalse(contract["callback_session_contract_schema"]["server_session_store_contains_tokens_or_claims"])
        self.assertTrue(contract["callback_session_contract_schema"]["session_audit_contract_in_contract_slice"])
        self.assertTrue(contract["callback_session_contract_schema"]["session_cookie_validation_in_contract_slice"])
        self.assertTrue(
            contract["callback_session_contract_schema"]["session_cookie_validation_opens_only_protected_start_status"]
        )
        self.assertFalse(contract["callback_session_contract_schema"]["session_cookie_validation_loads_mandate_data"])
        self.assertFalse(contract["callback_session_contract_schema"]["full_workspace_opened_after_session_validation"])
        self.assertEqual(
            contract["callback_session_contract_schema"]["session_validation_schema"]["schema_version"],
            "nac.session-validation/v0.1",
        )
        self.assertTrue(
            contract["callback_session_contract_schema"]["session_validation_schema"][
                "invalid_missing_tampered_or_expired_cookie_fails_closed"
            ]
        )
        self.assertFalse(
            contract["callback_session_contract_schema"]["session_validation_schema"]["session_cookie_exposed_in_result"]
        )
        self.assertIn("protected_start_status_page", contract["allowed_operations"])
        self.assertEqual(
            contract["callback_session_contract_schema"]["claim_boundary_schema"]["schema_version"],
            "nac.oidc-claim-boundary/v0.1",
        )
        self.assertTrue(
            contract["callback_session_contract_schema"]["claim_boundary_schema"][
                "verified_claims_forwarded_to_role_gate_only"
            ]
        )
        self.assertEqual(
            contract["role_case_gate_contract_schema"]["schema_version"],
            "nac.role-case-gate/v0.1",
        )
        self.assertTrue(contract["role_case_gate_contract_schema"]["verified_session_required"])
        self.assertTrue(contract["role_case_gate_contract_schema"]["subject_matter_role_required"])
        self.assertTrue(contract["role_case_gate_contract_schema"]["tenant_binding_required_before_workspace_route"])
        self.assertTrue(contract["role_case_gate_contract_schema"]["case_binding_required_before_workspace_route"])
        self.assertTrue(contract["role_case_gate_contract_schema"]["purpose_binding_required_before_workspace_route"])
        self.assertTrue(contract["role_case_gate_contract_schema"]["four_eyes_gate_supported"])
        self.assertEqual(
            contract["role_case_gate_contract_schema"]["allowed_surface"],
            "protected_status_metadata",
        )
        self.assertFalse(contract["role_case_gate_contract_schema"]["raw_mandate_content_allowed"])
        self.assertFalse(contract["role_case_gate_contract_schema"]["browser_payload_contains_case_or_session_identifiers"])
        self.assertFalse(contract["role_case_gate_contract_schema"]["browser_payload_contains_tenant_identifiers"])
        self.assertFalse(contract["role_case_gate_contract_schema"]["browser_payload_contains_claims_or_emails"])
        self.assertFalse(contract["role_case_gate_contract_schema"]["browser_payload_contains_provider_details"])
        self.assertFalse(contract["role_case_gate_contract_schema"]["full_workspace_opened_in_contract_slice"])
        self.assertEqual(
            contract["role_case_gate_contract_schema"]["audit_evidence_schema"]["schema_version"],
            "nac.role-case-gate.audit/v0.1",
        )
        self.assertTrue(contract["role_case_gate_contract_schema"]["audit_evidence_schema"]["redacted_metadata_only"])
        self.assertEqual(
            contract["role_case_gate_contract_schema"]["audit_evidence_schema"]["forbidden_values"],
            [
                "session_id",
                "tenant_hint",
                "case_id",
                "claims",
                "email",
                "provider_url",
                "callback_code",
                "callback_state",
                "mandate_content",
            ],
        )
        self.assertTrue(contract["guardrails"]["nac_role_gate_required_after_idp_login"])

    def test_domain_check_accepts_notary_domain_and_admin_email(self) -> None:
        from nac_identity.oci_tenant import check_domain_ready

        result = check_domain_ready(
            domain="kanzlei-notariat.example",
            tenant_slug="kanzlei-notariat",
            admin_email="admin@kanzlei-notariat.example",
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["schema_version"], "nac.tenant-domain-readiness/v0.1")
        self.assertEqual(result["domain"], "kanzlei-notariat.example")
        self.assertEqual(result["tenant_slug"], "kanzlei-notariat")
        self.assertEqual(result["blocking_findings"], [])
        self.assertEqual(result["verification"]["dns_record_name"], "_nac.kanzlei-notariat.example")
        self.assertTrue(result["verification"]["dns_record_value"].startswith("nac-domain-verification="))

    def test_domain_check_rejects_freemail_admin(self) -> None:
        from nac_identity.oci_tenant import check_domain_ready

        result = check_domain_ready(
            domain="kanzlei-notariat.example",
            tenant_slug="kanzlei-notariat",
            admin_email="admin@gmail.com",
        )

        self.assertFalse(result["ready"])
        self.assertIn("admin_email_domain_mismatch", result["blocking_findings"])
        self.assertIn("admin_email_freemail_domain", result["blocking_findings"])

    def test_domain_check_rejects_unstable_tenant_slug(self) -> None:
        from nac_identity.oci_tenant import check_domain_ready

        result = check_domain_ready(
            domain="kanzlei-notariat.example",
            tenant_slug="NaC Admin",
            admin_email="admin@kanzlei-notariat.example",
        )

        self.assertFalse(result["ready"])
        self.assertIn("tenant_slug_invalid", result["blocking_findings"])

    def test_admin_provisioning_plan_is_dry_run_and_uses_oci_identity_domain_paths(self) -> None:
        from nac_identity.oci_tenant import build_admin_provisioning_plan

        plan = build_admin_provisioning_plan(
            tenant_slug="kanzlei-notariat",
            domain="kanzlei-notariat.example",
            admin_email="admin@kanzlei-notariat.example",
            admin_display_name="Admin Notariat",
            identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
            identity_domain_id="ocid1.domain.oc1.example",
        )

        serialized = json.dumps(plan, sort_keys=True).lower()
        self.assertEqual(plan["schema_version"], "nac.oci-admin-provisioning-plan/v0.1")
        self.assertEqual(plan["mode"], "dry_run")
        self.assertTrue(plan["requires_human_approval"])
        self.assertFalse(plan["console_access_required_for_end_users"])
        self.assertEqual(plan["target"]["users_endpoint"], "https://idcs.example.identity.oraclecloud.com:443/admin/v1/Users")
        self.assertEqual(plan["target"]["groups_endpoint"], "https://idcs.example.identity.oraclecloud.com:443/admin/v1/Groups")
        self.assertEqual(plan["admin_user"]["user_name"], "admin@kanzlei-notariat.example")
        self.assertIn("nac-tenant-admin", plan["groups"])
        self.assertIn("users.create", plan["planned_writes"])
        self.assertNotIn("secret", serialized)
        self.assertNotIn("token", serialized)
        self.assertNotIn("private_key", serialized)

    def test_admin_provisioning_plan_refuses_unready_domain(self) -> None:
        from nac_identity.oci_tenant import build_admin_provisioning_plan

        with self.assertRaises(ValueError) as error:
            build_admin_provisioning_plan(
                tenant_slug="kanzlei-notariat",
                domain="kanzlei-notariat.example",
                admin_email="admin@gmail.com",
                admin_display_name="Admin Notariat",
                identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
                identity_domain_id="ocid1.domain.oc1.example",
            )

        self.assertIn("admin_email_domain_mismatch", str(error.exception))

    def test_apply_request_requires_all_apply_gates(self) -> None:
        from nac_identity.oci_tenant import build_admin_provisioning_plan, build_apply_request

        plan = build_admin_provisioning_plan(
            tenant_slug="kanzlei-notariat",
            domain="kanzlei-notariat.example",
            admin_email="admin@kanzlei-notariat.example",
            admin_display_name="Admin Notariat",
            identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
            identity_domain_id="ocid1.domain.oc1.example",
        )

        request = build_apply_request(
            plan,
            dns_verified=False,
            owner_approval_id="",
            audit_event_id="",
            rollback_plan_id="",
        )

        self.assertEqual(request["schema_version"], "nac.oci-identity-apply-request/v0.1")
        self.assertFalse(request["ready_to_apply"])
        self.assertEqual(request["mode"], "review_artifact_only")
        self.assertIn("dns_not_verified", request["blocking_findings"])
        self.assertIn("owner_apply_approval_missing", request["blocking_findings"])
        self.assertIn("audit_event_missing", request["blocking_findings"])
        self.assertIn("rollback_plan_missing", request["blocking_findings"])

    def test_apply_request_ready_artifact_is_secret_free(self) -> None:
        from nac_identity.oci_tenant import build_admin_provisioning_plan, build_apply_request

        plan = build_admin_provisioning_plan(
            tenant_slug="kanzlei-notariat",
            domain="kanzlei-notariat.example",
            admin_email="admin@kanzlei-notariat.example",
            admin_display_name="Admin Notariat",
            identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
            identity_domain_id="ocid1.domain.oc1.example",
        )

        request = build_apply_request(
            plan,
            dns_verified=True,
            owner_approval_id="OWNER-APPROVED-32",
            audit_event_id="AUDIT-32",
            rollback_plan_id="ROLLBACK-32",
        )
        serialized = json.dumps(request, sort_keys=True).lower()

        self.assertTrue(request["ready_to_apply"])
        self.assertEqual(request["blocking_findings"], [])
        self.assertEqual(request["approval"]["owner_approval_id"], "OWNER-APPROVED-32")
        self.assertEqual(request["audit"]["audit_event_id"], "AUDIT-32")
        self.assertEqual(request["rollback"]["rollback_plan_id"], "ROLLBACK-32")
        self.assertFalse(request["productive_write_executed"])
        self.assertIn("users.create", request["planned_writes"])
        self.assertNotIn("secret", serialized)
        self.assertNotIn("token", serialized)
        self.assertNotIn("private_key", serialized)

    def test_login_intent_builds_oci_oidc_authorize_url_without_authorizing_tenant(self) -> None:
        from nac_identity.oci_login import build_login_intent

        intent = build_login_intent(
            tenant_hint="notariat-musterstadt",
            identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
            client_id="nac-web-app",
            redirect_uri="https://app.notariat8.de/auth/callback",
        )
        serialized = json.dumps(intent, sort_keys=True).lower()

        self.assertEqual(intent["schema_version"], "nac.oci-login-intent/v0.1")
        self.assertEqual(intent["mode"], "authorization_code_redirect_intent")
        self.assertEqual(intent["tenant_context"]["tenant_hint"], "notariat-musterstadt")
        self.assertFalse(intent["tenant_context"]["tenant_authorized_by_hint"])
        self.assertTrue(intent["guardrails"]["nac_role_gate_required_after_idp_login"])
        self.assertTrue(intent["guardrails"]["server_generated_state_required"])
        self.assertEqual(
            intent["endpoints"]["authorization_endpoint"],
            "https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/authorize",
        )
        self.assertEqual(
            intent["endpoints"]["discovery_endpoint"],
            "https://idcs.example.identity.oraclecloud.com:443/.well-known/openid-configuration",
        )
        self.assertIn("response_type=code", intent["authorization_url"])
        self.assertIn("client_id=nac-web-app", intent["authorization_url"])
        self.assertIn("scope=openid+profile+email", intent["authorization_url"])
        self.assertTrue(intent["oidc"]["state"].startswith("state-"))
        self.assertTrue(intent["oidc"]["nonce"].startswith("nonce-"))
        self.assertNotIn("notariat-musterstadt", intent["authorization_url"])
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("private_key", serialized)

    def test_login_intent_can_use_signed_expiring_state_without_exposing_secret(self) -> None:
        from nac_identity.oci_login import build_login_intent
        from nac_identity.oidc_state import validate_signed_state

        intent = build_login_intent(
            tenant_hint="notariat-musterstadt",
            identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
            client_id="nac-web-app",
            redirect_uri="https://app.notariat8.de/auth/callback",
            state_signing_key="unit-test-state-signing-key",
            now=1_800_000_000,
        )
        validation = validate_signed_state(
            intent["oidc"]["state"],
            signing_key="unit-test-state-signing-key",
            now=1_800_000_060,
        )
        serialized = json.dumps(intent, sort_keys=True)

        self.assertEqual(intent["state_binding"]["status"], "signed")
        self.assertEqual(intent["state_binding"]["ttl_seconds"], 600)
        self.assertTrue(intent["state_binding"]["nonce_bound"])
        self.assertEqual(validation["status"], "valid")
        self.assertEqual(validation["tenant_hint"], "notariat-musterstadt")
        self.assertTrue(validation["nonce_bound"])
        self.assertEqual(
            validation["nonce_hash"],
            hashlib.sha256(intent["oidc"]["nonce"].encode("utf-8")).hexdigest(),
        )
        self.assertNotIn("unit-test-state-signing-key", serialized)

    def test_signed_state_binds_nonce_without_returning_raw_nonce(self) -> None:
        from nac_identity.oidc_state import build_signed_state, validate_signed_state

        state = build_signed_state(
            tenant_hint="notariat-musterstadt",
            signing_key="unit-test-state-signing-key",
            nonce="nonce-secret-for-id-token",
            now=1_800_000_000,
            ttl_seconds=120,
        )
        validation = validate_signed_state(
            state,
            signing_key="unit-test-state-signing-key",
            now=1_800_000_060,
        )
        serialized = json.dumps(validation, sort_keys=True)

        self.assertEqual(validation["status"], "valid")
        self.assertEqual(validation["tenant_hint"], "notariat-musterstadt")
        self.assertTrue(validation["nonce_bound"])
        self.assertEqual(
            validation["nonce_hash"],
            hashlib.sha256(b"nonce-secret-for-id-token").hexdigest(),
        )
        self.assertNotIn("nonce-secret-for-id-token", serialized)
        self.assertNotIn("unit-test-state-signing-key", serialized)

    def test_signed_state_rejects_tampering_and_expiry_without_returning_secret(self) -> None:
        from nac_identity.oidc_state import build_signed_state, validate_signed_state

        state = build_signed_state(
            tenant_hint="notariat-musterstadt",
            signing_key="unit-test-state-signing-key",
            now=1_800_000_000,
            ttl_seconds=120,
        )
        tampered_state = state[:-1] + ("A" if state[-1] != "A" else "B")
        tampered = validate_signed_state(
            tampered_state,
            signing_key="unit-test-state-signing-key",
            now=1_800_000_060,
        )
        expired = validate_signed_state(
            state,
            signing_key="unit-test-state-signing-key",
            now=1_800_000_120,
        )
        future_issued_state = build_signed_state(
            tenant_hint="notariat-musterstadt",
            signing_key="unit-test-state-signing-key",
            now=1_800_000_500,
            ttl_seconds=120,
        )
        future_issued = validate_signed_state(
            future_issued_state,
            signing_key="unit-test-state-signing-key",
            now=1_800_000_060,
        )
        non_string = validate_signed_state(
            None,  # type: ignore[arg-type]
            signing_key="unit-test-state-signing-key",
            now=1_800_000_060,
        )
        serialized = json.dumps({"tampered": tampered, "expired": expired}, sort_keys=True)

        self.assertEqual(tampered["status"], "invalid")
        self.assertEqual(expired["status"], "expired")
        self.assertEqual(future_issued["status"], "invalid")
        self.assertEqual(non_string["status"], "invalid")
        self.assertFalse(tampered["guardrails"]["contains_credentials"])
        self.assertFalse(expired["guardrails"]["contains_credentials"])
        self.assertNotIn("unit-test-state-signing-key", serialized)
        self.assertNotIn(state, serialized)

    def test_signed_state_rejects_malformed_payload_as_invalid(self) -> None:
        from nac_identity.oidc_state import validate_signed_state

        malformed = validate_signed_state(
            "state.not-valid-base64.signature",
            signing_key="unit-test-state-signing-key",
            now=1_800_000_060,
        )

        self.assertEqual(malformed["status"], "invalid")
        self.assertFalse(malformed["guardrails"]["contains_credentials"])

    def test_auth_callback_result_keeps_role_gate_closed_without_exposing_values(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-secret-from-nac",
            provider_error="",
            state_validation_configured=False,
            token_exchange_configured=False,
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["schema_version"], "nac.auth-callback/v0.1")
        self.assertEqual(result["status"], "received")
        self.assertEqual(result["state_validation"]["status"], "not_configured")
        self.assertEqual(result["token_exchange"]["status"], "not_configured")
        self.assertEqual(result["token_exchange"]["configuration"], "not_configured")
        self.assertEqual(result["role_gate"]["status"], "closed")
        self.assertFalse(result["guardrails"]["contains_credentials"])
        self.assertNotIn("secret-code-from-idp", serialized)
        self.assertNotIn("state-secret-from-nac", serialized)

    def test_auth_callback_result_accepts_validated_state_but_keeps_role_gate_closed(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=False,
            state_validation={"status": "valid", "tenant_hint": "notariat-musterstadt"},
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["status"], "received")
        self.assertEqual(result["state_validation"]["status"], "valid")
        self.assertEqual(result["state_validation"]["tenant_hint"], "notariat-musterstadt")
        self.assertEqual(result["role_gate"]["status"], "closed")
        self.assertNotIn("secret-code-from-idp", serialized)
        self.assertNotIn("state-redacted", serialized)

    def test_auth_callback_result_preserves_nonce_binding_without_hash(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=False,
            state_validation={
                "status": "valid",
                "tenant_hint": "notariat-musterstadt",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(b"nonce-secret-for-id-token").hexdigest(),
            },
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["status"], "received")
        self.assertTrue(result["state_validation"]["nonce_bound"])
        self.assertNotIn("nonce-secret-for-id-token", serialized)
        self.assertNotIn(hashlib.sha256(b"nonce-secret-for-id-token").hexdigest(), serialized)
        self.assertEqual(result["role_gate"]["status"], "closed")

    def test_auth_callback_result_rejects_configured_but_missing_state_validation(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=False,
            state_validation=None,
        )

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["role_gate"]["reason"], "state_not_started")

    def test_auth_callback_result_rejects_invalid_or_expired_state(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        invalid = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=False,
            state_validation={"status": "invalid"},
        )
        expired = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=False,
            state_validation={"status": "expired"},
        )

        self.assertEqual(invalid["status"], "rejected")
        self.assertEqual(invalid["role_gate"]["reason"], "state_invalid")
        self.assertEqual(expired["status"], "rejected")
        self.assertEqual(expired["role_gate"]["reason"], "state_expired")

    def test_auth_callback_result_rejects_unknown_state_validation_status(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=False,
            state_validation={"status": "unexpected"},
        )

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["role_gate"]["reason"], "state_invalid")

    def test_auth_callback_result_rejects_provider_error_without_provider_details(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        result = build_auth_callback_result(
            code="",
            state="",
            provider_error="access_denied",
            state_validation_configured=False,
            token_exchange_configured=False,
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["role_gate"]["status"], "closed")
        self.assertEqual(result["public_message"], "Anmeldung nicht abgeschlossen.")
        self.assertNotIn("access_denied", serialized)

    def test_oidc_role_gate_opens_only_for_verified_admin_claims(self) -> None:
        from nac_identity.oidc_role_gate import evaluate_oidc_role_gate

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_role_gate(
            claims={
                "iss": "https://idcs.example.identity.oraclecloud.com:443",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "groups": ["nac-tenant-admin", "other-group"],
                "email": "admin@example.test",
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["schema_version"], "nac.oidc-role-gate/v0.1")
        self.assertEqual(result["status"], "open")
        self.assertEqual(result["reason"], "authorized")
        self.assertEqual(result["role"], "nac-tenant-admin")
        self.assertTrue(result["session_allowed"])
        self.assertFalse(result["guardrails"]["contains_credentials"])
        self.assertFalse(result["guardrails"]["tokens_returned"])
        self.assertFalse(result["guardrails"]["callback_values_exposed"])
        self.assertNotIn(nonce, serialized)
        self.assertNotIn(hashlib.sha256(nonce.encode("utf-8")).hexdigest(), serialized)
        self.assertNotIn("admin@example.test", serialized)

    def test_oidc_role_gate_closes_when_admin_role_is_missing(self) -> None:
        from nac_identity.oidc_role_gate import evaluate_oidc_role_gate

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_role_gate(
            claims={
                "iss": "https://idcs.example.identity.oraclecloud.com:443",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "groups": ["viewer"],
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            state_validation={
                "status": "valid",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
        )

        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["reason"], "role_missing")
        self.assertFalse(result["session_allowed"])

    def test_oidc_role_gate_closes_on_issuer_or_audience_mismatch(self) -> None:
        from nac_identity.oidc_role_gate import evaluate_oidc_role_gate

        nonce = "nonce-from-id-token"
        state_validation = {
            "status": "valid",
            "nonce_bound": True,
            "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
        }
        wrong_issuer = evaluate_oidc_role_gate(
            claims={
                "iss": "https://wrong.example.identity.oraclecloud.com:443",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            state_validation=state_validation,
        )
        wrong_audience = evaluate_oidc_role_gate(
            claims={
                "iss": "https://idcs.example.identity.oraclecloud.com:443",
                "aud": "wrong-client",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            state_validation=state_validation,
        )

        self.assertEqual(wrong_issuer["status"], "closed")
        self.assertEqual(wrong_issuer["reason"], "issuer_mismatch")
        self.assertEqual(wrong_audience["status"], "closed")
        self.assertEqual(wrong_audience["reason"], "audience_mismatch")

    def test_oidc_role_gate_closes_on_missing_or_mismatched_nonce_binding(self) -> None:
        from nac_identity.oidc_role_gate import evaluate_oidc_role_gate

        result_without_binding = evaluate_oidc_role_gate(
            claims={
                "iss": "https://idcs.example.identity.oraclecloud.com:443",
                "aud": "notariat8_nac_app",
                "nonce": "nonce-from-id-token",
                "groups": ["nac-tenant-admin"],
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            state_validation={"status": "valid", "nonce_bound": False},
        )
        result_with_mismatch = evaluate_oidc_role_gate(
            claims={
                "iss": "https://idcs.example.identity.oraclecloud.com:443",
                "aud": "notariat8_nac_app",
                "nonce": "nonce-from-id-token",
                "groups": ["nac-tenant-admin"],
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            state_validation={
                "status": "valid",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(b"different-nonce").hexdigest(),
            },
        )

        self.assertEqual(result_without_binding["status"], "closed")
        self.assertEqual(result_without_binding["reason"], "nonce_not_bound")
        self.assertEqual(result_with_mismatch["status"], "closed")
        self.assertEqual(result_with_mismatch["reason"], "nonce_mismatch")

    def test_oidc_role_gate_closes_on_missing_expected_issuer_or_audience(self) -> None:
        from nac_identity.oidc_role_gate import evaluate_oidc_role_gate

        nonce = "nonce-from-id-token"
        claims = {
            "iss": "https://idcs.example.identity.oraclecloud.com:443",
            "aud": "notariat8_nac_app",
            "nonce": nonce,
            "groups": ["nac-tenant-admin"],
        }
        state_validation = {
            "status": "valid",
            "nonce_bound": True,
            "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
        }
        missing_issuer = evaluate_oidc_role_gate(
            claims=claims,
            expected_issuer="",
            expected_audience="notariat8_nac_app",
            state_validation=state_validation,
        )
        missing_audience = evaluate_oidc_role_gate(
            claims=claims,
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="",
            state_validation=state_validation,
        )
        all_empty = evaluate_oidc_role_gate(
            claims={
                "iss": "",
                "aud": "",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
            },
            expected_issuer="",
            expected_audience="",
            state_validation=state_validation,
        )

        self.assertEqual(missing_issuer["status"], "closed")
        self.assertEqual(missing_issuer["reason"], "issuer_mismatch")
        self.assertEqual(missing_audience["status"], "closed")
        self.assertEqual(missing_audience["reason"], "audience_mismatch")
        self.assertEqual(all_empty["status"], "closed")
        self.assertEqual(all_empty["reason"], "issuer_mismatch")

    def test_oidc_role_gate_closes_on_whitespace_modified_claims(self) -> None:
        from nac_identity.oidc_role_gate import evaluate_oidc_role_gate

        nonce = "nonce-from-id-token"
        state_validation = {
            "status": "valid",
            "nonce_bound": True,
            "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
        }
        issuer_with_space = evaluate_oidc_role_gate(
            claims={
                "iss": " https://idcs.example.identity.oraclecloud.com:443",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            state_validation=state_validation,
        )
        audience_with_space = evaluate_oidc_role_gate(
            claims={
                "iss": "https://idcs.example.identity.oraclecloud.com:443",
                "aud": "notariat8_nac_app ",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            state_validation=state_validation,
        )
        nonce_with_space = evaluate_oidc_role_gate(
            claims={
                "iss": "https://idcs.example.identity.oraclecloud.com:443",
                "aud": "notariat8_nac_app",
                "nonce": f" {nonce}",
                "groups": ["nac-tenant-admin"],
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            state_validation=state_validation,
        )

        self.assertEqual(issuer_with_space["status"], "closed")
        self.assertEqual(issuer_with_space["reason"], "issuer_mismatch")
        self.assertEqual(audience_with_space["status"], "closed")
        self.assertEqual(audience_with_space["reason"], "audience_mismatch")
        self.assertEqual(nonce_with_space["status"], "closed")
        self.assertEqual(nonce_with_space["reason"], "nonce_mismatch")

    def test_role_case_gate_opens_only_for_bound_session_role_tenant_case_and_purpose(self) -> None:
        from nac_identity.role_case_gate import evaluate_role_case_gate

        result = evaluate_role_case_gate(
            session_validation={
                "status": "valid",
                "session": {"protected_start_page_allowed": True, "workspace_opened": False},
                "server_session": {"status": "active", "audit_event_id": "audit-secret-1"},
            },
            role_gate={"status": "open", "role": "nac-notary", "session_allowed": True},
            tenant_context={"status": "bound", "tenant_authorized": True, "tenant_hint": "myjur"},
            case_context={
                "status": "bound",
                "case_authorized": True,
                "case_id": "case-secret-1",
                "case_type": "immobilienkaufvertrag",
            },
            purpose_context={"status": "bound", "purpose_allowed": True, "purpose": "protected_status_review"},
            subject_matter_roles=["nac-notary", "nac-case-worker"],
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["schema_version"], "nac.role-case-gate/v0.1")
        self.assertEqual(result["status"], "open")
        self.assertEqual(result["reason"], "authorized")
        self.assertEqual(result["allowed_surface"], "protected_status_metadata")
        self.assertTrue(result["tenant_bound"])
        self.assertTrue(result["case_bound"])
        self.assertTrue(result["purpose_bound"])
        self.assertFalse(result["full_workspace_opened"])
        self.assertFalse(result["mandate_data_loaded"])
        self.assertFalse(result["guardrails"]["contains_credentials"])
        self.assertFalse(result["guardrails"]["tokens_returned"])
        self.assertFalse(result["guardrails"]["claims_exposed"])
        self.assertFalse(result["guardrails"]["session_identifier_exposed"])
        self.assertFalse(result["guardrails"]["case_identifier_exposed"])
        self.assertFalse(result["guardrails"]["mandate_content_exposed"])
        self.assertEqual(
            result["audit_evidence"],
            {
                "schema_version": "nac.role-case-gate.audit/v0.1",
                "status": "recorded",
                "reason_class": "authorized",
                "checks": {
                    "session_valid": True,
                    "protected_start_allowed": True,
                    "subject_matter_role_matched": True,
                    "tenant_bound": True,
                    "case_bound": True,
                    "purpose_bound": True,
                    "four_eyes_satisfied": True,
                },
                "redaction": {
                    "contains_session_identifier": False,
                    "contains_tenant_identifier": False,
                    "contains_case_identifier": False,
                    "contains_claim_values": False,
                    "contains_email": False,
                    "contains_provider_details": False,
                    "contains_callback_values": False,
                    "contains_mandate_content": False,
                },
            },
        )
        self.assertNotIn("case-secret-1", serialized)
        self.assertNotIn("audit-secret-1", serialized)
        self.assertNotIn("myjur", serialized)
        self.assertNotIn("immobilienkaufvertrag", serialized)

    def test_role_case_gate_fails_closed_for_missing_bindings_and_four_eyes(self) -> None:
        from nac_identity.role_case_gate import evaluate_role_case_gate

        base = {
            "session_validation": {
                "status": "valid",
                "session": {"protected_start_page_allowed": True, "workspace_opened": False},
                "server_session": {"status": "active"},
            },
            "role_gate": {"status": "open", "role": "nac-notary", "session_allowed": True},
            "tenant_context": {"status": "bound", "tenant_authorized": True},
            "case_context": {"status": "bound", "case_authorized": True},
            "purpose_context": {"status": "bound", "purpose_allowed": True},
            "subject_matter_roles": ["nac-notary"],
        }
        scenarios = [
            ("session_missing", {"session_validation": {"status": "missing"}}),
            ("session_revoked", {"session_validation": {"status": "revoked"}}),
            ("role_missing", {"role_gate": {"status": "closed", "role": "nac-notary"}}),
            ("role_missing", {"role_gate": {"status": "open", "role": "nac-billing-viewer"}}),
            ("tenant_mismatch", {"tenant_context": {"status": "bound", "tenant_authorized": False}}),
            ("case_missing", {"case_context": {"status": "unbound", "case_authorized": False}}),
            ("purpose_missing", {"purpose_context": {"status": "bound", "purpose_allowed": False}}),
            ("four_eyes_required", {"requires_four_eyes": True, "four_eyes_approval": None}),
        ]

        for expected_reason, overrides in scenarios:
            payload = dict(base)
            payload.update(overrides)
            with self.subTest(expected_reason=expected_reason, overrides=sorted(overrides)):
                result = evaluate_role_case_gate(**payload)

            self.assertEqual(result["status"], "closed")
            self.assertEqual(result["reason"], expected_reason)
            self.assertEqual(result["allowed_surface"], "none")
            self.assertFalse(result["full_workspace_opened"])
            self.assertFalse(result["mandate_data_loaded"])
            self.assertFalse(result["guardrails"]["case_identifier_exposed"])
            self.assertFalse(result["guardrails"]["session_identifier_exposed"])
            self.assertEqual(result["audit_evidence"]["reason_class"], expected_reason)
            self.assertFalse(result["audit_evidence"]["redaction"]["contains_case_identifier"])
            self.assertFalse(result["audit_evidence"]["redaction"]["contains_session_identifier"])

    def test_role_case_gate_returns_explicit_safe_reason_classes(self) -> None:
        from nac_identity.role_case_gate import ROLE_CASE_GATE_REASON_CLASSES

        self.assertEqual(
            ROLE_CASE_GATE_REASON_CLASSES,
            (
                "session_missing",
                "session_revoked",
                "session_expired",
                "role_missing",
                "tenant_mismatch",
                "case_missing",
                "purpose_missing",
                "four_eyes_required",
            ),
        )

    def test_role_case_gate_returns_redacted_audit_evidence_without_subject_values(self) -> None:
        from nac_identity.role_case_gate import evaluate_role_case_gate

        result = evaluate_role_case_gate(
            session_validation={
                "status": "valid",
                "session": {
                    "protected_start_page_allowed": True,
                    "workspace_opened": False,
                    "session_id": "session-secret-1",
                },
                "server_session": {
                    "status": "active",
                    "audit_event_id": "audit-secret-1",
                    "subject": "ofunk@myjur.de",
                },
            },
            role_gate={
                "status": "open",
                "role": "nac-notary",
                "session_allowed": True,
                "claims": {"groups": ["nac-notary"], "email": "ofunk@myjur.de"},
            },
            tenant_context={"status": "bound", "tenant_authorized": True, "tenant_hint": "myjur"},
            case_context={"status": "bound", "case_authorized": True, "case_id": "case-secret-1"},
            purpose_context={"status": "bound", "purpose_allowed": True, "purpose": "workspace"},
            subject_matter_roles=["nac-notary"],
        )
        serialized = json.dumps(result["audit_evidence"], sort_keys=True)

        self.assertEqual(result["audit_evidence"]["schema_version"], "nac.role-case-gate.audit/v0.1")
        self.assertEqual(result["audit_evidence"]["status"], "recorded")
        self.assertEqual(result["audit_evidence"]["reason_class"], "authorized")
        self.assertNotIn("session-secret-1", serialized)
        self.assertNotIn("audit-secret-1", serialized)
        self.assertNotIn("ofunk@myjur.de", serialized)
        self.assertNotIn("myjur", serialized)
        self.assertNotIn("case-secret-1", serialized)
        self.assertNotIn("nac-notary", serialized)
        self.assertFalse(result["audit_evidence"]["redaction"]["contains_session_identifier"])
        self.assertFalse(result["audit_evidence"]["redaction"]["contains_tenant_identifier"])
        self.assertFalse(result["audit_evidence"]["redaction"]["contains_case_identifier"])
        self.assertFalse(result["audit_evidence"]["redaction"]["contains_claim_values"])
        self.assertFalse(result["audit_evidence"]["redaction"]["contains_email"])

    def test_workspace_binding_context_normalizers_preserve_exact_role_and_redact_raw_values(self) -> None:
        from nac_identity.role_case_gate import (
            evaluate_role_case_gate,
            normalize_workspace_case_binding_context,
            normalize_workspace_purpose_binding_context,
            normalize_workspace_role_gate_context,
            normalize_workspace_tenant_binding_context,
        )

        role_gate = normalize_workspace_role_gate_context(role=" nac-notary ", role_gate_open=True)
        tenant_context = normalize_workspace_tenant_binding_context(tenant_bound=True)
        case_context = normalize_workspace_case_binding_context(case_bound=True)
        purpose_context = normalize_workspace_purpose_binding_context(purpose_bound=True)
        serialized_contexts = json.dumps(
            {
                "role_gate": role_gate,
                "tenant_context": tenant_context,
                "case_context": case_context,
                "purpose_context": purpose_context,
            },
            sort_keys=True,
        )

        result = evaluate_role_case_gate(
            session_validation={
                "status": "valid",
                "session": {"protected_start_page_allowed": True, "workspace_opened": False},
            },
            role_gate=role_gate,
            tenant_context=tenant_context,
            case_context=case_context,
            purpose_context=purpose_context,
            subject_matter_roles=["nac-notary"],
        )

        self.assertEqual(role_gate, {"status": "open", "role": " nac-notary ", "session_allowed": True})
        self.assertEqual(tenant_context, {"status": "bound", "tenant_authorized": True})
        self.assertEqual(case_context, {"status": "bound", "case_authorized": True})
        self.assertEqual(purpose_context, {"status": "bound", "purpose_allowed": True})
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["reason"], "role_missing")
        self.assertNotIn("case-secret-1", serialized_contexts)
        self.assertNotIn("myjur", serialized_contexts)
        self.assertNotIn("idcs.example.identity.oraclecloud.com", serialized_contexts)
        self.assertNotIn("admin@example.test", serialized_contexts)

    def test_workspace_binding_context_normalizers_fail_closed_for_unbound_inputs(self) -> None:
        from nac_identity.role_case_gate import (
            normalize_workspace_case_binding_context,
            normalize_workspace_purpose_binding_context,
            normalize_workspace_role_gate_context,
            normalize_workspace_tenant_binding_context,
        )

        self.assertEqual(
            normalize_workspace_role_gate_context(role="nac-notary", role_gate_open=False),
            {"status": "closed", "role": "nac-notary", "session_allowed": False},
        )
        self.assertEqual(
            normalize_workspace_tenant_binding_context(tenant_bound=False),
            {"status": "unbound", "tenant_authorized": False},
        )
        self.assertEqual(
            normalize_workspace_case_binding_context(case_bound=False),
            {"status": "unbound", "case_authorized": False},
        )
        self.assertEqual(
            normalize_workspace_purpose_binding_context(purpose_bound=False),
            {"status": "unbound", "purpose_allowed": False},
        )

    def test_oidc_session_boundary_fails_closed_without_token_exchange(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary

        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(b"nonce-secret-for-id-token").hexdigest(),
            },
            token_exchange_result=None,
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["schema_version"], "nac.oidc-session-boundary/v0.1")
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["token_exchange"]["status"], "not_started")
        self.assertEqual(result["role_gate"]["status"], "closed")
        self.assertEqual(result["role_gate"]["reason"], "token_exchange_not_started")
        self.assertFalse(result["session"]["session_allowed"])
        self.assertFalse(result["session"]["cookie_issued"])
        self.assertFalse(result["session"]["workspace_opened"])
        self.assertFalse(result["guardrails"]["contains_credentials"])
        self.assertFalse(result["guardrails"]["tokens_returned"])
        self.assertNotIn("nonce-secret-for-id-token", serialized)
        self.assertNotIn(hashlib.sha256(b"nonce-secret-for-id-token").hexdigest(), serialized)

    def test_oidc_session_boundary_allows_verified_admin_claim_contract_without_cookie(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["status"], "session_allowed")
        self.assertEqual(result["token_exchange"]["status"], "verified")
        self.assertEqual(result["role_gate"]["status"], "open")
        self.assertTrue(result["session"]["session_allowed"])
        self.assertFalse(result["session"]["cookie_issued"])
        self.assertFalse(result["session"]["workspace_opened"])
        self.assertFalse(result["guardrails"]["tokens_returned"])
        self.assertNotIn(nonce, serialized)
        self.assertNotIn(hashlib.sha256(nonce.encode("utf-8")).hexdigest(), serialized)
        self.assertNotIn("admin@example.test", serialized)

    def test_oidc_session_boundary_issues_secure_cookie_after_verified_role_gate(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        session = result["session"]
        set_cookie = session["set_cookie"]
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["schema_version"], "nac.oidc-session-boundary/v0.2")
        self.assertEqual(result["status"], "session_bound")
        self.assertTrue(session["session_allowed"])
        self.assertTrue(session["cookie_issued"])
        self.assertEqual(session["cookie_name"], "__Host-nac_session")
        self.assertEqual(session["ttl_seconds"], 600)
        self.assertFalse(session["workspace_opened"])
        self.assertIn("__Host-nac_session=", set_cookie)
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("Secure", set_cookie)
        self.assertIn("SameSite=Lax", set_cookie)
        self.assertIn("Path=/", set_cookie)
        self.assertIn("Max-Age=600", set_cookie)
        self.assertFalse(result["guardrails"]["tokens_returned"])
        self.assertTrue(result["guardrails"]["session_cookie_issued"])
        self.assertNotIn(nonce, serialized)
        self.assertNotIn(hashlib.sha256(nonce.encode("utf-8")).hexdigest(), serialized)
        self.assertNotIn("admin@example.test", serialized)
        self.assertNotIn("notariat8_nac_app", set_cookie)
        self.assertNotIn("idcs.example.identity.oraclecloud.com", set_cookie)
        self.assertNotIn("nac-tenant-admin", set_cookie)
        self.assertNotIn(nonce, set_cookie)
        self.assertNotIn("admin@example.test", set_cookie)

    def test_session_cookie_validation_allows_protected_start_page_without_opening_workspace(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary, validate_session_cookie

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = result["session"]["set_cookie"].split(";", 1)[0]

        validation = validate_session_cookie(
            cookie_header,
            signing_key="unit-test-session-signing-key",
            now=1_800_000_010,
        )
        serialized = json.dumps(validation, sort_keys=True)

        self.assertEqual(validation["schema_version"], "nac.session-validation/v0.1")
        self.assertEqual(validation["status"], "valid")
        self.assertTrue(validation["session"]["session_allowed"])
        self.assertTrue(validation["session"]["protected_start_page_allowed"])
        self.assertFalse(validation["session"]["workspace_opened"])
        self.assertFalse(validation["session"]["mandate_data_loaded"])
        self.assertEqual(validation["session"]["ttl_remaining_seconds"], 590)
        self.assertFalse(validation["guardrails"]["tokens_returned"])
        self.assertFalse(validation["guardrails"]["claims_exposed"])
        self.assertFalse(validation["guardrails"]["session_cookie_exposed"])
        self.assertFalse(validation["guardrails"]["mandate_data_loaded"])
        self.assertNotIn(cookie_header, serialized)
        self.assertNotIn("__Host-nac_session=", serialized)
        self.assertNotIn(nonce, serialized)
        self.assertNotIn("admin@example.test", serialized)
        self.assertNotIn("nac-tenant-admin", serialized)
        self.assertNotIn("notariat8_nac_app", serialized)

    def test_session_cookie_validation_requires_active_server_session_record_when_store_is_supplied(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary, validate_session_cookie

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = result["session"]["set_cookie"].split(";", 1)[0]
        payload = _session_cookie_payload(cookie_header)
        audit_log: list[dict[str, object]] = []
        session_store = {
            payload["sid"]: {
                "schema_version": "nac.server-session/v0.1",
                "session_id": payload["sid"],
                "issued_at": payload["iat"],
                "expires_at": payload["exp"],
                "revoked_at": None,
                "audit_event_id": "audit-event-1",
                "contains_credentials": False,
                "tokens_stored": False,
                "claims_stored": False,
            }
        }

        validation = validate_session_cookie(
            cookie_header,
            signing_key="unit-test-session-signing-key",
            now=1_800_000_010,
            session_store=session_store,
            audit_log=audit_log,
        )
        serialized = json.dumps(validation, sort_keys=True)

        self.assertEqual(validation["status"], "valid")
        self.assertEqual(validation["server_session"]["status"], "active")
        self.assertTrue(validation["session"]["protected_start_page_allowed"])
        self.assertFalse(validation["session"]["workspace_opened"])
        self.assertFalse(validation["session"]["mandate_data_loaded"])
        self.assertEqual(audit_log[-1]["event_type"], "session_validation")
        self.assertEqual(audit_log[-1]["status"], "valid")
        self.assertFalse(audit_log[-1]["contains_credentials"])
        self.assertNotIn(str(payload["sid"]), serialized)
        self.assertNotIn(cookie_header, serialized)
        self.assertNotIn(nonce, serialized)
        self.assertNotIn("admin@example.test", serialized)
        self.assertNotIn("nac-tenant-admin", serialized)
        self.assertNotIn("notariat8_nac_app", serialized)

    def test_session_cookie_validation_can_require_server_session_store(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary, validate_session_cookie

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = result["session"]["set_cookie"].split(";", 1)[0]
        audit_log: list[dict[str, object]] = []

        validation = validate_session_cookie(
            cookie_header,
            signing_key="unit-test-session-signing-key",
            now=1_800_000_010,
            require_server_session_store=True,
            audit_log=audit_log,
        )
        serialized = json.dumps(validation, sort_keys=True)

        self.assertEqual(validation["status"], "unavailable")
        self.assertEqual(validation["reason"], "server_session_store_required")
        self.assertFalse(validation["session"]["session_allowed"])
        self.assertFalse(validation["session"]["protected_start_page_allowed"])
        self.assertFalse(validation["session"]["workspace_opened"])
        self.assertFalse(validation["session"]["mandate_data_loaded"])
        self.assertEqual(audit_log[-1]["event_type"], "session_validation")
        self.assertEqual(audit_log[-1]["status"], "unavailable")
        self.assertEqual(audit_log[-1]["reason"], "server_session_store_required")
        self.assertNotIn(cookie_header, serialized)
        self.assertNotIn(nonce, serialized)
        self.assertNotIn("admin@example.test", serialized)
        self.assertNotIn("nac-tenant-admin", serialized)
        self.assertNotIn("notariat8_nac_app", serialized)

    def test_session_cookie_validation_fails_closed_when_server_session_is_missing_revoked_or_expired(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary, validate_session_cookie

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = result["session"]["set_cookie"].split(";", 1)[0]
        payload = _session_cookie_payload(cookie_header)
        active_record = {
            "schema_version": "nac.server-session/v0.1",
            "session_id": payload["sid"],
            "issued_at": payload["iat"],
            "expires_at": payload["exp"],
            "contains_credentials": False,
            "tokens_stored": False,
            "claims_stored": False,
        }

        missing = validate_session_cookie(
            cookie_header,
            signing_key="unit-test-session-signing-key",
            now=1_800_000_010,
            session_store={},
        )
        revoked = validate_session_cookie(
            cookie_header,
            signing_key="unit-test-session-signing-key",
            now=1_800_000_010,
            session_store={payload["sid"]: {**active_record, "revoked_at": 1_800_000_005}},
        )
        store_expired = validate_session_cookie(
            cookie_header,
            signing_key="unit-test-session-signing-key",
            now=1_800_000_010,
            session_store={payload["sid"]: {**active_record, "expires_at": 1_800_000_009}},
        )

        self.assertEqual(missing["status"], "missing")
        self.assertEqual(missing["reason"], "server_session_missing")
        self.assertEqual(revoked["status"], "revoked")
        self.assertEqual(revoked["reason"], "server_session_revoked")
        self.assertEqual(store_expired["status"], "expired")
        self.assertEqual(store_expired["reason"], "server_session_expired")
        for validation in (missing, revoked, store_expired):
            self.assertFalse(validation["session"]["session_allowed"])
            self.assertFalse(validation["session"]["protected_start_page_allowed"])
            self.assertFalse(validation["session"]["workspace_opened"])
            self.assertFalse(validation["session"]["mandate_data_loaded"])
            self.assertFalse(validation["guardrails"]["tokens_returned"])
            self.assertFalse(validation["guardrails"]["claims_exposed"])
            self.assertFalse(validation["guardrails"]["session_cookie_exposed"])

    def test_session_cookie_validation_accepts_runtime_session_store_adapter(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary, validate_session_cookie
        from nac_identity.session_store import MappingSessionStoreAdapter

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = result["session"]["set_cookie"].split(";", 1)[0]
        payload = _session_cookie_payload(cookie_header)
        adapter = MappingSessionStoreAdapter(
            {
                payload["sid"]: {
                    "schema_version": "nac.server-session/v0.1",
                    "session_id": payload["sid"],
                    "issued_at": payload["iat"],
                    "expires_at": payload["exp"],
                    "revoked_at": None,
                    "audit_event_id": "audit-event-1",
                    "contains_credentials": False,
                    "tokens_stored": False,
                    "claims_stored": False,
                }
            }
        )

        validation = validate_session_cookie(
            cookie_header,
            signing_key="unit-test-session-signing-key",
            now=1_800_000_010,
            session_store=adapter,
        )
        serialized = json.dumps(validation, sort_keys=True)

        self.assertEqual(validation["status"], "valid")
        self.assertEqual(validation["server_session"]["status"], "active")
        self.assertTrue(validation["session"]["protected_start_page_allowed"])
        self.assertFalse(validation["session"]["workspace_opened"])
        self.assertNotIn(str(payload["sid"]), serialized)
        self.assertNotIn(cookie_header, serialized)
        self.assertNotIn(nonce, serialized)
        self.assertNotIn("admin@example.test", serialized)
        self.assertNotIn("notariat8_nac_app", serialized)

    def test_session_cookie_validation_fails_closed_when_runtime_session_store_adapter_is_unavailable(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary, validate_session_cookie
        from nac_identity.session_store import RuntimeSessionStoreAdapter

        class UnavailableSessionStore(RuntimeSessionStoreAdapter):
            def get_session_record(self, session_id: str):  # type: ignore[no-untyped-def]
                raise RuntimeError(f"store down for {session_id} with client_secret=password")

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = result["session"]["set_cookie"].split(";", 1)[0]

        validation = validate_session_cookie(
            cookie_header,
            signing_key="unit-test-session-signing-key",
            now=1_800_000_010,
            session_store=UnavailableSessionStore(),
        )
        serialized = json.dumps(validation, sort_keys=True)

        self.assertEqual(validation["status"], "unavailable")
        self.assertEqual(validation["reason"], "server_session_store_unavailable")
        self.assertFalse(validation["session"]["session_allowed"])
        self.assertFalse(validation["session"]["protected_start_page_allowed"])
        self.assertFalse(validation["session"]["workspace_opened"])
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("password", serialized)
        self.assertNotIn(cookie_header, serialized)
        self.assertNotIn(nonce, serialized)

    def test_session_cookie_validation_fails_closed_for_tampered_or_expired_cookie(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary, validate_session_cookie

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = result["session"]["set_cookie"].split(";", 1)[0]
        tampered_cookie = f"{cookie_header}x"

        tampered = validate_session_cookie(
            tampered_cookie,
            signing_key="unit-test-session-signing-key",
            now=1_800_000_010,
        )
        expired = validate_session_cookie(
            cookie_header,
            signing_key="unit-test-session-signing-key",
            now=1_800_000_601,
        )

        self.assertEqual(tampered["status"], "invalid")
        self.assertEqual(expired["status"], "expired")
        self.assertFalse(tampered["session"]["session_allowed"])
        self.assertFalse(tampered["session"]["protected_start_page_allowed"])
        self.assertFalse(expired["session"]["session_allowed"])
        self.assertFalse(expired["session"]["protected_start_page_allowed"])
        self.assertFalse(tampered["session"]["workspace_opened"])
        self.assertFalse(expired["session"]["workspace_opened"])
        self.assertFalse(tampered["guardrails"]["session_cookie_exposed"])
        self.assertFalse(expired["guardrails"]["session_cookie_exposed"])

    def test_oidc_session_boundary_does_not_issue_cookie_when_role_gate_is_closed(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["wrong-role"],
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
            session_signing_key="unit-test-session-signing-key",
        )

        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["role_gate"]["status"], "closed")
        self.assertEqual(result["role_gate"]["reason"], "role_missing")
        self.assertFalse(result["session"]["session_allowed"])
        self.assertFalse(result["session"]["cookie_issued"])
        self.assertNotIn("set_cookie", result["session"])

    def test_oidc_session_boundary_closes_for_invalid_token_result(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary

        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(b"nonce-from-id-token").hexdigest(),
            },
            token_exchange_result={"status": "invalid", "error_description": "provider detail"},
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["token_exchange"]["status"], "invalid")
        self.assertEqual(result["role_gate"]["reason"], "token_invalid")
        self.assertNotIn("provider detail", serialized)

    def test_oidc_session_boundary_marks_jwt_invalid_for_claim_validation_failure(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary

        nonce = "nonce-from-id-token"
        result = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://wrong.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
        )

        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["jwt_validation"]["status"], "invalid")
        self.assertEqual(result["role_gate"]["reason"], "issuer_mismatch")

    def test_oidc_token_exchange_contract_fails_closed_without_server_config(self) -> None:
        from nac_identity.oidc_token_exchange import build_oidc_token_exchange_contract

        contract = build_oidc_token_exchange_contract(
            configured=True,
            code="secret-code-from-idp",
            redirect_uri="",
            token_endpoint="",
            client_id="notariat8_nac_app",
        )
        public_result = contract.public_result()
        session_input = contract.session_input()
        serialized = json.dumps(public_result, sort_keys=True)

        self.assertEqual(public_result["schema_version"], "nac.oidc-token-exchange/v0.1")
        self.assertEqual(public_result["status"], "not_configured")
        self.assertEqual(session_input["status"], "not_configured")
        self.assertFalse(public_result["guardrails"]["contains_credentials"])
        self.assertFalse(public_result["guardrails"]["tokens_returned"])
        self.assertFalse(public_result["guardrails"]["live_token_exchange_performed"])
        self.assertNotIn("secret-code-from-idp", serialized)

    def test_oidc_token_exchange_contract_normalizes_verified_claims_without_public_leak(self) -> None:
        from nac_identity.oidc_token_exchange import build_oidc_token_exchange_contract

        nonce = "nonce-from-id-token"
        contract = build_oidc_token_exchange_contract(
            configured=True,
            code="secret-code-from-idp",
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            exchanger_result={
                "status": "verified",
                "access_token": "sample-access-token-value",
                "refresh_token": "sample-refresh-token-value",
                "id_token": "sample-id-token-value",
                "error_description": "provider detail",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
        )
        public_result = contract.public_result()
        session_input = contract.session_input()
        serialized_public = json.dumps(public_result, sort_keys=True)

        self.assertEqual(public_result["status"], "verified")
        self.assertEqual(session_input["status"], "verified")
        self.assertEqual(session_input["claims"]["aud"], "notariat8_nac_app")
        self.assertFalse(public_result["guardrails"]["contains_credentials"])
        self.assertFalse(public_result["guardrails"]["tokens_returned"])
        self.assertNotIn("secret-code-from-idp", serialized_public)
        self.assertNotIn("sample-access-token-value", serialized_public)
        self.assertNotIn("sample-refresh-token-value", serialized_public)
        self.assertNotIn("sample-id-token-value", serialized_public)
        self.assertNotIn("provider detail", serialized_public)
        self.assertNotIn(nonce, serialized_public)
        self.assertNotIn("admin@example.test", serialized_public)

    def test_oidc_token_exchange_adapter_exchanges_code_without_returning_tokens(self) -> None:
        from nac_identity.oidc_token_exchange import (
            build_oidc_token_exchange_contract,
            exchange_oidc_authorization_code,
        )

        calls: list[dict[str, object]] = []

        def http_post(
            url: str,
            body: bytes,
            headers: dict[str, str],
            timeout_seconds: float,
        ) -> dict[str, object]:
            calls.append(
                {
                    "url": url,
                    "body": body,
                    "headers": headers,
                    "timeout_seconds": timeout_seconds,
                }
            )
            return {
                "status_code": 200,
                "body": json.dumps(
                    {
                        "access_token": "sample-access-token-value",
                        "refresh_token": "sample-refresh-token-value",
                        "id_token": "sample-id-token-value",
                    }
                ).encode("utf-8"),
            }

        def verify_id_token(id_token: str) -> dict[str, object]:
            self.assertEqual(id_token, "sample-id-token-value")
            return {
                "iss": "https://idcs.example.identity.oraclecloud.com:443",
                "aud": "notariat8_nac_app",
                "nonce": "nonce-from-id-token",
                "groups": ["nac-tenant-admin"],
                "email": "admin@example.test",
            }

        exchange = exchange_oidc_authorization_code(
            code="secret-code-from-idp",
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            client_secret="client-secret-value",
            id_token_verifier=verify_id_token,
            http_post=http_post,
        )
        contract = build_oidc_token_exchange_contract(
            configured=True,
            code="secret-code-from-idp",
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            exchanger_result=exchange,
        )
        public_result = contract.public_result()
        request_body = calls[0]["body"].decode("utf-8")
        serialized_exchange = json.dumps(exchange, sort_keys=True)
        serialized_public = json.dumps(public_result, sort_keys=True)

        self.assertEqual(exchange["status"], "verified")
        self.assertEqual(exchange["claims"]["aud"], "notariat8_nac_app")
        self.assertEqual(public_result["status"], "verified")
        self.assertEqual(public_result["mode"], "server_side_token_exchange")
        self.assertTrue(public_result["guardrails"]["live_token_exchange_performed"])
        self.assertEqual(calls[0]["url"], "https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token")
        self.assertIn("grant_type=authorization_code", request_body)
        self.assertIn("code=secret-code-from-idp", request_body)
        self.assertIn("client_secret=client-secret-value", request_body)
        self.assertNotIn("sample-access-token-value", serialized_exchange)
        self.assertNotIn("sample-refresh-token-value", serialized_exchange)
        self.assertNotIn("sample-id-token-value", serialized_exchange)
        self.assertNotIn("secret-code-from-idp", serialized_public)
        self.assertNotIn("client-secret-value", serialized_public)
        self.assertNotIn("sample-access-token-value", serialized_public)
        self.assertNotIn("sample-refresh-token-value", serialized_public)
        self.assertNotIn("sample-id-token-value", serialized_public)
        self.assertNotIn("nonce-from-id-token", serialized_public)
        self.assertNotIn("admin@example.test", serialized_public)

    def test_oidc_token_exchange_adapter_fails_closed_without_secret_or_verifier(self) -> None:
        from nac_identity.oidc_token_exchange import exchange_oidc_authorization_code

        calls: list[dict[str, object]] = []

        def http_post(
            url: str,
            body: bytes,
            headers: dict[str, str],
            timeout_seconds: float,
        ) -> dict[str, object]:
            calls.append({"url": url, "body": body, "headers": headers, "timeout_seconds": timeout_seconds})
            return {"status_code": 200, "body": b'{"id_token":"sample-id-token-value"}'}

        missing_secret = exchange_oidc_authorization_code(
            code="secret-code-from-idp",
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            client_secret="",
            id_token_verifier=lambda _id_token: {"aud": "notariat8_nac_app"},
            http_post=http_post,
        )
        missing_verifier = exchange_oidc_authorization_code(
            code="secret-code-from-idp",
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            client_secret="client-secret-value",
            id_token_verifier=None,
            http_post=http_post,
        )
        serialized = json.dumps({"missing_secret": missing_secret, "missing_verifier": missing_verifier}, sort_keys=True)

        self.assertEqual(missing_secret["status"], "not_configured")
        self.assertEqual(missing_verifier["status"], "not_configured")
        self.assertEqual(calls, [])
        self.assertNotIn("secret-code-from-idp", serialized)
        self.assertNotIn("client-secret-value", serialized)
        self.assertNotIn("sample-id-token-value", serialized)

    def test_oidc_token_exchange_adapter_redacts_provider_failures(self) -> None:
        from nac_identity.oidc_token_exchange import exchange_oidc_authorization_code

        def http_post(
            url: str,
            body: bytes,
            headers: dict[str, str],
            timeout_seconds: float,
        ) -> dict[str, object]:
            return {
                "status_code": 400,
                "body": json.dumps(
                    {
                        "error": "invalid_grant",
                        "error_description": "secret-code-from-idp client-secret-value rejected",
                    }
                ).encode("utf-8"),
            }

        result = exchange_oidc_authorization_code(
            code="secret-code-from-idp",
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            client_secret="client-secret-value",
            id_token_verifier=lambda _id_token: {"aud": "notariat8_nac_app"},
            http_post=http_post,
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_class"], "authorization_code_rejected")
        self.assertFalse(result["guardrails"]["provider_error_details_exposed"])
        self.assertNotIn("error_description", serialized)
        self.assertNotIn("secret-code-from-idp", serialized)
        self.assertNotIn("client-secret-value", serialized)

        from nac_identity.oidc_token_exchange import build_oidc_token_exchange_contract

        contract = build_oidc_token_exchange_contract(
            configured=True,
            code="secret-code-from-idp",
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            exchanger_result=result,
        )
        public_result = contract.public_result()
        serialized_public = json.dumps(public_result, sort_keys=True)

        self.assertEqual(public_result["failure_class"], "authorization_code_rejected")
        self.assertNotIn("invalid_grant", serialized_public)
        self.assertNotIn("secret-code-from-idp", serialized_public)
        self.assertNotIn("client-secret-value", serialized_public)

    def test_oidc_token_exchange_adapter_uses_generic_failure_class_for_unknown_provider_errors(self) -> None:
        from nac_identity.oidc_token_exchange import exchange_oidc_authorization_code

        def http_post(
            url: str,
            body: bytes,
            headers: dict[str, str],
            timeout_seconds: float,
        ) -> dict[str, object]:
            return {
                "status_code": 400,
                "body": b'{"error":"vendor_specific_detail","error_description":"do not expose this"}',
            }

        result = exchange_oidc_authorization_code(
            code="secret-code-from-idp",
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            client_secret="client-secret-value",
            id_token_verifier=lambda _id_token: {"aud": "notariat8_nac_app"},
            http_post=http_post,
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_class"], "token_endpoint_rejected")
        self.assertNotIn("vendor_specific_detail", serialized)
        self.assertNotIn("do not expose this", serialized)
        self.assertNotIn("secret-code-from-idp", serialized)
        self.assertNotIn("client-secret-value", serialized)

    def test_oidc_id_token_verifier_accepts_rs256_jwks_claims(self) -> None:
        from nac_identity.oidc_jwt import build_oidc_id_token_verifier

        issuer = "https://idcs.example.identity.oraclecloud.com:443"
        audience = "notariat8_nac_app"
        fetch_urls: list[str] = []

        def fetch_json(url: str) -> dict[str, object]:
            fetch_urls.append(url)
            if url.endswith("/.well-known/openid-configuration"):
                return {"jwks_uri": f"{issuer}/admin/v1/SigningCert/jwk"}
            if url.endswith("/admin/v1/SigningCert/jwk"):
                return {"keys": [_test_jwk()]}
            raise AssertionError(f"unexpected fetch URL: {url}")

        token = _signed_test_id_token(
            {
                "iss": issuer,
                "aud": audience,
                "nonce": "nonce-from-id-token",
                "exp": 4102444800,
                "iat": 1900000000,
                "groups": ["nac-tenant-admin"],
                "email": "admin@example.test",
            }
        )
        verifier = build_oidc_id_token_verifier(
            issuer=issuer,
            audience=audience,
            jwks_fetcher=fetch_json,
            now=1900000100,
        )

        self.assertIsNotNone(verifier)
        claims = verifier(token) if verifier else None

        self.assertIsInstance(claims, dict)
        self.assertEqual(claims["iss"], issuer)
        self.assertEqual(claims["aud"], audience)
        self.assertEqual(claims["groups"], ["nac-tenant-admin"])
        self.assertEqual(
            fetch_urls,
            [
                f"{issuer}/.well-known/openid-configuration",
                f"{issuer}/admin/v1/SigningCert/jwk",
            ],
        )

    def test_oidc_id_token_verifier_can_use_separate_discovery_base_url(self) -> None:
        from nac_identity.oidc_jwt import build_oidc_id_token_verifier

        issuer = "https://identity.oraclecloud.com/"
        discovery_base_url = "https://idcs.example.identity.oraclecloud.com:443"
        audience = "notariat8_nac_app"
        fetch_urls: list[str] = []

        def fetch_json(url: str) -> dict[str, object]:
            fetch_urls.append(url)
            if url == f"{discovery_base_url}/.well-known/openid-configuration":
                return {"jwks_uri": f"{discovery_base_url}/admin/v1/SigningCert/jwk"}
            if url == f"{discovery_base_url}/admin/v1/SigningCert/jwk":
                return {"keys": [_test_jwk()]}
            raise AssertionError(f"unexpected fetch URL: {url}")

        token = _signed_test_id_token(
            {
                "iss": issuer.rstrip("/"),
                "aud": audience,
                "exp": 4102444800,
                "iat": 1900000000,
            }
        )
        verifier = build_oidc_id_token_verifier(
            issuer=issuer,
            audience=audience,
            discovery_base_url=discovery_base_url,
            jwks_fetcher=fetch_json,
            now=1900000100,
        )

        self.assertIsNotNone(verifier)
        claims = verifier(token) if verifier else None

        self.assertIsInstance(claims, dict)
        self.assertEqual(claims["iss"], issuer.rstrip("/"))
        self.assertEqual(
            fetch_urls,
            [
                f"{discovery_base_url}/.well-known/openid-configuration",
                f"{discovery_base_url}/admin/v1/SigningCert/jwk",
            ],
        )

    def test_oidc_id_token_verifier_fetches_oci_identity_jwks_with_signed_fallback(self) -> None:
        from nac_identity.oidc_jwt import build_oci_identity_domain_json_fetcher, build_oidc_id_token_verifier

        issuer = "https://identity.oraclecloud.com/"
        discovery_base_url = "https://idcs.example.identity.oraclecloud.com:443"
        audience = "notariat8_nac_app"
        signed_requests: list[dict[str, object]] = []

        def public_fetcher(url: str) -> dict[str, object]:
            if url == f"{discovery_base_url}/.well-known/openid-configuration":
                return {"jwks_uri": f"{discovery_base_url}/admin/v1/SigningCert/jwk"}
            if url == f"{discovery_base_url}/admin/v1/SigningCert/jwk":
                raise HTTPError(url, 401, "Unauthorized", {}, None)
            raise AssertionError(f"unexpected fetch URL: {url}")

        class FakeSigner:
            def __call__(self, request: object, enforce_content_headers: bool = True) -> object:
                request.headers["Authorization"] = "Signature unit-test"
                signed_requests.append(
                    {
                        "path_url": request.path_url,
                        "enforce_content_headers": enforce_content_headers,
                    }
                )
                return request

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *_args: object) -> bool:
                return False

            def read(self) -> bytes:
                return json.dumps({"keys": [_test_jwk()]}).encode("utf-8")

        def signed_urlopen(request: object, timeout: float = 0) -> FakeResponse:
            self.assertEqual(timeout, 5.0)
            self.assertEqual(request.full_url, f"{discovery_base_url}/admin/v1/SigningCert/jwk")
            self.assertEqual(request.get_header("Authorization"), "Signature unit-test")
            return FakeResponse()

        fetcher = build_oci_identity_domain_json_fetcher(
            public_fetcher=public_fetcher,
            signer_factory=FakeSigner,
        )
        token = _signed_test_id_token(
            {
                "iss": issuer.rstrip("/"),
                "aud": audience,
                "exp": 4102444800,
                "iat": 1900000000,
            }
        )
        verifier = build_oidc_id_token_verifier(
            issuer=issuer,
            audience=audience,
            discovery_base_url=discovery_base_url,
            jwks_fetcher=fetcher,
            now=1900000100,
        )

        with patch("nac_identity.oidc_jwt.urlopen", side_effect=signed_urlopen):
            claims = verifier(token) if verifier else None

        self.assertIsInstance(claims, dict)
        self.assertEqual(claims["iss"], issuer.rstrip("/"))
        self.assertEqual(
            signed_requests,
            [{"path_url": "/admin/v1/SigningCert/jwk", "enforce_content_headers": False}],
        )

    def test_oci_identity_domain_json_fetcher_does_not_sign_untrusted_hosts(self) -> None:
        from nac_identity.oidc_jwt import build_oci_identity_domain_json_fetcher

        signed = False

        def public_fetcher(url: str) -> dict[str, object]:
            raise HTTPError(url, 401, "Unauthorized", {}, None)

        def signer_factory() -> object:
            nonlocal signed
            signed = True
            return lambda request: request

        fetcher = build_oci_identity_domain_json_fetcher(
            public_fetcher=public_fetcher,
            signer_factory=signer_factory,
        )

        with self.assertRaises(HTTPError):
            fetcher("https://not-oci.example.test/admin/v1/SigningCert/jwk")

        self.assertFalse(signed)

    def test_oidc_id_token_verifier_fails_closed_for_bad_signature_or_claims(self) -> None:
        from nac_identity.oidc_jwt import build_oidc_id_token_verifier

        issuer = "https://idcs.example.identity.oraclecloud.com:443"
        audience = "notariat8_nac_app"

        def fetch_json(url: str) -> dict[str, object]:
            if url.endswith("/.well-known/openid-configuration"):
                return {"jwks_uri": f"{issuer}/admin/v1/SigningCert/jwk"}
            return {"keys": [_test_jwk()]}

        verifier = build_oidc_id_token_verifier(
            issuer=issuer,
            audience=audience,
            jwks_fetcher=fetch_json,
            now=1900000100,
        )
        self.assertIsNotNone(verifier)
        valid_claims = {
            "iss": issuer,
            "aud": audience,
            "exp": 4102444800,
            "iat": 1900000000,
            "groups": ["nac-tenant-admin"],
        }
        token = _signed_test_id_token(valid_claims)
        wrong_audience = _signed_test_id_token({**valid_claims, "aud": "other-client"})
        expired = _signed_test_id_token({**valid_claims, "exp": 1899999999})
        bad_signature = token[:-2] + "aa"

        self.assertIsNone(verifier(wrong_audience) if verifier else None)
        self.assertIsNone(verifier(expired) if verifier else None)
        self.assertIsNone(verifier(bad_signature) if verifier else None)

        unavailable_verifier = build_oidc_id_token_verifier(
            issuer=issuer,
            audience=audience,
            jwks_fetcher=lambda _url: (_ for _ in ()).throw(RuntimeError("idp unavailable")),
            now=1900000100,
        )
        self.assertIsNone(unavailable_verifier(token) if unavailable_verifier else None)

    def test_auth_callback_result_consumes_live_exchange_adapter_without_opening_workspace(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result
        from nac_identity.oidc_token_exchange import exchange_oidc_authorization_code

        nonce = "nonce-from-id-token"

        def http_post(
            url: str,
            body: bytes,
            headers: dict[str, str],
            timeout_seconds: float,
        ) -> dict[str, object]:
            return {"status_code": 200, "body": b'{"id_token":"sample-id-token-value"}'}

        exchange = exchange_oidc_authorization_code(
            code="secret-code-from-idp",
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            client_secret="client-secret-value",
            id_token_verifier=lambda _id_token: {
                "iss": "https://idcs.example.identity.oraclecloud.com:443",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
                "email": "admin@example.test",
            },
            http_post=http_post,
        )
        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=True,
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result=exchange,
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["status"], "received")
        self.assertEqual(result["token_exchange"]["status"], "verified")
        self.assertEqual(result["token_exchange"]["mode"], "server_side_token_exchange")
        self.assertEqual(result["session_boundary"]["status"], "session_allowed")
        self.assertEqual(result["role_gate"]["status"], "open")
        self.assertFalse(result["guardrails"]["workspace_opened"])
        self.assertFalse(result["guardrails"]["session_cookie_issued"])
        self.assertNotIn("secret-code-from-idp", serialized)
        self.assertNotIn("state-redacted", serialized)
        self.assertNotIn("client-secret-value", serialized)
        self.assertNotIn("sample-id-token-value", serialized)
        self.assertNotIn(nonce, serialized)
        self.assertNotIn("admin@example.test", serialized)

    def test_auth_callback_result_points_to_token_claim_role_gate_contract(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=False,
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(b"nonce-secret-for-id-token").hexdigest(),
            },
        )

        self.assertEqual(result["status"], "received")
        self.assertEqual(result["role_gate"]["status"], "closed")
        self.assertEqual(result["next_step"], "exchange_token_then_evaluate_oidc_role_gate_contract")

    def test_auth_callback_result_includes_session_boundary_contract(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=True,
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(b"nonce-secret-for-id-token").hexdigest(),
            },
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["status"], "received")
        self.assertEqual(result["session_boundary"]["schema_version"], "nac.oidc-session-boundary/v0.1")
        self.assertEqual(result["session_boundary"]["status"], "closed")
        self.assertEqual(result["session_boundary"]["role_gate"]["reason"], "token_exchange_not_started")
        self.assertFalse(result["session_boundary"]["session"]["cookie_issued"])
        self.assertFalse(result["guardrails"]["workspace_opened"])
        self.assertNotIn("secret-code-from-idp", serialized)
        self.assertNotIn("state-redacted", serialized)
        self.assertNotIn(hashlib.sha256(b"nonce-secret-for-id-token").hexdigest(), serialized)

    def test_auth_callback_result_can_consume_verified_claims_contract_without_opening_workspace(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        nonce = "nonce-from-id-token"
        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=True,
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "access_token": "sample-access-token-value",
                "id_token": "sample-id-token-value",
                "error_description": "provider detail",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["session_boundary"]["status"], "session_allowed")
        self.assertEqual(result["role_gate"]["status"], "open")
        self.assertTrue(result["session_boundary"]["session"]["session_allowed"])
        self.assertFalse(result["session_boundary"]["session"]["cookie_issued"])
        self.assertFalse(result["guardrails"]["workspace_opened"])
        self.assertNotIn("secret-code-from-idp", serialized)
        self.assertNotIn("state-redacted", serialized)
        self.assertNotIn("sample-access-token-value", serialized)
        self.assertNotIn("sample-id-token-value", serialized)
        self.assertNotIn("provider detail", serialized)
        self.assertNotIn(nonce, serialized)
        self.assertNotIn("admin@example.test", serialized)

    def test_auth_callback_result_marks_verified_claims_forwarded_to_role_gate_without_exposure(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        nonce = "nonce-from-id-token"
        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=True,
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "mode": "server_side_token_exchange",
                "live_token_exchange_performed": True,
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["claim_boundary"]["schema_version"], "nac.oidc-claim-boundary/v0.1")
        self.assertEqual(result["claim_boundary"]["status"], "verified")
        self.assertTrue(result["claim_boundary"]["claims_forwarded_to_role_gate"])
        self.assertTrue(result["claim_boundary"]["role_gate_evaluated"])
        self.assertFalse(result["claim_boundary"]["claims_exposed"])
        self.assertFalse(result["claim_boundary"]["tokens_returned"])
        self.assertEqual(result["session_boundary"]["claim_boundary"], result["claim_boundary"])
        self.assertEqual(result["role_gate"]["status"], "open")
        self.assertNotIn("admin@example.test", serialized)
        self.assertNotIn(nonce, serialized)
        self.assertNotIn("secret-code-from-idp", serialized)

    def test_auth_callback_result_ignores_verified_exchange_when_metadata_is_missing(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        nonce = "nonce-from-id-token"
        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=True,
            redirect_uri="",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "access_token": "sample-access-token-value",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertEqual(result["token_exchange"]["status"], "not_configured")
        self.assertEqual(result["token_exchange"]["configuration"], "metadata_missing")
        self.assertEqual(result["role_gate"]["status"], "closed")
        self.assertEqual(result["role_gate"]["reason"], "token_exchange_not_configured")
        self.assertFalse(result["session_boundary"]["session"]["session_allowed"])
        self.assertNotIn("sample-access-token-value", serialized)
        self.assertNotIn(nonce, serialized)
        self.assertNotIn("admin@example.test", serialized)

    def test_auth_callback_result_ignores_verified_claims_when_token_exchange_is_not_configured(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        nonce = "nonce-from-id-token"
        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=True,
            token_exchange_configured=False,
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
        )

        self.assertEqual(result["token_exchange"]["configuration"], "not_configured")
        self.assertEqual(result["token_exchange"]["status"], "not_configured")
        self.assertEqual(result["role_gate"]["status"], "closed")
        self.assertEqual(result["role_gate"]["reason"], "token_exchange_not_configured")
        self.assertFalse(result["session_boundary"]["session"]["session_allowed"])

    def test_auth_callback_result_ignores_state_validation_when_state_validation_is_not_configured(self) -> None:
        from nac_identity.oci_callback import build_auth_callback_result

        nonce = "nonce-from-id-token"
        result = build_auth_callback_result(
            code="secret-code-from-idp",
            state="state-redacted",
            provider_error="",
            state_validation_configured=False,
            token_exchange_configured=True,
            redirect_uri="https://app.notariat8.de/auth/callback",
            token_endpoint="https://idcs.example.identity.oraclecloud.com:443/oauth2/v1/token",
            client_id="notariat8_nac_app",
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs.example.identity.oraclecloud.com:443",
                    "aud": "notariat8_nac_app",
                    "nonce": nonce,
                    "groups": ["nac-tenant-admin"],
                },
            },
            expected_issuer="https://idcs.example.identity.oraclecloud.com:443",
            expected_audience="notariat8_nac_app",
        )

        self.assertEqual(result["state_validation"]["status"], "not_configured")
        self.assertEqual(result["role_gate"]["status"], "closed")
        self.assertEqual(result["role_gate"]["reason"], "state_not_configured")
        self.assertFalse(result["session_boundary"]["session"]["session_allowed"])

    def test_login_intent_rejects_non_https_redirect_uri(self) -> None:
        from nac_identity.oci_login import build_login_intent

        with self.assertRaises(ValueError) as error:
            build_login_intent(
                tenant_hint="notariat-musterstadt",
                identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
                client_id="nac-web-app",
                redirect_uri="http://app.notariat8.de/auth/callback",
            )

        self.assertIn("redirect_uri_invalid", str(error.exception))

    def test_login_intent_rejects_non_oci_identity_domain_url(self) -> None:
        from nac_identity.oci_login import build_login_intent

        with self.assertRaises(ValueError) as error:
            build_login_intent(
                tenant_hint="notariat-musterstadt",
                identity_domain_url="https://login.example.com",
                client_id="nac-web-app",
                redirect_uri="https://app.notariat8.de/auth/callback",
            )

        self.assertIn("identity_domain_url_not_oci_identity_domain", str(error.exception))


if __name__ == "__main__":
    unittest.main()
