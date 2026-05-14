# GitHub Usecase Repository Intake

Scan date: 2026-05-14

Authenticated GitHub user: `ofunk-nvidia`

## Decision Summary

| Repository | Decision | Reason |
| --- | --- | --- |
| `ofunk/Online-GmbH-Gruendung` | Canonicalized into `usecases/online-gmbh-gruendung/` | The repository name is a concrete notarial usecase. The repository is empty, so no source files were imported. |
| `ofunk/NaaS` | Do not move wholesale; decompose over time | The README describes a notarial workflow platform with usecases and workflows. It is broader than one usecase and should be decomposed into `usecases/` and `workflows/` through reviewed changes. |
| `ofunk/IDaaS` | Do not move to usecases | This is an identity-verification SaaS concept. It may become a plugin or workflow dependency, not a notarial usecase. |
| `ofunk/oci-landing-zone` | Do not move to usecases | This is infrastructure/evidence work and is already represented by the `noc-oci-evidence` plugin track. |
| `ofunk/PaaS` | Do not move to usecases | This is a VS Code extension/orchestrator integration repository, not a notarial business usecase. |
| `ofunk/1gem8` | Do not move to usecases | This is a startup workspace concept, not a notarial business usecase. |
| `ofunk/Steuer-aaS` | Canonicalized into `usecases/steuer-aas/` | The repository is empty, but the owner explicitly classified it as a usecase. It is now tracked as the canonical tax-readiness usecase for notary-adjacent formation, nonprofit, tax registration, and evidence workflows. |
| `ofunk/AO52aaS` | Canonicalized into `usecases/ao52aas-gemeinnuetzigkeit/` | The repository contains `docs/gemeinnuetzigkeit/` with AO52 nonprofit software-company formation material. It belongs in the usecase catalog because it drives notarial entity formation, statute preparation, tax/nonprofit pre-checks, and possible hybrid-structure decisions. |

## Follow-up

- Extract relevant `ofunk/NaaS` usecase and workflow material only through a
  reviewed migration plan.
- Keep `ofunk/Online-GmbH-Gruendung` as an external source reference until it is
  archived, redirected, or formally replaced by this repository.
- Keep `ofunk/AO52aaS` as an external source reference until it is archived,
  redirected, or formally replaced by this repository.
- Keep `ofunk/Steuer-aaS` as an external source reference until it is archived,
  redirected, or formally replaced by this repository.
- Add new notarial usecases directly under `usecases/` instead of creating
  separate repositories unless a formal split decision is documented.
