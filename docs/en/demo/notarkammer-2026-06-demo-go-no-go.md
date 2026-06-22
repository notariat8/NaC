# Notarkammer Demo 2026-06: Go/No-Go Matrix

Status: presentation decision for the notary chamber demo. This matrix does
not replace review or approval; it prevents spontaneous live decisions during
the meeting.

## Decision

| Area | Go | Warn | Stop |
| --- | --- | --- | --- |
| Public site | `notariat8.de` and the process model load. | Site loads slowly, but without internal wording. | Site shows provider, cloud, secret or mandate data. |
| Process model | Immobilienkaufvertrag, duration, parallel work, critical path and XNP boundaries are visible. | Only screenshot or fallback evidence is available. | Process model cannot be explained or implies productive XNP/register action. |
| App health | `/healthz` is reachable or the status is explainable as a technical boundary. | Healthcheck is slow or briefly unavailable. | Diagnosis would open secrets, wallets, DSN or provider operations. |
| Login | Login page opens and remains user-readable. | Login remains fail-closed; continue with the process path. | Callback values, tokens, claims or credentials would be visible. |
| Workspace | Closed without verified session or metadata-only status. | Fail-closed is slow but explainable. | Full workspace or mandate data would become visible without a gate. |
| XNP/card reader | Only local readiness boundary or prepared evidence. | Local workstation is unavailable; explain the boundary. | Productive XNP, signature, register or land-register action would be triggered. |
| Evidence | Redacted evidence is prepared and reviewed. | One evidence item is missing; fall back to script. | Evidence contains names, matter values, login fields, callback values or payloads. |

## Presentation Decision

- **Go:** All core areas are `Go`, or at most one area is `Warn` with prepared
  fallback evidence.
- **Warn-Go:** Two warnings are acceptable when the core line remains visible:
  BPMN, XNP boundary, protected entry and fail-closed boundary.
- **No-Go:** Any `Stop` ends the live path. Use only prepared screenshots,
  script and Q&A afterwards.

## Non-Negotiable Stop Lines

- No real mandate data, identity documents, deeds, register data or property
  data.
- No tokens, claims, callback values, secrets, PINs, wallets or DSN.
- No productive XNP, XNotar, register or land-register action.
- No provider, cloud or internal operations details on user-facing surfaces.
- No JSON endpoint as a user interface.

## Evidence

Before the demo starts, record:

- Date/time in CET/CEST.
- Smoke result with `summary-only`.
- Evidence IDs from the fallback manifest.
- Decision `Go`, `Warn-Go` or `No-Go`.
- Name of the person who made the presentation decision.
