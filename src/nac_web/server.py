from __future__ import annotations

import html
import json
import os
import threading
import webbrowser
from decimal import Decimal
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlencode, urlparse

from nac_gnotkg.costs import quote_fee
from nac_identity.customer_onboarding import build_dns_check_result, build_live_dns_check_result
from nac_identity.onboarding_requests import (
    DisabledOnboardingRequestStore,
    OciVaultSecretTextProvider,
    OnboardingRequestStoreDisabled,
    OnboardingRequestStoreUnavailable,
    build_onboarding_request,
    build_onboarding_request_store_from_env,
)
from nac_identity.oci_callback import build_auth_callback_result
from nac_identity.oci_login import build_login_intent
from nac_identity.oidc_jwt import build_oidc_id_token_verifier
from nac_identity.oidc_session import DEFAULT_SESSION_TTL_SECONDS, validate_session_cookie
from nac_identity.oidc_token_exchange import exchange_oidc_authorization_code
from nac_identity.oidc_state import validate_signed_state
from nac_identity.oci_tenant import build_admin_provisioning_plan, build_apply_request, check_domain_ready
from nac_identity.role_case_gate import (
    evaluate_role_case_gate,
    normalize_workspace_case_binding_context,
    normalize_workspace_purpose_binding_context,
    normalize_workspace_role_gate_context,
    normalize_workspace_tenant_binding_context,
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

DEFAULT_OCI_IDENTITY_DOMAIN_URL = "https://idcs.example.identity.oraclecloud.com:443"
DEFAULT_OCI_IDENTITY_DOMAIN_ID = "ocid1.domain.oc1.example"
DEFAULT_OWNER_APPLY_APPROVAL_ID = "OWNER-APPLY-2026-0001"
DEFAULT_AUDIT_EVENT_ID = "AUDIT-2026-0001"
DEFAULT_ROLLBACK_PLAN_ID = "ROLLBACK-2026-0001"


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
        operator_access: bool = False,
        secret_text_provider: Callable[[str], str] | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.dns_resolver = dns_resolver
        self.onboarding_request_store = onboarding_request_store or DisabledOnboardingRequestStore()
        self.operator_access = operator_access
        self.secret_text_provider = secret_text_provider

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
                )
                return _html_response(page, status, headers=headers)
            if route == "/workspace":
                status, page = build_protected_workspace_start_page(
                    headers or {},
                    secret_text_provider=self.secret_text_provider,
                )
                return _html_response(page, status)
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

    def handle_post(self, path: str, body: bytes) -> tuple[int, str, bytes]:
        parsed = urlparse(path)
        route = unquote(parsed.path)
        try:
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
                identity_domain_url=config["identity_domain_url"],
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
            plan = build_admin_provisioning_plan(
                tenant_slug=_payload_text(payload, "tenant_slug"),
                domain=_payload_text(payload, "domain"),
                admin_email=_payload_text(payload, "admin_email"),
                admin_display_name=_payload_text(payload, "admin_display_name"),
                identity_domain_url=_payload_text(payload, "identity_domain_url"),
                identity_domain_id=_payload_text(payload, "identity_domain_id"),
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
                f'{html.escape(preview_query, quote=True)}">Admin-Dry-Run vorbereiten</a>'
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
          Mandatsdaten, Zugangsdaten oder OCI-Credentials.</p>
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
    app = NaCLocalWebApp(repo_root, onboarding_request_store=build_onboarding_request_store_from_env())

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
            self._send_app_response(app.handle_post(self.path, self.rfile.read(length)))

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
          <li><span>Rollen- und Vorgangsprüfung entscheiden erst nach erfolgreicher Anmeldung über Zugriff.</span></li>
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
) -> tuple[HTTPStatus, str, dict[str, str]]:
    params = parse_qs(query, keep_blank_values=True)
    provider_error = _optional_query_text(params, "error", max_length=120)
    code = _optional_query_text(params, "code", max_length=4096)
    state = _optional_query_text(params, "state", max_length=4096)
    state_validation = _auth_callback_state_validation(state, secret_text_provider=secret_text_provider)
    token_exchange_metadata = _auth_callback_token_exchange_metadata()
    callback_result = build_auth_callback_result(
        code=code,
        state=state,
        provider_error=provider_error,
        state_validation_configured=_auth_callback_state_validation_configured(),
        token_exchange_configured=_auth_callback_token_exchange_configured(),
        state_validation=state_validation,
        token_exchange_result=_auth_callback_token_exchange_result(
            code=code,
            state_validation=state_validation,
            secret_text_provider=secret_text_provider,
            **token_exchange_metadata,
        ),
        expected_issuer=_auth_callback_expected_issuer(),
        expected_audience=token_exchange_metadata["client_id"],
        session_signing_key=_auth_callback_session_signing_key(secret_text_provider=secret_text_provider),
        session_ttl_seconds=_auth_callback_session_ttl_seconds(),
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
            "Die Sitzung ist aufgebaut und das notariat8-Rollengate bestätigt. "
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
          <li><span>Sitzung prüfen und notariat8-Rollengate anwenden.</span></li>
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
        <h2>Rollen- und Vorgangsprüfung</h2>
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
) -> tuple[HTTPStatus, str]:
    signing_key = _auth_callback_session_signing_key(secret_text_provider=secret_text_provider)
    validation = validate_session_cookie(
        _request_header(request_headers, "Cookie"),
        signing_key=signing_key,
    )
    if validation["status"] != "valid":
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

    role_case_gate = evaluate_role_case_gate(
        session_validation=validation,
        role_gate=normalize_workspace_role_gate_context(
            role=_request_header(request_headers, "X-NaC-Role"),
            role_gate_open=_workspace_header_bool(request_headers, "X-NaC-Role-Gate-Open", default=True),
        ),
        tenant_context=normalize_workspace_tenant_binding_context(
            tenant_bound=_workspace_header_bool(request_headers, "X-NaC-Tenant-Bound"),
        ),
        case_context=normalize_workspace_case_binding_context(
            case_bound=_workspace_header_bool(request_headers, "X-NaC-Case-Bound"),
        ),
        purpose_context=normalize_workspace_purpose_binding_context(
            purpose_bound=_workspace_header_bool(request_headers, "X-NaC-Purpose-Bound"),
        ),
        subject_matter_roles=["nac-notary", "nac-case-worker", "nac-tenant-admin"],
    )
    if role_case_gate["status"] != "open":
        reason_label = {
            "role_missing": "Rolle fehlt",
            "tenant_mismatch": "Tenant-Bindung fehlt",
            "case_missing": "Vorgangsbindung fehlt",
            "purpose_missing": "Zweckbindung fehlt",
            "four_eyes_required": "Vier-Augen-Freigabe fehlt",
        }.get(str(role_case_gate.get("reason")), "Freigabe fehlt")
        body = f"""
        <nav class="topline"><a href="/login">← Anmeldung</a></nav>
        <section class="hero">
          <p class="eyebrow">notariat8 Start</p>
          <h1>Rollen- und Vorgangsprüfung offen</h1>
          <p>Ihre Sitzung wurde geprüft. Der geschützte Arbeitsbereich bleibt geschlossen,
          bis Rolle, Tenant, Vorgang und Zweck geprüft sind.</p>
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
        return HTTPStatus.FORBIDDEN, _layout("notariat8 Rollen- und Vorgangsprüfung offen", body)

    body = """
    <nav class="topline"><a href="/login">← Anmeldung</a></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Start</p>
      <h1>Geschützte Workspace-Metadaten</h1>
      <p>Ihre Sitzung und die fachliche Bindung wurden geprüft. notariat8 zeigt hier nur
      Status-Metadaten.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Rollen- und Vorgangsgate bestätigt</h2>
        <p><strong>Status-Metadaten freigegeben</strong></p>
        <ul class="link-list">
          <li><span>Rolle bestätigt.</span></li>
          <li><span>Tenant-Bindung bestätigt.</span></li>
          <li><span>Vorgangsbindung bestätigt.</span></li>
          <li><span>Zweckbindung bestätigt.</span></li>
        </ul>
      </section>
      <section>
        <h2>Nächster sicherer Schritt</h2>
        <ul class="link-list">
          <li><span>Vollständiger Arbeitsbereich noch geschlossen.</span></li>
          <li><span>Nur geprüfte Navigation und Statushinweise anzeigen.</span></li>
          <li><span>Keine Mandatsdaten geladen.</span></li>
        </ul>
      </section>
    </div>
    """
    return HTTPStatus.OK, _layout("notariat8 Start", body)


def _workspace_header_bool(headers: dict[str, str], name: str, *, default: bool = False) -> bool:
    value = _request_header(headers, name)
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
        "approved": "Freigabe ist dokumentiert; Einladung bleibt bis zum nächsten Gate offen",
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
    body = f"""
    {nav}
    <section class="hero">
      <p class="eyebrow">notariat8 Einrichtung</p>
      <h1>Einrichtung angefragt</h1>
      <p>Ihre Anfrage ist bei notariat8 eingegangen. Wir prüfen jetzt die angegebene E-Mail-Adresse
      und bereiten die nächsten Schritte vor.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Ihre Angaben</h2>
        <p><strong>Domain:</strong> {html.escape(str(request.get("domain", "")))}</p>
        <p><strong>E-Mail-Adresse:</strong> {html.escape(str(request.get("admin_email", "")))}</p>
        <p><strong>Status:</strong> Anfrage eingegangen</p>
        <p><strong>Einladung:</strong> Einladung noch nicht versendet</p>
        <div class="toolbar">
          <a class="button-link" href="/onboarding/readiness?{html.escape(readiness_query, quote=True)}">Einrichtungsstatus öffnen</a>
        </div>
      </section>
      <section>
        <h2>Was passiert als Nächstes?</h2>
        <ul class="link-list">
          <li><span><strong>Prüfung:</strong> notariat8 prüft die E-Mail-Adresse der verantwortlichen Person.</span></li>
          <li><span><strong>Freigabe:</strong> Nach der Prüfung wird die erste Einrichtung vorbereitet.</span></li>
          <li><span><strong>Nachweis:</strong> Die Referenz dieser Anfrage lautet <code>{html.escape(str(request.get("request_id", "")))}</code>.</span></li>
          <li><span><strong>Keine Mandatsdaten:</strong> Diese Anfrage enthält keine Urkunden, Ausweise, Akten oder Geschäftswerte.</span></li>
        </ul>
      </section>
    </div>
    """
    return _layout("notariat8 Einrichtung angefragt", body)


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
            f'{html.escape(preview_query, quote=True)}">Admin-Dry-Run vorbereiten</a>'
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
    plan = build_admin_provisioning_plan(
        tenant_slug=tenant_slug,
        domain=domain,
        admin_email=admin_email,
        admin_display_name=_optional_query_text(params, "admin_display_name", max_length=120) or "Admin Notariat",
        identity_domain_url=DEFAULT_OCI_IDENTITY_DOMAIN_URL,
        identity_domain_id=DEFAULT_OCI_IDENTITY_DOMAIN_ID,
    )
    planned_write_items = "".join(
        f"<li><span>{html.escape(write)}</span></li>" for write in plan["planned_writes"]
    )
    group_items = "".join(f"<li><span>{html.escape(group)}</span></li>" for group in plan["groups"])
    binding_rows = "".join(
        "<tr>"
        f'<td data-label="Gruppe">{html.escape(binding["group"])}</td>'
        f'<td data-label="Mitglied">{html.escape(binding["member"])}</td>'
        f'<td data-label="Zweck">{html.escape(binding["purpose"])}</td>'
        "</tr>"
        for binding in plan["role_bindings"]
    )
    apply_query = urlencode(
        {
            "domain": plan["domain"],
            "tenant_slug": plan["tenant_slug"],
            "admin_email": plan["admin_user"]["primary_email"],
        }
    )
    body = f"""
    <nav class="topline"><a href="/onboarding/readiness?{html.escape(urlencode({"domain_hint": plan["domain"], "tenant_slug": plan["tenant_slug"], "admin_email": plan["admin_user"]["primary_email"]}), quote=True)}">← Readiness</a><span><a href="/admin/onboarding">Admin-Queue</a></span></nav>
    <section class="hero">
      <p class="eyebrow">OCI Identity Preview</p>
      <h1>OCI-Admin-Dry-Run</h1>
      <p>Lokale Vorschau für die initiale Tenant-Admin-Einladung. Diese Seite schreibt nicht nach OCI
      und enthält keine Zugangsdaten.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Tenant</h2>
        <p><strong>Domain:</strong> {html.escape(plan["domain"])}</p>
        <p><strong>Tenant-Slug:</strong> {html.escape(plan["tenant_slug"])}</p>
        <p><strong>Modus:</strong> <code>{html.escape(plan["mode"])}</code></p>
        <p><strong>Approval-Gate:</strong> <code>{html.escape(plan["approval_gate"])}</code></p>
        <div class="toolbar">
          <a class="button-link" href="/admin/onboarding/apply-readiness?{html.escape(apply_query, quote=True)}">Apply-Readiness vorbereiten</a>
        </div>
      </section>
      <section>
        <h2>Initialer Admin</h2>
        <p><strong>E-Mail:</strong> {html.escape(plan["admin_user"]["primary_email"])}</p>
        <p><strong>Anzeigename:</strong> {html.escape(plan["admin_user"]["display_name"])}</p>
        <p><strong>OCI Console für Endnutzer:</strong> nein</p>
      </section>
    </div>
    <div class="grid">
      <section>
        <h2>Geplante Writes</h2>
        <ul class="link-list">{planned_write_items}</ul>
      </section>
      <section>
        <h2>Gruppen</h2>
        <ul class="link-list">{group_items}</ul>
      </section>
    </div>
    <section>
      <h2>Rollenbindung</h2>
      <div class="table-scroll responsive-table">
        <table>
          <thead><tr><th>Gruppe</th><th>Mitglied</th><th>Zweck</th></tr></thead>
          <tbody>{binding_rows}</tbody>
        </table>
      </div>
    </section>
    <section>
      <h2>Guardrails</h2>
      <ul class="link-list">
        <li><span>Produktive Identity-Writes bleiben bis Owner-Apply-Freigabe gesperrt.</span></li>
        <li><span>DNS-Verifikation, Audit-Event und Rollback-Plan bleiben Pflicht-Gates.</span></li>
        <li><span>Client-Zugangsdaten, API Keys und Token werden nicht erfasst.</span></li>
      </ul>
    </section>
    """
    return _layout("NaC OCI-Admin-Dry-Run", body)


def build_admin_apply_readiness_page(query: str) -> str:
    params = parse_qs(query, keep_blank_values=True)
    domain = _query_text(params, "domain")
    tenant_slug = _query_text(params, "tenant_slug")
    admin_email = _query_text(params, "admin_email")
    plan = build_admin_provisioning_plan(
        tenant_slug=tenant_slug,
        domain=domain,
        admin_email=admin_email,
        admin_display_name=_optional_query_text(params, "admin_display_name", max_length=120) or "Admin Notariat",
        identity_domain_url=DEFAULT_OCI_IDENTITY_DOMAIN_URL,
        identity_domain_id=DEFAULT_OCI_IDENTITY_DOMAIN_ID,
    )
    apply_request = build_apply_request(
        plan,
        dns_verified=_optional_query_bool(params, "dns_verified", default=True),
        owner_approval_id=(
            _optional_query_text(params, "owner_approval_id", max_length=120) or DEFAULT_OWNER_APPLY_APPROVAL_ID
        ),
        audit_event_id=_optional_query_text(params, "audit_event_id", max_length=120) or DEFAULT_AUDIT_EVENT_ID,
        rollback_plan_id=(
            _optional_query_text(params, "rollback_plan_id", max_length=120) or DEFAULT_ROLLBACK_PLAN_ID
        ),
    )
    readiness_query = urlencode(
        {
            "domain_hint": apply_request["domain"],
            "tenant_slug": apply_request["tenant_slug"],
            "admin_email": apply_request["admin_user"]["primary_email"],
        }
    )
    preview_query = urlencode(
        {
            "domain": apply_request["domain"],
            "tenant_slug": apply_request["tenant_slug"],
            "admin_email": apply_request["admin_user"]["primary_email"],
        }
    )
    gate_rows = "".join(
        "<tr>"
        f'<td data-label="Gate"><code>{html.escape(gate)}</code></td>'
        f'<td data-label="Status">{html.escape("erfüllt" if bool(value) else "fehlt")}</td>'
        "</tr>"
        for gate, value in apply_request["gates"].items()
    )
    guardrail_rows = "".join(
        "<tr>"
        f'<td data-label="Guardrail"><code>{html.escape(guardrail)}</code></td>'
        f'<td data-label="Wert">{html.escape(str(value).lower())}</td>'
        "</tr>"
        for guardrail, value in apply_request["guardrails"].items()
    )
    planned_write_items = "".join(
        f"<li><span>{html.escape(write)}</span></li>" for write in apply_request["planned_writes"]
    )
    finding_items = "".join(
        f"<li><span>{html.escape(finding)}</span></li>" for finding in apply_request["blocking_findings"]
    ) or "<li><span>keine Blocker</span></li>"
    binding_rows = "".join(
        "<tr>"
        f'<td data-label="Gruppe">{html.escape(str(binding.get("group", "")))}</td>'
        f'<td data-label="Mitglied">{html.escape(str(binding.get("member", "")))}</td>'
        f'<td data-label="Zweck">{html.escape(str(binding.get("purpose", "")))}</td>'
        "</tr>"
        for binding in apply_request["role_bindings"]
        if isinstance(binding, dict)
    )
    body = f"""
    <nav class="topline"><a href="/admin/onboarding/provisioning-preview?{html.escape(preview_query, quote=True)}">← Admin-Dry-Run</a><span><a href="/onboarding/readiness?{html.escape(readiness_query, quote=True)}">Readiness</a><a href="/admin/onboarding">Admin-Queue</a></span></nav>
    <section class="hero">
      <p class="eyebrow">Owner Apply Review</p>
      <h1>Apply-Readiness</h1>
      <p>Lokales Review-Artefakt für den späteren OCI-Connector-Apply. Diese Seite dokumentiert Gates,
      schreibt nicht nach OCI und enthält keine Zugangsdaten.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Review-Artefakt</h2>
        <p><strong>Schema:</strong> <code>{html.escape(apply_request["schema_version"])}</code></p>
        <p><strong>Modus:</strong> <code>{html.escape(apply_request["mode"])}</code></p>
        <p><strong>Status-Feld:</strong> <code>ready_to_apply</code></p>
        <p><strong>Status:</strong> {html.escape("bereit" if apply_request["ready_to_apply"] else "blockiert")}</p>
        <p><strong>Nächster Schritt:</strong> <code>{html.escape(apply_request["next_step"])}</code></p>
      </section>
      <section>
        <h2>Tenant</h2>
        <p><strong>Domain:</strong> {html.escape(apply_request["domain"])}</p>
        <p><strong>Tenant-Slug:</strong> {html.escape(apply_request["tenant_slug"])}</p>
        <p><strong>Admin:</strong> {html.escape(apply_request["admin_user"]["primary_email"])}</p>
        <p><strong>Quelle:</strong> <code>{html.escape(apply_request["source_plan"]["mode"])}</code></p>
      </section>
    </div>
    <div class="grid">
      <section>
        <h2>Apply-Gates</h2>
        <div class="table-scroll responsive-table compact-table">
          <table>
            <thead><tr><th>Gate</th><th>Status</th></tr></thead>
            <tbody>{gate_rows}</tbody>
          </table>
        </div>
      </section>
      <section>
        <h2>Freigabe-Nachweise</h2>
        <p><strong>Owner:</strong> <code>{html.escape(apply_request["approval"]["owner_approval_id"])}</code></p>
        <p><strong>Audit:</strong> <code>{html.escape(apply_request["audit"]["audit_event_id"])}</code></p>
        <p><strong>Rollback:</strong> <code>{html.escape(apply_request["rollback"]["rollback_plan_id"])}</code></p>
      </section>
    </div>
    <div class="grid">
      <section>
        <h2>Guardrails</h2>
        <div class="table-scroll responsive-table compact-table">
          <table>
            <thead><tr><th>Guardrail</th><th>Wert</th></tr></thead>
            <tbody>{guardrail_rows}<tr><td data-label="Guardrail"><code>productive_write_executed</code></td><td data-label="Wert">{html.escape(str(apply_request["productive_write_executed"]).lower())}</td></tr></tbody>
          </table>
        </div>
      </section>
      <section>
        <h2>Blocker</h2>
        <ul class="link-list">{finding_items}</ul>
      </section>
    </div>
    <div class="grid">
      <section>
        <h2>Geplante Writes</h2>
        <ul class="link-list">{planned_write_items}</ul>
      </section>
      <section>
        <h2>Rollenbindung</h2>
        <div class="table-scroll responsive-table">
          <table>
            <thead><tr><th>Gruppe</th><th>Mitglied</th><th>Zweck</th></tr></thead>
            <tbody>{binding_rows}</tbody>
          </table>
        </div>
      </section>
    </div>
    """
    return _layout("NaC Apply-Readiness", body)


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
        "identity_domain_url",
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
        "identity_domain_url": os.environ.get("NAC_OCI_IDENTITY_DOMAIN_URL", "").strip(),
        "client_id": os.environ.get("NAC_OIDC_CLIENT_ID", "").strip(),
        "redirect_uri": os.environ.get("NAC_OIDC_REDIRECT_URI", "").strip(),
        "state_signing_key": _oidc_state_signing_key_from_env(secret_text_provider=secret_text_provider),
    }
    if not all(config[field] for field in ("identity_domain_url", "client_id", "redirect_uri")):
        raise ValueError("login_intent_config_missing")
    return config


def _auth_callback_state_validation_configured() -> bool:
    return bool(
        os.environ.get("NAC_OIDC_STATE_SIGNING_KEY", "").strip()
        or os.environ.get("NAC_OIDC_STATE_SIGNING_KEY_SECRET_OCID", "").strip()
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
    secret_id = os.environ.get("NAC_OIDC_STATE_SIGNING_KEY_SECRET_OCID", "").strip()
    if not secret_id:
        return ""
    provider = secret_text_provider or OciVaultSecretTextProvider(secret_id)
    try:
        signing_key = provider(secret_id).strip()
    except Exception as exc:  # pragma: no cover - concrete OCI SDK errors are integration concerns
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
    secret_ref = os.environ.get("NAC_OIDC_CLIENT_SECRET_REF", "").strip()
    if not secret_ref:
        return ""
    provider = secret_text_provider or OciVaultSecretTextProvider(secret_ref)
    try:
        client_secret = provider(secret_ref).strip()
    except Exception as exc:  # pragma: no cover - concrete OCI SDK errors are integration concerns
        raise ValueError("oidc_client_secret_unavailable") from exc
    if not client_secret:
        raise ValueError("oidc_client_secret_unavailable")
    return client_secret


def _auth_callback_id_token_verifier() -> Callable[[str], dict[str, Any] | None] | None:
    issuer = _auth_callback_expected_issuer()
    audience = os.environ.get("NAC_OIDC_CLIENT_ID", "").strip()
    return build_oidc_id_token_verifier(issuer=issuer, audience=audience)


def _auth_callback_token_exchange_metadata() -> dict[str, str]:
    identity_domain_url = os.environ.get("NAC_OCI_IDENTITY_DOMAIN_URL", "").strip().rstrip("/")
    return {
        "redirect_uri": os.environ.get("NAC_OIDC_REDIRECT_URI", "").strip(),
        "token_endpoint": f"{identity_domain_url}/oauth2/v1/token" if identity_domain_url else "",
        "client_id": os.environ.get("NAC_OIDC_CLIENT_ID", "").strip(),
    }


def _auth_callback_expected_issuer() -> str:
    return os.environ.get("NAC_OCI_IDENTITY_DOMAIN_URL", "").strip().rstrip("/")


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
    provider = secret_text_provider or OciVaultSecretTextProvider(secret_ref)
    try:
        return provider(secret_ref).strip()
    except Exception:
        return ""


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


def _auth_callback_diagnostics_html(callback_result: dict[str, Any]) -> str:
    session_boundary = callback_result.get("session_boundary", {})
    token_exchange = callback_result.get("token_exchange", {})
    jwt_validation = callback_result.get("jwt_validation", {})
    role_gate = callback_result.get("role_gate", {})
    session = session_boundary.get("session", {}) if isinstance(session_boundary, dict) else {}
    items = [
        ("Token-Austausch", _safe_status_label(token_exchange.get("status"))),
        ("Token-Prüfung", _safe_status_label(jwt_validation.get("status"))),
        ("Rollenprüfung", _safe_status_label(role_gate.get("status"))),
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
