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
- The login page opens the notariat8 sign-in entry.
- The protected workspace remains closed without a session.

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

### 20-30 Minutes: Critical Path And Parallel Work

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
- Local gate "check card, XNP and signing path".
- XNotar/XJustiz step as package or exchange-folder evidence.

Say the safety line:

- "The cloud does not access XNP directly. The local workstation checks only
  readiness and evidence-capable status values. Productive XNP, register or
  land-register actions remain outside this demo."

### 30-40 Minutes: Editable Process And XNP/XNotar Boundary

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

### 40-50 Minutes: App Entry And Protected Workspace

Open: `https://app.notariat8.de/login`

Say:

- "The app does not open the workspace directly."
- "Session and role are checked before the workspace opens."
- "Without a valid session, `https://app.notariat8.de/workspace` remains
  closed."

Show:

1. Login page.
2. Protected start status or sign-in step.
3. `https://app.notariat8.de/workspace` without a session as the closed view.

### 50-55 Minutes: Short Comparison Process

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

## Fallbacks

| Risk | Fallback |
| --- | --- |
| Public page loads slowly | Use a local copy or an already opened browser tab with `https://notariat8.de/prozessmodell.html`. |
| App login is slow | Open `https://app.notariat8.de/workspace` directly and explain fail-closed behavior. |
| Identity provider takes too long | Use the Stop-Line: "External sign-in is not part of the business-process demo; the closed workspace is the relevant security evidence here." |
| Local BPMN editor is unavailable | Use the public process model page and mention GitHub PRs/validators only briefly as governance evidence. |
| XNP or card reader is unavailable locally | Do not show a live XNP action; explain the BPMN gate and the XNP/XNotar demo contract. |
| Live DNS or network is unstable | Do not show a live new-customer setup; use the existing readiness/DNS status page only. |

## Stop-Lines

- If login or identity verification takes longer than two minutes, do not debug
  live. Switch to the protected workspace and process viewer.
- If a link shows JSON instead of HTML, stop and restart through the intended
  button path.
- If a page exposes internal technical terms, do not explain them; return to
  the public process model page.
- Do not show real mandate data, real identity documents, real deeds or
  productive register/land-register actions.
- Do not claim that NaC receives land-register data directly from XNP.

## Demonstrable Core Claims

- notariat8 is centered on notarial work.
- The Immobilienkaufvertrag requires parallel work and critical path.
- Duration values are editable planning values.
- The public view contains no mandate data.
- XNP, Kartenleser, XNotar and XJustiz are shown as visible domain-system
  boundaries in the process.
- The app opens the workspace only after security checks.
- GitHub protected pull requests make model changes auditable.
