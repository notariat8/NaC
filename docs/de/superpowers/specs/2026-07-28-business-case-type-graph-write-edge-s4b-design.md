# BusinessCaseType Graph Write Edge S4b Design

Status: `S4B_OFFLINE_ONLY`; produktive Komposition bleibt außerhalb des Scopes
Datum: 28. Juli 2026
Scope: begrenzte Graph-Write-Planung und synthetische Fake-Graph-Ausführung

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-graph-write-edge-s4b
leading_issue: https://github.com/notariat8/NaC/issues/694
risk_gate: Privacy
delivery_mode: Protected PR
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4B-01
  - AC-S4B-02
  - AC-S4B-03
  - AC-S4B-04
  - AC-S4B-05
  - AC-S4B-06
  - AC-S4B-07
validation_commands:
  - python3 -m unittest tests.test_business_case_type_graph_write_edge tests.test_business_case_type_graph_write_edge_contract tests.test_business_case_type_graph_write_edge_cli tests.test_business_case_type_graph_write_edge_graph_contract tests.test_business_case_type_graph_write_edge_reconciliation tests.test_business_case_type_graph_write_edge_schema
  - python3 scripts/validate_business_case_type_graph_write_edge.py
  - python3 -m compileall -q src/notary_kg/business_case_type_mutation.py src/nac_m365_graph/business_case_type_write_plan.py src/nac_m365_graph/business_case_type_write_edge.py src/nac_m365_graph/business_case_type_write_dry_run.py scripts/validate_business_case_type_graph_write_edge.py tests/test_business_case_type_graph_write_edge.py tests/test_business_case_type_graph_write_edge_contract.py tests/test_business_case_type_graph_write_edge_cli.py tests/test_business_case_type_graph_write_edge_graph_contract.py tests/test_business_case_type_graph_write_edge_reconciliation.py tests/test_business_case_type_graph_write_edge_schema.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - git diff --check
```

## Zweck Und Grenze

S4b ergänzt eine eigene `BusinessCaseTypeMutation` und eine ausschließlich über
Ports injizierte Graph-Write-Kante für `case_create`, `case_status_update`,
`task_create`, `task_update` und `business_case_type_backfill`. Der
[Domain-Vertrag](../../../../workflows/contracts/business-case-type-graph-write-edge-s4b.contract.json)
ist die normative Grenze.

Der Slice enthält keine Live-Factory, keinen HTTP-Client, keine Credentials,
keine Environment-/Token-/Zertifikatslesung und keine Tenant-Schreibaktion.
Transport und Evidence sind Protokolle; Tests verwenden nur synthetische
In-Memory-Fakes.

## Exakte Operationen

| Operation | Methode | Liste | Felder |
| --- | --- | --- | --- |
| `case_create` | `POST` | `Akten` | `NacCaseId`, `Aktenzeichen`, `Vorgangstyp`, `VorgangstypId`, `Status`, `NotarTeam`, `Vertraulichkeitsstufe`, `NacWorkflowVersion`, `KgVersion` |
| `case_status_update` | `PATCH` | `Akten` | ausschließlich `Status` |
| `task_create` | `POST` | `AufgabenFristen` | `NacTaskId`, `NacCaseId`, `BpmnStepCode`, `Status`, `RequiresNotaryApproval`, optional `DueDate` |
| `task_update` | `PATCH` | `AufgabenFristen` | nichtleere Teilmenge aus `Status`, `DueDate`, `RequiresNotaryApproval`, `BlockedReason` |
| `business_case_type_backfill` | `PATCH` | `Akten` | ausschließlich `VorgangstypId` |

Alle Feldwerte werden vor der Planung gegen das Basis-Schema und die additive
BusinessCaseType-Foundation validiert. `VorgangstypId` ist Text mit
`maxLength: 128`, während nur das Legacy-Feld `Vorgangstyp` die vier Choices
trägt. Auch die übrigen Textlängen und Choice-Werte müssen dem provisionierten
Schema entsprechen; `RequiresNotaryApproval` ist das einzige Boolean-Feld und
`DueDate` muss ein zeitzonenbehafteter ISO-Zeitpunkt sein. `bool` darf nicht
als Integer- oder Textwert andere Feldtypen passieren.

Alle Ziele liegen exakt unter
`https://graph.microsoft.com/v1.0/sites/{site-id}/lists/{list-id}/items`.
Beta, Graph SDK, SharePoint REST und PnP sind nicht zulässig.

Solange `Akten.Vorgangstyp` ein Pflichtfeld ist, akzeptiert `case_create` nur
die vier Legacy-abbildbaren Typen `immobilienkaufvertrag`,
`unterschriftsbeglaubigung`, `online-gmbh-gruendung` und
`handelsregisteranmeldung`. `VorgangstypId` muss exakt demselben Wert
entsprechen.

## Bindung Und Identitäten

Ein Planer wird unveränderlich an Workspace, Site, beide Listen sowie zwei
verschiedene Principal-Referenzen gebunden. Der Laufzeitkontext muss Site,
Liste, Rolle, Zweck, freigegebene Operation und Approval exakt wiederholen.
Jede Abweichung blockiert vor Transport. Der Target-Binding-Hash enthält immer
Workspace, Site, Akten-Listen-ID und AufgabenFristen-Listen-ID; auch Drift in
der inaktiven Liste blockiert. Der Builder friert Mutation und Requests tief ein und bindet den vollständigen Plan an einen kanonischen SHA-256. Vor jedem Execute werden Mutation, S5-Hashes, Target, Liste, URLs, Methode, Felder, Authorization, Approval sowie Dedupe-/Freshness-Requests gegen den gebundenen Builder neu konstruiert und verglichen; jede Manipulation blockiert ohne Transport.

Die spätere Write-Identität ist nur Vertrag: `Sites.Selected` mit Site-Grant
`write`. Die bestehende BFF-UAMI bleibt unverändert `Sites.Selected` mit
Site-Grant `read`. Beide Identitäten müssen verschieden sein. Der Slice
erteilt keine Permission und erzeugt keine Credentials.

## Idempotenz Und Concurrency

`case_create` prüft vor dem Intent per GET den eindeutigen `NacCaseId`;
`task_create` entsprechend `NacTaskId`. Der Dedupe-GET verwendet ausschließlich
die dokumentierten Query-Optionen `expand` und `$filter`; top-level
`$select` und `$top` werden nicht gesendet. Der lokale Parser akzeptiert
höchstens zwei Treffer. Jedes `@odata.nextLink` ist eine Ambiguität und
erzwingt Reconciliation ohne POST. Kein Treffer erlaubt genau einen
POST-Versuch. Ein exakter Treffer löst nach dauerhaft eröffnetem Intent einen
frischen GET des konkreten Items aus. Erst dessen gebundene Item-ID, nichtleerer
ETag und exakte Felder liefern `DEDUPLICATED` ohne POST. Mehrere Treffer,
Payload-Drift oder fehlerhafter frischer Readback erzeugen sticky
Reconciliation. Bei HTTP 409 entscheidet derselbe Dedupe- und konkrete
Item-Readback ohne POST-Retry.

Vor jedem PATCH wird das Zielitem frisch und nur mit den Mutationsfeldern
gelesen. Nur wenn dessen exakter ETag
dem erwarteten ETag entspricht, wird genau dieser frische Wert als `If-Match`
verwendet. Es gibt höchstens einen PATCH-Versuch. HTTP 412 wird nie automatisch wiederholt. Der anschließende Readback darf
`PRECONDITION_FAILED` oder `PRECONDITION_FAILED_ALREADY_APPLIED` nur aus HTTP
200, exakt gebundener Item-ID, nichtleerem ETag, valider Response-Shape und den
tatsächlichen Mutationsfeldern ableiten. Unpassender Status oder Shape erzeugt
Reconciliation und niemals falsche `verified_not_applied`-Evidence. Auch sonstige
negative Provider-Antworten unterscheiden nach strengem Readback zwischen
`WRITE_REJECTED`, `WRITE_REJECTED_STATE_ALREADY_APPLIED` und Reconciliation.
Bei PATCH-5xx stammt die Readback-Item-ID ausnahmslos aus
`plan.mutation.item_id`; eine fremde `id` im Response-Body wird ignoriert und
erscheint nicht in Evidence. Nur POST darf eine valide Response-Item-ID für den
Readback verwenden.

## S5-Hashbindung

Backfill akzeptiert ausschließlich eine S5-Einzeloperation. Der Edge berechnet
erneut den S5-Idempotenzschlüssel aus Manifest-Hash, Record-Ref-Hash,
Ziel-`BusinessCaseTypeId` und aktuellem ETag. Zusätzlich wird der kanonische
SHA-256 der vollständigen S5-Operation mit `record_ref_hash`, `field`,
`value`, `if_match` und `idempotency_key` geprüft. Erst danach darf ein
`VorgangstypId`-PATCH geplant werden.

## Evidence Und Reconciliation

Der Evidence-Hook und sein autoritativer, prozessübergreifend persistenter
State-Store werden injiziert. Der Store führt für jeden Execution-Key aus
`target_binding_hash` und `mutation_id` `reconciliation_state`,
`intent_state`, `intent_generation` und `closed_generation`. Ein Lookup nur
über die Mutation-ID ist verboten. Vor dem Write muss der Edge die atomar
eröffnete nächste Intent-Generation dauerhaft als `open` zurücklesen. Ein
Start ist nur bei `clear + absent` oder zuvor verifiziertem `retryable`
zulässig. `closed` ist für diesen Execution-Key terminal.

Im normalen Pfad gilt exakt `intent -> write -> outcome -> readback`. Nur ein
atomar bestätigter verifizierter Readback darf dieselbe Intent-Generation mit
`closed_generation == intent_generation` schließen. Bei unklarem
Transportergebnis, Provider-5xx, fehlendem Create-Item, fehlgeschlagenem
Outcome-Hook oder nicht verifiziertem Readback bleibt das Intent offen; die
Evidencefolge lautet dann
`intent -> outcome -> reconciliation_required -> readback`.

Schlägt das Acknowledgement des Reconciliation-Markers fehl, bleibt das zuvor
dauerhaft eröffnete Intent beweiskräftig offen. Auch wenn eine frische
Hook-Instanz über demselben Store später `reconciliation_state=clear` meldet,
blockiert `intent_state=open` jeden weiteren Write vor Transport. Erst ein
externer Reconciliation-Prozess darf mit persistentem Closure-Proof exakt die
offene Generation schließen. Ein erfolgreicher Readback im unklaren Pfad,
ein bloßes `clear` oder ein lokaler In-Memory-Marker reichen niemals aus.

Wird die atomare Closure physisch persistiert, aber ihre nachgelagerte
Zustandsbestätigung ist nicht verfügbar, liefert der aktuelle Lauf einen
Persistenzfehler. Ein frischer Builder, Hook und Edge sehen dennoch das terminale
`closed` und blockieren vor jedem Transport; ein zweiter Write bleibt unmöglich.

Preflight-, Dedupe- und Freshness-Transportfehler liefern ausschließlich feste
strukturierte Reason-Codes; Exception-Typ, Meldung, URL, Header und Body werden
nicht exponiert. Evidence enthält nur Operationsname, Mutation-/Target-Hashes, technische
Result-Codes und optional den S5-Operationshash, keine rohen Site-, Listen-,
Item- oder Feldwerte.

HTTP 401, 403, 408 und 429 werden im selben Lauf nicht automatisch wiederholt.
Nur wenn ein strikter Readback beweist, dass der Write nicht angewendet wurde,
wird die Generation als `retryable` geschlossen. Ein späterer, separat
autorisierter Lauf darf nur mit einer neuen kanonischen
Authorization-Run-Identity aus Plan-SHA-256 und Approval-Referenz neu starten;
für 401/403 ist zusätzlich die Authentisierung zu erneuern.
Unklare Ergebnisse bleiben sticky offen; HTTP 412 bleibt terminal ohne Retry.

## Akzeptanzkriterien

- **AC-S4B-01:** Exakte Graph-v1.0-Methode, Ziel-, Feld-, Authorization-,
  Approval-, Request-, Workspace-, Site- und beide Listenbindungen werden vor
  jedem Execute kanonisch revalidiert; Feldtypen und Choices entsprechen dem
  produktiven SharePoint-Schema und auch Drift der inaktiven Liste blockiert.
- **AC-S4B-02:** Drift bei Rolle, Zweck, Approval, Site, Liste oder
  Write-Grant blockiert vor Transport.
- **AC-S4B-03:** Dokumentierter Dedupe-Query, lokales Zwei-Treffer-Limit,
  `nextLink` als Ambiguität, frischer konkreter Item-Readback, frischer exakter
  PATCH-ETag, strikter Readback und kein Retry auf HTTP 412.
- **AC-S4B-04:** Backfill schreibt nur `VorgangstypId` und bindet die
  kanonische S5-Einzeloperation.
- **AC-S4B-05:** Zielgebundene Execution-Keys, persistente Intent-Generationen
  und Closure-Proofs bleiben über frische Hook-Instanzen fail-closed:
  `clear + open` und terminales `closed` blockieren Replay; verifiziertes
  `retryable` erlaubt nur einen später separat autorisierten Lauf.
- **AC-S4B-06:** Null Live-Calls, Credentials, Factories und Tenant-Writes;
  BFF-UAMI bleibt `Sites.Selected/read`.
- **AC-S4B-07:** Contract, Validator, Fake-Graph-Tests, DE/EN-Traceability und
  Review stimmen überein.
