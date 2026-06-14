# OIDC Token-Claim And Role-Gate Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pure, locally testable contract for OIDC claim validation and the notariat8 role gate that decides fail-closed without live token exchange.

**Architecture:** `nac_identity.oidc_role_gate` accepts already server-side verified claim data plus the expected callback context. The module validates issuer, audience, nonce binding and `nac-tenant-admin`, returns only safe metadata and does not open a session. `nac_identity.oci_callback` can consume this contract in a later Q2D slice after token exchange and JWT validation.

**Tech Stack:** Python standard library, `unittest`, protected PR. This plan contains no OCI write and no secrets.

---

### Task 1: Introduce The Pure Role-Gate Contract With TDD

**Files:**
- Create: `src/nac_identity/oidc_role_gate.py`
- Modify: `src/nac_identity/__init__.py`
- Modify: `tests/test_oci_tenant_identity.py`

- [ ] **Step 1: Write failing tests**

Write tests for these cases:

- valid claims with matching `iss`, `aud`, `nonce`, validated nonce-bound state and role `nac-tenant-admin` yield `status="open"` and `session_allowed=True`,
- missing role yields `status="closed"` and `reason="role_missing"`,
- wrong issuer or wrong audience close with `issuer_mismatch` or `audience_mismatch`,
- missing or wrong nonce binding closes with `nonce_not_bound` or `nonce_mismatch`,
- serialized results contain no raw tokens, codes, states, nonces, nonce hashes or secret values.

- [ ] **Step 2: Verify RED**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_oidc_role_gate_opens_only_for_verified_admin_claims
```

Expected: FAIL because `nac_identity.oidc_role_gate` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement `evaluate_oidc_role_gate(...)` with explicit expected values:

- `expected_issuer`
- `expected_audience`
- `state_validation`
- `claims`
- optional `required_role="nac-tenant-admin"`

The function returns a dict contract with `schema_version`, `status`, `reason`,
`role`, `session_allowed` and `guardrails`. It must not copy raw inputs into the
output. The `nonce` claim from `claims` is only hashed and compared with
`state_validation["nonce_hash"]`; the hash is not copied into the result.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity
```

Expected: OK.

### Task 2: Prepare The Callback Contract For The Future Role-Gate Step

**Files:**
- Modify: `src/nac_identity/oci_callback.py`
- Modify: `tests/test_oci_tenant_identity.py`

- [ ] **Step 1: Write the failing test**

Add a test proving that after valid state validation the callback still remains
closed, but names the next step as token-claim and role-gate evaluation instead
of generic session setup.

- [ ] **Step 2: Verify RED**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_auth_callback_result_points_to_token_claim_role_gate_contract
```

Expected: FAIL because the callback still reports the previous `next_step`.

- [ ] **Step 3: Update only the minimal callback contract text**

Change only the machine-readable `next_step` to the Q2C contract. Browser-facing
text stays unchanged so no new cloud behavior is introduced.

- [ ] **Step 4: Run identity and web tests**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity tests.test_nac_web tests.test_oci_functions_adapter
```

Expected: OK.

### Task 3: Quality Gate And PR

**Files:**
- All files touched above.

- [ ] **Step 1: Run the strict Quality Gate**

Run:

```bash
env GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: PASSED.

- [ ] **Step 2: Commit, push and open PR**

Commit on `agent/128-q2c-token-role-gate-contract`, push the branch and open a
protected PR against `main`, linked to Issue #128. No OCI apply and no live
token exchange in this PR.
