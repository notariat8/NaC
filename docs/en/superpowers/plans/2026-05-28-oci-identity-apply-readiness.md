# OCI Identity Apply-Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NaC creates checkable OCI Identity apply requests without productive OCI write operations.

**Architecture:** `src/nac_identity/oci_tenant.py` remains the central pure-Python domain layer. The CLI calls this logic, while the contract and validator check gates, credential freedom and the clear boundary between apply readiness and later productive execution.

**Tech Stack:** Python Standard Library, `unittest`, NaC CLI, workflow contracts, strict Quality Gate.

---

### Task 1: Apply-Request Core

**Files:**
- Modify: `src/nac_identity/oci_tenant.py`
- Test: `tests/test_oci_tenant_identity.py`

- [ ] **Step 1: Write failing tests**

```python
def test_apply_request_requires_all_apply_gates(self) -> None:
    from nac_identity.oci_tenant import build_admin_provisioning_plan, build_apply_request
    plan = build_admin_provisioning_plan(...)
    request = build_apply_request(plan, dns_verified=False, owner_approval_id="", audit_event_id="", rollback_plan_id="")
    self.assertFalse(request["ready_to_apply"])
    self.assertIn("dns_not_verified", request["blocking_findings"])
```

- [ ] **Step 2: Verify RED**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_apply_request_requires_all_apply_gates`

Expected: import failure for `build_apply_request`.

- [ ] **Step 3: Implement minimal core**

Add `build_apply_request(plan, dns_verified, owner_approval_id, audit_event_id, rollback_plan_id)` with deterministic JSON-safe output and no credentials.

- [ ] **Step 4: Verify GREEN**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity`

### Task 2: CLI And Contract

**Files:**
- Modify: `src/nac_cli/cli.py`
- Modify: `workflows/contracts/oci-tenant-identity.contract.json`
- Modify: `scripts/validate_oci_tenant_identity.py`
- Test: `tests/test_nac_cli.py`

- [ ] **Step 1: Write failing CLI test**

```python
def test_tenant_apply_request_cli_is_review_artifact_only(self) -> None:
    rc, output = run_cli("tenant", "apply-request", "--tenant-slug", "kanzlei-notariat", "--domain", "kanzlei-notariat.example", "--admin-email", "admin@kanzlei-notariat.example", "--admin-display-name", "Admin Notariat", "--identity-domain-url", "https://idcs.example.identity.oraclecloud.com:443", "--identity-domain-id", "ocid1.domain.oc1.example", "--dns-verified", "--owner-approval-id", "OWNER-APPROVED-32", "--audit-event-id", "AUDIT-32", "--rollback-plan-id", "ROLLBACK-32", "--dry-run", "--format", "json")
    self.assertEqual(rc, 0)
    self.assertTrue(json.loads(output)["ready_to_apply"])
```

- [ ] **Step 2: Verify RED**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_cli.NaCCliTests.test_tenant_apply_request_cli_is_review_artifact_only`

Expected: unknown command.

- [ ] **Step 3: Implement CLI and validator**

Add `nac tenant apply-request --dry-run`, extend contract schema and validator checks.

- [ ] **Step 4: Verify GREEN**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity tests.test_nac_cli`

### Task 3: Final Verification

**Files:**
- All touched files

- [ ] **Step 1: Run contract validation**

Run: `/home/ubuntu/.venvs/nac/bin/python scripts/nac.py contracts validate`

- [ ] **Step 2: Run strict Quality Gate**

Run: `/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict`

- [ ] **Step 3: Commit and open protected PR**

Commit: `feat: add oci identity apply readiness`

Open PR for Issue #32.
