from __future__ import annotations

import json
import hashlib
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


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
            "nac.oidc-session-boundary/v0.1",
        )
        self.assertEqual(
            contract["token_exchange_contract_schema"]["schema_version"],
            "nac.oidc-token-exchange/v0.1",
        )
        self.assertTrue(contract["token_exchange_contract_schema"]["server_side_live_adapter_available"])
        self.assertFalse(contract["token_exchange_contract_schema"]["live_token_exchange_performed_by_default"])
        self.assertTrue(contract["token_exchange_contract_schema"]["vault_secret_read_in_contract_slice"])
        self.assertTrue(
            contract["token_exchange_contract_schema"][
                "vault_secret_read_requires_valid_state_code_metadata_and_id_token_verifier"
            ]
        )
        self.assertTrue(contract["callback_session_contract_schema"]["live_token_exchange_in_contract_slice"])
        self.assertTrue(contract["callback_session_contract_schema"]["live_token_exchange_requires_valid_state"])
        self.assertFalse(contract["callback_session_contract_schema"]["session_cookie_issued_in_contract_slice"])
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
        self.assertFalse(result["guardrails"]["provider_error_details_exposed"])
        self.assertNotIn("invalid_grant", serialized)
        self.assertNotIn("secret-code-from-idp", serialized)
        self.assertNotIn("client-secret-value", serialized)

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
