---
name: oac-oci-evidence
description: Use when preparing OCI landing-zone, Resource Manager, Vault, eventstream, audit or drift evidence work for OaC regulated operations.
---

# OaC OCI Evidence

## Operating Boundary

Runtime mode: `local-cloud-cli-companion`.

This plugin is for regulated-industry work. Default to plan-preview, local execution, explicit human approval, and evidence metadata. Do not perform external writes unless a separate reviewed connector explicitly implements that action.

## Allowed Work

- Prepare OCI CLI readiness and Resource Manager plan reviews.
- Document Vault, compartment, audit and eventstream decisions.
- Track Day2 drift, cost and rotation tasks.

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

- `docs/plugin-plans/oci-infrastructure.md`
