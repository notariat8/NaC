# Notary Usecases

This directory contains concrete notarial usecases. Usecases are separate from
installable plugins and from reusable workflow execution logic.

## Boundary

- `plugins/` provides installable companion capabilities.
- `workflows/` provides reusable skills and deterministic Python workflow logic.
- `usecases/` describes concrete notarial business scenarios and their required
  plugin/workflow bindings.

## Current Catalog

| Usecase | Folder | Status | Primary plugin dependencies |
| --- | --- | --- | --- |
| Online GmbH formation | `online-gmbh-gruendung/` | Active intake | `noc-regulated-core`, `noc-cyberjack-rfid`, `noc-bnotk-xnp`, `noc-handelsregister` |
| AO52 nonprofit software company | `ao52aas-gemeinnuetzigkeit/` | Active intake | `noc-regulated-core`, `noc-bnotk-xnp`, `noc-handelsregister`, `noc-elster-eric` |
| Steuer-aaS tax readiness | `steuer-aas/` | Active intake | `noc-regulated-core`, `noc-elster-eric` |
| Real-estate purchase contract | `grundstueckskaufvertrag/` | Starter | `noc-regulated-core`, `noc-grundbuch-portal`, `noc-bnotk-xnp` |
| Testament | `testament/` | Starter | `noc-regulated-core` |

## Intake Rule

External GitHub repositories that are really notarial usecases should be
canonicalized here. If an external repository is empty, only the canonical
folder and source reference are created here; no empty history is imported.

See `usecases/github-repo-intake.md` for the latest GitHub scan.
