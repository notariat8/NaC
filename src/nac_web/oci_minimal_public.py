from __future__ import annotations

import base64
import html
import io
import json
import logging
import os
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlencode, urlparse

from nac_identity.customer_onboarding import build_dns_check_result, build_live_dns_check_result
from nac_identity.oci_login import build_login_intent
from nac_identity.oci_tenant import check_domain_ready


PUBLIC_GET_ROUTES = {
    "/",
    "/healthz",
    "/login",
    "/api/tenant/login-intent",
    "/onboarding/readiness",
    "/onboarding/dns-check",
}


@dataclass(frozen=True)
class PublicHttpResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes


def dispatch_minimal_public_get_request(
    ctx: Any,
    data: io.BytesIO | None = None,
    *,
    repo_root: Path | None = None,
    dns_resolver: Callable[[str], dict[str, Any]] | None = None,
    secret_text_provider: Callable[[str], str] | None = None,
) -> PublicHttpResponse:
    del data, repo_root
    _suppress_provider_sdk_debug_logs()
    request_url = _request_url(ctx)
    method = _request_method(ctx).upper()
    parsed = urlparse(request_url)
    route = unquote(parsed.path) or "/"

    if method not in {"GET", "HEAD"}:
        return _json_response(
            {"error": "OCI Functions public runtime is read-only in this release slice."},
            HTTPStatus.METHOD_NOT_ALLOWED,
        )
    if route not in PUBLIC_GET_ROUTES:
        return _json_response(
            {"error": "Route is not exposed by the OCI Functions public runtime."},
            HTTPStatus.NOT_FOUND,
        )

    try:
        response = _dispatch_get_route(
            route,
            parsed.query,
            dns_resolver=dns_resolver,
            secret_text_provider=secret_text_provider,
        )
    except ValueError as exc:
        response = _json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    if method == "HEAD":
        return PublicHttpResponse(response.status_code, response.headers, b"")
    return response


def _dispatch_get_route(
    route: str,
    query: str,
    *,
    dns_resolver: Callable[[str], dict[str, Any]] | None,
    secret_text_provider: Callable[[str], str] | None,
) -> PublicHttpResponse:
    if route == "/healthz":
        return _json_response({"status": "ok"})
    if route == "/api/tenant/login-intent":
        return _tenant_login_intent_response(query, secret_text_provider=secret_text_provider)
    if route == "/onboarding/readiness":
        return _html_response(_customer_readiness_page(query, dns_resolver=dns_resolver))
    if route == "/onboarding/dns-check":
        return _html_response(_customer_dns_check_page(query, dns_resolver=dns_resolver))
    return _html_response(_login_page(query))


def _tenant_login_intent_response(
    query: str,
    *,
    secret_text_provider: Callable[[str], str] | None,
) -> PublicHttpResponse:
    params = parse_qs(query, keep_blank_values=True)
    _reject_caller_supplied_login_config(params)
    payload = build_login_intent(
        tenant_hint=_optional_query_text(params, "tenant_hint", max_length=120),
        identity_domain_url=_required_env("NAC_OCI_IDENTITY_DOMAIN_URL"),
        client_id=_required_env("NAC_OIDC_CLIENT_ID"),
        redirect_uri=_required_env("NAC_OIDC_REDIRECT_URI"),
        state_signing_key=_state_signing_key_from_env(secret_text_provider=secret_text_provider) or None,
    )
    return _json_response(payload)


def _customer_readiness_page(
    query: str,
    *,
    dns_resolver: Callable[[str], dict[str, Any]] | None,
) -> str:
    params = parse_qs(query, keep_blank_values=True)
    domain_hint = _optional_query_text(params, "domain_hint", max_length=120) or "kanzlei-notariat.example"
    tenant_slug = _optional_query_text(params, "tenant_slug", max_length=80) or _tenant_slug_from_domain_hint(domain_hint)
    admin_email = _optional_query_text(params, "admin_email", max_length=160)
    readiness = check_domain_ready(domain=domain_hint, tenant_slug=tenant_slug, admin_email=admin_email)
    verification = readiness["verification"]
    dns_check = (
        build_live_dns_check_result(
            expected_name=verification["dns_record_name"],
            expected_value=verification["dns_record_value"],
            resolver=dns_resolver,
        )
        if admin_email
        else build_dns_check_result(
            expected_name=verification["dns_record_name"],
            expected_value=verification["dns_record_value"],
            observed_values=[],
            resolver_error="not_found",
        )
    )
    check_query = urlencode(
        _present_query_values(
            {
                "audience": "customer",
                "domain": readiness["domain"],
                "tenant_slug": readiness["tenant_slug"],
                "admin_email": readiness["admin_email"],
            }
        )
    )
    resume_query = urlencode(
        _present_query_values(
            {
                "audience": "customer",
                "domain_hint": readiness["domain"],
                "tenant_slug": readiness["tenant_slug"],
                "admin_email": readiness["admin_email"],
            }
        )
    )
    email_line = (
        f'<p><strong>E-Mail-Adresse der verantwortlichen Person:</strong> {html.escape(readiness["admin_email"])}</p>'
        if admin_email
        else "<p><strong>E-Mail-Adresse der verantwortlichen Person:</strong> noch nicht angegeben</p>"
    )
    email_form = ""
    if not admin_email:
        email_form = f"""
        <section class="notice">
          <h2>E-Mail-Adresse angeben</h2>
          <p>Tragen Sie die E-Mail-Adresse der Person ein, die die Einrichtung für Ihr Notariat starten soll.
          notariat8 leitet diese Adresse nicht aus der Domain ab.</p>
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
    dns_action = (
        f'<a class="button-link" href="/onboarding/dns-check?{html.escape(check_query, quote=True)}">DNS jetzt prüfen</a>'
        if admin_email
        else "<p>Die DNS-Prüfung startet erst nach Angabe der E-Mail-Adresse.</p>"
    )
    status_label = "E-Mail offen" if not admin_email else "bereit" if readiness["ready"] else "blockiert"
    dns_status_label, dns_guidance = _customer_dns_check_copy(dns_check)
    guidance_items = (
        """
        <li><span>Geben Sie zuerst die E-Mail-Adresse der verantwortlichen Person ein; notariat8 nimmt dafür keine Standardadresse an.</span></li>
        <li><span>Danach tragen Sie den DNS-TXT-Eintrag bei Ihrem DNS-Anbieter ein oder geben ihn an Ihre IT weiter.</span></li>
        <li><span>Nach erfolgreicher DNS-Prüfung bereitet notariat8 die Einladung vor.</span></li>
        <li><span>Keine Mandatsdaten: Diese Seite sammelt keine Urkunden, Ausweise, Akten oder Geschäftswerte.</span></li>
        """
        if not admin_email
        else """
        <li><span>Tragen Sie den DNS-TXT-Eintrag bei Ihrem DNS-Anbieter ein oder geben Sie ihn an Ihre IT weiter.</span></li>
        <li><span>Nach erfolgreicher DNS-Prüfung bereitet notariat8 die Einladung vor.</span></li>
        <li><span>Keine Mandatsdaten: Diese Seite sammelt keine Urkunden, Ausweise, Akten oder Geschäftswerte.</span></li>
        """
    )
    body = f"""
    {_customer_onboarding_nav(resume_query)}
    <section class="hero">
      <p class="eyebrow">notariat8 Neukunden-Onboarding</p>
      <h1>Domain vorbereiten</h1>
      <p>Prüfen Sie hier, ob Ihre Domain für notariat8 vorbereitet ist. Diese Seite verwendet nur Domain,
      E-Mail-Adresse und DNS-TXT-Eintrag. Keine Mandatsdaten und keine Vorgangsdokumente.</p>
    </section>
    <div class="grid">
      <section class="notice">
        <h2>Ihre Domain</h2>
        <p><strong>Domain:</strong> {html.escape(readiness["domain"])}</p>
        <p><strong>notariat8-Referenz:</strong> {html.escape(readiness["tenant_slug"])}</p>
        {email_line}
        <p><strong>Status:</strong> {html.escape(status_label)}</p>
      </section>
      {email_form}
      <section>
        <h2>DNS-TXT</h2>
        <p><strong>Name:</strong> <code>{html.escape(verification["dns_record_name"])}</code></p>
        <p><strong>Wert:</strong> <code>{html.escape(verification["dns_record_value"])}</code></p>
        <div class="toolbar">
          {dns_action}
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
    return _layout("notariat8 Domain vorbereiten", body)


def _customer_dns_check_page(
    query: str,
    *,
    dns_resolver: Callable[[str], dict[str, Any]] | None,
) -> str:
    params = parse_qs(query, keep_blank_values=True)
    readiness = check_domain_ready(
        domain=_query_text(params, "domain"),
        tenant_slug=_query_text(params, "tenant_slug"),
        admin_email=_query_text(params, "admin_email"),
    )
    verification = readiness["verification"]
    result = build_live_dns_check_result(
        expected_name=verification["dns_record_name"],
        expected_value=verification["dns_record_value"],
        resolver=dns_resolver,
    )
    readiness_query = urlencode(
        {
            "audience": "customer",
            "domain_hint": readiness["domain"],
            "tenant_slug": readiness["tenant_slug"],
            "admin_email": readiness["admin_email"],
        }
    )
    dns_query = urlencode(
        {
            "audience": "customer",
            "domain": readiness["domain"],
            "tenant_slug": readiness["tenant_slug"],
            "admin_email": readiness["admin_email"],
        }
    )
    confirmed = result["status"] == "verified"
    headline = "Domain bestätigt" if confirmed else "DNS noch nicht bestätigt"
    status_label = "bestätigt" if confirmed else "ausstehend"
    guidance = (
        "Ihre Domain ist bestätigt. notariat8 prüft jetzt die angegebene E-Mail-Adresse für die erste Einrichtung."
        if confirmed
        else "Der DNS-TXT-Eintrag wurde noch nicht gefunden. Prüfen Sie den Eintrag bei Ihrem DNS-Anbieter und versuchen Sie es später erneut."
    )
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
    {_customer_onboarding_nav(readiness_query)}
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
        <p><strong>Einladung:</strong> Einladung noch nicht versendet</p>
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


def _login_page(query: str) -> str:
    params = parse_qs(query, keep_blank_values=True)
    tenant_hint = _optional_query_text(params, "tenant_hint", max_length=120)
    intent_query = urlencode(_present_query_values({"tenant_hint": tenant_hint}))
    intent_href = "/api/tenant/login-intent" + (f"?{intent_query}" if intent_query else "")
    body = f"""
    <nav class="topline"><a href="https://www.notariat8.de/">← notariat8.de</a></nav>
    <section class="hero">
      <p class="eyebrow">notariat8 Anmeldung</p>
      <h1>Anmeldung vorbereiten</h1>
      <p>notariat8 erstellt im nächsten Schritt die sichere Anmeldung für Ihr Notariat.</p>
      <div class="toolbar">
        <a class="button-link" href="{html.escape(intent_href, quote=True)}">Anmeldung starten</a>
      </div>
    </section>
    """
    return _layout("notariat8 Anmeldung", body)


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


def _state_signing_key_from_env(
    *,
    secret_text_provider: Callable[[str], str] | None,
) -> str:
    inline_key = os.environ.get("NAC_OIDC_STATE_SIGNING_KEY", "").strip()
    if inline_key:
        return inline_key
    secret_id = os.environ.get("NAC_OIDC_STATE_SIGNING_KEY_SECRET_OCID", "").strip()
    if not secret_id:
        return ""
    provider = secret_text_provider or _read_oci_secret_text
    try:
        signing_key = provider(secret_id).strip()
    except Exception as exc:  # pragma: no cover - OCI SDK errors are integration concerns.
        raise ValueError("state_signing_key_unavailable") from exc
    if not signing_key:
        raise ValueError("state_signing_key_unavailable")
    return signing_key


def _read_oci_secret_text(secret_id: str) -> str:
    import oci

    signer = oci.auth.signers.get_resource_principals_signer()
    client = oci.secrets.SecretsClient(config={}, signer=signer)
    bundle = client.get_secret_bundle(secret_id).data
    encoded = bundle.secret_bundle_content.content
    return base64.b64decode(encoded).decode("utf-8")


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError("login_intent_config_missing")
    return value


def _query_text(params: dict[str, list[str]], key: str) -> str:
    value = _optional_query_text(params, key)
    if value:
        return value
    raise ValueError(f"{key} fehlt")


def _optional_query_text(params: dict[str, list[str]], key: str, *, max_length: int | None = None) -> str:
    values = params.get(key) or []
    value = values[0].strip() if values else ""
    if max_length is not None:
        return value[:max_length]
    return value


def _present_query_values(values: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in values.items() if value}


def _tenant_slug_from_domain_hint(domain_hint: str) -> str:
    normalized = domain_hint.strip().lower().rstrip(".")
    label = normalized.split(".", 1)[0]
    return "".join(character if character.isalnum() else "-" for character in label).strip("-") or "neukunde"


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


def _customer_onboarding_nav(readiness_query: str) -> str:
    escaped_query = html.escape(readiness_query, quote=True)
    return (
        '<nav class="topline">'
        '<a href="https://www.notariat8.de/">← notariat8.de</a>'
        f'<span><a href="/onboarding/readiness?{escaped_query}">Einrichtungsstatus</a></span>'
        "</nav>"
    )


def _html_response(text: str, status: HTTPStatus = HTTPStatus.OK) -> PublicHttpResponse:
    return PublicHttpResponse(
        status_code=int(status),
        headers=_headers("text/html; charset=utf-8"),
        body=text.encode("utf-8"),
    )


def _json_response(payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> PublicHttpResponse:
    return PublicHttpResponse(
        status_code=int(status),
        headers=_headers("application/json; charset=utf-8"),
        body=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
    )


def _headers(content_type: str) -> dict[str, str]:
    return {
        "Content-Type": content_type,
        "X-Content-Type-Options": "nosniff",
    }


def _request_method(ctx: Any) -> str:
    method = _call_context_method(ctx, "Method")
    if method:
        return str(method)
    headers = _context_headers(ctx)
    return headers.get("fn-http-method") or headers.get("Fn-Http-Method") or "GET"


def _request_url(ctx: Any) -> str:
    request_url = _call_context_method(ctx, "RequestURL")
    if request_url:
        return str(request_url)
    headers = _context_headers(ctx)
    return headers.get("fn-http-request-url") or headers.get("Fn-Http-Request-Url") or "/"


def _context_headers(ctx: Any) -> dict[str, str]:
    raw_headers = _call_context_method(ctx, "Headers")
    if not isinstance(raw_headers, dict):
        return {}
    return {str(key): str(value) for key, value in raw_headers.items()}


def _call_context_method(ctx: Any, name: str) -> Any:
    candidate = getattr(ctx, name, None)
    if callable(candidate):
        return candidate()
    return None


def _layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{_css()}</style>
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
    .link-list span { color: var(--muted); font-size: 14px; }
    .topline { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin: 0 0 18px; }
    .topline span { display: flex; gap: 14px; flex-wrap: wrap; }
    .topline a { color: #0b4f6c; font-weight: 700; text-decoration: none; }
    .toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 0 0 14px; }
    button { appearance: none; border: 0; border-radius: 6px; background: #0b4f6c; color: #fff; font-weight: 700; padding: 10px 14px; cursor: pointer; }
    .button-link { display: inline-flex; align-items: center; min-height: 40px; border-radius: 6px; background: #0b4f6c; color: #fff; font-weight: 700; padding: 10px 14px; text-decoration: none; }
    .inline-link { color: #0b4f6c; font-weight: 700; }
    .notice { border-left: 4px solid var(--accent); }
    .readiness-form { display: grid; gap: 10px; max-width: 560px; }
    .readiness-form label { display: grid; gap: 6px; font-weight: 700; font-size: 13px; }
    .readiness-form input { width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 9px 10px; font: inherit; background: #fff; }
    @media (max-width: 720px) { main { width: calc(100% - 24px); padding: 16px 0; } h1 { font-size: 28px; } .hero, section { padding: 16px; } }
    """


def _suppress_provider_sdk_debug_logs() -> None:
    for logger_name in ("oci", "oci.circuit_breaker", "urllib3", "urllib3.connectionpool"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
