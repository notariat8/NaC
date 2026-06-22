# Notarkammer Demo 2026-06: 60-Minute Live Test Script

Status: Operational script for demo day. The goal is live demonstrable in 60
minutes, not perfect. Protected PR only; no productive submission, no real
mandate data, no secrets.

## Purpose

This script runs the Notarkammer demo as a live test. It names browser start
points, order, expected visible results and failover cards. The demo shows the
public process view, protected entry, local domain-system boundaries and an
auditable NaC Gate.

## Safety Frame

- Protected PR only: changes and evidence move through branch, review and pull
  request.
- No productive submission: no register filing, no land-register
  communication and no domain-system action from the demo.
- No real mandate data: open no person, deed, identity, register or property
  data.
- No secrets: show no credentials, PINs, tokens, keys or internal operating
  details.
- The operator does not debug live; do not debug live. If something differs, use the matching
  Failover Card.

## Browser Start Points

| Order | Start point | Expected visible result | Operator line |
| --- | --- | --- | --- |
| 1 | `https://notariat8.de` | public start page loads; no mandate data is visible. | "This is the public entry view." |
| 2 | `https://notariat8.de/prozessmodell.html` | process model loads with Immobilienkaufvertrag, duration logic and critical path. | "This makes the process auditable, not productively executed." |
| 3 | `https://app.notariat8.de/healthz` | non-sensitive status or closed boundary. | "The status is only a technical precheck without matter content." |
| 4 | `https://app.notariat8.de/login` | Login or OIDC interstitial; enter no real credentials. | "Login continues only with demo approval." |
| 5 | `https://app.notariat8.de/workspace` | protected workspace remains closed without an approved session. | "Fail-closed is an expected safety result here." |

## 60-Minute Live Order

| Time | Action | Expected visible result | If it does not work |
| --- | --- | --- | --- |
| 0-5 | Open `https://notariat8.de`. | public start page is visible without matter or mandate reference. | Failover: www-n8 does not load. |
| 5-15 | Open `https://notariat8.de/prozessmodell.html`. | process model shows Immobilienkaufvertrag, roles, duration and critical path. | Failover: BPMN viewer does not load. |
| 15-25 | Explain notary, staff, client interface, Evidence and Gate on the process model. | The audience sees which steps are open, checked or blocked. | Stay with the screenshot; no live repair. |
| 25-35 | Explain XNP/card reader/register/land register as boundaries. | No domain system opens productively; only access-point logic is visible. | Failover: XNP/card reader is unavailable. |
| 35-45 | Show `https://app.notariat8.de/healthz`, then `https://app.notariat8.de/login`. | Status or login/OIDC boundary appears; no real credentials. | Failover: app login only shows the OIDC interstitial. |
| 45-52 | Show `https://app.notariat8.de/workspace`. | protected workspace is reachable only with an approved session; otherwise fail-closed. | Explain the closed boundary as the demo result. |
| 52-55 | Short comparison: Unterschriftsbeglaubigung as a smaller process. | Same Gate logic, fewer process steps. | Keep the comparison verbal. |
| 55-60 | Close. | Visible Evidence: browser paths, boundaries, Protected PR, no productive submission. | Use the Stop-Line and capture questions. |

## Failover Cards

Prepared screenshots and fallback views must be approved in the
[`Fallback Evidence Manifest`](notarkammer-2026-06-demo-fallback-evidence-manifest.md).

### www-n8 does not load

1. Do not debug live.
2. Use an already opened tab or prepared screenshot; use a prepared screenshot.
3. Then try `https://notariat8.de/prozessmodell.html` directly.
4. If that also fails, speak the 20-minute fallback from the existing runbook
   and show the PR evidence.

### app login only shows the OIDC interstitial

1. Enter no credentials and do not force login.
2. Explain the OIDC interstitial as a protection boundary.
3. Continue only with explicit demo approval.
4. Without approval, switch to `https://app.notariat8.de/workspace` and show
   fail-closed behavior.

### XNP/card reader is unavailable

1. Start no live XNP action.
2. XNP is a local workstation boundary.
3. Kartenleser/card reader is an access point, not a NaC data store.
4. Mark the Gate in the talk track as `manual_review` or `blocked`.
5. Register is an external destination and Grundbuch/land register is an
   external destination; NaC triggers no productive domain-system action.

### BPMN viewer does not load

1. Do not debug live.
2. Switch to a prepared screenshot or existing runbook.
3. Keep the visible statement: process model, Evidence, Gate and
   domain-system boundary.
4. If needed, explain the Gate as `blocked` and move to protected entry.

## Boundaries And Access Points

- XNP is a local workstation boundary: NaC describes readiness and handoff
  points, but does not operate XNP productively.
- Kartenleser/card reader is an access point: the card reader remains local on
  the approved workstation.
- Register is an external destination: commercial-register and
  association-register paths are external target systems with human approval.
- Grundbuch/land register is an external destination: land-register access
  remains outside NaC and without demo filing.
- XNP does not deliver land-register data to NaC.
- XNotar/XJustiz is a package and exchange boundary, not hidden automation.
- no productive submission, no real mandate data, no secrets.

## Closing Evidence

At the end, show or name only this evidence:

- Browser start points and visible results.
- Protected PR only as change and audit trail.
- Local XNP/card reader boundary.
- Register and land-register boundary as external access points.
- Failover result: screenshot, OIDC boundary, `manual_review`, `blocked` or
  fail-closed.
