# START HERE: Operational Entry Into NoC

Status: binding start path
Last content update: 2026-05-15

## Why This Document Exists Next To The README

`README.md` and `docs/en/README.md` are project overview and index files. This
document is the operational start sequence for working in the active NoC project.

`START_HERE.md` remains necessary, but it has a different job than the README:

| Document | Purpose |
| --- | --- |
| `README.md` | Repository overview, product structure, quick checks, current build commands. |
| `docs/en/README.md` | English business orientation and documentation index. |
| `docs/en/START_HERE.md` | Binding work-start sequence for new sessions, contributors and agents. |

This repository is the active project state for `Notariat as Code` with `NoC`
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
   - `AGENTS.md`, if present in the workspace.
   - `.github/copilot-instructions.md`
   - `.cursor/rules/`
2. Read project status:
   - `roadmap/BUILD_NOW.md`
   - `roadmap/GANTT.md`
   - for area work, also `plugins/GANTT.md`, `workflows/GANTT.md` or
     `usecases/GANTT.md`
3. Check the current Git state:

   ```bash
   git status --short --branch
   ```

4. Check the active runtime:

   ```bash
   python scripts/notary_kg.py --repo-root . status
   ```

5. Run the strict local gate before treating a state as push-ready:

   ```bash
   python scripts/quality_gate.py --profile strict
   ```

## Working Mode

NoC is developed as software. Concept work is complete only when it also updates
at least one matching implementation surface:

- runtime code under `src/`
- scripts under `scripts/`
- tests under `tests/`
- plugin artifacts under `plugins/`
- workflow contracts under `workflows/contracts/`
- KG artifacts under `knowledge-graph/`
- roadmap or Gantt status under `roadmap/`, `plugins/`, `workflows/` or
  `usecases/`

## Product Structure

| Area | Purpose |
| --- | --- |
| `plugins/` | Installable plugin artifacts for GPT Store, workspace or local integration. |
| `workflows/` | Skills, workflow contracts and deterministic Python workflows. |
| `usecases/` | Concrete notarial case types and pilot packages. |
| `knowledge-graph/` | Static KG/DB for open information, documents, decisions, gates and evidence. |
| `src/` | Executable Python runtime. |
| `scripts/` | Local and CI-adjacent developer tooling. |
| `policies/` | Binding governance, role, technology, privacy and SBOM rules. |

## Current Developer Commands

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . case bautraegervertrag
python scripts/validate_knowledge_graph.py
python scripts/quality_gate.py --profile strict
```

## Push Rule

Every push must update `roadmap/GANTT.md`. Changes below `plugins/`,
`workflows/` or `usecases/` must also update the matching area Gantt:

- `plugins/GANTT.md`
- `workflows/GANTT.md`
- `usecases/GANTT.md`

## Localization Rule

German and English are standard languages. Changes to localized content must
always maintain both language paths:

- `docs/de/`
- `docs/en/`
- `prompts/de/`
- `prompts/en/`

Parity is checked with `scripts/validate_language_parity.py`.

## Completion Rule

An update is complete only after it has been validated, committed, pushed to
GitHub and merged into the target branch. Local changes and unmerged PR branches
are intermediate states.
