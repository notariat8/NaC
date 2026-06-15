# Minimal Public GET Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make customer-facing public GET routes use a minimal OCI Functions runtime path that avoids booting the full `NaCLocalWebApp` for simple public requests.

**Architecture:** Add a focused public runtime module that owns only the public GET/HEAD routes: `/healthz`, `/api/tenant/login-intent`, `/onboarding/readiness`, and `/onboarding/dns-check`. The existing generic `nac_web.oci_functions` runtime remains the stateful/runtime path for POST, callback, operator, BPMN, KG, and cost routes. The public Function entrypoint imports the minimal module directly, so the container no longer imports the full local web server at cold start.

**Tech Stack:** Python stdlib, existing `nac_identity` helpers, OCI Functions FDK package, `unittest`.

---

### Task 1: Public Runtime Boundary Test

**Files:**
- Modify: `tests/test_oci_functions_adapter.py`
- Read: `src/nac_web/oci_public_functions.py`
- Read: `src/nac_web/oci_functions.py`

- [ ] **Step 1: Write the failing test**

Add this test to `OCIFunctionsAdapterTests`:

```python
def test_public_get_runtime_uses_minimal_adapter_without_generic_webapp_boot(self) -> None:
    public_runtime = self.read("src/nac_web/oci_public_functions.py")

    self.assertNotIn("from nac_web.oci_functions import", public_runtime)
    self.assertNotIn("dispatch_oci_function_request", public_runtime)
    self.assertNotIn("NaCLocalWebApp", public_runtime)
    self.assertIn("dispatch_minimal_public_get_request", public_runtime)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_public_get_runtime_uses_minimal_adapter_without_generic_webapp_boot
```

Expected: FAIL because `oci_public_functions.py` still imports `nac_web.oci_functions`.

- [ ] **Step 3: Do not implement yet**

Leave implementation for Task 2 after the behavior tests exist.

### Task 2: Minimal Public GET Behavior

**Files:**
- Create: `src/nac_web/oci_minimal_public.py`
- Modify: `src/nac_web/oci_public_functions.py`
- Modify: `tests/test_oci_functions_adapter.py`

- [ ] **Step 1: Write failing route tests**

Add tests that call `dispatch_oci_public_function_request` with a small fake OCI context:

```python
class FakeOciContext:
    def __init__(self, method: str, url: str) -> None:
        self._method = method
        self._url = url

    def Method(self) -> str:
        return self._method

    def RequestURL(self) -> str:
        return self._url
```

Test health:

```python
def test_minimal_public_get_runtime_serves_health_without_webapp_boot(self) -> None:
    from nac_web.oci_public_functions import dispatch_oci_public_function_request

    result = dispatch_oci_public_function_request(FakeOciContext("GET", "/healthz"))

    self.assertEqual(result.status_code, 200)
    self.assertEqual(result.headers["Content-Type"], "application/json; charset=utf-8")
    self.assertEqual(result.body, b'{"status": "ok"}')
```

Test method guard:

```python
def test_minimal_public_get_runtime_rejects_public_post(self) -> None:
    from nac_web.oci_public_functions import dispatch_oci_public_function_request

    result = dispatch_oci_public_function_request(FakeOciContext("POST", "/onboarding/requests"))

    self.assertEqual(result.status_code, 405)
    self.assertIn(b"read-only", result.body)
```

Test non-exposed route:

```python
def test_minimal_public_get_runtime_rejects_auth_callback(self) -> None:
    from nac_web.oci_public_functions import dispatch_oci_public_function_request

    result = dispatch_oci_public_function_request(FakeOciContext("GET", "/auth/callback"))

    self.assertEqual(result.status_code, 404)
    self.assertIn(b"not exposed", result.body)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_minimal_public_get_runtime_serves_health_without_webapp_boot tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_minimal_public_get_runtime_rejects_public_post tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_minimal_public_get_runtime_rejects_auth_callback
```

Expected: at least one FAIL because the current public runtime delegates to generic `oci_functions`.

- [ ] **Step 3: Implement minimal response boundary**

Create `src/nac_web/oci_minimal_public.py` with:

- `PublicHttpResponse`
- request method and URL extraction from OCI context
- JSON response helper
- HTML response helper
- exposed route dispatch
- no import from `nac_web.server`
- no import from BPMN, KG, GNotKG, onboarding store, or callback modules

Keep `/healthz` exact and lightweight. Keep unsupported POST fail-closed with 405. Keep `/auth/callback` unavailable from public runtime.

- [ ] **Step 4: Wire public entrypoint**

Change `src/nac_web/oci_public_functions.py` to import and call `dispatch_minimal_public_get_request` from the new module. Keep the FDK `handler` wrapper unchanged.

- [ ] **Step 5: Run green tests**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_public_get_runtime_uses_minimal_adapter_without_generic_webapp_boot tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_minimal_public_get_runtime_serves_health_without_webapp_boot tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_minimal_public_get_runtime_rejects_public_post tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_minimal_public_get_runtime_rejects_auth_callback
```

Expected: OK.

### Task 3: Public Customer Pages and Login Intent

**Files:**
- Modify: `src/nac_web/oci_minimal_public.py`
- Modify: `tests/test_oci_functions_adapter.py`

- [ ] **Step 1: Write failing public GET parity tests**

Add tests that verify:

```python
def test_minimal_public_get_runtime_serves_customer_readiness_page(self) -> None:
    from nac_web.oci_public_functions import dispatch_oci_public_function_request

    result = dispatch_oci_public_function_request(
        FakeOciContext(
            "GET",
            "/onboarding/readiness?audience=customer&domain_hint=myjur.de&tenant_slug=myjur&admin_email=ofunk%40myjur.de",
        )
    )

    body = result.body.decode("utf-8")
    self.assertEqual(result.status_code, 200)
    self.assertIn("notariat8", body)
    self.assertIn("myjur.de", body)
    self.assertIn("_nac.myjur.de", body)
    self.assertNotIn("Oracle", body)
    self.assertNotIn("OCI", body)
```

```python
def test_minimal_public_get_runtime_serves_login_intent_json(self) -> None:
    from nac_web.oci_public_functions import dispatch_oci_public_function_request

    with self.public_oidc_env():
        result = dispatch_oci_public_function_request(FakeOciContext("GET", "/api/tenant/login-intent?tenant_hint=myjur"))

    payload = json.loads(result.body.decode("utf-8"))
    self.assertEqual(result.status_code, 200)
    self.assertEqual(payload["schema_version"], "nac.oci-login-intent/v0.1")
    self.assertEqual(payload["tenant_context"]["tenant_hint"], "myjur")
    self.assertFalse(payload["guardrails"]["contains_credentials"])
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_minimal_public_get_runtime_serves_customer_readiness_page tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_minimal_public_get_runtime_serves_login_intent_json
```

Expected: FAIL until the minimal module renders readiness and login-intent.

- [ ] **Step 3: Implement only the required public route renderers**

Implement readiness, DNS-check and login-intent with existing `nac_identity` helpers:

- `check_domain_ready`
- `build_dns_check_result`
- `build_live_dns_check_result`
- `build_login_intent`

Duplicate only the small amount of customer-safe HTML needed for public pages. Do not import `_layout` or `NaCLocalWebApp` from `server.py`, because that is the cold-start problem.

- [ ] **Step 4: Run green tests**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_minimal_public_get_runtime_serves_customer_readiness_page tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_minimal_public_get_runtime_serves_login_intent_json
```

Expected: OK.

### Task 4: Regression and Quality Gate

**Files:**
- Modify: `docs/superpowers/plans/2026-06-15-minimal-public-get-runtime.md`
- Modify: `tests/test_oci_functions_adapter.py`
- Modify: `src/nac_web/oci_public_functions.py`
- Create: `src/nac_web/oci_minimal_public.py`

- [ ] **Step 1: Run focused tests**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter
```

Expected: OK.

- [ ] **Step 2: Run web tests**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web
```

Expected: OK.

- [ ] **Step 3: Run quality gate**

Run:

```bash
env GITHUB_BASE_REF=main PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: STATUS: PASSED.

- [ ] **Step 4: Commit and open Protected PR**

Commit:

```bash
git add docs/superpowers/plans/2026-06-15-minimal-public-get-runtime.md tests/test_oci_functions_adapter.py src/nac_web/oci_public_functions.py src/nac_web/oci_minimal_public.py
git commit -m "fix: use minimal public get runtime"
```

Open PR against `main` and link Issue #123. State explicitly:

- no OCI apply
- no release
- no Function update
- no secret value read
- live cold-start evidence is in Issue #123

### Self-Review

- Spec coverage: The plan covers the owner-approved Ansatz A by removing full web-app boot from simple public GETs and keeping OCI writes out of scope.
- Placeholder scan: No TBD/TODO placeholders are present.
- Type consistency: `dispatch_minimal_public_get_request`, `PublicHttpResponse`, and `dispatch_oci_public_function_request` are used consistently.
