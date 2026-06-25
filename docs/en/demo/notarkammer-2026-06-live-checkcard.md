# Notarkammer Demo: Live Checkcard

Status: 2026-06-24

This checkcard is the short decision aid immediately before and during the
presentation. It states when the current live state is good enough and when to
switch to BPMN, script and fallback evidence without live debugging.

Scope: demo orientation, public process view and protected portal start. No
runtime change, no cloud change, no secrets, no mandate data, keine
Mandatsdaten, no productive XNP action and no productive filing.

## Live Route

| Step | Route or view | Go | Fallback |
| --- | --- | --- | --- |
| L1 | `https://notariat8.de/prozessmodell.html` | Immobilienkaufvertrag, XNP/SNP, duration band, parallel work and critical path are visible. | Show the preloaded view or an approved screenshot. |
| L2 | `https://app.notariat8.de/login` | The user starts on notariat8 and triggers sign-in. | Do not switch to technical endpoints; use prepared presenter wording. |
| L3 | `https://app.notariat8.de/workspace` after sign-in | Portal start is ready: session is established, role gate is confirmed, Rollengate is satisfied. | If the view remains closed: explain the closed boundary and switch to the process model. |
| L4 | First matter in portal start | Immobilienkaufvertrag is shown only as a metadata-only entry point. | Switch to `notarkammer-first-matter-metadata.md` and BPMN evidence. |

## Good Enough For The Demo

The live state is sufficient when these conditions are met:

1. `Portal-Start bereit` or fail-closed is clearly visible.
2. Session and authorization are described without internal details.
3. The first matter remains metadata-only.
4. No full workspace is opened; kein vollständiger Arbeitsbereich.
5. No mandate data is loaded; keine Mandatsdaten.
6. XNP/SNP is explained as a modeled domain-system boundary and target path.
7. No productive XNP action and no productive filing are claimed.

## Stop Lines

Use these lines to keep the presentation bounded:

- notariat8 shows the protected start status here, not the file.
- The real estate purchase agreement is modeled in BPMN; the full workspace
  remains closed.
- XNP/SNP is prepared as a target path and evidence boundary; productive
  interface approval is part of the next coordination step.
- The critical path in closing mostly depends on external responses.
- If a live step remains closed, that is safety behavior, not a reason for
  live debugging during the meeting.

## Do Not Say

- This demo does not include productive XNP or land-register coupling.
- No real deeds, register values, identity documents or purchase-price values
  are shown.
- No technical vendor, key, session or infrastructure details are shown.
- No productive process is filed.

