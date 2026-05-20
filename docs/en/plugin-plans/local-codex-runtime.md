# Plugin Plan: Local Codex Runtime

Status: `proposed`

## Goal

Codex should edit NaC locally in the real workspace `~/NaC`. The local session
is the execution location for plan generation, Git operations, tests and later
domain integrations.

## Non-Goals

- No NaC execution from Omnistation.
- No copying of local secrets to remote hosts.
- No bypassing GitHub, browser or OCI callbacks through SSH bridges.

## Day 0

- Start Codex Desktop with workspace `\\wsl$\\Ubuntu\\home\\ofunk\\NaC`.
- Update repository:

```bash
cd ~/NaC
git pull
```

- Execute startup check:

```bash
python3 scripts/startup_check.py --ide auto --run-tests
```

- Document missing local tools and install them locally.

## Day 1

- Regenerate plugin plans locally in [docs/en/plugin-plans/](.).
- Move changes only through branch, review and merge into `main`.
- Keep Cursor and VS Code Copilot paths synchronized for concept changes.
- Create a plan preview as Markdown before a connector changes real target
  systems.

## Day 2

- Regularly run `git pull`, startup check and tests.
- Document local tool versions when they matter for reproducibility.
- Capture broken integrations as issues instead of masking them through remote
  execution.
- Make drift between repository and target systems visible in Git.

## Local Minimum Tools

- `git`
- `python3`
- `python` alias or compatible command if the startup check requires it
- `gh`
- `code`
- optional `pandoc`

## Acceptance Criteria

- Codex sees `/home/ofunk/NaC` as working directory.
- `git status --short --branch` runs locally.
- Startup check is run locally and its result is known.
- Plugin plans can be edited, committed and pushed locally.
