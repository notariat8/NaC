# Notarkammer Demo 2026-06: Script And Fallbacks

This script supports an approximately 60-minute presentation of notariat8 and
NaC to the Notarkammer. It uses only public references, test/status pages and
mandate-data-free process models.

## Demo Goal

The demo shows that notarial matters are not linear four-step checklists.
notariat8 shows a controlled, editable and auditable flow with roles, evidence,
parallel work, critical path and protected app entry.

Central subject-matter point for this demo: NaC shows when XNP, Kartenleser
card-reader paths, XNotar, XJustiz, land-register and commercial-register
paths become relevant in the matter. NaC does not replace those systems. XNP
does not deliver land-register data to NaC; land-register and
commercial-register steps are modeled as local XNotar/XJustiz handoffs,
evidence and human-approved gates.

Demo Gate: continue the login flow only when the demo session is approved.
Without approval, intentionally show the workspace fail-closed; that is
security evidence, not a broken path.

Use local chamber/Berlin time in the demo: CET in winter (UTC+1), CEST in
summer (UTC+2). June 2026 uses CEST; never keep audit notes UTC-only.

## Preflight

Open these URLs in a fresh browser window before the demo:

1. `https://notariat8.de`
2. `https://notariat8.de/prozessmodell.html`
3. `https://app.notariat8.de/healthz`
4. `https://app.notariat8.de/login`
5. `https://app.notariat8.de/workspace`

Expected:

- The public page loads.
- The process model shows the Immobilienkaufvertrag.
- The app health page returns `ok`.
- The login page opens the notariat8 sign-in entry; the flow continues only
  with approval.
- The protected workspace remains closed without an approved session.

Additional read-only checks if time allows:

```text
https://app.notariat8.de/onboarding/readiness?audience=customer&domain_hint=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example
https://app.notariat8.de/onboarding/dns-check?audience=customer&domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example
https://app.notariat8.de/api/tenant/login-intent?tenant_hint=notariat-musterstadt
python scripts/nac.py tenant customer-plan --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --saas-admin-email saas-owner@example.com --format json
python scripts/nac.py tenant dns-check --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --format json
python scripts/nac.py bpmn validate
```

These checks show status and readiness. They submit no forms, read no secrets,
write nothing to the cloud control plane and open no real mandate data.
The login-intent check remains a redacted technical preparation evidence item.
It is not a browser surface for the Notarkammer demo.

## 60-Minute Run

### 0-5 Minutes: Public Entry

Open: `https://notariat8.de`

Say:

- "notariat8 does not show mandate data here; it shows approved process
  references."
- "The public view explains what is structured and reviewed."
- "The actual workspace remains protected."

Click sequence:

1. Open the home page.
2. Go to the matters/process section.
3. Select `Immobilienkaufvertrag`.
4. Open `Prozessmodell ansehen`.

### 5-20 Minutes: Immobilienkaufvertrag As Business Process

Open: `https://notariat8.de/prozessmodell.html`

Say:

- "The real-estate purchase agreement is not a short status flow."
- "Before and after notarization, reviews, external responses and evidence
  converge."
- "Duration values are planning values, not official averages."

Show:

- `Immobilienkaufvertrag`
- `Dauer und kritischer Pfad`
- `Parallel möglich`
- `Blockiert den kritischen Pfad`

### 20-28 Minutes: Critical Path And Parallel Work

Keep the companion talk track ready:
[BPMN Critical Path Talking Points](notarkammer-bpmn-critical-path-talking-points.md).

Say:

- "After notarization, several work streams can run in parallel: land register,
  financing, municipality, tax and evidence."
- "The critical path remains blocked where a response is needed for the next
  legal step."
- "When an external domain-system step is needed, BPMN shows the boundary:
  local XNP/Kartenleser card-reader readiness, an XNotar/XJustiz package or a
  land-register/commercial-register portal."
- "The goal is not automation at any price; it is visibility and auditability."

Show:

- Planning value "hours to days" for internal review.
- Planning value "weeks" for external responses.
- Planning value "weeks to months" for complex completion.
- Separate external gates: priority notice, release documents, municipal
  pre-emption right, tax clearance certificate and ownership transfer.
- Local gate "check card, XNP and signing path".
- XNotar/XJustiz step as package or exchange-folder evidence.

Say the safety line:

- "The cloud does not access XNP directly. The local workstation checks only
  readiness and evidence-capable status values. Productive XNP, register or
  land-register actions remain outside this demo."

### 28-35 Minutes: Public Onboarding, DNS And Request Status

Open:

- `https://app.notariat8.de/onboarding/readiness?audience=customer&domain_hint=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example`
- `https://app.notariat8.de/onboarding/dns-check?audience=customer&domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example`

Say:

- "This is the public onboarding path: domain, admin email, DNS guidance and
  setup status, but no mandate data."
- "The DNS check is a readiness status. `pending`, `mismatch` or `verified`
  are setup states, not live debugging."
- "An existing request can be shown as a status page. If the ATP store is
  `disabled` or `unavailable`, that remains a gate and we do not debug the
  database during the meeting."

Do not:

- Submit a new onboarding request.
- Run admin review POSTs.
- Open ATP wallet, DSN, secret reference or cloud console.

Fallback:

- Show an already loaded readiness/DNS page.
- If request status is unavailable, explain exactly that store-gate status as
  the safety boundary.

### 35-43 Minutes: Editable Process And XNP/XNotar Boundary

Open locally if available:

```text
python scripts/nac.py web
http://127.0.0.1:8766/bpmn/immobilienkaufvertrag/edit
```

Say:

- "BPMN is the source for the business model."
- "The editor is intended for model maintenance, not real mandate documents."
- "Changes go through GitHub pull requests and validation."
- "XNP-adjacent steps remain local workstation gates. XNotar/XJustiz is the
  file bridge for register and land-register communication, not hidden cloud
  automation."

If the local editor is unavailable, use this fallback:

- `https://notariat8.de/prozessmodell.html`
- GitHub reference only as technical evidence, not as the user-facing view.
- The statement remains the same: XNP does not deliver land-register data to
  NaC.

### 43-52 Minutes: App Entry And Protected Workspace

Open: `https://app.notariat8.de/login`

Say:

- "The app does not open the workspace directly."
- "Session and role are checked before the workspace opens."
- "Without a valid session, `https://app.notariat8.de/workspace` remains
  closed."
- "Protected start is metadata-only: status, gate and reason, but no matter
  file and no document contents."
- "The ATP healthcheck is only a store gate. `https://app.notariat8.de/healthz`
  intentionally stays short and non-sensitive."
- "We continue login only if it is approved for this demo; otherwise
  fail-closed is the intended result."

Show:

1. Login page.
2. Only with approval: protected start status or sign-in step.
3. `https://app.notariat8.de/workspace` without a session as the closed view.

Do not show:

- No login-intent JSON and no technical login-intent endpoint as a browser
  surface. If this read-only check is needed, evaluate it only in redacted
  preparation.

### 52-55 Minutes: Short Comparison Process

Show:

- `Unterschriftsbeglaubigung`

Say:

- "The short matter has different risks and different duration logic."
- "The model must fit each usecase; it cannot be one generic notarial flow."

### 55-60 Minutes: Close

Say:

- "This is intentionally not a complete notarial product yet."
- "What is demonstrable today is the controlled path: public reference,
  business model, process view, protected entry and GitHub governance."
- "The next step is deeper business-process detail and a better visual
  editor/critical-path view."

## 5-Minute Short Version

1. Open `https://notariat8.de`.
2. Go to the Immobilienkaufvertrag.
3. Show `https://notariat8.de/prozessmodell.html`.
4. Explain duration, parallel work and critical path.
5. Explain XNP/Kartenleser as a local gate and XNotar/XJustiz as the handoff
   path.
6. Open `https://app.notariat8.de/login`.
7. Show `https://app.notariat8.de/workspace` without a session as closed.
8. Close: "No mandate data, controlled model maintenance, protected workspace."

## 20-Minute Fallback

1. 0-3 minutes: open `https://notariat8.de`.

   Say: "We show only public process references. No mandate data, no real
   identity documents, no real deeds."

2. 3-9 minutes: show `https://notariat8.de/prozessmodell.html`.

   Say: "The Immobilienkaufvertrag needs duration logic, parallel work,
   critical path and domain Gates."

3. 9-13 minutes: explain XNP local as a system boundary.

   Say: "XNP, Kartenleser card reader, SAK lite, secureFramework, role and
   official activity context are checked on the local workstation. NaC starts
   no productive XNP action here."

4. 13-16 minutes: explain XNotar/XJustiz as a handoff boundary.

   Say: "Register and land-register communication remains a package,
   exchange-folder or portal boundary. We open no real packages, register data
   or property data."

5. 16-18 minutes: show `https://app.notariat8.de/login`.

   Say: "Login only with demo approval. Without approval, we go directly to
   `https://app.notariat8.de/workspace` and show fail-closed behavior."

6. 18-20 minutes: close.

   Say: "NaC shows BPMN, Evidence and Gate. The domain systems remain visibly
   bounded; there is no productive register, land-register or XNP claim."

## Fallbacks

| Risk | Fallback |
| --- | --- |
| Public page loads slowly | Use a local copy or an already opened browser tab with `https://notariat8.de/prozessmodell.html`. |
| App login is slow | Open `https://app.notariat8.de/workspace` directly and explain fail-closed behavior. |
| Identity provider takes too long | Use the Stop-Line: "External sign-in is not part of the business-process demo; the closed workspace is the relevant security evidence here." |
| Login flow is not approved | Do not attempt login; go directly to `https://app.notariat8.de/workspace` and show fail-closed behavior. |
| Local BPMN editor is unavailable | Use the public process model page and mention GitHub PRs/validators only briefly as governance evidence. |
| XNP or card reader is unavailable locally | Do not show a live XNP action; explain the BPMN gate and the XNP/XNotar demo contract. |
| Live DNS or network is unstable | Do not show a live new-customer setup; use the existing readiness/DNS status page only. |

## Stop-Lines

- If login or identity verification takes longer than two minutes, do not debug
  live. Switch to the protected workspace and process viewer.
- If login approval is missing, do not continue the login flow; the closed
  workspace is then the demo statement.
- If a link shows JSON instead of HTML, stop and restart through the intended
  button path.
- If a page exposes internal technical terms, do not explain them; return to
  the public process model page.
- Do not show real mandate data, real identity documents, real deeds or
  productive register/land-register actions.
- Do not claim that NaC receives land-register data directly from XNP.
- Do not make a productive claim about XNP, XNotar, XJustiz, register or
  land-register automation.

## Demonstrable Core Claims

- notariat8 is centered on notarial work.
- The Immobilienkaufvertrag requires parallel work and critical path.
- Duration values are editable planning values.
- The public view contains no mandate data.
- XNP, Kartenleser, XNotar and XJustiz are shown as visible domain-system
  boundaries in the process.
- The app opens the workspace only after security checks.
- GitHub protected pull requests make model changes auditable.
