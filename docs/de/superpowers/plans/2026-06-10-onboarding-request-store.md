# Onboarding Request Store Implementation Plan

> **Für agentische Worker:** ERFORDERLICHE SUB-SKILL: Nutze superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans, um diesen Plan Schritt für Schritt umzusetzen. Schritte nutzen Checkboxen (`- [ ]`) zur Nachverfolgung.

**Ziel:** NaC bekommt einen echten Onboarding-Request-Vertrag mit fail-closed Store-Grenze, Kundenseite `Einrichtung anfragen` und Admin-Queue auf Basis realer Request-Objekte.

**Architektur:** Die App definiert einen Store-unabhängigen Request-Vertrag in `nac_identity`. Produktive Persistenz wird nicht lokal simuliert; ohne Store-Konfiguration antwortet POST fail-closed. Die OCI Function bleibt read-only bis auf die explizit erlaubte Route `POST /onboarding/requests`.

**Tech Stack:** Python stdlib, `unittest`, bestehender NaC-Webserver, OCI Functions Adapter, spätere ATP-Integration über oci-landing-zone#44.

---

### Aufgabe 1: Request-Modell Und Store-Grenze

**Dateien:**
- Erstellen: `src/nac_identity/onboarding_requests.py`
- Ändern: `src/nac_identity/__init__.py`
- Test: `tests/test_onboarding_requests.py`

- [x] **Schritt 1: Fehlende Tests schreiben**

```python
def test_build_onboarding_request_creates_stable_non_secret_id(self) -> None:
    request = build_onboarding_request(
        domain="kanzlei-notariat.example",
        tenant_slug="kanzlei-notariat",
        admin_email="verwaltung@kanzlei-notariat.example",
        dns_status="verified",
        now="2026-06-10T00:00:00Z",
    )
    self.assertEqual(request["schema_version"], "nac.onboarding-request/v0.1")
    self.assertEqual(request["request_id"], "onr_kanzlei_notariat_20260610_000000")
    self.assertEqual(request["invitation_status"], "not_sent")
    self.assertNotIn("verwaltung", request["request_id"])
```

```python
def test_disabled_store_fails_closed_without_writing(self) -> None:
    store = DisabledOnboardingRequestStore()
    with self.assertRaises(OnboardingRequestStoreDisabled):
        store.create_request({"request_id": "onr_kanzlei_notariat_20260610_000000"})
```

- [x] **Schritt 2: Zieltest rot ausführen**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_onboarding_requests
```

Erwartung: Importfehler, weil Modul und Klassen noch fehlen.

- [x] **Schritt 3: Minimale Implementierung**

`onboarding_requests.py` definiert:

```python
class OnboardingRequestStoreDisabled(RuntimeError):
    pass

class DisabledOnboardingRequestStore:
    def create_request(self, payload: dict) -> dict:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")

    def get_request(self, request_id: str) -> dict | None:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")

    def list_requests(self, limit: int = 50) -> list[dict]:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")
```

`build_onboarding_request(...)` normalisiert Domain, Tenant-Referenz und E-Mail,
nutzt eine deterministische nicht-geheime `request_id` aus Slug und Zeitstempel
und gibt keine Credentials aus.

- [x] **Schritt 4: Tests grün ausführen**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_onboarding_requests
```

Erwartung: OK.

### Aufgabe 2: Customer API Und DNS-Erfolgsseite

**Dateien:**
- Ändern: `src/nac_web/server.py`
- Test: `tests/test_nac_web.py`

- [x] **Schritt 1: Fehlende Webtests schreiben**

```python
def test_customer_dns_success_offers_onboarding_request_without_provider_terms(self) -> None:
    html = app.handle("/onboarding/dns-check?audience=customer&domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=verwaltung@kanzlei-notariat.example")[2].decode("utf-8")
    self.assertIn("Einrichtung anfragen", html)
    self.assertIn("/onboarding/requests", html)
    self.assertNotIn("OCI", html)
    self.assertNotIn("NaC", html)
```

```python
def test_onboarding_request_post_fails_closed_when_store_disabled(self) -> None:
    status, content_type, body = app.handle_post(
        "/onboarding/requests",
        b"domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=verwaltung%40kanzlei-notariat.example",
    )
    self.assertEqual(status, 503)
    self.assertIn(b"onboarding_request_store_disabled", body)
```

- [x] **Schritt 2: Tests rot ausführen**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_customer_dns_success_offers_onboarding_request_without_provider_terms tests.test_nac_web.NaCLocalWebTests.test_onboarding_request_post_fails_closed_when_store_disabled
```

Erwartung: FAIL, weil Route/Formular noch fehlen.

- [x] **Schritt 3: Webserver minimal erweitern**

`handle_post` akzeptiert `/onboarding/requests`, parst URL-encoded Bodies und
ruft den Store. Bei `OnboardingRequestStoreDisabled` antwortet es 503 JSON und
schreibt nichts.

Die öffentliche DNS-Erfolgsseite ergänzt ein Formular:

```html
<form method="post" action="/onboarding/requests">
  <input type="hidden" name="domain" value="kanzlei-notariat.example">
  <input type="hidden" name="tenant_slug" value="kanzlei-notariat">
  <input type="hidden" name="admin_email" value="verwaltung@kanzlei-notariat.example">
  <button type="submit">Einrichtung anfragen</button>
</form>
```

- [x] **Schritt 4: Zieltests grün ausführen**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_customer_dns_success_offers_onboarding_request_without_provider_terms tests.test_nac_web.NaCLocalWebTests.test_onboarding_request_post_fails_closed_when_store_disabled
```

Erwartung: OK.

### Aufgabe 3: Function POST-Ausnahme

**Dateien:**
- Ändern: `src/nac_web/oci_functions.py`
- Test: `tests/test_oci_functions_adapter.py`

- [x] **Schritt 1: Fehlende Adaptertests schreiben**

```python
def test_allows_only_onboarding_request_post(self) -> None:
    result = dispatch_oci_function_request(
        FakeFunctionContext(request_url="/onboarding/requests", method="POST"),
        io.BytesIO(b"domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=verwaltung%40kanzlei-notariat.example"),
        repo_root=REPO_ROOT,
    )
    self.assertEqual(result.status_code, 503)
    self.assertIn(b"onboarding_request_store_disabled", result.body)
```

```python
def test_still_rejects_other_post_routes(self) -> None:
    result = dispatch_oci_function_request(
        FakeFunctionContext(request_url="/api/gnotkg/quote", method="POST"),
        FailingBody(),
        repo_root=REPO_ROOT,
    )
    self.assertEqual(result.status_code, 405)
```

- [x] **Schritt 2: Tests rot ausführen**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_allows_only_onboarding_request_post tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_still_rejects_other_post_routes
```

Erwartung: FAIL für erlaubte POST-Ausnahme, bestehende Ablehnung bleibt.

- [x] **Schritt 3: Adapter minimal erweitern**

`dispatch_oci_function_request` erlaubt nur:

```python
elif method == "POST" and _is_exposed_post_route(request_url):
    status, content_type, response_body = app.handle_post(request_url, data.read() if data else b"")
```

`_is_exposed_post_route` akzeptiert ausschließlich `/onboarding/requests`.

- [x] **Schritt 4: Adaptertests grün ausführen**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter
```

Erwartung: OK.

### Aufgabe 4: Admin-Queue Für Request-Objekte

**Dateien:**
- Ändern: `src/nac_web/server.py`
- Test: `tests/test_nac_web.py`

- [x] **Schritt 1: Admin-Queue-Test schreiben**

```python
def test_admin_queue_can_render_real_onboarding_requests(self) -> None:
    request = build_onboarding_request(
        domain="kanzlei-notariat.example",
        tenant_slug="kanzlei-notariat",
        admin_email="verwaltung@kanzlei-notariat.example",
        dns_status="verified",
        now="2026-06-10T00:00:00Z",
    )
    html = build_admin_onboarding_page(requests=[request])
    self.assertIn("onr_kanzlei_notariat_20260610_000000", html)
    self.assertIn("kanzlei-notariat.example", html)
    self.assertIn("verwaltung@kanzlei-notariat.example", html)
    self.assertIn("E-Mail-Prüfung", html)
```

- [x] **Schritt 2: Test rot ausführen**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_admin_queue_can_render_real_onboarding_requests
```

Erwartung: FAIL, weil `build_admin_onboarding_page` keine Request-Liste annimmt.

- [x] **Schritt 3: Admin-Queue minimal erweitern**

`build_admin_onboarding_page(requests: list[dict] | None = None)` rendert echte
Requests, wenn sie übergeben werden. Ohne Store bleibt die Seite mit einem
klaren Hinweis sichtbar, dass die produktive Queue noch nicht aktiviert ist.

- [x] **Schritt 4: Webtests grün ausführen**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web
```

Erwartung: OK.

### Aufgabe 5: Vollständige Verifikation Und PR

**Dateien:**
- Prüfen: `src/nac_identity/onboarding_requests.py`
- Prüfen: `src/nac_web/server.py`
- Prüfen: `src/nac_web/oci_functions.py`
- Prüfen: `tests/test_onboarding_requests.py`
- Prüfen: `tests/test_nac_web.py`
- Prüfen: `tests/test_oci_functions_adapter.py`

- [x] **Schritt 1: Vollständige Tests und Gates ausführen**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
git diff --check
GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Erwartung: Tests OK, Whitespace OK, Quality Gate PASSED.

- [ ] **Schritt 2: Commit und Protected PR**

```bash
git add src/nac_identity/onboarding_requests.py src/nac_identity/__init__.py src/nac_web/server.py src/nac_web/oci_functions.py tests/test_onboarding_requests.py tests/test_nac_web.py tests/test_oci_functions_adapter.py docs/de/superpowers/specs/2026-06-10-onboarding-request-store-design.md docs/en/superpowers/specs/2026-06-10-onboarding-request-store-design.md docs/de/superpowers/plans/2026-06-10-onboarding-request-store.md docs/en/superpowers/plans/2026-06-10-onboarding-request-store.md
git commit -m "feat: add onboarding request contract"
git push -u origin agent/83-onboarding-request-store
gh pr create --repo notariat8/NaC --base main --head agent/83-onboarding-request-store --title "P1: Add onboarding request contract" --body "Closes #83. Linked notariat8/oci-landing-zone#44. Deployment requires Owner Release Approval after merge. Productive ATP apply is out of scope."
```

Erwartung: PR offen, Checks grün, kein OCI-Write.
