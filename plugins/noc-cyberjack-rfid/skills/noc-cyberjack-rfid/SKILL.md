---
name: noc-cyberjack-rfid
description: Use first when notary-side XNP login or Online HRA testing needs BNotK chip/signature card readiness, REINER SCT cyberJack reader checks, RFID-off verification, security-class-3 reader checks, BNotK SAK lite/XNP card path, secureFramework, XNP local-interface readiness, PC/SC state, driver versions, firmware notes or evidence metadata.
---

# NoC Card SAK Gate

## Operating Boundary

Runtime mode: `local-card-sak-gate`.

This installable local Codex plugin is the first gate before XNP login testing for notary-side Online HRA. Default to plan-preview, local execution, explicit human approval, and evidence metadata. Do not perform external writes unless a separate reviewed connector explicitly implements that action.

## Allowed Work

- Prepare local card, compatible security-class-3 reader, RFID-off, SAK-lite/XNP-card-path, secureFramework and XNP local-interface readiness checks.
- Run `python plugins\noc-cyberjack-rfid\scripts\check_readiness.py --json` from the repository root to create a local readiness evidence preview.
- Run `python plugins\noc-cyberjack-rfid\scripts\check_readiness.py --json --probe-morris-api` when the operator explicitly wants the local morris localhost API and PC/SC list-readers path tested without reading card data.
- Record anonymized reader fingerprints and driver version metadata.
- Record morris SID/auth values only as hashes and never expose raw authorization data in evidence.
- Route PIN/card issues to the human operator without requesting values.
- Record only non-secret XNP local-interface metadata such as active state and localhost port range.

## Prohibited Work

- Store passwords, PINs, private keys, certificate material, session cookies, or one-time codes in Git.
- Store XNP local-interface API keys, login credentials, certificate material, card values or encrypted key blobs in Git.
- Bypass human review for regulated filing, register, mailbox, or notarial actions.
- Upload client or mandate content to an LLM unless an explicit approved data-processing basis exists.
- Scrape protected portals or exceed published usage limits.

## Workflow

1. Classify the target: XNP login test, Online HRA gate, beA/BNotK precheck or other card workflow.
2. Check Day0 prerequisites with the local readiness script where possible: BNotK chip/signature card, compatible security-class-3 reader, RFID disabled where present, PC/SC, driver, BNotK SAK lite or XNP card path, secureFramework and XNP local-interface configuration.
3. Produce a human-readable Day1 plan preview before any local or external action.
4. Ask for explicit human approval for any PIN prompt, certificate selection, XNP login test or notarial action.
5. Capture evidence metadata only: timestamp, actor role, non-secret reader fingerprint hash, RFID-off status, component readiness, XNP local-interface active/port metadata, decision, result and follow-up owner.
6. For Day2, report drift, expired access, failed checks, version changes and recertification tasks.

## Output Shape

Return concise sections named `Readiness`, `Plan`, `Approval Needed`, `Evidence`, and `Day2 Follow-up`. If something cannot proceed, put it under `Approval Needed` and reference `docs/de/plugin-operations/account-and-approval-requests.md` and `docs/en/plugin-operations/account-and-approval-requests.md`.

## Source Plan

- `docs/de/plugin-plans/cyberjack-rfid-plugin-integration.md`
- `docs/en/plugin-plans/cyberjack-rfid-plugin-integration.md`
