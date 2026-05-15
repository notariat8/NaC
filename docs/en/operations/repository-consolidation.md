# Repository Consolidation Into NoC

Status: 2026-05-14

## Purpose

This document separates three states that are easy to confuse in GitHub:

1. `canonicalized`: content or the business slot exists in the NoC repository.
2. `merged`: the NoC target state is on `main`.
3. `retired`: the old source repository is archived, deleted, or has a clear
   redirect README.

A repository does not disappear from GitHub when its content is moved into NoC.
Retirement is a separate step.

## Current Status

| Source repo | NoC target | Status in NoC | Source repo status | Next action |
| --- | --- | --- | --- | --- |
| `ofunk/NaC` | Target repository | Target system | open | Merge PR #6. |
| `ofunk/Online-GmbH-Gruendung` | `usecases/online-gmbh-gruendung/` | canonicalized in PR #6 | old repo visible, empty | After merge, add redirect README or archive. |
| `ofunk/AO52aaS` | `usecases/ao52aas-gemeinnuetzigkeit/` | migrated in PR #6 | old repo visible | After merge, add redirect README or archive. |
| `ofunk/Steuer-aaS` | `usecases/steuer-aas/` | canonicalized in PR #6 | old repo visible, empty | After merge, add redirect README or archive. |
| `ofunk/IDaaS` | `plugins/noc-idaas/` | migrated in PR #6 | old repo visible | After merge, add redirect README or archive. |
| `ofunk/NaaS` | `usecases/` and `workflows/` | not migrated yet | old repo visible | Decompose instead of moving wholesale: usecases, workflow contracts, and backlog separately. |
| `ofunk/oci-landing-zone` | `plugins/noc-oci-evidence/` and cloud/evidence docs | partly covered conceptually | old repo visible | Check whether runbooks or infra contracts are missing in NoC; migrate or keep as external infrastructure source. |
| `ofunk/PaaS` | possibly `workflows/` or editor/workspace docs | not migrated | old repo visible | Check whether content belongs in NoC or should remain a separate VS Code orchestrator repository. |
| `ofunk/1gem8` | possibly `usecases/ao52aas-gemeinnuetzigkeit/` or startup docs | not migrated | old repo visible | Check whether remaining content extends the AO52/nonprofit usecase. |
| `ofunk/machine-setup` | no business NoC domain | external | old repo visible | Do not move into NoC unless intentionally adopted as tooling runbook. |

## Retirement Rule

After PR #6 is merged:

1. Compare the source repository with the NoC target path.
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
# Moved to NoC

This repository has been consolidated into `ofunk/NaC`.

Canonical location:
`<target-path>`

Do not create new work here. Open issues and changes in `ofunk/NaC`.
```
