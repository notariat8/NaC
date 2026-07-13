# BusinessCaseType Graph Read Edge S4 Design

Status: Runtime offline implementiert in PR #617; Governance-Synchronisierung im S5-PR bis zu grüner Remote-CI offen; S4b-Writes bleiben offen
Datum: 11. Juli 2026
Scope: offline geplante Microsoft-Graph-v1.0-Lesekante zwischen `nac_m365_graph` und dem bestehenden `notary_kg`-Domain-Port

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-graph-read-edge-s4
leading_issue: https://github.com/notariat8/NaC/issues/616
risk_gate: External Service
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-07-11-business-case-type-graph-read-edge-s4.md
acceptance_ids:
  - AC-S4-01
  - AC-S4-02
  - AC-S4-03
  - AC-S4-04
  - AC-S4-05
  - AC-S4-06
  - AC-S4-07
validation_commands:
  - python3 -m unittest tests.test_business_case_type_graph_read_edge tests.test_business_case_type_graph_read_edge_cli tests.test_business_case_type_graph_read_edge_contract
  - python3 scripts/validate_business_case_type_graph_read_edge.py
  - python3 scripts/nac.py m365 teams-sharepoint business-case-type-read-plan --help
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Zweck und Schichtgrenze

S4 ergänzt den in S3 implementierten, viewer-unabhängigen
`BusinessCaseTypeRegistryReadPort` um genau einen Adapter unter
`src/nac_m365_graph`. Der Adapter reduziert Microsoft-Graph-Antworten auf
`BusinessCaseTypeRegistryRow` und liefert ausschließlich
`RegistryFetchResult` an `notary_kg`. Die fachliche Gültigkeitsentscheidung,
der Registry-Cache und seine Zustandsmaschine bleiben Eigentum von S3 und
werden durch diesen Slice nicht geändert.

Der Slice ist GET-only und offline geplant. Er führt keine Live-Anfrage aus,
lädt keine Credentials und verändert weder Entra noch SharePoint. S4b-Writes
für `case_create`, Korrektur und Backfill sind ein separater Folgescope.

## Gebundener Request

Eine Adapterinstanz wird unveränderlich an folgende Werte gebunden:

- Graph-Basis `https://graph.microsoft.com/v1.0`,
- genau eine genehmigte `site_id`,
- genau eine genehmigte `list_id` für `Vorgangsartenregister`,
- genau eine Operation aus `case_create_validation`,
  `matter_type_correction_validation`, `backfill_validation` oder
  `optional_process_read`,
- eine für diese Operation zugelassene Rolle,
- Application Permission exakt `Sites.Selected` und einen bestehenden
  Site-Grant mit Leserecht.

Site, Liste, Operation, Rolle und Permission werden vor Aufbau oder Übergabe
eines HTTP-Requests geprüft. Ein Mismatch endet fail-closed ohne Transport.
`Sites.Read.All`, `Sites.ReadWrite.All`, `Sites.Manage.All`,
`Files.Read.All`, Delegated Permissions sowie Schema- oder
Provisioning-Rechte sind für diese Kante unzulässig.

## Graph-Request und Datenminimierung

Der Adapter darf nur `GET` auf der gebundenen Collection
`/sites/{site-id}/lists/{list-id}/items` unter Graph REST v1.0 planen. Der
initiale Request filtert auf die exakte `BusinessCaseTypeId` und `CatalogVersion` und selektiert
auf Item-Ebene exakt `id` und `eTag`. Aus `fields` werden exakt
`BusinessCaseTypeId`, `LifecycleStatus`, `Selectable` und `CatalogVersion`
expandiert. Andere Properties werden weder in Domain-Objekte übernommen noch
persistiert oder als Evidence ausgegeben.

Viewer-, Prozess-, Akten-, Dokument- und Personenfelder beeinflussen die
Typgültigkeit nicht. `optional_process_read` ist nur eine gebundene
Operationsberechtigung für einen späteren, getrennten Prozessread; sie
erweitert diesen Registry-Request nicht um Prozess- oder Viewer-Felder.

## Vollständiges Paging

Ein Ergebnis ist nur mit einem validierten Collection-Ende vollständig. Jeder
`@odata.nextLink` wird vor dem Folge-GET kanonisch geparst und muss weiterhin

1. HTTPS und Host `graph.microsoft.com`,
2. die Basis `/v1.0`,
3. dieselbe gebundene Site und Liste,
4. dieselbe Items-Collection und dieselbe Feldprojektion,
5. denselben exakten `BusinessCaseTypeId`- und `CatalogVersion`-Filter

adressieren. Redirects, relative oder benutzerkontrollierte Hosts,
Graph-Beta, abweichende Sites/Listen und veränderte Projektionen sind
unzulässig. Besuchte kanonische NextLinks werden erkannt. Eine Schleife, ein
ungültiger Payload sowie die Überschreitung des festen Page- oder Item-Limits
liefern kein partielles `OK`, sondern ein redigiertes `UNAVAILABLE` mit
`pages_complete=false`. Jede einzelne HTTP-Antwort wird vor dem JSON-Parsing auf maximal 1 MiB begrenzt; eine Überschreitung scheitert ebenfalls fail-closed.

## ETag-Semantik

Der Adapter liest die gefilterte Collection immer vollständig. Erst nach dem
validierten Ende darf er bei genau einer vollständig typisierten, exakt
passenden Zeile deren `eTag` lokal mit dem von S3 übergebenen positiven ETag
vergleichen. Identität ergibt `RegistryFetchResult.NOT_MODIFIED`; ein
abweichender ETag liefert die neue Zeile als vollständiges `OK`.

Ein Row-ETag wird niemals als Collection-Header `If-None-Match` gesendet.
Damit gibt es in S4 weder eine allgemeine HTTP-304-Erweiterung noch ein
vermeintliches Collection-Not-Modified ohne stabilen Item-Endpunkt. Null,
mehrere oder unvollständige Zeilen können niemals `NOT_MODIFIED` ergeben.

## Redigierte Fehler und Evidence

Die Graph-Kante gibt nur die bereits vom Domain-Port erlaubten festen Codes
aus: `transport_authentication_failed`, `transport_authorization_failed`,
`transport_rate_limited`, `transport_timeout` und `transport_unavailable`.
Unbekannte HTTP-Statuswerte, ungültige Payloads, Paging-Verstöße, Schleifen
und Grenzüberschreitungen werden auf `transport_unavailable` reduziert.
`fixture_transport_unavailable` bleibt ausschließlich dem S3-Fixture-Pfad
vorbehalten.

Exceptions, Ergebnisse, Logs und Evidence enthalten weder Token noch
konkreten Graph-Pfad, Site-/List-/Item-ID, Graph-Body, Mandatswert oder
Credential-Metadaten. Zulässig sind nur feste Reason-Codes, Zähler innerhalb
der Limits, boolesche Gate-Ergebnisse, Contract-Version und redigierte
Korrelationsreferenzen.

## Offline-CLI

Die zentrale `nac`-CLI erhält in diesem Implementierungsslice den Befehl
`nac m365 teams-sharepoint business-case-type-read-plan`. Er erzeugt ausschließlich einen
redigierten Offline-Plan mit Methode, Graph-Version, logischer
Resource-Bindung, ausgewählten Feldnamen, Limits und Gate-Ergebnissen. Der
Befehl akzeptiert oder liest keine Tokens, Zertifikate oder Secret-Dateien,
instanziiert keinen Live-Graph-Client und führt weder HTTP noch DNS aus.

## Akzeptanzkriterien

- **AC-S4-01:** Der Adapter erzeugt nur Graph REST v1.0 GETs für die gebundene Site/Liste und selektiert exakt id, eTag sowie BusinessCaseTypeId, LifecycleStatus, Selectable und CatalogVersion.
- **AC-S4-02:** Paging gilt nur nach validiertem Ende als vollständig; fremde Hosts/Basen/Sites/Listen, Schleifen, ungültige Payloads und Page-/Item-Limit-Überschreitung liefern nie einen gültigen Typ.
- **AC-S4-03:** Nach vollständigem Read wird ein identischer Zeilen-ETag lokal auf NOT_MODIFIED abgebildet; abweichende ETags liefern die neue Zeile. Ein Zeilen-ETag wird nie als Collection-If-None-Match missbraucht.
- **AC-S4-04:** Falsche Site, Liste, Operation, Rolle oder Runtime-Permission werden vor dem Transport blockiert; der Vertrag erlaubt nur Sites.Selected und keine Schema-/Provisioning-Rechte.
- **AC-S4-05:** Graph-Antworten werden streng typisiert und auf die Registry-Felder reduziert; Viewer-, Prozess-, Akten-, Dokument- und Personenfelder beeinflussen die Typgültigkeit nicht.
- **AC-S4-06:** HTTP-/Transportfehler werden auf feste redigierte Reason-Codes abgebildet; Tokens, Pfade, IDs, Graph-Body und Mandatswerte erscheinen weder in Resultaten noch Exceptions/Evidence.
- **AC-S4-07:** Zentrale CLI, Domain-/Verification-Contract, Standalone-Validator, Fake-Graph-Tests, DE/EN-Doku, Strict-Gate und unabhängiger base...head-Review bestehen.

## Nichtziele

- keine Änderung der S3-Runtime, ihrer Domain-Entscheidungen oder Caches,
- keine Live-Graph-, Tenant-, Credential- oder Entra-Aktion,
- keine Graph-, SharePoint-, MCP-, Schema- oder Provisioning-Writes,
- kein S4b-Write-Plan und keine Ausführung von `case_create`, Korrektur oder Backfill,
- kein SharePoint REST, PnP, Graph SDK oder Graph Beta,
- keine Prozessregister-, BPMN- oder Viewer-Abhängigkeit für Typgültigkeit.
