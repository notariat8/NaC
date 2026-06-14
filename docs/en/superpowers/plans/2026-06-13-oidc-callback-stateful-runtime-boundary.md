# OIDC Callback Stateful Runtime Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move `/auth/callback` out of the lean Public-GET runtime and into the stateful/auth runtime boundary, without opening the workspace or adding secrets to Git.

**Architecture:** The Public-GET Function continues to serve public onboarding and login-intent GET routes. The stateful `nac-app` Function owns `/auth/callback`, so the separate Q2B implementation can add token exchange, Vault-backed client secret access, session creation and NaC role gate without making the public runtime secret-capable. API Gateway must route `/auth/callback` to `nac_app`, not `nac_public_app`.

**Tech Stack:** Python stdlib, `unittest`, existing NaC Functions adapter, Terraform tests in `oci-landing-zone`, OCI Resource Manager guarded by an explicit Owner Apply Approval after PR review.

---

### Task 1: NaC Function Route Boundary

**Files:**
- Modify: `/home/ubuntu/src/private/NaC/tests/test_oci_functions_adapter.py`
- Modify: `/home/ubuntu/src/private/NaC/src/nac_web/oci_functions.py`

- [ ] **Step 1: Write the failing test**

Add this test near the other public/runtime exposure tests in
`/home/ubuntu/src/private/NaC/tests/test_oci_functions_adapter.py`:

```python
    def test_public_function_does_not_expose_auth_callback(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request
        from nac_web.oci_public_functions import dispatch_oci_public_function_request

        request = FakeFunctionContext(
            request_url="/auth/callback?code=secret-code-from-idp&state=state-secret-from-nac",
            method="GET",
        )

        public_result = dispatch_oci_public_function_request(request, repo_root=REPO_ROOT)
        stateful_result = dispatch_oci_function_request(request, repo_root=REPO_ROOT)

        self.assertEqual(public_result.status_code, 404)
        self.assertNotIn(b"secret-code-from-idp", public_result.body)
        self.assertNotIn(b"state-secret-from-nac", public_result.body)
        self.assertEqual(stateful_result.status_code, 200)
        self.assertIn(b"Anmeldung empfangen", stateful_result.body)
        self.assertNotIn(b"secret-code-from-idp", stateful_result.body)
        self.assertNotIn(b"state-secret-from-nac", stateful_result.body)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_public_function_does_not_expose_auth_callback
```

Expected: FAIL because the public Function still exposes `/auth/callback`.

- [ ] **Step 3: Implement the route boundary**

In `/home/ubuntu/src/private/NaC/src/nac_web/oci_functions.py`:

```python
EXPOSED_GET_ROUTES = {
    "/",
    "/healthz",
    "/login",
    "/api/tenant/login-intent",
    "/onboarding/readiness",
    "/onboarding/dns-check",
}

STATEFUL_GET_ROUTES = {
    "/auth/callback",
}
```

Then update `_is_exposed_get_route` so stateful-only routes are available only
when `expose_stateful_onboarding_routes` is true:

```python
    if route in EXPOSED_GET_ROUTES:
        return True
    if expose_stateful_onboarding_routes and route in STATEFUL_GET_ROUTES:
        return True
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/ubuntu/src/private/NaC add tests/test_oci_functions_adapter.py src/nac_web/oci_functions.py
git -C /home/ubuntu/src/private/NaC commit -m "fix: keep auth callback stateful"
```

### Task 2: Landing Zone API Gateway Route Split

**Files:**
- Modify: `/home/ubuntu/src/oci-landing-zone/tests/test_cloud_native_runtime_iac.py`
- Modify: `/home/ubuntu/src/oci-landing-zone/infra/modules/cloud_native_runtime/main.tf`
- Modify: `/home/ubuntu/src/oci-landing-zone/runbooks/no-ssh-functions-release.md`

- [ ] **Step 1: Write the failing Terraform contract test**

In `/home/ubuntu/src/oci-landing-zone/tests/test_cloud_native_runtime_iac.py`,
change the public route assertions so `/auth/callback` is not listed with
`public_route_paths`. Add a dedicated assertion:

```python
        callback_route_start = module_main.index('path    = "/auth/callback"')
        callback_route_end = module_main.find("\n    routes {", callback_route_start + 1)
        callback_route_body = (
            module_main[callback_route_start:]
            if callback_route_end == -1
            else module_main[callback_route_start:callback_route_end]
        )
        self.assertIn("function_id = oci_functions_function.nac_app[0].id", callback_route_body)
        self.assertNotIn("function_id = local.public_get_function_id", callback_route_body)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
env PYTHONPATH=. /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_cloud_native_runtime_iac.CloudNativeRuntimeIaCTests.test_cloud_native_runtime_can_split_public_get_function_from_stateful_function
```

Expected: FAIL because `/auth/callback` is still routed to
`local.public_get_function_id`.

- [ ] **Step 3: Update Terraform route target**

In `/home/ubuntu/src/oci-landing-zone/infra/modules/cloud_native_runtime/main.tf`,
change only the `/auth/callback` route integration:

```hcl
    routes {
      path    = "/auth/callback"
      methods = ["GET", "HEAD"]

      backend {
        type        = "ORACLE_FUNCTIONS_BACKEND"
        function_id = oci_functions_function.nac_app[0].id
      }
    }
```

Do not change `/healthz`, `/login`, `/api/tenant/login-intent`,
`/onboarding/readiness` or `/onboarding/dns-check`; those remain public.

- [ ] **Step 4: Update runbook wording**

In `/home/ubuntu/src/oci-landing-zone/runbooks/no-ssh-functions-release.md`,
add a short note in the Public-GET split section:

```markdown
`/auth/callback` is intentionally routed to the stateful `nac-app` Function.
The public Function must not own the callback because Q2 token exchange and
role-gate checks need server-side secret and session boundaries.
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
env PYTHONPATH=. /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_cloud_native_runtime_iac
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git -C /home/ubuntu/src/oci-landing-zone add tests/test_cloud_native_runtime_iac.py infra/modules/cloud_native_runtime/main.tf runbooks/no-ssh-functions-release.md
git -C /home/ubuntu/src/oci-landing-zone commit -m "fix: route auth callback to stateful function"
```

### Task 3: Verification And GitHub Tracking

**Files:**
- Verify: `/home/ubuntu/src/private/NaC`
- Verify: `/home/ubuntu/src/oci-landing-zone`

- [ ] **Step 1: Run NaC focused verification**

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter tests.test_nac_web
```

Expected: PASS.

- [ ] **Step 2: Run NaC quality gate**

```bash
GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: PASS.

- [ ] **Step 3: Run Landing Zone focused verification**

```bash
env PYTHONPATH=. /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_cloud_native_runtime_iac
```

Expected: PASS.

- [ ] **Step 4: Open protected PRs**

Open one PR in `notariat8/NaC` against `main` for the NaC route-boundary
change, and one PR in `notariat8/oci-landing-zone` against `main` for the API
Gateway route split.

Both PR bodies must reference `notariat8/NaC#128` and state:

```markdown
No OCI write is performed by this PR. Runtime deployment and Resource Manager
Apply remain owner-gated.
```

- [ ] **Step 5: Update Issue #128**

Comment with the PR links, test results, and the next expected owner actions:
review/merge the PRs, then release the NaC image, then Resource Manager
no-apply plan, then owner-gated Apply.
