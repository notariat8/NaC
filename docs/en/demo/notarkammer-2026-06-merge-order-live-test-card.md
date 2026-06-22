# Notarkammer Demo 2026-06: Merge Order and Live-Test Card

Status: 2026-06-22

This card turns the remaining demo artifacts into a showable order. It is not a
release or apply instruction. It only states which reviewed changes should land
first and how the live test is then run safely.

## Merge Order

1. **www-n8 process model and public XNP/SNP entry:** merge the public pages
   first so that the chamber, real estate purchase agreement, process model,
   XNP/SNP, XNotar, completion and ISV questions are visible.
2. **NaC demo base:** then merge the NaC runbooks for venv use, XNP/SNP
   questions, one-page talk track and smoke decision.
3. **NaC diagnostics and evidence:** finally merge login diagnostics and the
   evidence matrix so the live test has clear stop lines and evidence.

## Live Test After Merge

1. Open `https://notariat8.de` and show the public entry point.
2. Open `https://notariat8.de/prozessmodell.html?vorgang=immobilienkaufvertrag`
   and explain the real estate purchase agreement, duration, parallel work,
   critical path, XNP/SNP, XNotar, card reader, registers, land register and
   completion.
3. Open `https://app.notariat8.de/healthz` only as a short technical precheck.
4. Start `https://app.notariat8.de/login` only with an approved test user.
5. Show `https://app.notariat8.de/workspace` as a fail-closed or metadata-only
   boundary when session or role are not green.

## Safe Demo Decision

- **Go:** process model loads, app health is short and non-sensitive, login is
  either green or cleanly fail-closed, and workspace stays closed without a
  valid session.
- **Warn-Go:** login diagnostics stay yellow or red, but process model,
  XNP/SNP boundaries and evidence matrix are explainable.
- **No-Go:** user-facing pages show internal provider values, tokens, claims,
  callback values, secrets or mandate data.

## Stop Lines

- No productive XNP action.
- No productive XNotar, register or land-register action.
- No mandate data.
- No secrets.
- No live repair.
- No JSON endpoint as a user interface.

## Demo Statement

NaC shows the real estate purchase agreement as a reviewable XNP/SNP-centered
workflow. The demo asks specifically for test access, ISV role, evidence
fields, status callbacks and certification steps. It does not claim productive
access.
