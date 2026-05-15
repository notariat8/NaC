# NoC Quality Gate

## Zweck

Der Quality Gate stellt sicher, dass PRs mit einer vorhersagbaren und reproduzierbaren Pruefreihenfolge bewertet werden.

Prinzip:

- ein Einstiegspunkt,
- feste Reihenfolge,
- maschinenlesbares Ergebnis,
- menschenlesbarer Report.

## Einstieg

Lokal:

```bash
python scripts/quality_gate.py --profile strict
```

CI:

- Workflow: `.github/workflows/quality-gate.yml`
- Profil in CI: `strict`

## Profile

- `minimal`: Prozessvalidierung + Unit Tests
- `standard`: `minimal` + Privacy Lint
- `strict`: `standard` + Governance Policy Sync + Language Parity + Documentation Links + Cloud Runbook Parity + Gantt + AI-SBOM + Knowledge Graph

## Feste Reihenfolge

1. `process_validate`
2. `unit_tests`
3. `plugin_validate`
4. `privacy_lint` (ab `standard`)
5. `governance_sync` (nur `strict`)
6. `language_parity` (nur `strict`)
7. `doc_links` (nur `strict`)
8. `gantt_progress` (nur `strict`)
9. `cloud_runbook_parity` (nur `strict`)
10. `ai_sbom` (nur `strict`)
11. `knowledge_graph` (nur `strict`)

## Artefakte

Standardausgabe:

- JSON: `out/quality/status.json`
- Markdown: `out/quality/report.md`
- PR-Kommentar: `out/quality/comment.md` (fuer Upsert in Pull Requests)

Diese Artefakte werden im CI-Lauf hochgeladen.

## Nutzen fuer Vorhersagbarkeit

- Gleiche Checks in gleicher Reihenfolge fuer lokale und CI-Laeufe.
- Keine uneinheitlichen Einzelbefehle pro Teammitglied.
- Klare Statuslinie (`PASSED`/`FAILED`) mit nachvollziehbarem Report.
