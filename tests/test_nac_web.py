from __future__ import annotations

import base64
import http.client
import hashlib
import io
import json
import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
FIRST_MATTER_METADATA_FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "demo"
    / "notarkammer-first-immobilienkaufvertrag.metadata.json"
)
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_web.bpmn import find_bpmn_model, list_bpmn_models, render_bpmn_svg  # noqa: E402
import nac_web.server as nac_server  # noqa: E402
from nac_runtime.status_source import AtpJsonRuntimeMetadataSource  # noqa: E402
from nac_web.server import NaCLocalWebApp, build_bpmn_editor_page, build_bpmn_page, build_cost_page, build_home_page, build_kg_page  # noqa: E402
from nac_gnotkg.views import build_cost_review_view  # noqa: E402
from notary_kg.editor import build_editor_view  # noqa: E402


def _session_cookie_payload(cookie_header: str) -> dict[str, object]:
    cookie_value = cookie_header.split("=", 1)[1]
    payload_part = cookie_value.split(".", 1)[0]
    padding = "=" * (-len(payload_part) % 4)
    return json.loads(base64.urlsafe_b64decode(f"{payload_part}{padding}".encode("ascii")).decode("utf-8"))


def _bound_workspace_app_and_cookie(first_matter_runtime_metadata_source=None) -> tuple[NaCLocalWebApp, str]:
    from nac_identity.oidc_session import evaluate_oidc_session_boundary
    from nac_identity.session_store import MappingSessionStoreAdapter

    session = evaluate_oidc_session_boundary(
        state_validation={
            "status": "valid",
            "tenant_hint": "myjur",
            "nonce_bound": True,
            "nonce_hash": hashlib.sha256("nonce-from-id-token".encode("utf-8")).hexdigest(),
        },
        token_exchange_result={
            "status": "verified",
            "claims": {
                "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "aud": "notariat8_nac_app",
                "nonce": "nonce-from-id-token",
                "groups": ["nac-notary"],
                "email": "notar@example.test",
            },
        },
        expected_issuer="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
        expected_audience="notariat8_nac_app",
        required_role="nac-notary",
        session_signing_key="unit-test-session-signing-key",
        now=1_800_000_000,
        session_ttl_seconds=600,
    )
    cookie_header = session["session"]["set_cookie"].split(";", 1)[0]
    payload = _session_cookie_payload(cookie_header)
    app = NaCLocalWebApp(
        REPO_ROOT,
        session_store=MappingSessionStoreAdapter(
            {
                payload["sid"]: {
                    "schema_version": "nac.server-session/v0.1",
                    "session_id": payload["sid"],
                    "issued_at": payload["iat"],
                    "expires_at": payload["exp"],
                    "revoked_at": None,
                    "audit_event_id": "audit-event-secret",
                    "contains_credentials": False,
                    "tokens_stored": False,
                    "claims_stored": False,
                    "tenant_bound": True,
                    "subject_bound": True,
                    "role_bound": True,
                    "case_bound": True,
                    "purpose_bound": True,
                }
            }
        ),
        first_matter_runtime_metadata_source=first_matter_runtime_metadata_source,
    )
    return app, cookie_header


class NaCLocalWebTests(unittest.TestCase):
    def test_home_page_links_bpmn_and_kg_views(self) -> None:
        html = build_home_page(REPO_ROOT)

        self.assertIn("/bpmn/immobilienkaufvertrag", html)
        self.assertIn("/bpmn/handelsregisteranmeldung", html)
        self.assertIn("/bpmn/handelsregisteranmeldung/edit", html)
        self.assertIn("/kg/immobilienkaufvertrag", html)
        self.assertIn("/costs/immobilienkaufvertrag", html)
        self.assertIn("Lokaler NaC-Webserver", html)

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

    def test_runtime_server_binds_session_store_from_environment(self) -> None:
        class DummySessionStore:
            pass

        session_store = DummySessionStore()
        runtime_source = AtpJsonRuntimeMetadataSource(lambda _object_key: {})
        with (
            patch("nac_web.server.build_session_store_from_env", return_value=session_store) as session_factory,
            patch("nac_web.server.build_onboarding_request_store_from_env") as onboarding_factory,
            patch(
                "nac_web.server.build_first_matter_runtime_metadata_source_from_env",
                return_value=runtime_source,
            ) as runtime_source_factory,
            patch("nac_web.server.NaCLocalWebApp") as app_factory,
        ):
            server = nac_server.build_server(REPO_ROOT, "127.0.0.1", 0)
            server.server_close()

        session_factory.assert_called_once_with()
        onboarding_factory.assert_called_once_with()
        runtime_source_factory.assert_called_once_with()
        _, kwargs = app_factory.call_args
        self.assertIs(kwargs["session_store"], session_store)
        self.assertIs(kwargs["first_matter_runtime_metadata_source"], runtime_source)

    def test_runtime_server_sanitizes_auth_callback_query_in_logs(self) -> None:
        server = nac_server.build_server(REPO_ROOT, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        log_output = io.StringIO()
        try:
            with patch("sys.stdout", log_output):
                conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                conn.request("GET", "/auth/callback?code=secret-code-from-idp&state=state-secret-from-nac")
                response = conn.getresponse()
                response.read()
                conn.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        logs = log_output.getvalue()
        self.assertEqual(response.status, 200)
        self.assertIn("/auth/callback", logs)
        self.assertNotIn("secret-code-from-idp", logs)
        self.assertNotIn("state-secret-from-nac", logs)

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
                    "identity_domain_url": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                    "identity_domain_id": "ocid1.domain.oc1..aaaaaaaarealidentitydomain",
                }
            ).encode("utf-8"),
        )

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["mode"], "dry_run")
        self.assertTrue(payload["requires_human_approval"])

    def test_admin_queue_page_fails_closed_without_static_demo_request(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT, operator_access=True)

        status, content_type, body = app.handle("/admin/onboarding")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("Readiness-Anfragen", html)
        self.assertIn("Produktive Queue noch nicht verbunden", html)
        self.assertNotIn("kanzlei-notariat.example", html)
        self.assertNotIn("nac-saas-owner", html)
        self.assertNotIn("api_key", html.lower())
        self.assertNotIn("password", html.lower())

    def test_admin_routes_require_operator_access(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        blocked_paths = [
            "/admin/onboarding",
            "/admin/onboarding/provisioning-preview"
            "?domain=kanzlei-notariat.example"
            "&tenant_slug=kanzlei-notariat"
            "&admin_email=admin@kanzlei-notariat.example",
            "/admin/onboarding/apply-readiness"
            "?domain=kanzlei-notariat.example"
            "&tenant_slug=kanzlei-notariat"
            "&admin_email=admin@kanzlei-notariat.example",
        ]

        for path in blocked_paths:
            with self.subTest(path=path):
                status, content_type, body = app.handle(path)
                html = body.decode("utf-8")

                self.assertEqual(status, 403)
                self.assertIn("text/html", content_type)
                self.assertIn("notariat8 Anmeldung erforderlich", html)
                self.assertIn("Rollenprüfung", html)
                self.assertNotIn("Readiness-Anfragen", html)
                self.assertNotIn("OCI-Admin-Dry-Run", html)
                self.assertNotIn("Apply-Readiness", html)
                self.assertNotIn("api_key", html.lower())
                self.assertNotIn("client_secret", html.lower())

    def test_admin_review_post_requires_operator_access(self) -> None:
        class FakeOnboardingRequestStore:
            def review_request(self, **_kwargs: str) -> dict[str, str]:
                raise AssertionError("store must not be called without operator access")

        app = NaCLocalWebApp(REPO_ROOT, onboarding_request_store=FakeOnboardingRequestStore())

        status, content_type, body = app.handle_post(
            "/admin/onboarding/review",
            b"request_id=onr_myjur_20260611_182453&decision=approve",
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 403)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("notariat8 Anmeldung erforderlich", html)
        self.assertIn("Rollenprüfung", html)
        self.assertNotIn("onr_myjur_20260611_182453", html)
        self.assertNotIn("approved", html)

    def test_admin_queue_page_renders_real_onboarding_requests_without_secrets(self) -> None:
        class FakeOnboardingRequestStore:
            def list_requests(self) -> list[dict[str, str]]:
                return [
                    {
                        "request_id": "onr_myjur_20260610_000000",
                        "tenant_slug": "myjur",
                        "domain": "myjur.de",
                        "admin_email": "ofunk@myjur.de",
                        "dns_status": "verified",
                        "request_status": "submitted",
                        "invitation_status": "not_sent",
                        "created_at": "2026-06-10T00:00:00Z",
                    }
                ]

        app = NaCLocalWebApp(
            REPO_ROOT,
            onboarding_request_store=FakeOnboardingRequestStore(),
            operator_access=True,
        )

        status, content_type, body = app.handle("/admin/onboarding")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("onr_myjur_20260610_000000", html)
        self.assertIn("myjur.de", html)
        self.assertIn("ofunk@myjur.de", html)
        self.assertIn("submitted", html)
        self.assertIn("not_sent", html)
        self.assertNotIn("kanzlei-notariat.example", html)
        self.assertNotIn("api_key", html.lower())
        self.assertNotIn("password", html.lower())
        self.assertNotIn("client_secret", html.lower())

    def test_admin_queue_page_offers_review_action_without_invitation_send(self) -> None:
        class FakeOnboardingRequestStore:
            def list_requests(self) -> list[dict[str, str]]:
                return [
                    {
                        "request_id": "onr_myjur_20260611_182453",
                        "tenant_slug": "myjur",
                        "domain": "myjur.de",
                        "admin_email": "ofunk@myjur.de",
                        "dns_status": "verified",
                        "request_status": "submitted",
                        "invitation_status": "not_sent",
                        "created_at": "2026-06-11T18:24:53Z",
                    }
                ]

        app = NaCLocalWebApp(
            REPO_ROOT,
            onboarding_request_store=FakeOnboardingRequestStore(),
            operator_access=True,
        )

        status, _content_type, body = app.handle("/admin/onboarding")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn('action="/admin/onboarding/review"', html)
        self.assertIn('name="request_id" value="onr_myjur_20260611_182453"', html)
        self.assertIn('name="decision" value="approve"', html)
        self.assertIn("E-Mail geprüft", html)
        self.assertIn("Einladung noch nicht senden", html)
        self.assertNotIn("Einladung senden", html)

    def test_admin_review_post_marks_request_ready_without_sending_invitation(self) -> None:
        class FakeOnboardingRequestStore:
            def __init__(self) -> None:
                self.review_calls: list[dict[str, str]] = []

            def review_request(self, **kwargs: str) -> dict[str, str]:
                self.review_calls.append(kwargs)
                return {
                    "request_id": kwargs["request_id"],
                    "tenant_slug": "myjur",
                    "domain": "myjur.de",
                    "admin_email": "ofunk@myjur.de",
                    "dns_status": "verified",
                    "request_status": "approved",
                    "invitation_status": "not_sent",
                    "created_at": "2026-06-11T18:24:53Z",
                    "updated_at": "2026-06-11T18:30:00Z",
                    "review_audit": {
                        "schema_version": "nac.onboarding-review-audit/v0.1",
                        "request_id": kwargs["request_id"],
                        "decision": kwargs["decision"],
                        "reviewed_at": "2026-06-11T18:30:00Z",
                        "review_surface": "admin.onboarding.review",
                        "contains_mandate_data": False,
                        "customer_mail_dispatched": False,
                        "oci_write_executed": False,
                        "atp_schema_change_required": False,
                    },
                }

        store = FakeOnboardingRequestStore()
        app = NaCLocalWebApp(REPO_ROOT, onboarding_request_store=store, operator_access=True)

        status, content_type, body = app.handle_post(
            "/admin/onboarding/review",
            b"request_id=onr_myjur_20260611_182453&decision=approve",
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertEqual(
            store.review_calls,
            [
                {
                    "request_id": "onr_myjur_20260611_182453",
                    "decision": "approve",
                }
            ],
        )
        self.assertIn("Prüfung gespeichert", html)
        self.assertIn("myjur.de", html)
        self.assertIn("ofunk@myjur.de", html)
        self.assertIn("approved", html)
        self.assertIn("Einladung noch nicht versendet", html)
        self.assertIn("Audit-Metadaten", html)
        self.assertIn("nac.onboarding-review-audit/v0.1", html)
        self.assertIn("Keine Mandatsdaten im Review-Audit", html)
        self.assertIn("Keine E-Mail ausgelöst", html)
        self.assertIn("Keine Cloud-Schreiboperation", html)
        self.assertIn("Keine Datenbank-Schemaänderung", html)
        self.assertNotIn("client_secret", html.lower())
        self.assertNotIn("private_key", html.lower())
        self.assertNotIn("password", html.lower())

    def test_customer_readiness_page_explains_next_steps(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle("/onboarding/readiness?domain_hint=kanzlei-notariat.example")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("Domain vorbereiten", html)
        self.assertIn("DNS-TXT", html)
        self.assertIn("E-Mail-Adresse angeben", html)
        self.assertIn("Die DNS-Prüfung startet erst nach Angabe der E-Mail-Adresse", html)
        self.assertIn("/onboarding/readiness?audience=customer", html)
        self.assertIn("später", html)
        self.assertIn("Keine Mandatsdaten", html)
        self.assertIn("DNS-Änderungen", html)
        self.assertNotIn("Admin-Queue", html)
        self.assertNotIn("Admin-Dry-Run", html)
        self.assertNotIn("Tenant-Slug", html)
        self.assertNotIn("nac-saas-owner", html)
        self.assertNotIn("NaC", html)
        self.assertNotIn("OCI Console", html)

    def test_customer_dns_check_page_renders_customer_result_without_raw_json(self) -> None:
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
        self.assertIn("Domain bestätigt", html)
        self.assertIn("bestätigt", html)
        self.assertIn("Einrichtungsstatus öffnen", html)
        self.assertIn("E-Mail-Adresse prüfen", html)
        self.assertNotIn("verified", html)
        self.assertNotIn("live_dns", html)
        self.assertNotIn("Admin-Dry-Run vorbereiten", html)
        self.assertNotIn("Admin-Queue", html)
        self.assertNotIn("NaC", html)
        self.assertNotIn("OCI", html)
        self.assertNotIn('"schema_version"', html)
        self.assertNotIn("client_secret", html.lower())

    def test_customer_readiness_page_does_not_link_admin_provisioning_preview(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, _content_type, body = app.handle(
            "/onboarding/readiness"
            "?domain_hint=kanzlei-notariat.example"
            "&tenant_slug=kanzlei-notariat"
            "&admin_email=admin@kanzlei-notariat.example"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("Domain vorbereiten", html)
        self.assertIn("DNS jetzt prüfen", html)
        self.assertIn("/onboarding/dns-check?audience=customer", html)
        self.assertNotIn("Admin-Dry-Run vorbereiten", html)
        self.assertNotIn("/admin/onboarding/provisioning-preview", html)
        self.assertNotIn("Admin-Queue", html)
        self.assertNotIn("Tenant-Slug", html)
        self.assertNotIn("nac-saas-owner", html)

    def test_admin_provisioning_preview_page_renders_dry_run_without_credentials(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT, operator_access=True)

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OCI_IDENTITY_DOMAIN_ID": "ocid1.domain.oc1..aaaaaaaarealidentitydomain",
            },
        ):
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

    def test_admin_provisioning_preview_page_fails_closed_without_identity_env(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT, operator_access=True)

        with patch.dict(os.environ, {}, clear=True):
            status, content_type, body = app.handle(
                "/admin/onboarding/provisioning-preview"
                "?domain=kanzlei-notariat.example"
                "&tenant_slug=kanzlei-notariat"
                "&admin_email=admin@kanzlei-notariat.example"
            )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("Konfiguration erforderlich", html)
        self.assertIn("admin_identity_config_missing", html)
        self.assertNotIn("OCI-Admin-Dry-Run", html)
        self.assertNotIn("users.create", html)

    def test_admin_apply_readiness_preview_page_renders_review_artifact_without_credentials(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT, operator_access=True)

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OCI_IDENTITY_DOMAIN_ID": "ocid1.domain.oc1..aaaaaaaarealidentitydomain",
            },
        ):
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
            "/onboarding/readiness?audience=customer&amp;domain_hint=kanzlei-notariat.example&amp;tenant_slug=notariat-2026&amp;admin_email=verwaltung%40kanzlei-notariat.example",
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
        self.assertIn("Domain vorbereiten", html)
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
        self.assertIn("kanzlei-notariat.example", html)
        self.assertIn("admin@kanzlei-notariat.example", html)
        self.assertIn("Einrichtungsstatus öffnen", html)
        self.assertIn("E-Mail-Adresse prüfen", html)
        self.assertIn("Einrichtung freigeben", html)
        self.assertIn("Einrichtung anfragen", html)
        self.assertIn("Einladung noch nicht versendet", html)
        self.assertIn("Technischer Nachweis", html)
        self.assertIn("Erneut prüfen", html)
        self.assertIn('method="post"', html)
        self.assertIn('action="/onboarding/requests?audience=customer"', html)
        self.assertIn('name="domain" value="kanzlei-notariat.example"', html)
        self.assertIn('name="admin_email" value="admin@kanzlei-notariat.example"', html)
        self.assertIn("/onboarding/readiness?audience=customer", html)
        self.assertNotIn("Domain-Readiness öffnen", html)
        self.assertNotIn("notariat8 führt Sie anschließend", html)
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
        self.assertNotIn("resolver", html)
        self.assertNotIn("findings", html)
        self.assertNotIn("dns_record", html)

    def test_customer_onboarding_request_post_redirects_to_reloadable_status_page(self) -> None:
        class FakeOnboardingRequestStore:
            def __init__(self) -> None:
                self.created: list[dict[str, str]] = []
                self.requests: dict[str, dict[str, str]] = {}

            def create_request(self, payload: dict[str, str]) -> dict[str, str]:
                self.created.append(dict(payload))
                created = {
                    **payload,
                    "request_id": "onr_myjur_20260610_111500",
                    "created_at": "2026-06-10T11:15:00Z",
                }
                self.requests[created["request_id"]] = created
                return created

            def get_request(self, request_id: str) -> dict[str, str] | None:
                return self.requests.get(request_id)

        store = FakeOnboardingRequestStore()
        app = NaCLocalWebApp(REPO_ROOT, onboarding_request_store=store)

        response = app.handle_post(
            "/onboarding/requests?audience=customer",
            b"domain=myjur.de&tenant_slug=myjur&admin_email=ofunk%40myjur.de",
        )
        status, content_type, body = response

        self.assertEqual(status, 303)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertEqual(body, b"")
        self.assertEqual(
            response.headers["Location"],
            "/onboarding/requests/onr_myjur_20260610_111500?audience=customer",
        )
        self.assertNotIn("ofunk%40myjur.de", response.headers["Location"])
        self.assertEqual(len(store.created), 1)
        self.assertEqual(store.created[0]["domain"], "myjur.de")
        self.assertEqual(store.created[0]["admin_email"], "ofunk@myjur.de")

        status, content_type, body = app.handle(response.headers["Location"])
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Einrichtung angefragt", html)
        self.assertIn("myjur.de", html)
        self.assertIn("ofunk@myjur.de", html)
        self.assertIn("onr_myjur_20260610_111500", html)
        self.assertIn("Einladung noch nicht versendet", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)
        self.assertNotIn("client_secret", html.lower())
        self.assertNotIn("private_key", html.lower())

    def test_customer_onboarding_request_status_reflects_approved_review_without_invitation_send(self) -> None:
        html = nac_server.build_customer_onboarding_request_page(
            {
                "request_id": "onr_myjur_20260610_111500",
                "domain": "myjur.de",
                "tenant_slug": "myjur",
                "admin_email": "ofunk@myjur.de",
                "request_status": "approved",
                "invitation_status": "not_sent",
            }
        )

        self.assertIn("Einrichtung freigegeben", html)
        self.assertIn("Prüfung dokumentiert", html)
        self.assertIn("Einladung noch nicht versendet", html)
        self.assertIn("Eine E-Mail wird erst nach Freigabe ausgelöst", html)
        self.assertNotIn(">approved<", html)
        self.assertNotIn("not_sent", html)
        self.assertNotIn("Admin", html)
        self.assertNotIn("Operator", html)
        self.assertNotIn("Owner", html)
        self.assertNotIn("Apply", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)
        self.assertNotIn("client_secret", html.lower())
        self.assertNotIn("private_key", html.lower())

    def test_customer_onboarding_request_status_reflects_rejected_review_without_invitation_send(self) -> None:
        html = nac_server.build_customer_onboarding_request_page(
            {
                "request_id": "onr_myjur_20260610_111500",
                "domain": "myjur.de",
                "tenant_slug": "myjur",
                "admin_email": "ofunk@myjur.de",
                "request_status": "rejected",
                "invitation_status": "not_sent",
            }
        )

        self.assertIn("Einrichtung noch nicht freigegeben", html)
        self.assertIn("Prüfung dokumentiert", html)
        self.assertIn("Einladung noch nicht versendet", html)
        self.assertIn("notariat8 meldet sich mit den nächsten Schritten", html)
        self.assertNotIn(">rejected<", html)
        self.assertNotIn("not_sent", html)
        self.assertNotIn("Admin", html)
        self.assertNotIn("Operator", html)
        self.assertNotIn("Owner", html)
        self.assertNotIn("Apply", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)
        self.assertNotIn("client_secret", html.lower())
        self.assertNotIn("private_key", html.lower())

    def test_customer_onboarding_request_post_validation_error_renders_customer_page(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle_post(
            "/onboarding/requests?audience=customer",
            b"domain=myjur.de&tenant_slug=myjur&admin_email=ofunk%40funktion8.de",
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 400)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("E-Mail-Adresse prüfen", html)
        self.assertIn("myjur.de", html)
        self.assertIn("ofunk@funktion8.de", html)
        self.assertIn("/onboarding/readiness?audience=customer", html)
        self.assertNotIn('"admin_email_domain_mismatch"', html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)
        self.assertNotIn("client_secret", html.lower())
        self.assertNotIn("private_key", html.lower())

    def test_customer_onboarding_request_post_fails_closed_without_store(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle_post(
            "/onboarding/requests",
            (
                "domain=kanzlei-notariat.example"
                "&tenant_slug=kanzlei-notariat"
                "&admin_email=admin%40kanzlei-notariat.example"
            ).encode("utf-8"),
        )
        payload = json.loads(body.decode("utf-8"))

        self.assertEqual(status, 503)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        self.assertEqual(payload["error"], "onboarding_request_store_disabled")
        self.assertEqual(payload["status"], "unavailable")
        self.assertNotIn("client_secret", body.decode("utf-8").lower())
        self.assertNotIn("private_key", body.decode("utf-8").lower())

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
        self.assertIn("Lokaler NaC-Webserver", html)
        self.assertNotIn("NaC App-Einstieg", html)

    def test_login_page_accepts_www_n8_customer_context_without_authorizing_tenant(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/login?source=www-n8&entry=customer&tenant_hint=notariat-musterstadt"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("notariat8 Anmeldung", html)
        self.assertIn("notariat-musterstadt", html)
        self.assertIn("serverseitig mit einmaligen Sicherheitswerten erzeugt", html)
        self.assertIn("Jetzt anmelden", html)
        self.assertIn("/api/tenant/login-intent?tenant_hint=notariat-musterstadt", html)
        self.assertIn("window.location.assign", html)
        self.assertIn("Berechtigung und Vorgang", html)
        self.assertNotIn("client_secret", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)
        self.assertNotIn("oraclecloud", html)

    def test_auth_callback_acknowledges_code_without_displaying_callback_values(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/auth/callback?code=secret-code-from-idp&state=state-secret-from-nac"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Anmeldung empfangen", html)
        self.assertIn("Anmeldung und Berechtigung", html)
        self.assertIn("Arbeitsbereich bleibt geschlossen", html)
        self.assertIn("Sicherheitsprüfung offen", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn("state-secret-from-nac", html)
        self.assertNotIn("client_secret", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_fails_closed_when_state_validation_is_configured_without_result(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        with patch.dict(os.environ, {"NAC_OIDC_STATE_VALIDATION_KEY_REF": "vault://nac/state"}, clear=False):
            status, content_type, body = app.handle(
                "/auth/callback?code=secret-code-from-idp&state=attacker-state"
            )
        html = body.decode("utf-8")

        self.assertEqual(status, 400)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Anmeldung nicht abgeschlossen", html)
        self.assertNotIn("attacker-state", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_validates_signed_state_but_keeps_operator_queue_closed(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT)
        nonce = "nonce-secret-for-id-token"
        nonce_hash = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )

        with patch.dict(
            os.environ,
            {"NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key"},
            clear=False,
        ):
            status, content_type, body = app.handle(
                f"/auth/callback?code=secret-code-from-idp&state={state}"
            )
            admin_status, _admin_content_type, admin_body = app.handle("/admin/onboarding")
        html = body.decode("utf-8")
        admin_html = admin_body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Anmeldung empfangen", html)
        self.assertIn("Anmeldung und Berechtigung", html)
        self.assertIn("Sicherheitsprüfung bestätigt", html)
        self.assertIn("Arbeitsbereich bleibt geschlossen", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, html)
        self.assertNotIn(nonce, html)
        self.assertNotIn(nonce_hash, html)
        self.assertNotIn("unit-test-state-signing-key", html)
        self.assertEqual(admin_status, 403)
        self.assertIn("notariat8 Anmeldung erforderlich", admin_html)

    def test_auth_callback_with_token_exchange_metadata_stays_closed_and_redacted(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT)
        nonce = "nonce-secret-for-id-token"
        nonce_hash = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "vault://nac/oidc-client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
            },
            clear=False,
        ):
            status, content_type, body = app.handle(
                f"/auth/callback?code=secret-code-from-idp&state={state}"
            )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Anmeldung empfangen", html)
        self.assertIn("Arbeitsbereich bleibt geschlossen", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, html)
        self.assertNotIn(nonce, html)
        self.assertNotIn(nonce_hash, html)
        self.assertNotIn("vault://nac/oidc-client-secret", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("notariat8_nac_app", html)
        self.assertNotIn("unit-test-state-signing-key", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_shows_redacted_status_diagnostics_when_session_stays_closed(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
        nonce = "nonce-secret-for-id-token"
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.session-key",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: None,
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value={
                "status": "failed",
                "mode": "server_side_token_exchange",
                "live_token_exchange_performed": True,
                "failure_class": "authorization_code_rejected",
                "error_description": "provider failure detail",
            },
            create=True,
        ):
            status, content_type, body = app.handle(
                f"/auth/callback?code=secret-code-from-idp&state={state}"
            )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Technische Statusdiagnose", html)
        self.assertIn("Token-Austausch: Anmeldung abgelaufen oder bereits verwendet", html)
        self.assertIn("Token-Prüfung: nicht gestartet", html)
        self.assertIn("Rollenprüfung: geschlossen", html)
        self.assertIn("Sitzung: nicht erstellt", html)
        self.assertNotIn("authorization_code_rejected", html)
        self.assertNotIn("provider failure detail", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, html)
        self.assertNotIn(nonce, html)
        self.assertNotIn("unit-test-client-secret", html)
        self.assertNotIn("ocid1.vaultsecret", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("notariat8_nac_app", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_shows_redacted_invalid_token_exchange_substatus(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce="nonce-secret-for-id-token",
        )

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.session-key",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: None,
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value={
                "status": "invalid",
                "mode": "server_side_token_exchange",
                "live_token_exchange_performed": True,
                "diagnostic_class": "id_token_verification_failed",
                "id_token": "sample-id-token-value",
            },
            create=True,
        ):
            status, _content_type, body = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("Token-Austausch: Token-Prüfung fehlgeschlagen", html)
        self.assertNotIn("id_token_verification_failed", html)
        self.assertNotIn("sample-id-token-value", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, html)
        self.assertNotIn("ocid1.vaultsecret", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("notariat8_nac_app", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_shows_customer_safe_fallback_for_unclassified_invalid_token_exchange(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce="nonce-secret-for-id-token",
        )

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.session-key",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: None,
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value={
                "status": "invalid",
                "mode": "server_side_token_exchange",
                "live_token_exchange_performed": True,
                "id_token": "sample-id-token-value",
            },
            create=True,
        ):
            status, _content_type, body = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("Token-Austausch: Anmeldung nicht vollständig geprüft", html)
        self.assertNotIn("ungültig", html)
        self.assertNotIn("sample-id-token-value", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, html)
        self.assertNotIn("ocid1.vaultsecret", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("notariat8_nac_app", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_shows_customer_safe_label_for_unavailable_token_exchange(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce="nonce-secret-for-id-token",
        )

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.session-key",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: None,
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value={
                "status": "unavailable",
                "mode": "server_side_token_exchange",
                "live_token_exchange_performed": True,
                "error": "network-or-secret-detail",
            },
            create=True,
        ):
            status, _content_type, body = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("Token-Austausch: Anmeldung vorübergehend nicht verfügbar", html)
        self.assertNotIn("unavailable", html)
        self.assertNotIn("network-or-secret-detail", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, html)
        self.assertNotIn("ocid1.vaultsecret", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("notariat8_nac_app", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_shows_customer_safe_labels_for_failed_token_exchange_classes(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        expected_labels = {
            "client_auth_rejected": "Anmeldung technisch nicht verfügbar",
            "client_not_authorized": "Anmeldung technisch nicht verfügbar",
            "grant_type_unsupported": "Anmeldung technisch nicht verfügbar",
            "token_endpoint_unavailable": "Anmeldung vorübergehend nicht verfügbar",
            "token_request_rejected": "Anmeldung abgelehnt",
            "token_endpoint_rejected": "Anmeldung abgelehnt",
        }

        for failure_class, expected_label in expected_labels.items():
            app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
            state = build_signed_state(
                tenant_hint="myjur",
                signing_key="unit-test-state-signing-key",
                nonce="nonce-secret-for-id-token",
            )

            with self.subTest(failure_class=failure_class), patch.dict(
                os.environ,
                {
                    "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                    "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                    "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                    "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                    "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                    "NAC_SESSION_SIGNING_KEY_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.session-key",
                },
                clear=False,
            ), patch.object(
                nac_server,
                "_auth_callback_id_token_verifier",
                return_value=lambda _id_token: None,
                create=True,
            ), patch.object(
                nac_server,
                "exchange_oidc_authorization_code",
                return_value={
                    "status": "failed",
                    "mode": "server_side_token_exchange",
                    "live_token_exchange_performed": True,
                    "failure_class": failure_class,
                    "error_description": "provider failure detail",
                },
                create=True,
            ):
                status, _content_type, body = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
            html = body.decode("utf-8")

            self.assertEqual(status, 200)
            self.assertIn(f"Token-Austausch: {expected_label}", html)
            self.assertNotIn(failure_class, html)
            self.assertNotIn("provider failure detail", html)
            self.assertNotIn("secret-code-from-idp", html)
            self.assertNotIn(state, html)
            self.assertNotIn("ocid1.vaultsecret", html)
            self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
            self.assertNotIn("notariat8_nac_app", html)
            self.assertNotIn("Oracle", html)
            self.assertNotIn("OCI", html)

    def test_auth_callback_logs_redacted_status_evidence_for_invalid_token_exchange(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce="nonce-secret-for-id-token",
        )

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.session-key",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: None,
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value={
                "status": "invalid",
                "mode": "server_side_token_exchange",
                "live_token_exchange_performed": True,
                "diagnostic_class": "id_token_verification_failed",
                "id_token": "sample-id-token-value",
            },
            create=True,
        ), self.assertLogs("nac_web.server", level="INFO") as logs:
            status, _content_type, _body = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
        log_text = "\n".join(logs.output)

        self.assertEqual(status, 200)
        self.assertIn("auth_callback_status", log_text)
        self.assertIn("state=valid", log_text)
        self.assertIn("token_exchange=invalid", log_text)
        self.assertIn("token_exchange_class=invalid_token", log_text)
        self.assertIn("token_exchange_detail=id_token_verification_failed", log_text)
        self.assertIn("jwt_validation=not_started", log_text)
        self.assertIn("role_gate=closed", log_text)
        self.assertIn("session_cookie=false", log_text)
        self.assertIn("session_store=false", log_text)
        self.assertNotIn("secret-code-from-idp", log_text)
        self.assertNotIn(state, log_text)
        self.assertNotIn("nonce-secret-for-id-token", log_text)
        self.assertNotIn("sample-id-token-value", log_text)
        self.assertNotIn("unit-test-client-secret", log_text)
        self.assertNotIn("ocid1.vaultsecret", log_text)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", log_text)
        self.assertNotIn("notariat8_nac_app", log_text)
        self.assertNotIn("Oracle", log_text)
        self.assertNotIn("OCI", log_text)

    def test_auth_callback_prints_redacted_status_evidence_for_oci_function_logs(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce="nonce-secret-for-id-token",
        )
        stdout = io.StringIO()

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.session-key",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: None,
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value={
                "status": "invalid",
                "mode": "server_side_token_exchange",
                "live_token_exchange_performed": True,
                "diagnostic_class": "id_token_verification_failed",
                "id_token": "sample-id-token-value",
            },
            create=True,
        ), patch("sys.stdout", new=stdout):
            status, _content_type, _body = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
        output = stdout.getvalue()

        self.assertEqual(status, 200)
        self.assertIn("auth_callback_status", output)
        self.assertIn("state=valid", output)
        self.assertIn("token_exchange=invalid", output)
        self.assertIn("token_exchange_class=invalid_token", output)
        self.assertIn("token_exchange_detail=id_token_verification_failed", output)
        self.assertIn("jwt_validation=not_started", output)
        self.assertIn("role_gate=closed", output)
        self.assertIn("session_cookie=false", output)
        self.assertIn("session_store=false", output)
        self.assertNotIn("secret-code-from-idp", output)
        self.assertNotIn(state, output)
        self.assertNotIn("nonce-secret-for-id-token", output)
        self.assertNotIn("sample-id-token-value", output)
        self.assertNotIn("unit-test-client-secret", output)
        self.assertNotIn("ocid1.vaultsecret", output)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", output)
        self.assertNotIn("notariat8_nac_app", output)
        self.assertNotIn("Oracle", output)
        self.assertNotIn("OCI", output)

    def test_auth_callback_reports_redacted_role_missing_boundary(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
        nonce = "nonce-secret-for-id-token"
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )
        exchange_result = {
            "status": "verified",
            "mode": "server_side_token_exchange",
            "live_token_exchange_performed": True,
            "claims": {
                "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "email": "admin@example.test",
            },
        }

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.session-key",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: exchange_result["claims"],
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value=exchange_result,
            create=True,
        ), self.assertLogs("nac_web.server", level="INFO") as logs:
            status, _content_type, body = app.handle(
                f"/auth/callback?code=secret-code-from-idp&state={state}"
            )
        html = body.decode("utf-8")
        log_text = "\n".join(logs.output)

        self.assertEqual(status, 200)
        self.assertIn("Token-Austausch: bestätigt", html)
        self.assertIn("Token-Prüfung: bestätigt", html)
        self.assertIn("Rollenprüfung: Berechtigung offen", html)
        self.assertIn("role_gate_reason=role_missing", log_text)
        self.assertIn("session_cookie=false", log_text)
        self.assertNotIn("secret-code-from-idp", log_text)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, log_text)
        self.assertNotIn(state, html)
        self.assertNotIn(nonce, log_text)
        self.assertNotIn(nonce, html)
        self.assertNotIn("admin@example.test", log_text)
        self.assertNotIn("admin@example.test", html)
        self.assertNotIn("unit-test-client-secret", log_text)
        self.assertNotIn("ocid1.vaultsecret", log_text)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", log_text)
        self.assertNotIn("notariat8_nac_app", log_text)
        self.assertNotIn("Oracle", log_text)
        self.assertNotIn("OCI", log_text)

    def test_auth_callback_invokes_token_exchange_adapter_with_vault_client_secret(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        requested_secret_ids: list[str] = []

        def secret_text_provider(secret_id: str) -> str:
            requested_secret_ids.append(secret_id)
            return "unit-test-client-secret"

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=secret_text_provider)
        nonce = "nonce-secret-for-id-token"
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )
        client_secret_ref = "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret"
        exchange_result = {
            "status": "verified",
            "mode": "server_side_token_exchange",
            "live_token_exchange_performed": True,
            "claims": {
                "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
                "email": "admin@example.test",
            },
        }

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": client_secret_ref,
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: exchange_result["claims"],
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value=exchange_result,
            create=True,
        ) as exchange:
            status, content_type, body = app.handle(
                f"/auth/callback?code=secret-code-from-idp&state={state}"
            )
        html = body.decode("utf-8")
        exchange.assert_called_once()
        _args, kwargs = exchange.call_args

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertEqual(requested_secret_ids, [client_secret_ref])
        self.assertEqual(kwargs["code"], "secret-code-from-idp")
        self.assertEqual(kwargs["redirect_uri"], "https://app.notariat8.de/auth/callback")
        self.assertEqual(
            kwargs["token_endpoint"],
            "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com/oauth2/v1/token",
        )
        self.assertEqual(kwargs["client_id"], "notariat8_nac_app")
        self.assertEqual(kwargs["client_secret"], "unit-test-client-secret")
        self.assertIsNotNone(kwargs["id_token_verifier"])
        self.assertIn("Anmeldung empfangen", html)
        self.assertIn("Arbeitsbereich bleibt geschlossen", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, html)
        self.assertNotIn(nonce, html)
        self.assertNotIn("unit-test-client-secret", html)
        self.assertNotIn(client_secret_ref, html)
        self.assertNotIn("admin@example.test", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("notariat8_nac_app", html)

    def test_auth_callback_builds_runtime_id_token_verifier_from_env(self) -> None:
        created: list[dict[str, object]] = []

        def build_verifier(
            *,
            issuer: str,
            audience: str,
            discovery_base_url: str = "",
            jwks_fetcher: object | None = None,
        ):
            created.append(
                {
                    "issuer": issuer,
                    "audience": audience,
                    "discovery_base_url": discovery_base_url,
                    "jwks_fetcher_injected": callable(jwks_fetcher),
                }
            )
            return lambda _id_token: {"iss": issuer, "aud": audience}

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_EXPECTED_ISSUER": "https://identity.oraclecloud.com/",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "build_oidc_id_token_verifier",
            side_effect=build_verifier,
            create=True,
        ):
            verifier = nac_server._auth_callback_id_token_verifier()

        self.assertIsNotNone(verifier)
        self.assertEqual(
            created,
            [
                {
                    "issuer": "https://identity.oraclecloud.com",
                    "audience": "notariat8_nac_app",
                    "discovery_base_url": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                    "jwks_fetcher_injected": True,
                }
            ],
        )

    def test_auth_callback_shows_role_gate_confirmed_without_opening_workspace(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
        nonce = "nonce-secret-for-id-token"
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )
        exchange_result = {
            "status": "verified",
            "mode": "server_side_token_exchange",
            "live_token_exchange_performed": True,
            "claims": {
                "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
                "email": "admin@example.test",
            },
        }

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: exchange_result["claims"],
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value=exchange_result,
            create=True,
        ):
            status, content_type, body = app.handle(
                f"/auth/callback?code=secret-code-from-idp&state={state}"
            )
            admin_status, _admin_content_type, _admin_body = app.handle("/admin/onboarding")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Rollenprüfung bestätigt", html)
        self.assertIn("Arbeitsbereich bleibt geschlossen", html)
        self.assertIn("Mandatsdaten werden in diesem Zwischenschritt nicht geladen", html)
        self.assertEqual(admin_status, 403)
        self.assertNotIn("admin@example.test", html)
        self.assertNotIn(nonce, html)
        self.assertNotIn(state, html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn("unit-test-client-secret", html)
        self.assertNotIn("ocid1.vaultsecret", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_uses_server_side_role_lookup_after_verified_token(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        observed: list[dict[str, object]] = []

        def role_membership_resolver(*, claims: dict[str, object], required_role: str) -> dict[str, object]:
            observed.append({"claims_keys": sorted(claims.keys()), "required_role": required_role})
            return {
                "status": "confirmed",
                "role": required_role,
                "source": "oci_identity_domain_server_lookup",
            }

        app = NaCLocalWebApp(
            REPO_ROOT,
            secret_text_provider=lambda _secret_id: "unit-test-client-secret",
            role_membership_resolver=role_membership_resolver,
        )
        nonce = "nonce-secret-for-id-token"
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )
        exchange_result = {
            "status": "verified",
            "mode": "server_side_token_exchange",
            "live_token_exchange_performed": True,
            "claims": {
                "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "sub": "subject-secret-from-provider",
                "email": "admin@example.test",
            },
        }

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key",
                "NAC_SESSION_TTL_SECONDS": "600",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: exchange_result["claims"],
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value=exchange_result,
            create=True,
        ), self.assertLogs("nac_web.server", level="INFO") as logs:
            response = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
        html = response.body.decode("utf-8")
        log_text = "\n".join(logs.output)

        self.assertEqual(response.status, 200)
        self.assertEqual(observed, [{"claims_keys": ["aud", "email", "iss", "nonce", "sub"], "required_role": "nac-tenant-admin"}])
        self.assertIn("Rollenprüfung bestätigt", html)
        self.assertIn("Sitzung vorbereitet", html)
        self.assertIn("Startstatus freigegeben", html)
        self.assertIn("__Host-nac_session=", response.headers["Set-Cookie"])
        self.assertIn("role_gate_reason=server_membership_confirmed", log_text)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, html)
        self.assertNotIn(nonce, html)
        self.assertNotIn("subject-secret-from-provider", html)
        self.assertNotIn("admin@example.test", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)
        self.assertNotIn("subject-secret-from-provider", log_text)
        self.assertNotIn("admin@example.test", log_text)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", log_text)
        self.assertNotIn("Oracle", log_text)
        self.assertNotIn("OCI", log_text)

    def test_auth_callback_fails_closed_when_server_side_role_lookup_is_unavailable(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        def role_membership_resolver(*, claims: dict[str, object], required_role: str) -> dict[str, object]:
            return {
                "status": "unavailable",
                "role": required_role,
                "failure_class": "identity_domain_forbidden",
                "contains_credentials": False,
                "tokens_returned": False,
                "claims_exposed": False,
                "provider_details_exposed": False,
            }

        app = NaCLocalWebApp(
            REPO_ROOT,
            secret_text_provider=lambda _secret_id: "unit-test-client-secret",
            role_membership_resolver=role_membership_resolver,
        )
        nonce = "nonce-secret-for-id-token"
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )
        exchange_result = {
            "status": "verified",
            "mode": "server_side_token_exchange",
            "live_token_exchange_performed": True,
            "claims": {
                "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "sub": "subject-secret-from-provider",
                "email": "admin@example.test",
            },
        }

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: exchange_result["claims"],
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value=exchange_result,
            create=True,
        ), self.assertLogs("nac_web.server", level="INFO") as logs:
            response = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
        html = response.body.decode("utf-8")
        log_text = "\n".join(logs.output)

        self.assertEqual(response.status, 200)
        self.assertNotIn("Set-Cookie", response.headers)
        self.assertIn("Token-Austausch: bestätigt", html)
        self.assertIn("Token-Prüfung: bestätigt", html)
        self.assertIn("Rollenprüfung: Berechtigung offen", html)
        self.assertIn("Sitzung offen", html)
        self.assertIn("role_gate_reason=server_membership_unavailable", log_text)
        self.assertIn("role_lookup_detail=identity_domain_forbidden", log_text)
        self.assertIn("session_cookie=false", log_text)
        self.assertNotIn("identity_domain_forbidden", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, html)
        self.assertNotIn(nonce, html)
        self.assertNotIn("subject-secret-from-provider", html)
        self.assertNotIn("admin@example.test", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_sets_secure_session_cookie_after_verified_role_gate(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
        nonce = "nonce-secret-for-id-token"
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )
        exchange_result = {
            "status": "verified",
            "mode": "server_side_token_exchange",
            "live_token_exchange_performed": True,
            "claims": {
                "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
                "email": "admin@example.test",
            },
        }

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key",
                "NAC_SESSION_TTL_SECONDS": "600",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: exchange_result["claims"],
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value=exchange_result,
            create=True,
        ):
            response = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
            status, content_type, body = response
            admin_status, _admin_content_type, _admin_body = app.handle("/admin/onboarding")
        html = body.decode("utf-8")
        set_cookie = response.headers["Set-Cookie"]

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Sitzung vorbereitet", html)
        self.assertIn("Startstatus freigegeben", html)
        self.assertIn('href="/workspace"', html)
        self.assertIn("Vollständiger Arbeitsbereich bleibt geschlossen", html)
        self.assertEqual(admin_status, 403)
        self.assertIn("__Host-nac_session=", set_cookie)
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("Secure", set_cookie)
        self.assertIn("SameSite=Lax", set_cookie)
        self.assertIn("Path=/", set_cookie)
        self.assertIn("Max-Age=600", set_cookie)
        self.assertNotIn("secret-code-from-idp", set_cookie)
        self.assertNotIn(state, set_cookie)
        self.assertNotIn(nonce, set_cookie)
        self.assertNotIn("unit-test-client-secret", set_cookie)
        self.assertNotIn("ocid1.vaultsecret", set_cookie)
        self.assertNotIn("admin@example.test", set_cookie)
        self.assertNotIn("notariat8_nac_app", set_cookie)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", set_cookie)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_persists_server_session_record_after_verified_role_gate(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        class CapturingSessionStore:
            def __init__(self) -> None:
                self.created: list[dict[str, object]] = []

            def create_session_record(self, **kwargs: object) -> dict[str, object]:
                self.created.append(dict(kwargs))
                return {"schema_version": "nac.server-session/v0.1", "session_id_exposed": False}

            def get_session_record(self, _session_id: str) -> dict[str, object] | None:
                return None

        store = CapturingSessionStore()
        app = NaCLocalWebApp(
            REPO_ROOT,
            secret_text_provider=lambda _secret_id: "unit-test-client-secret",
            session_store=store,
        )
        nonce = "nonce-secret-for-id-token"
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )
        exchange_result = {
            "status": "verified",
            "mode": "server_side_token_exchange",
            "live_token_exchange_performed": True,
            "claims": {
                "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
                "email": "admin@example.test",
                "sub": "subject-secret-from-provider",
            },
        }

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key",
                "NAC_SESSION_TTL_SECONDS": "600",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: exchange_result["claims"],
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value=exchange_result,
            create=True,
        ):
            response = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
        html = response.body.decode("utf-8")
        set_cookie = response.headers["Set-Cookie"]
        payload = _session_cookie_payload(set_cookie.split(";", 1)[0])

        self.assertEqual(response.status, 200)
        self.assertEqual(len(store.created), 1)
        created = store.created[0]
        self.assertEqual(created["session_id"], payload["sid"])
        self.assertEqual(created["tenant_slug"], "myjur")
        self.assertEqual(created["role_class"], "nac-tenant-admin")
        self.assertEqual(created["usecase_slug"], "immobilienkaufvertrag")
        self.assertEqual(created["purpose"], "portal-start")
        self.assertEqual(created["issued_at"], payload["iat"])
        self.assertEqual(created["expires_at"], payload["exp"])
        self.assertNotEqual(created["subject_hash"], "subject-secret-from-provider")
        serialized_created = json.dumps(created, sort_keys=True)
        self.assertNotIn("subject-secret-from-provider", serialized_created)
        self.assertNotIn("admin@example.test", serialized_created)
        self.assertNotIn("secret-code-from-idp", serialized_created)
        self.assertNotIn(state, serialized_created)
        self.assertNotIn(nonce, serialized_created)
        self.assertNotIn("subject-secret-from-provider", html)
        self.assertNotIn("admin@example.test", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_keeps_protected_startstatus_closed_without_session_cookie(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
        nonce = "nonce-secret-for-id-token"
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )
        exchange_result = {
            "status": "verified",
            "mode": "server_side_token_exchange",
            "live_token_exchange_performed": True,
            "claims": {
                "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
                "email": "admin@example.test",
            },
        }

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY": "",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: exchange_result["claims"],
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value=exchange_result,
            create=True,
        ):
            response = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
            status, content_type, body = response
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertNotIn("Set-Cookie", response.headers)
        self.assertIn("Sitzung offen", html)
        self.assertIn("Arbeitsbereich bleibt geschlossen", html)
        self.assertNotIn("Startstatus freigegeben", html)
        self.assertNotIn('href="/workspace"', html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, html)
        self.assertNotIn(nonce, html)
        self.assertNotIn("admin@example.test", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_workspace_requires_signed_session_cookie(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        with patch.dict(
            os.environ,
            {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"},
            clear=False,
        ):
            status, content_type, body = app.handle("/workspace")
        html = body.decode("utf-8")

        self.assertEqual(status, 401)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("notariat8 Anmeldung erforderlich", html)
        self.assertIn("Keine Mandatsdaten geladen", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)
        self.assertNotIn("token", html.lower())
        self.assertNotIn("claim", html.lower())

    def test_workspace_requires_server_session_store_even_with_valid_session_cookie(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=lambda _secret_id: "unit-test-client-secret")
        nonce = "nonce-secret-for-id-token"
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
            nonce=nonce,
        )
        exchange_result = {
            "status": "verified",
            "mode": "server_side_token_exchange",
            "live_token_exchange_performed": True,
            "claims": {
                "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "aud": "notariat8_nac_app",
                "nonce": nonce,
                "groups": ["nac-tenant-admin"],
                "email": "admin@example.test",
            },
        }

        with patch.dict(
            os.environ,
            {
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
                "NAC_OIDC_CLIENT_SECRET_REF": "ocid1.vaultsecret.oc1.eu-frankfurt-1.client-secret",
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key",
                "NAC_SESSION_TTL_SECONDS": "600",
            },
            clear=False,
        ), patch.object(
            nac_server,
            "_auth_callback_id_token_verifier",
            return_value=lambda _id_token: exchange_result["claims"],
            create=True,
        ), patch.object(
            nac_server,
            "exchange_oidc_authorization_code",
            return_value=exchange_result,
            create=True,
        ):
            callback_response = app.handle(f"/auth/callback?code=secret-code-from-idp&state={state}")
            cookie_header = callback_response.headers["Set-Cookie"].split(";", 1)[0]
            status, content_type, body = app.handle(
                "/workspace",
                headers={"Cookie": cookie_header},
            )
        html = body.decode("utf-8")

        self.assertEqual(status, 401)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("notariat8 Start", html)
        self.assertIn("notariat8 Anmeldung erforderlich", html)
        self.assertIn("Sitzung nicht geprüft", html)
        self.assertIn("Keine Mandatsdaten geladen", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn(state, html)
        self.assertNotIn(nonce, html)
        self.assertNotIn(cookie_header, html)
        self.assertNotIn("unit-test-client-secret", html)
        self.assertNotIn("ocid1.vaultsecret", html)
        self.assertNotIn("admin@example.test", html)
        self.assertNotIn("notariat8_nac_app", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("Oracle", html)

    def test_workspace_requires_q2q_role_case_and_purpose_binding_after_session(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary
        from nac_identity.session_store import MappingSessionStoreAdapter

        session = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256("nonce-from-id-token".encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                    "aud": "notariat8_nac_app",
                    "nonce": "nonce-from-id-token",
                    "groups": ["nac-notary"],
                    "email": "notar@example.test",
                },
            },
            expected_issuer="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            expected_audience="notariat8_nac_app",
            required_role="nac-notary",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = session["session"]["set_cookie"].split(";", 1)[0]
        payload = _session_cookie_payload(cookie_header)
        app = NaCLocalWebApp(
            REPO_ROOT,
            session_store=MappingSessionStoreAdapter(
                {
                    payload["sid"]: {
                        "schema_version": "nac.server-session/v0.1",
                        "session_id": payload["sid"],
                        "issued_at": payload["iat"],
                        "expires_at": payload["exp"],
                        "revoked_at": None,
                        "audit_event_id": "audit-event-1",
                        "contains_credentials": False,
                        "tokens_stored": False,
                        "claims_stored": False,
                        "tenant_bound": True,
                        "subject_bound": True,
                        "role_bound": True,
                        "case_bound": False,
                        "purpose_bound": True,
                    }
                }
            ),
        )

        headers = {
            "Cookie": cookie_header,
            "X-NaC-Role": "nac-notary",
            "X-NaC-Tenant-Bound": "true",
        }

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            status, content_type, body = app.handle("/workspace", headers=headers)
        html = body.decode("utf-8")

        self.assertEqual(status, 403)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Berechtigungsprüfung offen", html)
        self.assertIn("Vorgangsbindung fehlt", html)
        self.assertIn("Keine Mandatsdaten geladen", html)
        self.assertNotIn(cookie_header, html)
        self.assertNotIn("notar@example.test", html)
        self.assertNotIn("myjur", html)
        self.assertNotIn("nonce-from-id-token", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_workspace_rejects_browser_spoofed_bindings_when_server_record_has_no_bindings(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary
        from nac_identity.session_store import MappingSessionStoreAdapter

        session = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256("nonce-from-id-token".encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                    "aud": "notariat8_nac_app",
                    "nonce": "nonce-from-id-token",
                    "groups": ["nac-notary"],
                    "email": "notar@example.test",
                },
            },
            expected_issuer="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            expected_audience="notariat8_nac_app",
            required_role="nac-notary",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = session["session"]["set_cookie"].split(";", 1)[0]
        payload = _session_cookie_payload(cookie_header)
        app = NaCLocalWebApp(
            REPO_ROOT,
            session_store=MappingSessionStoreAdapter(
                {
                    payload["sid"]: {
                        "schema_version": "nac.server-session/v0.1",
                        "session_id": payload["sid"],
                        "issued_at": payload["iat"],
                        "expires_at": payload["exp"],
                        "revoked_at": None,
                        "audit_event_id": "audit-event-secret",
                        "contains_credentials": False,
                        "tokens_stored": False,
                        "claims_stored": False,
                    }
                }
            ),
        )
        spoofed_headers = {
            "Cookie": cookie_header,
            "X-NaC-Role": "nac-notary",
            "X-NaC-Role-Gate-Open": "true",
            "X-NaC-Tenant-Bound": "true",
            "X-NaC-Case-Bound": "true",
            "X-NaC-Purpose-Bound": "true",
            "X-NaC-Case-Id": "case-secret-1",
            "X-NaC-Tenant-Hint": "myjur",
            "X-NaC-Provider-Url": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
        }

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            status, content_type, body = app.handle("/workspace", headers=spoofed_headers)
        html = body.decode("utf-8")

        self.assertEqual(status, 403)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Berechtigungsprüfung offen", html)
        self.assertIn("Keine Mandatsdaten geladen", html)
        self.assertNotIn("Portal-Start bereit", html)
        self.assertNotIn("case-secret-1", html)
        self.assertNotIn("myjur", html)
        self.assertNotIn("audit-event-secret", html)
        self.assertNotIn(cookie_header, html)
        self.assertNotIn("notar@example.test", html)
        self.assertNotIn("nonce-from-id-token", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_workspace_shows_metadata_only_after_q2q_role_case_and_purpose_gate(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary
        from nac_identity.session_store import MappingSessionStoreAdapter

        session = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256("nonce-from-id-token".encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                    "aud": "notariat8_nac_app",
                    "nonce": "nonce-from-id-token",
                    "groups": ["nac-notary"],
                    "email": "notar@example.test",
                },
            },
            expected_issuer="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            expected_audience="notariat8_nac_app",
            required_role="nac-notary",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = session["session"]["set_cookie"].split(";", 1)[0]
        payload = _session_cookie_payload(cookie_header)
        app = NaCLocalWebApp(
            REPO_ROOT,
            session_store=MappingSessionStoreAdapter(
                {
                    payload["sid"]: {
                        "schema_version": "nac.server-session/v0.1",
                        "session_id": payload["sid"],
                        "issued_at": payload["iat"],
                        "expires_at": payload["exp"],
                        "revoked_at": None,
                        "audit_event_id": "audit-event-1",
                        "contains_credentials": False,
                        "tokens_stored": False,
                        "claims_stored": False,
                        "tenant_bound": True,
                        "subject_bound": True,
                        "role_bound": True,
                        "case_bound": True,
                        "purpose_bound": True,
                    }
                }
            ),
        )
        headers = {
            "Cookie": cookie_header,
            "X-NaC-Role": "nac-notary",
            "X-NaC-Tenant-Bound": "true",
            "X-NaC-Case-Bound": "true",
            "X-NaC-Purpose-Bound": "true",
            "X-NaC-Case-Id": "case-secret-1",
            "X-NaC-Tenant-Hint": "myjur",
        }

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            status, content_type, body = app.handle("/workspace", headers=headers)
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("notariat8 Portal-Start", html)
        self.assertIn("Anmeldung und Berechtigung bestätigt", html)
        self.assertIn("Portal-Start bereit", html)
        self.assertIn("Notariat, Vorgang und Zweck sind serverseitig gebunden", html)
        self.assertIn("Immobilienkaufvertrag", html)
        self.assertIn("Erster Vorgang vorbereitet", html)
        self.assertIn("Nächster sicherer Schritt", html)
        self.assertIn("BPMN-Modell vorhanden", html)
        self.assertIn("XNP/SNP-Zielpfad vorbereitet", html)
        self.assertIn("Vollzugspfad sichtbar", html)
        self.assertIn("Kritischer Pfad: externer Rücklauf", html)
        self.assertIn("Dauerband: Wochen bis Monate", html)
        self.assertIn("Der vollständige Arbeitsbereich bleibt geschlossen", html)
        self.assertIn("Keine Mandatsdaten geladen", html)
        self.assertNotIn("Geschützter Startstatus", html)
        self.assertNotIn("Demo-Schritt", html)
        self.assertNotIn("DEMO-MATTER", html)
        self.assertNotIn("DEMO-TENANT", html)
        self.assertNotIn("Grundbuchblatt", html)
        self.assertNotIn("Flurstück", html)
        self.assertNotIn("case-secret-1", html)
        self.assertNotIn("myjur", html)
        self.assertNotIn(cookie_header, html)
        self.assertNotIn("notar@example.test", html)
        self.assertNotIn("nonce-from-id-token", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_workspace_uses_server_session_bindings_without_browser_headers(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary
        from nac_identity.session_store import MappingSessionStoreAdapter

        session = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256("nonce-from-id-token".encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                    "aud": "notariat8_nac_app",
                    "nonce": "nonce-from-id-token",
                    "groups": ["nac-notary"],
                    "email": "notar@example.test",
                },
            },
            expected_issuer="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            expected_audience="notariat8_nac_app",
            required_role="nac-notary",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = session["session"]["set_cookie"].split(";", 1)[0]
        payload = _session_cookie_payload(cookie_header)
        app = NaCLocalWebApp(
            REPO_ROOT,
            session_store=MappingSessionStoreAdapter(
                {
                    payload["sid"]: {
                        "schema_version": "nac.server-session/v0.1",
                        "issued_at": payload["iat"],
                        "expires_at": payload["exp"],
                        "revoked_at": None,
                        "audit_event_id": "audit-event-1",
                        "contains_credentials": False,
                        "tokens_stored": False,
                        "claims_stored": False,
                        "tenant_bound": True,
                        "subject_bound": True,
                        "role_bound": True,
                        "case_bound": True,
                        "purpose_bound": True,
                    }
                }
            ),
        )

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            status, content_type, body = app.handle("/workspace", headers={"Cookie": cookie_header})
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("notariat8 Portal-Start", html)
        self.assertIn("Anmeldung und Berechtigung bestätigt", html)
        self.assertIn("Portal-Start bereit", html)
        self.assertIn("Immobilienkaufvertrag", html)
        self.assertIn("Erster Vorgang vorbereitet", html)
        self.assertIn("Nächster sicherer Schritt", html)
        self.assertIn("BPMN-Modell vorhanden", html)
        self.assertIn("XNP/SNP-Zielpfad vorbereitet", html)
        self.assertIn("Vollzugspfad sichtbar", html)
        self.assertIn("Ersten Vorgang als Statusansicht öffnen", html)
        self.assertIn("Keine Mandatsdaten geladen", html)
        self.assertNotIn("Geschützter Startstatus", html)
        self.assertNotIn("Demo-Schritt", html)
        self.assertNotIn("Workspace", html)
        self.assertNotIn("Tenant", html)
        self.assertNotIn("Gate", html)
        self.assertNotIn("DEMO-MATTER", html)
        self.assertNotIn("DEMO-TENANT", html)
        self.assertNotIn("Grundbuchblatt", html)
        self.assertNotIn("Flurstück", html)
        self.assertNotIn("myjur", html)
        self.assertNotIn("case-secret", html)
        self.assertNotIn(cookie_header, html)
        self.assertNotIn("notar@example.test", html)
        self.assertNotIn("nonce-from-id-token", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_workspace_links_first_matter_metadata_status_without_exposing_identifiers(self) -> None:
        app, cookie_header = _bound_workspace_app_and_cookie()

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            status, _content_type, body = app.handle("/workspace", headers={"Cookie": cookie_header})
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("Ersten Vorgang als Statusansicht öffnen", html)
        self.assertIn('href="/workspace/immobilienkaufvertrag"', html)
        self.assertNotIn("case-secret", html)
        self.assertNotIn("myjur", html)
        self.assertNotIn("audit-event-secret", html)
        self.assertNotIn(cookie_header, html)
        self.assertNotIn("notar@example.test", html)
        self.assertNotIn("notariat8_nac_app", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_first_matter_status_requires_valid_session_cookie(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            status, content_type, body = app.handle("/workspace/immobilienkaufvertrag")
        html = body.decode("utf-8")

        self.assertEqual(status, 401)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("notariat8 Anmeldung erforderlich", html)
        self.assertIn("Keine Mandatsdaten geladen", html)
        self.assertNotIn("Immobilienkaufvertrag Status", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_first_matter_status_shows_metadata_only_after_role_case_gate(self) -> None:
        app, cookie_header = _bound_workspace_app_and_cookie()
        headers = {
            "Cookie": cookie_header,
            "X-NaC-Case-Id": "case-secret-1",
            "X-NaC-Tenant-Hint": "myjur",
            "X-NaC-Provider-Url": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            "X-NaC-Callback-State": "state-secret-1",
        }

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            status, content_type, body = app.handle("/workspace/immobilienkaufvertrag", headers=headers)
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Immobilienkaufvertrag Status", html)
        self.assertIn("Vorgangsstatus ohne Mandatsdaten", html)
        self.assertIn("Aufnahme und Beteiligte", html)
        self.assertIn("Entwurf und Abstimmung", html)
        self.assertIn("Beurkundung", html)
        self.assertIn("Vollzug", html)
        self.assertIn("XNP/SNP-Kommunikation vorbereitet", html)
        self.assertIn("Grundbuch- und Registerrückläufe als externe Statuspunkte", html)
        self.assertIn("GNotKG-Prüfung erforderlich", html)
        self.assertIn("XNP/SNP-Zielpfad nur als Metadaten", html)
        self.assertIn("Kartenleser- und Signaturpfad als Bereitschaftsgrenze", html)
        self.assertIn("Fachliche Freigabe erforderlich", html)
        self.assertIn("Nachweis ohne Mandatsdaten", html)
        self.assertIn("Parallel möglich", html)
        self.assertIn("Kritischer Pfad", html)
        self.assertIn("Dauerband: Wochen bis Monate", html)
        self.assertIn("Keine Mandatsdaten geladen", html)
        self.assertIn("Vollständiger Arbeitsbereich bleibt geschlossen", html)
        self.assertIn("Nur Statusmetadaten ohne Mandatsdaten", html)
        self.assertNotIn("Live-Demo", html)
        self.assertNotIn("Demo", html)
        self.assertNotIn("DEMO-MATTER", html)
        self.assertNotIn("DEMO-TENANT", html)
        self.assertNotIn("Grundbuchblatt", html)
        self.assertNotIn("Flurstück", html)
        self.assertNotIn("Kaufpreis", html)
        self.assertNotIn("case-secret-1", html)
        self.assertNotIn("myjur", html)
        self.assertNotIn("audit-event-secret", html)
        self.assertNotIn(cookie_header, html)
        self.assertNotIn("notar@example.test", html)
        self.assertNotIn("nonce-from-id-token", html)
        self.assertNotIn("notariat8_nac_app", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("state-secret-1", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_first_matter_status_accepts_injected_atp_json_runtime_source(self) -> None:
        fixture = json.loads(FIRST_MATTER_METADATA_FIXTURE.read_text(encoding="utf-8"))
        requested_keys: list[str] = []

        def read_atp_json(object_key: str) -> dict[str, object]:
            requested_keys.append(object_key)
            return dict(fixture)

        app, cookie_header = _bound_workspace_app_and_cookie(
            AtpJsonRuntimeMetadataSource(
                read_atp_json,
                object_key="runtime/atp/notarkammer-first.json",
            )
        )

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            status, content_type, body = app.handle("/workspace/immobilienkaufvertrag", headers={"Cookie": cookie_header})
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertEqual(requested_keys, ["runtime/atp/notarkammer-first.json"])
        self.assertIn("Immobilienkaufvertrag Status", html)
        self.assertIn("Vorgangsstatus ohne Mandatsdaten", html)
        self.assertIn("Keine Mandatsdaten geladen", html)
        self.assertNotIn("runtime/atp", html)
        self.assertNotIn("DEMO-MATTER", html)
        self.assertNotIn("DEMO-TENANT", html)
        self.assertNotIn(cookie_header, html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_first_matter_status_fails_closed_when_runtime_source_is_unavailable(self) -> None:
        class FailingRuntimeMetadataSource:
            def load_first_matter_metadata(self) -> dict[str, object]:
                raise RuntimeError("runtime/secret/object-key token-secret")

        app, cookie_header = _bound_workspace_app_and_cookie()
        app.first_matter_runtime_metadata_source = FailingRuntimeMetadataSource()

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            status, content_type, body = app.handle("/workspace/immobilienkaufvertrag", headers={"Cookie": cookie_header})
        html = body.decode("utf-8")

        self.assertEqual(status, 503)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Vorgangsstatus vorübergehend geschlossen", html)
        self.assertIn("Runtime-Quelle nicht freigegeben", html)
        self.assertIn("Keine Mandatsdaten geladen", html)
        self.assertIn("Vollständiger Arbeitsbereich bleibt geschlossen", html)
        self.assertNotIn("RuntimeError", html)
        self.assertNotIn("runtime/secret", html)
        self.assertNotIn("token-secret", html)
        self.assertNotIn("Immobilienkaufvertrag Status", html)
        self.assertNotIn(cookie_header, html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_first_matter_status_display_uses_packaged_runtime_source(self) -> None:
        captured: dict[str, object] = {}

        def build_runtime_display(*, source: object) -> dict[str, object]:
            captured["source_type"] = type(source).__name__
            return {
                "schema_version": "nac.runtime-status-presenter/v0.1",
                "title": "Immobilienkaufvertrag Status",
            }

        with patch.object(
            nac_server,
            "build_first_matter_status_display_from_metadata_source",
            side_effect=build_runtime_display,
        ):
            display = nac_server._first_matter_status_display()

        self.assertEqual(display["title"], "Immobilienkaufvertrag Status")
        self.assertEqual(captured["source_type"], "PackagedRuntimeMetadataSource")

    def test_workspace_redacts_gate_reason_context_values(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary
        from nac_identity.session_store import MappingSessionStoreAdapter

        session = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256("nonce-from-id-token".encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                    "aud": "notariat8_nac_app",
                    "nonce": "nonce-from-id-token",
                    "groups": ["nac-notary"],
                    "email": "notar@example.test",
                },
            },
            expected_issuer="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            expected_audience="notariat8_nac_app",
            required_role="nac-notary",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = session["session"]["set_cookie"].split(";", 1)[0]
        payload = _session_cookie_payload(cookie_header)
        app = NaCLocalWebApp(
            REPO_ROOT,
            session_store=MappingSessionStoreAdapter(
                {
                    payload["sid"]: {
                        "schema_version": "nac.server-session/v0.1",
                        "session_id": payload["sid"],
                        "issued_at": payload["iat"],
                        "expires_at": payload["exp"],
                        "revoked_at": None,
                        "audit_event_id": "audit-event-secret",
                        "contains_credentials": False,
                        "tokens_stored": False,
                        "claims_stored": False,
                        "tenant_bound": True,
                        "subject_bound": True,
                        "role_bound": True,
                        "case_bound": False,
                        "purpose_bound": True,
                    }
                }
            ),
        )
        headers = {
            "Cookie": cookie_header,
            "X-NaC-Role": "nac-notary",
            "X-NaC-Tenant-Bound": "true",
            "X-NaC-Case-Bound": "false",
            "X-NaC-Purpose-Bound": "true",
            "X-NaC-Case-Id": "case-secret-1",
            "X-NaC-Tenant-Hint": "myjur",
            "X-NaC-Provider-Url": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            "X-NaC-Callback-State": "state-secret-1",
        }

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            status, content_type, body = app.handle("/workspace", headers=headers)
        html = body.decode("utf-8")

        self.assertEqual(status, 403)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Vorgangsbindung fehlt", html)
        self.assertIn("Keine Mandatsdaten geladen", html)
        self.assertNotIn("case-secret-1", html)
        self.assertNotIn("myjur", html)
        self.assertNotIn("audit-event-secret", html)
        self.assertNotIn(cookie_header, html)
        self.assertNotIn("notar@example.test", html)
        self.assertNotIn("nonce-from-id-token", html)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", html)
        self.assertNotIn("state-secret-1", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_auth_callback_validates_vault_backed_signed_state_without_leaking_reference(self) -> None:
        from nac_identity.oidc_state import build_signed_state

        requested_secret_ids: list[str] = []

        def secret_text_provider(secret_id: str) -> str:
            requested_secret_ids.append(secret_id)
            return "unit-test-state-signing-key"

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=secret_text_provider)
        state = build_signed_state(
            tenant_hint="myjur",
            signing_key="unit-test-state-signing-key",
        )
        secret_ocid = "ocid1.vaultsecret.oc1.eu-frankfurt-1.state-key"

        with patch.dict(
            os.environ,
            {"NAC_OIDC_STATE_SIGNING_KEY_SECRET_OCID": secret_ocid},
            clear=False,
        ):
            status, content_type, body = app.handle(
                f"/auth/callback?code=secret-code-from-idp&state={state}"
            )
            admin_status, _admin_content_type, admin_body = app.handle("/admin/onboarding")
        html = body.decode("utf-8")
        admin_html = admin_body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertEqual(requested_secret_ids, [secret_ocid])
        self.assertIn("Sicherheitsprüfung bestätigt", html)
        self.assertIn("Arbeitsbereich bleibt geschlossen", html)
        self.assertNotIn("unit-test-state-signing-key", html)
        self.assertNotIn(secret_ocid, html)
        self.assertNotIn(state, html)
        self.assertEqual(admin_status, 403)
        self.assertIn("notariat8 Anmeldung erforderlich", admin_html)

    def test_auth_callback_fails_closed_when_vault_state_key_is_unavailable(self) -> None:
        app = NaCLocalWebApp(
            REPO_ROOT,
            secret_text_provider=lambda _secret_id: (_ for _ in ()).throw(RuntimeError("vault down")),
        )

        with patch.dict(
            os.environ,
            {"NAC_OIDC_STATE_SIGNING_KEY_SECRET_OCID": "ocid1.vaultsecret.oc1.eu-frankfurt-1.state-key"},
            clear=False,
        ):
            status, content_type, body = app.handle(
                "/auth/callback?code=secret-code-from-idp&state=attacker-state"
            )
        html = body.decode("utf-8")

        self.assertEqual(status, 400)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Anmeldung nicht abgeschlossen", html)
        self.assertNotIn("vault down", html)
        self.assertNotIn("ocid1.vaultsecret", html)
        self.assertNotIn("secret-code-from-idp", html)
        self.assertNotIn("attacker-state", html)

    def test_auth_callback_fails_safely_without_provider_error_details(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/auth/callback?error=access_denied&error_description=provider-details"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 400)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Anmeldung nicht abgeschlossen", html)
        self.assertIn("Bitte starten Sie die Anmeldung erneut", html)
        self.assertNotIn("access_denied", html)
        self.assertNotIn("provider-details", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_app_serves_login_intent_api_without_leaking_tenant_hint_to_authorize_url(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
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

    def test_login_intent_api_rejects_placeholder_identity_domain_url(self) -> None:
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

        self.assertEqual(status, 400)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        self.assertEqual(payload["error"], "identity_domain_url_placeholder")

    def test_login_intent_api_rejects_placeholder_client_id(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "nac-local-preview",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
            },
        ):
            status, content_type, body = app.handle("/api/tenant/login-intent?tenant_hint=notariat-musterstadt")
        payload = json.loads(body.decode("utf-8"))

        self.assertEqual(status, 400)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        self.assertEqual(payload["error"], "client_id_placeholder")

    def test_app_serves_login_intent_api_with_signed_state_when_runtime_key_is_configured(self) -> None:
        from nac_identity.oidc_state import validate_signed_state

        app = NaCLocalWebApp(REPO_ROOT)

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "nac-web-app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_OIDC_STATE_SIGNING_KEY": "unit-test-state-signing-key",
            },
        ):
            status, content_type, body = app.handle("/api/tenant/login-intent?tenant_hint=notariat-musterstadt")
        payload = json.loads(body.decode("utf-8"))
        validation = validate_signed_state(
            payload["oidc"]["state"],
            signing_key="unit-test-state-signing-key",
        )
        serialized = json.dumps(payload, sort_keys=True)

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        self.assertEqual(payload["state_binding"]["status"], "signed")
        self.assertTrue(payload["state_binding"]["nonce_bound"])
        self.assertEqual(validation["status"], "valid")
        self.assertEqual(validation["tenant_hint"], "notariat-musterstadt")
        self.assertTrue(validation["nonce_bound"])
        self.assertEqual(
            validation["nonce_hash"],
            hashlib.sha256(payload["oidc"]["nonce"].encode("utf-8")).hexdigest(),
        )
        self.assertNotIn("unit-test-state-signing-key", serialized)
        self.assertNotIn("client_secret", serialized)

    def test_app_serves_login_intent_api_with_vault_backed_signed_state(self) -> None:
        from nac_identity.oidc_state import validate_signed_state

        requested_secret_ids: list[str] = []

        def secret_text_provider(secret_id: str) -> str:
            requested_secret_ids.append(secret_id)
            return "unit-test-state-signing-key"

        app = NaCLocalWebApp(REPO_ROOT, secret_text_provider=secret_text_provider)
        secret_ocid = "ocid1.vaultsecret.oc1.eu-frankfurt-1.state-key"

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "nac-web-app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_OIDC_STATE_SIGNING_KEY_SECRET_OCID": secret_ocid,
            },
        ):
            status, content_type, body = app.handle("/api/tenant/login-intent?tenant_hint=notariat-musterstadt")
        payload = json.loads(body.decode("utf-8"))
        validation = validate_signed_state(
            payload["oidc"]["state"],
            signing_key="unit-test-state-signing-key",
        )
        serialized = json.dumps(payload, sort_keys=True)

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        self.assertEqual(requested_secret_ids, [secret_ocid])
        self.assertEqual(payload["state_binding"]["status"], "signed")
        self.assertTrue(payload["state_binding"]["nonce_bound"])
        self.assertEqual(validation["status"], "valid")
        self.assertEqual(validation["tenant_hint"], "notariat-musterstadt")
        self.assertTrue(validation["nonce_bound"])
        self.assertEqual(
            validation["nonce_hash"],
            hashlib.sha256(payload["oidc"]["nonce"].encode("utf-8")).hexdigest(),
        )
        self.assertNotIn("unit-test-state-signing-key", serialized)
        self.assertNotIn(secret_ocid, serialized)
        self.assertNotIn("client_secret", serialized)

    def test_login_intent_api_fails_closed_when_vault_state_key_is_unavailable(self) -> None:
        app = NaCLocalWebApp(
            REPO_ROOT,
            secret_text_provider=lambda _secret_id: (_ for _ in ()).throw(RuntimeError("vault down")),
        )

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "nac-web-app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_OIDC_STATE_SIGNING_KEY_SECRET_OCID": "ocid1.vaultsecret.oc1.eu-frankfurt-1.state-key",
            },
        ):
            status, content_type, body = app.handle("/api/tenant/login-intent?tenant_hint=notariat-musterstadt")
        payload = json.loads(body.decode("utf-8"))

        self.assertEqual(status, 400)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        self.assertEqual(payload["error"], "state_signing_key_unavailable")
        self.assertNotIn("vault down", json.dumps(payload, sort_keys=True))
        self.assertNotIn("ocid1.vaultsecret", json.dumps(payload, sort_keys=True))

    def test_login_intent_api_rejects_caller_supplied_oidc_config(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle(
            "/api/tenant/login-intent"
            "?tenant_hint=notariat-musterstadt"
            "&identity_domain_url=https%3A%2F%2Fidcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com"
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
