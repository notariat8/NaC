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
        self.assertEqual(result["token_exchange"]["status"], "not_started")
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
