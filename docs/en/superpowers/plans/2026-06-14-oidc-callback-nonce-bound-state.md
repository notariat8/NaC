# OIDC Callback Nonce-Bound State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind the OIDC login `nonce` into notariat8's signed `state` contract so the next Q2B slice can validate an ID token against the original login intent without storing raw nonce values in Git, logs, browser text or public callback output.

**Architecture:** `nac_identity.oidc_state` accepts an optional raw nonce, stores only a deterministic nonce hash in the signed state payload, and returns only nonce-binding metadata plus the hash needed for server-side validation. `nac_identity.oci_login` generates nonce before state and signs the nonce binding. `nac_identity.oci_callback` and the web callback keep the workspace closed while exposing only safe progress wording.

**Tech Stack:** Python standard library only, `unittest`, protected PR delivery. No OCI write is part of this plan.

---

### Task 1: Signed State Carries Nonce Binding Metadata

**Files:**
- Modify: `src/nac_identity/oidc_state.py`
- Modify: `tests/test_oci_tenant_identity.py`

- [ ] **Step 1: Write the failing nonce-bound state test**

Add a test that builds signed state with `tenant_hint`, `signing_key`, `nonce`, fixed `now` and TTL, then validates it. Assert:

- validation status is `valid`,
- `tenant_hint` is preserved,
- `nonce_bound` is `True`,
- a `nonce_hash` is returned for later server-side ID-token nonce comparison,
- the serialized validation result does not contain the raw nonce or signing key.

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_signed_state_binds_nonce_without_returning_raw_nonce
```

Expected: FAIL because `build_signed_state` does not accept `nonce` yet.

- [ ] **Step 3: Implement nonce hash support**

Update `build_signed_state` to accept `nonce: str | None = None`. If a nonce is present, store `nonce_hash = sha256(nonce).hexdigest()` in the signed payload. Update `validate_signed_state` to return `nonce_bound` and `nonce_hash` only for valid states. Older states without nonce remain valid with `nonce_bound=False`.

- [ ] **Step 4: Run state tests**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity
```

Expected: OK.

### Task 2: Login Intent Signs The Generated Nonce

**Files:**
- Modify: `src/nac_identity/oci_login.py`
- Modify: `tests/test_oci_tenant_identity.py`
- Modify: `tests/test_nac_web.py`

- [ ] **Step 1: Write failing login-intent tests**

Add or extend tests so signed login intent validation proves:

- `state_binding.nonce_bound` is `True`,
- validating the returned state yields `nonce_bound=True`,
- the returned `nonce_hash` matches the generated nonce by hash,
- neither the state validation payload nor serialized login intent exposes the signing key.

- [ ] **Step 2: Run tests to verify RED**

Run the focused login-intent tests and expect FAIL until `oci_login` signs the nonce.

- [ ] **Step 3: Generate nonce before signing state**

Update `build_login_intent` to generate the nonce before `build_signed_state`, pass it into the state builder, and include `nonce_bound=True` in signed-state binding metadata. Opaque-state fallback remains `nonce_bound=False`.

- [ ] **Step 4: Run web and identity tests**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity tests.test_nac_web
```

Expected: OK.

### Task 3: Callback Progress Reflects Nonce-Bound State Without Opening Workspace

**Files:**
- Modify: `src/nac_identity/oci_callback.py`
- Modify: `tests/test_oci_tenant_identity.py`
- Modify: `tests/test_nac_web.py`

- [ ] **Step 1: Write callback tests**

Add tests proving that a callback with valid nonce-bound state:

- is accepted as `received`,
- reports `state_validation.nonce_bound=True` internally,
- keeps `role_gate.status=closed`,
- keeps the HTML free of raw state, code, nonce, nonce hash, signing key, Oracle/OCI wording and secrets.

- [ ] **Step 2: Run callback tests to verify RED**

Run the focused new callback tests and expect FAIL until callback result carries nonce-binding metadata safely.

- [ ] **Step 3: Normalize nonce metadata in callback result**

Update `build_auth_callback_result` so `state_validation` preserves `nonce_bound=True` but does not include `nonce_hash` in browser-facing result text. Keep role gate reason at `session_not_established`.

- [ ] **Step 4: Run callback tests**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity tests.test_nac_web tests.test_oci_functions_adapter
```

Expected: OK.

### Task 4: Quality Gate And PR

**Files:**
- Modify documentation only if acceptance language needs to mention nonce-bound state.

- [ ] **Step 1: Run strict quality gate**

Run:

```bash
env GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: PASSED.

- [ ] **Step 2: Commit and open protected PR**

Commit on `agent/128-nonce-bound-state`, push it, open a PR linked to issue #128, apply labels/project fields, and leave runtime deployment for a separate Owner Release Approval.
