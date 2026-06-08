from __future__ import annotations

import http.client
import json
import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_web.bpmn import find_bpmn_model, list_bpmn_models, render_bpmn_svg  # noqa: E402
import nac_web.server as nac_server  # noqa: E402
from nac_web.server import NaCLocalWebApp, build_bpmn_editor_page, build_bpmn_page, build_cost_page, build_home_page, build_kg_page  # noqa: E402
from nac_gnotkg.views import build_cost_review_view  # noqa: E402
from notary_kg.editor import build_editor_view  # noqa: E402


class NaCLocalWebTests(unittest.TestCase):
    def test_home_page_links_bpmn_and_kg_views(self) -> None:
        html = build_home_page(REPO_ROOT)

        self.assertIn("/bpmn/immobilienkaufvertrag", html)
        self.assertIn("/bpmn/handelsregisteranmeldung", html)
        self.assertIn("/bpmn/handelsregisteranmeldung/edit", html)
        self.assertIn("/kg/immobilienkaufvertrag", html)
        self.assertIn("/costs/immobilienkaufvertrag", html)
        self.assertIn("Notariat8-App", html)
        self.assertIn("Notarielle Abläufe ohne Mandatsdaten ansehen.", html)
        self.assertIn("Ablaufmodelle", html)
        self.assertIn("Offene Angaben", html)
        self.assertIn("Kostenansichten", html)
        self.assertIn("freigegebene Ablaufmodelle", html)
        self.assertIn("Änderung vorbereiten", html)
        self.assertIn("Kosten prüfen", html)
        self.assertNotIn("Lokaler NaC-Webserver", html)
        self.assertNotIn("Lokale Notariat8-App", html)
        self.assertNotIn("Grafische Ausgaben", html)
        self.assertNotIn("BPMN-Prozessmodelle", html)
        self.assertNotIn("Wissensgraphen", html)
        self.assertNotIn("Wissensgraph-Ansichten", html)
        self.assertNotIn("Knowledge Graphs", html)
        self.assertNotIn("KG-Editor-Views", html)
        self.assertNotIn("KG-Editor", html)
        self.assertNotIn("Repository gelesen", html)
        self.assertNotIn("Repository", html)
        self.assertNotIn("bindet standardmäßig", html)
        self.assertNotIn("127.0.0.1", html)
        self.assertNotIn("bpmn/immobilienkaufvertrag.bpmn", html)
        self.assertNotIn("Bookkeeping Process", html)
        self.assertNotIn("Invoice Process", html)
        self.assertNotIn("Onboarding Entry Process", html)
        self.assertNotIn("/bpmn/bookkeeping-process", html)
        self.assertNotIn("/bpmn/invoice-process", html)
        self.assertNotIn("/bpmn/onboarding-entry", html)

    def test_bpmn_svg_renders_local_model(self) -> None:
        model = find_bpmn_model(REPO_ROOT, "immobilienkaufvertrag")
        svg = render_bpmn_svg(model)

        self.assertIn("<svg", svg)
        self.assertIn('width="', svg)
        self.assertIn('height="', svg)
        self.assertIn("Auftrag und Beteiligte", svg)
        self.assertIn("xnp_local", svg)
        self.assertTrue(model.has_diagram)

    def test_bpmn_page_uses_responsive_diagram_and_table_layout(self) -> None:
        model = find_bpmn_model(REPO_ROOT, "immobilienkaufvertrag")
        html = build_bpmn_page(model)

        self.assertIn('class="canvas bpmn-diagram-panel"', html)
        self.assertIn('class="diagram-scroll"', html)
        self.assertIn('class="table-scroll responsive-table"', html)
        self.assertIn('data-label="Name"', html)
        self.assertIn('data-label="Nachweis"', html)
        self.assertIn(".responsive-table td::before", html)
        self.assertIn(".diagram-scroll", html)

    def test_kg_page_blocks_value_field_surface(self) -> None:
        view = build_editor_view(REPO_ROOT, "immobilienkaufvertrag")
        html = build_kg_page(view)

        self.assertIn("Schutzregel", html)
        self.assertIn("Offene Angaben", html)
        self.assertIn("Mandatswerte", html)
        self.assertNotIn("<td>value</td>", html)
        self.assertNotIn("<code>value</code>", html)

    def test_kg_page_uses_german_status_and_role_labels(self) -> None:
        view = build_editor_view(REPO_ROOT, "immobilienkaufvertrag")
        html = build_kg_page(view)

        self.assertIn("Status: offen", html)
        self.assertIn("Kaufpreis und Fälligkeitsmodell", html)
        self.assertIn("Öffentlich-rechtliche Genehmigungen", html)
        self.assertIn("Notariatsfachkraft", html)
        self.assertIn("Notarin/Notar", html)
        self.assertNotIn(">open<", html)
        self.assertNotIn("Faellig", html)
        self.assertNotIn("notary_clerk", html)
        self.assertNotIn(">notary<", html)
        self.assertNotIn("Pull Request", html)

    def test_cost_page_exposes_local_quote_form_without_value_fields(self) -> None:
        view = build_cost_review_view(REPO_ROOT, "immobilienkaufvertrag")
        html = build_cost_page(view)

        self.assertIn("GNotKG-Kostenprüfung", html)
        self.assertIn('id="gnotkg-quote-form"', html)
        self.assertIn("/api/gnotkg/quote", html)
        self.assertIn("method: \"POST\"", html)
        self.assertIn("Geschäftswert für GNotKG-Kostenprüfung", html)
        self.assertNotIn("<td>value</td>", html)
        self.assertNotIn("<code>value</code>", html)

    def test_app_serves_health_and_api(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        health_status, health_type, health_body = app.handle("/healthz")
        api_status, api_type, api_body = app.handle("/api/bpmn/immobilienkaufvertrag")
        cost_status, cost_type, cost_body = app.handle("/api/costs/immobilienkaufvertrag")
        quote_status, quote_type, quote_body = app.handle_post(
            "/api/gnotkg/quote",
            json.dumps(
                {
                    "business_value": "500000",
                    "table": "A",
                    "fee_rate": "1.0",
                    "kv_number": "21100",
                }
            ).encode("utf-8"),
        )

        self.assertEqual(health_status, 200)
        self.assertEqual(health_type, "application/json; charset=utf-8")
        self.assertIn(b'"status": "ok"', health_body)
        self.assertEqual(api_status, 200)
        self.assertEqual(api_type, "application/json; charset=utf-8")
        self.assertIn(b"Process_immobilienkaufvertrag", api_body)
        self.assertEqual(cost_status, 200)
        self.assertEqual(cost_type, "application/json; charset=utf-8")
        self.assertIn(b"gate.gnotkg_cost_review", cost_body)
        self.assertEqual(quote_status, 200)
        self.assertEqual(quote_type, "application/json; charset=utf-8")
        quote_payload = json.loads(quote_body.decode("utf-8"))
        self.assertEqual(quote_payload["fee_amount"], "4138.00")

    def test_runtime_server_supports_head_healthz_for_lb_monitoring(self) -> None:
        server = nac_server.build_server(REPO_ROOT, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request("HEAD", "/healthz")
            response = conn.getresponse()
            body = response.read()
            conn.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Type"), "application/json; charset=utf-8")
        self.assertEqual(response.getheader("Content-Length"), "20")
        self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
        self.assertEqual(body, b"")

    def test_app_serves_empty_favicon_without_browser_console_404(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle("/favicon.ico")

        self.assertEqual(status, 204)
        self.assertEqual(content_type, "image/x-icon")
        self.assertEqual(body, b"")

    def test_app_serves_tenant_domain_check_api(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/api/tenant/domain-check"
            "?domain=kanzlei-notariat.example"
            "&tenant_slug=kanzlei-notariat"
            "&admin_email=admin@kanzlei-notariat.example"
        )

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        payload = json.loads(body.decode("utf-8"))
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["tenant_slug"], "kanzlei-notariat")

    def test_app_serves_tenant_provision_admin_preview_api(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle_post(
            "/api/tenant/provision-admin/preview",
            json.dumps(
                {
                    "tenant_slug": "kanzlei-notariat",
                    "domain": "kanzlei-notariat.example",
                    "admin_email": "admin@kanzlei-notariat.example",
                    "admin_display_name": "Admin Notariat",
                    "identity_domain_url": "https://idcs.example.identity.oraclecloud.com:443",
                    "identity_domain_id": "ocid1.domain.oc1.example",
                }
            ).encode("utf-8"),
        )

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["mode"], "dry_run")
        self.assertTrue(payload["requires_human_approval"])

    def test_admin_queue_page_shows_customer_onboarding_request_without_secrets(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle("/admin/onboarding")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("Readiness-Anfragen", html)
        self.assertIn("nac-saas-owner", html)
        self.assertIn("owner_apply_ready", html)
        self.assertNotIn("api_key", html.lower())
        self.assertNotIn("password", html.lower())

    def test_customer_readiness_page_explains_next_steps(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle("/onboarding/readiness?domain_hint=kanzlei-notariat.example")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("Domain-Readiness", html)
        self.assertIn("DNS-TXT", html)
        self.assertIn("DNS jetzt prüfen", html)
        self.assertIn("/onboarding/dns-check?domain=kanzlei-notariat.example", html)
        self.assertIn("später", html)
        self.assertIn("Keine Mandatsdaten", html)
        self.assertIn("propagation", html)
        self.assertNotIn("OCI Console", html)

    def test_customer_dns_check_page_renders_live_dns_result_without_raw_json(self) -> None:
        def fake_resolver(record_name: str) -> dict:
            return {
                "name": record_name,
                "values": ["nac-domain-verification=36685e54c3d26580dace709f1f09c702"],
                "resolver_error": "",
            }

        app = NaCLocalWebApp(REPO_ROOT, dns_resolver=fake_resolver)

        status, content_type, body = app.handle(
            "/onboarding/dns-check"
            "?domain=kanzlei-notariat.example"
            "&tenant_slug=kanzlei-notariat"
            "&admin_email=admin@kanzlei-notariat.example"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("DNS-Prüfergebnis", html)
        self.assertIn("verified", html)
        self.assertIn("live_dns", html)
        self.assertIn("Admin-Dry-Run vorbereiten", html)
        self.assertNotIn('"schema_version"', html)
        self.assertNotIn("client_secret", html.lower())

    def test_customer_readiness_page_links_admin_provisioning_preview(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, _content_type, body = app.handle(
            "/onboarding/readiness"
            "?domain_hint=kanzlei-notariat.example"
            "&tenant_slug=kanzlei-notariat"
            "&admin_email=admin@kanzlei-notariat.example"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("Admin-Dry-Run vorbereiten", html)
        self.assertIn(
            "/admin/onboarding/provisioning-preview?domain=kanzlei-notariat.example&amp;tenant_slug=kanzlei-notariat&amp;admin_email=admin%40kanzlei-notariat.example",
            html,
        )

    def test_admin_provisioning_preview_page_renders_dry_run_without_credentials(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/admin/onboarding/provisioning-preview"
            "?domain=kanzlei-notariat.example"
            "&tenant_slug=kanzlei-notariat"
            "&admin_email=admin@kanzlei-notariat.example"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("OCI-Admin-Dry-Run", html)
        self.assertIn("dry_run", html)
        self.assertIn("owner_apply_approval", html)
        self.assertIn("users.create", html)
        self.assertIn("nac-tenant-admin", html)
        self.assertIn("admin@kanzlei-notariat.example", html)
        self.assertIn("Apply-Readiness vorbereiten", html)
        self.assertIn(
            "/admin/onboarding/apply-readiness?domain=kanzlei-notariat.example&amp;tenant_slug=kanzlei-notariat&amp;admin_email=admin%40kanzlei-notariat.example",
            html,
        )
        self.assertNotIn("api_key", html.lower())
        self.assertNotIn("password", html.lower())
        self.assertNotIn("client_secret", html.lower())

    def test_admin_apply_readiness_preview_page_renders_review_artifact_without_credentials(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/admin/onboarding/apply-readiness"
            "?domain=kanzlei-notariat.example"
            "&tenant_slug=kanzlei-notariat"
            "&admin_email=admin@kanzlei-notariat.example"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("Apply-Readiness", html)
        self.assertIn("review_artifact_only", html)
        self.assertIn("ready_to_apply", html)
        self.assertIn("bereit", html)
        self.assertIn("OWNER-APPLY-2026-0001", html)
        self.assertIn("AUDIT-2026-0001", html)
        self.assertIn("ROLLBACK-2026-0001", html)
        self.assertIn("dns_verified", html)
        self.assertIn("connector_apply_in_scope", html)
        self.assertIn("productive_write_executed", html)
        self.assertIn("compact-table", html)
        self.assertIn(".compact-table table { min-width: 0;", html)
        self.assertIn("admin@kanzlei-notariat.example", html)
        self.assertNotIn("api_key", html.lower())
        self.assertNotIn("password", html.lower())
        self.assertNotIn("client_secret", html.lower())
        self.assertNotIn("private_key", html.lower())

    def test_customer_readiness_return_later_preserves_customer_context(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, _content_type, body = app.handle(
            "/onboarding/readiness"
            "?domain_hint=kanzlei-notariat.example"
            "&tenant_slug=notariat-2026"
            "&admin_email=verwaltung@kanzlei-notariat.example"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn(
            "/onboarding/readiness?domain_hint=kanzlei-notariat.example&amp;tenant_slug=notariat-2026&amp;admin_email=verwaltung%40kanzlei-notariat.example",
            html,
        )

    def test_app_receives_www_n8_customer_handoff_without_tenant_decision(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/?source=www-n8&entry=customer&tenant_hint=notariat-musterstadt"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("notariat8 App-Einstieg", html)
        self.assertIn("Bestandskunde", html)
        self.assertIn("notariat-musterstadt", html)
        self.assertIn("Anmeldung öffnen", html)
        self.assertIn("Ihr Notariat", html)
        self.assertIn("notariat8", html)
        self.assertIn("/login?source=notariat8&amp;entry=customer&amp;tenant_hint=notariat-musterstadt", html)
        self.assertNotIn("www-n8", html)
        self.assertNotIn("NaC", html)
        self.assertNotIn("OCI", html)
        self.assertNotIn("Tenant", html)

    def test_app_receives_www_n8_prospect_handoff_on_customer_readiness_page(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/?source=www-n8&entry=prospect&domain_hint=kanzlei-notariat.example"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Domain-Readiness", html)
        self.assertIn("DNS-TXT", html)
        self.assertIn("Keine Mandatsdaten", html)
        self.assertIn("notariat8", html)
        self.assertIn("kanzlei-notariat.example", html)
        self.assertIn("notariat8-Referenz", html)
        self.assertIn("E-Mail-Adresse angeben", html)
        self.assertIn('name="admin_email"', html)
        self.assertIn("keine E-Mail automatisch versendet", html)
        self.assertIn("noch offen", html)
        self.assertNotIn("DNS jetzt prüfen", html)
        self.assertNotIn("admin@kanzlei-notariat.example", html)
        self.assertNotIn("admin%40kanzlei-notariat.example", html)
        self.assertNotIn("NaC App-Einstieg", html)
        self.assertNotIn("API-Kante", html)
        self.assertNotIn("Guardrails", html)
        self.assertNotIn("www-n8", html)
        self.assertNotIn("NaC-Kennung", html)
        self.assertNotIn("Administrations-E-Mail", html)
        self.assertNotIn("Tenant-Slug", html)
        self.assertNotIn("Admin-Queue", html)
        self.assertNotIn("Admin-Dry-Run", html)
        self.assertNotIn("nac-saas-owner", html)
        self.assertNotIn("Notariat8", html)
        self.assertNotIn("pending", html)
        self.assertNotIn("propagation", html)

    def test_www_n8_prospect_readiness_uses_explicit_admin_email_only(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/onboarding/readiness"
            "?audience=customer"
            "&domain_hint=kanzlei-notariat.example"
            "&tenant_slug=kanzlei-notariat"
            "&admin_email=verwaltung@kanzlei-notariat.example"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("verwaltung@kanzlei-notariat.example", html)
        self.assertIn("DNS jetzt prüfen", html)
        self.assertIn("admin_email=verwaltung%40kanzlei-notariat.example", html)
        self.assertNotIn("admin@kanzlei-notariat.example", html)

    def test_www_n8_prospect_dns_check_stays_customer_facing(self) -> None:
        def fake_resolver(record_name: str) -> dict:
            return {
                "name": record_name,
                "values": ["nac-domain-verification=36685e54c3d26580dace709f1f09c702"],
                "resolver_error": "",
            }

        app = NaCLocalWebApp(REPO_ROOT, dns_resolver=fake_resolver)

        status, content_type, body = app.handle(
            "/onboarding/dns-check"
            "?audience=customer"
            "&domain=kanzlei-notariat.example"
            "&tenant_slug=kanzlei-notariat"
            "&admin_email=admin@kanzlei-notariat.example"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("DNS-Prüfergebnis", html)
        self.assertIn("Domain bestätigt", html)
        self.assertIn("Was passiert als Nächstes?", html)
        self.assertIn("notariat8", html)
        self.assertIn("bestätigt", html)
        self.assertIn("Erneut prüfen", html)
        self.assertIn("noch keine Einladung versendet", html)
        self.assertNotIn("verified", html)
        self.assertNotIn("www-n8", html)
        self.assertNotIn("NaC", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)
        self.assertNotIn("Administrations-E-Mail", html)
        self.assertNotIn("Admin-Queue", html)
        self.assertNotIn("Admin-Dry-Run", html)
        self.assertNotIn("Tenant-Slug", html)
        self.assertNotIn("nac-saas-owner", html)
        self.assertNotIn("live_dns", html)
        self.assertNotIn("OCI-Credentials", html)
        self.assertNotIn("Beobachtete Werte", html)
        self.assertNotIn("Diagnose", html)

    def test_www_n8_handoff_escapes_hint_values(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, _content_type, body = app.handle(
            "/?source=www-n8&entry=prospect&domain_hint=%3Cscript%3Ealert(1)%3C/script%3E"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_www_n8_handoff_falls_back_for_unknown_source(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, _content_type, body = app.handle(
            "/?source=unknown&entry=prospect&domain_hint=kanzlei-notariat.example"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("Notariat8-App", html)
        self.assertNotIn("NaC App-Einstieg", html)

    def test_login_page_accepts_www_n8_customer_context_without_authorizing_tenant(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/login?source=www-n8&entry=customer&tenant_hint=notariat-musterstadt"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("OCI-IdP Login-Contract", html)
        self.assertIn("notariat-musterstadt", html)
        self.assertIn("serverseitig erzeugte State- und Nonce-Werte", html)
        self.assertIn("NaC-Rollen- und Vorgangs-Gate", html)
        self.assertNotIn("client_secret", html)

    def test_app_serves_login_intent_api_without_leaking_tenant_hint_to_authorize_url(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs.example.identity.oraclecloud.com:443",
                "NAC_OIDC_CLIENT_ID": "nac-web-app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
            },
        ):
            status, content_type, body = app.handle("/api/tenant/login-intent?tenant_hint=notariat-musterstadt")
        payload = json.loads(body.decode("utf-8"))

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        self.assertEqual(payload["schema_version"], "nac.oci-login-intent/v0.1")
        self.assertIn("/oauth2/v1/authorize", payload["authorization_url"])
        self.assertNotIn("notariat-musterstadt", payload["authorization_url"])
        self.assertFalse(payload["tenant_context"]["tenant_authorized_by_hint"])
        self.assertNotEqual(payload["oidc"]["state"], "state-1234567890")
        self.assertNotEqual(payload["oidc"]["nonce"], "nonce-1234567890")

    def test_login_intent_api_rejects_caller_supplied_oidc_config(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/api/tenant/login-intent"
            "?tenant_hint=notariat-musterstadt"
            "&identity_domain_url=https%3A%2F%2Fidcs.example.identity.oraclecloud.com%3A443"
            "&state=attacker-state"
            "&nonce=attacker-nonce"
        )
        payload = json.loads(body.decode("utf-8"))

        self.assertEqual(status, 400)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        self.assertEqual(payload["error"], "login_intent_config_is_server_side")

    def test_gnotkg_quote_rejects_get_query_to_avoid_logged_values(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, _content_type, body = app.handle(
            "/api/gnotkg/quote?business_value=500000&table=A&fee_rate=1.0"
        )

        self.assertEqual(status, 405)
        self.assertIn("POST", body.decode("utf-8"))

    def test_app_serves_bpmn_xml_and_editor(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        xml_status, xml_type, xml_body = app.handle("/api/bpmn/handelsregisteranmeldung/xml")
        edit_status, edit_type, edit_body = app.handle("/bpmn/handelsregisteranmeldung/edit")
        payload = json.loads(xml_body.decode("utf-8"))

        self.assertEqual(xml_status, 200)
        self.assertEqual(xml_type, "application/json; charset=utf-8")
        self.assertIn("<bpmn:definitions", payload["xml"])
        self.assertIn("sha256", payload)
        self.assertEqual(edit_status, 200)
        self.assertEqual(edit_type, "text/html; charset=utf-8")
        self.assertIn(b"BPMN-js Editor", edit_body)
        self.assertIn(b"/api/bpmn/handelsregisteranmeldung/xml", edit_body)

    def test_bpmn_editor_exposes_full_workbench_controls(self) -> None:
        model = find_bpmn_model(REPO_ROOT, "immobilienkaufvertrag")
        html = build_bpmn_editor_page(model)

        self.assertIn("BPMN Editor Menü", html)
        self.assertIn("diagram-js.css", html)
        self.assertIn("bpmn-embedded.css", html)
        self.assertIn('class="editor-workbench"', html)
        self.assertIn('class="editor-properties-panel"', html)
        self.assertIn('data-create-kind="bpmn:Task"', html)
        self.assertIn('data-select-element="', html)
        self.assertIn('id="nac-role"', html)
        self.assertIn('id="nac-kg-ref"', html)
        self.assertIn('id="toggle-xml"', html)
        self.assertIn('modeling.updateProperties', html)
        self.assertNotIn("bpmn-js laden", html)

    def test_app_serves_all_usecase_workbench_routes(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)
        slugs = sorted(
            path.name
            for path in (REPO_ROOT / "usecases").iterdir()
            if path.is_dir() and (path / "knowledge-graph.graph.json").is_file()
        )

        self.assertEqual(len(slugs), 22)
        failures: list[str] = []
        for slug in slugs:
            for route in (f"/kg/{slug}", f"/costs/{slug}", f"/bpmn/{slug}", f"/bpmn/{slug}/edit"):
                status, content_type, body = app.handle(route)
                if status != 200:
                    failures.append(f"{status} {route}")
                self.assertIn(content_type, {"text/html; charset=utf-8", "application/json; charset=utf-8"})
                self.assertGreater(len(body), 100)

        self.assertEqual(failures, [])

    def test_bpmn_xml_save_rejects_stale_hash(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        xml_status, _xml_type, xml_body = app.handle("/api/bpmn/handelsregisteranmeldung/xml")
        payload = json.loads(xml_body.decode("utf-8"))
        save_status, save_type, save_body = app.handle_post(
            "/api/bpmn/handelsregisteranmeldung/xml",
            json.dumps({"xml": payload["xml"], "base_sha256": "0" * 64}).encode("utf-8"),
        )

        self.assertEqual(xml_status, 200)
        self.assertEqual(save_status, 409)
        self.assertEqual(save_type, "application/json; charset=utf-8")
        self.assertIn("geändert", save_body.decode("utf-8"))

    def test_bpmn_model_catalog_is_not_empty(self) -> None:
        models = list_bpmn_models(REPO_ROOT)

        self.assertGreaterEqual(len(models), 1)
        self.assertTrue(any(model.stem == "immobilienkaufvertrag" for model in models))
        self.assertTrue(any(model.stem == "handelsregisteranmeldung" for model in models))


if __name__ == "__main__":
    unittest.main()
