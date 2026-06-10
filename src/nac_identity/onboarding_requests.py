from __future__ import annotations

from datetime import datetime, timezone

from nac_identity.oci_tenant import check_domain_ready


ONBOARDING_REQUEST_SCHEMA_VERSION = "nac.onboarding-request/v0.1"
DEFAULT_REQUEST_STATUS = "submitted"
DEFAULT_INVITATION_STATUS = "not_sent"
DEFAULT_CREATED_BY_SURFACE = "app.notariat8.de"


class OnboardingRequestStoreDisabled(RuntimeError):
    pass


class DisabledOnboardingRequestStore:
    def create_request(self, payload: dict) -> dict:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")

    def get_request(self, request_id: str) -> dict | None:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")

    def list_requests(self, limit: int = 50) -> list[dict]:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")


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
