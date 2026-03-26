# OaC8 Quality Gate

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
- `strict`: `standard` + Governance Policy Sync + Cloud Runbook Parity

## Feste Reihenfolge

1. `process_validate`
2. `unit_tests`
3. `privacy_lint` (ab `standard`)
4. `governance_sync` (nur `strict`)
5. `cloud_runbook_parity` (nur `strict`)

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
