# Release- und Sync-Playbook

## Zweck

Dieses Playbook standardisiert, wie ein Unternehmens-Fork neue Versionen aus dem zentralen Upstream übernimmt, prüft und freigibt.

## Übernahmezyklus

- Standardzyklus: monatlich oder quartalsweise.
- Außerplanmäßig nur bei sicherheits- oder compliance-kritischen Änderungen.
- Übernommen werden nur freigegebene Upstream-Releases, keine ungeprüften Zwischenstände.

## Rollen im Übernahmeprozess

- `sync_owner`: steuert den gesamten Übernahmezyklus.
- `reviewer_fachlich`: prüft fachliche Auswirkungen.
- `reviewer_compliance`: prüft regulatorische Risiken.
- `approver`: finales Go für produktive Nutzung.

## Standardablauf je Release

1. Upstream-Release identifizieren (`v*` + Changelog).
2. Sync-Branch erstellen: `sync/upstream-YYYY-MM`.
3. Upstream-Stand übernehmen.
4. Impact-Assessment erfassen (fachlich, technisch, regulatorisch).
5. Tests und Validierung ausführen.
6. Sync-PR mit Nachweisen eroefnen.
7. Review und Freigabe nach Rollenmodell.
8. Merge in Unternehmens-`main`.
9. Unternehmens-Release taggen (`v*`) und Rollout starten.

## Pflichtinhalte eines Sync-PR

- Referenz auf Upstream-Release-ID.
- Zusammenfassung der relevanten Änderungen.
- Impact-Einstufung (`low`, `medium`, `high`).
- Testnachweise (Validierung, relevante Regressionen, Pilotfall).
- Rollout-Entscheidung:
  - sofort für neue Vorgänge aktiv,
  - erst nach Pilot,
  - zurückgestellt.

## PR-Gates (Minimum)

- kein direkter Push nach `main`,
- mindestens ein fachlicher Review,
- zusätzlicher Compliance-Review bei `medium/high impact`,
- erfolgreiche Validierung der betroffenen Prozessdateien,
- dokumentierter Verantwortlicher für Rollout-Entscheidung.

## Rollback-Regel

Wenn ein neues Release im Pilot oder Betrieb unzulässige Risiken erzeugt:

1. Rollout für neue Vorgänge sofort stoppen.
2. Rückkehr auf zuletzt freigegebenes Release für neue Vorgänge.
3. Incident und Entscheidungspfad als Issue dokumentieren.
4. Korrektur als Hotfix oder nächster Sync-PR.

Laufende Vorgänge bleiben auf ihrer Startversion und werden nicht rückwirkend umgebogen.

## Artefakte und Nachweise

Jede Übernahme erzeugt mindestens:

- Sync-PR mit Freigabehistorie,
- Release-Tag im Unternehmens-Fork,
- ggf. SBOM-Artefakt gemaess Policy,
- Entscheidungseintrag für Rollout und Geltungsbeginn.
