# Notarkammer Demo 2026-06: Fallback Evidence Manifest

Status: protected demo evidence for prepared screenshots and fallback views. No
productive submission, no real mandate data, no secrets.

This manifest defines which prepared views may be used in the Notarkammer demo
when live pages are slow or a local workstation is not ready. It does not
replace live checks; it prevents ad-hoc debugging during the meeting.

## Allowed prepared evidence

| Evidence | Allowed content | Purpose |
| --- | --- | --- |
| `notariat8.de` home page | Public home page without matter or mandate reference. | Show the entry point if the page does not load. |
| `notariat8.de/prozessmodell.html` | Immobilienkaufvertrag process model with duration logic, parallel work and critical path. | Explain BPMN logic if the viewer does not load. |
| `app.notariat8.de/workspace` | Closed or metadata-only view with fail-closed status. | Show the security boundary when login is not continued. |
| XNP and card reader readiness | Local status only: `ready`, `manual_review` or `blocked`; no raw data. | Explain XNP as a local workstation boundary. |
| Protected PR | Pull request, checks and redacted test output. | Show change and review evidence. |

## Prepared Evidence Package

| Evidence ID | Artifact name | Allowed view | Status | After the demo |
| --- | --- | --- | --- | --- |
| `NK-EVIDENCE-001-public-home` | `notariat8-public-home-redacted.png` | Public `notariat8.de` home page. | `redacted`, `reviewed` | `delete-after-demo` |
| `NK-EVIDENCE-002-process-model` | `notariat8-process-model-immobilienkaufvertrag-redacted.png` | Process model without mandate data. | `redacted`, `reviewed` | `delete-after-demo` |
| `NK-EVIDENCE-003-workspace-boundary` | `notariat8-workspace-boundary-redacted.png` | Closed or metadata-only workspace boundary. | `redacted`, `reviewed` | `delete-after-demo` |
| `NK-EVIDENCE-004-local-xnp-readiness` | `notariat8-local-xnp-readiness-redacted.png` | Local readiness status without raw data. | `redacted`, `reviewed` | `delete-after-demo` |
| `NK-EVIDENCE-005-protected-pr` | `notariat8-protected-pr-checks-redacted.png` | PR checks and review trail without secrets. | `redacted`, `reviewed` | `delete-after-demo` |

Each artifact must be marked `redacted` and `reviewed` before the
presentation. Artifacts missing either status are not shown.

## Disallowed evidence

- no real mandate data
- no identity documents
- no deeds
- no register extracts
- no land-register data
- no credentials
- no PINs
- no tokens
- no keys
- no productive submission
- no productive XNP, register or land-register action
- no login fields
- no callback values
- no authorization code
- no state value
- no session cookie
- no provider details
- no real names
- no XNP payload
- no register payload
- no land-register payload

## Redaction rule

Screenshots and evidence may show only visible product or process surfaces.
Windows containing logins, tokens, cookies, session values, internal
infrastructure, secret references, wallets or real names are not used. If a
screenshot is uncertain, it is not shown.

## Stop-Line

"We now show the prepared, redacted evidence. It proves the checked demo state
and contains no mandate data."
