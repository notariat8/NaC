# NaC Quality Gate

## Purpose

The quality gate ensures that pull requests are evaluated with a predictable
and reproducible check sequence.

Principle:

- one entry point,
- fixed order,
- machine-readable result,
- human-readable report.

## Entry Point

Local:

```bash
python scripts/nac.py doctor --profile strict
```

CI:

- Workflow: [.github/workflows/quality-gate.yml](../../.github/workflows/quality-gate.yml)
- CI profile: `strict`

## Profiles

- `minimal`: process validation and unit tests
- `standard`: `minimal` plus privacy lint
- `strict`: `standard` plus governance policy sync, language parity including
  skill language markers, documentation links, BPMN model validation, cloud
  runbook parity, Gantt, AI-SBOM and knowledge graph

## Fixed Order

1. `process_validate`
2. `unit_tests`
3. `plugin_validate`
4. `privacy_lint` from `standard`
5. `governance_sync` only in `strict`
6. `language_parity` only in `strict`
7. `doc_links` only in `strict`
8. `bpmn_models` only in `strict`
9. `gantt_progress` only in `strict`; checks required Gantt files and
   Mermaid render safety, and emits guidance for business roadmap/scope/status
   updates
10. `cloud_runbook_parity` only in `strict`
11. `ai_sbom` only in `strict`
12. `knowledge_graph` only in `strict`

## Artifacts

Default output:

- JSON: [out/quality/status.json](../../out/quality/status.json)
- Markdown: [out/quality/report.md](../../out/quality/report.md)
- PR comment: [out/quality/comment.md](../../out/quality/comment.md) for pull
  request upsert

These artifacts are uploaded during CI runs.

## Predictability Benefit

- Same checks in the same order for local and CI runs.
- No inconsistent one-off commands per team member.
- Clear `PASSED`/`FAILED` status line with a traceable report.
