---
name: oac-bnotk-xnp
description: Use after oac-cyberjack-rfid when a notary-side Online HRA, Handelsregister, XNotar or notarial software workflow needs an installable local Codex plugin for XNP authentication readiness, Amtstaetigkeitskontext checks, API-key presence documentation without values, or evidence plans.
---

# OaC BNotK XNP

## Operating Boundary

Runtime mode: `local-xnp-auth-gate`.

This installable local Codex plugin is the XNP gate for notary-side Online HRA workflows. Run `oac-cyberjack-rfid` first because XNP login testing depends on card-reader, BNotK SAK lite or XNP-card-path and secureFramework readiness. Default to plan-preview, local execution, explicit human approval, and evidence metadata. Do not perform external writes unless a separate reviewed connector explicitly implements that action.

## Allowed Work

- Document local XNP readiness, current local authentication and interface status.
- Record boolean presence of local configuration without values.
- Prepare local-only XNotar/register handoff steps for notarial software.

## Prohibited Work

- Store passwords, PINs, private keys, certificate material, session cookies, or one-time codes in Git.
- Bypass local XNP authentication, Amtstaetigkeitskontext validation, human review, register, mailbox, or notarial action controls.
- Upload client or mandate content to an LLM unless an explicit approved data-processing basis exists.
- Scrape protected portals or exceed published usage limits.

## Workflow

1. Classify the mode: citizen preflight or notary-side workstation workflow.
2. Confirm completed `oac-cyberjack-rfid` card/SAK readiness before any XNP login testing.
3. For notary-side workflows, check local XNP installation, local login, user role and Amtstaetigkeitskontext before any Handelsregister-specific work.
4. Check XNotar/register module or exchange-folder route, local admin ownership and vendor interface status.
5. Produce a human-readable Day1 plan preview before any local or external action.
6. Ask for explicit human approval for regulated submissions, register applications, notarial actions or cloud applies.
7. Capture evidence metadata only: timestamp, actor role, local readiness status, source, hash, decision, result and follow-up owner.
8. For Day2, report drift, expired access, failed checks, version changes and recertification tasks.

## Output Shape

Return concise sections named `Readiness`, `Plan`, `Approval Needed`, `Evidence`, and `Day2 Follow-up`. If something cannot proceed, put it under `Approval Needed` and reference `docs/plugin-operations/account-and-approval-requests.md`.

## Source Plan

- `docs/plugin-plans/bnotk-xnp-notariatssoftware.md`
