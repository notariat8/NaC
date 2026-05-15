# Plugin Plan: Domain Connector Runtime

Status: `draft`

## Goal

Domain-system connectors should reconcile NoC changes into target systems in a
controlled way:

- IAM,
- GitHub,
- Jira or comparable ticket systems,
- Slack or Teams for notifications,
- later domain or customer systems.

## Guiding Principle

Connectors are adapters. They must not replace subject-matter truth. Truth
resides in Git, schemas, policies, reviews and approved process versions.

## Contract Model

Every connector needs:

- input schema for intent,
- plan schema for preview,
- apply protocol,
- idempotency key,
- audit-event schema,
- drift check,
- exit and replacement path.

## Day 0

- Confirm target systems for the MVP:
  - GitHub,
  - IAM,
  - Jira.
- Provide test or sandbox access per target system.
- Use no real customer data in examples.
- Start connector configuration as documentation, not as a secret file.

## Day 1

- Build the first connector in dry-run mode only.
- Generate plan preview in the PR.
- Enforce reviewer gates for sensitive changes.
- Apply only after merge or explicit approval.
- Write audit evidence:
  - planned target state,
  - executed operation,
  - target-system response without secrets,
  - timestamp,
  - actor.

## Day 2

- Check drift regularly.
- Capture connector failures as issues.
- Execute replays idempotently.
- Recertify target-system permissions.
- Test exit path for every connector.

## MVP Sequence

1. GitHub connector for issues, PRs, labels, reviews and releases.
2. IAM connector for role and access changes in the pilot.
3. Jira connector for ticket and process handoff.
4. Notification connector for Slack or Teams.
5. OCI evidence connector for eventstream and audit journal.
6. Commercial-register spike for register research without productive
   automation.
7. XNP companion for local notary-software integration.

## Acceptance Criteria

- Every connector creates a human-readable plan before apply.
- Every apply is idempotent.
- Every apply writes audit evidence.
- Drift becomes visible as an issue or plan diff.
- Secrets stay outside Git.
