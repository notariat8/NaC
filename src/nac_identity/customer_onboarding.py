from __future__ import annotations

from nac_identity.tenant_readiness import check_domain_ready


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
    team_mail_nickname = f"nac-{normalized_slug}".replace("-", "")

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
        "m365": {
            "identity": {
                "provider": "entra_id",
                "tenant_binding": "microsoft_365_group_membership",
                "customer_domain_key": normalized_domain,
            },
            "workspace": {
                "strategy": "team_per_notary_team",
                "team_display_name": f"NaC {normalized_slug}",
                "mail_nickname": team_mail_nickname[:64],
            },
            "data_plane": {
                "strategy": "teams_sharepoint_graph_rest",
                "sharepoint_as_start_data_store": True,
                "graph_rest_only": True,
                "legacy_sharepoint_api_allowed": False,
            },
        },
        "sharepoint": {
            "strategy": "team_site_lists_and_document_libraries",
            "required_controls": [
                "tenant_id",
                "matter_id",
                "role_bound_site_permission",
                "time_limited_delegation_grant",
                "audit_journal_lite",
            ],
        },
        "readiness": readiness,
        "requires_owner_apply": True,
    }


def build_dns_check_result(
    *,
    expected_name: str,
    expected_value: str,
    observed_values: list[str],
    resolver_error: str = "",
    observed_name: str = "",
) -> dict:
    normalized_expected_name = expected_name.strip().lower().rstrip(".")
    normalized_observed_name = (observed_name or normalized_expected_name).strip().lower().rstrip(".")
    expected_txt = expected_value.strip()
    observed_txt_values = [value.strip() for value in observed_values if value.strip()]
    normalized_error = resolver_error.strip().lower()
    findings: list[str] = []

    if normalized_observed_name != normalized_expected_name:
        status = "wrong_name"
        findings.append("dns_record_name_mismatch")
        retry_allowed = False
        guidance = "Der DNS-TXT-Record steht unter einem anderen Namen. Bitte den Recordnamen korrigieren."
    elif expected_txt in observed_txt_values:
        status = "verified"
        retry_allowed = False
        guidance = "DNS-TXT wurde gefunden. NaC kann die SaaS-Admin-Prüfung vorbereiten."
    elif not observed_txt_values and normalized_error in {"", "not_found", "nxdomain", "no_answer"}:
        status = "pending"
        findings.append("dns_record_not_found")
        retry_allowed = True
        guidance = "DNS-TXT wurde noch nicht gefunden. DNS propagation kann einige Minuten dauern; später erneut prüfen."
    elif observed_txt_values:
        status = "wrong_value"
        findings.append("dns_record_value_mismatch")
        retry_allowed = False
        guidance = "Der DNS-TXT-Record wurde gefunden, aber der Wert passt nicht zur NaC-Challenge."
    else:
        status = "resolver_error"
        findings.append("dns_resolver_error")
        retry_allowed = True
        guidance = "Die DNS-Prüfung konnte nicht abgeschlossen werden. Bitte später erneut prüfen."

    return {
        "schema_version": "nac.dns-readiness-check/v0.1",
        "expected": {
            "name": normalized_expected_name,
            "value": expected_txt,
        },
        "observed": {
            "name": normalized_observed_name,
            "values": observed_txt_values,
            "resolver_error": normalized_error,
        },
        "status": status,
        "findings": findings,
        "retry_allowed": retry_allowed,
        "customer_guidance": guidance,
    }


def build_live_dns_check_result(
    *,
    expected_name: str,
    expected_value: str,
    resolver=None,
) -> dict:
    if resolver is None:
        from nac_identity.dns_txt import resolve_txt_records

        resolver = resolve_txt_records
    observation = resolver(expected_name)
    result = build_dns_check_result(
        expected_name=expected_name,
        expected_value=expected_value,
        observed_name=str(observation.get("name", expected_name)),
        observed_values=[str(value) for value in observation.get("values", [])],
        resolver_error=str(observation.get("resolver_error", "")),
    )
    result["source"] = "live_dns"
    return result
