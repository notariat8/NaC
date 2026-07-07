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
  technology policy, language parity including skill language markers,
  documentation links, BPMN model validation, cloud runbook parity, Gantt,
  AI-SBOM, AI-SBOM export mapping, knowledge graph, Teams/SharePoint Graph data plane, matter-data
  classification/redaction and private operating frame gate, private-payload target design and
  private-payload access policy plus legal source inventory/license TDM,
  Legal Nemotron readiness, legal model-card/AI-SBOM delta, legal model-card
  proposal, legal AI-SBOM delta proposal and legal model evaluation benchmark

## Fixed Order

1. `process_validate`
2. `unit_tests`
3. `plugin_validate`
4. `privacy_lint` from `standard`
5. `governance_sync` only in `strict`
6. `spec_traceability` only in `strict`
7. `technology_policy` only in `strict`
8. `language_parity` only in `strict`
9. `doc_links` only in `strict`
10. `bpmn_models` only in `strict`
11. `gantt_progress` only in `strict`; checks required Gantt files and
   Mermaid render safety, and emits guidance for business roadmap/scope/status
   updates
12. `cloud_runbook_parity` only in `strict`
13. `ai_sbom` only in `strict`
14. `ai_sbom_export_mapping` only in `strict`
15. `knowledge_graph` only in `strict`
16. `kg_editor` only in `strict`
17. `codex_parallel_review` only in `strict`
18. `teams_sharepoint_graph_data_plane` only in `strict`
19. `m365_release_readiness_gate` only in `strict`
20. `m365_sharepoint_bpmn_viewer_adapter` only in `strict`
21. `notarial_application_interface_inventory` only in `strict`
22. `matter_data_classification_redaction` only in `strict`
23. `private_operating_frame_gate` only in `strict`
24. `private_payload_target_design` only in `strict`
25. `private_payload_access_policy` only in `strict`
26. `gnotkg_costs` only in `strict`
27. `secure_document_links` only in `strict`
28. `legal_research_connectors` only in `strict`
29. `legal_source_inventory_license_tdm` only in `strict`
30. `legal_model_customization_readiness` only in `strict`
31. `legal_model_card_ai_sbom_delta` only in `strict`
32. `legal_model_card_proposal` only in `strict`
33. `legal_ai_sbom_delta_proposal` only in `strict`
34. `legal_model_evaluation_benchmark` only in `strict`
35. `legal_graph_contracts` only in `strict`

## Artifacts

Default output:

- JSON: [out/quality/status.json](../../out/quality/status.json)
- Markdown: [out/quality/report.md](../../out/quality/report.md)
- PR comment: [out/quality/comment.md](../../out/quality/comment.md) for pull
  request upsert with build status, check summary and KG readiness from the
  usecase-local knowledge graphs
- Markdown report and PR comment also show the M365 MVP readiness status: CI
  enforcement for the `m365_release_readiness_gate`, Go/No-Go target
  `mvp_release_readiness=READY` and runner summary
  `release_gate_readiness=READY`

These artifacts are uploaded during CI runs.

## Predictability Benefit

- Same checks in the same order for local and CI runs.
- No inconsistent one-off commands per team member.
- Clear `PASSED`/`FAILED` status line with a traceable report.
