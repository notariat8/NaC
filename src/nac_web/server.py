from __future__ import annotations

import base64
import hashlib
import html
import json
import logging
import os
import threading
import webbrowser
from http.cookies import CookieError, SimpleCookie
from decimal import Decimal
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlencode, urlparse

from nac_gnotkg.costs import quote_fee
from nac_identity.customer_onboarding import (
    build_customer_tenant_plan,
    build_dns_check_result,
    build_live_dns_check_result,
)
from nac_identity.onboarding_requests import (
    DisabledOnboardingRequestStore,
    OnboardingRequestStoreDisabled,
    OnboardingRequestStoreUnavailable,
    build_onboarding_request,
    build_onboarding_request_store_from_env,
)
from nac_identity.oidc_callback import build_auth_callback_result
from nac_identity.oidc_login import build_login_intent
from nac_identity.oidc_jwt import build_oidc_id_token_verifier
from nac_identity.oidc_session import DEFAULT_SESSION_COOKIE_NAME, DEFAULT_SESSION_TTL_SECONDS, validate_session_cookie
from nac_identity.session_store import RuntimeSessionStoreAdapter, build_session_store_from_env
from nac_identity.oidc_token_exchange import exchange_oidc_authorization_code
from nac_identity.oidc_state import validate_signed_state
from nac_identity.tenant_readiness import check_domain_ready
from nac_identity.role_case_gate import (
    evaluate_role_case_gate,
    normalize_workspace_case_binding_context,
    normalize_workspace_purpose_binding_context,
    normalize_workspace_role_gate_context,
    normalize_workspace_tenant_binding_context,
)
from nac_runtime.status_source import (
    RuntimeMetadataSource,
    build_first_matter_runtime_metadata_source_from_env,
    build_first_matter_status_display_from_metadata_source,
    resolve_first_matter_runtime_metadata_source,
)
from nac_gnotkg.views import build_cost_review_view
from nac_web.bpmn import (
    BpmnSaveConflict,
    bpmn_model_json,
    bpmn_xml_document,
    find_bpmn_model,
    list_bpmn_models,
    render_bpmn_svg,
    save_bpmn_xml,
)
from notary_kg.catalog import all_case_summaries, load_catalogs
from notary_kg.editor import build_editor_view


STATUS_LABELS_DE = {
    "active_intake": "aktive Aufnahme",
    "draft": "Entwurf",
    "legacy_alias": "Altbezeichnung",
    "open": "offen",
}

ROLE_LABELS_DE = {
    "applicant": "Antragsteller",
    "association": "Verein",
    "client": "Mandant",
    "compliance": "Compliance",
    "developer": "Entwicklung",
    "founder": "Gründer",
    "notary": "Notarin/Notar",
    "notary_clerk": "Notariatsfachkraft",
    "principal": "Vollmachtgeber",
    "spouses": "Ehegatten",
    "system_betreuer": "Systembetreuung",
    "testator": "Erblasser",
}

LOGGER = logging.getLogger(__name__)


class AppResponse:
    def __init__(
        self,
        status: int | HTTPStatus,
        content_type: str,
        body: bytes,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = int(status)
        self.content_type = content_type
        self.body = body
        self.headers = dict(headers or {})

    def __iter__(self):
        yield self.status
        yield self.content_type
        yield self.body


class NaCLocalWebApp:
    def __init__(
        self,
        repo_root: Path,
        dns_resolver=None,
        onboarding_request_store: Any | None = None,
        session_store: RuntimeSessionStoreAdapter | None = None,
        operator_access: bool = False,
        secret_text_provider: Callable[[str], str] | None = None,
        role_membership_resolver: Callable[..., dict[str, Any]] | None = None,
        first_matter_runtime_metadata_source: RuntimeMetadataSource | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.dns_resolver = dns_resolver
        self.onboarding_request_store = onboarding_request_store or DisabledOnboardingRequestStore()
        self.session_store = session_store
        self.operator_access = operator_access
        self.secret_text_provider = secret_text_provider
        self.role_membership_resolver = role_membership_resolver
        self.first_matter_runtime_metadata_source = first_matter_runtime_metadata_source

    def handle(self, path: str, headers: dict[str, str] | None = None) -> tuple[int, str, bytes]:
        parsed = urlparse(path)
        route = unquote(parsed.path)
        try:
            if route == "/" or route == "":
                handoff_page = build_www_n8_handoff_page(parsed.query, dns_resolver=self.dns_resolver)
                if handoff_page is not None:
                    return _html_response(handoff_page)
                return _html_response(build_home_page(self.repo_root))
            if route == "/login":
                return _html_response(build_login_page(parsed.query))
            if route == "/auth/callback":
                status, page, headers = build_auth_callback_page(
                    parsed.query,
                    secret_text_provider=self.secret_text_provider,
                    session_store=self.session_store,
                    role_membership_resolver=self.role_membership_resolver,
                )
                return _html_response(page, status, headers=headers)
            if route == "/workspace":
                status, page = build_protected_workspace_start_page(
                    headers or {},
                    secret_text_provider=self.secret_text_provider,
                    session_store=self.session_store,
                )
                return _html_response(page, status)
            if route == "/workspace/immobilienkaufvertrag":
                status, page = build_protected_first_matter_status_page(
                    headers or {},
                    repo_root=self.repo_root,
                    secret_text_provider=self.secret_text_provider,
                    session_store=self.session_store,
                    runtime_metadata_source=self.first_matter_runtime_metadata_source,
                )
                return _html_response(page, status)
            if route == "/agent/status":
                return self._agent_status_api(headers or {})
            if route == "/onboarding/readiness":
                return _html_response(build_customer_readiness_page(parsed.query, dns_resolver=self.dns_resolver))
            if route == "/onboarding/dns-check":
                return _html_response(self._tenant_dns_check_page(parsed.query))
            if route.startswith("/onboarding/requests/"):
                return self._customer_onboarding_request_status_get(route)
            if route == "/admin/onboarding" or route.startswith("/admin/onboarding/"):
                if not self.operator_access:
                    return _html_response(build_operator_access_required_page(), HTTPStatus.FORBIDDEN)
            if route == "/admin/onboarding/provisioning-preview":
                return _html_response(build_admin_provisioning_preview_page(parsed.query))
            if route == "/admin/onboarding/apply-readiness":
                return _html_response(build_admin_apply_readiness_page(parsed.query))
            if route == "/admin/onboarding":
                return _html_response(self._admin_onboarding_page())
            if route == "/healthz":
                return _json_response({"status": "ok"})
            if route == "/favicon.ico":
                return AppResponse(HTTPStatus.NO_CONTENT, "image/x-icon", b"")
            if route == "/api/tenant/domain-check":
                return self._tenant_domain_check_api(parsed.query)
            if route == "/api/tenant/login-intent":
                return self._tenant_login_intent_api(parsed.query)
            if route == "/api/agent/work/next":
                return self._agent_work_next_api(headers or {})
            if route == "/api/bpmn-moddle":
                return _json_text_response((self.repo_root / "bpmn" / "nac-moddle.json").read_text(encoding="utf-8"))
            if route.startswith("/bpmn/"):
                return self._bpmn_route(route.removeprefix("/bpmn/"))
            if route.startswith("/kg/"):
                return self._kg_route(route.removeprefix("/kg/"))
            if route.startswith("/costs/"):
                return self._cost_route(route.removeprefix("/costs/"))
            if route.startswith("/api/bpmn/"):
                return self._bpmn_api_route(route.removeprefix("/api/bpmn/"))
            if route.startswith("/api/kg/"):
                return self._kg_api_route(route.removeprefix("/api/kg/"))
            if route.startswith("/api/costs/"):
                return self._cost_api_route(route.removeprefix("/api/costs/"))
            if route == "/api/gnotkg/quote":
                return _json_response({"error": "GNotKG-Quote nutzt POST, damit Werte nicht in URL oder Requestlog stehen."}, HTTPStatus.METHOD_NOT_ALLOWED)
        except KeyError as exc:
            return _html_response(_layout("Nicht Gefunden", f"<p>{html.escape(str(exc))}</p>"), HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            return _html_response(_layout("Ungültiges Modell", f"<p>{html.escape(str(exc))}</p>"), HTTPStatus.BAD_REQUEST)
        return _html_response(_layout("Nicht Gefunden", "<p>Diese lokale NaC-Seite gibt es nicht.</p>"), HTTPStatus.NOT_FOUND)

    def handle_post(
        self,
        path: str,
        body: bytes,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str, bytes]:
        parsed = urlparse(path)
        route = unquote(parsed.path)
        try:
            if route == "/agent/leases/prepare":
                return self._agent_lease_prepare_api(headers or {}, body)
            if route == "/api/agent/connect":
                return self._agent_connector_api(headers or {}, body, action="connect")
            if route == "/api/agent/heartbeat":
                return self._agent_connector_api(headers or {}, body, action="heartbeat")
            if route == "/api/agent/work/result":
                return self._agent_connector_api(headers or {}, body, action="work_result")
            if route.startswith("/api/bpmn/"):
                return self._bpmn_api_post(route.removeprefix("/api/bpmn/"), body)
            if route == "/api/gnotkg/quote":
                return self._gnotkg_quote_api_post(body)
            if route == "/onboarding/requests":
                return self._onboarding_request_post(parsed.query, body)
            if route == "/admin/onboarding" or route.startswith("/admin/onboarding/"):
                if not self.operator_access:
                    return _html_response(build_operator_access_required_page(), HTTPStatus.FORBIDDEN)
            if route == "/admin/onboarding/review":
                return self._admin_onboarding_review_post(body)
            if route == "/api/tenant/provision-admin/preview":
                return self._tenant_provision_admin_preview_api_post(body)
        except KeyError as exc:
            return _json_response({"error": str(exc)}, HTTPStatus.NOT_FOUND)
        except BpmnSaveConflict as exc:
            return _json_response({"error": str(exc)}, HTTPStatus.CONFLICT)
        except ValueError as exc:
            return _json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        return _json_response({"error": "Diese lokale NaC-POST-Route gibt es nicht."}, HTTPStatus.NOT_FOUND)

    def _agent_status_api(self, headers: dict[str, str]) -> tuple[int, str, bytes]:
        access = _evaluate_workspace_access(
            headers,
            secret_text_provider=self.secret_text_provider,
            session_store=self.session_store,
        )
        if access["status"] != "open":
            return _agent_fail_closed_response("agent_session_required")
        return _json_response(
            _agent_metadata_payload(
                status="prepared",
                reason_class="metadata_only_no_active_lease",
                lease_status="not_prepared",
            )
        )

    def _agent_lease_prepare_api(self, headers: dict[str, str], body: bytes) -> tuple[int, str, bytes]:
        access = _evaluate_workspace_access(
            headers,
            secret_text_provider=self.secret_text_provider,
            session_store=self.session_store,
        )
        if access["status"] != "open":
            return _agent_fail_closed_response("agent_session_required")
        payload = _safe_json_object(body)
        if _contains_agent_control_blocked_fields(payload):
            return _agent_fail_closed_response("blocked_payload_field")
        return _json_response(
            _agent_metadata_payload(
                status="prepared",
                reason_class="lease_prepare_metadata_only",
                lease_status="prepared",
                extra={
                    "sandbox_binding_id": "sandbox-binding.pending",
                    "sandbox_lease_id": "sandbox-lease.pending",
                    "expires_at": "not_issued_without_atp",
                },
            ),
            HTTPStatus.ACCEPTED,
        )

    def _agent_connector_api(
        self,
        headers: dict[str, str],
        body: bytes,
        *,
        action: str,
    ) -> tuple[int, str, bytes]:
        if not _connector_control_authorized(headers):
            return _agent_fail_closed_response("connector_auth_required")
        payload = _safe_json_object(body)
        if _contains_agent_control_blocked_fields(payload):
            return _agent_fail_closed_response("blocked_payload_field")
        status_by_action = {
            "connect": "connected_metadata_received",
            "heartbeat": "heartbeat_metadata_received",
            "work_result": "work_result_metadata_received",
        }
        return _json_response(
            _agent_metadata_payload(
                status=status_by_action[action],
                reason_class="connector_control_metadata_only",
                lease_status="not_mutated",
            ),
            HTTPStatus.ACCEPTED,
        )

    def _agent_work_next_api(self, headers: dict[str, str]) -> tuple[int, str, bytes]:
        if not _connector_control_authorized(headers):
            return _agent_fail_closed_response("connector_auth_required")
        if not _workspace_header_bool(headers, "X-NaC-Agent-Lease-Active"):
            return _agent_fail_closed_response("active_lease_required")
        return _json_response(
            _agent_metadata_payload(
                status="no_work",
                reason_class="metadata_only_no_work_envelope",
                lease_status="active",
                extra={"work_envelope_id": "none"},
            )
        )

    def _onboarding_request_post(self, query: str, body: bytes) -> tuple[int, str, bytes]:
        params = parse_qs(query, keep_blank_values=True)
        source = _optional_query_text(params, "source", max_length=40)
        entry = _optional_query_text(params, "entry", max_length=40)
        audience = _optional_query_text(params, "audience", max_length=40)
        public_context = _is_public_prospect_context(source=source, entry=entry, audience=audience)
        form = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        domain = _optional_query_text(form, "domain", max_length=120)
        tenant_slug = _optional_query_text(form, "tenant_slug", max_length=80)
        admin_email = _optional_query_text(form, "admin_email", max_length=160)
        try:
            request = build_onboarding_request(
                domain=domain,
                tenant_slug=tenant_slug,
                admin_email=admin_email,
                dns_status="verified",
            )
        except ValueError as exc:
            if public_context:
                return _html_response(
                    build_customer_onboarding_request_validation_page(
                        domain=domain,
                        tenant_slug=tenant_slug,
                        admin_email=admin_email,
                        error=str(exc),
                    ),
                    HTTPStatus.BAD_REQUEST,
                )
            raise
        try:
            created = self.onboarding_request_store.create_request(request)
        except OnboardingRequestStoreDisabled:
            return _json_response(
                {"error": "onboarding_request_store_disabled", "status": "unavailable"},
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
        except OnboardingRequestStoreUnavailable:
            return _json_response(
                {"error": "onboarding_request_store_unavailable", "status": "unavailable"},
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
        if public_context:
            status_query = urlencode({"audience": "customer"})
            location = f"/onboarding/requests/{_safe_segment(str(created['request_id']))}?{status_query}"
            return _redirect_response(location)
        return _json_response(created, HTTPStatus.CREATED)

    def _customer_onboarding_request_status_get(self, route: str) -> AppResponse:
        request_id = _safe_segment(route.removeprefix("/onboarding/requests/"))
        try:
            request = self.onboarding_request_store.get_request(request_id)
        except OnboardingRequestStoreDisabled:
            return _html_response(
                build_customer_onboarding_request_unavailable_page("Einrichtungsstatus derzeit nicht verfügbar."),
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
        except OnboardingRequestStoreUnavailable:
            return _html_response(
                build_customer_onboarding_request_unavailable_page("Einrichtungsstatus derzeit nicht verfügbar."),
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
        if request is None:
            return _html_response(
                build_customer_onboarding_request_unavailable_page("Diese Einrichtungsanfrage wurde nicht gefunden."),
                HTTPStatus.NOT_FOUND,
            )
        return _html_response(build_customer_onboarding_request_page(request))

    def _admin_onboarding_review_post(self, body: bytes) -> tuple[int, str, bytes]:
        form = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        try:
            reviewed = self.onboarding_request_store.review_request(
                request_id=_query_text(form, "request_id"),
                decision=_query_text(form, "decision"),
            )
        except OnboardingRequestStoreDisabled:
            return _html_response(
                build_operator_review_unavailable_page("Produktive Queue noch nicht verbunden."),
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
        except OnboardingRequestStoreUnavailable:
            return _html_response(
                build_operator_review_unavailable_page("Einrichtungsanfragen sind gerade nicht erreichbar."),
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
        return _html_response(build_operator_review_result_page(reviewed))

    def _admin_onboarding_page(self) -> str:
        try:
            requests = list(self.onboarding_request_store.list_requests())
            store_available = True
        except (OnboardingRequestStoreDisabled, OnboardingRequestStoreUnavailable):
            requests = []
            store_available = False
        return build_admin_onboarding_page(requests=requests, store_available=store_available)

    def _bpmn_route(self, stem: str) -> tuple[int, str, bytes]:
        if stem.endswith("/edit"):
            model = find_bpmn_model(self.repo_root, _safe_segment(stem.removesuffix("/edit")))
            return _html_response(build_bpmn_editor_page(model))
        model = find_bpmn_model(self.repo_root, _safe_segment(stem))
        return _html_response(build_bpmn_page(model))

    def _kg_route(self, slug: str) -> tuple[int, str, bytes]:
        view = build_editor_view(self.repo_root, _safe_segment(slug))
        return _html_response(build_kg_page(view))

    def _cost_route(self, slug: str) -> tuple[int, str, bytes]:
        view = build_cost_review_view(self.repo_root, _safe_segment(slug))
        return _html_response(build_cost_page(view))

    def _bpmn_api_route(self, stem: str) -> tuple[int, str, bytes]:
        if stem.endswith("/xml"):
            return _json_response(bpmn_xml_document(self.repo_root, _safe_segment(stem.removesuffix("/xml"))))
        model = find_bpmn_model(self.repo_root, _safe_segment(stem))
        return _json_text_response(bpmn_model_json(model))

    def _bpmn_api_post(self, stem: str, body: bytes) -> tuple[int, str, bytes]:
        if not stem.endswith("/xml"):
            return _json_response({"error": "Nur /api/bpmn/<modell>/xml nimmt POST entgegen."}, HTTPStatus.NOT_FOUND)
        try:
            payload = json.loads(body.decode("utf-8"))
        except ValueError as exc:
            raise ValueError(f"Request Body ist kein gültiges JSON: {exc}") from exc
        xml = payload.get("xml")
        base_sha256 = payload.get("base_sha256")
        if not isinstance(xml, str):
            raise ValueError("xml muss ein String sein")
        if not isinstance(base_sha256, str):
            raise ValueError("base_sha256 muss ein String sein")
        return _json_response(save_bpmn_xml(self.repo_root, _safe_segment(stem.removesuffix("/xml")), xml, base_sha256))

    def _kg_api_route(self, slug: str) -> tuple[int, str, bytes]:
        view = build_editor_view(self.repo_root, _safe_segment(slug))
        return _json_response(view)

    def _cost_api_route(self, slug: str) -> tuple[int, str, bytes]:
        view = build_cost_review_view(self.repo_root, _safe_segment(slug))
        return _json_response(view)

    def _tenant_domain_check_api(self, query: str) -> tuple[int, str, bytes]:
        try:
            params = parse_qs(query, keep_blank_values=True)
            payload = check_domain_ready(
                domain=_query_text(params, "domain"),
                tenant_slug=_query_text(params, "tenant_slug"),
                admin_email=_query_text(params, "admin_email"),
            )
        except ValueError as exc:
            return _json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        return _json_response(payload)

    def _tenant_login_intent_api(self, query: str) -> tuple[int, str, bytes]:
        try:
            params = parse_qs(query, keep_blank_values=True)
            _reject_caller_supplied_login_config(params)
            config = _login_intent_config_from_env(secret_text_provider=self.secret_text_provider)
            payload = build_login_intent(
                tenant_hint=_optional_query_text(params, "tenant_hint", max_length=120),
                issuer_url=config["issuer_url"],
                client_id=config["client_id"],
                redirect_uri=config["redirect_uri"],
                state_signing_key=config.get("state_signing_key") or None,
            )
        except ValueError as exc:
            return _json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        return _json_response(payload)

    def _tenant_provision_admin_preview_api_post(self, body: bytes) -> tuple[int, str, bytes]:
        try:
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Request Body muss ein JSON-Objekt sein")
            plan = build_customer_tenant_plan(
                tenant_slug=_payload_text(payload, "tenant_slug"),
                domain=_payload_text(payload, "domain"),
                admin_email=_payload_text(payload, "admin_email"),
                saas_admin_email=str(payload.get("saas_admin_email", "saas-owner@example.com")),
            )
        except (ValueError, json.JSONDecodeError) as exc:
            return _json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        return _json_response(plan)

    def _tenant_dns_check_page(self, query: str) -> str:
        params = parse_qs(query, keep_blank_values=True)
        source = _optional_query_text(params, "source", max_length=40)
        entry = _optional_query_text(params, "entry", max_length=40)
        audience = _optional_query_text(params, "audience", max_length=40)
        public_context = _is_public_prospect_context(source=source, entry=entry, audience=audience) or not (
            source or entry or audience
        )
        context_query = {"audience": "customer"} if public_context else {}
        readiness = check_domain_ready(
            domain=_query_text(params, "domain"),
            tenant_slug=_query_text(params, "tenant_slug"),
            admin_email=_query_text(params, "admin_email"),
        )
        verification = readiness["verification"]
        result = build_live_dns_check_result(
            expected_name=verification["dns_record_name"],
            expected_value=verification["dns_record_value"],
            resolver=self.dns_resolver,
        )
        readiness_query = urlencode(
            {
                **context_query,
                "domain_hint": readiness["domain"],
                "tenant_slug": readiness["tenant_slug"],
                "admin_email": readiness["admin_email"],
            }
        )
        dns_query = urlencode(
            {
                **context_query,
                "domain": readiness["domain"],
                "tenant_slug": readiness["tenant_slug"],
                "admin_email": readiness["admin_email"],
            }
        )
        preview_query = urlencode(
            {
                "domain": readiness["domain"],
                "tenant_slug": readiness["tenant_slug"],
                "admin_email": readiness["admin_email"],
            }
        )
        observed_values = result["observed"]["values"]
        observed_items = "".join(
            f"<li><span><code>{html.escape(str(value))}</code></span></li>" for value in observed_values
        ) or "<li><span>kein DNS-TXT-Wert beobachtet</span></li>"
        findings = result["findings"]
        finding_items = "".join(
            f"<li><span>{html.escape(str(finding))}</span></li>" for finding in findings
        ) or "<li><span>keine Blocker</span></li>"
        admin_action = ""
        if not public_context and readiness["ready"] and result["status"] == "verified":
            admin_action = (
                f'<a class="button-link" href="/admin/onboarding/provisioning-preview?'
                f'{html.escape(preview_query, quote=True)}">M365-Plan vorbereiten</a>'
            )
        nav = _customer_onboarding_nav(readiness_query) if public_context else (
            f'<nav class="topline"><a href="/onboarding/readiness?{html.escape(readiness_query, quote=True)}">← Readiness</a>'
            '<span><a href="/admin/onboarding">Admin-Queue</a></span></nav>'
        )
        if public_context:
            confirmed = result["status"] == "verified"
            headline = "Domain bestätigt" if confirmed else "DNS noch nicht bestätigt"
            status_label = "bestätigt" if confirmed else "ausstehend"
            guidance = (
                "Ihre Domain ist bestätigt. notariat8 prüft jetzt die angegebene E-Mail-Adresse für die erste Einrichtung."
                if confirmed
                else "Der DNS-TXT-Eintrag wurde noch nicht gefunden. Prüfen Sie den Eintrag bei Ihrem DNS-Anbieter und versuchen Sie es später erneut."
            )
            invitation_status = "Einladung noch nicht versendet"
            request_form = ""
            if confirmed:
                request_form = f"""
                <form class="readiness-form" method="post" action="/onboarding/requests?audience=customer">
                  <input type="hidden" name="domain" value="{html.escape(readiness["domain"], quote=True)}">
                  <input type="hidden" name="tenant_slug" value="{html.escape(readiness["tenant_slug"], quote=True)}">
                  <input type="hidden" name="admin_email" value="{html.escape(readiness["admin_email"], quote=True)}">
                  <button type="submit">Einrichtung anfragen</button>
                </form>
                """
            body = f"""
            {nav}
            <section class="hero">
              <p class="eyebrow">notariat8 Domain-Check</p>
              <h1>DNS-Prüfergebnis</h1>
              <p>Hier sehen Sie, ob Ihre Domain für notariat8 bestätigt wurde. Geprüft werden nur die Domain,
              die E-Mail-Adresse der verantwortlichen Person und der DNS-TXT-Eintrag.</p>
            </section>
            <div class="grid">
              <section class="notice">
                <h2>{html.escape(headline)}</h2>
                <p><strong>Status:</strong> {html.escape(status_label)}</p>
                <p>{html.escape(guidance)}</p>
                <div class="toolbar">
                  <a class="button-link" href="/onboarding/readiness?{html.escape(readiness_query, quote=True)}">Einrichtungsstatus öffnen</a>
                  <a class="inline-link" href="/onboarding/dns-check?{html.escape(dns_query, quote=True)}">Erneut prüfen</a>
                </div>
              </section>
              <section>
                <h2>Ihre Angaben</h2>
                <p><strong>Domain:</strong> {html.escape(readiness["domain"])}</p>
                <p><strong>E-Mail-Adresse:</strong> {html.escape(readiness["admin_email"])}</p>
                <p><strong>Einladung:</strong> {html.escape(invitation_status)}</p>
                {request_form}
              </section>
            </div>
            <div class="grid">
              <section>
                <h2>Was passiert als Nächstes?</h2>
                <ul class="link-list">
                  <li><span><strong>E-Mail-Adresse prüfen:</strong> notariat8 prüft, ob die angegebene E-Mail-Adresse für die Einrichtung Ihres Notariats passt.</span></li>
                  <li><span><strong>Einrichtung freigeben:</strong> Nach der Prüfung wird die erste Einrichtung vorbereitet.</span></li>
                  <li><span><strong>Einladung noch nicht versendet:</strong> Eine E-Mail wird erst nach Freigabe ausgelöst.</span></li>
                  <li><span><strong>Keine Mandatsdaten:</strong> Diese Seite sammelt keine Urkunden, Ausweise, Akten oder Geschäftswerte.</span></li>
                </ul>
              </section>
              <section>
                <h2>Technischer Nachweis</h2>
                <p><strong>Name:</strong> <code>{html.escape(result["expected"]["name"])}</code></p>
                <p><strong>Wert:</strong> <code>{html.escape(result["expected"]["value"])}</code></p>
              </section>
            </div>
            """
            return _layout("notariat8 DNS-Prüfergebnis", body)
        body = f"""
        {nav}
        <section class="hero">
          <p class="eyebrow">Live DNS</p>
          <h1>DNS-Prüfergebnis</h1>
          <p>NaC hat den DNS-TXT-Record über den konfigurierten Resolver geprüft. Diese Seite speichert keine
          Mandatsdaten, Zugangsdaten oder Cloud-Credentials.</p>
        </section>
        <div class="grid">
          <section class="notice">
            <h2>Ergebnis</h2>
            <p><strong>Status:</strong> <code>{html.escape(result["status"])}</code></p>
            <p><strong>Quelle:</strong> <code>{html.escape(result["source"])}</code></p>
            <p>{html.escape(result["customer_guidance"])}</p>
            <div class="toolbar">
              <a class="button-link" href="/onboarding/dns-check?{html.escape(dns_query, quote=True)}">Erneut prüfen</a>
              {admin_action}
            </div>
          </section>
          <section>
            <h2>Erwarteter DNS-TXT</h2>
            <p><strong>Name:</strong> <code>{html.escape(result["expected"]["name"])}</code></p>
            <p><strong>Wert:</strong> <code>{html.escape(result["expected"]["value"])}</code></p>
          </section>
        </div>
        <div class="grid">
          <section>
            <h2>Beobachtete Werte</h2>
            <ul class="link-list">{observed_items}</ul>
          </section>
          <section>
            <h2>Diagnose</h2>
            <ul class="link-list">{finding_items}</ul>
          </section>
        </div>
        """
        return _layout("NaC DNS-Prüfergebnis", body)

    def _gnotkg_quote_api_post(self, body: bytes) -> tuple[int, str, bytes]:
        try:
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Request Body muss ein JSON-Objekt sein")
            quote = quote_fee(
                business_value=Decimal(_payload_text(payload, "business_value")),
                table=_payload_text(payload, "table").upper(),
                fee_rate=Decimal(_payload_text(payload, "fee_rate", "1.0")),
                kv_number=_payload_text(payload, "kv_number", ""),
                usecase_slug=_payload_text(payload, "usecase_slug", ""),
            )
        except (ArithmeticError, ValueError, json.JSONDecodeError) as exc:
            return _json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        return _json_response(quote.to_dict())


def build_server(repo_root: Path, host: str, port: int) -> ThreadingHTTPServer:
    app = NaCLocalWebApp(
        repo_root,
        onboarding_request_store=build_onboarding_request_store_from_env(),
        session_store=build_session_store_from_env(),
        first_matter_runtime_metadata_source=build_first_matter_runtime_metadata_source_from_env(),
    )

    class Handler(BaseHTTPRequestHandler):
        def _send_app_response(self, response: AppResponse, *, include_body: bool = True) -> None:
            status, content_type, body = response
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            for name, value in response.headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if include_body:
                self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            self._send_app_response(app.handle(self.path, headers=dict(self.headers.items())))

        def do_HEAD(self) -> None:  # noqa: N802
            self._send_app_response(app.handle(self.path, headers=dict(self.headers.items())), include_body=False)

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            self._send_app_response(
                app.handle_post(
                    self.path,
                    self.rfile.read(length),
                    headers=dict(self.headers.items()),
                )
            )

        def log_message(self, format: str, *args: Any) -> None:
            sanitized_args = tuple(_sanitize_request_log_text(str(arg)) for arg in args)
            print(f"{self.address_string()} - {format % sanitized_args}")

    return ThreadingHTTPServer((host, port), Handler)


def run_server(repo_root: Path, host: str, port: int, open_browser: bool = False) -> None:
    server = build_server(repo_root, host, port)
    url = f"http://{host}:{server.server_port}/"
    print(f"NaC local web server: {url}")
    print("Abbrechen mit Ctrl+C.")
    if open_browser:
        threading.Timer(0.2, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nNaC local web server beendet.")
    finally:
        server.server_close()


def build_home_page(repo_root: Path) -> str:
    bpmn_models = list_bpmn_models(repo_root)
    catalogs = load_catalogs(repo_root)
    cases = all_case_summaries(catalogs)
    bpmn_items = "".join(
        f'<li><a href="/bpmn/{html.escape(model.stem)}">{html.escape(model.name)}</a>'
        f'<span>{html.escape(model.path)} · <a class="inline-link" href="/bpmn/{html.escape(model.stem)}/edit">bearbeiten</a></span></li>'
        for model in bpmn_models
    )
    kg_items = "".join(
        f'<li><a href="/kg/{html.escape(case.slug)}">{html.escape(case.title)}</a>'
        f'<span>{html.escape(case.slug)} · {case.open_required_information} offene Angaben · '
        f'<a class="inline-link" href="/costs/{html.escape(case.slug)}">Kosten</a></span></li>'
        for case in cases[:40]
    )
    body = f"""
    <section class="hero">
      <p class="eyebrow">Lokaler NaC-Webserver</p>
      <h1>Grafische Ausgaben lokal prüfen</h1>
      <p>BPMN-Modelle und KG-Editor-Views werden direkt aus dem Repository gelesen.
      Der Server bindet standardmäßig an <code>127.0.0.1</code> und speichert keine Mandatsdaten.</p>
    </section>
    <div class="grid">
      <section>
        <h2>BPMN</h2>
        <ul class="link-list">{bpmn_items}</ul>
      </section>
      <section>
        <h2>Knowledge Graphs</h2>
        <ul class="link-list">{kg_items}</ul>
      </section>
    </div>
    """
    return _layout("NaC Lokaler Webserver", body)


def build_www_n8_handoff_page(query: str, *, dns_resolver=None) -> str | None:
    params = parse_qs(query, keep_blank_values=True)
    if not _is_notariat8_source(_optional_query_text(params, "source")):
        return None
    entry = _optional_query_text(params, "entry")
    if entry == "customer":
        tenant_hint = _optional_query_text(params, "tenant_hint", max_length=120)
        hint = html.escape(tenant_hint) if tenant_hint else "nicht übergeben"
        login_href = "/login?" + urlencode({"source": "notariat8", "entry": "customer", "tenant_hint": tenant_hint})
        body = f"""
        <nav class="topline"><a href="/">← Übersicht</a><span><a href="/healthz">Health</a></span></nav>
        <section class="hero">
          <p class="eyebrow">notariat8 App-Einstieg</p>
          <h1>Bestandskunde</h1>
          <p>Der Übergang von <code>notariat8</code> wurde empfangen. notariat8 prüft den passenden
          Notariatskontext erst nach Ihrer Anmeldung.</p>
        </section>
        <div class="grid">
          <section class="notice">
            <h2>Ihr Notariat</h2>
            <p><strong>Hinweis:</strong> {hint}</p>
            <p><strong>Nächster Schritt:</strong> Anmeldung öffnen.</p>
            <p><a class="inline-link" href="{html.escape(login_href)}">Anmeldung öffnen</a></p>
          </section>
          <section>
            <h2>Datenschutz</h2>
            <ul class="link-list">
              <li><span>Keine Mandatsdaten, keine Zugangsdaten, keine Secrets aus Query-Parametern.</span></li>
              <li><span>Der Hinweis allein öffnet noch keinen geschützten Arbeitsbereich.</span></li>
            </ul>
          </section>
        </div>
        """
        return _layout("notariat8 App-Einstieg", body)
    if entry == "prospect":
        domain_hint = _optional_query_text(params, "domain_hint", max_length=120)
        readiness_params = {"source": "notariat8", "entry": "prospect"}
        if domain_hint:
            readiness_params["domain_hint"] = domain_hint
        readiness_query = urlencode(readiness_params)
        return build_customer_readiness_page(readiness_query, dns_resolver=dns_resolver)
    return None


def build_login_page(query: str) -> str:
    params = parse_qs(query, keep_blank_values=True)
    source = _optional_query_text(params, "source")
    entry = _optional_query_text(params, "entry")
    tenant_hint = _optional_query_text(params, "tenant_hint", max_length=120)
    context_label = "notariat8 Bestandskunde" if _is_notariat8_source(source) and entry == "customer" else "direkter Login-Einstieg"
    hint = html.escape(tenant_hint) if tenant_hint else "nicht übergeben"
    intent_params = {"tenant_hint": tenant_hint} if tenant_hint else {}
    login_intent_href = "/api/tenant/login-intent"
    if intent_params:
        login_intent_href += "?" + urlencode(intent_params)
    login_intent_js = json.dumps(login_intent_href)
    body = f"""
    <nav class="topline"><a href="/">← Übersicht</a></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Zugang</p>
      <h1>notariat8 Anmeldung</h1>
      <p>notariat8 bereitet die sichere Anmeldung vor. Der konkrete Anmeldeschritt wird
      serverseitig mit einmaligen Sicherheitswerten erzeugt; Hinweise aus der URL bleiben nur Kontext.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Anmeldekontext</h2>
        <p><strong>Quelle:</strong> {html.escape(context_label)}</p>
        <p><strong>Notariats-Hinweis:</strong> {hint}</p>
        <div class="toolbar">
          <button class="button-link" id="nac-login-button" type="button">Jetzt anmelden</button>
          <span id="nac-login-status" class="muted" aria-live="polite"></span>
        </div>
      </section>
      <section>
        <h2>Sicherheitsprüfung</h2>
        <ul class="link-list">
          <li><span>Die Anmeldung wird erst nach serverseitiger Sicherheitsprüfung geöffnet.</span></li>
          <li><span>Berechtigung und Vorgang werden erst nach erfolgreicher Anmeldung geprüft.</span></li>
          <li><span>Keine Mandatsdaten, Zugangsdaten oder Client-Secrets in dieser Einstiegskante.</span></li>
        </ul>
      </section>
    </div>
    <script>
    (() => {{
      const button = document.getElementById("nac-login-button");
      const status = document.getElementById("nac-login-status");
      const intentUrl = {login_intent_js};
      if (!button || !status) {{
        return;
      }}
      button.addEventListener("click", async () => {{
        button.disabled = true;
        status.textContent = "Anmeldung wird vorbereitet ...";
        try {{
          const response = await fetch(intentUrl, {{ headers: {{ "Accept": "application/json" }} }});
          if (!response.ok) {{
            throw new Error("intent failed");
          }}
          const payload = await response.json();
          if (!payload || typeof payload.authorization_url !== "string" || payload.authorization_url.length === 0) {{
            throw new Error("intent incomplete");
          }}
          window.location.assign(payload.authorization_url);
        }} catch (error) {{
          status.textContent = "Anmeldung konnte nicht vorbereitet werden. Bitte versuchen Sie es erneut.";
          button.disabled = false;
        }}
      }});
    }})();
    </script>
    """
    return _layout("notariat8 Anmeldung", body)


def build_auth_callback_page(
    query: str,
    *,
    secret_text_provider: Callable[[str], str] | None = None,
    session_store: RuntimeSessionStoreAdapter | None = None,
    role_membership_resolver: Callable[..., dict[str, Any]] | None = None,
) -> tuple[HTTPStatus, str, dict[str, str]]:
    params = parse_qs(query, keep_blank_values=True)
    provider_error = _optional_query_text(params, "error", max_length=120)
    code = _optional_query_text(params, "code", max_length=4096)
    state = _optional_query_text(params, "state", max_length=4096)
    state_validation = _auth_callback_state_validation(state, secret_text_provider=secret_text_provider)
    token_exchange_metadata = _auth_callback_token_exchange_metadata()
    token_exchange_result = _auth_callback_token_exchange_result(
        code=code,
        state_validation=state_validation,
        secret_text_provider=secret_text_provider,
        **token_exchange_metadata,
    )
    callback_result = build_auth_callback_result(
        code=code,
        state=state,
        provider_error=provider_error,
        state_validation_configured=_auth_callback_state_validation_configured(),
        token_exchange_configured=_auth_callback_token_exchange_configured(),
        state_validation=state_validation,
        token_exchange_result=token_exchange_result,
        expected_issuer=_auth_callback_expected_issuer(),
        expected_audience=token_exchange_metadata["client_id"],
        session_signing_key=_auth_callback_session_signing_key(secret_text_provider=secret_text_provider),
        session_ttl_seconds=_auth_callback_session_ttl_seconds(),
        role_membership_resolver=role_membership_resolver,
        **token_exchange_metadata,
    )
    if callback_result["status"] == "rejected":
        body = """
        <nav class="topline"><a href="/login">← Anmeldung erneut öffnen</a></nav>
        <section class="hero">
          <p class="eyebrow">notariat8 Anmeldung</p>
          <h1>Anmeldung nicht abgeschlossen</h1>
          <p>Bitte starten Sie die Anmeldung erneut. Es wurden keine Mandatsdaten geöffnet.</p>
        </section>
        <section class="notice">
          <h2>Nächster Schritt</h2>
          <p>Öffnen Sie die Anmeldung noch einmal und bestätigen Sie den Zugriff vollständig.</p>
          <p><a class="button-link" href="/login">Erneut anmelden</a></p>
        </section>
        """
        return HTTPStatus.BAD_REQUEST, _layout("notariat8 Anmeldung nicht abgeschlossen", body), {}
    state_label = (
        "Sicherheitsprüfung bestätigt"
        if callback_result["state_validation"]["status"] == "valid"
        else "Sicherheitsprüfung offen"
    )
    role_label = (
        "Rollenprüfung bestätigt"
        if callback_result.get("role_gate", {}).get("status") == "open"
        else "Rollenprüfung offen"
    )
    session_bound = bool(callback_result.get("session_boundary", {}).get("session", {}).get("cookie_issued"))
    if session_bound and session_store is not None:
        session_bound = _persist_auth_callback_session(
            callback_result=callback_result,
            token_exchange_result=token_exchange_result,
            state_validation=state_validation,
            session_store=session_store,
        )
        if not session_bound:
            _mark_callback_session_store_unavailable(callback_result)
    _log_auth_callback_redacted_status(callback_result, session_store_bound=session_bound and session_store is not None)
    session_label = "Sitzung vorbereitet" if session_bound else "Sitzung offen"
    escaped_state_label = html.escape(state_label)
    escaped_role_label = html.escape(role_label)
    escaped_session_label = html.escape(session_label)
    diagnostics_html = _auth_callback_diagnostics_html(callback_result)
    headers = _auth_callback_response_headers(callback_result)
    if session_bound:
        callback_summary = (
            "notariat8 hat die Rückmeldung zur Anmeldung empfangen. Der Startstatus ist "
            "freigegeben. Vollständiger Arbeitsbereich bleibt geschlossen."
        )
        role_gate_detail = (
            "Die Sitzung ist aufgebaut und die notariat8-Berechtigung bestätigt. "
            "Dieser Schritt öffnet nur den geschützten Startstatus."
        )
        next_step_html = """
          <li><a class="inline-link" href="/workspace">Geschützten Startstatus öffnen</a>
          <span>Die Startseite zeigt nur Sitzungsstatus und keine Mandatsdaten.</span></li>
          <li><span>Vollständiger Arbeitsbereich bleibt geschlossen.</span></li>
          <li><span>Mandatsdaten werden in diesem Zwischenschritt nicht geladen.</span></li>
        """
        startstatus_label_html = "<p><strong>Startstatus freigegeben</strong></p>"
    else:
        callback_summary = (
            "notariat8 hat die Rückmeldung zur Anmeldung empfangen. Der Arbeitsbereich bleibt "
            "geschlossen, bis Sitzung und Rolle geprüft sind."
        )
        role_gate_detail = (
            "Der geschützte Arbeitsbereich wird erst geöffnet, wenn notariat8 die Sitzung "
            "aufgebaut und die Rolle geprüft hat."
        )
        next_step_html = """
          <li><span>Sitzung und Berechtigung prüfen.</span></li>
          <li><span>Mandatsdaten werden in diesem Zwischenschritt nicht geladen.</span></li>
        """
        startstatus_label_html = ""
    body = f"""
    <nav class="topline"><a href="/login">← Anmeldung</a></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Anmeldung</p>
      <h1>Anmeldung empfangen</h1>
      <p>{html.escape(callback_summary)}</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Anmeldung und Berechtigung</h2>
        <p><strong>{escaped_state_label}</strong></p>
        <p><strong>{escaped_role_label}</strong></p>
        <p><strong>{escaped_session_label}</strong></p>
        {startstatus_label_html}
        <p>{html.escape(role_gate_detail)}</p>
      </section>
      <section>
        <h2>Nächster Schritt</h2>
        <ul class="link-list">
          {next_step_html}
        </ul>
      </section>
    </div>
    {diagnostics_html}
    """
    return HTTPStatus.OK, _layout("notariat8 Anmeldung empfangen", body), headers


def build_protected_workspace_start_page(
    request_headers: dict[str, str],
    *,
    secret_text_provider: Callable[[str], str] | None = None,
    session_store: RuntimeSessionStoreAdapter | None = None,
) -> tuple[HTTPStatus, str]:
    access = _evaluate_workspace_access(
        request_headers,
        secret_text_provider=secret_text_provider,
        session_store=session_store,
    )
    if access["status"] == "session_required":
        body = """
        <nav class="topline"><a href="/login">← Anmeldung</a></nav>
        <section class="hero">
          <p class="eyebrow">notariat8 Start</p>
          <h1>notariat8 Anmeldung erforderlich</h1>
          <p>Bitte melden Sie sich erneut an. Der geschützte Startstatus bleibt geschlossen,
          bis die Sitzung geprüft ist.</p>
        </section>
        <section class="notice">
          <h2>Geschützter Startstatus</h2>
          <ul class="link-list">
            <li><span>Sitzung nicht geprüft.</span></li>
            <li><span>Keine Mandatsdaten geladen.</span></li>
          </ul>
          <p><a class="button-link" href="/login">Anmeldung öffnen</a></p>
        </section>
        """
        return HTTPStatus.UNAUTHORIZED, _layout("notariat8 Anmeldung erforderlich", body)

    if access["status"] == "gate_closed":
        reason_label = _workspace_gate_reason_label(str(access.get("reason")))
        body = f"""
        <nav class="topline"><a href="/login">← Anmeldung</a></nav>
        <section class="hero">
          <p class="eyebrow">notariat8 Start</p>
          <h1>Berechtigungsprüfung offen</h1>
          <p>Ihre Sitzung wurde geprüft. Der geschützte Arbeitsbereich bleibt geschlossen,
          bis Berechtigung, Notariat, Vorgang und Zweck geprüft sind.</p>
        </section>
        <div class="grid">
          <section class="notice">
            <h2>Geschützter Startstatus</h2>
            <ul class="link-list">
              <li><span>Sitzung geprüft.</span></li>
              <li><span>{html.escape(reason_label)}</span></li>
              <li><span>Keine Mandatsdaten geladen.</span></li>
            </ul>
          </section>
          <section>
            <h2>Nächster Schritt</h2>
            <ul class="link-list">
              <li><span>notariat8 prüft die fachliche Bindung für diesen Arbeitsbereich.</span></li>
              <li><span>Der vollständige Arbeitsbereich bleibt geschlossen.</span></li>
            </ul>
          </section>
        </div>
        """
        return HTTPStatus.FORBIDDEN, _layout("notariat8 Berechtigungsprüfung offen", body)

    body = """
    <nav class="topline"><a href="/login">← Anmeldung</a></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Portal-Start</p>
      <h1>Portal-Start bereit</h1>
      <p>Ihre Anmeldung und Berechtigung wurden geprüft. notariat8 öffnet hier
      nur den sicheren Startbereich ohne Mandatsdaten.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Anmeldung und Berechtigung bestätigt</h2>
        <p><strong>Portal-Start bereit</strong></p>
        <ul class="link-list">
          <li><span>Berechtigung bestätigt.</span></li>
          <li><span>Notariat, Vorgang und Zweck sind serverseitig gebunden.</span></li>
          <li><span>Keine Mandatsdaten geladen.</span></li>
        </ul>
      </section>
      <section>
        <h2>Nächster sicherer Schritt</h2>
        <ul class="link-list">
          <li><span>Erste sichere Vorgangsübersicht vorbereiten.</span></li>
          <li><span>Der vollständige Arbeitsbereich bleibt geschlossen.</span></li>
          <li><span>Mandatsinhalte werden erst nach den nächsten Freigaben geladen.</span></li>
        </ul>
      </section>
    </div>
    <section class="notice">
      <h2>Erster Vorgang vorbereitet</h2>
      <p><strong>Immobilienkaufvertrag</strong></p>
      <ul class="link-list">
        <li><span>BPMN-Modell vorhanden.</span></li>
        <li><span>XNP/SNP-Zielpfad vorbereitet.</span></li>
        <li><span>Vollzugspfad sichtbar.</span></li>
        <li><span>Kritischer Pfad: externer Rücklauf.</span></li>
        <li><span>Dauerband: Wochen bis Monate.</span></li>
        <li><span>Keine Mandatsdaten geladen.</span></li>
      </ul>
    </section>
    <section>
      <h2>Nächster sicherer Schritt</h2>
      <ul class="link-list">
        <li><a class="inline-link" href="/workspace/immobilienkaufvertrag">Ersten Vorgang als Statusansicht öffnen.</a></li>
        <li><span>Vollständiger Arbeitsbereich und Mandatsinhalte bleiben geschlossen.</span></li>
      </ul>
    </section>
    """
    return HTTPStatus.OK, _layout("notariat8 Start", body)


def build_protected_first_matter_status_page(
    request_headers: dict[str, str],
    *,
    repo_root: Path,
    secret_text_provider: Callable[[str], str] | None = None,
    session_store: RuntimeSessionStoreAdapter | None = None,
    runtime_metadata_source: RuntimeMetadataSource | None = None,
) -> tuple[HTTPStatus, str]:
    access = _evaluate_workspace_access(
        request_headers,
        secret_text_provider=secret_text_provider,
        session_store=session_store,
    )
    if access["status"] == "session_required":
        body = """
        <nav class="topline"><a href="/login">← Anmeldung</a></nav>
        <section class="hero">
          <p class="eyebrow">notariat8 Start</p>
          <h1>notariat8 Anmeldung erforderlich</h1>
          <p>Bitte melden Sie sich erneut an. Der Vorgangsstatus bleibt geschlossen,
          bis die Sitzung geprüft ist.</p>
        </section>
        <section class="notice">
          <h2>Vorgangsstatus geschlossen</h2>
          <ul class="link-list">
            <li><span>Sitzung nicht geprüft.</span></li>
            <li><span>Keine Mandatsdaten geladen.</span></li>
          </ul>
        </section>
        """
        return HTTPStatus.UNAUTHORIZED, _layout("notariat8 Anmeldung erforderlich", body)

    if access["status"] == "gate_closed":
        reason_label = _workspace_gate_reason_label(str(access.get("reason")))
        body = f"""
        <nav class="topline"><a href="/workspace">← Portal-Start</a></nav>
        <section class="hero">
          <p class="eyebrow">notariat8 Vorgangsstatus</p>
          <h1>Berechtigungsprüfung offen</h1>
          <p>Der Vorgangsstatus bleibt geschlossen, bis Berechtigung, Notariat,
          Vorgang und Zweck geprüft sind.</p>
        </section>
        <section class="notice">
          <h2>Vorgangsstatus geschlossen</h2>
          <ul class="link-list">
            <li><span>{html.escape(reason_label)}</span></li>
            <li><span>Keine Mandatsdaten geladen.</span></li>
            <li><span>Vollständiger Arbeitsbereich bleibt geschlossen.</span></li>
          </ul>
        </section>
        """
        return HTTPStatus.FORBIDDEN, _layout("notariat8 Vorgangsstatus geschlossen", body)

    try:
        display = _first_matter_status_display(source=runtime_metadata_source)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        LOGGER.warning(
            "first_matter_runtime_metadata_unavailable",
            extra={"error_type": type(exc).__name__},
        )
        return _first_matter_status_unavailable_page()

    status_items_html = _link_list_items(display["status_items"])
    next_steps_html = _link_list_items(display["next_steps"])

    body = f"""
    <nav class="topline"><a href="/workspace">← Portal-Start</a></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Vorgangsstatus</p>
      <h1>{html.escape(display["title"])}</h1>
      <p>{html.escape(display["summary"])}</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Ablaufstatus</h2>
        <ul class="link-list">
          {status_items_html}
        </ul>
      </section>
      <section>
        <h2>XNP/SNP und Vollzug</h2>
        <ul class="link-list">
          <li><span>XNP/SNP-Kommunikation vorbereitet.</span></li>
          <li><span>Grundbuch- und Registerrückläufe als externe Statuspunkte.</span></li>
          <li><span>Kartenleser- und Signaturpfad als Integrationsgrenze markiert.</span></li>
        </ul>
      </section>
    </div>
    <section class="notice">
      <h2>Nachweis ohne Mandatsdaten</h2>
      <ul class="link-list">
        <li><span><strong>GNotKG-Prüfung erforderlich:</strong> Gebührenprüfung bleibt fachlich freigabepflichtig.</span></li>
        <li><span><strong>XNP/SNP-Zielpfad nur als Metadaten:</strong> keine produktive Aktion und kein Versand.</span></li>
        <li><span><strong>Kartenleser- und Signaturpfad als Bereitschaftsgrenze:</strong> lokale Anbindung bleibt als Integrationspunkt markiert.</span></li>
        <li><span><strong>Fachliche Freigabe erforderlich:</strong> menschliche Prüfung vor jedem produktiven Schritt.</span></li>
      </ul>
    </section>
    <div class="grid">
      <section>
        <h2>Zeit und Abhängigkeiten</h2>
        <ul class="link-list">
          <li><span><strong>Parallel möglich:</strong> Entwurf, Abstimmung und Vorbereitungen können teilweise parallel laufen.</span></li>
          {next_steps_html}
        </ul>
      </section>
      <section>
        <h2>Sicherheitsgrenze</h2>
        <ul class="link-list">
          <li><span>Keine Mandatsdaten geladen.</span></li>
          <li><span>Vollständiger Arbeitsbereich bleibt geschlossen.</span></li>
          <li><span>Nur Statusmetadaten ohne Mandatsdaten.</span></li>
        </ul>
      </section>
    </div>
    """
    return HTTPStatus.OK, _layout("notariat8 Immobilienkaufvertrag Status", body)


def _first_matter_status_display(
    *,
    source: RuntimeMetadataSource | None = None,
) -> dict[str, Any]:
    return build_first_matter_status_display_from_metadata_source(
        source=resolve_first_matter_runtime_metadata_source(source),
    )


def _first_matter_status_unavailable_page() -> tuple[HTTPStatus, str]:
    body = """
    <nav class="topline"><a href="/workspace">← Portal-Start</a></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Vorgangsstatus</p>
      <h1>Vorgangsstatus vorübergehend geschlossen</h1>
      <p>Die Runtime-Metadaten konnten nicht geprüft werden. Der vollständige
      Arbeitsbereich bleibt geschlossen.</p>
    </section>
    <section class="notice">
      <h2>Sicherheitsgrenze aktiv</h2>
      <ul class="link-list">
        <li><span>Runtime-Quelle nicht freigegeben.</span></li>
        <li><span>Keine Mandatsdaten geladen.</span></li>
        <li><span>Vollständiger Arbeitsbereich bleibt geschlossen.</span></li>
      </ul>
    </section>
    """
    return HTTPStatus.SERVICE_UNAVAILABLE, _layout("notariat8 Vorgangsstatus geschlossen", body)


def _link_list_items(items: Any) -> str:
    if not isinstance(items, (list, tuple)):
        return ""
    return "\n".join(f"<li><span>{html.escape(str(item))}</span></li>" for item in items)


def _evaluate_workspace_access(
    request_headers: dict[str, str],
    *,
    secret_text_provider: Callable[[str], str] | None = None,
    session_store: RuntimeSessionStoreAdapter | None = None,
) -> dict[str, Any]:
    signing_key = _auth_callback_session_signing_key(secret_text_provider=secret_text_provider)
    validation = validate_session_cookie(
        _request_header(request_headers, "Cookie"),
        signing_key=signing_key,
        session_store=session_store,
        require_server_session_store=True,
    )
    if validation["status"] != "valid":
        return {"status": "session_required"}

    server_bindings = _server_session_bindings(validation)
    role_case_gate = evaluate_role_case_gate(
        session_validation=validation,
        role_gate=normalize_workspace_role_gate_context(
            role=_workspace_role_from_binding_or_header(server_bindings, request_headers),
            role_gate_open=server_bindings.get("role_bound")
            if "role_bound" in server_bindings
            else _workspace_header_bool(request_headers, "X-NaC-Role-Gate-Open", default=True),
        ),
        tenant_context=normalize_workspace_tenant_binding_context(
            tenant_bound=server_bindings.get("tenant_bound", _workspace_header_bool(request_headers, "X-NaC-Tenant-Bound")),
        ),
        case_context=normalize_workspace_case_binding_context(
            case_bound=server_bindings.get("case_bound", _workspace_header_bool(request_headers, "X-NaC-Case-Bound")),
        ),
        purpose_context=normalize_workspace_purpose_binding_context(
            purpose_bound=server_bindings.get("purpose_bound", _workspace_header_bool(request_headers, "X-NaC-Purpose-Bound")),
        ),
        subject_matter_roles=["nac-notary", "nac-case-worker", "nac-tenant-admin"],
    )
    if role_case_gate["status"] != "open":
        return {"status": "gate_closed", "reason": role_case_gate.get("reason")}
    return {"status": "open"}


def _workspace_gate_reason_label(reason: str) -> str:
    return {
        "role_missing": "Rolle fehlt",
        "tenant_mismatch": "Notariatsbindung fehlt",
        "case_missing": "Vorgangsbindung fehlt",
        "purpose_missing": "Zweckbindung fehlt",
        "four_eyes_required": "Vier-Augen-Freigabe fehlt",
    }.get(reason, "Freigabe fehlt")


def _workspace_header_bool(headers: dict[str, str], name: str, *, default: bool = False) -> bool:
    value = _request_header(headers, name)
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _server_session_bindings(validation: dict[str, Any]) -> dict[str, bool]:
    server_session = validation.get("server_session")
    if not isinstance(server_session, dict):
        return {}
    bindings = server_session.get("bindings")
    if not isinstance(bindings, dict):
        bindings = {}
    allowed = {"tenant_bound", "subject_bound", "role_bound", "case_bound", "purpose_bound"}
    return {key: bool(bindings.get(key)) for key in allowed}


def _workspace_role_from_binding_or_header(bindings: dict[str, bool], headers: dict[str, str]) -> str:
    if bindings.get("role_bound"):
        return "nac-tenant-admin"
    return _request_header(headers, "X-NaC-Role")


AGENT_CONTROL_BLOCKED_FIELDS = {
    "id_token",
    "access_token",
    "refresh_token",
    "session_cookie",
    "provider_claims",
    "dashboard_token",
    "private_key",
    "client_secret",
    "environment_dump",
    "raw_mandate_content",
    "document_full_text",
    "card_pin",
    "xnp_payload",
}


def _agent_metadata_payload(
    *,
    status: str,
    reason_class: str,
    lease_status: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "nac.agent-control-api/v0.1",
        "request_id": "local.metadata-only",
        "tenant_id": "server_session",
        "user_binding_id": "server_session",
        "agent_id": "nac-onprem",
        "endpoint_id": "notoclaw01.outbound",
        "sandbox_binding_id": "",
        "sandbox_lease_id": "",
        "lease_status": lease_status,
        "redacted_health_state": "not_connected_in_contract_slice",
        "work_envelope_id": "",
        "status": status,
        "reason_class": reason_class,
        "created_at": "runtime_generated",
        "expires_at": "",
        "raw_mandate_data_loaded": False,
        "secret_material_loaded": False,
        "dashboard_token_captured": False,
        "oci_gateway_apply_performed": False,
        "atp_schema_apply_performed": False,
        "notoclaw_connector_started": False,
    }
    if extra:
        for key, value in extra.items():
            if key in AGENT_CONTROL_BLOCKED_FIELDS:
                continue
            payload[key] = value
    return payload


def _agent_fail_closed_response(reason_class: str) -> tuple[int, str, bytes]:
    return _json_response(
        _agent_metadata_payload(
            status="closed",
            reason_class=reason_class,
            lease_status="closed",
        ),
        HTTPStatus.FORBIDDEN,
    )


def _safe_json_object(body: bytes) -> dict[str, Any]:
    if not body.strip():
        return {}
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("agent_control_payload_must_be_object")
    return payload


def _contains_agent_control_blocked_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in AGENT_CONTROL_BLOCKED_FIELDS:
                return True
            if _contains_agent_control_blocked_fields(nested):
                return True
    if isinstance(value, list):
        return any(_contains_agent_control_blocked_fields(item) for item in value)
    return False


def _connector_control_authorized(headers: dict[str, str]) -> bool:
    metadata_auth_enabled = os.environ.get("NAC_AGENT_CONTROL_ALLOW_METADATA_CONNECTOR_HEADER", "").strip().lower()
    if metadata_auth_enabled not in {"1", "true", "yes", "on"}:
        return False
    return _request_header(headers, "X-NaC-Connector-Authenticated").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_operator_access_required_page() -> str:
    body = """
    <nav class="topline"><a href="/login">← Anmeldung</a></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Operator-Bereich</p>
      <h1>notariat8 Anmeldung erforderlich</h1>
      <p>Dieser Bereich ist nur für berechtigte Personen von notariat8 sichtbar.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Rollenprüfung</h2>
        <p>Die Übersicht wird erst geöffnet, wenn Anmeldung, Sitzung und Rolle geprüft wurden.</p>
      </section>
      <section>
        <h2>Nächster Schritt</h2>
        <ul class="link-list">
          <li><span>Mit einem berechtigten notariat8-Konto anmelden.</span></li>
          <li><span>Danach prüft notariat8, ob der Operator-Zugriff erlaubt ist.</span></li>
          <li><span>Mandatsdaten werden auf dieser Seite nicht geladen.</span></li>
        </ul>
      </section>
    </div>
    """
    return _layout("notariat8 Anmeldung erforderlich", body)


def build_admin_onboarding_page(
    *, requests: list[dict[str, Any]] | None = None, store_available: bool = False
) -> str:
    request_rows = _admin_onboarding_request_rows(requests or [])
    if request_rows:
        queue_body = f"""
        <div class="table-scroll responsive-table">
          <table>
            <thead>
              <tr>
                <th>Anfrage</th>
                <th>Domain</th>
                <th>Einrichtung</th>
                <th>E-Mail-Adresse</th>
                <th>DNS</th>
                <th>Status</th>
                <th>Einladung</th>
                <th>Eingegangen</th>
                <th>Aktion</th>
              </tr>
            </thead>
            <tbody>{request_rows}</tbody>
          </table>
        </div>
        """
    elif store_available:
        queue_body = """
        <div class="notice">
          <h2>Keine offenen Anfragen</h2>
          <p>Aktuell liegt keine neue Einrichtungsanfrage vor.</p>
        </div>
        """
    else:
        queue_body = """
        <div class="notice">
          <h2>Produktive Queue noch nicht verbunden</h2>
          <p>Neue Einrichtungsanfragen werden erst gespeichert, wenn der freigegebene Request-Store aktiv ist.</p>
        </div>
        """
    states = [
        "submitted",
        "dns_challenge_issued",
        "domain_verified",
        "in_review",
        "approved",
        "rejected",
        "invited",
    ]
    state_rows = "".join(
        "<tr>"
        f'<td data-label="Status">{html.escape(state)}</td>'
        f'<td data-label="Gate">{html.escape(_onboarding_state_gate(state))}</td>'
        "</tr>"
        for state in states
    )
    body = f"""
    <nav class="topline"><a href="/">← Übersicht</a><span><a href="/onboarding/readiness">Readiness</a></span></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Betrieb</p>
      <h1>Readiness-Anfragen</h1>
      <p>Interne Queue für bestätigte Domain-Hinweise. Schreibende Einrichtungsschritte bleiben an Review,
      Freigabe, Audit und Rollback-Plan gebunden.</p>
    </section>
    <section>
      <h2>Aktuelle Anfragen</h2>
      {queue_body}
    </section>
    <section>
      <h2>Statusfolge</h2>
      <div class="table-scroll responsive-table">
        <table>
          <thead><tr><th>Status</th><th>Gate</th></tr></thead>
          <tbody>{state_rows}</tbody>
        </table>
      </div>
    </section>
    """
    return _layout("NaC Onboarding Admin", body)


def _admin_onboarding_request_rows(requests: list[dict[str, Any]]) -> str:
    rows = []
    for request in requests:
        action = _admin_onboarding_review_action(request)
        rows.append(
            "<tr>"
            f'<td data-label="Anfrage"><code>{html.escape(str(request.get("request_id", "")))}</code></td>'
            f'<td data-label="Domain">{html.escape(str(request.get("domain", "")))}</td>'
            f'<td data-label="Einrichtung">{html.escape(str(request.get("tenant_slug", "")))}</td>'
            f'<td data-label="E-Mail-Adresse">{html.escape(str(request.get("admin_email", "")))}</td>'
            f'<td data-label="DNS">{html.escape(str(request.get("dns_status", "")))}</td>'
            f'<td data-label="Status">{html.escape(str(request.get("request_status", "")))}</td>'
            f'<td data-label="Einladung">{html.escape(str(request.get("invitation_status", "")))}</td>'
            f'<td data-label="Eingegangen">{html.escape(str(request.get("created_at", "")))}</td>'
            f'<td data-label="Aktion">{action}</td>'
            "</tr>"
        )
    return "".join(rows)


def _admin_onboarding_review_action(request: dict[str, Any]) -> str:
    request_id = str(request.get("request_id", "")).strip()
    request_status = str(request.get("request_status", "")).strip()
    invitation_status = str(request.get("invitation_status", "")).strip()
    if not request_id or request_status not in {"submitted", "in_review"} or invitation_status != "not_sent":
        return "<span>Keine offene Aktion</span>"
    return f"""
    <form class="readiness-form" method="post" action="/admin/onboarding/review">
      <input type="hidden" name="request_id" value="{html.escape(request_id, quote=True)}">
      <input type="hidden" name="decision" value="approve">
      <button type="submit">E-Mail geprüft</button>
      <p>Einladung noch nicht senden.</p>
    </form>
    """


def _onboarding_state_gate(state: str) -> str:
    labels = {
        "submitted": "Domain-Hinweis aus notariat8 eingegangen",
        "dns_challenge_issued": "DNS-TXT-Challenge ausgegeben",
        "domain_verified": "DNS-TXT bestätigt",
        "in_review": "notariat8 prüft Einrichtung und E-Mail-Adresse",
        "approved": "Freigabe ist dokumentiert; Einladung bleibt bis zum nächsten Freigabeschritt offen",
        "rejected": "Anfrage wurde abgelehnt und nicht eingeladen",
        "invited": "Initialer Tenant-Admin wurde eingeladen",
    }
    return labels[state]


def _customer_dns_check_copy(dns_check: dict[str, Any]) -> tuple[str, str]:
    status = str(dns_check.get("status", ""))
    if status == "verified":
        return "bestätigt", "DNS-TXT wurde gefunden. Ihre Domain ist für notariat8 bestätigt."
    if status == "wrong_name":
        return "nicht bestätigt", "Der DNS-TXT-Eintrag steht unter einem anderen Namen. Bitte prüfen Sie den Recordnamen."
    if status == "wrong_value":
        return "nicht bestätigt", "Der DNS-TXT-Eintrag wurde gefunden, der Wert passt aber noch nicht."
    if status == "resolver_error":
        return "später erneut prüfen", "Die DNS-Prüfung konnte gerade nicht abgeschlossen werden. Bitte versuchen Sie es später erneut."
    return "noch offen", "Der DNS-TXT-Eintrag wurde noch nicht gefunden. DNS-Änderungen können einige Minuten dauern; später erneut prüfen."


def build_operator_review_result_page(request: dict[str, Any]) -> str:
    audit = request.get("review_audit")
    audit_section = ""
    if isinstance(audit, dict):
        audit_section = f"""
      <section>
        <h2>Audit-Metadaten</h2>
        <ul class="link-list">
          <li><span><strong>Schema:</strong> <code>{html.escape(str(audit.get("schema_version", "")))}</code></span></li>
          <li><span>Keine Mandatsdaten im Review-Audit</span></li>
          <li><span>Keine E-Mail ausgelöst</span></li>
          <li><span>Keine Cloud-Schreiboperation</span></li>
          <li><span>Keine Datenbank-Schemaänderung</span></li>
        </ul>
      </section>
        """
    body = f"""
    <nav class="topline"><a href="/admin/onboarding">← Readiness-Anfragen</a><span><a href="/">Übersicht</a></span></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Betrieb</p>
      <h1>Prüfung gespeichert</h1>
      <p>Die Operator-Entscheidung wurde dokumentiert. Eine Einladung wird in diesem Schritt nicht versendet.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Anfrage</h2>
        <p><strong>Referenz:</strong> <code>{html.escape(str(request.get("request_id", "")))}</code></p>
        <p><strong>Domain:</strong> {html.escape(str(request.get("domain", "")))}</p>
        <p><strong>E-Mail-Adresse:</strong> {html.escape(str(request.get("admin_email", "")))}</p>
        <p><strong>Status:</strong> {html.escape(str(request.get("request_status", "")))}</p>
        <p><strong>Einladung:</strong> Einladung noch nicht versendet</p>
      </section>
      <section>
        <h2>Nächster Schritt</h2>
        <ul class="link-list">
          <li><span>Owner-Review und Apply-Gate bleiben erforderlich.</span></li>
          <li><span>Die Einladung wird erst in einem separaten freigegebenen Schritt ausgelöst.</span></li>
          <li><span>Keine Mandatsdaten: Diese Ansicht enthält keine Urkunden, Ausweise, Akten oder Geschäftswerte.</span></li>
        </ul>
      </section>
      {audit_section}
    </div>
    """
    return _layout("notariat8 Prüfung gespeichert", body)


def build_operator_review_unavailable_page(message: str) -> str:
    body = f"""
    <nav class="topline"><a href="/admin/onboarding">← Readiness-Anfragen</a><span><a href="/">Übersicht</a></span></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Betrieb</p>
      <h1>Prüfung nicht gespeichert</h1>
      <p>{html.escape(message)}</p>
    </section>
    <section class="notice">
      <h2>Nächster Schritt</h2>
      <p>Bitte später erneut prüfen. In diesem Schritt wurde keine Einladung ausgelöst.</p>
    </section>
    """
    return _layout("notariat8 Prüfung nicht gespeichert", body)


def build_customer_onboarding_request_page(request: dict[str, Any]) -> str:
    readiness_query = urlencode(
        _present_query_values(
            {
                "audience": "customer",
                "domain_hint": str(request.get("domain", "")),
                "tenant_slug": str(request.get("tenant_slug", "")),
                "admin_email": str(request.get("admin_email", "")),
            }
        )
    )
    nav = _customer_onboarding_nav(readiness_query)
    status_copy = _customer_onboarding_status_copy(request)
    body = f"""
    {nav}
    <section class="hero">
      <p class="eyebrow">notariat8 Einrichtung</p>
      <h1>{html.escape(status_copy["headline"])}</h1>
      <p>{html.escape(status_copy["summary"])}</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Ihre Angaben</h2>
        <p><strong>Domain:</strong> {html.escape(str(request.get("domain", "")))}</p>
        <p><strong>E-Mail-Adresse:</strong> {html.escape(str(request.get("admin_email", "")))}</p>
        <p><strong>Status:</strong> {html.escape(status_copy["status_label"])}</p>
        <p><strong>Einladung:</strong> {html.escape(status_copy["invitation_label"])}</p>
        <div class="toolbar">
          <a class="button-link" href="/onboarding/readiness?{html.escape(readiness_query, quote=True)}">Einrichtungsstatus öffnen</a>
        </div>
      </section>
      <section>
        <h2>Was passiert als Nächstes?</h2>
        <ul class="link-list">
          <li><span><strong>Prüfung:</strong> {html.escape(status_copy["review_step"])}</span></li>
          <li><span><strong>Freigabe:</strong> {html.escape(status_copy["release_step"])}</span></li>
          <li><span><strong>Einladung:</strong> {html.escape(status_copy["invitation_step"])}</span></li>
          <li><span><strong>Nachweis:</strong> Die Referenz dieser Anfrage lautet <code>{html.escape(str(request.get("request_id", "")))}</code>.</span></li>
          <li><span><strong>Keine Mandatsdaten:</strong> Diese Anfrage enthält keine Urkunden, Ausweise, Akten oder Geschäftswerte.</span></li>
        </ul>
      </section>
    </div>
    """
    return _layout("notariat8 Einrichtung angefragt", body)


def _customer_onboarding_status_copy(request: dict[str, Any]) -> dict[str, str]:
    request_status = str(request.get("request_status") or "").strip().lower()
    invitation_status = str(request.get("invitation_status") or "").strip().lower()
    invitation_label = "Einladung noch nicht versendet"
    invitation_step = "Eine E-Mail wird erst nach Freigabe ausgelöst."
    if invitation_status and invitation_status != "not_sent":
        invitation_label = "Einladungsstatus wird geprüft"
        invitation_step = "notariat8 prüft den nächsten sicheren Einladungsschritt."
    if request_status == "approved":
        return {
            "headline": "Einrichtung freigegeben",
            "summary": "Die Prüfung ist dokumentiert. notariat8 bereitet die nächsten sicheren Schritte vor.",
            "status_label": "Prüfung dokumentiert",
            "invitation_label": invitation_label,
            "review_step": "Die E-Mail-Adresse der verantwortlichen Person wurde geprüft.",
            "release_step": "Die erste Einrichtung kann vorbereitet werden.",
            "invitation_step": invitation_step,
        }
    if request_status == "rejected":
        return {
            "headline": "Einrichtung noch nicht freigegeben",
            "summary": "Die Prüfung ist dokumentiert. notariat8 meldet sich mit den nächsten Schritten.",
            "status_label": "Prüfung dokumentiert",
            "invitation_label": invitation_label,
            "review_step": "Die E-Mail-Adresse der verantwortlichen Person wurde geprüft.",
            "release_step": "Die Einrichtung ist noch nicht freigegeben.",
            "invitation_step": invitation_step,
        }
    return {
        "headline": "Einrichtung angefragt",
        "summary": (
            "Ihre Anfrage ist bei notariat8 eingegangen. Wir prüfen jetzt die angegebene E-Mail-Adresse "
            "und bereiten die nächsten Schritte vor."
        ),
        "status_label": "Anfrage eingegangen",
        "invitation_label": invitation_label,
        "review_step": "notariat8 prüft die E-Mail-Adresse der verantwortlichen Person.",
        "release_step": "Nach der Prüfung wird die erste Einrichtung vorbereitet.",
        "invitation_step": invitation_step,
    }


def build_customer_onboarding_request_unavailable_page(message: str) -> str:
    body = f"""
    <nav class="topline"><a href="/">← notariat8.de</a><span><a href="/onboarding/readiness?audience=customer">Einrichtungsstatus</a></span></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Einrichtung</p>
      <h1>Einrichtungsstatus nicht verfügbar</h1>
      <p>{html.escape(message)}</p>
    </section>
    <section class="notice">
      <h2>Nächster Schritt</h2>
      <p>Bitte öffnen Sie den Einrichtungsstatus später erneut. Es wurden keine Mandatsdaten verarbeitet.</p>
    </section>
    """
    return _layout("notariat8 Einrichtungsstatus", body)


def build_customer_onboarding_request_validation_page(
    *,
    domain: str,
    tenant_slug: str,
    admin_email: str,
    error: str,
) -> str:
    readiness_query = urlencode(
        _present_query_values(
            {
                "audience": "customer",
                "domain_hint": domain,
                "tenant_slug": tenant_slug,
            }
        )
    )
    nav = _customer_onboarding_nav(readiness_query)
    if "admin_email_domain_mismatch" in error:
        guidance = (
            "Die E-Mail-Adresse muss zur angegebenen Domain passen. "
            "Bitte verwenden Sie eine Adresse der verantwortlichen Person in diesem Notariat."
        )
    elif "admin_email_invalid" in error:
        guidance = "Bitte geben Sie eine gültige E-Mail-Adresse der verantwortlichen Person an."
    elif "admin_email_freemail_domain" in error:
        guidance = "Bitte verwenden Sie keine private Freemail-Adresse, sondern eine Adresse des Notariats."
    else:
        guidance = "Bitte prüfen Sie Ihre Angaben und starten Sie die Einrichtung erneut."
    body = f"""
    {nav}
    <section class="hero">
      <p class="eyebrow">notariat8 Einrichtung</p>
      <h1>E-Mail-Adresse prüfen</h1>
      <p>{html.escape(guidance)}</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Ihre Angaben</h2>
        <p><strong>Domain:</strong> {html.escape(domain)}</p>
        <p><strong>E-Mail-Adresse:</strong> {html.escape(admin_email) if admin_email else "nicht angegeben"}</p>
        <p><strong>Status:</strong> Einrichtung noch nicht angefragt</p>
        <div class="toolbar">
          <a class="button-link" href="/onboarding/readiness?{html.escape(readiness_query, quote=True)}">E-Mail-Adresse korrigieren</a>
        </div>
      </section>
      <section>
        <h2>Was passiert als Nächstes?</h2>
        <ul class="link-list">
          <li><span>notariat8 übernimmt keine E-Mail-Adresse automatisch aus der Domain.</span></li>
          <li><span>Nach der Korrektur prüfen Sie den DNS-TXT-Eintrag erneut.</span></li>
          <li><span>Eine Einladung wird erst nach erfolgreicher Prüfung und Freigabe vorbereitet.</span></li>
          <li><span>Keine Mandatsdaten: Diese Seite sammelt keine Urkunden, Ausweise, Akten oder Geschäftswerte.</span></li>
        </ul>
      </section>
    </div>
    """
    return _layout("notariat8 E-Mail-Adresse prüfen", body)


def build_customer_readiness_page(query: str, *, dns_resolver=None) -> str:
    params = parse_qs(query, keep_blank_values=True)
    source = _optional_query_text(params, "source", max_length=40)
    entry = _optional_query_text(params, "entry", max_length=40)
    audience = _optional_query_text(params, "audience", max_length=40)
    public_context = _is_public_prospect_context(source=source, entry=entry, audience=audience) or not (
        source or entry or audience
    )
    context_query = {"audience": "customer"} if public_context else {}
    domain_hint = _optional_query_text(params, "domain_hint", max_length=120) or "kanzlei-notariat.example"
    tenant_slug = _optional_query_text(params, "tenant_slug", max_length=80) or _tenant_slug_from_domain_hint(domain_hint)
    admin_email = _optional_query_text(params, "admin_email", max_length=160)
    admin_email_provided = bool(admin_email)
    readiness = check_domain_ready(domain=domain_hint, tenant_slug=tenant_slug, admin_email=admin_email)
    verification = readiness["verification"]
    if admin_email_provided:
        dns_check = build_live_dns_check_result(
            expected_name=verification["dns_record_name"],
            expected_value=verification["dns_record_value"],
            resolver=dns_resolver,
        )
    else:
        dns_check = build_dns_check_result(
            expected_name=verification["dns_record_name"],
            expected_value=verification["dns_record_value"],
            observed_values=[],
            resolver_error="not_found",
        )
    check_query = urlencode(
        _present_query_values({
            **context_query,
            "domain": readiness["domain"],
            "tenant_slug": readiness["tenant_slug"],
            "admin_email": readiness["admin_email"],
        })
    )
    preview_query = urlencode(
        _present_query_values({
            "domain": readiness["domain"],
            "tenant_slug": readiness["tenant_slug"],
            "admin_email": readiness["admin_email"],
        })
    )
    resume_query = urlencode(
        _present_query_values({
            **context_query,
            "domain_hint": readiness["domain"],
            "tenant_slug": readiness["tenant_slug"],
            "admin_email": readiness["admin_email"],
        })
    )
    nav = _customer_onboarding_nav(resume_query) if public_context else (
        '<nav class="topline"><a href="/">← Übersicht</a><span><a href="/admin/onboarding">Admin-Queue</a></span></nav>'
    )
    slug_label = "notariat8-Referenz" if public_context else "Tenant-Slug"
    admin_email_label = "E-Mail-Adresse der verantwortlichen Person" if public_context else "Administrations-E-Mail"
    admin_email_line = (
        f'<p><strong>{admin_email_label}:</strong> {html.escape(readiness["admin_email"])}</p>'
        if admin_email_provided
        else f"<p><strong>{admin_email_label}:</strong> noch nicht angegeben</p>"
    )
    status_label = "bereit" if readiness["ready"] else "blockiert"
    if public_context and not admin_email_provided:
        status_label = "E-Mail offen"
    admin_action = ""
    if not public_context:
        admin_action = (
            f'<a class="button-link" href="/admin/onboarding/provisioning-preview?'
            f'{html.escape(preview_query, quote=True)}">M365-Plan vorbereiten</a>'
        )
    dns_action = (
        f'<a class="button-link" href="/onboarding/dns-check?{html.escape(check_query, quote=True)}">DNS jetzt prüfen</a>'
        if admin_email_provided or not public_context
        else "<p>Die DNS-Prüfung startet erst nach Angabe der E-Mail-Adresse.</p>"
    )
    admin_email_form = ""
    if public_context and not admin_email_provided:
        admin_email_form = f"""
        <section class="notice">
          <h2>E-Mail-Adresse angeben</h2>
          <p>Tragen Sie die E-Mail-Adresse der Person ein, die die Einrichtung für Ihr Notariat starten soll.
          notariat8 leitet diese Adresse nicht aus der Domain ab; in diesem Schritt wird keine E-Mail automatisch versendet.</p>
          <form class="readiness-form" method="get" action="/onboarding/readiness">
            <input type="hidden" name="audience" value="customer">
            <input type="hidden" name="domain_hint" value="{html.escape(readiness["domain"], quote=True)}">
            <input type="hidden" name="tenant_slug" value="{html.escape(readiness["tenant_slug"], quote=True)}">
            <label>E-Mail-Adresse der verantwortlichen Person
              <input type="email" name="admin_email" autocomplete="email" required>
            </label>
            <button type="submit">E-Mail übernehmen</button>
          </form>
        </section>
        """
    guidance_items = (
        """
        <li><span>Geben Sie zuerst die E-Mail-Adresse der verantwortlichen Person ein; notariat8 nimmt dafür keine Standardadresse an.</span></li>
        <li><span>Danach tragen Sie den DNS-TXT-Eintrag bei Ihrem DNS-Anbieter ein oder geben ihn an Ihre IT weiter.</span></li>
        <li><span>Nach erfolgreicher DNS-Prüfung bereitet notariat8 die Einladung vor.</span></li>
        <li><span>Keine Mandatsdaten: Diese Seite sammelt keine Urkunden, Ausweise, Akten oder Geschäftswerte.</span></li>
        """
        if public_context and not admin_email_provided
        else """
        <li><span>Tragen Sie den DNS-TXT-Eintrag bei Ihrem DNS-Anbieter ein oder geben Sie ihn an Ihre IT weiter.</span></li>
        <li><span>Nach erfolgreicher DNS-Prüfung bereitet notariat8 die Einladung vor.</span></li>
        <li><span>Keine Mandatsdaten: Diese Seite sammelt keine Urkunden, Ausweise, Akten oder Geschäftswerte.</span></li>
        """
        if public_context
        else """
        <li><span>Nach DNS propagation kann derselbe Link erneut geprüft werden.</span></li>
        <li><span>Nach verifizierter Domain prüft <code>nac-saas-owner</code> die Admin-Einladung und den Owner-Apply-Plan.</span></li>
        <li><span>Keine Mandatsdaten: Diese Seite sammelt keine Urkunden, Ausweise, Akten oder Geschäftswerte.</span></li>
        """
    )
    dns_status_label = dns_check["status"]
    dns_guidance = dns_check["customer_guidance"]
    if public_context:
        dns_status_label, dns_guidance = _customer_dns_check_copy(dns_check)
    body = f"""
    {nav}
    <section class="hero">
      <p class="eyebrow">notariat8 Neukunden-Onboarding</p>
      <h1>{'Domain vorbereiten' if public_context else 'Domain-Readiness'}</h1>
      <p>Prüfen Sie hier, ob Ihre Domain für notariat8 vorbereitet ist. Diese Seite verwendet nur Domain,
      E-Mail-Adresse und DNS-TXT-Eintrag. Keine Mandatsdaten und keine Vorgangsdokumente.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Ihre Domain</h2>
        <p><strong>Domain:</strong> {html.escape(readiness["domain"])}</p>
        <p><strong>{html.escape(slug_label)}:</strong> {html.escape(readiness["tenant_slug"])}</p>
        {admin_email_line}
        <p><strong>Status:</strong> {html.escape(status_label)}</p>
      </section>
      {admin_email_form}
      <section>
        <h2>DNS-TXT</h2>
        <p><strong>Name:</strong> <code>{html.escape(verification["dns_record_name"])}</code></p>
        <p><strong>Wert:</strong> <code>{html.escape(verification["dns_record_value"])}</code></p>
        <div class="toolbar">
          {dns_action}
          {admin_action}
          <a class="inline-link" href="/onboarding/readiness?{html.escape(resume_query, quote=True)}">später erneut öffnen</a>
        </div>
      </section>
    </div>
    <section>
      <h2>Letzter Check</h2>
      <p><strong>DNS-Status:</strong> {html.escape(dns_status_label)}</p>
      <p>{html.escape(dns_guidance)}</p>
      <ul class="link-list">
        {guidance_items}
      </ul>
    </section>
    """
    return _layout("notariat8 Domain vorbereiten" if public_context else "NaC Domain-Readiness", body)


def build_admin_provisioning_preview_page(query: str) -> str:
    params = parse_qs(query, keep_blank_values=True)
    domain = _query_text(params, "domain")
    tenant_slug = _query_text(params, "tenant_slug")
    admin_email = _query_text(params, "admin_email")
    saas_admin_email = _optional_query_text(params, "saas_admin_email", max_length=160) or "saas-owner@example.com"
    try:
        plan = build_customer_tenant_plan(
            domain=domain,
            tenant_slug=tenant_slug,
            admin_email=admin_email,
            saas_admin_email=saas_admin_email,
        )
    except ValueError as exc:
        return _layout(
            "NaC M365-Plan blockiert",
            f"""
            <nav class="topline"><a href="/admin/onboarding">← Admin-Queue</a></nav>
            <section class="hero">
              <p class="eyebrow">M365 Graph Plan</p>
              <h1>Konfiguration blockiert</h1>
              <p><strong>Grund:</strong> <code>{html.escape(str(exc))}</code></p>
            </section>
            """,
        )
    data_plane = plan["m365"]["data_plane"]
    workspace = plan["m365"]["workspace"]
    controls = "".join(f"<li><span>{html.escape(control)}</span></li>" for control in plan["sharepoint"]["required_controls"])
    apply_query = urlencode({"domain": domain, "tenant_slug": tenant_slug, "admin_email": admin_email})
    body = f"""
    <nav class="topline"><a href="/onboarding/readiness?{html.escape(urlencode({"domain_hint": domain, "tenant_slug": tenant_slug, "admin_email": admin_email}), quote=True)}">← Readiness</a><span><a href="/admin/onboarding">Admin-Queue</a></span></nav>
    <section class="hero">
      <p class="eyebrow">M365 Graph Plan</p>
      <h1>Teams-/SharePoint-Plan</h1>
      <p>Lokale Vorschau für Entra ID, Teams und SharePoint. Diese Seite schreibt nicht nach Microsoft Graph und enthält keine Zugangsdaten.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Tenant</h2>
        <p><strong>Domain:</strong> {html.escape(plan["tenant"]["domain"])}</p>
        <p><strong>Tenant-Slug:</strong> {html.escape(plan["tenant"]["slug"])}</p>
        <p><strong>Datenhaltung:</strong> <code>{html.escape(data_plane["strategy"])}</code></p>
        <p><strong>Graph REST only:</strong> <code>{html.escape(str(data_plane["graph_rest_only"]).lower())}</code></p>
        <div class="toolbar">
          <a class="button-link" href="/admin/onboarding/apply-readiness?{html.escape(apply_query, quote=True)}">Privileged-Plan vorbereiten</a>
        </div>
      </section>
      <section>
        <h2>Arbeitsbereich</h2>
        <p><strong>Team:</strong> {html.escape(workspace["team_display_name"])}</p>
        <p><strong>Mail-Nickname:</strong> {html.escape(workspace["mail_nickname"])}</p>
        <p><strong>Initialer Admin:</strong> {html.escape(plan["admin_user"]["email"])}</p>
        <p><strong>Rolle:</strong> <code>{html.escape(plan["admin_user"]["role"])}</code></p>
      </section>
    </div>
    <section>
      <h2>SharePoint-Kontrollen</h2>
      <ul class="link-list">{controls}</ul>
    </section>
    """
    return _layout("NaC Teams-/SharePoint-Plan", body)


def build_admin_apply_readiness_page(query: str) -> str:
    params = parse_qs(query, keep_blank_values=True)
    domain = _query_text(params, "domain")
    tenant_slug = _query_text(params, "tenant_slug")
    admin_email = _query_text(params, "admin_email")
    saas_admin_email = _optional_query_text(params, "saas_admin_email", max_length=160) or "saas-owner@example.com"
    try:
        plan = build_customer_tenant_plan(
            domain=domain,
            tenant_slug=tenant_slug,
            admin_email=admin_email,
            saas_admin_email=saas_admin_email,
        )
    except ValueError as exc:
        return _layout(
            "NaC M365 Privileged-Plan blockiert",
            f"""
            <nav class="topline"><a href="/admin/onboarding">← Admin-Queue</a></nav>
            <section class="hero">
              <p class="eyebrow">Owner Apply Review</p>
              <h1>Privileged-Plan blockiert</h1>
              <p><strong>Grund:</strong> <code>{html.escape(str(exc))}</code></p>
            </section>
            """,
        )
    readiness_query = urlencode({"domain_hint": domain, "tenant_slug": tenant_slug, "admin_email": admin_email})
    preview_query = urlencode({"domain": domain, "tenant_slug": tenant_slug, "admin_email": admin_email})
    body = f"""
    <nav class="topline"><a href="/admin/onboarding/provisioning-preview?{html.escape(preview_query, quote=True)}">← Teams-/SharePoint-Plan</a><span><a href="/onboarding/readiness?{html.escape(readiness_query, quote=True)}">Readiness</a><a href="/admin/onboarding">Admin-Queue</a></span></nav>
    <section class="hero">
      <p class="eyebrow">Owner Apply Review</p>
      <h1>Privileged-Plan</h1>
      <p>Review-Artefakt für Teams, SharePoint-Schema, Site-Permissions und App-Owner. Produktive Graph-Änderungen bleiben Owner-gated.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Review-Artefakt</h2>
        <p><strong>Modus:</strong> <code>review_artifact_only</code></p>
        <p><strong>Status:</strong> <code>owner_apply_required</code></p>
        <p><strong>CLI:</strong> <code>nac m365 teams-sharepoint privileged-plan --format json</code></p>
      </section>
      <section>
        <h2>Tenant</h2>
        <p><strong>Domain:</strong> {html.escape(plan["tenant"]["domain"])}</p>
        <p><strong>Team-Strategie:</strong> <code>{html.escape(plan["m365"]["workspace"]["strategy"])}</code></p>
        <p><strong>Datenhaltung:</strong> <code>{html.escape(plan["m365"]["data_plane"]["strategy"])}</code></p>
      </section>
    </div>
    """
    return _layout("NaC M365 Privileged-Plan", body)


def _tenant_slug_from_domain_hint(domain_hint: str) -> str:
    normalized = domain_hint.strip().lower().rstrip(".")
    label = normalized.split(".", 1)[0]
    return "".join(character if character.isalnum() else "-" for character in label).strip("-") or "neukunde"


def build_bpmn_page(model) -> str:
    node_rows = "".join(
        "<tr>"
        f'<td data-label="Name">{html.escape(node.name)}</td>'
        f'<td data-label="Typ">{html.escape(node.type)}</td>'
        f'<td data-label="Rolle">{html.escape(node.nac.get("role", ""))}</td>'
        f'<td data-label="Kanal">{html.escape(node.nac.get("channel", ""))}</td>'
        f'<td data-label="Datenklasse">{html.escape(node.nac.get("dataClass", ""))}</td>'
        f'<td data-label="Freigabe">{html.escape(node.nac.get("approval", ""))}</td>'
        f'<td data-label="Nachweis">{html.escape(node.nac.get("evidence", ""))}</td>'
        "</tr>"
        for node in model.nodes
    )
    body = f"""
    <nav class="topline"><a href="/">← Übersicht</a><span><a href="/bpmn/{html.escape(model.stem)}/edit">Bearbeiten</a><a href="/api/bpmn/{html.escape(model.stem)}">JSON</a></span></nav>
    <section class="hero">
      <p class="eyebrow">BPMN-Modell</p>
      <h1>{html.escape(model.name)}</h1>
      <p>{html.escape(model.path)} · {"bpmn-js-Diagrammfläche vorhanden" if model.has_diagram else "Fallback-Layout"}</p>
    </section>
    <section class="canvas bpmn-diagram-panel"><div class="diagram-scroll">{render_bpmn_svg(model)}</div></section>
    <section>
      <h2>NaC-Schritte</h2>
      <div class="table-scroll responsive-table">
        <table>
          <thead><tr><th>Name</th><th>Typ</th><th>Rolle</th><th>Kanal</th><th>Datenklasse</th><th>Freigabe</th><th>Nachweis</th></tr></thead>
          <tbody>{node_rows}</tbody>
        </table>
      </div>
    </section>
    """
    return _layout(f"BPMN: {model.name}", body)


def build_bpmn_editor_page(model) -> str:
    stem = html.escape(model.stem)
    node_menu = _bpmn_editor_node_menu(model)
    body = f"""
    <nav class="topline"><a href="/">← Übersicht</a><span><a href="/kg/{stem}">Checkliste</a><a href="/bpmn/{stem}">Ansicht</a><a href="/api/bpmn/{stem}/xml">XML API</a></span></nav>
    <section class="hero">
      <p class="eyebrow">BPMN-js Editor</p>
      <h1>{html.escape(model.name)}</h1>
      <p>{html.escape(model.path)} · Änderungen werden erst als BPMN-XML im Repository gespeichert und danach über Git validiert.</p>
    </section>
    <section class="bpmn-editor-shell">
      <div class="editor-commandbar" role="toolbar" aria-label="BPMN Editor Menü">
        <div class="command-group">
          <button id="save-model" type="button">Speichern</button>
          <button id="reload-model" type="button">Neu laden</button>
          <button id="validate-model" type="button">Prüfen</button>
        </div>
        <div class="command-group">
          <button id="undo-model" type="button">Rückgängig</button>
          <button id="redo-model" type="button">Wiederholen</button>
          <button id="delete-element" type="button">Löschen</button>
        </div>
        <div class="command-group">
          <button data-create-kind="bpmn:Task" type="button">Aufgabe</button>
          <button data-create-kind="bpmn:UserTask" type="button">Person</button>
          <button data-create-kind="bpmn:ServiceTask" type="button">Service</button>
          <button data-create-kind="bpmn:ExclusiveGateway" type="button">Entscheidung</button>
          <button data-create-kind="bpmn:EndEvent" type="button">Ende</button>
        </div>
        <div class="command-group">
          <button id="fit-model" type="button">Einpassen</button>
          <button id="zoom-in-model" type="button">Zoom +</button>
          <button id="zoom-out-model" type="button">Zoom -</button>
          <button id="toggle-xml" type="button">XML</button>
        </div>
      </div>
      <div class="editor-statusbar">
        <span id="editor-status">lade Editor ...</span>
        <span id="dirty-state">unverändert</span>
      </div>
      <div class="editor-workbench">
        <aside class="editor-side-panel">
          <h2>Schritte</h2>
          <div class="step-list">{node_menu}</div>
        </aside>
        <div class="editor-canvas-region">
          <div id="bpmn-canvas" class="modeler-canvas"></div>
        </div>
        <aside class="editor-properties-panel">
          <h2>Eigenschaften</h2>
          <form id="properties-form">
            <div class="selected-element" id="selected-element">Kein Element ausgewählt</div>
            <label for="element-name">Name</label>
            <input id="element-name" name="name" type="text" autocomplete="off">
            <label for="nac-role">Rolle</label>
            <select id="nac-role" name="role">
              <option value=""></option>
              <option value="notary_clerk">Notariatsfachkraft</option>
              <option value="notary">Notarin/Notar</option>
              <option value="system_betreuer">Systembetreuung</option>
              <option value="client">Mandant</option>
              <option value="compliance">Compliance</option>
            </select>
            <label for="nac-channel">Kanal</label>
            <input id="nac-channel" name="channel" type="text" autocomplete="off">
            <label for="nac-data-class">Datenklasse</label>
            <input id="nac-data-class" name="dataClass" type="text" autocomplete="off">
            <label for="nac-approval">Freigabe</label>
            <input id="nac-approval" name="approval" type="text" autocomplete="off">
            <label for="nac-evidence">Nachweis</label>
            <input id="nac-evidence" name="evidence" type="text" autocomplete="off">
            <label for="nac-plugin">Plugin</label>
            <input id="nac-plugin" name="plugin" type="text" autocomplete="off">
            <label for="nac-kg-ref">KG-Referenz</label>
            <input id="nac-kg-ref" name="kgRef" type="text" autocomplete="off">
            <label class="check-label" for="nac-local-execution">
              <input id="nac-local-execution" name="localExecution" type="checkbox">
              lokal ausführen
            </label>
            <button id="apply-properties" type="submit">Übernehmen</button>
          </form>
        </aside>
      </div>
      <div id="xml-panel" class="xml-panel is-hidden">
        <div class="xml-toolbar">
          <label class="xml-label" for="xml-editor">BPMN XML</label>
          <button id="import-xml" type="button">XML anwenden</button>
        </div>
        <textarea id="xml-editor" spellcheck="false"></textarea>
      </div>
    </section>
    <script>{_bpmn_editor_script(model.stem)}</script>
    """
    return _layout(f"BPMN bearbeiten: {model.name}", body, head_extra=_bpmn_editor_head())


def _bpmn_editor_head() -> str:
    return """
  <link rel="stylesheet" href="https://unpkg.com/bpmn-js@17.11.1/dist/assets/diagram-js.css">
  <link rel="stylesheet" href="https://unpkg.com/bpmn-js@17.11.1/dist/assets/bpmn-font/css/bpmn-embedded.css">
"""


def _bpmn_editor_node_menu(model) -> str:
    if not model.nodes:
        return '<p class="empty-state">Keine Schritte.</p>'
    return "".join(
        '<button class="step-button" type="button" '
        f'data-select-element="{html.escape(node.id, quote=True)}">'
        f'<span>{html.escape(node.name or node.id)}</span>'
        f'<small>{html.escape(_bpmn_node_type_label(node.type))}</small>'
        "</button>"
        for node in model.nodes
    )


def _bpmn_node_type_label(node_type: str) -> str:
    labels = {
        "businessRuleTask": "Regel",
        "callActivity": "Aufruf",
        "endEvent": "Ende",
        "exclusiveGateway": "Entscheidung",
        "manualTask": "Manuell",
        "parallelGateway": "Parallel",
        "receiveTask": "Empfang",
        "scriptTask": "Skript",
        "sendTask": "Versand",
        "serviceTask": "Service",
        "startEvent": "Start",
        "subProcess": "Teilprozess",
        "task": "Aufgabe",
        "userTask": "Person",
    }
    return labels.get(node_type, node_type)


def _bpmn_editor_script(stem: str) -> str:
    replacements = {
        "__ENDPOINT__": json.dumps(f"/api/bpmn/{stem}/xml"),
        "__MODDLE_ENDPOINT__": json.dumps("/api/bpmn-moddle"),
    }
    script = r"""
    const endpoint = __ENDPOINT__;
    const moddleEndpoint = __MODDLE_ENDPOINT__;
    const modelerScript = "https://unpkg.com/bpmn-js@17.11.1/dist/bpmn-modeler.production.min.js";
    const nacKeys = ["role", "channel", "dataClass", "approval", "evidence", "plugin", "kgRef"];
    let baseSha256 = "";
    let loadedXml = "";
    let modeler = null;
    let selectedElement = null;
    let wired = false;

    const statusEl = document.getElementById("editor-status");
    const dirtyEl = document.getElementById("dirty-state");
    const xmlEditor = document.getElementById("xml-editor");
    const xmlPanel = document.getElementById("xml-panel");
    const propertiesForm = document.getElementById("properties-form");
    const selectedEl = document.getElementById("selected-element");
    const buttons = {
      save: document.getElementById("save-model"),
      reload: document.getElementById("reload-model"),
      validate: document.getElementById("validate-model"),
      undo: document.getElementById("undo-model"),
      redo: document.getElementById("redo-model"),
      delete: document.getElementById("delete-element"),
      fit: document.getElementById("fit-model"),
      zoomIn: document.getElementById("zoom-in-model"),
      zoomOut: document.getElementById("zoom-out-model"),
      toggleXml: document.getElementById("toggle-xml"),
      importXml: document.getElementById("import-xml")
    };

    function setStatus(value) {
      statusEl.textContent = value;
    }

    function setDirty(value) {
      dirtyEl.textContent = value ? "ungespeichert" : "unverändert";
      dirtyEl.classList.toggle("is-dirty", value);
    }

    function setBusy(value) {
      document.querySelectorAll(".editor-commandbar button, #import-xml")
        .forEach((button) => { button.disabled = value; });
      if (value) document.getElementById("apply-properties").disabled = true;
    }

    function loadScript(src) {
      return new Promise((resolve, reject) => {
        if (window.BpmnJS) {
          resolve();
          return;
        }
        const script = document.createElement("script");
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }

    async function loadDocument() {
      const response = await fetch(endpoint);
      if (!response.ok) throw new Error(await response.text());
      const payload = await response.json();
      baseSha256 = payload.sha256;
      loadedXml = payload.xml;
      xmlEditor.value = payload.xml;
      setDirty(false);
      setStatus("geladen · " + payload.sha256.slice(0, 12));
    }

    async function createModeler() {
      if (modeler) return;
      await loadScript(modelerScript);
      const descriptor = await fetch(moddleEndpoint).then((response) => response.json());
      modeler = new window.BpmnJS({
        container: "#bpmn-canvas",
        keyboard: { bindTo: document },
        moddleExtensions: { nac: descriptor }
      });
      wireModeler();
    }

    function wireModeler() {
      if (wired) return;
      wired = true;
      const eventBus = modeler.get("eventBus");
      eventBus.on("selection.changed", (event) => {
        selectedElement = event.newSelection[0] || null;
        renderProperties();
        markStepSelection();
      });
      eventBus.on("element.changed", (event) => {
        if (selectedElement && event.element && event.element.id === selectedElement.id) {
          selectedElement = event.element;
          renderProperties();
        }
      });
      eventBus.on("commandStack.changed", async () => {
        await syncXmlFromCanvas();
        updateCommandState();
      });
    }

    async function importXml(xml) {
      await createModeler();
      await modeler.importXML(xml);
      modeler.get("canvas").zoom("fit-viewport");
      selectedElement = null;
      renderProperties();
      updateCommandState();
      setStatus("Editor bereit · Änderungen bleiben lokal bis Speichern");
    }

    async function syncXmlFromCanvas() {
      if (!modeler) return;
      const saved = await modeler.saveXML({ format: true });
      xmlEditor.value = saved.xml;
      setDirty(saved.xml !== loadedXml);
    }

    function updateCommandState() {
      if (!modeler) return;
      const commandStack = modeler.get("commandStack");
      buttons.undo.disabled = !commandStack.canUndo();
      buttons.redo.disabled = !commandStack.canRedo();
      buttons.delete.disabled = !selectedElement;
    }

    function markStepSelection() {
      document.querySelectorAll("[data-select-element]").forEach((button) => {
        button.classList.toggle("is-selected", selectedElement && button.dataset.selectElement === selectedElement.id);
      });
    }

    function selectElement(id) {
      if (!modeler) return;
      const registry = modeler.get("elementRegistry");
      const selection = modeler.get("selection");
      const element = registry.get(id);
      if (!element) return;
      selection.select(element);
      focusElement(element);
    }

    function focusElement(element) {
      const canvas = modeler.get("canvas");
      const viewbox = canvas.viewbox();
      canvas.viewbox({
        x: element.x + element.width / 2 - viewbox.width / 2,
        y: element.y + element.height / 2 - viewbox.height / 2,
        width: viewbox.width,
        height: viewbox.height
      });
    }

    function getNacValue(businessObject, key) {
      if (!businessObject) return "";
      if (typeof businessObject.get === "function") {
        const namespaced = businessObject.get("nac:" + key);
        if (namespaced !== undefined && namespaced !== null) return String(namespaced);
        const plain = businessObject.get(key);
        if (plain !== undefined && plain !== null) return String(plain);
      }
      if (businessObject.$attrs && businessObject.$attrs["nac:" + key] !== undefined) {
        return String(businessObject.$attrs["nac:" + key]);
      }
      return "";
    }

    function canHaveNacProperties(businessObject) {
      if (!businessObject || !businessObject.$type) return false;
      return !businessObject.$type.includes("SequenceFlow") && !businessObject.$type.includes("Participant");
    }

    function renderProperties() {
      const businessObject = selectedElement && selectedElement.businessObject;
      const hasSelection = Boolean(businessObject);
      const hasNac = canHaveNacProperties(businessObject);
      selectedEl.textContent = hasSelection
        ? selectedElement.id + " · " + businessObject.$type.replace("bpmn:", "")
        : "Kein Element ausgewählt";
      document.getElementById("element-name").value = hasSelection ? (businessObject.name || "") : "";
      nacKeys.forEach((key) => {
        const fieldId = "nac-" + key.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
        const field = document.getElementById(fieldId);
        if (!field) return;
        field.value = hasSelection ? getNacValue(businessObject, key) : "";
        field.disabled = !hasNac;
      });
      const localExecution = document.getElementById("nac-local-execution");
      localExecution.checked = hasSelection && getNacValue(businessObject, "localExecution") === "true";
      localExecution.disabled = !hasNac;
      document.getElementById("apply-properties").disabled = !hasSelection;
      updateCommandState();
    }

    function applyProperties(event) {
      event.preventDefault();
      if (!modeler || !selectedElement) return;
      const modeling = modeler.get("modeling");
      const props = { name: document.getElementById("element-name").value.trim() };
      if (canHaveNacProperties(selectedElement.businessObject)) {
        nacKeys.forEach((key) => {
          const fieldId = "nac-" + key.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
          const field = document.getElementById(fieldId);
          props["nac:" + key] = field ? field.value.trim() : "";
        });
        props["nac:localExecution"] = document.getElementById("nac-local-execution").checked;
      }
      modeling.updateProperties(selectedElement, props);
      setStatus("Eigenschaften übernommen");
    }

    function addShape(type) {
      if (!modeler) return;
      const canvas = modeler.get("canvas");
      const elementFactory = modeler.get("elementFactory");
      const modeling = modeler.get("modeling");
      const shape = elementFactory.createShape({ type });
      if (selectedElement && selectedElement.parent && !selectedElement.businessObject.$type.includes("SequenceFlow")) {
        const position = {
          x: selectedElement.x + selectedElement.width + 180,
          y: selectedElement.y + selectedElement.height / 2
        };
        modeling.appendShape(selectedElement, shape, position, selectedElement.parent);
        return;
      }
      const root = canvas.getRootElement();
      const viewbox = canvas.viewbox();
      modeling.createShape(shape, {
        x: viewbox.x + viewbox.width / 2,
        y: viewbox.y + viewbox.height / 2
      }, root);
    }

    async function saveDocument() {
      try {
        setBusy(true);
        setStatus("speichere ...");
        await syncXmlFromCanvas();
        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ xml: xmlEditor.value, base_sha256: baseSha256 })
        });
        const payload = await response.json();
        if (!response.ok) {
          setStatus("nicht gespeichert · " + payload.error);
          return;
        }
        baseSha256 = payload.sha256;
        loadedXml = payload.xml;
        xmlEditor.value = payload.xml;
        setDirty(false);
        setStatus("gespeichert · " + payload.sha256.slice(0, 12));
      } catch (error) {
        setStatus("nicht gespeichert · " + error.message);
      } finally {
        setBusy(false);
        renderProperties();
      }
    }

    async function reloadDocument() {
      if (dirtyEl.classList.contains("is-dirty") && !window.confirm("Ungespeicherte Änderungen verwerfen?")) return;
      try {
        setBusy(true);
        await loadDocument();
        await importXml(xmlEditor.value);
      } catch (error) {
        setStatus("Fehler · " + error.message);
      } finally {
        setBusy(false);
        renderProperties();
      }
    }

    async function validateDocument() {
      try {
        await syncXmlFromCanvas();
        if (!xmlEditor.value.includes("<bpmn:process")) {
          setStatus("Prüfung fehlgeschlagen · bpmn:process fehlt");
          return;
        }
        setStatus("Prüfung ok · XML kann gespeichert werden");
      } catch (error) {
        setStatus("Prüfung fehlgeschlagen · " + error.message);
      }
    }

    buttons.save.addEventListener("click", saveDocument);
    buttons.reload.addEventListener("click", reloadDocument);
    buttons.validate.addEventListener("click", validateDocument);
    buttons.undo.addEventListener("click", () => modeler && modeler.get("commandStack").undo());
    buttons.redo.addEventListener("click", () => modeler && modeler.get("commandStack").redo());
    buttons.delete.addEventListener("click", () => {
      if (modeler && selectedElement) modeler.get("modeling").removeElements([selectedElement]);
    });
    buttons.fit.addEventListener("click", () => modeler && modeler.get("canvas").zoom("fit-viewport"));
    buttons.zoomIn.addEventListener("click", () => modeler && modeler.get("zoomScroll").stepZoom(1));
    buttons.zoomOut.addEventListener("click", () => modeler && modeler.get("zoomScroll").stepZoom(-1));
    buttons.toggleXml.addEventListener("click", () => xmlPanel.classList.toggle("is-hidden"));
    buttons.importXml.addEventListener("click", async () => {
      try {
        await importXml(xmlEditor.value);
        setDirty(xmlEditor.value !== loadedXml);
      } catch (error) {
        setStatus("XML nicht angewendet · " + error.message);
      }
    });
    propertiesForm.addEventListener("submit", applyProperties);
    xmlEditor.addEventListener("input", () => setDirty(xmlEditor.value !== loadedXml));
    document.querySelectorAll("[data-select-element]").forEach((button) => {
      button.addEventListener("click", () => selectElement(button.dataset.selectElement));
    });
    document.querySelectorAll("[data-create-kind]").forEach((button) => {
      button.addEventListener("click", () => addShape(button.dataset.createKind));
    });

    setBusy(true);
    loadDocument()
      .then(() => importXml(xmlEditor.value))
      .catch((error) => setStatus("Fehler · " + error.message))
      .finally(() => {
        setBusy(false);
        renderProperties();
      });
"""
    for key, value in replacements.items():
        script = script.replace(key, value)
    return script


def build_kg_page(view: dict[str, Any]) -> str:
    tabs = "".join(_render_kg_tab(tab) for tab in view["editor_model"]["tabs"])
    status = _status_label(view.get("status", ""))
    body = f"""
    <nav class="topline"><a href="/">← Übersicht</a><span><a href="/costs/{html.escape(view['usecase_slug'])}">Kosten</a><a href="/api/kg/{html.escape(view['usecase_slug'])}">JSON</a></span></nav>
    <section class="hero">
      <p class="eyebrow">KG-Editor-View</p>
      <h1>{html.escape(view['title'])}</h1>
      <p>Status: {html.escape(status)}</p>
    </section>
    <section class="notice">
      <strong>Schutzregel:</strong> Diese Ansicht zeigt keine Mandatswerte.
      Änderungen werden als Vorschlag erfasst und erst nach Validierung, Änderungsvergleich und Review übernommen.
    </section>
    {tabs}
    """
    return _layout(f"KG: {view['title']}", body)


def build_cost_page(view: dict[str, Any]) -> str:
    slug = html.escape(view["usecase_slug"])
    node_items = "".join(
        "<li>"
        f"<strong>{html.escape(str(node.get('label', node.get('id', ''))))}</strong>"
        f"<span>{html.escape(_status_label(node.get('status', '')))} · {html.escape(str(node.get('type', '')))}</span>"
        "</li>"
        for node in view.get("nodes", [])
    )
    edge_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(edge.get('source', '')))}</td>"
        f"<td>{html.escape(str(edge.get('type', '')))}</td>"
        f"<td>{html.escape(str(edge.get('target', '')))}</td>"
        "</tr>"
        for edge in view.get("edges", [])
    )
    body = f"""
    <nav class="topline"><a href="/">← Übersicht</a><span><a href="/kg/{slug}">Checkliste</a><a href="/api/costs/{slug}">JSON</a></span></nav>
    <section class="hero">
      <p class="eyebrow">GNotKG-Kostenprüfung</p>
      <h1>{html.escape(view['title'])}</h1>
      <p>Geschäftswerte werden nur lokal eingegeben und nicht im Produktrepo gespeichert.</p>
    </section>
    <section class="notice">
      <strong>Prüfgrenze:</strong> Die Berechnung ist ein technischer Entwurf.
      Die finale Kostenprüfung bleibt ein notarielles Review-Gate.
    </section>
    <section class="quote-panel">
      <h2>Gebühr berechnen</h2>
      <form id="gnotkg-quote-form" class="quote-form">
        <label for="business-value">Geschäftswert</label>
        <input id="business-value" name="business_value" inputmode="decimal" value="500000">
        <label for="fee-table">Tabelle</label>
        <select id="fee-table" name="table">
          <option value="A">Tabelle A</option>
          <option value="B">Tabelle B</option>
        </select>
        <label for="fee-rate">Gebührensatz</label>
        <input id="fee-rate" name="fee_rate" inputmode="decimal" value="1.0">
        <label for="kv-number">KV-Nummer</label>
        <input id="kv-number" name="kv_number" value="21100">
        <button type="submit">Berechnen</button>
      </form>
      <output id="gnotkg-quote-result" class="quote-result">Noch keine Berechnung.</output>
    </section>
    <section>
      <h2>Kostenpfad</h2>
      <ol class="cost-flow">{node_items}</ol>
    </section>
    <section>
      <h2>Verknüpfungen</h2>
      <div class="table-scroll">
        <table>
          <thead><tr><th>Quelle</th><th>Beziehung</th><th>Ziel</th></tr></thead>
          <tbody>{edge_rows}</tbody>
        </table>
      </div>
    </section>
    <script>{_cost_page_script(view['usecase_slug'])}</script>
    """
    return _layout(f"GNotKG: {view['title']}", body)


def _cost_page_script(slug: str) -> str:
    return f"""
    const form = document.getElementById("gnotkg-quote-form");
    const result = document.getElementById("gnotkg-quote-result");
    form.addEventListener("submit", async (event) => {{
      event.preventDefault();
      const data = new FormData(form);
      const payload = Object.fromEntries(data.entries());
      payload.usecase_slug = {json.dumps(slug)};
      result.textContent = "berechne ...";
      const response = await fetch("/api/gnotkg/quote", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload)
      }});
      const quotePayload = await response.json();
      if (!response.ok) {{
        result.textContent = "Fehler: " + (quotePayload.error || "ungültige Eingabe");
        return;
      }}
      result.textContent = [
        "Basisgebühr " + quotePayload.base_fee + " EUR",
        "Gebühr " + quotePayload.fee_amount + " EUR",
        "Tabelle " + quotePayload.table,
        "Satz " + quotePayload.fee_rate
      ].join(" · ");
    }});
"""


def _render_kg_tab(tab: dict[str, Any]) -> str:
    if "groups" in tab:
        content = "".join(_render_kg_items(group["label_de"], group.get("items", [])) for group in tab["groups"])
    else:
        content = _render_kg_items(tab["label_de"], tab.get("items", []))
    return f"<section><h2>{html.escape(tab['label_de'])}</h2>{content}</section>"


def _render_kg_items(label: str, items: list[dict[str, Any]]) -> str:
    if not items:
        return f"<p>{html.escape(label)}: keine Einträge.</p>"
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('label', item.get('id', ''))))}</td>"
        f"<td>{html.escape(_status_label(item.get('status', '')))}</td>"
        f"<td>{html.escape(_role_or_source_label(item))}</td>"
        "</tr>"
        for item in items
    )
    return (
        "<table>"
        "<thead><tr><th>Eintrag</th><th>Status</th><th>Rolle/Quelle</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
    )


def _status_label(value: Any) -> str:
    raw = str(value or "").strip()
    return STATUS_LABELS_DE.get(raw, _identifier_fallback(raw))


def _role_or_source_label(item: dict[str, Any]) -> str:
    if "owner_role" in item:
        raw = str(item.get("owner_role") or "").strip()
        return ROLE_LABELS_DE.get(raw, _identifier_fallback(raw))
    return str(item.get("source", "") or "").strip()


def _identifier_fallback(value: str) -> str:
    return value.replace("_", " ").replace("-", " ")


def _payload_text(payload: dict[str, Any], key: str, default: str | None = None) -> str:
    value = payload.get(key)
    if value not in (None, ""):
        return str(value)
    if default is not None:
        return default
    raise ValueError(f"{key} fehlt")


def _query_text(params: dict[str, list[str]], key: str) -> str:
    values = params.get(key) or []
    value = values[0] if values else ""
    if value:
        return value
    raise ValueError(f"{key} fehlt")


def _optional_query_text(params: dict[str, list[str]], key: str, *, max_length: int | None = None) -> str:
    values = params.get(key) or []
    value = values[0].strip() if values else ""
    if max_length is not None:
        return value[:max_length]
    return value


def _is_notariat8_source(source: str) -> bool:
    return source in {"notariat8", "www-n8"}


def _present_query_values(values: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in values.items() if value}


def _is_public_prospect_context(*, source: str, entry: str, audience: str) -> bool:
    return audience == "customer" or (_is_notariat8_source(source) and entry == "prospect")


def _customer_onboarding_nav(readiness_query: str) -> str:
    escaped_query = html.escape(readiness_query, quote=True)
    return (
        '<nav class="topline">'
        '<a href="https://www.notariat8.de/">← notariat8.de</a>'
        f'<span><a href="/onboarding/readiness?{escaped_query}">Einrichtungsstatus</a></span>'
        "</nav>"
    )


def _optional_query_bool(params: dict[str, list[str]], key: str, *, default: bool) -> bool:
    raw = _optional_query_text(params, key, max_length=12).lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "ja"}:
        return True
    if raw in {"0", "false", "no", "nein"}:
        return False
    raise ValueError(f"{key} ungültig")


def _reject_caller_supplied_login_config(params: dict[str, list[str]]) -> None:
    server_side_fields = {
        "issuer_url",
        "authorization_endpoint",
        "token_endpoint",
        "client_id",
        "redirect_uri",
        "state",
        "nonce",
    }
    if any(params.get(field) for field in server_side_fields):
        raise ValueError("login_intent_config_is_server_side")


def _login_intent_config_from_env(
    *,
    secret_text_provider: Callable[[str], str] | None = None,
) -> dict[str, str]:
    config = {
        "issuer_url": os.environ.get("NAC_OIDC_ISSUER_URL", "").strip(),
        "client_id": os.environ.get("NAC_OIDC_CLIENT_ID", "").strip(),
        "redirect_uri": os.environ.get("NAC_OIDC_REDIRECT_URI", "").strip(),
        "state_signing_key": _oidc_state_signing_key_from_env(secret_text_provider=secret_text_provider),
    }
    if not all(config[field] for field in ("issuer_url", "client_id", "redirect_uri")):
        raise ValueError("login_intent_config_missing")
    return config


def _auth_callback_state_validation_configured() -> bool:
    return bool(
        os.environ.get("NAC_OIDC_STATE_SIGNING_KEY", "").strip()
        or os.environ.get("NAC_OIDC_STATE_SIGNING_KEY_SECRET_REF", "").strip()
        or os.environ.get("NAC_OIDC_STATE_VALIDATION_KEY_REF", "").strip()
    )


def _auth_callback_state_validation(
    state: str,
    *,
    secret_text_provider: Callable[[str], str] | None = None,
) -> dict[str, Any] | None:
    try:
        signing_key = _oidc_state_signing_key_from_env(secret_text_provider=secret_text_provider)
    except ValueError:
        return None
    if not signing_key:
        return None
    return validate_signed_state(state, signing_key=signing_key)


def _oidc_state_signing_key_from_env(
    *,
    secret_text_provider: Callable[[str], str] | None = None,
) -> str:
    inline_key = os.environ.get("NAC_OIDC_STATE_SIGNING_KEY", "").strip()
    if inline_key:
        return inline_key
    secret_ref = os.environ.get("NAC_OIDC_STATE_SIGNING_KEY_SECRET_REF", "").strip()
    if not secret_ref:
        return ""
    try:
        signing_key = _secret_text(secret_ref, secret_text_provider, error_class="state_signing_key_unavailable")
    except ValueError as exc:
        raise ValueError("state_signing_key_unavailable") from exc
    if not signing_key:
        raise ValueError("state_signing_key_unavailable")
    return signing_key


def _auth_callback_token_exchange_configured() -> bool:
    return bool(os.environ.get("NAC_OIDC_CLIENT_SECRET_REF", "").strip())


def _auth_callback_token_exchange_result(
    *,
    code: str,
    state_validation: dict[str, Any] | None,
    redirect_uri: str,
    token_endpoint: str,
    client_id: str,
    secret_text_provider: Callable[[str], str] | None = None,
) -> dict[str, Any] | None:
    if not _auth_callback_token_exchange_configured():
        return None
    if not isinstance(state_validation, dict) or state_validation.get("status") != "valid":
        return None
    verifier = _auth_callback_id_token_verifier()
    if not code or not redirect_uri or not token_endpoint or not client_id or verifier is None:
        return exchange_oidc_authorization_code(
            code=code,
            redirect_uri=redirect_uri,
            token_endpoint=token_endpoint,
            client_id=client_id,
            client_secret="",
            id_token_verifier=verifier,
        )
    client_secret = ""
    try:
        client_secret = _auth_callback_oidc_client_secret_from_env(secret_text_provider=secret_text_provider)
    except ValueError:
        client_secret = ""
    return exchange_oidc_authorization_code(
        code=code,
        redirect_uri=redirect_uri,
        token_endpoint=token_endpoint,
        client_id=client_id,
        client_secret=client_secret,
        id_token_verifier=verifier,
    )


def _auth_callback_oidc_client_secret_from_env(
    *,
    secret_text_provider: Callable[[str], str] | None = None,
) -> str:
    inline_secret = os.environ.get("NAC_OIDC_CLIENT_SECRET", "").strip()
    if inline_secret:
        return inline_secret
    secret_ref = os.environ.get("NAC_OIDC_CLIENT_SECRET_REF", "").strip()
    if not secret_ref:
        return ""
    try:
        client_secret = _secret_text(secret_ref, secret_text_provider, error_class="oidc_client_secret_unavailable")
    except ValueError as exc:
        raise ValueError("oidc_client_secret_unavailable") from exc
    if not client_secret:
        raise ValueError("oidc_client_secret_unavailable")
    return client_secret


def _auth_callback_id_token_verifier() -> Callable[[str], dict[str, Any] | None] | None:
    issuer = _auth_callback_expected_issuer()
    audience = os.environ.get("NAC_OIDC_CLIENT_ID", "").strip()
    return build_oidc_id_token_verifier(
        issuer=issuer,
        audience=audience,
        discovery_base_url=_auth_callback_issuer_url(),
    )


def _auth_callback_token_exchange_metadata() -> dict[str, str]:
    issuer_url = _auth_callback_issuer_url()
    token_endpoint = _token_endpoint_from_issuer(issuer_url) if issuer_url else ""
    return {
        "redirect_uri": os.environ.get("NAC_OIDC_REDIRECT_URI", "").strip(),
        "token_endpoint": token_endpoint,
        "client_id": os.environ.get("NAC_OIDC_CLIENT_ID", "").strip(),
    }


def _auth_callback_expected_issuer() -> str:
    return (
        os.environ.get("NAC_OIDC_EXPECTED_ISSUER", "").strip().rstrip("/")
        or _auth_callback_issuer_url()
    )


def _auth_callback_issuer_url() -> str:
    return os.environ.get("NAC_OIDC_ISSUER_URL", "").strip().rstrip("/")


def _token_endpoint_from_issuer(issuer_url: str) -> str:
    parsed = urlparse(issuer_url)
    hostname = (parsed.hostname or "").lower()
    if hostname in {"login.microsoftonline.com", "login.windows.net", "sts.windows.net"} and parsed.path.rstrip("/").endswith("/v2.0"):
        return f"{issuer_url.removesuffix('/v2.0').rstrip('/')}/oauth2/v2.0/token"
    return f"{issuer_url}/oauth2/v1/token"


def _auth_callback_session_signing_key(
    *,
    secret_text_provider: Callable[[str], str] | None = None,
) -> str:
    inline_key = os.environ.get("NAC_SESSION_SIGNING_KEY", "").strip()
    if inline_key:
        return inline_key
    secret_ref = os.environ.get("NAC_SESSION_SIGNING_KEY_REF", "").strip()
    if not secret_ref:
        return ""
    try:
        return _secret_text(secret_ref, secret_text_provider, error_class="session_signing_key_unavailable")
    except Exception:
        return ""


def _secret_text(
    secret_ref: str,
    secret_text_provider: Callable[[str], str] | None,
    *,
    error_class: str,
) -> str:
    if secret_text_provider is None:
        raise ValueError(error_class)
    try:
        return secret_text_provider(secret_ref).strip()
    except Exception as exc:
        raise ValueError(error_class) from exc


def _auth_callback_session_ttl_seconds() -> int:
    raw_value = os.environ.get("NAC_SESSION_TTL_SECONDS", "").strip()
    if not raw_value:
        return DEFAULT_SESSION_TTL_SECONDS
    try:
        return int(raw_value)
    except ValueError:
        return DEFAULT_SESSION_TTL_SECONDS


def _auth_callback_response_headers(callback_result: dict[str, Any]) -> dict[str, str]:
    session = callback_result.get("session_boundary", {}).get("session", {})
    set_cookie = session.get("set_cookie") if isinstance(session, dict) else None
    if not isinstance(set_cookie, str) or not set_cookie:
        return {}
    return {"Set-Cookie": set_cookie}


def _persist_auth_callback_session(
    *,
    callback_result: dict[str, Any],
    token_exchange_result: dict[str, Any] | None,
    state_validation: dict[str, Any],
    session_store: RuntimeSessionStoreAdapter,
) -> bool:
    create_session_record = getattr(session_store, "create_session_record", None)
    if not callable(create_session_record):
        return False
    session = callback_result.get("session_boundary", {}).get("session", {})
    if not isinstance(session, dict):
        return False
    payload = _session_cookie_payload_from_set_cookie(str(session.get("set_cookie", "")))
    if not payload:
        return False
    claims = token_exchange_result.get("claims") if isinstance(token_exchange_result, dict) else {}
    subject_hash = _auth_subject_hash(claims if isinstance(claims, dict) else {})
    tenant_slug = _safe_auth_session_text(state_validation.get("tenant_hint"), 80) or "default"
    role_class = _safe_auth_session_text(callback_result.get("role_gate", {}).get("role"), 80) or "nac-tenant-admin"
    try:
        create_session_record(
            session_id=str(payload["sid"]),
            tenant_slug=tenant_slug,
            subject_hash=subject_hash,
            role_class=role_class,
            usecase_slug=_auth_callback_default_usecase_slug(),
            purpose="portal-start",
            issued_at=int(payload["iat"]),
            expires_at=int(payload["exp"]),
            audit_event_id=_auth_session_audit_event_id(payload),
        )
        return True
    except Exception:
        return False


def _mark_callback_session_store_unavailable(callback_result: dict[str, Any]) -> None:
    session = callback_result.get("session_boundary", {}).get("session")
    if isinstance(session, dict):
        session["cookie_issued"] = False
        session["session_allowed"] = False
        session.pop("set_cookie", None)
    guardrails = callback_result.get("guardrails")
    if isinstance(guardrails, dict):
        guardrails["session_cookie_issued"] = False
    callback_result["next_step"] = "server_session_store_unavailable"


def _session_cookie_payload_from_set_cookie(set_cookie: str) -> dict[str, Any] | None:
    cookie = SimpleCookie()
    try:
        cookie.load(set_cookie)
    except CookieError:
        return None
    morsel = cookie.get(DEFAULT_SESSION_COOKIE_NAME)
    if morsel is None:
        return None
    payload_part = morsel.value.strip().split(".", 1)[0]
    if not payload_part:
        return None
    try:
        padding = "=" * (-len(payload_part) % 4)
        payload = json.loads(base64.urlsafe_b64decode(f"{payload_part}{padding}".encode("ascii")).decode("utf-8"))
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get("sid"), str) or not payload.get("sid"):
        return None
    if not isinstance(payload.get("iat"), int) or not isinstance(payload.get("exp"), int):
        return None
    return payload


def _auth_subject_hash(claims: dict[str, Any]) -> str:
    subject = _safe_auth_session_text(claims.get("sub"), 256)
    if not subject:
        subject = _safe_auth_session_text(claims.get("email"), 256)
    if not subject:
        subject = "subject-unavailable"
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()


def _auth_session_audit_event_id(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(str(payload.get("sid", "")).encode("utf-8")).hexdigest()[:16]
    return f"session-{digest}"


def _auth_callback_default_usecase_slug() -> str:
    return os.environ.get("NAC_DEFAULT_USECASE_SLUG", "immobilienkaufvertrag").strip() or "immobilienkaufvertrag"


def _safe_auth_session_text(value: Any, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _auth_callback_diagnostics_html(callback_result: dict[str, Any]) -> str:
    session_boundary = callback_result.get("session_boundary", {})
    token_exchange = callback_result.get("token_exchange", {})
    jwt_validation = callback_result.get("jwt_validation", {})
    role_gate = callback_result.get("role_gate", {})
    session = session_boundary.get("session", {}) if isinstance(session_boundary, dict) else {}
    items = [
        ("Token-Austausch", _token_exchange_status_label(token_exchange)),
        ("Token-Prüfung", _safe_status_label(jwt_validation.get("status"))),
        ("Rollenprüfung", _role_gate_status_label(role_gate)),
        ("Sitzung", "erstellt" if isinstance(session, dict) and session.get("cookie_issued") else "nicht erstellt"),
    ]
    rows = "\n".join(
        f"<li><span>{html.escape(name)}: {html.escape(value)}</span></li>"
        for name, value in items
    )
    return f"""
    <section>
      <h2>Technische Statusdiagnose</h2>
      <ul class="link-list">
        {rows}
      </ul>
    </section>
    """


def _log_auth_callback_redacted_status(callback_result: dict[str, Any], *, session_store_bound: bool) -> None:
    token_exchange = callback_result.get("token_exchange", {})
    jwt_validation = callback_result.get("jwt_validation", {})
    role_gate = callback_result.get("role_gate", {})
    session_boundary = callback_result.get("session_boundary", {})
    role_evidence = session_boundary.get("role_evidence", {}) if isinstance(session_boundary, dict) else {}
    session = session_boundary.get("session", {}) if isinstance(session_boundary, dict) else {}
    message = (
        "auth_callback_status state=%s token_exchange=%s token_exchange_class=%s "
        "token_exchange_detail=%s jwt_validation=%s role_gate=%s role_gate_reason=%s "
        "role_lookup_detail=%s session_cookie=%s session_store=%s"
    ) % (
        _safe_auth_log_status(callback_result.get("state_validation", {}).get("status")),
        _safe_auth_log_status(token_exchange.get("status") if isinstance(token_exchange, dict) else None),
        _safe_token_exchange_log_class(token_exchange),
        _safe_token_exchange_log_detail(token_exchange),
        _safe_auth_log_status(jwt_validation.get("status") if isinstance(jwt_validation, dict) else None),
        _safe_auth_log_status(role_gate.get("status") if isinstance(role_gate, dict) else None),
        _safe_role_gate_log_reason(role_gate),
        _safe_role_lookup_log_detail(role_evidence),
        _safe_auth_log_bool(isinstance(session, dict) and bool(session.get("cookie_issued"))),
        _safe_auth_log_bool(session_store_bound),
    )
    LOGGER.info("%s", message)
    print(message, flush=True)


def _safe_token_exchange_log_class(token_exchange: Any) -> str:
    if not isinstance(token_exchange, dict):
        return "unknown"
    if token_exchange.get("status") == "invalid":
        return "invalid_token"
    if token_exchange.get("status") == "failed":
        return "exchange_failed"
    return _safe_auth_log_status(token_exchange.get("status"))


def _safe_token_exchange_log_detail(token_exchange: Any) -> str:
    if not isinstance(token_exchange, dict):
        return "unknown"
    diagnostic_class = str(token_exchange.get("diagnostic_class") or "")
    if diagnostic_class in {"missing_id_token", "token_response_not_json", "id_token_verification_failed"}:
        return diagnostic_class
    failure_class = str(token_exchange.get("failure_class") or "")
    if failure_class in {
        "authorization_code_rejected",
        "client_auth_rejected",
        "client_not_authorized",
        "grant_type_unsupported",
        "token_endpoint_unavailable",
        "token_request_rejected",
        "token_endpoint_rejected",
    }:
        return failure_class
    return "none"


def _safe_auth_log_status(value: Any) -> str:
    status = str(value or "")
    if status in {
        "closed",
        "expired",
        "failed",
        "invalid",
        "missing",
        "not_configured",
        "not_started",
        "open",
        "received",
        "rejected",
        "session_allowed",
        "session_bound",
        "unavailable",
        "valid",
        "verified",
    }:
        return status
    return "unknown"


def _safe_auth_log_bool(value: bool) -> str:
    return "true" if value else "false"


def _safe_role_gate_log_reason(role_gate: Any) -> str:
    if not isinstance(role_gate, dict):
        return "unknown"
    reason = str(role_gate.get("reason") or "")
    if reason in {
        "audience_mismatch",
        "authorized",
        "issuer_mismatch",
        "nonce_mismatch",
        "nonce_not_bound",
        "role_missing",
        "server_membership_confirmed",
        "server_membership_missing",
        "server_membership_unavailable",
        "state_invalid",
    }:
        return reason
    return "unknown"


def _safe_role_lookup_log_detail(role_evidence: Any) -> str:
    if not isinstance(role_evidence, dict):
        return "none"
    failure_class = str(role_evidence.get("failure_class") or "")
    if failure_class in {
        "idp_lookup_client_error",
        "idp_lookup_forbidden",
        "idp_lookup_http_error",
        "idp_lookup_unavailable",
        "idp_lookup_network_error",
        "idp_lookup_server_error",
        "idp_lookup_timeout",
        "idp_lookup_unauthorized",
    }:
        return failure_class
    status = str(role_evidence.get("status") or "")
    if status in {"confirmed", "missing", "unavailable"}:
        return status
    return "none"


def _role_gate_status_label(role_gate: Any) -> str:
    if not isinstance(role_gate, dict):
        return _safe_status_label(None)
    if role_gate.get("status") == "closed" and role_gate.get("reason") in {
        "role_missing",
        "server_membership_missing",
        "server_membership_unavailable",
    }:
        return "Berechtigung offen"
    return _safe_status_label(role_gate.get("status"))


def _token_exchange_status_label(token_exchange: Any) -> str:
    if not isinstance(token_exchange, dict):
        return _safe_status_label(None)
    if token_exchange.get("status") == "invalid":
        return {
            "missing_id_token": "Anmeldung unvollständig",
            "token_response_not_json": "Anmeldung technisch nicht verfügbar",
            "id_token_verification_failed": "Token-Prüfung fehlgeschlagen",
        }.get(str(token_exchange.get("diagnostic_class") or ""), "Anmeldung nicht vollständig geprüft")
    if token_exchange.get("status") == "unavailable":
        return "Anmeldung vorübergehend nicht verfügbar"
    if token_exchange.get("status") != "failed":
        return _safe_status_label(token_exchange.get("status"))
    return {
        "authorization_code_rejected": "Anmeldung abgelaufen oder bereits verwendet",
        "client_auth_rejected": "Anmeldung technisch nicht verfügbar",
        "client_not_authorized": "Anmeldung technisch nicht verfügbar",
        "grant_type_unsupported": "Anmeldung technisch nicht verfügbar",
        "token_endpoint_unavailable": "Anmeldung vorübergehend nicht verfügbar",
        "token_request_rejected": "Anmeldung abgelehnt",
        "token_endpoint_rejected": "Anmeldung abgelehnt",
    }.get(str(token_exchange.get("failure_class") or ""), "fehlgeschlagen")


def _safe_status_label(value: Any) -> str:
    return {
        "closed": "geschlossen",
        "expired": "abgelaufen",
        "failed": "fehlgeschlagen",
        "invalid": "ungültig",
        "missing": "fehlt",
        "not_configured": "nicht konfiguriert",
        "not_started": "nicht gestartet",
        "open": "bestätigt",
        "received": "empfangen",
        "rejected": "abgelehnt",
        "session_allowed": "freigegeben",
        "session_bound": "vorbereitet",
        "unavailable": "nicht verfügbar",
        "valid": "bestätigt",
        "verified": "bestätigt",
    }.get(str(value or ""), "unbekannt")


def _request_header(headers: dict[str, str], name: str) -> str:
    expected = name.lower()
    for key, value in headers.items():
        if key.lower() == expected and isinstance(value, str):
            return value
    return ""


def _sanitize_request_log_text(value: str) -> str:
    marker = "/auth/callback?"
    if marker not in value:
        return value
    prefix, suffix = value.split(marker, 1)
    if " " not in suffix:
        return f"{prefix}/auth/callback?<redacted>"
    _query, rest = suffix.split(" ", 1)
    return f"{prefix}/auth/callback?<redacted> {rest}"


def _layout(title: str, body: str, head_extra: str = "") -> str:
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{_css()}</style>
{head_extra}
</head>
<body>
  <main>{body}</main>
</body>
</html>
"""


def _css() -> str:
    return """
    :root { color-scheme: light; --ink: #1f2328; --muted: #636c76; --line: #d8dee4; --bg: #f6f8fa; --panel: #fff; --accent: #2f6f88; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: var(--bg); }
    main { width: calc(100% - 32px); max-width: 1440px; margin: 0 auto; padding: 28px 0; }
    h1 { margin: 0 0 12px; font-size: 36px; line-height: 1.1; letter-spacing: 0; }
    h2 { margin: 0 0 16px; font-size: 22px; letter-spacing: 0; }
    p { color: var(--muted); line-height: 1.55; overflow-wrap: anywhere; }
    code { background: #eef2f5; border-radius: 4px; padding: 2px 5px; }
    .hero, section { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 22px; margin: 0 0 20px; }
    .eyebrow { margin: 0 0 8px; color: var(--accent); font-weight: 700; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
    .link-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
    .link-list li { border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fff; }
    .link-list a { display: block; color: #0b4f6c; font-weight: 700; text-decoration: none; margin-bottom: 4px; }
    .link-list .inline-link { display: inline; margin: 0; font-weight: 600; }
    .link-list span { color: var(--muted); font-size: 14px; }
    .topline { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin: 0 0 18px; }
    .topline span { display: flex; gap: 14px; flex-wrap: wrap; }
    .topline a { color: #0b4f6c; font-weight: 700; text-decoration: none; }
    .toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 0 0 14px; }
    button { appearance: none; border: 0; border-radius: 6px; background: #0b4f6c; color: #fff; font-weight: 700; padding: 10px 14px; cursor: pointer; }
    .button-link { display: inline-flex; align-items: center; min-height: 40px; border-radius: 6px; background: #0b4f6c; color: #fff; font-weight: 700; padding: 10px 14px; text-decoration: none; }
    button:disabled { opacity: .55; cursor: not-allowed; }
    #editor-status { color: var(--muted); font-size: 14px; }
    .bpmn-editor-shell { padding: 0; overflow: hidden; }
    .editor-commandbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 14px; border-bottom: 1px solid var(--line); background: #fff; }
    .command-group { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; padding-right: 10px; border-right: 1px solid var(--line); }
    .command-group:last-child { border-right: 0; }
    .command-group button { background: #254b68; padding: 9px 12px; }
    .command-group [data-create-kind] { background: #2f6b50; }
    .editor-statusbar { display: flex; justify-content: space-between; gap: 14px; align-items: center; padding: 10px 14px; border-bottom: 1px solid var(--line); background: #fbfcfd; }
    #dirty-state { font-size: 13px; color: var(--muted); font-weight: 700; }
    #dirty-state.is-dirty { color: #9a5b00; }
    .editor-workbench { display: grid; grid-template-columns: 250px minmax(520px, 1fr) 300px; min-height: 680px; }
    .editor-side-panel, .editor-properties-panel { border: 0; border-radius: 0; margin: 0; padding: 14px; background: #fbfcfd; overflow: auto; }
    .editor-side-panel { border-right: 1px solid var(--line); }
    .editor-properties-panel { border-left: 1px solid var(--line); }
    .editor-side-panel h2, .editor-properties-panel h2 { font-size: 16px; margin-bottom: 12px; }
    .step-list { display: grid; gap: 8px; }
    .step-button { width: 100%; background: #fff; color: var(--ink); border: 1px solid var(--line); text-align: left; padding: 10px; }
    .step-button span, .step-button small { display: block; }
    .step-button span { font-weight: 700; line-height: 1.25; }
    .step-button small { color: var(--muted); margin-top: 3px; }
    .step-button.is-selected { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); }
    .editor-canvas-region { min-width: 0; background: #fff; }
    .modeler-canvas { height: 68vh; min-height: 680px; border: 0; background: #fff; margin: 0; position: relative; overflow: hidden; }
    .modeler-canvas .djs-container { width: 100% !important; height: 100% !important; }
    .modeler-canvas .djs-palette { top: 16px; left: 16px; }
    .selected-element { min-height: 40px; border: 1px solid var(--line); border-radius: 6px; background: #fff; padding: 9px 10px; color: var(--muted); font-size: 13px; margin-bottom: 12px; overflow-wrap: anywhere; }
    #properties-form { display: grid; gap: 8px; }
    #properties-form label { font-weight: 700; font-size: 13px; }
    #properties-form input, #properties-form select { width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 8px 9px; font: inherit; background: #fff; }
    #properties-form input:disabled, #properties-form select:disabled { background: #eef2f5; color: var(--muted); }
    .check-label { display: flex; align-items: center; gap: 8px; margin: 2px 0 6px; }
    .check-label input { width: auto; }
    .xml-panel { border-top: 1px solid var(--line); padding: 14px; background: #fff; }
    .xml-panel.is-hidden { display: none; }
    .xml-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 8px; }
    .xml-label { display: block; font-weight: 700; margin: 0 0 8px; }
    textarea { width: 100%; min-height: 280px; resize: vertical; border: 1px solid var(--line); border-radius: 8px; padding: 12px; font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace; font-size: 13px; line-height: 1.45; }
    .canvas { overflow: hidden; padding: 8px; background: #fbfcfd; }
    .bpmn-diagram-panel { min-height: 220px; }
    .diagram-scroll { width: 100%; overflow-x: auto; overflow-y: hidden; padding: 6px 0 12px; }
    .bpmn-svg { width: auto; max-width: none; height: auto; display: block; }
    .flow { fill: none; stroke: #41516b; stroke-width: 2.2; }
    .flow-label { font-size: 13px; fill: #41516b; text-anchor: middle; font-weight: 700; }
    .node rect, .node circle, .node polygon { fill: #fff; stroke: #2f6f88; stroke-width: 2.2; }
    .node.serviceTask rect { fill: #edf7f4; stroke: #2f6b50; }
    .gateway polygon { fill: #fff8e8; stroke: #936e1d; }
    .end circle { stroke: #7b2d26; }
    .node-label { text-anchor: middle; dominant-baseline: middle; font-size: 14px; font-weight: 700; fill: var(--ink); }
    .node-badge { text-anchor: middle; font-size: 12px; fill: var(--muted); }
    .table-scroll { width: 100%; overflow-x: auto; }
    .table-scroll table { min-width: 980px; }
    .compact-table table { min-width: 0; }
    table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    th, td { text-align: left; border-bottom: 1px solid var(--line); padding: 10px 12px; vertical-align: top; overflow-wrap: anywhere; }
    th { background: #eef2f5; font-size: 13px; color: #424a53; }
    .notice { border-left: 4px solid var(--accent); }
    .quote-form { display: grid; grid-template-columns: repeat(5, minmax(130px, 1fr)); gap: 10px; align-items: end; }
    .quote-form label { display: grid; gap: 6px; font-weight: 700; font-size: 13px; }
    .quote-form input, .quote-form select { width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 9px 10px; font: inherit; background: #fff; }
    .quote-result { display: block; margin-top: 14px; padding: 12px; border: 1px solid var(--line); border-radius: 8px; background: #fbfcfd; color: var(--ink); overflow-wrap: anywhere; }
    .readiness-form { display: grid; gap: 10px; max-width: 560px; }
    .readiness-form label { display: grid; gap: 6px; font-weight: 700; font-size: 13px; }
    .readiness-form input { width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 9px 10px; font: inherit; background: #fff; }
    .cost-flow { list-style: none; counter-reset: step; display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: 0; padding: 0; }
    .cost-flow li { counter-increment: step; position: relative; border: 1px solid var(--line); border-radius: 8px; background: #fff; padding: 14px 14px 14px 48px; min-height: 86px; }
    .cost-flow li::before { content: counter(step); position: absolute; left: 14px; top: 14px; width: 24px; height: 24px; border-radius: 50%; background: var(--accent); color: #fff; display: grid; place-items: center; font-size: 13px; font-weight: 800; }
    .cost-flow strong, .cost-flow span { display: block; }
    .cost-flow strong { line-height: 1.25; }
    .cost-flow span { color: var(--muted); margin-top: 6px; font-size: 13px; }
    @media (max-width: 1040px) { .editor-workbench { grid-template-columns: 1fr; } .editor-side-panel, .editor-properties-panel { border: 0; border-bottom: 1px solid var(--line); } .modeler-canvas { min-height: 560px; } }
    @media (max-width: 900px) { .quote-form { grid-template-columns: repeat(2, minmax(0, 1fr)); } .quote-form button { grid-column: 1 / -1; } }
    @media (max-width: 760px) { .responsive-table { overflow: visible; } .responsive-table table, .responsive-table thead, .responsive-table tbody, .responsive-table tr, .responsive-table th, .responsive-table td { display: block; width: 100%; min-width: 0; } .responsive-table thead { display: none; } .responsive-table table { min-width: 0; border: 0; background: transparent; } .responsive-table tr { border: 1px solid var(--line); border-radius: 8px; background: #fff; margin: 0 0 10px; padding: 10px 12px; } .responsive-table td { display: grid; grid-template-columns: 116px minmax(0, 1fr); gap: 12px; border: 0; padding: 6px 0; } .responsive-table td::before { content: attr(data-label); color: #424a53; font-size: 13px; font-weight: 700; } }
    @media (max-width: 720px) { main { width: calc(100% - 24px); padding: 16px 0; } h1 { font-size: 28px; } .hero, section { padding: 16px; } .bpmn-editor-shell { padding: 0; } }
    """


def _html_response(
    text: str,
    status: HTTPStatus = HTTPStatus.OK,
    *,
    headers: dict[str, str] | None = None,
) -> AppResponse:
    return AppResponse(status, "text/html; charset=utf-8", text.encode("utf-8"), headers=headers)


def _json_response(payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> AppResponse:
    return _json_text_response(json.dumps(payload, ensure_ascii=False, indent=2), status)


def _json_text_response(text: str, status: HTTPStatus = HTTPStatus.OK) -> AppResponse:
    return AppResponse(status, "application/json; charset=utf-8", text.encode("utf-8"))


def _redirect_response(location: str) -> AppResponse:
    return AppResponse(
        HTTPStatus.SEE_OTHER,
        "text/html; charset=utf-8",
        b"",
        headers={"Location": location},
    )


def _safe_segment(value: str) -> str:
    segment = Path(value).name
    if not segment or segment in {".", ".."}:
        raise KeyError(value)
    return segment
