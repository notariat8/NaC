---
name: noc-cyberjack-rfid
description: Use first when notary-side XNP login or Online HRA testing needs BNotK chip/signature card or local Schneider/SCP-card readiness, security-class-3 reader checks, BNotK SAK lite/XNP card path, secureFramework, PC/SC state, driver versions, firmware notes or evidence metadata.
---

# NoC Card SAK Gate

## Operating Boundary

Runtime mode: `local-card-sak-gate`.

This installable local Codex plugin is the first gate before XNP login testing for notary-side Online HRA. Default to plan-preview, local execution, explicit human approval, and evidence metadata. Do not perform external writes unless a separate reviewed connector explicitly implements that action.

## Allowed Work

- Prepare local card, security-class-3 reader, SAK-lite/XNP-card-path and secureFramework readiness checks.
- Record anonymized reader fingerprints and driver version metadata.
- Route PIN/card issues to the human operator without requesting values.

## Prohibited Work

- Store passwords, PINs, private keys, certificate material, session cookies, or one-time codes in Git.
- Bypass human review for regulated filing, register, mailbox, or notarial actions.
- Upload client or mandate content to an LLM unless an explicit approved data-processing basis exists.
- Scrape protected portals or exceed published usage limits.

## Workflow

1. Classify the target: XNP login test, Online HRA gate, beA/BNotK precheck or other card workflow.
2. Check Day0 prerequisites: BNotK chip/signature card or local Schneider/SCP card, security-class-3 reader, PC/SC, driver, BNotK SAK lite or XNP card path and secureFramework.
3. Produce a human-readable Day1 plan preview before any local or external action.
4. Ask for explicit human approval for any PIN prompt, certificate selection, XNP login test or notarial action.
5. Capture evidence metadata only: timestamp, actor role, non-secret reader fingerprint hash, component readiness, decision, result and follow-up owner.
6. For Day2, report drift, expired access, failed checks, version changes and recertification tasks.

## Output Shape

Return concise sections named `Readiness`, `Plan`, `Approval Needed`, `Evidence`, and `Day2 Follow-up`. If something cannot proceed, put it under `Approval Needed` and reference `docs/plugin-operations/account-and-approval-requests.md`.

## Source Plan

- `docs/plugin-plans/cyberjack-rfid-plugin-integration.md`
