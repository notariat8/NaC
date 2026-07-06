from __future__ import annotations

import hashlib
import re


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


def check_domain_ready(domain: str, tenant_slug: str, admin_email: str) -> dict:
    normalized_domain = domain.strip().lower().rstrip(".")
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
        "schema_version": "nac.tenant-domain-readiness/v0.2",
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
        "next_step": "build_m365_graph_tenant_workspace_plan" if not findings else "resolve_blocking_findings",
    }


def _verification_value(domain: str, tenant_slug: str) -> str:
    digest = hashlib.sha256(f"{domain}:{tenant_slug}".encode("utf-8")).hexdigest()
    return digest[:32]
