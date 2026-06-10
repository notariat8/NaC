# Customer DNS Success UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the public DNS success page read like a customer-facing notariat8 setup status instead of an internal DNS diagnostic page.

**Architecture:** Keep the existing `NaCLocalWebApp._tenant_dns_check_page` routing and split only the public-context HTML branch. Public HTML receives clearer labels, explicit domain/email reflection, and no internal/provider terms. Internal DNS diagnostics remain unchanged.

**Tech Stack:** Python stdlib HTTP app, `unittest`, existing NaC quality gate.

---

### Task 1: Customer DNS Success Assertions

**Files:**
- Modify: `tests/test_nac_web.py`
- Reference: `src/nac_web/server.py`

- [x] **Step 1: Write the failing test**

Update `test_www_n8_prospect_dns_check_stays_customer_facing` so the public DNS success page must contain:

```python
self.assertIn("Einrichtungsstatus öffnen", html)
self.assertIn("E-Mail-Adresse prüfen", html)
self.assertIn("Einladung noch nicht versendet", html)
self.assertIn("Technischer Nachweis", html)
self.assertIn("admin@kanzlei-notariat.example", html)
self.assertNotIn("Domain-Readiness öffnen", html)
self.assertNotIn("notariat8 führt Sie anschließend", html)
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_www_n8_prospect_dns_check_stays_customer_facing
```

Expected: FAIL because the current page still uses `Domain-Readiness öffnen` and does not show the new customer setup labels.

### Task 2: Public DNS Page Copy

**Files:**
- Modify: `src/nac_web/server.py`
- Test: `tests/test_nac_web.py`

- [x] **Step 1: Implement the minimal HTML change**

In `_tenant_dns_check_page`, update only the `public_context` branch:

- keep `notariat8 Domain-Check`,
- use `Einrichtungsstatus öffnen` for the readiness link,
- show a customer details card with domain, responsible email, domain status and invitation status,
- rename the DNS section to `Technischer Nachweis`,
- replace vague next-step lines with `E-Mail-Adresse prüfen`, `Einrichtung freigeben`, and `Einladung noch nicht versendet`.

- [x] **Step 2: Run the targeted tests**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_www_n8_prospect_dns_check_stays_customer_facing tests.test_nac_web.NaCLocalWebTests.test_customer_dns_check_page_renders_live_dns_result_without_raw_json
```

Expected: OK.

### Task 3: Verification And PR

**Files:**
- Verify: `src/nac_web/server.py`
- Verify: `tests/test_nac_web.py`
- Verify: `docs/de/superpowers/specs/2026-06-10-customer-dns-success-ux-design.md`

- [x] **Step 1: Run full test and quality checks**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
git diff --check
GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: tests OK, no whitespace errors, strict quality gate PASSED.

- [ ] **Step 2: Commit and open a protected PR**

Commit message:

```bash
feat: clarify customer dns success page
```

PR title:

```text
P1: Clarify customer DNS success page
```

PR body must link `Closes #81` and mention deployment requires Owner Release Approval after merge.
