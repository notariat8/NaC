from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable

from nac_identity.tenant_readiness import check_domain_ready


ONBOARDING_REQUEST_SCHEMA_VERSION = "nac.onboarding-request/v0.1"
ONBOARDING_REVIEW_AUDIT_SCHEMA_VERSION = "nac.onboarding-review-audit/v0.1"
DEFAULT_REQUEST_STATUS = "submitted"
DEFAULT_INVITATION_STATUS = "not_sent"
DEFAULT_CREATED_BY_SURFACE = "app.notariat8.de"


class OnboardingRequestStoreDisabled(RuntimeError):
    pass


class OnboardingRequestStoreUnavailable(RuntimeError):
    pass


class DisabledOnboardingRequestStore:
    def create_request(self, payload: dict) -> dict:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")

    def review_request(self, **_kwargs: str) -> dict:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")

    def get_request(self, request_id: str) -> dict | None:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")

    def list_requests(self, limit: int = 50) -> list[dict]:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")


def build_onboarding_request_store_from_env(
    environ: dict[str, str] | None = None,
    *,
    secret_text_provider: Callable[[str], str] | None = None,
    secret_bytes_provider: Callable[[str], bytes] | None = None,
    object_bytes_provider: Callable[[str, str, str], bytes] | None = None,
    connector: Callable[..., Any] | None = None,
) -> DisabledOnboardingRequestStore:
    del secret_text_provider, secret_bytes_provider, object_bytes_provider, connector
    env = environ if environ is not None else os.environ
    mode = env.get("NAC_ONBOARDING_STORE", "").strip().lower()
    if mode in {"atp", "oci", "oracle"}:
        return DisabledOnboardingRequestStore()
    return DisabledOnboardingRequestStore()


def build_onboarding_request(
    *,
    domain: str,
    tenant_slug: str,
    admin_email: str,
    dns_status: str,
    now: str | None = None,
    created_by_surface: str = DEFAULT_CREATED_BY_SURFACE,
) -> dict:
    normalized_dns_status = dns_status.strip().lower()
    if normalized_dns_status != "verified":
        raise ValueError("dns_status_not_verified")

    readiness = check_domain_ready(domain=domain, tenant_slug=tenant_slug, admin_email=admin_email)
    if not readiness["ready"]:
        raise ValueError(", ".join(readiness["blocking_findings"]))

    timestamp = _normalize_timestamp(now)
    request_id = _request_id(readiness["tenant_slug"], timestamp)

    return {
        "schema_version": ONBOARDING_REQUEST_SCHEMA_VERSION,
        "request_id": request_id,
        "tenant_id": f"tenant.{readiness['tenant_slug']}",
        "tenant_slug": readiness["tenant_slug"],
        "domain": readiness["domain"],
        "admin_email": readiness["admin_email"],
        "dns_status": normalized_dns_status,
        "request_status": DEFAULT_REQUEST_STATUS,
        "invitation_status": DEFAULT_INVITATION_STATUS,
        "created_at": timestamp,
        "updated_at": timestamp,
        "created_by_surface": created_by_surface.strip() or DEFAULT_CREATED_BY_SURFACE,
    }


def build_onboarding_review_audit_metadata(
    *,
    request_id: str,
    decision: str,
    reviewed_at: str,
    review_surface: str = "admin.onboarding.review",
) -> dict[str, Any]:
    return {
        "schema_version": ONBOARDING_REVIEW_AUDIT_SCHEMA_VERSION,
        "request_id": request_id.strip(),
        "decision": decision.strip().lower(),
        "reviewed_at": reviewed_at.strip(),
        "review_surface": review_surface,
        "contains_mandate_data": False,
        "customer_mail_dispatched": False,
        "cloud_write_executed": False,
        "legacy_oci_atp_write_executed": False,
        "sharepoint_schema_change_required": False,
    }


def _normalize_timestamp(now: str | None) -> str:
    if now is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    normalized = now.strip()
    if not normalized:
        raise ValueError("created_at_missing")
    if normalized.endswith("+00:00"):
        normalized = normalized[:-6] + "Z"
    datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    return normalized


def _request_id(tenant_slug: str, timestamp: str) -> str:
    compact_time = timestamp.replace("-", "").replace(":", "").replace("T", "_").replace("Z", "")
    return f"onr_{tenant_slug}_{compact_time}"
