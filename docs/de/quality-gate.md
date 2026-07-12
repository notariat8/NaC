# NaC Quality Gate

## Zweck

Der Quality Gate stellt sicher, dass PRs mit einer vorhersagbaren und reproduzierbaren Prüfreihenfolge bewertet werden.

Prinzip:

- ein Einstiegspunkt,
- feste Reihenfolge,
- maschinenlesbares Ergebnis,
- menschenlesbarer Report.

## Einstieg

Lokal:

```bash
python scripts/nac.py doctor --profile strict
```

CI:

- Workflow: `.github/workflows/quality-gate.yml`
- Profil in CI: `strict`

## Profile

- `minimal`: Prozessvalidierung + Unit Tests
- `standard`: `minimal` + Privacy Lint
- `strict`: `standard` + Governance Policy Sync + Spec-Traceability +
  Technology Policy + Language Parity inklusive Skill-Sprachmarkern +
  Documentation Links + BPMN-Modellprüfung + Cloud Runbook Parity + Gantt +
  AI-SBOM + AI-SBOM-Export-Mapping + Knowledge Graph +
  Codex-Worktree-Betriebsmodell + Codex-Agent-Context-Betriebsmodell +
  Codex-5h-Batch-Run-Envelope +
  Teams-/SharePoint-Graph-Datenebene + Mandatsdaten-Klassifikation und Redaktionsgrenze + privater Betriebsrahmen +
  Private-Payload-Zielarchitektur + Private-Payload-Zugriffsmatrix +
  Legal-Source-Inventar-Lizenz-TDM + Legal-Nemotron-Readiness +
  Legal-Model-Card-/AI-SBOM-Delta + Legal-Model-Card-Vorschlag +
  Legal-AI-SBOM-Delta-Vorschlag + Legal-Model-Evaluationsbenchmark

## Feste Reihenfolge

1. `process_validate`
2. `unit_tests`
3. `plugin_validate`
4. `privacy_lint` (ab `standard`)
5. `governance_sync` (nur `strict`)
6. `spec_traceability` (nur `strict`)
7. `technology_policy` (nur `strict`)
8. `language_parity` (nur `strict`)
9. `doc_links` (nur `strict`)
10. `bpmn_models` (nur `strict`)
11. `gantt_progress` (nur `strict`)
12. `cloud_runbook_parity` (nur `strict`)
13. `ai_sbom` (nur `strict`)
14. `ai_sbom_export_mapping` (nur `strict`)
15. `knowledge_graph` (nur `strict`)
16. `kg_editor` (nur `strict`)
17. `notarial_business_case_inventory` (nur `strict`)
18. `notarial_ontology_storage_contract` (nur `strict`)
19. `notarial_process_ontology_contract` (nur `strict`)
20. `business_case_type_runtime` (nur `strict`)
21. `business_case_type_graph_read_edge` (nur `strict`)
22. `business_case_type_migration_s5` (nur `strict`)
23. `process_ontology_sharepoint_schema_gap` (nur `strict`)
24. `process_ontology_sharepoint_schema_apply_plan` (nur `strict`)
25. `process_ontology_sharepoint_schema_apply_readiness` (nur `strict`)
26. `process_ontology_sharepoint_schema_apply_execution_contract` (nur `strict`)
27. `process_ontology_sharepoint_schema_apply_runner_dry_run` (nur `strict`)
28. `process_ontology_sharepoint_schema_apply_runner_dry_run_artifact` (nur `strict`)
29. `process_ontology_sharepoint_schema_apply_artifact_index` (nur `strict`)
30. `process_ontology_sharepoint_schema_apply_live_readiness_gate` (nur `strict`)
31. `process_ontology_sharepoint_schema_apply_owner_gated_live_plan` (nur `strict`)
32. `process_ontology_sharepoint_schema_apply_owner_gated_runner_contract` (nur `strict`)
33. `process_ontology_sharepoint_schema_apply_live_runner` (nur `strict`)
34. `process_ontology_sharepoint_schema_apply_graph_dispatcher` (nur `strict`)
35. `notarial_ontology_scale_budget` (nur `strict`)
36. `notarial_deep_process_candidate_routing` (nur `strict`)
37. `first_wave_bpmn_outline` (nur `strict`)
38. `first_wave_bpmn_outline_gap_review` (nur `strict`)
39. `first_wave_bpmn_outline_gap_review_artifact` (nur `strict`)
40. `first_wave_process_deep_model` (nur `strict`)
41. `codex_parallel_review` (nur `strict`)
42. `codex_subagent_operating_gate` (nur `strict`)
43. `codex_worktree_operating_model` (nur `strict`)
44. `codex_agent_context_operating_model` (nur `strict`)
45. `codex_agent_context_index_audit` (nur `strict`)
46. `codex_memory_hooks_operating_model` (nur `strict`)
47. `codex_command_rules_operating_model` (nur `strict`)
48. `codex_command_rules_adoption_smoke` (nur `strict`)
49. `codex_5h_batch_run_envelope` (nur `strict`)
50. `verification_contracts_domain_pilot` (nur `strict`)
51. `teams_sharepoint_graph_data_plane` (nur `strict`)
52. `microsoft_first_onprem_target_architecture` (nur `strict`)
53. `m365_release_readiness_gate` (nur `strict`)
54. `m365_sharepoint_bpmn_viewer_adapter` (nur `strict`)
55. `m365_matter_access_delegation` (nur `strict`)
56. `m365_matter_access_decision_replay` (nur `strict`)
57. `m365_matter_access_apply_live_smoke_release_lane` (nur `strict`)
58. `m365_matter_access_apply_live_smoke_retention` (nur `strict`)
59. `notarial_application_interface_inventory` (nur `strict`)
60. `xnotar_xjustiz_package_boundary` (nur `strict`)
61. `matter_data_classification_redaction` (nur `strict`)
62. `private_operating_frame_gate` (nur `strict`)
63. `private_payload_target_design` (nur `strict`)
64. `private_payload_access_policy` (nur `strict`)
65. `gnotkg_costs` (nur `strict`)
66. `secure_document_links` (nur `strict`)
67. `legal_research_connectors` (nur `strict`)
68. `legal_source_inventory_license_tdm` (nur `strict`)
69. `legal_model_customization_readiness` (nur `strict`)
70. `legal_model_card_ai_sbom_delta` (nur `strict`)
71. `legal_model_card_proposal` (nur `strict`)
72. `legal_ai_sbom_delta_proposal` (nur `strict`)
73. `legal_model_evaluation_benchmark` (nur `strict`)
74. `legal_graph_contracts` (nur `strict`)

## Artefakte

Standardausgabe:

- JSON: `out/quality/status.json`
- Markdown: `out/quality/report.md`
- PR-Kommentar: `out/quality/comment.md` (für Upsert in Pull Requests)
  mit Build-Status, Check-Zusammenfassung und KG-Readiness aus den
  usecase-lokalen Knowledge Graphs
- Markdown-Report und PR-Kommentar zeigen zusätzlich den
  M365-MVP-Readiness-Status: CI-Enforcement für den
  `m365_release_readiness_gate`, Go/No-Go-Ziel `mvp_release_readiness=READY`
  und Runner-Zusammenfassung `release_gate_readiness=READY` sowie die
  Pflichtnachweise `matter_access_delegation_smoke`,
  `matter_access_apply_readiness`, `matter_access_apply_request_plan` und
  `matter_access_apply_policy_smoke`
- Für Matter-Access-Änderungen muss der Review außerdem den Verification
  Contract `verification.m365_matter_access_delegation` sichtbar machen: das
  Apply-Policy-Smoke-Artefakt muss `5/5` Negativfälle zeigen
  (`missing_reason`, `expired_delegation`, `workspace_scope_violation`,
  `missing_cleanup`, `audit_readback_missing`) und die Fail-Closed-Grenze vor
  Graph-Writes bestätigen.
- Der echte `matter-access-apply-smoke` ist ein separater owner-gated
  Release-Lane-Standard. Er ist kein Default-Schritt im One-Shot-Gate; ein
  Live-Smoke-Artefakt darf nur explizit mit
  `--release-gate-matter-access-apply-smoke-artifact` an Evidence angehängt
  werden.
- Erfolgreiche `matter-access-apply-smoke`-Artefakte müssen zusätzlich in den
  eigenen Live-Smoke-Retention-Index unter
  `out/m365/teams-sharepoint/matter-access-apply-live-smokes/` aufgenommen
  werden; die Retention selbst bleibt offline und führt keine Graph- oder
  Tenant-Aktion aus. Kurzflag: keine Graph- oder Tenant-Aktion.

Diese Artefakte werden im CI-Lauf hochgeladen.

## Nutzen für Vorhersagbarkeit

- Gleiche Checks in gleicher Reihenfolge für lokale und CI-Läufe.
- Keine uneinheitlichen Einzelbefehle pro Teammitglied.
- Klare Statuslinie (`PASSED`/`FAILED`) mit nachvollziehbarem Report.
