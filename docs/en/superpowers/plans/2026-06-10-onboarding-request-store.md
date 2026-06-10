# Onboarding Request Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NaC gets a real onboarding-request contract with a fail-closed store boundary, customer-facing `Einrichtung anfragen`, and an admin queue based on real request objects.

**Architecture:** The app defines a store-independent request contract in `nac_identity`. Productive persistence is not simulated locally; without store configuration, POST fails closed. The OCI Function remains read-only except for the explicitly allowed route `POST /onboarding/requests`.

**Tech Stack:** Python stdlib, `unittest`, existing NaC web server, OCI Functions adapter, later ATP integration through oci-landing-zone#44.

---

### Task 1: Request Model And Store Boundary

**Files:**
- Create: `src/nac_identity/onboarding_requests.py`
- Modify: `src/nac_identity/__init__.py`
- Test: `tests/test_onboarding_requests.py`

- [x] **Step 1: Write failing tests**

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

- [x] **Step 2: Run the target test red**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_onboarding_requests
```

Expected: import failure because the module and classes do not exist yet.

- [x] **Step 3: Minimal implementation**

`onboarding_requests.py` defines:

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

`build_onboarding_request(...)` normalizes domain, tenant reference and email,
uses a deterministic non-secret `request_id` from slug and timestamp, and emits
no credentials.

- [x] **Step 4: Run tests green**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_onboarding_requests
```

Expected: OK.

### Task 2: Customer API And DNS Success Page

**Files:**
- Modify: `src/nac_web/server.py`
- Test: `tests/test_nac_web.py`

- [x] **Step 1: Write failing web tests**

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

- [x] **Step 2: Run tests red**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_customer_dns_success_offers_onboarding_request_without_provider_terms tests.test_nac_web.NaCLocalWebTests.test_onboarding_request_post_fails_closed_when_store_disabled
```

Expected: FAIL because route and form do not exist yet.

- [x] **Step 3: Minimal web server extension**

`handle_post` accepts `/onboarding/requests`, parses URL-encoded bodies and
calls the store. On `OnboardingRequestStoreDisabled`, it responds with 503 JSON
and writes nothing.

The public DNS success page adds a form:

```html
<form method="post" action="/onboarding/requests">
  <input type="hidden" name="domain" value="kanzlei-notariat.example">
  <input type="hidden" name="tenant_slug" value="kanzlei-notariat">
  <input type="hidden" name="admin_email" value="verwaltung@kanzlei-notariat.example">
  <button type="submit">Einrichtung anfragen</button>
</form>
```

- [x] **Step 4: Run target tests green**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_customer_dns_success_offers_onboarding_request_without_provider_terms tests.test_nac_web.NaCLocalWebTests.test_onboarding_request_post_fails_closed_when_store_disabled
```

Expected: OK.

### Task 3: Function POST Exception

**Files:**
- Modify: `src/nac_web/oci_functions.py`
- Test: `tests/test_oci_functions_adapter.py`

- [x] **Step 1: Write failing adapter tests**

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

- [x] **Step 2: Run tests red**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_allows_only_onboarding_request_post tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_still_rejects_other_post_routes
```

Expected: FAIL for the allowed POST exception, existing rejection remains.

- [x] **Step 3: Minimal adapter extension**

`dispatch_oci_function_request` allows only:

```python
elif method == "POST" and _is_exposed_post_route(request_url):
    status, content_type, response_body = app.handle_post(request_url, data.read() if data else b"")
```

`_is_exposed_post_route` accepts only `/onboarding/requests`.

- [x] **Step 4: Run adapter tests green**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter
```

Expected: OK.

### Task 4: Admin Queue For Request Objects

**Files:**
- Modify: `src/nac_web/server.py`
- Test: `tests/test_nac_web.py`

- [x] **Step 1: Write admin queue test**

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

- [x] **Step 2: Run test red**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_admin_queue_can_render_real_onboarding_requests
```

Expected: FAIL because `build_admin_onboarding_page` does not accept a request
list yet.

- [x] **Step 3: Minimal admin queue extension**

`build_admin_onboarding_page(requests: list[dict] | None = None)` renders real
requests when passed. Without store configuration, the page remains visible
with a clear note that the productive queue is not enabled yet.

- [x] **Step 4: Run web tests green**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web
```

Expected: OK.

### Task 5: Full Verification And PR

**Files:**
- Verify: `src/nac_identity/onboarding_requests.py`
- Verify: `src/nac_web/server.py`
- Verify: `src/nac_web/oci_functions.py`
- Verify: `tests/test_onboarding_requests.py`
- Verify: `tests/test_nac_web.py`
- Verify: `tests/test_oci_functions_adapter.py`

- [x] **Step 1: Run full tests and gates**

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
git diff --check
GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: tests OK, whitespace OK, quality gate PASSED.

- [x] **Step 2: Commit and open protected PR**

```bash
git add src/nac_identity/onboarding_requests.py src/nac_identity/__init__.py src/nac_web/server.py src/nac_web/oci_functions.py tests/test_onboarding_requests.py tests/test_nac_web.py tests/test_oci_functions_adapter.py docs/de/superpowers/specs/2026-06-10-onboarding-request-store-design.md docs/en/superpowers/specs/2026-06-10-onboarding-request-store-design.md docs/de/superpowers/plans/2026-06-10-onboarding-request-store.md docs/en/superpowers/plans/2026-06-10-onboarding-request-store.md
git commit -m "feat: add onboarding request contract"
git push -u origin agent/83-onboarding-request-store
gh pr create --repo notariat8/NaC --base main --head agent/83-onboarding-request-store --title "P1: Add onboarding request contract" --body "Closes #83. Linked notariat8/oci-landing-zone#44. Deployment requires Owner Release Approval after merge. Productive ATP apply is out of scope."
```

Expected: PR open, checks green, no OCI write.
