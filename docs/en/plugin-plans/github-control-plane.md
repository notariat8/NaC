# Plugin Plan: GitHub Control Plane

Status: `proposed`

## Goal

GitHub remains the binding GitOps control plane for NoC:

- branches and pull requests represent subject-matter change requests,
- reviews and checks represent approvals,
- issues and projects represent work, risks and drift,
- Actions create reproducible validation and artifact runs.

## Day 0

- Set up local GitHub authentication:

```bash
gh auth status
```

- Check repository access:

```bash
git remote -v
git pull
```

- Check roles and GitHub identities against
  [policies/github-identity-registry.json](../../../policies/github-identity-registry.json).

## Day 1

- Activate branch protection and review rules for `main`.
- Bind required checks to existing workflows:
  - `quality-gate.yml`
  - `validate-process.yml`
  - `privacy-and-secrets.yml`
  - `governance-policy-sync.yml`
- Use issue templates for compliance, features and bugs.
- Generate plan preview for connector changes as PR comment or artifact.

## Day 2

- Regularly recertify rights and roles.
- Review open drift and compliance issues.
- Classify workflow failures:
  - policy error,
  - test or validation error,
  - external integration error,
  - manual follow-up.
- Tag releases for binding process versions.

## Connector Boundaries

The GitHub connector may:

- read issues, PRs, checks and releases,
- propose planned changes as branch or PR,
- write status and audit evidence.

The GitHub connector must not:

- bypass review rules,
- write directly around `main`,
- store secrets in the repository,
- replace human approvals for sensitive processes.

## Acceptance Criteria

- `gh auth status` is green locally.
- Pull requests enforce review.
- Governance and quality gates run.
- Every connector apply is traceable through PR, check or audit event.
