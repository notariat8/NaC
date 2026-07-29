# BusinessCaseType Graph Write Composition S4c Design

Status: `S4C_DESIGN`
Datum: 29. Juli 2026
Scope: produktionsnahe, aber strikt offline ausgeführte lokale Runtime-Komposition

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-graph-write-composition-s4c
leading_issue: https://github.com/notariat8/NaC/issues/698
risk_gate: Privacy
delivery_mode: Protected PR
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4C-01
  - AC-S4C-02
  - AC-S4C-03
  - AC-S4C-04
  - AC-S4C-05
  - AC-S4C-06
  - AC-S4C-07
  - AC-S4C-08
validation_commands:
  - python3 -m unittest tests.test_business_case_type_graph_write_composition tests.test_business_case_type_graph_write_state_store tests.test_business_case_type_graph_write_http_transport tests.test_business_case_type_graph_write_credentials tests.test_business_case_type_graph_write_crash_recovery tests.test_business_case_type_graph_write_composition_contract tests.test_business_case_type_graph_write_composition_cli
  - python3 scripts/validate_business_case_type_graph_write_composition.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 -m compileall -q src/nac_m365_graph/business_case_type_write_state.py src/nac_m365_graph/business_case_type_write_transport.py src/nac_m365_graph/business_case_type_write_composition.py src/nac_m365_graph/business_case_type_write_composition_smoke.py scripts/validate_business_case_type_graph_write_composition.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Zweck Und Grenze

S4c verdrahtet die unveränderte S4b-Write-Edge mit einem lokal persistenten
State-/Evidence-Adapter, einem exakten Microsoft-Graph-REST-v1.0-Transport und
einer expliziten Dependency-Injection-Komposition. Der Slice ergänzt keine
Fachoperation und lockert keine S4b-Grenze.

S4c ist kein Live-Pfad. Der Offline-Smoke verwendet einen temporären
SQLite-State und einen skriptbaren HTTP-Port. Er liest weder Environment,
Tokens noch Zertifikate und führt keine DNS-, Socket-, Graph- oder
Tenant-Aktion aus. Eine zentrale Multi-Instanz-Durabilität, S6/WORM-Publikation,
echte Approval-Verifikation, Write-Identität und Live-Factory bleiben
eigenständige spätere Gates.

## Lokaler Persistenzadapter

Der Store verwendet SQLite ausschließlich für technische, redigierte
Execution-Zustände. Der Schlüssel bleibt der in S4b definierte Hash aus
Target-Binding und Mutation-ID. Zustandsänderung und zugehöriges Event werden
in derselben `BEGIN IMMEDIATE`-Transaktion geschrieben.

Der garantierte Durabilitäts-Envelop ist ausdrücklich ein lokaler POSIX-
Dateisystempfad auf einem einzelnen Host, nicht OneDrive, NFS oder ein anderes
Netzdateisystem. Das Verzeichnis hat Modus `0700`, die Datenbank `0600`;
Symlinks sowie fremde Owner werden abgewiesen. SQLite läuft mit
`journal_mode=DELETE`, `synchronous=FULL`, `foreign_keys=ON`,
`trusted_schema=OFF` und `busy_timeout=0`. Nach Erstanlage wird auch das
Elternverzeichnis synchronisiert. Eine transiente, gleichberechtigte
`-journal`-Datei ist nur während einer SQLite-Transaktion zulässig; nach
sauberem Close bleibt keine Sidecar-Datei zurück. Getestet und behauptet wird
Prozessabsturz plus Reopen auf demselben Host. Kernel-, Strom-, Hardware-,
Dateisystem- oder Hostverlust sowie zentrale Multi-Instanz-Durabilität sind
nicht Teil der Garantie.

Jeder Übergang prüft die erwartete Generation und
`authorization_run_identity` per Compare-and-Swap. Die zulässige Matrix lautet:

| Ausgang | Aktion | CAS-Prädikat | Ergebnis |
| --- | --- | --- | --- |
| `clear + absent`, Generation `0/0` | `intent` | expected `0`, keine vorherige Run-Identity | `clear + open`, Generation `1/0` |
| `clear + retryable`, Generation `n/n` | `intent` | expected `n`, vorherige Identity exakt, neue Identity verschieden | `clear + open`, Generation `n+1/n` |
| `clear + open`, Generation `n/c` | `outcome` | gleiche Generation/Identity, noch kein gleiches Phasenereignis | State unverändert, Event ergänzt |
| `clear + open`, Generation `n/c` | `reconciliation_required` | gleiche Generation/Identity | `required + open`, Generation `n/c` |
| `clear + open`, Generation `n/c` | verifizierter `readback` | gleiche Generation/Identity, Closure terminal oder retryable | `clear + closed|retryable`, Generation `n/n` |
| `required + open`, Generation `n/c` | nicht schließender `readback` | gleiche Generation/Identity, `close_intent=false` | State unverändert, Event ergänzt |
| `required + open` | Closure/Replay | immer | blockiert |
| `closed` | jede Mutation | immer | terminal blockiert |

Konkurrierende Erst-Intents, doppelte Phasenereignisse, falsche Generationen,
gleiche Retry-Identity, Busy/Timeout sowie Commitfehler liefern `false` oder
`unavailable` und verursachen keinen Teilcommit. Ein offenes Intent wird vor
jedem Transport committed und durch eine neue Verbindung zurückgelesen.

Die Datenbankdatei wird nicht über Symlinks geöffnet, erhält restriktive
Berechtigungen und feste Größen-/Schema-Grenzen. Persistiert werden nur
allowlist-basierte technische Hashes, Operation, Generationen, HTTP-Status und
stabile Result-Codes. Feldwerte, Site-/Listen-/Item-IDs, URLs, Header, Bodies,
Tokens, Zertifikate und rohe Approval-Referenzen sind verboten.

## HTTP- Und Credential-Grenze

Die Kompositionswurzel übergibt den Transport ausschließlich an den
`BusinessCaseTypeGraphWriteEdge`; andere Aufrufer sind nicht Teil des
Contracts. Der Transport wird zusätzlich mit den zwei exakten, aus dem bereits
validierten Target abgeleiteten Collection-Pfaden konstruiert und akzeptiert nur
Requests darunter. Eine Plan-SHA-Prüfung kann der bestehende
`GraphWriteTransport`-Port nicht selbst durchführen und wird daher nicht
behauptet. Zulässig sind `GET`, `POST` und `PATCH` unter
`https://graph.microsoft.com/v1.0`. Graph Beta, fremde Hosts, SharePoint REST,
PnP, Redirects und automatische Retries sind gesperrt.

Nur der Transport kennt den injizierten Access-Token-Provider. Er wird erst
nach erfolgreicher Plan-, Authorization- und Persistenzprüfung aufgerufen.
Jeder `transport.request` führt exakt einen HTTP-Versuch aus; ein vollständiger
Edge-Lauf darf entsprechend seinem S4b-Plan mehrere Transportaufrufe enthalten.
S4c enthält keine Env-/Managed-Identity-/Zertifikatsfactory. Der HTTP-Port
erhält kanonische Requestbytes und liefert Status, begrenzte objektförmige
JSON-Antworten sowie allowlist-basierte Response-Header. Providerfehler werden
ohne Exception-Text oder Rohdaten in feste Ergebnisse übersetzt.

## Crash-Recovery

Fault-Injection prüft mindestens:

1. Intent persistiert, Transport noch nicht aufgerufen,
2. Transportwirkung unklar, Outcome noch nicht persistiert,
3. Outcome persistiert, Readback noch nicht abgeschlossen,
4. Closure persistiert, Acknowledgement verloren,
5. korrupter, übergroßer oder nicht lesbarer State.

Nach einem Restart darf kein automatischer zweiter Write entstehen. Offene oder
unklare Zustände bleiben gesperrt, bis ein späterer externer
Reconciliation-Prozess einen Closure-Proof liefert. Dieser Prozess ist nicht
Teil von S4c.

## Akzeptanzkriterien

- **AC-S4C-01:** Eine Kompositionswurzel verdrahtet unveränderten S4b-Builder
  und -Edge mit State-, HTTP- und Credential-Ports; zulässig bleiben exakt fünf
  Operationen.
- **AC-S4C-02:** State und redigiertes Event committen im definierten lokalen
  POSIX-/SQLite-Prozess-Restart-Envelop atomar mit Generation-CAS,
  Authorization-Run-Bindung, Locking und fail-closed
  Datei-/Schema-/Größenprüfung.
- **AC-S4C-03:** Nur der Edge darf den auf beide Ziel-Collections begrenzten
  Transport verwenden; er erlaubt nur Graph-v1.0-Requests,
  `GET`/`POST`/`PATCH`, exakte Header, begrenztes Objekt-JSON, keine Redirects
  und exakt einen HTTP-Versuch pro Transportaufruf.
- **AC-S4C-04:** Nur der Transport darf den injizierten Token-Provider
  aufrufen. Blockaden vor dem ersten Transport verursachen null
  Token-Provider-Aufrufe; der Offline-Smoke darf synthetische Token-Provider-
  Aufrufe, aber keine externen Credential-Store-, Env- oder Dateireads haben.
- **AC-S4C-05:** Persistenz, Resultate und Fehler sind rekursiv allowlist-basiert
  und enthalten keine Ziel-, Payload-, Approval- oder Credential-Rohdaten.
- **AC-S4C-06:** Dedupe, ETag/`If-Match`, S5-Hash, Execution-Key und
  Authorization-Run-Identity bleiben unverändert bindend.
- **AC-S4C-07:** Crash-/Restart-Tests beweisen, dass offene oder unklare
  Zustände Replay blockieren und eine dauerhaft geschlossene Generation auch
  nach verlorenem Acknowledgement terminal bleibt.
- **AC-S4C-08:** Abschlussstatus ist nur
  `S4C_COMPOSITION_READY_OFFLINE` bei null Socket-/DNS-/Live-Graph-,
  externen Credential-Store- und Tenant-Aktivitäten. Synthetische
  Token-Provider-Aufrufe werden separat gezählt; zentrale oder produktive
  Durabilität wird nicht behauptet.

## Nicht Im Scope

- echte Write-Identität, Entra-App, Permission oder Site-Grant,
- Environment-, Managed-Identity-, Secret- oder Zertifikatsfactory,
- Live-Graph-, SharePoint- oder Teams-Aufruf,
- zentraler Multi-Instanz-State oder verteilter Lock,
- S6/WORM-Publisher-Komposition,
- Live-Execute-, Reconcile- oder Cleanup-Command.
