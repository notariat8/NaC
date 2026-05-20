# GitHub Usecase Repository Intake

Scan date: 2026-05-14

Authenticated GitHub user: `ofunk-nvidia`

## Decision Summary

| Repository | Decision | Reason |
| --- | --- | --- |
| `ofunk/Online-GmbH-Gruendung` | Canonicalized into `usecases/online-gmbh-gruendung/` | The repository name is a concrete notarial usecase. The repository is empty, so no source files were imported. |
| `ofunk/NaaS` | Do not move wholesale; decompose over time | The README describes a notarial workflow platform with usecases and workflows. It is broader than one usecase and should be decomposed into `usecases/` and `workflows/` through reviewed changes. |
| `ofunk/IDaaS` | Migrated as plugin `plugins/nac-idaas/` | This is an identity-verification and IAM-projection concept. It belongs in the plugin layer, not in the usecase catalog. |
| `ofunk/oci-landing-zone` | Do not move to usecases | This is infrastructure/evidence work and is already represented by the `nac-oci-evidence` plugin track. |
| `ofunk/PaaS` | Do not move to usecases | This is a VS Code extension/orchestrator integration repository, not a notarial business usecase. |
| `ofunk/1gem8` | Do not move to usecases | This is a startup workspace concept, not a notarial business usecase. |
| `ofunk/Steuer-aaS` | Removed from the NaC usecase catalog | The tax-readiness concept is not a concrete notarial office proceeding for this repository. It remains external unless a reviewed plugin or workflow decision reclassifies it. |

## Follow-up

- Extract relevant `ofunk/NaaS` usecase and workflow material only through a
  reviewed migration plan.
- Keep `ofunk/Online-GmbH-Gruendung` as an external source reference until it is
  archived, redirected, or formally replaced by this repository.
- Add new notarial usecases directly under `usecases/` instead of creating
  separate repositories unless a formal split decision is documented.
