# Notarkammer Demo 2026-06: Login/Portal Diagnostics

Status: internal Protected PR track for demo decisions, no runtime change.
Scope: `docs/de/demo`, `docs/en/demo` and `tests/test_notarkammer_`. No
secrets, no tokens, no claims, no provider details, no callback values and no
mandate data.

This runbook answers only three questions during the meeting: what is showable,
what is a stopper, and what is the fallback. It is not a technical root-cause
analysis and it exposes no provider or session details.

## Status Classes

| Class | Meaning | Demo decision |
| --- | --- | --- |
| Green / Grün | Token exchange, token validation, role check and session are green. | Continue live login only when the demo approval is in place. |
| Yellow / Gelb | Sign-in received, but at least one gate is open, slow or not reliable enough. | Go to fallback: process model fallback, readiness fallback or workspace boundary fallback. |
| Red / Rot | Token exchange is invalid, technically unavailable or session/role remains closed without reliable evidence. | Stop the live login path; do not debug live. |

Continue only when token exchange, token validation, role check and session are
green. With yellow or red, do not guess, reconfigure or open anything
productive.

## Current Live Diagnosis

Known browser state at `/auth/callback`:

| Visible signal | Classification | Meeting line | Fallback |
| --- | --- | --- | --- |
| `Sign-in received` | Yellow while downstream checks are open. | "Sign-in was received; the app stays closed until checks complete." | Readiness fallback or process model fallback. |
| `Token exchange: invalid` | Red. | "Login is fail-closed; we show the checked process path." | Stop the live login path. |
| `Token exchange: technically unavailable` | Red. | "Technical sign-in is not demo-stable; we do not debug live." | Process model fallback. |
| `Token validation: open` | Yellow. | "Without validated sign-in, we open no workspace." | Workspace boundary fallback. |
| `Role check open` | Yellow. | "The role is not yet showably confirmed." | Show /workspace only as fail-closed or metadata-only boundary. |
| `Session open` | Yellow. | "The session is not reliably complete." | Workspace boundary fallback. |

## Gate Criteria

| Gate | Green | Yellow | Red |
| --- | --- | --- | --- |
| Token exchange | Confirmed without visible technical details. | Sign-in received, but result open. | `Token exchange: invalid` or `Token exchange: technically unavailable`. |
| Token validation | Validation complete. | Validation open or not started. | Validation fails or remains without reliable evidence. |
| Role check | Demo role confirmed. | Role check open. | No demo role can be evidenced. |
| Session | Session complete and demo-approved. | Session open. | No reliable session. |

## Fallback Criteria

Go to fallback as soon as a gate is yellow or red and does not become green
within the pre-approved demo time.

- Process model fallback: show `https://notariat8.de/prozessmodell.html` and
  explain Immobilienkaufvertrag, duration, parallel work and critical path.
- Readiness fallback: show prepared readiness/DNS/request-status surfaces with
  synthetic data; submit no new request.
- Workspace boundary fallback: show /workspace only as fail-closed or
  metadata-only boundary; no file content, no mandate data.
- Stop the live login path when token exchange is invalid or technically
  unavailable.
- Do not debug live, open no cloud console, provider values, callback values
  or tokens.

## Showable, Stopper, Fallback

| State | Showable | Stopper | Fallback |
| --- | --- | --- | --- |
| Green | Login page, protected entry, approved start view without real data. | None. | Switch to the process model if the path slows down. |
| Yellow | Sign-in received, closed workspace boundary, readiness status. | Do not claim the protected workspace as successful. | Process model fallback or workspace boundary fallback. |
| Red | Fail-closed status as security evidence. | Stop the live login path. | Process model fallback and technical follow-up after the meeting. |

## Redaction Rules

Public output stays short and non-technical:

- no secrets
- no tokens
- no claims
- no provider details
- no callback values
- no mandate data
- no real IDs, files, deeds, identity documents, register or property data
- no runtime change, no OCI/IaC change, no productive action

Allowed internal ticket wording: status class, gate name, short error text and
fallback decision. Not allowed: raw values from browser address, response,
session, token, claim, provider configuration or mandate context.

## Stop Lines

- "Login is fail-closed; we now show the checked process path."
- "Without green token, role and session checks, we open no workspace."
- "The demo stays with redacted diagnostics; technical details are checked
  after the meeting."
- "This is not a productive login proof; it is a safe demo decision."
