# Notarkammer Demo 2026-06: Live Runbook

Status: Protected PR ready presentation checklist for the 60-minute live demo.

This runbook merges the already landed demo tracks:

- XNP demo contract: `notarkammer-xnp-demo-contract.md`
- 60-minute script: `notarkammer-2026-06-demo-script.md`
- XNP preflight/audit trail: `notarkammer-2026-06-demo-preflight.md`

Scope for this PR: only `docs/de`, `docs/en` and `tests`. No runtime, No OCI,
no infrastructure, no release, no apply, no runtime change, no cloud change,
no secrets and no real mandate data. All examples remain synthetic.

## Core Line

1. XNP local: XNP, card reader, SAK lite, secureFramework, role and official
   activity context are checked only on the approved workstation.
2. XNotar/XJustiz handoff: register and land-register paths are shown as an
   exchange folder, XJustiz package, local import and human confirmation.
3. NaC BPMN/Evidence/Gate: NaC shows the domain-system boundary in BPMN,
   accepts only redacted Evidence and blocks or opens the next step through an
   explicit Gate.
4. Hard statement: XNP does not deliver land-register data to NaC.
5. Hard statement: no automated external XNotar import trigger.
6. Demo Gate: continue login and workspace only when the demo session is
   approved; otherwise show the fail-closed boundary.
7. Public onboarding can be shown today as a GET/status path: readiness, DNS
   check and request status, but no new request is submitted during the
   meeting.
8. ATP healthcheck is a store gate: `enabled`, `disabled`, `unavailable` or
   `not_checked`; secrets, wallets, DSN and OCI writes are not opened.

## Time Wording

The presentation uses local chamber/Berlin time: CET in winter (UTC+1) and
CEST in summer (UTC+2). June 2026 uses CEST. Write audit notes as CET/CEST
with optional technical UTC context, never UTC-only.

## Open Browser Tabs Beforehand

No live searching, no browser history and no spontaneous admin or cloud
consoles during the meeting. Before starting, open only these tabs:

| Tab | Page | Purpose | Fallback |
| --- | --- | --- | --- |
| Tab 1 | `https://notariat8.de` | Public entry point. | Keep the loaded tab. |
| Tab 2 | `https://notariat8.de/prozessmodell.html` | BPMN, duration, parallel work and critical path. | Use the approved screenshot. |
| Tab 3 | `https://app.notariat8.de/onboarding/dns-check?audience=customer&domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example` | DNS/readiness evidence with a synthetic domain. | Explain setup status. |
| Tab 4 | `https://app.notariat8.de/onboarding/requests/<request_id>?audience=customer` | existing request status. | Explain Store Gate `unavailable`. |
| Tab 5 | `https://app.notariat8.de/login` | protected entry. | Do not debug login live. |
| Tab 6 | `https://app.notariat8.de/workspace` | fail-closed or metadata-only workspace. | Explain the closed boundary. |

## T-03:00 Preflight Order

| Order | Live-Test | Expected | Fallback |
| --- | --- | --- | --- |
| 1 | `https://notariat8.de` | Home page loads without mandate data. | Use an already loaded tab. |
| 2 | `https://notariat8.de/prozessmodell.html` | Immobilienkaufvertrag, duration logic and critical path are visible. | Use a screenshot or opened tab. |
| 3 | `https://app.notariat8.de/healthz` | Short, non-sensitive status. | Close the tab and show the workspace boundary. |
| 4 | `https://app.notariat8.de/onboarding/readiness?audience=customer&domain_hint=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example` | Public onboarding shows setup status without mandate data. | Show the loaded tab; submit no request. |
| 5 | `https://app.notariat8.de/onboarding/dns-check?...` and CLI DNS check | Expected TXT record and status are visible. | Explain `pending`/`mismatch` as setup status. |
| 6 | `/onboarding/requests/<request_id>?audience=customer` | Status page for an existing request or `unavailable` as the store gate. | Do not debug ATP. |
| 7 | `https://app.notariat8.de/login` | Login page opens; no real credentials are entered; continue the login flow only when approved. | Do not debug, switch to the process model. |
| 8 | `https://app.notariat8.de/api/tenant/login-intent?tenant_hint=notariat-musterstadt` | Read-only login intent without credentials. | If JSON/error is visible, show login page or workspace boundary. |
| 9 | `https://app.notariat8.de/workspace` | Without an approved session, the workspace remains closed; metadata status only, no matter file. | Explain fail-closed as security evidence. |
| 10 | BPMN validation | `python scripts/nac.py bpmn validate` stays green; `bpmn show immobilienkaufvertrag` is readable. | Use the public process-model page. |
| 11 | ATP healthcheck status | `/healthz` shows runtime status; ATP store gate is only classified as `enabled`, `disabled`, `unavailable` or `not_checked`. | Open no secrets, wallets, DSN or OCI CLI. |
| 12 | XNP local | Card path, XNP localhost `12774` through `12784` and role are locally plausible only. | Show no live XNP action; mark Gate as `manual_review` or `blocked`. |
| 13 | XNotar/XJustiz handoff | Exchange folder and package boundary are checkable synthetically or empty. | Open no package; explain only the handoff boundary. |

## Exact Read-only Checks

```bash
curl -fsS https://app.notariat8.de/healthz
curl -fsS "https://app.notariat8.de/onboarding/readiness?audience=customer&domain_hint=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example" >/tmp/nac-onboarding-readiness.html
curl -fsS "https://app.notariat8.de/api/tenant/login-intent?tenant_hint=notariat-musterstadt" >/tmp/nac-login-intent.json
curl -i "https://app.notariat8.de/workspace"
python scripts/nac.py tenant customer-plan --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --saas-admin-email saas-owner@example.com --format json
python scripts/nac.py tenant dns-check --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --format json
python scripts/nac.py tenant apply-request --tenant-slug kanzlei-notariat --domain kanzlei-notariat.example --admin-email admin@kanzlei-notariat.example --admin-display-name "Admin Notariat" --identity-domain-url https://idcs.example.invalid --identity-domain-id ocid1.domain.oc1.example --dns-verified --owner-approval-id DEMO-OWNER --audit-event-id DEMO-AUDIT --rollback-plan-id DEMO-ROLLBACK --dry-run --format json
python scripts/nac.py bpmn validate
python scripts/nac.py bpmn show immobilienkaufvertrag --format text
```

Do not execute: `POST /onboarding/requests`, `POST /admin/onboarding/review`,
OCI CLI, Vault/wallet reads, ATP schema changes or real Identity
provisioning.

## 60-Minute Live Order

1. 0-5 minutes: show `https://notariat8.de` and state clearly that the public
   view contains no mandate data.
2. 5-20 minutes: open `https://notariat8.de/prozessmodell.html`; explain
   Immobilienkaufvertrag, duration logic, parallel work and critical path.
3. 20-28 minutes: show public onboarding, DNS readiness and existing request
   status as a customer-readable setup path. Submit no new request during the
   meeting.
4. 28-35 minutes: show domain-system boundaries: XNP local for readiness, card
   reader and signature path; XNotar/XJustiz handoff for register and
   land-register communication.
5. 35-43 minutes: if locally available, show the BPMN editor; otherwise stay
   on the public process model. NaC BPMN/Evidence/Gate is the point, not live
   automation.
6. 43-52 minutes: show `https://app.notariat8.de/login`,
   `https://app.notariat8.de/api/tenant/login-intent?...` and
   `https://app.notariat8.de/workspace` as the protected entry. Continue
   login only if it was pre-approved for this demo; otherwise show the closed
   workspace with the metadata-only gate as the expected result.
7. 52-55 minutes: mention Unterschriftsbeglaubigung as the short comparison
   process.
8. 55-60 minutes: close with visible domain-system boundaries, Protected PRs,
   redacted Evidence and no productive register/land-register actions.

## 5-Minute Short Order

1. Open `https://notariat8.de`.
2. Show `https://notariat8.de/prozessmodell.html`.
3. Name Immobilienkaufvertrag, duration, parallel work and critical path.
4. Show public onboarding/DNS status as a GET-only setup path.
5. Explain XNP local as a readiness Gate.
6. Explain XNotar/XJustiz handoff as a package/exchange-folder boundary.
7. Show `https://app.notariat8.de/login`, login intent and the closed
   metadata-only workspace.
8. Close with: NaC BPMN/Evidence/Gate makes work visible and auditable.

## 20-Minute Fallback

1. 0-3 minutes: open `https://notariat8.de` and state that the demo shows only
   public process references without mandate data.
2. 3-9 minutes: show `https://notariat8.de/prozessmodell.html`; name
   Immobilienkaufvertrag, duration logic, parallel work and critical path.
3. 9-12 minutes: show public onboarding readiness and DNS status. If request
   status or ATP is unavailable, explain `unavailable` as the store gate.
4. 12-15 minutes: explain XNP local, card reader, SAK lite, secureFramework,
   role and official activity context as the workstation boundary and Demo
   Gate. Start no productive XNP action.
5. 15-17 minutes: explain XNotar/XJustiz as the package/exchange-folder
   boundary for register and land-register communication. Open no real
   packages, register data or property data.
6. 17-19 minutes: show `https://app.notariat8.de/login`. Continue the login
   flow only with explicit approval; otherwise go directly to
   `https://app.notariat8.de/workspace` and show fail-closed behavior.
7. 19-20 minutes: summarize the Stop-Lines: NaC models BPMN, Evidence and
   Gate; external domain systems remain boundaries; no real data and no
   productive claim.

## Stop-Lines

- Stop-Line: "We are not debugging live; the demo shows the checked process
  path."
- Stop-Line: "Without approval, we do not continue the login flow; the closed
  workspace is then the expected demo result."
- Stop-Line: "Do not read the callback URL aloud and show no values from
  `code` or `state`; close the tab or switch to `/workspace`."
- Stop-Line: "XNP stays local. XNP does not deliver land-register data to NaC."
- Stop-Line: "XNotar/XJustiz is a handoff boundary here, not hidden cloud
  automation."
- Stop-Line: "Without Evidence, the NaC Gate remains blocked."
- Stop-Line: "This demo contains no release, apply, runtime, OCI or cloud
  action."

## Protected PR Evidence

- Branch: `agent/notarkammer-live-demo-runbook-2`.
- Changed surfaces: `docs/de/demo/`, `docs/en/demo/`, `tests/`.
- Expected checks: focused demo runbook tests, existing demo contract,
  demo script and preflight tests.
- Audit trail: commit SHA, test output, branch and PR link; no person, matter,
  deed, identity, register or property data.
