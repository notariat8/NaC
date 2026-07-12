# BusinessCaseType Graph Read Edge S4 Implementierungsplan

**Status:** Runtime offline implementiert in PR #617; WP9 im synchronisierenden S5-PR bis zu grüner Remote-CI offen; S4b-Writes bleiben offen

**Spec:** [BusinessCaseType Graph Read Edge S4 Design](../specs/2026-07-11-business-case-type-graph-read-edge-s4-design.md)
**Leading Issue:** [GitHub #616](https://github.com/notariat8/NaC/issues/616)
**Delivery Mode:** Protected PR
**Risk Gate:** External Service; im S4-Slice geschlossen, `allowed_live_graph_calls=0`

## Ziel

Den GET-only Graph-v1.0-Adapter von `nac_m365_graph` zum bestehenden
`notary_kg`-Domain-Port in diesem Implementierungsslice bauen. Runtime, Request-Bindung, Paging, lokale ETag-Semantik, Redaction,
Offline-CLI und Nachweise sind im Branch umgesetzt. S3 bleibt unverändert,
S4b-Writes bleiben außerhalb des Scopes; WP9 wird erst nach Merge des synchronisierenden S5-PR mit grüner Remote-CI abgeschlossen.

## Acceptance-Mapping zu Issue #616

- **AC-S4-01:** Der Adapter erzeugt nur Graph REST v1.0 GETs für die gebundene Site/Liste und selektiert exakt id, eTag sowie BusinessCaseTypeId, LifecycleStatus, Selectable und CatalogVersion.
- **AC-S4-02:** Paging gilt nur nach validiertem Ende als vollständig; fremde Hosts/Basen/Sites/Listen, Schleifen, ungültige Payloads und Page-/Item-Limit-Überschreitung liefern nie einen gültigen Typ.
- **AC-S4-03:** Nach vollständigem Read wird ein identischer Zeilen-ETag lokal auf NOT_MODIFIED abgebildet; abweichende ETags liefern die neue Zeile. Ein Zeilen-ETag wird nie als Collection-If-None-Match missbraucht.
- **AC-S4-04:** Falsche Site, Liste, Operation, Rolle oder Runtime-Permission werden vor dem Transport blockiert; der Vertrag erlaubt nur Sites.Selected und keine Schema-/Provisioning-Rechte.
- **AC-S4-05:** Graph-Antworten werden streng typisiert und auf die Registry-Felder reduziert; Viewer-, Prozess-, Akten-, Dokument- und Personenfelder beeinflussen die Typgültigkeit nicht.
- **AC-S4-06:** HTTP-/Transportfehler werden auf feste redigierte Reason-Codes abgebildet; Tokens, Pfade, IDs, Graph-Body und Mandatswerte erscheinen weder in Resultaten noch Exceptions/Evidence.
- **AC-S4-07:** Zentrale CLI, Domain-/Verification-Contract, Standalone-Validator, Fake-Graph-Tests, DE/EN-Doku, Strict-Gate und unabhängiger base...head-Review bestehen.

## Arbeitspakete für diesen Implementierungsslice

- [x] **WP1 – Adaptergrenze:** einen Adapter ausschließlich unter
  `src/nac_m365_graph` implementieren, der den unveränderten
  `BusinessCaseTypeRegistryReadPort` aus `notary_kg` erfüllt und nur
  `RegistryFetchResult` zurückgibt.
- [x] **WP2 – Scope-Gate:** unveränderliche Site-/List-Bindung,
  Operations-/Rollenmatrix, `Sites.Selected` und vorhandenen Site-Read-Grant
  vor jedem Transport prüfen; alle breiteren oder provisioningnahen Rechte
  blockieren.
- [x] **WP3 – Request-Plan:** ausschließlich Graph REST v1.0 `GET` für die
  gebundene Items-Collection mit exaktem Filter und exakt sechs ausgewählten
  Item-/Registry-Feldern erzeugen.
- [x] **WP4 – Paging:** NextLinks strukturiert auf HTTPS, Host, v1.0-Basis,
  Site, Liste, Collection, Projektion sowie identische BusinessCaseTypeId- und CatalogVersion-Filter prüfen; vollständiges Ende,
  Loop-Erkennung sowie feste Page-/Item-Limits fail-closed erzwingen.
- [x] **WP5 – Parsing und ETag:** jede Seite streng typisieren, fremde Felder
  verwerfen und erst nach vollständigem Collection-Read genau eine passende
  Zeile lokal auf ETag-Gleichheit prüfen; keinen Collection-Header
  `If-None-Match` setzen.
- [x] **WP6 – Redaction:** HTTP-/Transportfehler auf die feste
  Domain-Allowlist reduzieren und sicherstellen, dass Resultate, Exceptions,
  Logs und Evidence keine Tokens, Pfade, IDs, Bodies oder Mandatswerte tragen.
- [x] **WP7 – Offline-CLI:** den zentralen Befehl
  `nac m365 teams-sharepoint business-case-type-read-plan` als redigierten Planer ohne
  Credentials, HTTP, DNS oder Live-Client implementieren.
- [x] **WP8 – Verification:** Domain-/Verification-Contract und
  Standalone-Validator integrieren; Fake-Graph-Tests für alle positiven und
  negativen Paging-, Scope-, Typisierungs-, Redaction- und ETag-Grenzen
  ergänzen.
- [ ] **WP9 – Abschluss:** DE/EN-Dokumentation und Agent-Context im dann
  freigegebenen Scope synchronisieren, Strict-Gate ausführen, vollständige
  `base...head`-Diff unabhängig reviewen, Findings beheben und Protected PR
  mit grünen Remote-Checks bereitstellen.

## Verbindliche Negativfälle

Fake-Graph-Tests blockieren mindestens falsche Methode oder Graph-Version,
abweichende Site/Liste/Operation/Rolle/Permission, fehlenden Site-Read-Grant,
fremden NextLink-Host oder Basis, Site-/List- oder Filterwechsel, Redirect, relative URL,
Paging-Schleife, unvollständiges Ende, ungültigen Payload, falsche Feldtypen,
Null-/Mehrfachzeile sowie Page-/Item-Limit-Überschreitung. Ein partieller Read
darf weder `OK`, `NOT_MODIFIED` noch einen gültigen Typ erzeugen.

Die ETag-Tests beweisen zusätzlich, dass der vollständige Read vor dem lokalen
Vergleich stattfindet, nur eine exakt passende Zeile `NOT_MODIFIED` ergeben
kann und kein Request einen Row-ETag als Collection-`If-None-Match` trägt.

## Validierungsreihenfolge

1. fokussierte Fake-Graph-, Adapter- und CLI-Tests,
2. Standalone-S4-Validator und `nac contracts verify`,
3. CLI-Hilfe sowie Offline-/No-Credential-/No-HTTP-Nachweise,
4. Spec-Traceability, Sprachparität und Links,
5. `python3 scripts/nac.py doctor --profile strict`,
6. `git diff --check`, vollständige `base...head`-Review und Remote-CI.

Die konkreten Befehle sind im Spec-Traceability-Manifest bindend aufgeführt.
Alle genannten Planungs-, Runtime-, Contract- und CLI-Checks werden in diesem
Implementierungsslice ausgeführt.

## Abschlussregel

S4 wurde mit Erfüllung aller sieben ACs, bestandenem Strict-Gate,
unabhängigem Review und grünen Protected-PR-Checks in PR #617 technisch offline implementiert; die Governance-Synchronisierung erfolgt im S5-PR. Der Branch öffnet weder External Service noch Human Approval und erlaubt
exakt null Live-Graph-Aufrufe. S4b bleibt ein separates Issue für spätere
Writes; S3 wird nicht stillschweigend erweitert.
