# OCI Tenant Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NaC gets a tenant-aware OCI Identity dry-run path, and `www-n8` leads into this SaaS path without mandate data.

**Architecture:** A new NaC domain layer computes domain readiness and OCI admin provisioning plans deterministically. CLI and web API use the same logic. `www-n8` remains static and links existing and new customers into the NaC app.

**Tech Stack:** Python Standard Library, `unittest`, NaC CLI, NaC local web server, GitHub Project, static HTML/CSS/JS for `www-n8`.

---

### Task 1: Contract And Documentation Boundary

**Files:**
- Create: `workflows/contracts/oci-tenant-identity.contract.json`
- Modify: `workflows/contracts/README.md`
- Modify: `docs/de/authenticated-webapp-operating-model.md`
- Modify: `docs/en/authenticated-webapp-operating-model.md`
- Test: `tests/test_oci_tenant_identity.py`

- [ ] **Step 1: Write the failing contract test**

```python
def test_contract_declares_dry_run_only_boundary(self) -> None:
    contract = json.loads((REPO_ROOT / "workflows/contracts/oci-tenant-identity.contract.json").read_text())
    self.assertEqual(contract["schema_version"], "nac.oci-tenant-identity-contract/v0.1")
    self.assertFalse(contract["productive_identity_writes_allowed"])
    self.assertIn("domain_ready", contract["required_gates"])
    self.assertIn("owner_apply_approval", contract["required_gates"])
```

- [ ] **Step 2: Run the test and verify RED**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_contract_declares_dry_run_only_boundary`

Expected: fails because the contract file does not exist.

- [ ] **Step 3: Add the contract and docs**

Create the JSON contract with schema version, required gates, allowed
operations and forbidden operations. Update the authenticated-webapp operating
model so OCI Identity Domains is the IdP for this SaaS path.

- [ ] **Step 4: Run the focused test and commit**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_contract_declares_dry_run_only_boundary`

Commit: `docs: define oci tenant identity boundary`

### Task 2: Domain-Readiness Core

**Files:**
- Create: `src/nac_identity/__init__.py`
- Create: `src/nac_identity/oci_tenant.py`
- Test: `tests/test_oci_tenant_identity.py`

- [ ] **Step 1: Write failing domain-ready tests**

```python
def test_domain_check_accepts_notary_domain_and_admin_email(self) -> None:
    result = check_domain_ready("kanzlei-notariat.example", "kanzlei-notariat", "admin@kanzlei-notariat.example")
    self.assertTrue(result["ready"])
    self.assertEqual(result["tenant_slug"], "kanzlei-notariat")
    self.assertEqual(result["verification"]["dns_record_name"], "_nac.kanzlei-notariat.example")

def test_domain_check_rejects_external_admin_domain(self) -> None:
    result = check_domain_ready("kanzlei-notariat.example", "kanzlei-notariat", "admin@example.com")
    self.assertFalse(result["ready"])
    self.assertIn("admin_email_domain_mismatch", result["blocking_findings"])
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_domain_check_accepts_notary_domain_and_admin_email tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_domain_check_rejects_freemail_admin`

Expected: import or name failure because the module is not implemented.

- [ ] **Step 3: Implement the minimal core**

Implement pure functions for domain normalization, tenant slug validation,
admin email domain matching and deterministic DNS TXT token proposal.

- [ ] **Step 4: Run focused tests and commit**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity`

Commit: `feat: add oci tenant domain readiness`

### Task 3: OCI Admin-Provisioning Dry Run

**Files:**
- Modify: `src/nac_identity/oci_tenant.py`
- Test: `tests/test_oci_tenant_identity.py`

- [ ] **Step 1: Write failing dry-run tests**

```python
def test_admin_provisioning_plan_is_dry_run_and_secret_free(self) -> None:
    plan = build_admin_provisioning_plan(
        tenant_slug="kanzlei-notariat",
        domain="kanzlei-notariat.example",
        admin_email="admin@kanzlei-notariat.example",
        admin_display_name="Admin Notariat",
        identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
        identity_domain_id="ocid1.domain.oc1.example",
    )
    self.assertEqual(plan["mode"], "dry_run")
    self.assertTrue(plan["requires_human_approval"])
    self.assertFalse(plan["console_access_required_for_end_users"])
    self.assertNotIn("secret", json.dumps(plan).lower())
```

- [ ] **Step 2: Run the test and verify RED**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_admin_provisioning_plan_is_dry_run_and_secret_free`

Expected: fails because the function is not implemented.

- [ ] **Step 3: Implement dry-run plan**

Return a deterministic plan with Oracle endpoint paths `/admin/v1/Users` and
`/admin/v1/Groups`, NaC groups, planned writes, and owner approval gate.

- [ ] **Step 4: Run focused tests and commit**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity`

Commit: `feat: add oci admin provisioning dry run`

### Task 4: CLI, Web API And Quality Gate

**Files:**
- Modify: `src/nac_cli/cli.py`
- Modify: `src/nac_web/server.py`
- Modify: `scripts/validate_oci_tenant_identity.py`
- Modify: `scripts/quality_gate.py`
- Test: `tests/test_nac_cli.py`
- Test: `tests/test_nac_web.py`

- [ ] **Step 1: Write failing CLI and web tests**

```python
def test_tenant_domain_check_cli_returns_json(self) -> None:
    rc, output = run_cli("tenant", "domain-check", "--domain", "kanzlei-notariat.example", "--tenant-slug", "kanzlei-notariat", "--admin-email", "admin@kanzlei-notariat.example", "--format", "json")
    self.assertEqual(rc, 0)
    self.assertTrue(json.loads(output)["ready"])

def test_app_serves_tenant_domain_check_api(self) -> None:
    app = NaCLocalWebApp(REPO_ROOT)
    status, _content_type, body = app.handle("/api/tenant/domain-check?domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin@kanzlei-notariat.example")
    self.assertEqual(status, 200)
    self.assertTrue(json.loads(body.decode("utf-8"))["ready"])
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_cli.NaCCliTests.test_tenant_domain_check_cli_returns_json tests.test_nac_web.NaCLocalWebTests.test_app_serves_tenant_domain_check_api`

Expected: unknown command and missing route.

- [ ] **Step 3: Implement CLI and API**

Add `nac tenant domain-check` and `nac tenant provision-admin --dry-run`.
Add `/api/tenant/domain-check` and `/api/tenant/provision-admin/preview`.
Wire `validate_oci_tenant_identity.py` into `nac contracts validate` and the
strict Quality Gate.

- [ ] **Step 4: Run focused tests and commit**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity tests.test_nac_cli tests.test_nac_web`

Commit: `feat: expose oci tenant identity dry run`

### Task 5: www-n8 Tenant-Aware Transition

**Files:**
- Modify in `/home/ubuntu/src/www-n8`: `index.html`
- Modify in `/home/ubuntu/src/www-n8`: `en/index.html`
- Modify in `/home/ubuntu/src/www-n8`: `assets/site.css`
- Modify in `/home/ubuntu/src/www-n8`: `assets/site.js`

- [ ] **Step 1: Add static transition UI**

Add a compact product-app section with two paths: existing customer login and
new customer domain check. Keep all form values client-side and pass only
tenant/domain hints to the configured NaC app URL.

- [ ] **Step 2: Check there are no secrets or mandate-data paths**

Run: `rg -n "secret|token|mandat|personalausweis|api[_-]?key" /home/ubuntu/src/www-n8`

Expected: no introduced secret-handling or raw mandate upload path.

- [ ] **Step 3: Commit**

Commit in `www-n8`: `feat: add tenant-aware nac app transition`

### Task 6: Final Verification And PRs

**Files:**
- All touched NaC files
- All touched `www-n8` files

- [ ] **Step 1: Run NaC strict verification**

Run: `/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict`

Expected: `STATUS: PASSED`.

- [ ] **Step 2: Push branches and open PRs**

Push `agent/30-oci-tenant-identity` to `notariat8/NaC` and
`agent/1-tenant-aware-login` to `notariat8/www-n8`.

- [ ] **Step 3: Set Project status to Review**

Move Issue #30 and `www-n8` Issue #1 to Review after checks pass.
