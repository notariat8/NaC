from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse


DOMAIN_PATTERN = re.compile(
    r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
TENANT_SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@([a-z0-9.-]+\.[a-z]{2,63})$")
FREEMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "yahoo.com",
    "icloud.com",
    "gmx.de",
    "web.de",
    "proton.me",
    "protonmail.com",
}
NAC_TENANT_ROLES = (
    "nac-tenant-admin",
    "nac-notary",
    "nac-case-worker",
    "nac-auditor",
    "nac-billing-viewer",
)


def check_domain_ready(domain: str, tenant_slug: str, admin_email: str) -> dict:
    normalized_domain = _normalize_domain(domain)
    normalized_slug = tenant_slug.strip().lower()
    normalized_email = admin_email.strip().lower()
    findings: list[str] = []

    if not DOMAIN_PATTERN.fullmatch(normalized_domain):
        findings.append("domain_invalid")

    if not TENANT_SLUG_PATTERN.fullmatch(normalized_slug):
        findings.append("tenant_slug_invalid")

    email_match = EMAIL_PATTERN.fullmatch(normalized_email)
    admin_domain = email_match.group(1) if email_match else ""
    if not email_match:
        findings.append("admin_email_invalid")
    elif admin_domain != normalized_domain:
        findings.append("admin_email_domain_mismatch")

    if admin_domain in FREEMAIL_DOMAINS:
        findings.append("admin_email_freemail_domain")

    return {
        "schema_version": "nac.tenant-domain-readiness/v0.1",
        "ready": not findings,
        "domain": normalized_domain,
        "tenant_slug": normalized_slug,
        "admin_email": normalized_email,
        "blocking_findings": findings,
        "verification": {
            "method": "dns_txt",
            "dns_record_name": f"_nac.{normalized_domain}",
            "dns_record_value": f"nac-domain-verification={_verification_value(normalized_domain, normalized_slug)}",
            "must_be_confirmed_before_identity_write": True,
        },
        "next_step": "build_oci_admin_provisioning_dry_run" if not findings else "resolve_blocking_findings",
    }


def build_admin_provisioning_plan(
    *,
    tenant_slug: str,
    domain: str,
    admin_email: str,
    admin_display_name: str,
    identity_domain_url: str,
    identity_domain_id: str,
) -> dict:
    readiness = check_domain_ready(domain=domain, tenant_slug=tenant_slug, admin_email=admin_email)
    if not readiness["ready"]:
        raise ValueError(", ".join(readiness["blocking_findings"]))

    base_url = _normalize_identity_domain_url(identity_domain_url)
    normalized_domain = readiness["domain"]
    normalized_slug = readiness["tenant_slug"]
    normalized_email = readiness["admin_email"]
    admin_name = admin_display_name.strip()
    if not admin_name:
        raise ValueError("admin_display_name_empty")
    domain_id = identity_domain_id.strip()
    if not domain_id:
        raise ValueError("identity_domain_id_empty")

    return {
        "schema_version": "nac.oci-admin-provisioning-plan/v0.1",
        "mode": "dry_run",
        "tenant_slug": normalized_slug,
        "domain": normalized_domain,
        "requires_human_approval": True,
        "approval_gate": "owner_apply_approval",
        "console_access_required_for_end_users": False,
        "target": {
            "provider": "oracle_oci_identity_domains",
            "identity_domain_id": domain_id,
            "identity_domain_url": base_url,
            "users_endpoint": f"{base_url}/admin/v1/Users",
            "groups_endpoint": f"{base_url}/admin/v1/Groups",
        },
        "admin_user": {
            "user_name": normalized_email,
            "display_name": admin_name,
            "primary_email": normalized_email,
            "active": True,
        },
        "groups": list(NAC_TENANT_ROLES),
        "planned_writes": [
            "users.create",
            "groups.ensure",
            "groupMemberships.add",
        ],
        "role_bindings": [
            {
                "group": "nac-tenant-admin",
                "member": normalized_email,
                "purpose": "initial_tenant_administration",
            }
        ],
        "required_permissions": [
            "Identity Domain Administrator",
            "User Administrator",
        ],
        "credential_material_included": False,
        "readiness": readiness,
    }


def build_apply_request(
    plan: dict,
    *,
    dns_verified: bool,
    owner_approval_id: str,
    audit_event_id: str,
    rollback_plan_id: str,
) -> dict:
    findings: list[str] = []
    if plan.get("schema_version") != "nac.oci-admin-provisioning-plan/v0.1":
        findings.append("source_plan_schema_invalid")
    if plan.get("mode") != "dry_run":
        findings.append("source_plan_not_dry_run")
    if plan.get("requires_human_approval") is not True:
        findings.append("source_plan_missing_human_approval")
    if not dns_verified:
        findings.append("dns_not_verified")

    normalized_owner_approval = owner_approval_id.strip()
    normalized_audit_event = audit_event_id.strip()
    normalized_rollback_plan = rollback_plan_id.strip()
    if not normalized_owner_approval:
        findings.append("owner_apply_approval_missing")
    if not normalized_audit_event:
        findings.append("audit_event_missing")
    if not normalized_rollback_plan:
        findings.append("rollback_plan_missing")

    target = plan.get("target") if isinstance(plan.get("target"), dict) else {}
    admin_user = plan.get("admin_user") if isinstance(plan.get("admin_user"), dict) else {}
    planned_writes = plan.get("planned_writes") if isinstance(plan.get("planned_writes"), list) else []
    role_bindings = plan.get("role_bindings") if isinstance(plan.get("role_bindings"), list) else []
    return {
        "schema_version": "nac.oci-identity-apply-request/v0.1",
        "mode": "review_artifact_only",
        "tenant_slug": str(plan.get("tenant_slug", "")),
        "domain": str(plan.get("domain", "")),
        "ready_to_apply": not findings,
        "blocking_findings": findings,
        "productive_write_executed": False,
        "source_plan": {
            "schema_version": str(plan.get("schema_version", "")),
            "mode": str(plan.get("mode", "")),
        },
        "target": {
            "provider": str(target.get("provider", "")),
            "identity_domain_id": str(target.get("identity_domain_id", "")),
            "identity_domain_url": str(target.get("identity_domain_url", "")),
            "users_endpoint": str(target.get("users_endpoint", "")),
            "groups_endpoint": str(target.get("groups_endpoint", "")),
        },
        "admin_user": {
            "user_name": str(admin_user.get("user_name", "")),
            "display_name": str(admin_user.get("display_name", "")),
            "primary_email": str(admin_user.get("primary_email", "")),
        },
        "planned_writes": [str(item) for item in planned_writes],
        "role_bindings": role_bindings,
        "gates": {
            "dns_verified": dns_verified,
            "owner_apply_approval": bool(normalized_owner_approval),
            "audit_event_prepared": bool(normalized_audit_event),
            "rollback_plan_prepared": bool(normalized_rollback_plan),
        },
        "approval": {
            "owner_approval_id": normalized_owner_approval,
            "required_before_connector_apply": True,
        },
        "audit": {
            "audit_event_id": normalized_audit_event,
            "records_intent_only": True,
        },
        "rollback": {
            "rollback_plan_id": normalized_rollback_plan,
            "must_be_reviewed_before_connector_apply": True,
        },
        "guardrails": {
            "contains_credentials": False,
            "connector_apply_in_scope": False,
            "end_user_console_work_allowed": False,
        },
        "next_step": "reviewed_connector_apply" if not findings else "resolve_apply_blocking_findings",
    }


def _normalize_domain(domain: str) -> str:
    return domain.strip().lower().rstrip(".")


def _verification_value(domain: str, tenant_slug: str) -> str:
    digest = hashlib.sha256(f"{domain}:{tenant_slug}".encode("utf-8")).hexdigest()
    return digest[:32]


def _normalize_identity_domain_url(value: str) -> str:
    raw = value.strip().rstrip("/")
    if raw.endswith("/admin/v1"):
        raw = raw.removesuffix("/admin/v1").rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("identity_domain_url_invalid")
    hostname = parsed.hostname or ""
    if not _is_oci_identity_domain_host(hostname):
        raise ValueError("identity_domain_url_not_oci_identity_domain")
    if _is_placeholder_identity_domain_host(hostname):
        raise ValueError("identity_domain_url_placeholder")
    return raw


def _is_oci_identity_domain_host(hostname: str) -> bool:
    normalized = hostname.lower().strip(".")
    return normalized.endswith(".identity.oraclecloud.com") or (
        ".identity." in normalized and normalized.endswith(".oci.oraclecloud.com")
    )


def _is_placeholder_identity_domain_host(hostname: str) -> bool:
    normalized = hostname.lower().strip(".")
    return normalized.startswith("idcs.example.") or ".example." in normalized
