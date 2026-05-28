# Release-Checkliste für Prozessversionen

## Zweck

Diese Checkliste ist das verbindliche Freigabeformular für versionierte
Prozesspakete. Sie verbindet Tag, GitHub Release, Audit-Artefakte und
Rollout-Entscheidung, damit eine Prozessversion später nachvollziehbar geprüft
werden kann.

Die Checkliste gilt für:

- neue oder geänderte Prozesspakete,
- Upstream-Syncs in Unternehmens-Forks,
- produktive Pilotfreigaben,
- Releases, die als Referenzstand für neue Vorgänge genutzt werden.

Nicht gemeint sind reine Tippfehler, interne Doku-Klarstellungen ohne
Prozesswirkung oder lokale Testläufe ohne Freigabecharakter.

## Release-Daten

Vor dem Tag müssen diese Angaben im führenden Issue, PR oder Release-Entwurf
stehen:

- Prozesspaket oder Scope, zum Beispiel `notary`, `software_company` oder ein
  konkreter Usecase.
- Zielversion oder Tag, zum Beispiel `v*`.
- Geltungsbeginn für neue Vorgänge.
- Rollout-Modus:
  - sofort für neue Vorgänge,
  - erst nach Pilot,
  - zurückgestellt.
- Verantwortliche Rollen: fachlicher Review, Compliance-Review, operative
  Freigabe.
- Rückfallstand für neue Vorgänge, falls der Rollout gestoppt werden muss.

## Pflichtprüfungen

Vor Tag und Release müssen die betroffenen Prüfungen frisch dokumentiert sein:

- `python scripts/startup_check.py --profile base --ide auto --run-tests`
- `python scripts/nac.py doctor --profile strict`
- betroffene BPMN-, KG-, Plugin- oder QMS-Prüfungen, wenn der Scope diese
  Flächen ändert,
- GitHub-Checks für Privacy, Secrets und Quality Gate,
- Review-Entscheidung nach dem gewählten Delivery Mode.

Wenn eine Prüfung nicht anwendbar ist, wird der Grund dokumentiert. Ein
fehlendes Werkzeug ist kein stiller Ersatz für einen Nachweis.

## Audit- und Nachweisartefakte

Das Release verweist mindestens auf:

- führendes Issue mit Auftrag, Scope, Risk Gate und Delivery Mode,
- Pull Request oder Owner-Direct-Nachweis,
- Changelog oder Release Notes,
- Test- und Validierungsnachweise,
- betroffene Prozess-, BPMN-, KG- oder QMS-Artefakte,
- SBOM-/AI-SBOM-Artefakte, wenn Abhängigkeiten, Plugins, AI-Flächen oder
  Runtime-Voraussetzungen geändert wurden,
- Datenschutz-/Secrets-Prüfung,
- Freigabeentscheidung und Rollout-Beginn.

Die Artefakte dürfen keine Secrets, PINs, Zugangsdaten, privaten Dokumentinhalte
oder echten Mandatsdaten enthalten.

## Tag- und Release-Ablauf

1. Release-Scope einfrieren und offene Blocker prüfen.
2. Alle Pflichtprüfungen frisch ausführen oder begründet als nicht anwendbar
   dokumentieren.
3. Review- und Freigabeentscheidung im führenden Issue oder PR erfassen.
4. Changelog oder Release Notes mit betroffenen Prozesspaketen schreiben.
5. Tag `v*` auf dem freigegebenen Commit setzen.
6. GitHub Release aus dem Tag erstellen und auf diese Checkliste sowie die
   Nachweisartefakte verweisen.
7. Rollout-Entscheidung für neue Vorgänge dokumentieren.
8. Bei Pilotbetrieb den nächsten Review-Zeitpunkt festhalten.

## Go/No-Go

Ein Release darf nur als freigegeben gelten, wenn:

- der freigegebene Commit eindeutig ist,
- der Tag auf genau diesem Commit liegt,
- alle Pflichtprüfungen und Reviews dokumentiert sind,
- der Rollout-Modus feststeht,
- ein Rückfallstand bekannt ist,
- keine Secrets oder echten Mandatsdaten in Release Notes, Artefakten oder
  GitHub-Kommentaren stehen.

Wenn eines dieser Kriterien fehlt, bleibt der Stand ein Kandidat und wird nicht
als gültige Prozessversion genutzt.

## Nach dem Release

Nach dem Release wird das führende Issue aktualisiert mit:

- Tag und GitHub Release,
- Geltungsbeginn,
- Rollout-Modus,
- Link auf Nachweisartefakte,
- offene Folgeaktionen,
- Entscheidung, ob Pilot-Review, Hotfix oder regulärer nächster Sync nötig ist.
