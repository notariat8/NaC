# START HERE: Operational Entry Into NaC

Status: binding start path
Last content update: 2026-05-19

## Why This Document Exists Next To The README

[README.md](../../README.md) and [docs/en/README.md](README.md) are project overview and index files. This
document is the operational start sequence for working in the active NaC project.

[START_HERE.md](START_HERE.md) remains necessary, but it has a different job than the README:

| Document | Purpose |
| --- | --- |
| [README.md](../../README.md) | Repository overview, product structure, quick checks, current build commands. |
| [docs/en/README.md](README.md) | English business orientation and documentation index. |
| [docs/en/START_HERE.md](START_HERE.md) | Binding work-start sequence for new sessions, contributors and agents. |

This repository is the active project state for `Notariat as Code` with `NaC`
as the concrete Enterprise Control Plane.

## When To Use START_HERE

Use this document:

- when starting a new work session,
- before productive changes to code, documentation, policies, plugins,
  workflows or usecases,
- after switching branches or pulling changes,
- when a new contributor or agent starts in the repository,
- before a push when affected gates or Gantts are unclear.

## Binding Start Sequence

1. Read repository rules:
   - [AGENTS.md](../../AGENTS.md), if present in the workspace.
   - [.github/copilot-instructions.md](../../.github/copilot-instructions.md)
   - [.cursor/rules/](../../.cursor/rules)
2. Read project status:
   - [roadmap/BUILD_NOW.md](../../roadmap/BUILD_NOW.md)
   - [roadmap/GANTT.md](../../roadmap/GANTT.md)
   - [docs/en/minimum-requirements.md](minimum-requirements.md)
   - for area work, also [plugins/GANTT.md](../../plugins/GANTT.md), [workflows/GANTT.md](../../workflows/GANTT.md) or
     [usecases/GANTT.md](../../usecases/GANTT.md)
3. Check the current Git state:

   ```bash
   git status --short --branch
   ```

4. Check the active runtime:

   ```bash
   python scripts/nac.py status
   ```

5. Run the strict local gate before treating a state as push-ready:

   ```bash
   python scripts/startup_check.py --profile base --ide auto --run-tests
   python scripts/nac.py doctor --profile strict
   ```

For plugin or notary-workstation work, also run the matching profile:

```bash
python scripts/nac.py plugins validate
python scripts/nac.py plugins install --mode link
python scripts/startup_check.py --profile plugin-dev --ide auto
python scripts/startup_check.py --profile notary-workstation --ide auto
```

After `nac plugins install --mode link`, reopen Codex. The running session reads
plugins at startup and sees repo-local plugins only after the local mirror and a
restart.

## Working Mode

NaC is developed as software. Concept work is complete only when it also updates
at least one matching implementation surface:

- runtime code under [src/](../../src)
- scripts under [scripts/](../../scripts)
- tests under [tests/](../../tests)
- plugin artifacts under [plugins/](../../plugins)
- workflow contracts under [workflows/contracts/](../../workflows/contracts)
- KG artifacts directly in the matching usecase folder under [usecases/](../../usecases)
- roadmap or Gantt status under [roadmap/](../../roadmap), [plugins/](../../plugins), [workflows/](../../workflows) or
  [usecases/](../../usecases)

## Product Structure

| Area | Purpose |
| --- | --- |
| [plugins/](../../plugins) | Installable plugin artifacts for GPT Store, workspace or local integration. |
| [workflows/](../../workflows) | Skills, workflow contracts and deterministic Python workflows. |
| [usecases/](../../usecases) | Concrete notarial case types and pilot packages with their own static KG/DB as `knowledge-graph.graph.json` and `knowledge-graph.md`. |
| [docs/en/eventstream/](eventstream) | Event journal, EventLock and cloud runbooks. |
| [docs/en/issues/](issues) | Issue taxonomy, issue operations and public backlog. |
| [docs/en/operations/](operations) | Fork/release, upstream sync, version binding, work model and repository consolidation. |
| [docs/en/service-model/](service-model) | Core/vertical structure, provider services, tenant ownership and exit. |
| [src/](../../src) | Executable Python runtime. |
| [scripts/](../../scripts) | Local and CI-adjacent developer tooling. |
| [policies/](../../policies) | Binding governance, role, technology, privacy and SBOM rules. |
| [sbom/](../../sbom) | Machine-readable SBOM/AI-SBOM artifacts for runtime, infrastructure and local dependencies. |

## Current Developer Commands

```bash
python scripts/nac.py status
python scripts/nac.py kg case bautraegervertrag
python scripts/nac.py bpmn validate
python scripts/nac.py config validate
python scripts/validate_knowledge_graph.py
python scripts/nac.py plugins validate
python scripts/startup_check.py --profile base --ide auto --run-tests
python scripts/nac.py doctor --profile strict
```

## Roadmap And Gantt Rule

[roadmap/GANTT.md](../../roadmap/GANTT.md) is updated when roadmap, scope,
status, milestone or active build-board state changes. Changes below
[plugins/](../../plugins), [workflows/](../../workflows) or
[usecases/](../../usecases) update the matching area Gantt only when they
affect area scope, status or milestones:

- [plugins/GANTT.md](../../plugins/GANTT.md)
- [workflows/GANTT.md](../../workflows/GANTT.md)
- [usecases/GANTT.md](../../usecases/GANTT.md)

Small bug fixes, typo fixes, local documentation clarifications,
test/validator fixes or UI details without roadmap impact do not need an
artificial Gantt change. The strict gate still checks that required Gantts exist
and remain Mermaid-renderable.

## Localization Rule

German and English are standard languages. Changes to localized content must
always maintain both language paths:

- [docs/en/](.)
- [prompts/en/](../../prompts/en)

The German counterparts are maintained in parallel, but they are not linked as
navigation targets from English subject-matter documents.

Parity is checked with `python scripts/nac.py doctor --profile strict`.

## Completion Rule

An update is complete only after it has been validated, committed, pushed to
GitHub and merged into the target branch. Local changes and unmerged PR branches
are intermediate states.
