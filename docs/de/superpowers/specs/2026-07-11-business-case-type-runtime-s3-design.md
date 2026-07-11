# BusinessCaseType Runtime S3 Design

Status: in Umsetzung; Abschluss nur nach erfolgreicher Code- und Vertragsvalidierung
Datum: 11. Juli 2026
Scope: deterministische, viewer-unabhängige Offline-Runtime für `BusinessCaseTypeId`

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-runtime-s3
leading_issue: https://github.com/notariat8/NaC/issues/612
risk_gate: Privacy
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-07-11-business-case-type-runtime-s3.md
acceptance_ids:
  - AC-S3-01
  - AC-S3-02
  - AC-S3-03
  - AC-S3-04
  - AC-S3-05
  - AC-S3-06
validation_commands:
  - python3 -m unittest tests.test_business_case_type_runtime tests.test_business_case_type_cache tests.test_business_case_type_cli tests.test_business_case_type_id_contract tests.test_business_case_type_id_cli tests.test_business_case_type_id_schema_plan tests.test_notary_kg
  - python3 scripts/validate_business_case_type_runtime.py
  - python3 scripts/validate_notarial_business_case_inventory.py
  - python3 scripts/validate_notarial_process_ontology_contract.py
  - python3 scripts/nac.py kg business-case-type-get --help
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/validate_gantt_progress.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Zweck

S3 soll die fachliche Lesekante `business_case_type_get` vollständig
offline implementieren. Die Runtime entscheidet deterministisch, ob eine exakte
`BusinessCaseTypeId` für eine kanonische Zuordnung zulässig ist oder ob ein
direkter Legacy-Alias ausschließlich für einen begrenzten Lese- oder
Migrationszweck aufgelöst werden darf. Microsoft Graph, Authentisierung,
Credentials und Tenant-Zugriffe gehören erst zu S4.

## Autoritativer Katalog-Snapshot

Die Runtime lädt einen unveränderlichen, repo-versionierten Snapshot. Er
enthält kanonische IDs, direkte Aliase, `LifecycleStatus`, `Selectable`,
Vertragsversion und einen `catalog_version`-Wert. `catalog_version` ist der
SHA-256 über die kanonisch serialisierten IDs, Aliasregeln und
Runtime-Lifecycle-Felder. Die Schema-Version des Inventars und Zeitstempel sind
keine Katalogversion.

Der Runtime-Lifecycle ist eigenständig. Ein Planungswert wie
`source_status="open"` darf weder stillschweigend `LifecycleStatus="active"`
noch `Selectable=true` erzeugen. Nicht explizit freigegebene Einträge sind für
neue Akten nicht auswählbar.

Beim Laden werden exakte Syntax, Länge, Eindeutigkeit, direkte Aliasziele sowie
Kollisionen, Ketten, Zyklen, Selbstziele und unbekannte Ziele fail-closed
geprüft. Eingaben werden nicht getrimmt, kleingeschrieben, Unicode-normalisiert
oder URL-dekodiert.

## Lookup-Zwecke Und Ergebnisse

Die API unterscheidet mindestens:

- `canonical_assignment`: nur eine exakte kanonische, aktive und auswählbare
  ID ist zulässig; Aliase sind ungültig.
- `legacy_read`: genau ein direkter Alias darf aufgelöst werden; das Ergebnis
  ist nicht auswählbar und auditpflichtig.
- `migration`: genau ein direkter Alias darf als expliziter
  Migrationsnachweis aufgelöst werden und bleibt auditpflichtig.

Ergebnisse verwenden die disjunkten Zustände `VALID`, `INVALID` und
`VALIDATION_UNAVAILABLE` mit strukturierten Reason-Codes. Rohantworten des
Transports werden nicht ausgegeben oder gespeichert.

## Registry-Validierung

Der read-only Port liefert alle Seiten eines exakten ID-Lookups. Erst danach
prüft die Runtime:

1. insgesamt genau eine Zeile,
2. exakte `BusinessCaseTypeId`,
3. exakte `CatalogVersion`,
4. `LifecycleStatus == "active"`,
5. `Selectable is True` als boolescher Wert,
6. einen nichtleeren Zeilen-ETag,
7. ausschließlich ausgewählte Registry-Metadaten.

Null oder mehrere Zeilen, Pagingfehler, fehlende oder falsch typisierte
Felder, Versionsdrift und unbekannte Statuswerte liefern niemals `VALID`.

## Cache-Zustandsmaschine

Der Registry-Cache verwendet den Schlüssel
`(site_id, BusinessCaseTypeId, CatalogVersion)`, eine injizierbare monotone Uhr,
begrenzte Größe, Thread-Schutz und Single-Flight-Revalidierung.

- Unter 300 Sekunden ist ein positiver Eintrag `FRESH`.
- Ab 300 Sekunden ist synchrone Revalidierung erforderlich. Eine Mutation
  bleibt bei Timeout oder Transportfehler blockiert.
- Bis unter 900 Sekunden darf eine read-only Anzeige alte Metadaten nur als
  `VALIDATION_UNAVAILABLE` kennzeichnen; sie darf daraus kein `VALID` ableiten.
- Ab 900 Sekunden ist der Eintrag `HARD_EXPIRED` und unbrauchbar.
- Deterministisch negative Ergebnisse werden höchstens 30 Sekunden gehalten.
  Timeout, Authentisierungs-, Transport- und 5xx-Fehler werden nicht negativ
  gecacht.
- `304 Not Modified` ist nur mit passendem vorherigem positiven ETag zulässig.
- Katalogversions- oder unerwarteter ETag-Wechsel invalidiert atomar die
  Registry-Partition der Site und erhöht ihre Generation. Veraltete laufende
  Requests dürfen danach keinen Cacheeintrag mehr schreiben.

Der Cache enthält nur ID, Lifecycle, `Selectable`, `CatalogVersion`, ETag und
Zeitwerte, niemals Akten-, Personen-, Dokument- oder Graph-Rohdaten.

## Viewer-Isolation

Registry- und Viewer-Metadaten verwenden getrennte Klassen, Eintragstypen,
Speicherbereiche, Locks, Generationen, Transport-Ports und
Invalidierungsfunktionen. `business_case_type_get` für Typgültigkeit importiert
oder liest keinen Viewer-Port. Ausfall, Duplikate oder Drift in
`Prozessregister` oder BPMN-Metadaten ändern die Typgültigkeit nicht.

## Offline-Grenze

S3 bietet ausschließlich Fake-/Fixture-Transporte. Es gibt keine Option für
Tenant, Token, Zertifikat, Microsoft Graph oder Live-HTTP. Der produktive
Graph-REST-v1.0-Adapter, Response-Header/ETag und Paging gehören zu S4.
## Akzeptanzkriterien

- **AC-S3-01:** Kanonische IDs und direkte bekannte Aliase werden
  deterministisch aufgelöst; unbekannte IDs, Schreibvarianten, Alias-Ketten,
  Zyklen und retired/nonselectable Einträge blockieren fail-closed.
- **AC-S3-02:** Genau eine Registry-Zeile mit passender ID und
  `CatalogVersion` ist erforderlich; null, Duplikat, Timeout und Versionsdrift
  liefern keinen gültigen Typ.
- **AC-S3-03:** Der Registry-Cache erzwingt Revalidation, Hard-Expiry, negative
  TTL und site-weite Invalidierung bei ETag- oder Versionsdrift.
- **AC-S3-04:** Der Viewer-Cache ist technisch und semantisch getrennt und wird
  niemals für Typgültigkeit gelesen.
- **AC-S3-05:** ETag-/Not-Modified-Verhalten ist deterministisch getestet; der
  Cache enthält keine Akten-, Dokument- oder Personendaten.
- **AC-S3-06:** CLI, Standalone-Validator, DE/EN-Dokumentation, Strict-Gate und
  unabhängiger Review bestehen ohne Graph-, Credential- oder Tenant-Zugriff.

## Nichtziele

- kein Microsoft-Graph-Adapter oder MCP-Server,
- keine SharePoint- oder Entra-Live-Aktion,
- keine Aktenanlage, Korrektur oder Migration,
- kein persistenter Cache,
- keine Viewer-, BPMN- oder Prozessregister-Abhängigkeit für Typgültigkeit.
