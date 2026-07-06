from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

src_root_text = str(SRC_ROOT)
if src_root_text in sys.path:
    sys.path.remove(src_root_text)
sys.path.insert(0, src_root_text)

from nac_identity.oci_login import build_login_intent  # noqa: E402
from nac_identity.oci_tenant import build_admin_provisioning_plan, build_apply_request, check_domain_ready  # noqa: E402


CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "oci-tenant-identity.contract.json"


def main() -> int:
    errors: list[str] = []
    if not CONTRACT_PATH.exists():
        errors.append("Missing workflows/contracts/oci-tenant-identity.contract.json")
    else:
        _validate_contract(errors)
    _validate_domain_readiness(errors)
    _validate_admin_plan(errors)
    _validate_apply_request(errors)
    _validate_login_intent(errors)

    if errors:
        print("OCI tenant identity validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("OCI tenant identity validation passed.")
    return 0


def _validate_contract(errors: list[str]) -> None:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "nac.oci-tenant-identity-contract/v0.1":
        errors.append("Contract schema_version is unexpected")
    if payload.get("idp") != "oracle_oci_identity_domains":
        errors.append("Contract must use OCI Identity Domains")
    if payload.get("productive_identity_writes_allowed") is not False:
        errors.append("Contract must block productive identity writes")
    if payload.get("end_user_console_work_allowed") is not False:
        errors.append("Contract must block end-user OCI Console work")
    for endpoint in ("/admin/v1/Users", "/admin/v1/Groups", "/oauth2/v1/authorize"):
        if endpoint not in payload.get("oci_identity_domain_endpoints", []):
            errors.append(f"Contract missing endpoint {endpoint}")
    for gate in ("domain_ready", "dry_run_plan", "owner_apply_approval"):
        if gate not in payload.get("required_gates", []):
            errors.append(f"Contract missing gate {gate}")
    for gate in ("dns_verified", "audit_event_prepared", "rollback_plan_prepared"):
        if gate not in payload.get("required_gates", []):
            errors.append(f"Contract missing apply-readiness gate {gate}")
    if payload.get("apply_readiness_schema", {}).get("schema_version") != "nac.oci-identity-apply-request/v0.1":
        errors.append("Contract missing apply readiness schema")
    if payload.get("login_intent_schema", {}).get("schema_version") != "nac.oci-login-intent/v0.1":
        errors.append("Contract missing login intent schema")
    guardrails = payload.get("guardrails", {})
    if guardrails.get("apply_request_contains_credential_material") is not False:
        errors.append("Apply request must not contain credential material")
    if guardrails.get("login_intent_contains_credential_material") is not False:
        errors.append("Login intent must not contain credential material")
    if guardrails.get("tenant_hint_authorizes_access") is not False:
        errors.append("Tenant hint must not authorize access")


def _validate_domain_readiness(errors: list[str]) -> None:
    ready = check_domain_ready(
        domain="kanzlei-notariat.example",
        tenant_slug="kanzlei-notariat",
        admin_email="admin@kanzlei-notariat.example",
    )
    if ready.get("ready") is not True:
        errors.append(f"Expected ready domain check, got {ready.get('blocking_findings')}")
    if ready.get("verification", {}).get("method") != "dns_txt":
        errors.append("Domain readiness must use DNS TXT verification")

    blocked = check_domain_ready(
        domain="kanzlei-notariat.example",
        tenant_slug="kanzlei-notariat",
        admin_email="admin@gmail.com",
    )
    if blocked.get("ready") is not False:
        errors.append("Freemail admin domain must not be ready")
    if "admin_email_domain_mismatch" not in blocked.get("blocking_findings", []):
        errors.append("Freemail admin check must include domain mismatch")


def _validate_admin_plan(errors: list[str]) -> None:
    plan = build_admin_provisioning_plan(
        tenant_slug="kanzlei-notariat",
        domain="kanzlei-notariat.example",
        admin_email="admin@kanzlei-notariat.example",
        admin_display_name="Admin Notariat",
        identity_domain_url="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
        identity_domain_id="ocid1.domain.oc1..aaaaaaaarealidentitydomain",
    )
    if plan.get("mode") != "dry_run":
        errors.append("Admin provisioning plan must be dry_run")
    if plan.get("requires_human_approval") is not True:
        errors.append("Admin provisioning plan must require human approval")
    if plan.get("console_access_required_for_end_users") is not False:
        errors.append("Admin provisioning plan must avoid end-user OCI Console work")
    target = plan.get("target", {})
    if not str(target.get("users_endpoint", "")).endswith("/admin/v1/Users"):
        errors.append("Admin provisioning plan must include Users endpoint")
    if not str(target.get("groups_endpoint", "")).endswith("/admin/v1/Groups"):
        errors.append("Admin provisioning plan must include Groups endpoint")
    serialized = json.dumps(plan, sort_keys=True).lower()
    for forbidden in ("secret", "token", "private_key"):
        if forbidden in serialized:
            errors.append(f"Admin provisioning plan exposes forbidden marker {forbidden}")


def _validate_apply_request(errors: list[str]) -> None:
    plan = build_admin_provisioning_plan(
        tenant_slug="kanzlei-notariat",
        domain="kanzlei-notariat.example",
        admin_email="admin@kanzlei-notariat.example",
        admin_display_name="Admin Notariat",
        identity_domain_url="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
        identity_domain_id="ocid1.domain.oc1..aaaaaaaarealidentitydomain",
    )
    blocked = build_apply_request(
        plan,
        dns_verified=False,
        owner_approval_id="",
        audit_event_id="",
        rollback_plan_id="",
    )
    if blocked.get("ready_to_apply") is not False:
        errors.append("Apply request without gates must not be ready")
    for finding in ("dns_not_verified", "owner_apply_approval_missing", "audit_event_missing", "rollback_plan_missing"):
        if finding not in blocked.get("blocking_findings", []):
            errors.append(f"Blocked apply request missing finding {finding}")

    ready = build_apply_request(
        plan,
        dns_verified=True,
        owner_approval_id="OWNER-APPROVED-32",
        audit_event_id="AUDIT-32",
        rollback_plan_id="ROLLBACK-32",
    )
    if ready.get("ready_to_apply") is not True:
        errors.append(f"Ready apply request blocked by {ready.get('blocking_findings')}")
    if ready.get("productive_write_executed") is not False:
        errors.append("Apply request must not execute productive writes")
    serialized = json.dumps(ready, sort_keys=True).lower()
    for forbidden in ("secret", "token", "private_key"):
        if forbidden in serialized:
            errors.append(f"Apply request exposes forbidden marker {forbidden}")


def _validate_login_intent(errors: list[str]) -> None:
    intent = build_login_intent(
        tenant_hint="notariat-musterstadt",
        identity_domain_url="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
        client_id="nac-web-app",
        redirect_uri="https://app.notariat8.de/auth/callback",
    )
    if intent.get("schema_version") != "nac.oci-login-intent/v0.1":
        errors.append("Login intent schema_version is unexpected")
    if not str(intent.get("authorization_url", "")).startswith(
        "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com/oauth2/v1/authorize?"
    ):
        errors.append("Login intent must point to OCI authorize endpoint")
    if intent.get("tenant_context", {}).get("tenant_authorized_by_hint") is not False:
        errors.append("Login intent must not authorize tenant from hint")
    if intent.get("guardrails", {}).get("nac_role_gate_required_after_idp_login") is not True:
        errors.append("Login intent must require NaC role gate after IdP login")
    if not str(intent.get("oidc", {}).get("state", "")).startswith("state-"):
        errors.append("Login intent state must be server generated")
    if not str(intent.get("oidc", {}).get("nonce", "")).startswith("nonce-"):
        errors.append("Login intent nonce must be server generated")
    serialized = json.dumps(intent, sort_keys=True).lower()
    for forbidden in ("client_secret", "private_key"):
        if forbidden in serialized:
            errors.append(f"Login intent exposes forbidden marker {forbidden}")


if __name__ == "__main__":
    raise SystemExit(main())
