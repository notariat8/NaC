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
  Language Parity inklusive Skill-Sprachmarkern + Documentation Links +
  BPMN-Modellprüfung + Cloud Runbook Parity + Gantt + AI-SBOM +
  ATP-Runtime-Contract + Knowledge Graph + NaC-On-Prem-Agent-Runtime

## Feste Reihenfolge

1. `process_validate`
2. `unit_tests`
3. `plugin_validate`
4. `privacy_lint` (ab `standard`)
5. `governance_sync` (nur `strict`)
6. `spec_traceability` (nur `strict`)
7. `language_parity` (nur `strict`)
8. `doc_links` (nur `strict`)
9. `bpmn_models` (nur `strict`)
10. `gantt_progress` (nur `strict`; prüft Pflicht-Gantts und
   Mermaid-Render-Sicherheit, gibt aber nur Hinweise für fachliche
   Roadmap-/Scope-/Statusupdates)
11. `cloud_runbook_parity` (nur `strict`)
12. `ai_sbom` (nur `strict`)
13. `atp_runtime_contracts` (nur `strict`)
14. `knowledge_graph` (nur `strict`)
15. `kg_editor` (nur `strict`)
16. `codex_parallel_review` (nur `strict`)
17. `nac_onprem_agent_runtime` (nur `strict`)
18. `gnotkg_costs` (nur `strict`)
19. `secure_document_links` (nur `strict`)
20. `legal_research_connectors` (nur `strict`)
21. `legal_graph_contracts` (nur `strict`)
22. `oci_tenant_identity` (nur `strict`)

## Artefakte

Standardausgabe:

- JSON: `out/quality/status.json`
- Markdown: `out/quality/report.md`
- PR-Kommentar: `out/quality/comment.md` (für Upsert in Pull Requests)

Diese Artefakte werden im CI-Lauf hochgeladen.

## Nutzen für Vorhersagbarkeit

- Gleiche Checks in gleicher Reihenfolge für lokale und CI-Läufe.
- Keine uneinheitlichen Einzelbefehle pro Teammitglied.
- Klare Statuslinie (`PASSED`/`FAILED`) mit nachvollziehbarem Report.
