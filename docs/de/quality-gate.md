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
18. `teams_sharepoint_graph_data_plane` (nur `strict`)
19. `m365_release_readiness_gate` (nur `strict`)
20. `m365_sharepoint_bpmn_viewer_adapter` (nur `strict`)
21. `notarial_application_interface_inventory` (nur `strict`)
22. `matter_data_classification_redaction` (nur `strict`)
23. `private_operating_frame_gate` (nur `strict`)
24. `private_payload_target_design` (nur `strict`)
25. `private_payload_access_policy` (nur `strict`)
26. `gnotkg_costs` (nur `strict`)
27. `secure_document_links` (nur `strict`)
28. `legal_research_connectors` (nur `strict`)
29. `legal_source_inventory_license_tdm` (nur `strict`)
30. `legal_model_customization_readiness` (nur `strict`)
31. `legal_model_card_ai_sbom_delta` (nur `strict`)
32. `legal_model_card_proposal` (nur `strict`)
33. `legal_ai_sbom_delta_proposal` (nur `strict`)
34. `legal_model_evaluation_benchmark` (nur `strict`)
35. `legal_graph_contracts` (nur `strict`)

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
  und Runner-Zusammenfassung `release_gate_readiness=READY`

Diese Artefakte werden im CI-Lauf hochgeladen.

## Nutzen für Vorhersagbarkeit

- Gleiche Checks in gleicher Reihenfolge für lokale und CI-Läufe.
- Keine uneinheitlichen Einzelbefehle pro Teammitglied.
- Klare Statuslinie (`PASSED`/`FAILED`) mit nachvollziehbarem Report.
