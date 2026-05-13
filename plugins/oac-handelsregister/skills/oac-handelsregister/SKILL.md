---
name: oac-handelsregister
description: Use when preparing HRA-first online Handelsregister applications after deciding citizen-preflight versus notary-side mode, checking notary online-procedure readiness, documenting eID/app prerequisites, or creating non-secret evidence metadata for register filing workflows.
---

# OaC Handelsregister

## Operating Boundary

Runtime mode: `local-online-register-application-companion`.

This plugin is for Handelsregister application preparation, not register data retrieval. For notary-side filing workflows, run `oac-bnotk-xnp` first and require the local XNP authentication gate before XNotar/register handoff work. Default to plan-preview, local execution, explicit applicant/notary approval, and evidence metadata. Do not submit applications, automate notary systems or retrieve register data unless a separate reviewed connector explicitly implements that action.

## Allowed Work

- Classify whether the requested workflow is HRA, HRB or another register track.
- Split citizen preflight from notary-side workstation workflows.
- Prepare HRA-first online register application packages and missing-information lists.
- Check notary online-procedure readiness: Bundesnotarkammer app, eID-capable ID, PIN, video procedure, electronic signature and notary appointment.
- Prepare metadata-only evidence templates for approvals, package readiness and submission outcomes.

## Prohibited Work

- Store passwords, PINs, private keys, certificate material, session cookies, or one-time codes in Git.
- Bypass applicant approval, legal review, notarial review or signature checks.
- Upload client or mandate content to an LLM unless an explicit approved data-processing basis exists.
- Retrieve register data, scrape protected portals, submit filings or automate notary systems.

## Workflow

1. Classify the mode: citizen preflight or notary-side workstation workflow.
2. If notary-side, require `oac-bnotk-xnp` readiness before Handelsregister package work.
3. Classify the matter, legal form, register track, actor role, reviewer role and data class.
4. If the user asks for HRA but names a GmbH/UG, flag the likely HRB mismatch and ask for clarification.
5. Check Day0 prerequisites: applicant authority, notary route, eID/app readiness, required documents and approval owner.
6. Produce a human-readable Day1 plan preview before any notarial or external action.
7. Ask for explicit approval before notary appointments, signatures or submissions.
8. Capture evidence metadata only: timestamp, actor role, package version, source document hashes, decision, result and follow-up owner.
9. For Day2, report rejected filings, missing attachments, identity/signature failures and recertification tasks.

## Output Shape

Return concise sections named `Readiness`, `Application Package`, `Approval Needed`, `Evidence`, and `Day2 Follow-up`. If something cannot proceed, put it under `Approval Needed` and reference `docs/plugin-operations/account-and-approval-requests.md`.

## Source Plan

- `docs/plugin-plans/handelsregister-online-anmeldung.md`
