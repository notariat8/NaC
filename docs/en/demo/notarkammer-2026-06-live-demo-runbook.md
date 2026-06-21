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

## T-03:00 Preflight Order

| Order | Live-Test | Expected | Fallback |
| --- | --- | --- | --- |
| 1 | `https://notariat8.de` | Home page loads without mandate data. | Use an already loaded tab. |
| 2 | `https://notariat8.de/prozessmodell.html` | Immobilienkaufvertrag, duration logic and critical path are visible. | Use a screenshot or opened tab. |
| 3 | `https://app.notariat8.de/healthz` | Short, non-sensitive status. | Close the tab and show the workspace boundary. |
| 4 | `https://app.notariat8.de/login` | Login page opens; no real credentials are entered; continue the login flow only when approved. | Do not debug, switch to the process model. |
| 5 | `https://app.notariat8.de/workspace` | Without an approved session, the workspace remains closed. | Explain fail-closed as security evidence. |
| 6 | XNP local | Card path, XNP localhost `12774` through `12784` and role are locally plausible only. | Show no live XNP action; mark Gate as `manual_review` or `blocked`. |
| 7 | XNotar/XJustiz handoff | Exchange folder and package boundary are checkable synthetically or empty. | Open no package; explain only the handoff boundary. |

## 60-Minute Live Order

1. 0-5 minutes: show `https://notariat8.de` and state clearly that the public
   view contains no mandate data.
2. 5-20 minutes: open `https://notariat8.de/prozessmodell.html`; explain
   Immobilienkaufvertrag, duration logic, parallel work and critical path.
3. 20-30 minutes: show domain-system boundaries: XNP local for readiness, card
   reader and signature path; XNotar/XJustiz handoff for register and
   land-register communication.
4. 30-40 minutes: if locally available, show the BPMN editor; otherwise stay
   on the public process model. NaC BPMN/Evidence/Gate is the point, not live
   automation.
5. 40-50 minutes: show `https://app.notariat8.de/login` and
   `https://app.notariat8.de/workspace` as the protected entry. Continue
   login only if it was pre-approved for this demo; otherwise show the closed
   workspace as the expected result.
6. 50-55 minutes: mention Unterschriftsbeglaubigung as the short comparison
   process.
7. 55-60 minutes: close with visible domain-system boundaries, Protected PRs,
   redacted Evidence and no productive register/land-register actions.

## 5-Minute Short Order

1. Open `https://notariat8.de`.
2. Show `https://notariat8.de/prozessmodell.html`.
3. Name Immobilienkaufvertrag, duration, parallel work and critical path.
4. Explain XNP local as a readiness Gate.
5. Explain XNotar/XJustiz handoff as a package/exchange-folder boundary.
6. Show `https://app.notariat8.de/login` and the closed workspace.
7. Close with: NaC BPMN/Evidence/Gate makes work visible and auditable.

## 20-Minute Fallback

1. 0-3 minutes: open `https://notariat8.de` and state that the demo shows only
   public process references without mandate data.
2. 3-9 minutes: show `https://notariat8.de/prozessmodell.html`; name
   Immobilienkaufvertrag, duration logic, parallel work and critical path.
3. 9-13 minutes: explain XNP local, card reader, SAK lite, secureFramework,
   role and official activity context as the workstation boundary and Demo
   Gate. Start no productive XNP action.
4. 13-16 minutes: explain XNotar/XJustiz as the package/exchange-folder
   boundary for register and land-register communication. Open no real
   packages, register data or property data.
5. 16-18 minutes: show `https://app.notariat8.de/login`. Continue the login
   flow only with explicit approval; otherwise go directly to
   `https://app.notariat8.de/workspace` and show fail-closed behavior.
6. 18-20 minutes: summarize the Stop-Lines: NaC models BPMN, Evidence and
   Gate; external domain systems remain boundaries; no real data and no
   productive claim.

## Stop-Lines

- Stop-Line: "We are not debugging live; the demo shows the checked process
  path."
- Stop-Line: "Without approval, we do not continue the login flow; the closed
  workspace is then the expected demo result."
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
