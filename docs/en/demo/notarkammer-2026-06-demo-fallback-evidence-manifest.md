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

## Redaction rule

Screenshots and evidence may show only visible product or process surfaces.
Windows containing logins, tokens, cookies, session values, internal
infrastructure, secret references, wallets or real names are not used. If a
screenshot is uncertain, it is not shown.

## Stop-Line

"We now show the prepared, redacted evidence. It proves the checked demo state
and contains no mandate data."
