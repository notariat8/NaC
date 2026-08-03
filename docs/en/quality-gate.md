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
  AI-SBOM, AI-SBOM export mapping, knowledge graph, Codex worktree operating model,
  Codex agent context operating model, Codex 5h batch run envelope,
  Teams/SharePoint Graph data plane, matter-data
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
11. `gantt_progress` only in `strict`
12. `cloud_runbook_parity` only in `strict`
13. `ai_sbom` only in `strict`
14. `ai_sbom_export_mapping` only in `strict`
15. `knowledge_graph` only in `strict`
16. `kg_editor` only in `strict`
17. `notarial_business_case_inventory` only in `strict`
18. `notarial_ontology_storage_contract` only in `strict`
19. `notarial_process_ontology_contract` only in `strict`
20. `business_case_type_runtime` only in `strict`
21. `business_case_type_graph_read_edge` only in `strict`
22. `business_case_type_migration_s5` only in `strict`
23. `process_ontology_sharepoint_schema_gap` only in `strict`
24. `process_ontology_sharepoint_schema_apply_plan` only in `strict`
25. `process_ontology_sharepoint_schema_apply_readiness` only in `strict`
26. `process_ontology_sharepoint_schema_apply_execution_contract` only in `strict`
27. `process_ontology_sharepoint_schema_apply_runner_dry_run` only in `strict`
28. `process_ontology_sharepoint_schema_apply_runner_dry_run_artifact` only in `strict`
29. `process_ontology_sharepoint_schema_apply_artifact_index` only in `strict`
30. `process_ontology_sharepoint_schema_apply_live_readiness_gate` only in `strict`
31. `process_ontology_sharepoint_schema_apply_owner_gated_live_plan` only in `strict`
32. `process_ontology_sharepoint_schema_apply_owner_gated_runner_contract` only in `strict`
33. `process_ontology_sharepoint_schema_apply_live_runner` only in `strict`
34. `process_ontology_sharepoint_schema_apply_graph_dispatcher` only in `strict`
35. `notarial_ontology_scale_budget` only in `strict`
36. `notarial_deep_process_candidate_routing` only in `strict`
37. `first_wave_bpmn_outline` only in `strict`
38. `first_wave_bpmn_outline_gap_review` only in `strict`
39. `first_wave_bpmn_outline_gap_review_artifact` only in `strict`
40. `first_wave_process_deep_model` only in `strict`
41. `codex_parallel_review` only in `strict`
42. `codex_subagent_operating_gate` only in `strict`
43. `codex_worktree_operating_model` only in `strict`
44. `codex_agent_context_operating_model` only in `strict`
45. `codex_agent_context_index_audit` only in `strict`
46. `codex_memory_hooks_operating_model` only in `strict`
47. `codex_command_rules_operating_model` only in `strict`
48. `codex_command_rules_adoption_smoke` only in `strict`
49. `codex_5h_batch_run_envelope` only in `strict`
50. `verification_contracts_domain_pilot` only in `strict`
51. `teams_sharepoint_graph_data_plane` only in `strict`
52. `microsoft_first_onprem_target_architecture` only in `strict`
53. `m365_release_readiness_gate` only in `strict`
54. `m365_sharepoint_bpmn_viewer_adapter` only in `strict`
55. `m365_matter_access_delegation` only in `strict`
56. `m365_matter_access_decision_replay` only in `strict`
57. `m365_matter_access_apply_live_smoke_release_lane` only in `strict`
58. `m365_matter_access_apply_live_smoke_retention` only in `strict`
59. `notarial_application_interface_inventory` only in `strict`
60. `xnotar_xjustiz_package_boundary` only in `strict`
61. `matter_data_classification_redaction` only in `strict`
62. `private_operating_frame_gate` only in `strict`
63. `private_payload_target_design` only in `strict`
64. `private_payload_access_policy` only in `strict`
65. `gnotkg_costs` only in `strict`
66. `secure_document_links` only in `strict`
67. `legal_research_connectors` only in `strict`
68. `legal_source_inventory_license_tdm` only in `strict`
69. `legal_model_customization_readiness` only in `strict`
70. `legal_model_card_ai_sbom_delta` only in `strict`
71. `legal_model_card_proposal` only in `strict`
72. `legal_ai_sbom_delta_proposal` only in `strict`
73. `legal_model_evaluation_benchmark` only in `strict`
74. `legal_graph_contracts` only in `strict`

75. `business_case_type_immutable_evidence_s6` only in `strict`

Additional M365 BFF check: `m365_azure_bff_performance_acceptance` (strict
only) validates the capacity- and cost-bounded offline plan, dispatch journal
boundary and verification contract; it does not run a live load test.

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
  `release_gate_readiness=READY` plus the required evidence
  `matter_access_delegation_smoke`, `matter_access_apply_readiness`,
  `matter_access_apply_request_plan` and `matter_access_apply_policy_smoke`
- For matter-access changes, the review must also surface the verification
  contract `verification.m365_matter_access_delegation`: the apply-policy
  smoke artifact must show `5/5` negative cases (`missing_reason`,
  `expired_delegation`, `workspace_scope_violation`, `missing_cleanup`,
  `audit_readback_missing`) and confirm the fail-closed boundary before Graph
  writes.
- The real `matter-access-apply-smoke` is a separate owner-gated release-lane
  standard. It is not a default step in the one-shot gate; a live-smoke
  artifact may only be attached to evidence explicitly with
  `--release-gate-matter-access-apply-smoke-artifact`.
- Successful `matter-access-apply-smoke` artifacts must also be retained in the
  dedicated live-smoke retention index under
  `out/m365/teams-sharepoint/matter-access-apply-live-smokes/`; retention
  itself remains offline and performs no Graph or tenant action.

These artifacts are uploaded during CI runs.

## Predictability Benefit

- Same checks in the same order for local and CI runs.
- No inconsistent one-off commands per team member.
- Clear `PASSED`/`FAILED` status line with a traceable report.
