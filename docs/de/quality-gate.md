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
- `strict`: `standard` + Governance Policy Sync + Language Parity inklusive
  Skill-Sprachmarkern + Documentation Links + BPMN-Modellprüfung + Cloud
  Runbook Parity + Gantt + AI-SBOM + Knowledge Graph

## Feste Reihenfolge

1. `process_validate`
2. `unit_tests`
3. `plugin_validate`
4. `privacy_lint` (ab `standard`)
5. `governance_sync` (nur `strict`)
6. `language_parity` (nur `strict`)
7. `doc_links` (nur `strict`)
8. `bpmn_models` (nur `strict`)
9. `gantt_progress` (nur `strict`)
10. `cloud_runbook_parity` (nur `strict`)
11. `ai_sbom` (nur `strict`)
12. `knowledge_graph` (nur `strict`)

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
