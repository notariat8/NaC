# Customer-Centric Tenant Onboarding Journey Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NaC bildet die sichtbare Neukundenreise von `www-n8` bis zum initialen Kundenadmin in NaC ab.

**Architecture:** `www-n8` übergibt nur Domain-Hinweise. NaC führt Readiness, DNS-Challenge, Admin-Queue, Apply-Plan und Tenant Registry. OCI startet mit Default Domain für SaaS-Admins, Secondary IAM Domain für Kundenlogin, Compartment pro Kundendomain und gemeinsamer ATP mit Tenant-Mapping.

**Tech Stack:** Python Standard Library, `unittest`, NaC CLI, NaC local web server, OCI Identity Domains API contract, OCI compartment/apply-plan artifacts, Oracle ATP design contract, GitHub Protected PR.

---

### Task 1: Onboarding Journey Contract

**Files:**
- Create: `workflows/contracts/customer-tenant-onboarding.contract.json`
- Modify: `workflows/contracts/README.md`
- Test: `tests/test_customer_tenant_onboarding.py`

- [ ] **Step 1: Write the failing contract test**

```python
def test_contract_declares_customer_and_saas_admin_journeys(self) -> None:
    contract = json.loads((REPO_ROOT / "workflows/contracts/customer-tenant-onboarding.contract.json").read_text())
    self.assertEqual(contract["schema_version"], "nac.customer-tenant-onboarding/v0.1")
    self.assertEqual(contract["public_entry_surface"], "www-n8")
    self.assertEqual(contract["app_surface"], "app.notariat8.de")
    self.assertIn("customer_domain_readiness", contract["customer_journey"])
    self.assertIn("saas_admin_review_queue", contract["saas_admin_journey"])
    self.assertFalse(contract["guardrails"]["customer_oci_console_required"])
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_customer_tenant_onboarding.CustomerTenantOnboardingTests.test_contract_declares_customer_and_saas_admin_journeys`

Expected: fails because the contract file does not exist.

- [ ] **Step 3: Add the contract**

Create `customer-tenant-onboarding.contract.json` with customer journey,
SaaS-admin journey, OCI target model, ATP target model, apply gates and
guardrails. Use these concrete guardrails:

```json
{
  "customer_oci_console_required": false,
  "www_n8_accepts_mandate_data": false,
  "productive_oci_write_without_owner_apply": false,
  "github_contains_secrets": false
}
```

- [ ] **Step 4: Run the focused test and commit**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_customer_tenant_onboarding`

Commit: `docs: define customer tenant onboarding contract`

### Task 2: Tenant Registry And ATP Mapping Model

**Files:**
- Create: `src/nac_identity/customer_onboarding.py`
- Modify: `src/nac_identity/__init__.py`
- Test: `tests/test_customer_tenant_onboarding.py`

- [ ] **Step 1: Write failing registry tests**

```python
def test_customer_tenant_plan_uses_compartment_and_shared_atp_mapping(self) -> None:
    from nac_identity.customer_onboarding import build_customer_tenant_plan

    plan = build_customer_tenant_plan(
        domain="kanzlei-notariat.example",
        tenant_slug="kanzlei-notariat",
        admin_email="admin@kanzlei-notariat.example",
        saas_admin_email="saas-owner@example.com",
    )
    self.assertEqual(plan["schema_version"], "nac.customer-tenant-plan/v0.1")
    self.assertEqual(plan["oci"]["identity"]["customer_domain_strategy"], "single_secondary_domain")
    self.assertEqual(plan["oci"]["resource_isolation"]["compartment_strategy"], "one_compartment_per_customer_domain")
    self.assertEqual(plan["atp"]["strategy"], "shared_atp_with_tenant_id")
    self.assertIn("tenant_id", plan["atp"]["required_controls"])
```

- [ ] **Step 2: Run the test and verify RED**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_customer_tenant_onboarding.CustomerTenantOnboardingTests.test_customer_tenant_plan_uses_compartment_and_shared_atp_mapping`

Expected: import failure because `customer_onboarding.py` is not implemented.

- [ ] **Step 3: Implement deterministic planning**

Implement `build_customer_tenant_plan(...)` as a pure function. It must return
no secrets and must include:

```python
{
    "schema_version": "nac.customer-tenant-plan/v0.1",
    "tenant": {"slug": tenant_slug, "domain": normalized_domain},
    "saas_admin": {"email": "saas-owner@example.com", "role": "nac-saas-owner"},
    "oci": {
        "identity": {"admin_domain": "Default", "customer_domain_strategy": "single_secondary_domain"},
        "resource_isolation": {"compartment_strategy": "one_compartment_per_customer_domain"},
    },
    "atp": {"strategy": "shared_atp_with_tenant_id", "required_controls": ["tenant_registry", "tenant_id"]},
    "requires_owner_apply": True,
}
```

- [ ] **Step 4: Run tests and commit**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_customer_tenant_onboarding`

Commit: `feat: plan customer tenant registry and atp mapping`

### Task 3: NaC Admin Queue Preview

**Files:**
- Modify: `src/nac_web/server.py`
- Test: `tests/test_nac_web.py`

- [ ] **Step 1: Write failing web tests**

```python
def test_admin_queue_page_shows_customer_onboarding_request_without_secrets(self) -> None:
    app = NaCLocalWebApp(REPO_ROOT)
    status, content_type, body = app.handle("/admin/onboarding")
    html = body.decode("utf-8")
    self.assertEqual(status, 200)
    self.assertIn("text/html", content_type)
    self.assertIn("Readiness-Anfragen", html)
    self.assertIn("nac-saas-owner", html)
    self.assertNotIn("api_key", html.lower())
    self.assertNotIn("password", html.lower())
```

- [ ] **Step 2: Run the test and verify RED**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_admin_queue_page_shows_customer_onboarding_request_without_secrets`

Expected: route returns a missing page or no queue content.

- [ ] **Step 3: Add the admin queue preview**

Add `/admin/onboarding` as a read-only local preview. It shows the journey
states: `submitted`, `dns_challenge_issued`, `domain_verified`,
`saas_admin_review`, `owner_apply_ready`, `invited`. It must not show secrets,
tokens or mandate data.

- [ ] **Step 4: Run focused tests and commit**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web tests.test_customer_tenant_onboarding`

Commit: `feat: add customer onboarding admin queue preview`

### Task 4: Customer Readiness Page

**Files:**
- Modify: `src/nac_web/server.py`
- Test: `tests/test_nac_web.py`

- [ ] **Step 1: Write failing customer journey test**

```python
def test_customer_readiness_page_explains_next_steps(self) -> None:
    app = NaCLocalWebApp(REPO_ROOT)
    status, content_type, body = app.handle("/onboarding/readiness?domain_hint=kanzlei-notariat.example")
    html = body.decode("utf-8")
    self.assertEqual(status, 200)
    self.assertIn("text/html", content_type)
    self.assertIn("Domain-Readiness", html)
    self.assertIn("DNS-TXT", html)
    self.assertIn("Keine Mandatsdaten", html)
    self.assertNotIn("OCI Console", html)
```

- [ ] **Step 2: Run the test and verify RED**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_customer_readiness_page_explains_next_steps`

Expected: missing route.

- [ ] **Step 3: Add customer readiness page**

Add `/onboarding/readiness` as the app landing page for `www-n8` readiness
hints. The page explains domain, admin email from same domain, DNS-TXT,
SaaS-admin review and invitation. It must not collect mandate documents.

- [ ] **Step 4: Run tests and commit**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web tests.test_customer_tenant_onboarding`

Commit: `feat: add customer readiness onboarding page`

### Task 5: CLI Apply-Plan Preview

**Files:**
- Modify: `src/nac_cli/cli.py`
- Test: `tests/test_nac_cli.py`

- [ ] **Step 1: Write failing CLI test**

```python
def test_customer_onboarding_plan_cli_returns_json(self) -> None:
    rc, output = run_cli(
        "tenant",
        "customer-plan",
        "--domain",
        "kanzlei-notariat.example",
        "--tenant-slug",
        "kanzlei-notariat",
        "--admin-email",
        "admin@kanzlei-notariat.example",
        "--saas-admin-email",
        "saas-owner@example.com",
        "--format",
        "json",
    )
    self.assertEqual(rc, 0)
    payload = json.loads(output)
    self.assertEqual(payload["schema_version"], "nac.customer-tenant-plan/v0.1")
    self.assertTrue(payload["requires_owner_apply"])
```

- [ ] **Step 2: Run the test and verify RED**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_cli.NaCCliTests.test_customer_onboarding_plan_cli_returns_json`

Expected: unknown command.

- [ ] **Step 3: Add CLI command**

Add `nac tenant customer-plan --domain ... --tenant-slug ... --admin-email ... --saas-admin-email ... --format json`. The command prints the deterministic plan from `build_customer_tenant_plan`.

- [ ] **Step 4: Run tests and commit**

Run: `/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_customer_tenant_onboarding tests.test_nac_cli tests.test_nac_web`

Commit: `feat: expose customer tenant onboarding plan`

### Task 6: Final Verification And Protected PR

**Files:**
- All touched NaC files.

- [ ] **Step 1: Run strict verification**

Run: `GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict`

Expected: `STATUS: PASSED`.

- [ ] **Step 2: Inspect scope**

Run: `git status -sb`

Expected: only intended files are changed or the branch is clean after commit.

- [ ] **Step 3: Push and open PR**

Run: `git push -u origin agent/40-customer-tenant-onboarding`

Open a Protected PR against `main` with:

```text
Closes #40
Delivery Mode: Protected PR
Risk Gate: External Service / Human Approval
Validation: strict Quality Gate
```

- [ ] **Step 4: Set Project to Review**

Move Issue #40 and the PR to `Review` in the `NaC Control Plane` project.
