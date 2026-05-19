# Repository Consolidation Into NaC

Status: 2026-05-19

## Purpose

This document separates three states that are easy to confuse in GitHub:

1. `canonicalized`: content or the business slot exists in the NaC repository.
2. `merged`: the NaC target state is on `main`.
3. `retired`: the old source repository is archived, deleted, or has a clear
   redirect README.

A repository does not disappear from GitHub when its content is moved into NaC.
Retirement is a separate step.

## Current Status

| Source repo | NaC target | Status in NaC | Source repo status | Next action |
| --- | --- | --- | --- | --- |
| `ofunk/NaC` | Target repository | Target system | open | Merge PR #6. |
| `ofunk/Online-GmbH-Gruendung` | `usecases/online-gmbh-gruendung/` | canonicalized in PR #6 | old repo visible, empty | After merge, add redirect README or archive. |
| `ofunk/Steuer-aaS` | no NaC usecase target | removed from the NaC usecase catalog | old repo visible, empty | Keep external or re-evaluate later as a plugin/workflow idea. |
| `ofunk/IDaaS` | `plugins/nac-idaas/` | migrated in PR #6 | old repo visible | After merge, add redirect README or archive. |
| `ofunk/NaaS` | `usecases/` and `workflows/` | not migrated yet | old repo visible | Decompose instead of moving wholesale: usecases, workflow contracts, and backlog separately. |
| `ofunk/oci-landing-zone` | `plugins/nac-oci-evidence/` and cloud/evidence docs | partly covered conceptually | old repo visible | Check whether runbooks or infra contracts are missing in NaC; migrate or keep as external infrastructure source. |
| `ofunk/PaaS` | possibly `workflows/` or editor/workspace docs | not migrated | old repo visible | Check whether content belongs in NaC or should remain a separate VS Code orchestrator repository. |
| `ofunk/1gem8` | possibly startup docs | not migrated | old repo visible | Check whether content belongs in NaC or should remain external. |
| `ofunk/machine-setup` | no business NaC domain | external | old repo visible | Do not move into NaC unless intentionally adopted as tooling runbook. |

## Retirement Rule

After PR #6 is merged:

1. Compare the source repository with the NaC target path.
2. If fully migrated, add a redirect README to the source repository.
3. If no further history is needed, archive or delete the repository.
4. If only partly migrated, keep the remainder visible in this document and in
   the Gantt.

## Permission Reality

The GitHub app reports write access but no admin access for several `ofunk/*`
repositories. Without admin rights, I cannot reliably archive or delete those
repositories. I can push redirect READMEs if requested.

## Redirect README Pattern

```markdown
# Moved to NaC

This repository has been consolidated into `ofunk/NaC`.

Canonical location:
`<target-path>`

Do not create new work here. Open issues and changes in `ofunk/NaC`.
```
