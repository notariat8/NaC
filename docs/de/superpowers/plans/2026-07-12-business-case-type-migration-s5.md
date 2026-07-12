# BusinessCaseType Migration S5 Implementierungsplan

**Status:** offline im Branch implementiert; WP1-WP8 abgeschlossen; WP9 offen bis Review, Strict-Gate und Protected PR
**Spec:** [BusinessCaseType Migration S5 Design](../specs/2026-07-12-business-case-type-migration-s5-design.md)
**Leading Issue:** [GitHub #618](https://github.com/notariat8/NaC/issues/618)
**Delivery Mode:** Protected PR
**Risk Gate:** Privacy
**Review Gates:** Privacy, External Service und Human Approval geschlossen
**Thresholds:** Allowed live calls = 0; Allowed tenant writes = 0

## Ziel

Die vollständige S5-Migrationslogik als deterministische Offline-Runtime mit
synthetischem Bundle, persistenter lokaler Quarantäne, zentraler CLI und
ausführbaren Contracts umsetzen. Der Plan endet vor jeder Microsoft-Graph-,
Tenant-, Schema-, Backfill-, Cutover-, Rollback- oder Cleanup-Aktion.

## Acceptance-Mapping

- **AC-S5-01:** sieben disjunkte Inventarklassen und fail-closed Mapping.
- **AC-S5-02:** kanonisch gehashte Manifest-/Snapshot-Bindung.
- **AC-S5-03:** idempotenter `VorgangstypId`-Plan mit ETag und Quarantäne.
- **AC-S5-04:** zwei stabile Endscans und strikte Cutover-Readiness.
- **AC-S5-05:** deterministische gepinnte N-/N-1-Profil-Evaluation ohne Runtime-Ausführungsbehauptung.
- **AC-S5-06:** feste Rollback-Reihenfolge und blockierte Forward-Recovery.
- **AC-S5-07:** CLI, Contracts, Validator, Tests, Doku, Gates und Review.

## Arbeitspakete

- [x] **WP1 – Governance-Synchronisierung vorbereiten:** den in PR #617
  implementierten S4-Runtime-Stand in beiden S4-Contracts, Standalone-Validator,
  DE/EN-Spec und -Plan, ADR, Agent-Context, Roadmap und Gantts synchronisieren
  und S4 und S5 in `contracts validate/verify` registrieren. S4-WP9 und Issue
  #616 bleiben bis zum Merge dieses Protected PR mit grüner Remote-CI offen.
- [x] **WP2 – Domainmodell und Klassifikation:** Bundle-Typen, exakte
  Vier-Werte-Baseline, getrenntes versioniertes Legacy-Choice-Mapping,
  disjunkte Entscheidungstabelle, kanonische Hashes und Page-Grenzen
  implementieren.
- [x] **WP3 – Backfill-Plan und Quarantäne:** feste Sortierung und Seitengröße,
  idempotente `VorgangstypId`-Operationen, ETag-Bindung und crash-sichere
  content-addressed Quarantäne ohne Close/Delete-Pfad implementieren.
- [x] **WP4 – Manifest und Snapshots:** Akten-, Registry- und optionale
  Prozessregister-Snapshots einschließlich `not_provisioned`, Row-ETags,
  nullable BPMN-Links, Git-HEAD und Versionsbindungen implementieren.
- [x] **WP5 – Endscans, Profilevaluation und Recovery:** zwei unabhängig
  erfasste Scan-Seitenmengen, vollständige Manifestbindung,
  900-Sekunden-Stabilitätsregel, lokale N-/N-1-Profil-Evaluation,
  separat gepinnte Kandidatenprofile, sechsstufigen Rollback mit späterer
  ausführbarer N-1-Pflichtvalidierung und S6/S7-blockierte Forward-Recovery
  implementieren.
- [x] **WP6 – CLI und Fixtures:** zentrale
  `business-case-type-migration-dry-run`-Bedienkante und Fixtures für alle
  sieben Klassen, Clean-Cutover, Prozessregister `present`/
  `not_provisioned`, Pagingdrift, Replay sowie Quarantäne-Retry/-Konflikt
  integrieren.
- [x] **WP7 – Contracts und Verification:** Domain-/Verification-Contract,
  Standalone-Validator, beide Contract-READMEs, `contracts validate/verify`,
  Agent Verification-Contract-, Decision- und Invariant-Indizes, Escaped-Newline-Prüfung im Traceability-Validator, Strict-Gate
  sowie DE/EN-Quality-Gate-Dokumentation ergänzen.
- [x] **WP8 – Tests:** Entscheidungstabelle, Baseline-/Mappingdrift,
  Hashstabilität, Page-Reihenfolge/-Grenzen/-Duplikate, Idempotenz,
  Quarantäne-Crash-Reconciliation, ETag-Konflikte, Scan-Zeitgrenzen,
  N-/N-1-Fälle, Rollback-Reihenfolge, Pfadgrenzen, linked/detached Git-HEAD-Auflösung, Output-Atomizität, Redaction und No-Live
  testen.
- [ ] **WP9 – Abschluss:** vollständige `base...head`-Diff prüfen,
  unabhängigen Security-/Governance-Review durchführen, Findings beheben und
  Protected PR mit grünen Remote-Checks bereitstellen.

## Parallelisierung

Nach Planfreigabe arbeiten drei disjunkte Stränge parallel:

1. Domain-Klassifikation, Mapping und Backfill-Plan,
2. Snapshot, Quarantäne, Scan, Replay und Recovery,
3. Contracts, CLI, Fixtures, Validator und Governance-Integration.

Der Hauptlauf integriert die Stränge, löst Überschneidungen in
`src/nac_cli/cli.py`, `scripts/quality_gate.py` und den Indizes und führt die
Gesamtvalidierung aus.

## Validierungsreihenfolge

1. fokussierte S5-Domain-, CLI- und Contract-Tests,
2. S5-Standalone-Validator und bestehende S3-/S4-Regressionstests,
3. CLI-Hilfe und `nac contracts verify`,
4. Spec-Traceability, Sprachparität, Links, Gantt und Agent-Context,
5. vollständiges Strict-Gate,
6. `git diff --check`, vollständige `base...head`-Reviews und Remote-CI.

## Abschlussregel

S5 gilt erst nach Erfüllung aller sieben ACs, bestandener lokaler und Remote-
Validierung, unabhängigen Reviews und Protected-PR-Checks als implementiert.
Auch danach bleiben Live-Mutationen durch S6 und S7 blockiert.
