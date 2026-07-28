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
  - python3 -m unittest tests.test_business_case_type_graph_write_edge tests.test_business_case_type_graph_write_edge_contract
  - python3 scripts/validate_business_case_type_graph_write_edge.py
  - python3 -m compileall -q src/notary_kg/business_case_type_mutation.py src/nac_m365_graph/business_case_type_write_plan.py src/nac_m365_graph/business_case_type_write_edge.py scripts/validate_business_case_type_graph_write_edge.py tests/test_business_case_type_graph_write_edge.py tests/test_business_case_type_graph_write_edge_contract.py
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
`task_create` entsprechend `NacTaskId`. Der Dedupe-GET projiziert die
vollständige Create-Allowlist und fordert mit `$top=2` höchstens die zur
Ambiguitätserkennung nötigen Treffer an. Es wird keine Folgeseite geladen;
jedes `@odata.nextLink` ist selbst eine Ambiguität und erzwingt Reconciliation
ohne POST. Kein Treffer erlaubt genau einen POST-Versuch.
Nur ein Treffer mit exakt identischem Create-Payload liefert `DEDUPLICATED`
ohne POST. Mehrere Treffer oder Payload-Drift erzeugen sticky Reconciliation
ohne POST. Liefert ein konkurrierender POST HTTP 409, entscheidet ein exakter
Dedupe-Readback ohne POST-Retry zwischen `DEDUPLICATED`, Ablehnung und
Reconciliation.

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
State-Store werden injiziert. Der Store führt für jede Mutation
`reconciliation_state`, `intent_state`, `intent_generation` und
`closed_generation`. Vor dem Write muss der Edge die atomar eröffnete nächste
Intent-Generation dauerhaft als `open` zurücklesen. Ein Start ist nur bei
`clear + absent` zulässig. `closed` ist für diese Mutation-ID terminal und darf
nie wieder geöffnet oder erneut ausgeführt werden.

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

## Akzeptanzkriterien

- **AC-S4B-01:** Exakte Graph-v1.0-Methode, Ziel-, Feld-, Authorization-,
  Approval-, Request-, Workspace-, Site- und beide Listenbindungen werden vor
  jedem Execute kanonisch revalidiert; auch Drift der inaktiven Liste blockiert.
- **AC-S4B-02:** Drift bei Rolle, Zweck, Approval, Site, Liste oder
  Write-Grant blockiert vor Transport.
- **AC-S4B-03:** Bounded Dedupe mit `nextLink` als Ambiguität, frischer exakter
  PATCH-ETag, strikter Readback und kein Retry auf HTTP 412.
- **AC-S4B-04:** Backfill schreibt nur `VorgangstypId` und bindet die
  kanonische S5-Einzeloperation.
- **AC-S4B-05:** Persistente Intent-Generationen und Closure-Proofs bleiben
  über frische Hook-Instanzen fail-closed: `clear + open` und terminales `closed`
  blockieren Replay, auch nach fehlender nachgelagerter Closure-Bestätigung.
- **AC-S4B-06:** Null Live-Calls, Credentials, Factories und Tenant-Writes;
  BFF-UAMI bleibt `Sites.Selected/read`.
- **AC-S4B-07:** Contract, Validator, Fake-Graph-Tests, DE/EN-Traceability und
  Review stimmen überein.
