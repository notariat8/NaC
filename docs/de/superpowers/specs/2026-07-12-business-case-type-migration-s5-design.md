# BusinessCaseType Migration S5 Design

Status: offline im Branch implementiert; Abschluss nach Review, Strict-Gate und Protected PR
Datum: 12. Juli 2026
Scope: deterministische, vollständig offline ausgeführte Migration vom Legacy-Choice zur stabilen `BusinessCaseTypeId`

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-migration-s5
leading_issue: https://github.com/notariat8/NaC/issues/618
risk_gate: Privacy
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-07-12-business-case-type-migration-s5.md
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S5-01
  - AC-S5-02
  - AC-S5-03
  - AC-S5-04
  - AC-S5-05
  - AC-S5-06
  - AC-S5-07
validation_commands:
  - python3 -m unittest tests.test_business_case_type_migration tests.test_business_case_type_migration_quarantine tests.test_business_case_type_migration_cli tests.test_business_case_type_migration_contract
  - python3 -m unittest tests.test_business_case_type_runtime tests.test_business_case_type_cache tests.test_business_case_type_graph_read_edge tests.test_business_case_type_graph_read_edge_cli tests.test_business_case_type_graph_read_edge_contract tests.test_business_case_type_cli
  - python3 scripts/validate_business_case_type_migration.py
  - python3 scripts/nac.py kg business-case-type-migration-dry-run --help
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/validate_gantt_progress.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Zweck Und Grenze

S5 implementiert die Migrationslogik als lokale Python-Domain-Runtime. Sie
liest ausschließlich schema-validierte synthetische Fixtures unter
`tests/fixtures/business-case-type-migration/`, erzeugt deterministische
Pläne und redigierte Nachweise und führt keine Microsoft-Graph-, SharePoint-,
Entra-, HTTP-, DNS- oder Tenant-Aktion aus. S4b-Writes, S6 Immutable Evidence
und S7 Live-Freigabe bleiben getrennte Scopes. Ohne S6 und S7 bleibt jeder
echte Backfill, Cutover, Rollback oder Reconciliation-Abschluss blockiert.
Allowed live calls und allowed tenant writes sind jeweils exakt null.

## Eingabemodell Und Datenminimierung

Die statische Mappingtabelle liegt separat und versioniert unter
`workflows/migrations/business-case-type/legacy-choice.mapping.json`. Sie ist
nicht mit den historischen Slug-Aliasen aus S3 identisch. Das Offline-Bundle
bindet ihren kanonischen Hash, einen gebundenen Katalogstand, vollständig
nummerierte synthetische Aktenseiten, Registry- und optionale
Prozessregister-Snapshots und zwei Endscans. Jeder Endscan trägt seine eigene,
unabhängig erfasste paginierte Zeilenmenge; Scan-Zusammenfassung und -Hash
werden ausschließlich daraus rekonstruiert. Beide Registry-Snapshots müssen
exakt alle kanonischen IDs des gebundenen Runtime-Katalogs enthalten.
Zusätzlich enthält jedes Fixture einen eigenen `post_scan_observed_at`-Zeitpunkt sowie unabhängig materialisierte `post_scan_registry_snapshot`- und `post_scan_process_snapshot`-Objekte. Der Zeitpunkt muss strikt nach Scan zwei liegen; diese Post-Scan-Snapshots werden nicht aus den Manifest-Snapshots wiederverwendet.
Profile für die lokale N-/N-1-Capability-Evaluation liegen unabhängig vom
Szenario-Fixture unter
`workflows/migrations/business-case-type/runtime-candidates.json`; das Bundle
bindet Registry-Hash und Evaluationsszenarien.

Die Fixture-Wurzel trägt `data_classification="synthetic"` und
`contains_production_data=false`; Record-Referenzen entsprechen
`synref-[a-z0-9-]+`. Eine Zeile enthält nur `record_ref`,
`snapshot_etag`, `current_etag`, `legacy_choice`,
`business_case_type_id` und `read_status`. Dokumente, Personen, Freitext,
Graph-Rohantworten, Tokens und auflösbare Aktenzeichen sind verboten.
ETags, Snapshot-Felder, lokale BPMN-Links und Freigabereferenzen besitzen enge synthetische Grammatiken; Freigabereferenzen werden im Manifest nur gehasht gespeichert.

Stdout veröffentlicht Status, `S5_OFFLINE_ONLY`-Scope, den weiterhin
`BLOCKED_PENDING_S6_S7_APPROVAL` gesetzten Live-Cutover-Status, die beiden
Null-Live-Grenzen, feste Reason-Codes, Klassen-Counts und Top-Level-Hashes. Das redigierte Artefakt darf zusätzlich Operationsplan,
`record_ref_hash`, Ziel-ID, `if_match`, Idempotency-Key, Page-Hashes,
Quarantäne-IDs sowie Scan-, Profilevaluations- und Recovery-Ergebnisse
enthalten. Ein abschließender `readiness_evidence_hash` bindet Basemanifest,
Backfill-Plan, Evaluationsszenarien, Profilevaluation und reconciliierten
Quarantäneindex. Quarantäne enthält nur pseudonyme Hashes, ETags,
Klassifikation, Manifest-Hash und fixture-gebundene RFC-3339-UTC-Zeitwerte.
Sie ist persistent, aber nicht revisionssicher. Ihr Filesystem-Lock bleibt von
Reconciliation bis nach Readiness-Entscheidung und Output-Commit gehalten.
Bestehende Dateien werden nonblocking gelesen; Records sind auf 16 KiB, der
Index auf 32 MiB und ein Records-Verzeichnis auf 100128 Einträge begrenzt.

## Deterministische Klassifikation

Jede Zeile enthält alle sechs definierten Keys. Die beiden fachlichen Werte
sind entweder JSON `null` oder nichtleere Strings; leere oder reine
Whitespace-Strings sind `unresolved`. Fehlende Keys, eine ungültige
`record_ref` oder doppelte Referenzen über Seitengrenzen hinweg machen das
gesamte Bundle ungültig. Die kanonische Top-Level-Seitenmenge muss exakt der
zweiten Endscan-Seitenmenge entsprechen; damit klassifiziert Readiness immer
denselben final beobachteten Bestand.

Die disjunkte Auswertungsreihenfolge ist normativ:

1. `read_status != "complete"` oder ein ungültiger fachlicher Feldtyp ergibt
   `unresolved`.
2. Fehlender, leerer oder zwischen Snapshot und aktuellem Read abweichender
   ETag ergibt `etag_skipped`.
3. Sind beide fachlichen Werte `null`, ergibt dies `missing`.
4. Sind beide Werte gesetzt, ergibt nur eine bekannte kanonische ID mit exakt
   demselben bekannten Legacy-Mapping `already_canonical`; jeder andere Fall
   ist `conflict`.
5. Ist nur die neue ID gesetzt, ergibt eine bekannte kanonische ID
   `already_canonical`, andernfalls `unknown`.
6. Ist nur der Legacy-Wert gesetzt, ergibt ein exaktes Mapping `mappable`,
   andernfalls `unknown`.

Damit erhält jede gültig geformte Zeile exakt eine der sieben Klassen
`already_canonical`, `mappable`, `conflict`, `unknown`, `missing`,
`etag_skipped` oder `unresolved`. Werte werden nicht getrimmt,
normalisiert, kleingeschrieben oder geraten.

Die Mappingquellen entsprechen exakt und ohne Zusatzwerte den vier
eingefrorenen Legacy-Choices `immobilienkaufvertrag`,
`unterschriftsbeglaubigung`, `online-gmbh-gruendung` und
`handelsregisteranmeldung`. Legacy-Choice und kanonische ID sind getrennte typisierte Namensräume;
identische Strings über beide Namensräume hinweg sind ausdrücklich zulässige
Identity-Mappings. Jedes Legacy-Choice besitzt genau ein direktes kanonisches
Ziel. Doppelte Quellen, mehrere Ziele, unbekannte Ziele, zusätzliche Quellen
oder unvollständige Baseline-Abdeckung blockieren das Bundle. Alias-Ketten- und
Selbstzielregeln aus S3 werden nicht auf diese typisierten Identity-Mappings
übertragen. Mapping-Version und Manifest binden den kanonischen
Baseline-Fingerprint.

## Backfill-Plan Und Quarantäne

Eingabeseiten sind vollständig nummeriert: `page_number` beginnt bei 1 und
ist lückenlos, `page_count` ist auf jeder Seite identisch und nur die letzte
Seite trägt `complete=true`. Zulässig sind höchstens 1.000 Seiten, 100 Zeilen
je Seite und 100.000 Zeilen insgesamt. Ungültige oder unvollständige Seiten und
seitenübergreifende Duplikate liefern kein partielles Ergebnis.

Nur `mappable` erzeugt eine geplante Operation. Sie setzt ausschließlich
`VorgangstypId`, bindet den aktuellen Item-ETag als späteres `If-Match` und
besitzt einen stabilen Idempotency-Key aus Manifest-Hash,
`record_ref_hash`, Ziel-ID und ETag. `already_canonical` erzeugt ein No-op.
Die fünf Blockerklassen werden ohne Mutation quarantänisiert. Operationen
werden unabhängig von Eingabeseitengrenzen nach `record_ref_hash` sortiert
und mit fester Seitengröße 100 neu paginiert. Jede Seite trägt
`page_number`, `operation_count` und kanonischen Page-Hash; der Plan bindet
die geordneten Page-Hashes.

`record_ref_hash` ist SHA-256 der exakten Fixture-Referenz. `record_id` ist
SHA-256 aus Manifest-Hash, `record_ref_hash`, Klassifikation und aktuellem
ETag. `observed_at` stammt aus dem Fixture und ist nicht Teil der Identität.
Der Writer schreibt einen temporären Record im Zielverzeichnis und
synchronisiert ihn. Er veröffentlicht ihn per atomarem Hard-Link mit
No-overwrite-Semantik. Existiert das Ziel bereits, vergleicht er die Bytes:
identisch ist ein No-op, abweichend blockiert; ein bestehendes Ziel wird nie
ersetzt. Temporärdatei und Verzeichnis werden anschließend synchronisiert und
aufgeräumt. Danach baut er
den Index nur aus vollständig lesbaren content-addressed Records neu und
ersetzt auch ihn atomar. Der Startup-Abgleich nimmt vollständige verwaiste
Records in den Index auf; Referenzen auf fehlende oder ungültige Records
blockieren. Identische Records sind No-ops, abweichender Inhalt unter derselben
ID blockiert. Teilfehler liefern `artifact_write_failed` und nie partiellen
Erfolg. S5 besitzt keine Close-/Delete-Operation.

## Manifest Und Snapshots

Das Migrationsmanifest bindet mindestens:

- Repo-Commit, `CatalogVersion`, Mapping-, Schema-, Runtime- und
  Contract-Version N sowie das gepinnte, noch nicht ausführbar validierte N-1-Profil,
- gehashte Site-, Schema- und List-Bindungen,
- kanonischen Hash und Zeilenanzahl aller Aktenseiten einschließlich
  relevanter Feldwerte und Item-ETags,
  Der Hash erhält Page-Nummer, Page-Count, Complete-Flag, Seitengrenzen und die pro Seite technisch sortierten Zeilen; ein anderes Paging ergibt einen anderen Manifest-Hash.
- vollständigen `Vorgangsartenregister`-Snapshot mit Zeilen-ETags,
- `Prozessregister` als `present` mit Zeilen-ETags und nullable BPMN-Links oder
  explizit als `not_provisioned`,
- Mapping-Hash, gehashte synthetische Rollenfreigabe-Referenzen und alle Snapshot-Hashes.

Hashes entstehen exakt mit `json.dumps(value, sort_keys=True,
separators=(",", ":"), ensure_ascii=True, allow_nan=False)` und SHA-256 über
die UTF-8-Bytes. Erlaubt sind nur JSON-null, bool, Integer, String, Liste und
Objekt; Floats sind verboten. Eingabereihenfolgen werden vor dem Hashing anhand
stabiler technischer Schlüssel sortiert.

## Stabile Endscans Und Cutover-Readiness

Der Scan-Hash umfasst die vollständige kanonische Seitenform einschließlich
Seitennummer, Seitenanzahl, Abschlussflag und aller sechs exakt typisierten,
nach `record_ref` sortierten synthetischen Zeilenfelder.
Cutover-Readiness ist nur `READY`, wenn alle Datensätze
`already_canonical` sind und alle fünf Blockerklassen exakt null
zählen, beide paginierten Scans vollständig sind, unterschiedliche Scan-IDs
tragen, Migrationswrites jeweils eingefroren sind, mindestens 900 Sekunden
auseinanderliegen und Anzahl sowie Hash identisch sind.

Jede Abweichung liefert `BLOCKED` und verlangt zwei neue vollständige Scans.
Eine bereits befüllte, reconciliierte append-only Quarantäne blockiert
`READY` ebenfalls. Registry- und Prozesssnapshots werden nach Scan zwei neu
berechnet; beide vollständigen Scan-Seitenmengen, ihre Zusammenfassungen,
`post_scan_observed_at` und die Post-Scan-Snapshots sind Bestandteil des
Manifest-Hashes.

## N-/N-1-Profil-Evaluation

`runtime-candidates.json` pinnt Kandidaten-IDs, Contract-Versionen, Profile und
erwartete Profilhashes außerhalb aller Szenario-Fixtures; der Domain-Contract
bindet zusätzlich den Hash dieser Registry. Ein lokaler
`MigrationReplayPort` evaluiert für N und N-1 dieselben vier fest
codierten Profil-Szenarien: `VorgangstypId` lesen, additive Registry-Felder
ignorieren, unbekannte IDs fail-closed behandeln und neue Typen ohne
Legacy-Choice read-only anzeigen. Jeder Kandidat ist durch Kandidaten-ID,
Contract-Version und SHA-256 seines lokalen Replay-Profils gebunden.

Das Ergebnis enthält pro Kandidat und Szenario die vom Profil-Evaluator
erzeugte Entscheidung und einen festen Reason-Code; Fixture-Boolean-
Zusicherungen gelten nicht als Capability-Nachweis. Ein fehlgeschlagener
Einzelcheck oder Profilhash-Drift blockiert die Offline-Readiness. Der Nachweis
führt weder Kandidaten-Runtime noch Binärdatei, Deployment oder Release aus und
behauptet ausschließlich statische Contract-Kompatibilität des gepinnten
Profils. Ausführbare N-/N-1-Validierung bleibt vor jedem Umschalten Pflicht.

## Rollback Und Forward-Recovery

Der Rollback-Plan ist unveränderlich geordnet:

1. Neuanlage, Korrektur, Backfill, Cutover und abhängiges Routing stoppen.
2. Rollback-Intent, aktuelle Snapshots/ETags und Quarantäne über die noch zu
   implementierende immutable S6-Evidence sichern.
3. Canonical-Write-Flag deaktivieren und Registry-/Prozess-Caches invalidieren.
4. Erst nach separater ausführbarer Validierung auf einen freigegebenen N-1-Kandidaten zurückschalten.
5. Registry-/Prozessprojektionen nur bei Bedarf und nur ETag-gebunden gegen
   den im Manifest gebundenen Snapshot wiederherstellen; Spalten und
   kanonische Werte bleiben erhalten.
6. Readback und vollständigen Rescan ausführen und nur eindeutig abbildbare
   Legacy-Writes wieder öffnen.

Forward-Recovery deployt N erneut, lädt Katalog und Register frisch, verlangt
die noch zu implementierende immutable S6-Outbox und plant deren idempotenten
Replay, verlangt die Klärung sämtlicher Quarantänefälle und zwei neue stabile
Endscans. Sie erzeugt keine Legacy-Ersatzwerte und führt in S5 keine Aktion
aus. Beide Pläne melden `BLOCKED_PENDING_S6_S7_APPROVAL`.

## Zentrale CLI

Die Bedienkante lautet:

```text
nac kg business-case-type-migration-dry-run
```

Relative Pfade werden gegen `--repo-root` aufgelöst. `--fixture` muss eine
reguläre Datei innerhalb von
`tests/fixtures/business-case-type-migration/` sein; ein Symlink, der diese
Grenze verlässt, wird abgelehnt. `--quarantine-state` und `--output` werden kanonisch aufgelöst, dürfen keine
Symlink-Komponente besitzen und sind unterschiedliche, nicht überlappende Ziele
unter dem kanonisch aufgelösten `out/notary-kg/`.
`--output` hat den Default
`out/notary-kg/business-case-type-migration-s5.redacted.json`; das
Quarantäneverzeichnis ist Pflicht. Die zentrale CLI delegiert nur diese Pfade
an `notary_kg.cli`; Domain-I/O liegt nicht in `nac_cli`.

Der aktuelle Repo-Commit wird ohne Subprozess aus Git-Metadaten gelesen und in
das Manifest gebunden. Die Auflösung unterstützt `.git`-Verzeichnis oder
Worktree-`.git`-Datei, symbolisches oder detached HEAD, lose und `packed-refs`.
Unlesbares, ungeborenes oder nicht eindeutig auflösbares HEAD liefert
`repository_state_unavailable`. Fixture-Reads sind vor dem Lesen auf 4 MiB,
normale Git-Admin-Dateien auf 1 MiB und `packed-refs` auf 8 MiB begrenzt. Dirty-Worktree-Zustand ist nicht Teil dieses
Hashes; Protected-PR- und Strict-Gates bleiben dafür autoritativ. Sämtliche
Zeitwerte stammen normalisiert als UTC-Sekunden mit `Z` aus dem Fixture;
Wanduhrzeit wird nicht gelesen.

Der Befehl akzeptiert keine Site-, Tenant-, Token-, Zertifikat-, URL-, Graph-,
Credential-, Apply-, Cutover-, Rollback- oder Cleanup-Option. `READY` ist
ausschließlich qualifizierte S5-Offline-Readiness, enthält immer den blockierten
Live-Cutover-Status und liefert Exit-Code 0; ein gültig ausgewertetes
`BLOCKED` liefert Exit-Code 2. Form-, Contract-,
Hash- oder Persistenzfehler liefern Exit-Code 1. Das redigierte Output-Artefakt wird wie
der Index unter einem zielspezifischen Filesystem-Lock über temporäre Datei,
Sync und atomaren Replace geschrieben. Rollback erfolgt nur, solange das Ziel
noch dem eigenen Replacement-Inode entspricht; ein deklarierter
`.<name>.previous`-Recovery-Marker wird beim nächsten gelockten Start
deterministisch reconciliiert. Erlaubte Fehlercodes sind
`fixture_invalid`, `contract_invalid`, `artifact_write_failed`,
`repository_state_unavailable`;
fachliche Blocker verwenden die sieben Klassennamen sowie `scan_unstable`,
`profile_evaluation_failed` und `blocked_pending_s6_s7`.

## Akzeptanzkriterien

- **AC-S5-01:** Jede synthetische Akte wird deterministisch genau einer der
  sieben Klassen zugeordnet; uneindeutige, unbekannte, leere oder
  widersprüchliche Werte blockieren fail-closed.
- **AC-S5-02:** Das Basemanifest bindet alle Versionen, unabhängig erfassten
  Endscans und Snapshots einschließlich Item-/Row-ETags, nullable BPMN-Links
  und explizitem `not_provisioned`-Zustand. Der finale Evidence-Anchor bindet
  zusätzlich Backfill-Plan, Szenarien, Profilevaluation und Quarantäneindex.
- **AC-S5-03:** Der Backfill-Plan ist paginiert und idempotent, plant
  ausschließlich `VorgangstypId` mit aktuellem Item-ETag/`If-Match` und
  übernimmt alle fünf Blockerklassen dauerhaft in eine lokale persistente Quarantäne. Er führt
  keine Graph-, Tenant-, Registry-, Prozessregister- oder Akten-Writes aus;
  ausschließlich die deklarierten lokalen redigierten Artefakte werden
  geschrieben.
- **AC-S5-04:** S5-Offline-Readiness verlangt ausschließlich
  `already_canonical`, exakt null Blockerklassen, vollständige Registry-
  Abdeckung, eine leere reconciliierte Quarantäne und zwei unabhängig erfasste
  identische vollständige Scans bei eingefrorenen Writes mit mindestens 15
  Minuten Abstand.
- **AC-S5-05:** Die gepinnte N-/N-1-Profil-Evaluation prüft Lesen von
  `VorgangstypId`, Ignorieren additiver Registry-Felder, fail-closed unbekannte
  IDs und read-only Darstellung neuer Typen ohne Legacy-Choice, ohne
  ausführbare Runtime-Validierung zu behaupten.
- **AC-S5-06:** Rollback hält die festgelegte sechsstufige Reihenfolge ein und
  löscht keine Spalten oder Werte; Forward-Recovery nutzt keine
  Legacy-Ersatzwerte und bleibt ohne S6/S7 blockiert.
- **AC-S5-07:** Zentrale CLI, Domain-/Verification-Contract, Validator,
  synthetische Tests, DE/EN-Dokumentation, Strict-Gate und unabhängiger
  `base...head`-Review bestehen bei exakt null Live-Aufrufen.

## Nichtziele

- kein Live-Graph, kein Tenant-Write und keine Credential-Nutzung,
- kein Schema-Apply, Backfill-Write, Cutover, Rollback oder Cleanup,
- keine revisionssichere Evidence-Behauptung vor S6,
- kein Reconciliation-Abschluss und keine Quarantäne-Löschung,
- keine produktiven Akten-, Personen- oder Dokumentdaten.
