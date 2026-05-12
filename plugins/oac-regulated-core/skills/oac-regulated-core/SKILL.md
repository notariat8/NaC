---
name: oac-regulated-core
description: Use when an OaC regulated-industry workflow needs intake, policy checks, plan preview, human approval, evidence capture, drift handling, or a safe fallback path.
---

# OaC Regulated Core

## Operating Boundary

Runtime mode: `local-policy-companion`.

This plugin is for regulated-industry work. Default to plan-preview, local execution, explicit human approval, and evidence metadata. Do not perform external writes unless a separate reviewed connector explicitly implements that action.

## Allowed Work

- Create regulated workflow checklists and plan previews.
- Map Day0, Day1 and Day2 controls to plugin work.
- Prepare evidence templates that contain metadata only.
- Flag missing approvals, accounts or local prerequisites.

## Prohibited Work

- Store passwords, PINs, private keys, certificate material, session cookies, or one-time codes in Git.
- Bypass human review for regulated filing, register, mailbox, or notarial actions.
- Upload client or mandate content to an LLM unless an explicit approved data-processing basis exists.
- Scrape protected portals or exceed published usage limits.

## Workflow

1. Classify the matter, actor role, reviewer role, data class and target system.
2. Check Day0 prerequisites and list missing accounts or approvals.
3. Produce a human-readable Day1 plan preview before any local or external action.
4. Ask for explicit human approval for regulated submissions, register retrievals, mailbox actions, notarial actions or cloud applies.
5. Capture evidence metadata only: timestamp, actor role, source, hash, decision, result and follow-up owner.
6. For Day2, report drift, expired access, failed checks, version changes and recertification tasks.

## Output Shape

Return concise sections named `Readiness`, `Plan`, `Approval Needed`, `Evidence`, and `Day2 Follow-up`. If something cannot proceed, put it under `Approval Needed` and reference `docs/plugin-operations/account-and-approval-requests.md`.

## Source Plan

- `docs/plugin-plans/domain-connector-runtime.md`
