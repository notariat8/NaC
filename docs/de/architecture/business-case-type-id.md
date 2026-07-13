# ADR: Stabile BusinessCaseTypeId

Status: Angenommen; S1/S2/S3/S4 offline implementiert, S5 in Umsetzung, kein Live-Apply
Issues: [GitHub #610](https://github.com/notariat8/NaC/issues/610), [GitHub #612](https://github.com/notariat8/NaC/issues/612), [GitHub #616](https://github.com/notariat8/NaC/issues/616), [GitHub #618](https://github.com/notariat8/NaC/issues/618)
Datum: 2026-07-11

## Kontext

Der versionierte Usecase-Katalog führt die fachliche Entität
`BusinessCaseType`. Die aktive SharePoint-MVP-Liste `Akten` projiziert sie
derzeit als Pflicht-Choice `Vorgangstyp` mit vier Werten. Neue Vorgangsarten
würden deshalb je Workspace eine privilegierte Choice-Schemaänderung erfordern.
Der optionale BPMN-Viewer-Plan definiert dagegen bereits den indexierten
Textschlüssel `Prozessregister.ProcessKey`.

Diese Entscheidung führt den
[notariellen Prozessontologie-Vertrag](../../../workflows/contracts/notarial-process-ontology.contract.json)
und den
[BPMN-Viewer-Adapter-Vertrag](../../../workflows/contracts/m365-sharepoint-bpmn-viewer-adapter.contract.json)
auf eine Identität zusammen. Die heutigen Grenzen prüfen der
[Prozessontologie-Validator](../../../scripts/validate_notarial_process_ontology_contract.py)
und der
[BPMN-Viewer-Adapter-Validator](../../../scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py).
Issue #610 implementiert S1 und S2 ausschließlich offline in Verträgen,
Validatoren, Inventar und Schema-Planung. Es wurden keine Graph-Requests
ausgeführt, kein Tenant verändert und kein SharePoint-Schema live angewendet.
S1 bis S4 sind offline implementiert. S5 wird nach der
[S5-Spec](../superpowers/specs/2026-07-12-business-case-type-migration-s5-design.md)
und dem
[S5-Implementierungsplan](../superpowers/plans/2026-07-12-business-case-type-migration-s5.md)
in Issue #618 ausschließlich offline umgesetzt. Der Status bleibt bis zu
Code-, Vertrags-, Negativtest-, Strict-Gate-, Review- und Protected-PR-Nachweisen
`in Umsetzung`. S6 und S7 bleiben offen.

## Entscheidung

`BusinessCaseTypeId` ist der kanonische, unveränderliche Text-Identifier einer
notariellen Vorgangsart. Für jede kanonische Vorgangsart gilt exakt:

```text
BusinessCaseTypeId == Vorgangsartenregister.BusinessCaseTypeId
                   == Akten.VorgangstypId

Wenn eine Prozesszeile existiert:
BusinessCaseTypeId == Prozessregister.ProcessKey
```

- Der Wert ist der freigegebene kanonische Usecase-Slug in Kleinschreibung und
  Kebab-Case (`^[a-z0-9]+(?:-[a-z0-9]+)*$`, maximal 128 Zeichen).
- Vergleich und Speicherung erfolgen exakt. Runtime-Eingaben mit abweichender
  Großschreibung, Leerraum oder stiller Normalisierung werden abgelehnt.
- Ein veröffentlichter Identifier wird weder umbenannt noch erneut vergeben.
  Fachliche Nachfolger erhalten einen neuen Identifier; der alte Eintrag wird
  als nicht auswählbar oder stillgelegt markiert.
- `Vorgangsartenregister` ist eine schlanke, viewer-unabhängige
  Runtime-Projektion mit eindeutigem, indexiertem `BusinessCaseTypeId`,
  `LifecycleStatus`, `Selectable` und `CatalogVersion`. Sie enthält keine
  BPMN-, Modell- oder Viewer-Pflichtfelder und wird über
  `business_case_type_get` gelesen.
- `Prozessregister` bleibt optional. Existiert eine Zeile, ist `ProcessKey`
  indexiert, eindeutig und identisch zur `BusinessCaseTypeId`.
  `NacProcessId` bleibt technische Zeilenidentität; `NacBpmnModelId`,
  `BpmnDriveItemId` und sonstige BPMN-Verknüpfungen sind nullable.
- Eine fehlende `Prozessregister`-Zeile, ein fehlendes BPMN-Modell oder ein
  deaktivierter Viewer macht eine kanonische Vorgangsart nicht ungültig. Nur
  die konkret BPMN- oder viewer-abhängige Operation bleibt dann gesperrt.
- `Akten.VorgangstypId` wird als neue indexierte einzeilige Textspalte geplant.
  `Akten.Vorgangstyp` wird nicht in-place von Choice zu Text konvertiert.

Damit ist der Ontologiebegriff `BusinessCaseType` die fachliche Klasse, der
repo-versionierte Katalog ihre führende Definition, das
`Vorgangsartenregister` ihre minimale Runtime-Projektion und
`Prozessregister` eine optionale Prozess-/Viewer-Projektion. Es wird keine
zweite `BusinessCaseType`-Choice-Spalte eingeführt.

## Kanonische Und Alias-Regeln

Ein Identifier ist zur Runtime nur gültig, wenn der durch Review freigegebene
Repo-Katalog ihn als kanonisch und nicht stillgelegt führt und genau eine
passende Zeile im `Vorgangsartenregister` mit derselben `CatalogVersion`
existiert. Fehlende, doppelte, nicht auswählbare oder stillgelegte
Vorgangsartenzeilen blockieren die Aktenzuordnung. `Prozessregister` wird nur
für eine Prozess-/Viewer-Operation geprüft: Eine vorhandene Zeile mit
abweichendem `ProcessKey` blockiert diese Operation, ihre Abwesenheit blockiert
aber weder die kanonische Gültigkeit noch `case_create`.

Legacy-Aliase wie `grundstueckskaufvertrag` und `testament` bleiben reine
historische Übersetzungen:

- Ein Alias ist niemals `BusinessCaseTypeId`, `ProcessKey` oder
  `VorgangstypId` und darf bei neuen Akten nicht ausgewählt werden.
- Jeder Alias verweist direkt auf genau einen kanonischen Identifier. Ketten,
  Zyklen, mehrdeutige Ziele und Kollisionen mit kanonischen IDs sind ungültig.
- Alias-Übersetzung ist nur für Bestandsmigration oder einen befristeten
  Legacy-Read zulässig und erzeugt ein Audit-Ereignis.
- Ein Alias wird nicht still zu einer neuen Identität hochgestuft. Eine solche
  Änderung braucht eine eigene Architekturentscheidung und Migration.

## Fail-Closed-Validierung Und Cache

Vor `case_create` oder einer Korrektur der Vorgangsart prüft die Runtime über
den viewer-unabhängigen Lookup in dieser Reihenfolge:

1. Syntax und exakte Schreibweise der `BusinessCaseTypeId`.
2. Kanonischer, nicht stillgelegter und für Neuanlage freigegebener Eintrag im
   repo-versionierten Katalog.
3. Genau eine auswählbare, nicht stillgelegte `Vorgangsartenregister`-Zeile mit
   identischer `BusinessCaseTypeId` und passender `CatalogVersion`.
4. Bei einer bestehenden Akte: kein Widerspruch zwischen `VorgangstypId` und
   einem noch gelesenen Legacy-Choice.

Jeder Fehler, Timeout, unbekannte Status, Katalog-/Register-Versionsdrift,
Duplikat oder abgelaufene Cache-Eintrag blockiert die Mutation. Eine read-only
Anzeige darf `validation_unavailable` melden, aber den Wert nicht als gültig
behandeln. Erst eine konkret BPMN-/viewer-abhängige Operation lädt zusätzlich
`Prozessregister`; fehlende oder nicht freigegebene Prozess- oder
BPMN-Metadaten blockieren nur diese Operation.

Der Runtime-Cache enthält nur `BusinessCaseTypeId`, Status, `CatalogVersion`,
Zeilen-ETag und Zeitstempel aus dem `Vorgangsartenregister`, niemals Akten-
oder Dokumentdaten. Schlüssel ist `(siteId, BusinessCaseTypeId,
CatalogVersion)`. Nach fünf Minuten wird revalidiert; nach spätestens 15
Minuten ohne erfolgreiche Revalidierung ist der Eintrag unbrauchbar.
Graph-ETags werden für bedingte Reads genutzt, soweit der Endpunkt sie
unterstützt; andernfalls werden die zurückgegebenen Zeilen-ETags verglichen.
Ein Versionswechsel oder ETag-Konflikt invalidiert den betroffenen Site-Cache
vollständig. Negative Ergebnisse werden höchstens 30 Sekunden gehalten.
Prozess-/Viewer-Metadaten haben einen getrennten Cache und werden nie zur
Gültigkeitsentscheidung einer `BusinessCaseTypeId` herangezogen.

## Übergang Vom Legacy-Choice

Die Migration ist als explizite Zustandsfolge umzusetzen:

| Phase | Leseverhalten | Schreibverhalten | Exit-Kriterium |
| --- | --- | --- | --- |
| `inventory` | Legacy unverändert | keine Writes | redigierter Bestandsscan und eindeutige Mapping-Tabelle |
| `column_ready` | Legacy führend | `VorgangstypId` optional, keine Live-Automatik | owner-gated Schema-Readback bestätigt indexierten Text |
| `dual` | neue ID zuerst, Legacy-Fallback | neue ID immer; Legacy nur bei eindeutigem Altwert | null `unknown`, `missing`, `conflict`, `etag_skipped` oder `unresolved`; stabile Endscans |
| `canonical` | nur `VorgangstypId` | nur `VorgangstypId` | mindestens ein Release mit geprüfter N-1-Kompatibilität ohne Legacy-Fallback |
| `retired_legacy` | Legacy nur Audit-Historie | Legacy gesperrt | separate Cleanup-Freigabe |

Im Dual-Read gilt: Stimmen beide Felder nach der statischen Mapping-Tabelle
überein, gewinnt `VorgangstypId`. Fehlt die neue ID, darf der Legacy-Wert nur
bis zur dokumentierten Frist übersetzt werden. Widerspruch, leerer Wert oder
unbekannter Choice blockiert. Im Dual-Write wird der Legacy-Wert nur gesetzt,
wenn die eingefrorene Choice-Liste ihn abbilden kann. Solange
`Vorgangstyp` noch Pflichtfeld ist, bleiben Neuanlagen auf diese abbildbaren
Werte begrenzt; erst eine separat freigegebene Schemaänderung darf das Feld
optional machen.

`dual` ist auf höchstens zwei Releases oder 90 Kalendertage ab Aktivierung
begrenzt, je nachdem, was zuerst eintritt. Start, Frist und verantwortlicher
Owner stehen im Migrationsmanifest. Eine Verlängerung braucht Review und eine
begründete neue Entscheidung; es gibt keinen unbefristeten Dualbetrieb.

## Backfill, Snapshots Und Recovery

Der spätere Backfill beginnt mit einem read-only Dry-Run. Er klassifiziert jede
Akte als `already_canonical`, `mappable`, `conflict`, `unknown`, `missing`,
`etag_skipped` oder `unresolved` und veröffentlicht nur redigierte Counts und
Hashes. Der owner-gated Write-Lauf arbeitet paginiert und idempotent, schreibt
ausschließlich `VorgangstypId`, verwendet das aktuelle Item-ETag mit `If-Match`
und stellt konkurrierend geänderte Items dauerhaft in Quarantäne. Werte werden
nicht geraten.

Das Migrationsmanifest bindet Repo-Commit und `CatalogVersion`, Schema- und
List-IDs, paginierte `Akten`-Snapshots mit Item-ETags, den vollständigen
`Vorgangsartenregister`-Snapshot sowie einen `Prozessregister`-Snapshot mit
Zeilen-ETags und nullable BPMN-Links. Auch ein nicht vorhandenes
`Prozessregister` wird explizit als `not_provisioned` belegt. Zusätzlich bindet
das Manifest Runtime-/Vertragsversion N, das gepinnte N-1-Profil,
Mapping-Version, Rollenfreigaben und Snapshot-Hashes. Beide unabhängig
erfassten Endscan-Seitenmengen und alle Post-Scan-Nachweise sind ebenfalls
Bestandteil des Manifest-Hashes.

Cutover ist nur zulässig, wenn jede Akte `already_canonical` ist und die Counts
für `unknown`, `missing`, `conflict`, `etag_skipped` und `unresolved` exakt null
sind. Danach laufen bei eingefrorenen Migrationswrites zwei vollständige Scans
im Abstand von mindestens 15 Minuten. Item-Anzahl und Hash über Item-ID,
relevante Feldwerte und ETags müssen identisch sein; jede Abweichung startet
die Prüfung neu. Register- und Prozessregister-Snapshots werden unmittelbar vor
der Freigabe erneut gebunden.

N-1-Kompatibilität ist eine Cutover-Voraussetzung: Der vorherige
Runtime-Kandidat muss `VorgangstypId` lesen, additive Registry-Felder
ignorieren, unbekannte IDs fail-closed behandeln und neue Typen ohne
Legacy-Choice read-only anzeigen können. Die S5-Profil-Evaluation prüft nur
statische Contract-Kompatibilität; ohne spätere ausführbare N-/N-1-Validierung
gibt es weder Umschaltung noch Live-Cutover.

Rollback löscht weder Spalten noch Werte und läuft strikt in dieser Reihenfolge:

1. Akten-Neuanlage, Korrektur, Backfill, Cutover und abhängiges Routing stoppen.
2. Rollback-Intent, aktuelle Snapshots/ETags und Quarantäne immutable sichern.
3. Canonical-Write-Flag deaktivieren und Registry-/Prozess-Caches invalidieren.
4. Erst nach separater ausführbarer Validierung auf einen freigegebenen N-1-Kandidaten zurückschalten.
5. Registry-/Prozessprojektionen nur bei Bedarf und nur ETag-gesichert auf den
   gebundenen Snapshot zurückführen; Spalten und kanonische Werte bleiben.
6. Readback und vollständigen Rescan ausführen; nur eindeutig abbildbare
   Legacy-Writes wieder öffnen.

Forward-Recovery spielt keine Legacy-Ersatzwerte ein. Sie deployt N erneut,
lädt Katalog und Register frisch, spielt die immutable Outbox idempotent nach,
klärt alle Quarantänefälle und wiederholt beide stabilen Endscans. Eine spätere
Spaltenbereinigung bleibt ein eigenes Owner-Gate.

## Berechtigungen, Immutable Evidence Und Datenschutz

- Runtime-Reads und Akten-Metadatenzugriffe verwenden die bestehende, pro Site
  begrenzte `Sites.Selected`-Runtime-App. Sie erhalten keine
  Schema-Administrationsrechte.
- `Sites.Manage.All` bleibt ausschließlich beim kontrollierten, owner-gated
  Provisioning-Pfad. Microsoft dokumentiert es als kleinstes Recht für das
  [Ändern einer Spaltendefinition](https://learn.microsoft.com/en-us/graph/api/columndefinition-update?view=graph-rest-1.0).
- Runtime und Backfill lesen nur ausgewählte Metadatenfelder über Microsoft
  Graph REST v1.0. Keine SharePoint-Dateiinhalte, Graph-Rohantworten, Tokens
  oder Mandats-Payloads werden persistiert.
- `AuditJournalLite` ist nur eine veränderbare Betriebsprojektion und kein
  revisionssicherer Nachweis. Vor jeder Live-Mutation muss ein Intent in eine
  durable append-only Outbox geschrieben und über Broker, Hash-Kette,
  Signatur/Anchor und WORM-Speicher nach der
  [Revisionssicherheits-Policy](../../../policies/revisionssicherheit-eventstream-policy.yaml)
  übernommen werden; Ergebnis und Readback folgen als eigene Events.
- Solange Outbox, immutable Event-Stream, Readback oder eine persistente
  Reconciliation-Quarantäne fehlen, sind Live-Schema-, Backfill-, Korrektur-,
  Cutover- und Rollback-Mutationen verboten. Ein Fehler nach dem SharePoint-
  Write bleibt als `reconciliation_required` dauerhaft gesperrt; nur ein
  separat freigegebener Reconciliation-Abschluss darf ihn aufheben.
- Evidence enthält Correlation-ID, pseudonyme `ActorRef`, Tool-/Rollen-ID,
  Aktion, Ergebniscode, `BusinessCaseTypeId`, Katalog-/Manifestversion sowie
  Registry-, Prozessregister- und Item-ETags. Aktenzeichen und
  Dokumentinhalte bleiben ausgeschlossen.
- `ActorRef` ist trotz Pseudonymisierung personenbezogen. Sie wird als
  tenant-gebundener HMAC der Entra-Objekt-ID mit Key-Version erzeugt; Schlüssel
  und auflösbare Zuordnung liegen getrennt außerhalb von Repo, Event und
  SharePoint. Event und `ActorRef` unterliegen mindestens zehn Jahren
  immutable Retention plus Legal Hold. Zugriff auf pseudonyme Events erhält
  nur `revision_audit`; eine Auflösung braucht dokumentierten Zweck und
  Vier-Augen-Freigabe von `revision_audit` und `freigabeverantwortung`.
  Monatliche Access-Reviews und jeder Auflösungszugriff werden selbst immutable
  protokolliert.

## Rollen Und Funktionstrennung

Die Implementierung bindet diese Operationsrollen an qualifizierte Principals
aus dem bestehenden Rollenmodell; `automation` darf ausführen, aber nie
freigeben.

| Operation | Ausführung | Freigabe | Zwingende Trennung |
| --- | --- | --- | --- |
| Mapping | `MappingAuthor` | `MappingApprover` | Autor und Approver sind verschieden |
| Backfill | `BackfillOperator` | `MappingApprover` und `ReleaseApprover` | Operator war weder Mapping-Autor noch Approver |
| Einzelkorrektur | `MatterCorrector` | `CorrectionApprover` | Korrektur eigener Mapping-/Backfill-Writes ist verboten |
| Reconciliation | `ReconciliationOperator` | `ReconciliationApprover` | Writer darf Quarantäne nicht selbst schließen |
| Cutover | `CutoverOperator` | `ProcessOwner` und `ReleaseApprover` | beide Approver und Operator sind verschiedene Principals; kein Backfill-Operator |
| Rollback | `RollbackOperator` | `RollbackApprover` | Executor und Approver sind verschieden; Approval ist manifest- und snapshot-gebunden |
| Actor-Auflösung | `EvidenceCustodian` | `revision_audit` und `freigabeverantwortung` | duale Zweckfreigabe, kein Runtime-Principal |

Negative Autorisierungstests blockieren mindestens falsche Rolle,
Selbstfreigabe, fehlende getrennte Principals, falsche Site/Akte, abgelaufene
oder manifestfremde Freigabe, Korrektur durch Mapping-/Backfill-Autor,
Quarantäneschluss durch den Writer, Cutover durch den Backfill-Operator,
Rollback ohne unabhängige Freigabe und `ActorRef`-Auflösung ohne duale
Zweckfreigabe.

## Explizite Umsetzungsslices

Diese ADR ist angenommen. Issue #610 hat S1 und S2 am 2026-07-11 offline
implementiert. S3 und S4 sind offline implementiert; S5 bis S7 bleiben offen und brauchen jeweils Review und passende
Tests, bevor ein Live-Apply erwogen wird.

| Slice | Status | Erforderliche Änderung | Abnahmekante |
| --- | --- | --- | --- |
| S1 Vertrag | offline implementiert in #610 | Ontologie-, Inventory- und Viewer-Verträge auf unabhängiges `Vorgangsartenregister`, optionales `Prozessregister`, nullable BPMN-Links und Alias-Invarianten ausrichten | Validatoren beweisen viewer-unabhängige Typgültigkeit und blockieren Drift offline |
| S2 Schema-Plan | offline implementiert in #610 | `Akten.VorgangstypId` und `Vorgangsartenregister` im verpflichtenden Default planen; `Prozessregister` und `BPMN Models` bleiben getrennte optionale Viewer-Provisionierung; Legacy-Choice unverändert lassen | 33 Plan-Schritte und 66 Workspace-Apply-Units; Dry-Run, Readiness, Snapshot- und Rollback-Plan; `BLOCKED_PENDING_S6_S7_APPROVAL` |
| S3 Runtime | offline implementiert in #614 | `business_case_type_get`, inhaltsbasierte `CatalogVersion`, expliziten Runtime-Lifecycle, zweckgebundene Aliase und getrennte Registry-/Viewer-ETag-Caches offline implementieren | Spec, Domain-/Verification Contract, Validator, CLI, Negativtests, Strict-Gate, unabhängiger Review und Protected-PR-Checks bestehen ohne Graph-/Tenant-Zugriff |
| S4 Graph Read Edge | offline implementiert in #617; S4b-Writes offen | `case_create`, Korrektur-/Backfill-Pfad und optionale Prozessreads auf ausgewählte Felder, Paging, ETag, Site-Scope und Operationsrollen begrenzen | negative Autorisierung und Fake-Graph-Smokes beweisen keine breiten Rechte oder Viewer-Kopplung |
| S5 Migration | in Umsetzung in #618; ausschließlich offline | Inventory-Dry-Run, idempotenten Backfill, persistente Quarantäne, Registry-/Prozess-Snapshots, stabile Endscans und N-1-Replay implementieren | alle sieben Klassen, ETag-Konflikte, Rollback-Reihenfolge und Forward-Recovery bestehen |
| S6 Immutable Evidence | offen | durable Outbox, Broker/WORM-Events, Correlation, pseudonyme ActorRef, Retention, Access-Review und Reconciliation implementieren | ohne vollständigen Intent-/Ergebnis-/Readback-Nachweis bleibt jede Live-Mutation blockiert |
| S7 Live-Freigabe | offen | separaten owner-gated Schema-/Backfill-Apply mit Funktionstrennung und Cleanup-Verbot vorbereiten | vollständige PR-Diff, N-/N-1-Rollback-Probe, negative Autorisierung und explizite duale Freigabe |

## Akzeptanzkriterien Und Verifikation

- `AC-610-01`: Die drei Projektionen verwenden exakt denselben stabilen
  Identifier, soweit sie existieren; Typgültigkeit bleibt viewer-unabhängig.
- `AC-610-02`: Alias-, Retired-, Drift-, Duplikat- und Cache-Fehler blockieren
  fail-closed.
- `AC-610-03`: Dual-Read/-Write, Backfill, Cutover und Rollback sind begrenzt,
  ETag-gesichert, durch stabile Endscans belegt und ohne in-place
  Choice-Konvertierung.
- `AC-610-04`: Runtime, Provisioning und Audit sind nach Least Privilege und
  Funktionstrennung begrenzt; negative Autorisierungstests sind Pflicht.
- `AC-610-05`: S1 bis S7 benennen Code-, Schema-, MCP- und Evidence-Arbeit vor
  jedem Live-Apply.
- `AC-610-06`: Deutsche und englische ADR sowie interne Links sind valide.
- `AC-610-07`: `AuditJournalLite` ist keine revisionssichere Quelle; ohne
  immutable Outbox/Event-Stream und persistente Quarantäne bleibt Live-Mutation
  verboten.
- `AC-610-08`: Snapshots binden `Vorgangsartenregister`, `Prozessregister` und
  ETags; N-1-Rollback und Forward-Recovery sind vor Cutover getestet.
- `AC-610-09`: `ActorRef` wird als personenbezogen behandelt, pseudonymisiert,
  zweckgebunden aufgelöst und mindestens zehn Jahre geschützt aufbewahrt.

Für die offline implementierten S1-/S2-Artefakte gelten:

```bash
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
```

Spätere Implementierungs-PRs müssen zusätzlich die betroffenen
Vertragsvalidatoren und den
[strikten Quality Gate](../quality-gate.md) erfolgreich ausführen.

## S4 Graph Read Edge (#616)

Der aktive S4-Read-Edge bindet Graph REST v1.0 `GET` unveränderlich an Site, `Vorgangsartenregister`, Operation und Rolle. Zulässig sind ausschließlich `Sites.Selected` und ein vorhandener Site-Grant `read`; Paging muss `BusinessCaseTypeId`- und `CatalogVersion`-Filter beibehalten. Row-ETags werden erst nach vollständigem Read lokal verglichen und nie als Collection-`If-None-Match` gesendet. Ergebnisse bleiben redigiert und viewer-isoliert. Die Bedienkante ist `nac m365 teams-sharepoint business-case-type-read-plan`; sie ist offline und lädt weder Credentials noch HTTP/DNS/Graph-Clients. S4b-Writes bleiben offen.

Traceability: **AC-S4-01:** exakter GET/Projection-Pfad; **AC-S4-02:** vollständiges Same-Filter-Paging; **AC-S4-03:** lokale ETag-Auswertung; **AC-S4-04:** exakte Permission/Grant-Bindung; **AC-S4-05:** strikte Typisierung und Viewer-Isolation; **AC-S4-06:** Redaction; **AC-S4-07:** CLI, Contracts, Validator, Tests, Dokumentation und Gates.

## S5 Offline-Migration (#618)

Der aktive S5-Slice implementiert ausschließlich offline die sieben disjunkten Inventarklassen, das exakt vierzeilige typisierte Legacy-Mapping, kanonisch gebundene Seiten und Snapshots, einen idempotenten `VorgangstypId`-Plan mit ETag, prozessserialisierte persistente lokale Quarantäne, zwei unabhängig erfasste stabile Endscans sowie hash-gepinnte N-/N-1-Profil-Evaluation. Separate Post-Scan-Snapshots werden erst nach Scan zwei akzeptiert und vollständig an das Manifest gebunden. `READY` bedeutet nur `S5_OFFLINE_ONLY`; Live-Cutover bleibt `BLOCKED_PENDING_S6_S7_APPROVAL`. Der Befehl `nac kg business-case-type-migration-dry-run` liest nur synthetische Fixtures; Live-Aufrufe und Tenant-Writes bleiben null.

Traceability: **AC-S5-01** bis **AC-S5-07**, Domain-/Verification-Contract, Standalone-Validator, zentrale Offline-CLI, synthetische Fixtures und Strict-Gate.
