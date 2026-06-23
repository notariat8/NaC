# Notarkammer Demo: Login Checklist

Status: short demo checklist for the protected entry point. No runtime change,
no infrastructure apply, no secrets.

## Entry Point

- Start: `https://app.notariat8.de/login`
- Only the login entry point and the closed start boundary are in scope.
- No mandate data access, file content, deeds, register data or property data.

## Status Points

| Point | Showable | Stopper |
| --- | --- | --- |
| Token exchange | Status light or text status without technical raw values. | Not complete, invalid or not stable enough for the demo. |
| Token verification | Confirmation that the sign-in was checked. | Verification open, failed or not reliable. |
| Role gate | Demo role is approved for entry. | Role open, unknown or not approved for the demo. |
| Session | Session only redacted: status, time window, demo approval. | Session open, not reliable or raw values are visible. |

## Redaction Boundaries

- Show no secrets, tokens, claims or technical raw values.
- Show no callbacks, no parameters or browser address details.
- Name no provider details, configuration values or vendor diagnostics.
- Open no consoles, cloud views or infrastructure actions during the meeting.
- Use no real person, file, deed, register or property data.

## Decision

- Green: All four status points are complete and showable in redacted form.
- Yellow: One point is open; describe the entry as fail-closed and switch to
  the prepared process path.
- Red: One point failed or exposes raw values; stop the live path and do no
  live troubleshooting.
