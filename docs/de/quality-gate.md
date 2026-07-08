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
11. `gantt_progress` (nur `strict`; prüft Pflicht-Gantts und
   Mermaid-Render-Sicherheit, gibt aber nur Hinweise für fachliche
   Roadmap-/Scope-/Statusupdates)
12. `cloud_runbook_parity` (nur `strict`)
13. `ai_sbom` (nur `strict`)
14. `ai_sbom_export_mapping` (nur `strict`)
15. `knowledge_graph` (nur `strict`)
16. `kg_editor` (nur `strict`)
17. `codex_parallel_review` (nur `strict`)
18. `codex_subagent_operating_gate` (nur `strict`)
19. `codex_worktree_operating_model` (nur `strict`)
20. `codex_agent_context_operating_model` (nur `strict`)
21. `codex_agent_context_index_audit` (nur `strict`)
22. `codex_memory_hooks_operating_model` (nur `strict`)
23. `codex_command_rules_operating_model` (nur `strict`)
24. `codex_command_rules_adoption_smoke` (nur `strict`)
25. `verification_contracts_domain_pilot` (nur `strict`)
26. `teams_sharepoint_graph_data_plane` (nur `strict`)
27. `m365_release_readiness_gate` (nur `strict`)
28. `m365_sharepoint_bpmn_viewer_adapter` (nur `strict`)
29. `m365_matter_access_delegation` (nur `strict`)
30. `m365_matter_access_decision_replay` (nur `strict`)
31. `m365_matter_access_apply_live_smoke_release_lane` (nur `strict`)
32. `m365_matter_access_apply_live_smoke_retention` (nur `strict`)
33. `notarial_application_interface_inventory` (nur `strict`)
34. `matter_data_classification_redaction` (nur `strict`)
35. `private_operating_frame_gate` (nur `strict`)
36. `private_payload_target_design` (nur `strict`)
37. `private_payload_access_policy` (nur `strict`)
38. `gnotkg_costs` (nur `strict`)
39. `secure_document_links` (nur `strict`)
40. `legal_research_connectors` (nur `strict`)
41. `legal_source_inventory_license_tdm` (nur `strict`)
42. `legal_model_customization_readiness` (nur `strict`)
43. `legal_model_card_ai_sbom_delta` (nur `strict`)
44. `legal_model_card_proposal` (nur `strict`)
45. `legal_ai_sbom_delta_proposal` (nur `strict`)
46. `legal_model_evaluation_benchmark` (nur `strict`)
47. `legal_graph_contracts` (nur `strict`)

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
