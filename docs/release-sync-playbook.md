# Release- und Sync-Playbook

## Zweck

Dieses Playbook standardisiert, wie ein Unternehmens-Fork neue Versionen aus dem zentralen Upstream uebernimmt, prueft und freigibt.

## Uebernahmezyklus

- Standardzyklus: monatlich oder quartalsweise.
- Ausserplanmaessig nur bei sicherheits- oder compliance-kritischen Aenderungen.
- Uebernommen werden nur freigegebene Upstream-Releases, keine ungeprueften Zwischenstaende.

## Rollen im Uebernahmeprozess

- `sync_owner`: steuert den gesamten Uebernahmezyklus.
- `reviewer_fachlich`: prueft fachliche Auswirkungen.
- `reviewer_compliance`: prueft regulatorische Risiken.
- `approver`: finales Go fuer produktive Nutzung.

## Standardablauf je Release

1. Upstream-Release identifizieren (`v*` + Changelog).
2. Sync-Branch erstellen: `sync/upstream-YYYY-MM`.
3. Upstream-Stand uebernehmen.
4. Impact-Assessment erfassen (fachlich, technisch, regulatorisch).
5. Tests und Validierung ausfuehren.
6. Sync-PR mit Nachweisen eroefnen.
7. Review und Freigabe nach Rollenmodell.
8. Merge in Unternehmens-`main`.
9. Unternehmens-Release taggen (`v*`) und Rollout starten.

## Pflichtinhalte eines Sync-PR

- Referenz auf Upstream-Release-ID.
- Zusammenfassung der relevanten Aenderungen.
- Impact-Einstufung (`low`, `medium`, `high`).
- Testnachweise (Validierung, relevante Regressionen, Pilotfall).
- Rollout-Entscheidung:
  - sofort fuer neue Vorgaenge aktiv,
  - erst nach Pilot,
  - zurueckgestellt.

## PR-Gates (Minimum)

- kein direkter Push nach `main`,
- mindestens ein fachlicher Review,
- zusaetzlicher Compliance-Review bei `medium/high impact`,
- erfolgreiche Validierung der betroffenen Prozessdateien,
- dokumentierter Verantwortlicher fuer Rollout-Entscheidung.

## Rollback-Regel

Wenn ein neues Release im Pilot oder Betrieb unzulaessige Risiken erzeugt:

1. Rollout fuer neue Vorgaenge sofort stoppen.
2. Rueckkehr auf zuletzt freigegebenes Release fuer neue Vorgaenge.
3. Incident und Entscheidungspfad als Issue dokumentieren.
4. Korrektur als Hotfix oder naechster Sync-PR.

Laufende Vorgaenge bleiben auf ihrer Startversion und werden nicht rueckwirkend umgebogen.

## Artefakte und Nachweise

Jede Uebernahme erzeugt mindestens:

- Sync-PR mit Freigabehistorie,
- Release-Tag im Unternehmens-Fork,
- ggf. SBOM-Artefakt gemaess Policy,
- Entscheidungseintrag fuer Rollout und Geltungsbeginn.
