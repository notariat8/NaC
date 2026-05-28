from __future__ import annotations

from nac_identity.oci_tenant import check_domain_ready


def build_customer_tenant_plan(
    *,
    domain: str,
    tenant_slug: str,
    admin_email: str,
    saas_admin_email: str,
) -> dict:
    readiness = check_domain_ready(domain=domain, tenant_slug=tenant_slug, admin_email=admin_email)
    if not readiness["ready"]:
        raise ValueError(", ".join(readiness["blocking_findings"]))

    normalized_saas_admin = saas_admin_email.strip().lower()
    if "@" not in normalized_saas_admin:
        raise ValueError("saas_admin_email_invalid")

    normalized_domain = readiness["domain"]
    normalized_slug = readiness["tenant_slug"]
    tenant_id = f"tenant.{normalized_slug}"
    compartment_name = f"nac-{normalized_slug}"

    return {
        "schema_version": "nac.customer-tenant-plan/v0.1",
        "tenant": {
            "tenant_id": tenant_id,
            "slug": normalized_slug,
            "domain": normalized_domain,
        },
        "admin_user": {
            "email": readiness["admin_email"],
            "role": "nac-tenant-admin",
            "console_required": False,
        },
        "saas_admin": {
            "email": normalized_saas_admin,
            "role": "nac-saas-owner",
        },
        "oci": {
            "identity": {
                "admin_domain": "Default",
                "customer_domain_strategy": "single_secondary_domain",
                "customer_domain_key": normalized_domain,
            },
            "resource_isolation": {
                "compartment_strategy": "one_compartment_per_customer_domain",
                "compartment_name": compartment_name,
            },
        },
        "atp": {
            "strategy": "shared_atp_with_tenant_id",
            "tenant_registry_table": "tenant_registry",
            "required_controls": [
                "tenant_registry",
                "tenant_id",
                "row_level_tenant_scope",
                "audit_tenant_context",
            ],
        },
        "readiness": readiness,
        "requires_owner_apply": True,
    }
