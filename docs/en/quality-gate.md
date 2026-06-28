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
- `strict`: `standard` plus governance policy sync, spec traceability,
  language parity including skill language markers, documentation links, BPMN
  model validation, cloud runbook parity, Gantt, AI-SBOM, ATP runtime
  contract, knowledge graph, NaC on-prem agent runtime and notarial on-prem
  connector boundaries

## Fixed Order

1. `process_validate`
2. `unit_tests`
3. `plugin_validate`
4. `privacy_lint` from `standard`
5. `governance_sync` only in `strict`
6. `spec_traceability` only in `strict`
7. `language_parity` only in `strict`
8. `doc_links` only in `strict`
9. `bpmn_models` only in `strict`
10. `gantt_progress` only in `strict`; checks required Gantt files and
   Mermaid render safety, and emits guidance for business roadmap/scope/status
   updates
11. `cloud_runbook_parity` only in `strict`
12. `ai_sbom` only in `strict`
13. `atp_runtime_contracts` only in `strict`
14. `knowledge_graph` only in `strict`
15. `kg_editor` only in `strict`
16. `codex_parallel_review` only in `strict`
17. `nac_onprem_agent_runtime` only in `strict`
18. `notarial_onprem_connector_boundaries` only in `strict`
19. `gnotkg_costs` only in `strict`
20. `secure_document_links` only in `strict`
21. `legal_research_connectors` only in `strict`
22. `legal_graph_contracts` only in `strict`
23. `oci_tenant_identity` only in `strict`

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
