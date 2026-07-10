# ADR: Stabile BusinessCaseTypeId

Status: Vorschlag zur Review, offline, kein Live-Apply
Issue: [GitHub #605](https://github.com/notariat8/NaC/issues/605)
Datum: 2026-07-10

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
auf eine Identität zusammen. Sie ändert in diesem Issue weder Code noch
Verträge, Schema, Tenant oder Policies.

## Entscheidung

`BusinessCaseTypeId` ist der kanonische, unveränderliche Text-Identifier einer
notariellen Vorgangsart. Für jede kanonische Vorgangsart gilt exakt:

```text
BusinessCaseTypeId == Prozessregister.ProcessKey == Akten.VorgangstypId
```

- Der Wert ist der freigegebene kanonische Usecase-Slug in Kleinschreibung und
  Kebab-Case (`^[a-z0-9]+(?:-[a-z0-9]+)*$`, maximal 128 Zeichen).
- Vergleich und Speicherung erfolgen exakt. Runtime-Eingaben mit abweichender
  Großschreibung, Leerraum oder stiller Normalisierung werden abgelehnt.
- Ein veröffentlichter Identifier wird weder umbenannt noch erneut vergeben.
  Fachliche Nachfolger erhalten einen neuen Identifier; der alte Eintrag wird
  als nicht auswählbar oder stillgelegt markiert.
- `Prozessregister.ProcessKey` ist indexiert und eindeutig. Es gibt genau eine
  aktuelle Registerzeile pro `BusinessCaseTypeId`. `NacProcessId` bleibt die
  technische Zeilenidentität und ist kein zweiter fachlicher Schlüssel.
- BPMN-Versionen und Modell-Pointer referenzieren den `ProcessKey`; sie erzeugen
  keine weiteren Business-Case-Identitäten.
- `Akten.VorgangstypId` wird als neue indexierte einzeilige Textspalte geplant.
  `Akten.Vorgangstyp` wird nicht in-place von Choice zu Text konvertiert.

Damit ist der Ontologiebegriff `BusinessCaseType` die fachliche Klasse, der
repo-versionierte Katalog ihre führende Definition und `Prozessregister` nur
die freigegebene Runtime-Projektion. Es wird keine zweite
`BusinessCaseType`-Choice-Spalte eingeführt.

## Kanonische Und Alias-Regeln

Ein Identifier ist zur Runtime nur gültig, wenn der durch Review freigegebene
Repo-Katalog ihn als kanonisch und nicht stillgelegt führt. Sobald
`Prozessregister` produktiv aktiviert ist, muss zusätzlich genau eine Zeile mit
demselben `ProcessKey` und `ProcessStatus=Approved` existieren. Fehlende,
doppelte, `Draft`-, `ReviewRequired`- oder `Retired`-Zeilen blockieren die
Auswahl und Prozesszuordnung.

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

Vor `case_create`, einer Korrektur der Vorgangsart oder Prozess-Routing prüft
die Runtime in dieser Reihenfolge:

1. Syntax und exakte Schreibweise der `BusinessCaseTypeId`.
2. Kanonischer, nicht stillgelegter und für Neuanlage freigegebener Eintrag im
   repo-versionierten Katalog.
3. Nach Aktivierung der Registerprojektion: genau eine freigegebene
   `Prozessregister`-Zeile mit identischem `ProcessKey` und passender
   `CatalogVersion`.
4. Bei einer bestehenden Akte: kein Widerspruch zwischen `VorgangstypId` und
   einem noch gelesenen Legacy-Choice.

Jeder Fehler, Timeout, unbekannte Status, Katalog-/Register-Versionsdrift,
Duplikat oder abgelaufene Cache-Eintrag blockiert Mutation und Routing. Eine
read-only Anzeige darf `validation_unavailable` melden, aber den Wert nicht als
gültig behandeln.

Der Runtime-Cache enthält nur `BusinessCaseTypeId`, Status, `CatalogVersion`,
Zeilen-ETag und Zeitstempel, niemals Akten- oder Dokumentdaten. Schlüssel ist
`(siteId, BusinessCaseTypeId, CatalogVersion)`. Nach fünf Minuten wird
revalidiert; nach spätestens 15 Minuten ohne erfolgreiche Revalidierung ist der
Eintrag unbrauchbar. Graph-ETags werden für bedingte Reads genutzt, soweit der
Endpunkt sie unterstützt; andernfalls werden die zurückgegebenen Zeilen-ETags
verglichen. Ein Versionswechsel oder ETag-Konflikt invalidiert den betroffenen
Site-Cache vollständig. Negative Ergebnisse werden höchstens 30 Sekunden
gehalten.

## Übergang Vom Legacy-Choice

Die Migration ist als explizite Zustandsfolge umzusetzen:

| Phase | Leseverhalten | Schreibverhalten | Exit-Kriterium |
| --- | --- | --- | --- |
| `inventory` | Legacy unverändert | keine Writes | redigierter Bestandsscan und eindeutige Mapping-Tabelle |
| `column_ready` | Legacy führend | `VorgangstypId` optional, keine Live-Automatik | owner-gated Schema-Readback bestätigt indexierten Text |
| `dual` | neue ID zuerst, Legacy-Fallback | neue ID immer; Legacy nur bei eindeutigem Altwert | Backfill vollständig, null Konflikte |
| `canonical` | nur `VorgangstypId` | nur `VorgangstypId` | mindestens ein Release ohne Legacy-Fallback |
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

## Backfill Und Rollback

Der spätere Backfill beginnt mit einem read-only Dry-Run. Er klassifiziert jede
Akte als `already_canonical`, `mappable`, `conflict`, `unknown` oder `missing`
und veröffentlicht nur redigierte Counts und Hashes. Der owner-gated Write-Lauf
arbeitet paginiert und idempotent, schreibt ausschließlich
`VorgangstypId`, verwendet das aktuelle Item-ETag mit `If-Match` und überspringt
konkurrierend geänderte Items. Unbekannte oder widersprüchliche Werte werden
nicht geraten, sondern in eine manuelle Klärungsqueue gestellt. Cutover ist nur
bei 100 Prozent klassifizierten Akten, null offenen Konflikten, vollständigem
Readback und abgelegtem Audit-Nachweis zulässig.

Rollback löscht weder Spalten noch Werte. Vor dem kanonischen Cutover kann die
Runtime auf Legacy-Read zurückgestellt werden, weil der Dual-Write die
abbildbaren Choice-Werte erhalten hat. Nach Aufnahme einer Vorgangsart ohne
Legacy-Choice blockiert ein Rollback deren Writes und Routing; er darf keinen
Ersatzwert erfinden. Runtime-Version, Migrationsmanifest, Katalogversion und
Cache werden gemeinsam auf den letzten geprüften Stand zurückgesetzt. Eine
spätere Spaltenbereinigung ist ein eigenes Owner-Gate.

## Berechtigungen, Audit Und Evidence

- Runtime-Reads und Akten-Metadatenzugriffe verwenden die bestehende, pro Site
  begrenzte `Sites.Selected`-Runtime-App. Sie erhalten keine
  Schema-Administrationsrechte.
- `Sites.Manage.All` bleibt ausschließlich beim kontrollierten, owner-gated
  Provisioning-Pfad. Microsoft dokumentiert es als kleinstes Recht für das
  [Ändern einer Spaltendefinition](https://learn.microsoft.com/en-us/graph/api/columndefinition-update?view=graph-rest-1.0).
- Runtime und Backfill lesen nur ausgewählte Metadatenfelder über Microsoft
  Graph REST v1.0. Keine SharePoint-Dateiinhalte, Graph-Rohantworten, Tokens
  oder Mandats-Payloads werden persistiert.
- Jede Validierungsablehnung, Alias-Übersetzung, Korrektur, Backfill-Schreibung,
  ETag-Kollision und jeder Cutover erzeugt eine Correlation-ID und einen
  redigierten `AuditJournalLite`-Nachweis mit Actor-/Tool-ID, Zeit, Aktion,
  Ergebniscode, `BusinessCaseTypeId`, Katalogversion und Register-ETag.
- Ist der Audit-Pfad vor einer Mutation nicht bereit, wird nicht geschrieben.
  Scheitert der Audit-Append nach einem SharePoint-Write, wird der Vorgang als
  `reconciliation_required` gesperrt und vor weiterer Verarbeitung read-back
  geprüft.

Die Nachweise folgen der
[Revisionssicherheits-Policy](../../../policies/revisionssicherheit-eventstream-policy.yaml)
und enthalten keine Personen-, Aktenzeichen- oder Dokumentinhalte.

## Explizite Umsetzungsslices

Diese ADR genehmigt keinen Slice; jeder Slice braucht Review und passende
Tests, bevor ein Live-Apply erwogen wird.

| Slice | Erforderliche Änderung | Abnahmekante |
| --- | --- | --- |
| S1 Vertrag | Ontologie-, Inventory- und Viewer-Verträge auf `BusinessCaseTypeId`, `ProcessKey`, Lifecycle, `CatalogVersion` und Alias-Invarianten ausrichten | Validatoren lehnen Alias, Duplikat, Retired und Vertragsdrift offline ab |
| S2 Schema-Plan | `Akten.VorgangstypId` als indexierten Text planen; `Prozessregister.ProcessKey` eindeutig machen; Legacy-Choice unverändert lassen | Dry-Run, Readiness und Rollback-Plan; weiterhin kein Live-Apply |
| S3 Runtime | kanonische Validierung, Registerabgleich, ETag-/Versionscache und fail-closed Reason-Codes implementieren | Unit- und Negativtests für Timeout, Drift, Duplikat, Alias und Cache-Ablauf |
| S4 MCP/Graph | `case_create`, Korrektur-/Backfill-Pfad und `process_register_list` auf ausgewählte Felder, Paging, ETag und Site-Scope begrenzen | Fake-Graph-Smokes beweisen keine Datei-Reads, keine Rohantworten und keine breiten Rechte |
| S5 Migration | redigierten Inventory-Dry-Run, idempotenten Backfill, Konfliktqueue, Readback und Cutover-Gate implementieren | synthetische Fixtures für alle fünf Klassen und ETag-Konflikte |
| S6 Audit/Evidence | Correlation, `AuditJournalLite`, redigierte Artefakte, Retention und Reconciliation ergänzen | Evidence-Validator prüft Counts, Hashes, Privacy-Flags und vollständigen Readback |
| S7 Live-Freigabe | separaten owner-gated Schema-/Backfill-Apply mit Least Privilege und Cleanup-Verbot vorbereiten | vollständige PR-Diff, Rollback-Probe und explizite Owner-Freigabe |

## Akzeptanzkriterien Und Verifikation

- `AC-605-01`: Die drei Projektionen verwenden exakt denselben stabilen
  Identifier; `ProcessKey` ist eindeutig.
- `AC-605-02`: Alias-, Retired-, Drift-, Duplikat- und Cache-Fehler blockieren
  fail-closed.
- `AC-605-03`: Dual-Read/-Write, Backfill, Cutover und Rollback sind begrenzt,
  ETag-gesichert und ohne in-place Choice-Konvertierung.
- `AC-605-04`: Runtime, Provisioning und Audit sind nach Least Privilege und
  Datenminimierung getrennt.
- `AC-605-05`: S1 bis S7 benennen Code-, Schema-, MCP- und Evidence-Arbeit vor
  jedem Live-Apply.
- `AC-605-06`: Deutsche und englische ADR sowie interne Links sind valide.

Für diesen reinen Dokumentationsvorschlag gelten:

```bash
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
```

Spätere Implementierungs-PRs müssen zusätzlich die betroffenen
Vertragsvalidatoren und den
[strikten Quality Gate](../quality-gate.md) erfolgreich ausführen.
